# 07. NN 통합 (Neural Network Integration)

**최종 갱신**: 2026-04-28 (v0.35)

**NN 개발 모드** ([01 § 1.1](01_vision_scope.md#두-운용-모드))에서의 전용 워크플로 설계.
일반 DSP 모드에서는 이 문서의 내용 대부분이 숨겨져 있고, **학습 완료된 NN이 표준
Plugin 포맷으로 저장되면 DSP 모드에서 일반 Plugin처럼 사용 가능**한 것만 접점이다.

---

## NN 모드의 두 단계

NN 개발 모드는 **명확히 분리된 두 Step**으로 구성된다:

```
Step 1: 학습 데이터 추출 (Dataset Extraction)
  - 새로 개발할 NN의 학습 데이터를 Pipeline Run 경유로 수집
  - Variant별 물리 조건 분리 (A: 이상화 / D: 현실)
  - HDF5 포맷으로 저장 → Training/Dev/Test 분할

Step 2: NN 평가 (NN Evaluation)
  - <nn_file_name>.py 로드
  - Training / Dev / Test error 측정 (Bayes error는 고급 옵션)
  - Variant 격자 분석으로 bias/variance/data mismatch 진단
```

**본 문서 7.1~7.6 = Step 1·2 공통 인프라**, **7.4 = Step 1 상세**, **7.6 = Step 2 상세**.
Step 간 명확히 분리되었음을 Workbench UI가 반영 (05 § 5.x).

MVP 기준으로 **실제 구현 제공되는 NN은 Pairing 하나**이며, NN 모드 구조 자체는 MVP에
포함되어 다른 NN을 추가하려는 사용자의 기반이 된다.

---

## 7.1 설계 원칙

> ⚠️ **v0.35 정합**: 본 섹션의 NN Plugin 모델은 **v0.13 시점 사고**.
> v0.35 도입 SDK Layer (02 § 2.6b, 17 § 17.2.6) 와의 관계:
>
> - **NN Plugin도 SDK Plugin Protocol 준수** (DetectorProtocol/TrackerProtocol/AngleEstimatorProtocol/PredictorProtocol 등)
> - 일반 DSP Plugin과 NN Plugin은 동일 Protocol — 차이는 내부 구현뿐 (NN인지 numpy인지)
> - NN Plugin이 `.trsim-pkg`로 패키징될 수 있음 — `manifest.toml` 의 `[entry_points]` 에 `trsim.plugins.tracker = "my_nn:NNTracker"` 등록
> - DLC 작성자는 numpy 경계만 지키면 PyTorch/TF 자유 사용 (원칙 2)
>
> 즉 본 섹션 원칙은 모두 v0.35에서도 유효, 다만 **Plugin 등록 방식이 SDK API + .trsim-pkg manifest 표준화** 됨.

### 원칙 1: NN도 Plugin이다 (기존 시스템 확장, 별도 시스템 아님)

NN Plugin과 일반 Plugin은 **같은 Contract**를 만족한다.
차이는 "내부 구현이 신경망일 뿐".

```python
class MyAngleEstimator(AngleEstimatorContract):
    """4ch 위상 → AZ/EL NN 추정기. 여전히 numpy in/out."""

    def __init__(self):
        self._weights = load_weights("./my_model.npz")  # 학습된 가중치

    def estimate(self, phases: np.ndarray) -> tuple[float, float]:
        x = phases.astype(np.float32)
        h = relu(x @ self._weights["w1"] + self._weights["b1"])
        out = h @ self._weights["w2"] + self._weights["b2"]
        return float(out[0]), float(out[1])
```

Pipeline 입장에서는 **NN인지 아닌지 구별할 필요가 없다**.
이게 "프레임워크 무관" 원칙의 본질.

### 원칙 2: 프레임워크 경계는 numpy

- Plugin이 받는 것: numpy array
- Plugin이 돌려주는 것: numpy array or dataclass (내부에 ndarray)
- 내부에서 PyTorch/TF/JAX/pure numpy — **자유**

이 경계를 지키면:
- 외부 프레임워크 의존성이 Workbench 코어에 안 섞임
- ONNX, TensorRT 등으로 배포할 때도 동일 인터페이스
- 성능 프로파일링이 Plugin 경계에서 깔끔

### 원칙 3: 학습 데이터는 Pipeline Run의 부산물

**학습 데이터를 수집할 때도, 추론할 때도 동일한 Pipeline을 경유한다.**
시뮬의 물리 함수(`physics/fmcw.py` 등)를 직접 호출해 Dataset을 만드는 방식은
**금지**한다. 이유는 그러면 "학습 시점의 신호 경로 ≠ 추론 시점의 신호 경로"가 되어
검증 워크벤치의 일관성이 깨지기 때문.

```
추론 (Primary):
    Scenario → Pipeline (NN Plugin) → Run 결과

학습 (Auxiliary, 그러나 동일 Pipeline 사용):
    Scenario → Pipeline Run (정상 실행) → Probe 기록 → Trace
                                                          ↓
                                              SampleSpec 추출기
                                                          ↓
                                                      Dataset
                                                          ↓
                                              Training (Pipeline 외부)
                                                          ↓
                                                      가중치 .npz
                                                          ↓
                                              Plugin으로 로드 → 추론
```

**Pipeline 외부에서 돌아가는 것은 학습 알고리즘 자체뿐**:
optimizer step, loss 역전파, gradient 적용.
샘플을 만드는 과정·추론은 전부 Pipeline을 통해서만.

상호 의존 케이스(NN A의 학습 데이터가 NN B의 출력에 의존 등)는
§ 7.4.6 "단계적 학습 전략"에서 다룬다.

### 원칙 4: 학습된 가중치는 외부 파일

Plugin 코드와 가중치를 분리:

```
plugins/my_angle_estimator/
├── plugin.py              ← Plugin 클래스 정의 (얇음)
├── weights/
│   ├── v1.0_baseline.npz
│   └── v1.1_improved.npz  ← 여러 버전 공존
├── architecture.toml      ← 네트워크 구조 설명
└── training_log.json      ← 학습 기록 (재현용)
```

이러면:
- 같은 Plugin 코드 + 다른 가중치 = 다른 Run 결과 → 비교 실험 용이
- 가중치만 공유 가능 (코드는 공개, 가중치는 연구 자산으로 보호)

### 원칙 5: 학습 환경은 열려 있음

내부(Workbench UI) / 외부(CLI, 외부 GPU 서버) 어디서든 학습 가능.
**공유되는 것은 설정 스키마**(`training.toml`)와 **가중치 포맷**(`.npz`).

### 원칙 6: NN 도입은 부분적·선택적이다 (Opt-in)

**Workbench의 기본 상태는 "NN이 전혀 없는 Pipeline"이다.**
사용자는 원하는 **한 스테이지만** NN으로 교체할 수 있고, 나머지는 기본 구현을 그대로 쓴다.
전면 NN화(모든 스테이지 NN)는 **선택이지 요구사항이 아니다**.

```
가장 흔한 패턴 (Case 0):      [모두 기본] + [Pairing만 NN]
실험적 패턴 (Case A~C):        [여러 NN 조합]
연구 목표 (Case D):            [End-to-End, 모두 NN]
```

**이 원칙의 함의**:

- Pipeline은 **"NN 없이도 완전 동작"**해야 함 — 모든 기본 Plugin이 항상 제공됨
- 사용자가 Pairing만 NN으로 돌린 Run과 Tracker만 NN으로 돌린 Run은 **별개의 실험**이며, 서로 비교 가능
- Dataset Builder도 **"NN 없는 기본 Pipeline"**을 기본 설정으로 제공
- Wave 1 구현 목표는 "한 NN만 교체해도 완벽히 돌아가는 상태" — 여러 NN 동시 지원은 자연스러운 파생 결과

---

## 7.2 Stage Slot 시스템 (Pipeline 확장)

### 7.2.1 현재 → 확장 구조

**현재 (06 § 3.3)**: 6개 스테이지가 고정 순서로 연결된 선형 Pipeline.

**확장 후**: Pipeline이 **Slot 시퀀스**로 정의되며, 각 Slot은 Contract와 필수 여부를 가짐.

```python
@dataclass(frozen=True)
class StageSlot:
    """파이프라인의 한 자리."""
    slot_id: str                        # "detector", "classifier"
    contract: type                      # Protocol 타입
    required: bool                      # 비면 Pipeline 조립 실패 여부
    default_plugin: str | None          # "plugins_builtin/default_detector"

DEFAULT_PIPELINE_SLOTS = (
    StageSlot("transmitter", TransmitterContract, required=True,
              default_plugin="default_transmitter"),
    StageSlot("environment", EnvironmentContract, required=True,
              default_plugin="default_environment"),
    StageSlot("receiver", ReceiverContract, required=True,
              default_plugin="default_receiver"),
    StageSlot("detector", DetectorContract, required=True,
              default_plugin="default_detector"),       # v0.34: CA-CFAR / OS-CFAR 선택
    StageSlot("angle_estimator", AngleEstimatorContract, required=False,
              default_plugin="default_angle_estimator"),  # 🆕 NN 위한 분리
    StageSlot("pairing", PairingContract, required=True,
              default_plugin="default_pairing"),
    StageSlot("data_associator", DataAssociatorContract, required=True,
              default_plugin="default_gnn"),              # 🆕 v0.34: 다중 표적 1:1 매칭
    StageSlot("tracker", TrackerContract, required=True,
              default_plugin="default_ekf"),              # v0.34: EKF / UKF 선택
    StageSlot("classifier", ClassifierContract, required=False,
              default_plugin=None),  # 🆕 옵셔널, 비워두면 건너뜀
)
```

### 7.2.2 각도 추정 스테이지 분리 이유

현재 `Receiver.compute_angle()`이 FFT와 각도 추정을 같이 한다.
NN으로 각도 추정만 바꾸고 싶은 경우를 위해 **스테이지 분리**:

```
기존:    Receiver (FFT + Angle 같이) → Detector → Pairing → ...
분리 후:  Receiver (FFT) → Detector → AngleEstimator → Pairing → ...
```

Wave 1에서 NN 각도 추정을 실험하려면 이 분리가 선결 작업.
기본 Receiver는 내부에 기본 AngleEstimator를 쓰지만, Slot 기반 Pipeline은 두 스테이지를 분리된 단위로 다룸.

### 7.2.3 Classifier 스테이지 (새 스테이지)

```python
class ClassifierContract(Protocol):
    """Track 특성 → 표적 클래스 확률."""

    name: str
    version: str

    def classify(self, track: Track) -> ClassificationResult:
        ...
```

```python
@dataclass(frozen=True)
class ClassificationResult:
    class_probabilities: dict[str, float]   # {"corvette": 0.82, "frigate": 0.15, ...}
    predicted_class: str                     # top-1
    confidence: float                        # top-1 probability
```

Pipeline 끝에서 Tracker가 Track을 뱉으면 Classifier가 붙어 클래스를 부여.
없으면 스킵 (Track 그대로 출력).

### 7.2.4 Pipeline 실행

```python
class StagedPipeline:
    def __init__(self, slots, plugins: dict[str, Any]):
        self.slots = slots
        self.plugins = plugins

    def step(self, dt, env):
        # Slot 순서대로 실행, 각 Slot의 출력을 다음 Slot 입력으로
        context = PipelineContext(dt=dt, env=env)
        for slot in self.slots:
            plugin = self.plugins.get(slot.slot_id)
            if plugin is None:
                if slot.required:
                    raise MissingStage(slot.slot_id)
                continue
            context = self._run_slot(slot, plugin, context)
        return context.as_radar_output()
```

`PipelineContext`는 스테이지 간 주고받는 누적 상태 (기존 RadarOutput 확장).

---

## 7.3 NN Plugin Contract

> ⚠️ **v0.35 정합**: 본 섹션의 `NNPluginMixin` 은 v0.13 시점 사고.
> v0.35 SDK Layer 도입 후 다음 결정 필요 (Q-N7 등록):
>
> - **옵션 A**: `NNPluginMixin` 도 SDK Public API에 포함 (`trsim.sdk.NNPluginMixin`) —
>   DLC 작성자가 NN Plugin 만들 때 직접 사용
> - **옵션 B**: SDK는 일반 Protocol만 (TrackerProtocol/DetectorProtocol 등), NNPluginMixin은
>   App Layer 내부 헬퍼로만 — DLC는 일반 Protocol 통해 NN 적용
>
> MVP는 옵션 B (SDK 단순화). NN-specific 기능 (internal probes, weights 자동 로드 등)이
> 일반화되면 옵션 A로 전환. Q-N7 OPEN_QUESTIONS에 등록.

NN이라서 특별히 필요한 **추가 인터페이스** 정의.
기본 Contract(Detector, Tracker 등)에 **옵션으로 믹스인**하는 방식.

### 7.3.1 NNPluginMixin

```python
class NNPluginMixin(Protocol):
    """NN 기반 Plugin이 선택적으로 구현."""

    model_architecture: str                 # "mlp_3x64" / "resnet_small" / custom string
    weights_path: Path                      # 가중치 파일 경로
    framework_origin: str                   # "tensorflow" / "pytorch" / "numpy_only"

    def load_weights(self, path: Path) -> None:
        """가중치 로드. configure() 직후 자동 호출."""

    def declare_internal_probes(self) -> dict[str, type]:
        """Activation/feature map 등 내부 관찰점."""
        return {}
```

믹스인이므로:
- 일반 Plugin: `class MyDetector(DetectorContract): ...`
- NN Plugin: `class MyNNDetector(DetectorContract, NNPluginMixin): ...`

Pipeline은 여전히 Detector로만 다루고, 학습/시각화 도구만 NNPluginMixin을 추가로 인식.

### 7.3.2 Internal Probe (Wave 1 후 추가)

일반 Probe와 달리, **모델 내부 값**을 노출:

```python
class MyNNDetector(DetectorContract, NNPluginMixin):
    def declare_internal_probes(self):
        return {
            "layer1_activation": np.ndarray,
            "attention_weights": np.ndarray,
            "feature_map": np.ndarray,
        }

    def detect_from_spectrum(self, spectrum):
        x = self._preprocess(spectrum)
        h1 = relu(x @ self._w1)
        self._probe("layer1_activation", h1)
        ...
```

IDE의 Probe 패널이 이걸 자동 인식 — NN 내부 시각화(Q6 답변 반영).

### 7.3.3 Stateful 취급

대부분의 DSP 플러그인은 stateless이지만,
**Tracker NN / End-to-End 모델**은 **히든 스테이트**를 프레임 간 유지해야 함.

```python
class RNNTrackerContract(TrackerContract):
    def reset(self):
        """Run 시작 시 히든 스테이트 초기화."""
        self._hidden = None

    def update(self, detections, dt):
        output, new_hidden = self._rnn_step(detections, self._hidden)
        self._hidden = new_hidden
        return output
```

Pipeline이 **Run 경계에서 자동으로 reset()** 호출. Probe 시스템에 `_hidden`을 Internal Probe로 등록하면 타임라인 스크럽 시 상태 확인 가능.

---

## 7.4 학습 데이터 수집 (Data Export)

### 7.4.1 통합 모듈

**원래 요구 2가지**가 하나의 모듈로 통합:

- "추적 결과 CSV 추출" → Manual Export (작은 단위)
- "NN 학습 데이터 수집" → Automatic Dataset Building (큰 단위)

```
app/data_exporter.py  ← 하나의 모듈
├── ManualExporter       : 현재 Run을 CSV/HDF5로
├── AutoDatasetBuilder   : 여러 Run에 걸쳐 Dataset 누적
└── DatasetSchema        : 포맷 정의
```

### 7.4.2 Manual Export

UI에서 "Export Current Run..." 커맨드:

```
┌─ Export ────────────────────────────┐
│ Source: Current Run (frame 0 ~ 200) │
│                                      │
│ Select Probes to Export:             │
│  ☑ detections                        │
│  ☑ tracks                            │
│  ☐ fft_spectrum (large)              │
│  ☐ ground_truth                      │
│                                      │
│ Format: ○ CSV ● HDF5 ○ Parquet       │
│ Path:   ~/exports/run_0042.h5        │
│                                      │
│ [Cancel] [Export]                    │
└──────────────────────────────────────┘
```

- CSV는 **평탄화 가능한 Probe**에만 (tracks, detections). ndarray는 HDF5 필요
- 추적 결과 CSV는 기본 프리셋으로 "trajectory.csv"와 같은 포맷 자동 제공

### 7.4.3 Automatic Dataset Builder

여러 Pipeline Run을 연속 실행하며 **각 Run의 Trace에서 학습 샘플을 추출·누적**.

**중요**: 이 빌더는 시뮬 물리 함수를 직접 호출하지 않는다 (원칙 3).
반드시 **정상 Pipeline Run을 거친 Trace에서만** 샘플을 뽑는다.

#### 실행 흐름

```
for (scenario, seed) in build_job.runs:
    # 1. 정상 Pipeline 조립 — 이때 사용할 Pipeline 구성이 매우 중요
    pipeline = build_pipeline(build_job.pipeline_config, scenario)

    # 2. Run 실행 (Probe 기록 켜짐)
    trace = run_pipeline(pipeline, scenario, seed,
                         probe_selection=build_job.probe_selection)

    # 3. SampleSpec에 따라 Trace에서 샘플 추출
    samples = extract_samples(trace, build_job.sample_spec,
                              ground_truth=GTLoader.load(scenario))

    # 4. HDF5 shard에 누적
    dataset_writer.append(samples)
```

#### 스키마

```python
@dataclass(frozen=True)
class DatasetBuildJob:
    job_id: str
    output_path: Path              # workspace/datasets/<job_id>.h5

    # 어떤 Run을 돌릴지
    scenarios: tuple[str, ...]
    seeds: tuple[int, ...]

    # 어떤 Pipeline 구성으로 Run을 돌릴지 (핵심)
    #   - 학습 전 상태이므로 대개 "기본 구현" 조합
    #   - 상호 의존 케이스는 § 7.4.6 참조
    pipeline_config: PipelineConfig

    # Run에서 어떤 Probe를 기록할지
    probe_selection: ProbeConfig

    # Trace에서 어떻게 샘플을 잘라낼지
    sample_spec: SampleSpec

    # 학습 대상 Plugin — 이 Dataset으로 학습될 NN Plugin의 경로·메타
    # (신규) Dataset과 Trainer를 연결하는 명시적 다리
    training_target: TrainingTargetRef

    # 누적 제한
    max_samples: int | None


@dataclass(frozen=True)
class TrainingTargetRef:
    """이 Dataset이 학습시킬 NN Plugin의 참조."""
    plugin_id: str                      # "my_pairing_nn"
    plugin_source: Path                 # "plugins/my_pairing_nn/plugin.py"
    architecture_path: Path             # "plugins/my_pairing_nn/architecture.toml"
    weights_output_path: Path           # "plugins/my_pairing_nn/weights/v2.npz"

    # Dataset manifest에 기록됨. Trainer가 실행될 때 이 정보로:
    #   1. Plugin 클래스 로드 (forward 구조 파악)
    #   2. Architecture 로드 (레이어 크기)
    #   3. 학습 완료 후 weights_output_path에 .npz 저장
    #   4. Plugin Manager가 가중치 파일 변경 감지 → 자동 재로드
```

**왜 명시적으로 연결하는가**: 기존에는 "Dataset을 만든다" 와 "NN을 학습시킨다"가 분리된 두 행위였다. 사용자가 `open in trainer` 눌러도 어느 Plugin에 대해 학습하는지 모호. `training_target`을 Dataset Job의 필수 필드로 두면:

- Dataset Manifest에 "이 데이터가 어느 Plugin을 겨냥하는지" 기록됨
- Trainer가 Dataset을 열면 Plugin 정보가 자동 채워짐
- 학습 결과가 정해진 경로에 저장되어 **자동으로 Plugin의 다음 실행에 반영**됨


#### SampleSpec — 학습 태스크별

SampleSpec은 **Trace와 GT에서 어떤 필드를 어떻게 묶어 샘플로 만들지** 정의.
Trace 추출이라서 Probe 경로를 명시:

```python
# 각도 추정: (phases_4ch, az_gt, el_gt) 튜플
angle_spec = SampleSpec(
    inputs={"phases": ProbeRef("up_peaks", "phases_rad")},
    labels={"az_gt": GTRef("target.az_deg"), "el_gt": GTRef("target.el_deg")},
    per_frame=True,                     # 프레임마다 1 샘플
    filter="is_visible and in_beam",    # 필터 조건
)

# 분류: (track_features, class_label)
classifier_spec = SampleSpec(
    inputs={"track_features": ProbeRef("tracks", "features")},
    labels={"class": GTRef("target.ship_class")},
    per_track=True,                     # 트랙 하나당 1 샘플
)

# End-to-End: (raw_adc_cube, track_sequence)
e2e_spec = SampleSpec(
    inputs={"adc_cube": ProbeRef("rx_fft_spectrum", "channels_raw")},
    labels={"tracks": GTRef("tracks")},
    per_scenario=True,                  # 전체 시퀀스가 1 샘플
)
```

Workbench는 이걸 받아:
1. 지정 시나리오들을 배치로 실행
2. 프레임마다 SampleSpec에 따라 튜플 추출
3. HDF5 파일에 누적 (shard 분할 지원)
4. 최종 `dataset.h5` + `dataset_manifest.toml` (schema, stats 포함)

### 7.4.4 Dataset 포맷

표준 HDF5 구조:

```
dataset.h5
├── meta (attrs: job_id, created_at, scenarios, total_samples)
├── schema (attrs: JSON, 각 필드 shape/dtype/description)
├── inputs/
│   ├── phases        (dataset, N × 4, complex64)
│   └── ...
├── labels/
│   ├── az_gt         (dataset, N, float32)
│   ├── el_gt         (dataset, N, float32)
│   └── ...
└── splits/           (optional, pre-computed train/val/test indices)
    ├── train         (dataset of int indices)
    ├── val
    └── test
```

### 7.4.5 Wave별 기본 SampleSpec 템플릿 제공

각 Wave에 대해 "이걸로 바로 학습 시작 가능" 템플릿:

| Wave | 작업 | 템플릿 SampleSpec |
|---|---|---|
| 1 | 각도 추정 | `templates/angle_estimation.toml` |
| 1 | 분류 | `templates/classifier.toml` |
| 1 | **Pairing (Up/Down 매칭)** ⭐ | `templates/pairing.toml` |
| 3 | 추적 | `templates/tracking.toml` |
| 3 | End-to-End | `templates/e2e.toml` |

**주의**: 본 프로젝트의 Pairing은 FMCW Triangle의 Up/Down sweep 매칭 단일 정의이다.
다른 레이더 모델(예: CW+FMCW Hybrid)의 Pairing은 입출력이 완전히 다르므로 미래에 해당 RadarModel이
추가될 때 별개 템플릿으로 제공된다. 참고: [08 § 8.1](08_radar_waveforms.md#81-용어-정리-및-오류-교정).

사용자는 템플릿 복사 후 필요 시 수정.

### 7.4.5a Dataset Variant — 물리 조건별 분리 수집

계획서 v0.11에서 MVP 물리 요소(함선 자세, 사이드로브, 자함 동요)가 추가됐다.
이들은 모두 **시나리오 로드 시점에 on/off 가능한 옵션**이다.

**문제 의식**: NN을 물리가 전부 켜진 데이터로만 학습하면, 성능이 안 좋을 때 원인 분리가
어렵다. 모델이 부족한지(bias), 데이터 다양성이 부족한지(variance), 특정 물리 현상에
약한지 구분 불가.

**해결**: 같은 태스크에 대해 **Variant를 여러 개** 만들어 **물리 조건을 점진적으로** 쌓는다.
이것이 **bias/variance 진단의 재료**가 되고, 필요시 curriculum 학습도 가능.

#### 표준 Pairing Variant 4종

```
Variant_A  (Ideal)            sea_state=0, attitude=off, sidelobe=off
Variant_B  (Attitude only)    sea_state=3, attitude=on,  sidelobe=off
Variant_C  (Sidelobe only)    sea_state=0, attitude=off, sidelobe=on
Variant_D  (Full realistic)   sea_state=3, attitude=on,  sidelobe=on
```

각 Variant는 **별개 Dataset 파일**로 저장:

```
workspace/datasets/
├── pairing_variant_A.h5         # 이상화
├── pairing_variant_B.h5         # 자세만
├── pairing_variant_C.h5         # 사이드로브만
├── pairing_variant_D.h5         # 전부 on
└── pairing_variants_manifest.toml   # Variant 메타·파라미터 기록
```

Manifest에는 각 Variant의 물리 옵션이 명시적으로 기록됨 — 나중에 "이 모델은 어떤 조건에서
학습됐는지" 추적 가능.

#### 학습·비교 워크플로

```
1. Pairing NN 초기 구조를 Variant_A로 학습 → baseline
2. 같은 구조로 Variant_D 학습 → 현실 조건 학습
3. Workbench에서 두 모델 Compare:
   - Variant_A 모델 on Variant_D test set:  얼마나 떨어지는가?
   - Variant_D 모델 on Variant_A test set:  overfit 여부
   - Variant_D 모델 on Variant_D test set:  최종 성능
4. 진단:
   - A → A 좋음, A → D 나쁨: 물리 일반화 실패 → Variant_D 데이터 추가 필요
   - A → A도 나쁨: 모델 용량 부족 → 구조 개선 필요
   - D → D 좋지만 D → A 나쁨: 이상 조건 잊어버림 → curriculum 고려
5. 필요시 **Curriculum 학습**: A에서 먼저 학습 → D로 fine-tune
```

Workbench Compare UI는 이미 v0.10의 Run Compare 구조를 공유하므로, 모델 × Variant
격자 형태 테스트 결과 테이블을 제공 가능 (세부 UI는 Wave 1 구현 시 결정).

#### v0.25~v0.29 확장 Variant 차원 (사실성 강화)

v0.11 시점의 3차원(sea_state/attitude/sidelobe) 외에 새로운 물리 차원이 도입됐다. 모두
SampleSpec에서 조건 가능:

| 차원 | 출처 | 옵션 |
|---|---|---|
| **antenna_type** | v0.25 | parabolic / planar_array (16×16) / planar_array (32×32) |
| **rx_channels** | v0.25 | single_sum / monopulse_4ch |
| **dynamics_realism** | v0.27 | trajectory_only (단순 보간, 디버그) / dynamics (동역학 적분, 표준) |
| **target_motion_kind** | v0.27 | aircraft / powered_flight / ballistic / surface_vessel / floating_static |
| **atmosphere** | v0.28 | clear / rain_light / rain_heavy / fog |
| **outside_environment** | v0.29 | open_sea / open_land / blocked |
| **target_scattering** | v0.34 | point (단일 scatterer, 디버그) / multi_scatterer (3~5, glint 자동 발생, 표준) |
| **multipath** | v0.34 | off (free-space) / two_ray (sea bounce, 해상 표준) |
| **tracker_kind** | v0.34 | ekf / ukf — Stone Soup 호환 비교 |
| **data_associator** | v0.34 | nn (nearest neighbor) / gnn (Hungarian, 다중 표적 표준) |
| **detector** | v0.34 | ca_cfar (균일 클러터) / os_cfar (multi-target·edge 클러터) |
| **refraction** | v0.34 | flat (단순) / earth_4_3 (장거리 정확도, 표준) |

원칙은 v0.11과 동일 — **점진적으로 켜며 bias/variance 진단**. 다만 5+ 차원이 되면
**모든 조합**(2^N) Variant는 비현실. **선택적 조합**으로:

```
Variant_A_ideal       모든 조건 OFF/clear, parabolic, single_sum, trajectory_only
Variant_B_realistic   sea_state=3, attitude=on, sidelobe=on, dynamics=on
                      monopulse_4ch (실제 추적 레이더 표준 가정)
Variant_C_rain        Variant_B + atmosphere=rain_heavy
Variant_D_planar      Variant_B + antenna=planar_array_16x16
Variant_E_far_target  Variant_B + outside_environment=open_sea
                      + 표적이 Map 밖 (장거리 추적 검증)
Variant_F_ballistic   Variant_B + motion_kind=ballistic (탄도 표적 학습)
```

각 Variant는 **단일 axis만 변형**해 영향 분리. Curriculum 학습 시:
A_ideal → B_realistic → C_rain → ... 순서 점진.

#### Sample 형식 — 모노펄스 채널 (v0.25)

`rx_channels = "monopulse_4ch"` Variant의 Sample은:

```toml
[sample.input]
include_iq_per_channel = true       # 4채널 IQ 모두 (Σ/Δaz/Δel/Δ²)
include_monopulse_error = true      # error_az_rad, error_el_rad (계산값)
include_sigma_only = false          # MVP는 4채널 다 포함

[sample.gt]
include_true_az_rad = true
include_true_el_rad = true
include_monopulse_error_gt = true   # 이상적 모노펄스 error (참값과 비교용)
```

4채널 IQ는 SampleSpec 크기 ~4배. Pairing NN은 보통 SUM만 쓰지만, **각도 추정 NN**에는
4채널 다 필요 (Δaz/Δel이 핵심 입력).

#### Sample 형식 — 동역학 GT (v0.27)

`dynamics_realism = "dynamics"` Variant는 GT가 동역학 적분 결과:

```toml
[sample.gt]
include_true_position = true        # 동역학 적분 결과의 (x,y,z)
include_true_velocity = true        # 적분된 속도 vector
include_true_attitude = true        # MVP는 velocity로부터 derived (6DOF는 MVP+α)
include_force_breakdown = false     # 외력 디버그용 (MVP+α)
```

vs `dynamics_realism = "trajectory_only"` Variant는 사용자 trajectory CSV 그대로 GT 사용.
**비교 가치**: 동역학 모델이 학습에 미치는 영향 분리 진단.

#### Sample 형식 — Atmosphere (v0.28)

`atmosphere = "rain_*"` Variant는 SNR 감소된 신호:

```toml
[sample.input]
include_atmosphere_meta = true      # rain_rate_mmh, visibility_km, ...
                                    # NN이 환경 인식하면서 학습 가능
[sample.gt]
include_attenuation_db = false      # 보통 학습 입력에 안 줌 (실제 운영 시 모름)
```

Atmosphere는 **데이터 다양성** 차원으로 사용. 학습 입력에 atmosphere meta를 줄지 말지는
NN 설계자의 선택 (input feature engineering).

#### Variant Manifest (v0.29 갱신)

```toml
# pairing_variants_manifest.toml

[[variant]]
name = "B_realistic"
sea_state = 3
ownship_attitude = "on"
sidelobe = "on"
antenna_type = "parabolic"
rx_channels = "monopulse_4ch"       # v0.25
dynamics_realism = "dynamics"        # v0.27
atmosphere = "clear"                 # v0.28
outside_environment = "open_sea"     # v0.29 (Map 밖 표적 가능)
sample_count = 50000

[[variant]]
name = "E_far_target"
# ... B_realistic 그대로 +
# 표적 trajectory가 Map 밖까지 가도록 별도 trajectory 사용
trajectory_extends_outside_map = true
sample_count = 30000
```

### 7.4.5b Pairing NN — 구체 SampleSpec 예시

네가 Q1에서 Pairing NN을 Wave 1 최우선으로 선택했고, Q3에서 Primary 정보는 불포함으로
결정했다. 다음은 그에 맞는 구체 템플릿 `pairing_spec.toml`:

```toml
# templates/pairing.toml
# FMCW Triangle Pairing NN을 위한 기본 SampleSpec

[meta]
task = "pairing"
description = "Up-sweep과 Down-sweep 피크를 매칭해 거리·속도 분리"
radar_model = "fmcw_triangle_v1"

# 한 샘플 = 한 프레임의 전체 up/down 피크 집합 + 정답 매칭
[sample]
per_frame = true                # 프레임당 1 샘플
# per_frame = false 이면 per_scenario = true (시퀀스 샘플)

[inputs]
# Probe에서 뽑는 입력
up_peaks = "probe:up_peaks"     # shape: (N_up, peak_feature_dim)
down_peaks = "probe:down_peaks" # shape: (N_down, peak_feature_dim)
# peak_feature_dim: [range_bin, velocity_bin, snr_db, phase_ch0..3, az, el]

[labels]
# 시뮬이 알고 있는 정답: 어떤 up이 어떤 down과 같은 표적인지
# Primary 정보는 포함 안 함 — 모든 표적에 대한 매칭을 학습
gt_matching = "gt:pairing_matrix"  # shape: (N_up, N_down), 0/1 binary matrix

[filter]
# Variant별로 다르게 수집하기 위한 필터
# 이 조건을 만족하는 시나리오만 수집에 포함
sea_state_max = 3                  # 0~3 허용
require_multiple_targets = true    # Secondary 있는 시나리오만 (오염 학습용)
min_in_beam_frames = 100           # Primary가 빔 안에 있는 프레임이 최소 100개

[physics_options]
# 이 Variant의 물리 옵션 토글 (Variant 식별용)
ship_attitude_enabled = true       # false면 roll/pitch=0으로 강제
sidelobe_enabled = true            # false면 main beam만 사용
platform_dynamics_enabled = true   # false면 자함 고정

[variant]
# 이 설정이 어느 Variant에 해당하는지 명시적 태그
name = "D_full_realistic"
description = "모든 물리 옵션 활성, 현실 조건"
```

#### GT 라벨 생성 (`gt:pairing_matrix`) 방식

시뮬이 표적 위치와 속도를 알고 있으므로 **어떤 up-peak가 어떤 down-peak과 같은 표적인지**를
결정론적으로 계산 가능:

```python
# Evaluator 내부 로직 (사용자는 볼 필요 없음)

def build_pairing_matrix(up_peaks, down_peaks, gt_targets, tol_range=10.0):
    """각 표적마다 그 표적이 생성한 up-peak와 down-peak를 찾아서 1로 마킹."""
    matrix = np.zeros((len(up_peaks), len(down_peaks)), dtype=np.uint8)
    for target in gt_targets:
        # 표적의 실제 range/velocity로 up 피크와 down 피크가 어느 bin에 나타날지 예측
        predicted_up_bin, predicted_down_bin = forward_model(target, waveform)

        # 가장 가까운 피크 찾기
        up_idx = find_nearest(up_peaks, predicted_up_bin, tol=tol_range)
        dn_idx = find_nearest(down_peaks, predicted_down_bin, tol=tol_range)

        if up_idx is not None and dn_idx is not None:
            matrix[up_idx, dn_idx] = 1
    return matrix
```

이 정답 생성은 **Evaluator 책임** (03 § 3.3.4의 GT 체계 일부). Pipeline Plugin은 접근 불가.

#### 이 SampleSpec의 특징 정리

- **Primary 정보 없음**: 네 Q3 답변에 따라 Pairing NN은 모든 표적 동등 처리
- **N_up, N_down이 프레임마다 다름**: 가변 길이 입출력 → set matching NN 아키텍처 필요
  (Transformer, Set Transformer, Deep Set 등)
- **`require_multiple_targets`**: Secondary가 없으면 오염이 없으므로 학습 가치 낮음
- **Variant 태그**: Manifest에 기록되어 모델과 함께 추적

### 7.4.6 단계적 학습 전략 (Pipeline 경유 원칙의 실전 적용)

원칙 3(Pipeline 경유)과 원칙 6(부분 교체) 하에, 실제로 NN을 학습·투입하는 시나리오는
복잡도에 따라 케이스 0~D로 나뉜다. **케이스 0이 가장 흔하고 MVP+α의 기본 워크플로우**이며,
A~D는 이의 확장이다.

#### 케이스 0: 단일 스테이지 교체 (기본 워크플로우) ⭐

**원칙 6의 기본 패턴.** Pipeline의 **한 스테이지만** NN으로 교체, 나머지는 전부 기본 구현.
이게 "가장 먼저 해보는" 실험이며, Workbench가 **가장 매끈하게 지원해야 할 경로**.

##### Pairing NN을 예로 끝까지 따라가기

이 문서에서 NN 통합의 **모든 예시를 Pairing NN으로 통일**한다. 사용자가 가장 먼저 시도할
시나리오로 가정. (각도 추정, 분류 등 다른 스테이지도 동일한 절차, 입출력 타입만 다름.)

> **맥락**: 본 프로젝트의 타겟 레이더는 **FMCW Triangle 단독**이므로 Pairing은
> "Up-sweep 피크와 Down-sweep 피크의 매칭" 하나로 정의된다.
> 참고: [08 § 8.3](08_radar_waveforms.md#83-fmcw-triangle-radar-상세).
>
> 특히 실제 DSP 펌웨어 코드(`pairing/target_pairing.c`)는 **현재 비어 있는 상태**이다.
> 즉 Pairing 알고리즘 자체가 개발 대상이며, Workbench에서 여러 접근을 실험한 뒤
> 최종안을 C로 포팅하는 **실제 진행 중인 작업**이다. 가상 시나리오가 아님.

**1단계: 기본 Pipeline으로 Dataset 수집**

```
Pipeline 구성 (전부 기본 구현):
  Transmitter     : default_transmitter
  Receiver        : default_receiver
  AngleEstimator  : default_angle_estimator
  Detector        : default_detector
  Pairing         : default_pairing          ← 학습 대상 자리 (기본으로 돌림)
  Tracker         : default_tracker

→ 여러 시나리오 × 여러 seed로 Run 배치 실행
→ 각 Run에서 Probe 수집:
    - up_peaks       (Pairing 입력)
    - down_peaks     (Pairing 입력)
    - GT 라벨        (참 pairing assignment, 시뮬이 알고 있음)

→ pairing_dataset.h5 누적
```

**2단계: Dataset으로 NN 학습**

```
training_job.toml:
  task       = "pairing"
  dataset    = "pairing_dataset.h5"
  model      = ...
  framework  = "tensorflow"  (또는 numpy-only)
  output     = "plugins/my_pairing/weights/v1.npz"

→ workbench-train 또는 내부 Trainer
→ weights/v1.npz 생성
```

**3단계: Pipeline에 꽂고 추론**

```
Pipeline 구성:
  Transmitter     : default_transmitter      ← 변경 없음
  Receiver        : default_receiver         ← 변경 없음
  AngleEstimator  : default_angle_estimator  ← 변경 없음
  Detector        : default_detector         ← 변경 없음
  Pairing         : my_pairing_nn@v1.0      ← 🆕 NN으로 교체
  Tracker         : default_tracker          ← 변경 없음

→ Run 실행, 기존 방식과 메트릭 비교
```

**4단계: 반복 개선**

- 학습 재실행으로 v2, v3 가중치 생성
- 각 버전을 같은 시나리오에 돌려 메트릭 비교
- Pipeline 나머지는 **영원히 건드리지 않음**

##### 왜 케이스 0이 기본인가

- **의존 관계 없음**: NN이 뱉는 출력 형식이 기본 구현과 같으니 하류 영향 없음
- **비교가 깔끔**: "Pairing만 바꿨을 때 전체 성능이 어떻게 변하는지" 깨끗하게 볼 수 있음
- **재현성 쉬움**: 기본 구현은 고정된 코드라 Dataset 재구축 필요 없음
- **디버깅 쉬움**: 문제가 생기면 Pairing만 의심하면 됨

#### 케이스 A: 단일 스테이지 교체, 입출력 동일 (0의 일반화)

케이스 0과 사실상 동일하되, Pairing 외 다른 스테이지일 때:

- CFAR Detector → NN Detector
- 기본 각도 추정 → NN 각도 추정
- EKF Tracker → RNN Tracker (입출력 형식만 맞추면)

워크플로우는 케이스 0과 같음. **MVP+α 범위.**

#### 케이스 B: 하류 영향형 NN (Downstream-dependent)

학습 대상 NN이 **상류 스테이지의 출력**에 의존하는데,
그 상류의 결정이 결과 분포를 크게 좌우.

**예시**: Classifier가 Tracker 출력(Track)에 의존 →
        어느 Tracker를 쓰느냐에 따라 Track 특성이 달라 Classifier 학습 분포가 변함

**전략**:
1. 실제 추론 시 쓸 Tracker를 **먼저 확정**
2. 그 Tracker를 포함한 Pipeline으로 Dataset 수집
3. 수집된 Track 특성 위에서 Classifier 학습

**주의**: Tracker가 나중에 바뀌면 Classifier를 **재학습**해야 함.
이 의존성을 Dataset manifest에 명시.

```toml
# dataset_manifest.toml
[dependencies]
upstream_stages = ["tracker:default_tracker@v1.2.0"]
# 이 상류가 바뀌면 Dataset 무효
```

#### 케이스 C: 상류 영향형 NN (Upstream-modifying)

학습 대상 NN이 **상류에 위치**해 하류의 출력을 바꿈.

**예시**: NN Denoiser가 Receiver 이후 스펙트럼을 정화 →
        Detector가 정화된 스펙트럼을 봐야 하는데, 학습 시점에는 Denoiser가 아직 없음

**전략** — 단계적 학습 (Stage-wise):
1. 1단계: Denoiser 학습 (깨끗한 스펙트럼이 GT 라벨, 잡음 섞인 스펙트럼이 입력)
   → 이건 케이스 A의 특수 형태
2. 2단계: Denoiser를 Pipeline에 꽂고 고정 → Detector용 Dataset 수집
3. 3단계: Detector 학습

**원칙**: 상류를 먼저 학습·고정 후 하류로 진행.
각 단계마다 **"어느 상류를 고정했는지"** 명시.

#### 케이스 D: End-to-End

여러 스테이지를 **통째로 학습**. Pipeline 전체가 미분 가능해야 함.

**예시**: ADC 샘플 → Track 출력 한 번에

**전략**:
- **MVP 범위 밖** (Wave 3)
- Pipeline 구성 요소들이 TensorFlow/PyTorch 그래프로 표현 가능해야
- `physics/fmcw.py`, Default_RX 등을 미분 가능한 대체 구현으로 갈아끼우는 "미분 Pipeline 모드" 필요
- 이건 Workbench 설계 자체를 꽤 흔들어서, **별도 축으로 나중에 다시 기획**

#### 단계적 학습 UI 지원 (MVP+α)

Dataset Builder UI에 "어떤 Pipeline으로 뽑을지" 명시:

```
┌─ Dataset Builder ────────────────────────────┐
│ Target Task: Angle Estimator Training        │
│                                              │
│ Pipeline Config:                             │
│   Transmitter    : default_transmitter      │
│   Receiver       : default_receiver         │
│   AngleEstimator : ─ (빌드 대상이므로 생략) │
│   Detector       : default_detector         │
│   Pairing        : default_pairing          │
│   Tracker        : default_tracker          │
│                                              │
│ → Dataset이 이 Pipeline 구성에 종속됨         │
│ → manifest에 기록, 상류 변경 시 재구축 필요   │
│                                              │
│ [Cancel] [Start Build]                       │
└──────────────────────────────────────────────┘
```

Dataset을 만든 Pipeline 구성을 **manifest에 기록**,
나중에 상류가 바뀌면 Workbench가 경고:

> ⚠ 이 Dataset은 `tracker:default_tracker@v1.2.0` 기반인데,
> 현재 활성 Tracker는 `my_rnn_tracker@v0.3` 입니다.
> Classifier가 기대하는 Track 특성과 다를 수 있어 재학습을 권장합니다.

---

## 7.5 학습 실행 (Training Workflow)

### 7.5.1 하이브리드 구조

**원칙**: 학습 실행 위치는 열어두고, **Config 스키마와 가중치 포맷**만 공유.

```
training_job.toml   ← 공통 스키마
     ↓
┌─────────────────┐       ┌──────────────────┐
│ Workbench 내부  │  or   │  외부 (CLI)      │
│ TrainerService  │       │  workbench-train │
└─────────────────┘       └──────────────────┘
         │                         │
         └──────────┬──────────────┘
                    ▼
         weights.npz  (동일 포맷)
                    ▼
         Plugin이 load_weights()로 로드
```

### 7.5.2 training_job.toml 스키마

```toml
[job]
job_id = "angle_estimator_v2"
task = "angle_estimation"  # Wave 1 템플릿

[dataset]
path = "~/datasets/angle_v2.h5"
splits = { train = 0.8, val = 0.1, test = 0.1 }

[model]
architecture = "mlp"
layers = [4, 64, 64, 2]
activation = "relu"

[training]
framework = "tensorflow"   # or "pytorch" / "numpy_only"
optimizer = "adam"
learning_rate = 1e-3
batch_size = 32
epochs = 100
early_stopping_patience = 10

[output]
weights_path = "plugins/my_angle/weights/v2.npz"
metrics_path = "plugins/my_angle/training_log.json"
tensorboard_dir = "tb/angle_v2"  # optional
```

### 7.5.3 내부 TrainerService (간단 학습용)

```python
class TrainerService:
    """작은 모델, 짧은 학습을 위한 내부 러너."""

    def run(self, config: TrainingJob) -> TrainingResult:
        # EventBus로 진행도 emit
        for epoch in range(config.training.epochs):
            for batch in dataloader:
                loss = train_step(batch)
                event_bus.emit("training.batch_complete", epoch, loss)
            event_bus.emit("training.epoch_complete", epoch, val_loss)
        save_weights(config.output.weights_path)
```

UI에는 Training Panel:
```
┌─ Training ────────────────────────────┐
│ Job: angle_estimator_v2               │
│ Epoch: 37 / 100   [████████░░] 37%    │
│ Train Loss: 0.012    Val Loss: 0.015  │
│ Best Val: 0.014 @ epoch 33            │
│ [Pause] [Stop & Save]                 │
│                                       │
│ [Loss Curve]                          │
│  ▁▁▂▃▄▅▅▆▇▇▇▇▇▇                      │
└───────────────────────────────────────┘
```

### 7.5.4 외부 학습 (`workbench-train` CLI)

```bash
workbench-train --config training_job.toml --gpu 0
```

같은 Config 스키마, 같은 출력 포맷.
외부 GPU 서버에서 돌리기에 적합.
Workbench는 **파일 감지**로 완료를 알고 자동으로 Plugin 가중치 갱신.

### 7.5.5 TF → numpy 이식 파이프라인 (네 답변의 특별 요구)

네가 "TF로 초기 검증 후 로우레벨 Python으로 대체"한다고 했으니,
이 전환을 **자동화**하는 도구 제공:

```
1. TF/Keras 모델 학습 → model.h5 (TF 포맷)

2. workbench-convert --from tf --to numpy \
      --model model.h5 --output weights.npz

3. weights.npz가 Plugin의 load_weights()로 로드되는 "레이어 사전":
   {
     "w1": array(shape=(4, 64)),
     "b1": array(shape=(64,)),
     "w2": array(shape=(64, 64)),
     ...
   }

4. Plugin은 순수 numpy forward pass:

   def forward(x, weights):
       h = relu(x @ weights["w1"] + weights["b1"])
       h = relu(h @ weights["w2"] + weights["b2"])
       return h @ weights["w3"] + weights["b3"]

5. 검증: TF 모델과 numpy 구현의 출력이 임계값 이내 일치
   → workbench-verify-port --tf model.h5 --numpy plugin.py
      → "Match (max abs diff: 3.2e-7)"
```

이 **이식 검증 테스트**가 6.3의 테스팅 전략에 새 카테고리로 들어감:
"TF ↔ numpy 동치성 검증".

---

## 7.6 NN 평가 (Step 2)

**NN 개발 모드의 두 번째 Step**. 학습된 NN Plugin(`<nn_file_name>.py` + weights)을 받아
**4-error 진단**으로 bias/variance/data mismatch를 분리 분석한다.

### 7.6.0 Step 2의 핵심 개념 — 4-error 진단

ML에서 모델 성능이 떨어지는 원인을 분리하기 위한 표준 도구.

```
Bayes error ─── avoidable bias ───→ Training ─── variance ───→ Dev ─── data mismatch ───→ Test

  이론 하한         "모델 용량 부족"       학습셋         "과적합"        검증셋      "학습 분포 ≠ 실전"   미지 시나리오
  (선택적)                                                                                        (최종 평가)
```

#### Error 4종의 의미

| Error | 측정 방식 | 큰 값이 의미하는 것 |
|---|---|---|
| **Bayes** | 이론 하한 근사 (선택적) | 문제 자체가 어렵다 |
| **Training** | 학습셋에서의 평균 loss | 모델 용량 부족 or 학습 부족 |
| **Dev** | 검증셋(holdout)에서의 평균 loss | Variance (과적합) |
| **Test** | 학습 때 보지 못한 시나리오 | Data mismatch (학습 분포 ≠ 실전) |

#### Gap 해석 (자동 진단)

- `Training − Bayes` = **avoidable bias**. 모델을 키우거나 더 오래 학습해야 함
- `Dev − Training` = **variance**. Regularization 강화·Dev set 늘리기·early stopping
- `Test − Dev` = **data mismatch**. Test 시나리오 분포에 더 가까운 학습 데이터 필요

Workbench가 이 gap들을 자동 계산해 `diagnosis_hint`로 출력 (03 § 3.5.1a의 `NNEvalResult`).

#### Bayes Error는 선택적

Bayes error는 일반적으로 **미지수**. 본 Workbench에서는 **3가지 추정 방법** 중 사용자 선택:

1. **Variant A (Ideal) 성능** — v0.12의 이상화 Variant 성능이 Bayes 근사 (기본 추천)
2. **사람 수동 라벨링 일치율** — 인간이 직접 라벨링한 결과와 NN 결과 비교
3. **사용자 제공 수치** — 문헌이나 이론 분석으로 미리 알려진 값

Bayes를 쓰지 않으면 Training/Dev/Test 3개 error만 계산, `avoidable_bias=None`.

#### v0.25~v0.29 변경의 4-error 영향 (NN 보강 — v0.30 정합)

v0.25~v0.29의 사실성 강화는 **각 error의 의미를 더 의미 있게** 만든다:

**v0.25 Monopulse 4ch**:
- `EKF Command Error` 의 입력이 명시적 `error_az_rad / error_el_rad` (Σ에서 계산)
- 이전엔 단순 빔 중심 기반 각도 — 이제 추적 레이더 표준 모노펄스 신호
- **결과**: 4-error 측정의 **각도 추정 부분이 표준 모노펄스 모델과 일치**, 실제 시스템 비교 가능

**v0.27 Dynamics**:
- GT가 trajectory CSV가 아닌 **동역학 적분 결과**
- 표적이 실제처럼 거동 → NN이 비현실 trajectory에 과적합되지 않음
- **결과**: Test error의 **data mismatch 진단이 더 신뢰**됨 (학습-실전 분포 차이가 의미 있음)

**v0.28 Atmosphere**:
- Variant 차원에 `atmosphere` 추가 → 환경 다양성 명확
- 학습은 clear, Test는 rain_heavy 같은 **명시적 도메인 시프트** 시나리오
- **결과**: data mismatch 진단을 **명시적 환경 변수**로 분리. "이 NN은 폭우에 약함" 같은 결론

**v0.29 Simulation Domain**:
- `outside_environment` 차원 → 표적이 Map 밖에 있는 시나리오 학습 가능
- Map 안 학습 → Map 밖 Test = **거리·시야 도메인 시프트** 진단 가능
- **결과**: 추적 레이더가 **운영 거리 전 영역**에서 검증됨

**v0.34 Multi-scatterer + Glint** (16 § 16.3.2, 14 § 14.10):
- 표적이 점이 아닌 3~5 reflector → monopulse glint 자동 발생
- 학습 입력의 angle measurement에 glint noise 포함
- **결과**: NN이 **glint robust 추적 능력** 학습. 4-error 의 angle 정확도가 실제 추적 안정성과 직결

**v0.34 Two-ray multipath** (16 § 16.3.1):
- 해상 시나리오의 sea bounce → SNR lobing 패턴
- 표적 거리·고도에 따라 신호 강·약 변동
- **결과**: data mismatch 진단을 **multipath 환경 차원**으로 분리. "이 NN은 multipath null에서 약함" 같은 결론

**v0.34 EKF/UKF 선택 + GNN** (16 § 16.3.3, 16 § 16.3.4):
- Tracker NN 대비 baseline이 EKF·UKF 두 가지
- 다중 표적 환경의 GNN data association → NN이 단일 추적에 집중
- **결과**: Tracker NN의 비교 baseline이 명확 (Stone Soup 호환). 4-error 의 Test가 EKF/UKF/NN 셋의 격자 비교

종합: 4-error 진단 자체 알고리즘은 v0.13에서 결정 그대로지만, **각 error가 의미하는 물리적
조건이 명확**해져 실제 운영 환경 예측력 ↑.

### 7.6.1 Step 2 실행 절차

```
1. NN 모드 진입 (View > NN Development Mode)
2. "Step 2: NN Evaluation" 선택
3. 평가 대상 NN 선택:
   - <nn_file_name>.py (Plugin 파일)
   - weights/vX.npz (학습된 가중치)
4. Dataset 지정:
   - Training: 학습에 썼던 dataset (필수)
   - Dev: 검증셋 (필수)
   - Test: 미지 시나리오 (필수)
   - Variants: A/B/C/D 격자 (선택)
5. Bayes 추정 옵션:
   - "Skip" (기본, 3-error 모드)
   - "Variant A 기반"
   - "수동 입력" (고급)
6. Run Evaluation → NNEvalResult 생성
7. 결과 UI 표시:
   - 4개 숫자 (or 3개)
   - Gap 3개와 진단 힌트
   - Variant 격자 (있으면 표로)
```

### 7.6.2 NN 평가 전용 패널 (UI)

NN 모드 Step 2 화면의 전용 패널. DSP 모드에서는 안 보임.

```
┌─ NN Evaluation — my_pairing_nn@v1.2 ─────────────────────────────┐
│ Plugin: plugins/my_pairing_nn/plugin.py                          │
│ Weights: weights/v1.2.npz (1.4 MB, trained 2026-04-23)           │
├──────────────────────────────────────────────────────────────────┤
│ ── Errors ──                                                     │
│   Bayes       0.015   (from Variant_A)                           │
│   Training    0.042   ─── avoidable bias: +0.027 ⚠               │
│   Dev         0.068   ─── variance:       +0.026 ⚠               │
│   Test        0.089   ─── data mismatch:  +0.021                 │
│                                                                  │
│ ── Diagnosis ──                                                  │
│   ⚠ Avoidable bias 큼: 모델 용량·학습 에포크 재검토               │
│   ⚠ Variance도 큼: regularization 또는 dev set 확대               │
│   ◦ Data mismatch는 허용 범위                                     │
│                                                                  │
│ ── Variant Grid ──                                               │
│            │  A_ideal  B_attitude  C_sidelobe  D_full            │
│   Train on A │  0.042    0.071       0.088      0.112            │
│   Train on D │  0.058    0.049       0.052      0.055            │
│                                                                  │
│   해석: D-train 모델이 모든 Variant에서 균형 좋음 (일반화 성공)    │
└──────────────────────────────────────────────────────────────────┘
```

### 7.6.3 DSP 모드에서의 메트릭 (기존 내용)

아래 내용은 Step 2와는 **별개**. NN이 학습 완료 후 DSP 모드 Pipeline에 꽂혀 Run될 때
보조로 따라오는 NN 내부 메트릭.

기존 Task 메트릭(Primary 추적 연속성·ID Switch·Positioner Lag 등, [03 § 3.5.2](03_data_model.md#352-메트릭-목록-mvp))에
**NN 전용 메트릭**이 함께 나옴:

- **Task 메트릭** — "이 NN이 최종 목표(선택 표적 추적)에 얼마나 기여했나"
- **Model 메트릭** — "NN 자체는 얼마나 잘 작동하나 (loss, accuracy 등)"

둘 다 보여야, "NN loss는 좋은데 실제 추적은 오히려 나빠진" 같은 상황을 잡아낼 수 있음.

### 7.6.4 메트릭 분리 (DSP 모드 Run에 같이 담김)

```python
@dataclass(frozen=True)
class Metrics:
    task: TaskMetrics               # 03의 Metrics (Primary/Secondary/Overall/System)
    model: ModelMetrics | None      # NN Plugin 있을 때만

@dataclass(frozen=True)
class ModelMetrics:
    # 분류 전용
    accuracy: float | None
    confusion_matrix: np.ndarray | None
    top_k_accuracy: dict[int, float] | None

    # 회귀 전용
    mse: float | None
    mae: float | None

    # 시퀀스 전용 (RNN tracker)
    sequence_accuracy: float | None
    teacher_forcing_loss: float | None

    # 공통
    inference_time_ms: float
    model_size_mb: float
    peak_activation_magnitude: float  # NaN/Inf 방지 확인
```

### 7.6.5 Result Panel UI (DSP 모드 Run 결과)

```
┌─ Run Result ─────────────────────────────────────────┐
│ Tab: [Task Metrics] [Model Metrics] [Probes]         │
│                                                      │
│ [Task Metrics 탭]                                    │
│   🎯 Primary Target #1                               │
│     Track Continuity: 0.94                           │
│     ID Switches:      0                              │
│     Range RMSE:       3.2 m                          │
│     Positioner Lag:   avg 0.4°, max 1.8°             │
│                                                      │
│   Secondary Targets                                  │
│     Target #2: continuity 0.88                       │
│                                                      │
│   Overall:  Pd 0.89  Pfa 0.018 (보조 지표)           │
│                                                      │
│ [Model Metrics 탭]                                   │
│   Pairing NN Accuracy: 0.91 (학습 validation)        │
│   Inference: 2.3 ms/frame                            │
│   Model Size: 1.4 MB                                 │
└──────────────────────────────────────────────────────┘
```

Pairing NN은 분류 모델이 아니라 매칭 모델이라 `accuracy` 대신 `pair_match_rate` 같은
Pairing-specific 지표가 적절하지만, Model Metrics 구조가 유연하므로 Plugin이 자기 메트릭을
노출 가능 (디테일은 Wave 1 구현 시 확정).

### 7.6.6 Internal Visualization (Wave 1 후)

Probe 패널이 Internal Probe를 인식하면:

- **Activation 히트맵** — 레이어별 활성화 분포
- **Feature Map** — Conv 모델이면 공간 맵
- **Attention Weights** — Transformer면 어텐션 시각화
- **Gradient Flow** (학습 중) — 각 레이어 gradient norm

각각은 **작은 전용 위젯**으로 구현. 모델 종류마다 적용 가능한 것만 나타남.

### 7.6.7 Run Manifest — 어떤 스테이지가 NN인가 명시

원칙 6(부분 교체)을 실제 저장소 레벨에서 지원하려면, 각 Run이 **어느 Slot이 NN이고 어느 것이 기본 구현인지**를 명시해야 한다. 이래야:

- Run 목록에서 한눈에 "Pairing만 NN인 Run"을 필터링 가능
- 여러 Run 비교 시 "무엇이 바뀐 Run끼리 비교했는지" 명확
- 재현 시 **정확히 같은 구성**으로 다시 돌릴 수 있음

#### 저장 스키마 (RunResult 확장)

`03_data_model.md § 3.5`의 `RunResult`에 `pipeline_manifest` 필드 추가:

```json
{
  "run_id": "run_0042",
  "started_at": "2026-04-22T15:30:01",
  "scenario": "B_Conflict",
  "primary_target_id": 1,
  "pipeline_manifest": {
    "transmitter":     {"plugin": "default_transmitter@1.0", "is_nn": false},
    "receiver":        {"plugin": "default_receiver@1.0",    "is_nn": false},
    "angle_estimator": {"plugin": "default_angle@1.0",       "is_nn": false},
    "detector":        {"plugin": "default_detector@1.0",    "is_nn": false},
    "pairing":         {"plugin": "my_pairing_nn@1.2",       "is_nn": true,
                        "weights_hash": "sha256:abc...",
                        "training_dataset": "pairing_ds@2026-04-20"},
    "tracker":         {"plugin": "default_tracker@1.0",     "is_nn": false},
    "target_gate":     {"plugin": "default_gate@1.0",        "is_nn": false,
                        "enabled": true},
    "classifier":      null
  },
  "metrics": { ... }
}
```

#### Run 목록 UI에 표시

```
┌─ Run Panel ────────────────────────────────────────────────────────────┐
│ ID         Scenario    Primary  NN Slots        Continuity  IDSw  Lag  │
│ ─────────  ──────────  ───────  ──────────────  ──────────  ────  ──── │
│ run_0042   B_Conflict  #1       [pairing]          0.94      0    0.4° │
│ run_0041   B_Conflict  #1       —                  0.87      2    0.6° │
│ run_0040   C_Limit     #1       [pairing]          0.91      1    0.9° │
│ run_0039   C_Limit     #1       [pairing,tracker]  0.95      0    0.7° │
└────────────────────────────────────────────────────────────────────────┘
```

컬럼: `Primary`(선택 표적 id), `NN Slots`(활성 NN slot. "—"는 완전 기본 Pipeline),
`Continuity`, `IDSw`(ID Switch 횟수), `Lag`(Positioner Lag 평균).

#### 비교 UI도 같은 정보 활용

두 Run을 선택하면 Pipeline Manifest diff를 먼저 보여주고 메트릭 비교:

```
┌─ Run Compare (0042 vs 0041) ───────────────────────────────┐
│ Pipeline Diff:                                             │
│   pairing:  my_pairing_nn@1.2  vs  default_pairing         │
│   (rest: 동일)                                              │
│                                                            │
│ Primary Target Delta:                                      │
│   Track Continuity: +0.07  (0.94 vs 0.87)                 │
│   ID Switches:      −2     (0 vs 2)                       │
│   Positioner Lag:   −0.2°  (0.4° vs 0.6°)                 │
│                                                            │
│ Overall (보조):                                             │
│   Pd:  +0.04  (0.89 vs 0.85)                              │
└────────────────────────────────────────────────────────────┘
```

→ 사용자는 "Pairing을 NN으로 바꿨더니 **선택 표적 추적 연속성이 0.87→0.94로 향상,
ID Switch도 사라짐**"을 즉시 파악. Pd 0.04 향상은 부수 효과로 읽힘 (Pd 자체가 목표였던 게 아님).

---

## 7.7 MVP 범위 (NN 측면)

### 원칙 재확인

- **"Workbench 기본 상태는 NN 없는 Pipeline"** (원칙 6)
- Wave 1의 목표는 **"한 스테이지만 NN으로 교체하는 것이 완벽히 지원되는 상태"**
- 둘 이상의 NN 동시 사용은 구조적으로 가능하지만 **"기본 추천 워크플로우"는 아님**

### Wave 1 (MVP + α) — "한 NN 교체" 완성

MVP 기본 완료 후 **바로** 붙이는 범위.
**핵심 가치**: 사용자가 원하는 **한 스테이지만** NN으로 실험할 수 있다.

#### 인프라 (모든 단일-NN 교체가 공통으로 쓰는 것)

- ✅ StageSlot 시스템 (원칙 6 지원의 기반)
- ✅ AngleEstimator 스테이지 분리
- ✅ Classifier 스테이지 신규 (옵셔널)
- ✅ NNPluginMixin 정의
- ✅ Manual Export (CSV/HDF5)
- ✅ Automatic Dataset Builder (Pipeline Run 경유, **기본 구현 Pipeline**이 기본 설정)
- ✅ Dataset Manifest에 사용된 Pipeline 구성 기록 + 상류 변경 감지 경고
- ✅ training_job.toml 스키마
- ✅ `workbench-train` CLI
- ✅ TF → numpy 이식 도구 (`workbench-convert`, `workbench-verify-port`)
- ✅ TaskMetrics + ModelMetrics 분리
- ✅ Training Panel (간단)
- ✅ 이식 검증 테스트 (TF ↔ numpy 동치성)

#### 사전 검증되는 "단일 NN 교체" 시나리오

Wave 1에서 **공식 지원·템플릿 제공**할 단일 NN 교체 패턴:

| # | 시나리오 | 우선순위 | 케이스 | 비고 |
|---|---|---|---|---|
| 1 | **Pairing만 NN** | 🎯 1순위 | 0 | 사용자 주 관심사, End-to-End 문서 예시로 사용 |
| 2 | Detector만 NN (CFAR 대체) | 2 | A | 입출력이 Pairing과 유사, 재활용 쉬움 |
| 3 | 각도 추정만 NN | 3 | A | AngleEstimator 슬롯 분리의 직접 수혜 |
| 4 | Classifier만 (신규 추가) | 4 | 0 | Pipeline 뒤에 붙이기만 |
| 5 | Tracker만 NN | 5 | A | 상태 보존(RNN) 때문에 난이도 조금 높음 |

각 시나리오에 대해 Workbench가 제공:
- SampleSpec 템플릿 (`templates/<task>.toml`)
- 학습 Config 예시
- "기본 구현으로 Run → Dataset → 학습 → 교체 → 비교" 전체 매뉴얼

#### Wave 1 완료 기준 (갱신)

사용자가 **Pairing NN 교체 시나리오**를 끝까지 성공시킬 수 있으면 Wave 1 완료:

```
1. Workbench 실행, 시나리오 B_Conflict 로드
2. Plugin Manager에서 "Dataset Builder" 열기
3. "Pairing 학습 데이터 수집" 프리셋 선택
   → 나머지 스테이지는 전부 기본 구현 확인
4. 여러 시나리오 × 시드 조합으로 Dataset 수집 (자동 실행)
5. 외부 또는 내부 Trainer로 학습 → weights/v1.npz 생성
6. Plugin Manager에서 "my_pairing_nn" 등록
7. Pairing slot에 my_pairing_nn 활성화
8. 같은 시나리오 Run 실행
9. Run 결과 비교 UI에서 "기본 Pairing Run" vs "NN Pairing Run" 메트릭 대비
10. 재현: 어느 시점에 돌려도 동일한 가중치가 동일한 메트릭을 낸다
```

### Wave 2 (MVP + 6개월 목표)

- **여러 NN 동시 사용** 시 매니페스트·경고 시스템의 성숙
- Pairing NN의 set matching 특화 지원 (가변 길이 입출력 패턴)
- Internal Probe 시각화 (Activation, Feature Map)
- Model 비교 패널 (같은 데이터셋, 다른 NN 모델 metric 비교)

### Wave 3 (연구 축)

- RNN/Transformer Tracker Plugin (stateful)
- End-to-End 모델 지원 (ADC → Track 연속)
- 분산 학습 (외부 GPU 서버 플릿)

### Out of Scope

- AutoML, 하이퍼파라미터 탐색 도구
- 모델 압축/양자화
- 서빙(serving) 인프라 (ONNX Runtime, TensorRT 배포)

---

## 7.8 기존 계획서에 미치는 영향

| 문서 | 변경 내용 |
|---|---|
| [01 Vision](01_vision_scope.md) | MVP 범위에 "Wave 1 NN" 추가 여부 재확인 |
| [02 Architecture](02_architecture.md) | 블록도에 TrainerService, DataExporter 추가 |
| [03 Data Model](03_data_model.md) | StageSlot, NNPluginMixin, Dataset 스키마 추가 |
| [04 Migration](04_migration.md) | Phase 6(NN) 추가: MVP 완료 후 |
| [05 UI/UX](05_ui_ux.md) | Training Panel, Dataset Builder, Internal Probe 시각화 추가 |
| [06 Topics](06_topics.md) | 테스팅 전략에 "TF↔numpy 동치성" 카테고리 추가 |
| [Appendix A](appendix_A_code_audit.md) | `model/radar/receiver.py` 판정 조정 (각도 추정 분리) |
| [Appendix B](appendix_B_glossary.md) | 새 용어 추가: StageSlot, NN Plugin, SampleSpec, Internal Probe 등 |
| [08 Antenna](08_radar_waveforms.md) | **v0.25 모노펄스 4ch — Sample 형식 4채널 IQ + monopulse error 포함** |
| [12 Motion](12_placement_and_motion.md) | **v0.21 base/current — Dataset GT는 Sim Running 시점의 current_pose** |
| [14 Dynamics](14_dynamics_model.md) | **v0.27 동역학 — GT 정확도 ↑, dynamics_realism Variant 차원** |
| [15 Atmosphere](15_atmosphere_model.md) | **v0.28 대기 — atmosphere Variant 차원, SNR 영향 명시** |
| [11 § 11.11 Domain](11_coordinate_systems.md) | **v0.29 outside_environment — 학습 분포 Map 안/밖 시프트 평가** |
| [14 § 14.10 Multi-scatterer](14_dynamics_model.md) | **v0.34 — Sample 입력에 glint noise 자동 포함, target_scattering Variant 차원** |
| [08 § 8.5b Multipath](08_radar_waveforms.md) | **v0.34 — multipath Variant 차원, lobing pattern 분포 시프트** |
| [16 § 16.3.3 Tracker](16_baseline_audit.md) | **v0.34 — tracker_kind/data_associator Variant 차원, EKF/UKF/NN 비교** |
| [17 SDK Layer](17_open_platform.md) | **v0.35 — NN Plugin도 SDK Public Protocol, .trsim-pkg 패키징 가능** |

---

## 7.9 미결정 사항 (NN 특화 TBD)

| # | 항목 | 영향 | 결정 시점 |
|---|---|---|---|
| N1 | 학습 실행 위치 (내부/외부/하이브리드 세부) | 중 | Wave 1 진입 시 |
| N2 | GPU 지원 정책 (CPU 전용? CUDA?) | 중 | Wave 1 진입 시 |
| N3 | TF 버전 고정 (2.x? 3.x?) | 저 | 첫 템플릿 작성 시 |
| N4 | 가중치 포맷 (npz 단일? HDF5 혼용?) | 저 | Wave 1 착수 시 |
| N5 | 분산 학습 지원 범위 | 저 | Wave 3 |
| N6 | ONNX export 지원 여부 | 저 | MVP 후 |

---

## 섹션 상태

- 7.1 원칙 — ✅
    - 원칙 3 재작성 (Pipeline 경유)
    - **원칙 6 신규 (NN 도입은 부분적·선택적, opt-in)**
- 7.2 Stage Slot — ✅
- 7.3 NN Plugin Contract — ✅
- 7.4 Data Export — ✅
    - 7.4.1~7.4.5 ✅
    - 7.4.6 단계적 학습 전략 ✅
        - **케이스 0 신규 (단일 스테이지 교체, Pairing NN 기준 예시)**
        - 케이스 A/B/C/D 유지
- 7.5 Training — ✅
- 7.6 Metrics — ✅
    - **7.6.4 Run Manifest 신규 (활성 NN 슬롯 명시)**
- 7.7 MVP 범위 — ✅
    - 원칙 재확인 섹션 추가
    - Wave 1 완료 기준을 "Pairing NN 시나리오"로 재정의
- 7.8 기존 문서 영향 — ✅
- 7.9 TBD — ✅

---

👉 이전: [06_topics.md](06_topics.md)
👉 다음: [08_radar_waveforms.md](08_radar_waveforms.md) — RadarModel, FMCW Triangle, Antenna, Multipath, CFAR
