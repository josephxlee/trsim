# 08. 레이더 모델 & 파이프라인 구조

**최종 갱신**: 2026-04-28 (v0.34)

**배경**: 본 프로젝트의 타겟 레이더는 **FMCW Triangle** 방식 단독이다.
그러나 조직에는 **다른 레이더 모델**(예: CW+FMCW Hybrid)이 별개 하드웨어로 존재하며
미래에 Workbench에 추가될 가능성이 있다. 이를 반영해:

- **현재(MVP)**: FMCW Triangle 레이더 전용으로 구체화
- **미래**: 다른 RadarModel을 추가할 수 있는 **추상화 자리**만 마련

이 섹션은 그 경계선을 명확히 그린다.

---

## 8.1 용어 정리 및 오류 교정

### 8.1.1 "Pairing"의 정확한 의미 (본 프로젝트 기준)

본 프로젝트에서 **Pairing**은:

> **FMCW Triangle 파형의 Up-sweep 피크와 Down-sweep 피크를 매칭하는 작업.**
> 목적: 거리(Range)와 속도(Velocity) 분리.

### 8.1.2 이전 버전(v0.5)의 오판 교정

계획서 v0.5에서 내가 `rcs_monopulse_slave/Code/App/radar/detection/alg_signal_pairing.c`를
보고 "본 시스템은 CW+FMCW Hybrid"라고 해석한 것은 **잘못된 추론**이었다.

실제 상황:

| 파일 | 정체 |
|---|---|
| `detection/alg_signal_pairing.c` | **다른 레이더(Hybrid) 프로젝트의 자산**. 본 프로젝트에서는 참고만. |
| `pairing/target_pairing.c` | **본 프로젝트의 FMCW Triangle Up/Down 매칭 자리**. 아직 설계 전. |

따라서 **본 프로젝트의 Pairing = FMCW Triangle Up/Down 매칭 하나뿐**.
Hybrid Pairing은 미래에 "Hybrid 레이더 모델"을 추가할 때 다룬다.

### 8.1.3 v0.5에서 도입했다가 철회하는 것

v0.5에서 너무 일반화했던 개념 중 현재 MVP에 맞지 않는 것들을 **철회** 또는 **미래 영역으로 이동**:

| v0.5에서 도입 | 현재 처리 |
|---|---|
| WaveformKind enum 5종 | 🔻 축소 — 현재는 `FMCW_TRIANGLE` 하나. 나머지는 RadarModel 추상화 자리로 이동 |
| `TrianglePairingContract` / `HybridCwFmcwPairingContract` 두 개 | 🔻 Triangle 하나만 남김. Hybrid는 미래 레이더 모델 문서에서 |
| Pipeline DAG + 피드백 (CW 경로 + FMCW 경로 병렬) | 🔻 현재는 단순 DAG (CW 경로 없음). 피드백(Target Gate)은 유지 |
| DSP 매핑 표에 `alg_pairing_result_t` (CW+FMCW) | 🔻 현재 범위 밖. 참고 자료로만 |

---

## 8.2 RadarModel 추상화 — 미래 확장의 경계

### 8.2.1 개념

**RadarModel**: 실제 하드웨어 레이더 시스템 하나를 표현하는 추상.
정의하는 것은:

- 사용하는 Waveform(들)
- 신호 경로(Signal Path)의 구조
- 파이프라인 Stage 구성
- 각 Stage의 기본 구현 제공

```python
# src/workbench/domain/radar_model.py

class RadarModel(Protocol):
    """하나의 레이더 시스템 모델."""

    model_id: str                       # "fmcw_triangle_v1"
    display_name: str                   # "FMCW Triangle Radar"
    description: str

    def waveform_schema(self) -> WaveformSchema:
        """이 모델이 사용하는 파형 파라미터 스키마."""
        ...

    def build_pipeline_graph(
        self,
        plugins: dict[str, Any],
    ) -> PipelineGraph:
        """이 모델의 Pipeline 구조를 구성."""
        ...

    def default_plugins(self) -> dict[str, Any]:
        """기본 Plugin 세트 반환 (Plugin 미지정 Slot 채움용)."""
        ...
```

### 8.2.2 MVP 시점의 구체화

**MVP에는 RadarModel 구현체 하나만 존재**:

```python
class FMCWTriangleRadar(RadarModel):
    model_id = "fmcw_triangle_v1"
    display_name = "FMCW Triangle Radar"
    ...
```

나머지(`HybridCwFmcwRadar`, `PulseRadar` 등)는 **"여기가 자리"**라는 주석만
`workbench/domain/radar_model/` 디렉토리에 README로 남긴다. 코드 없음.

### 8.2.3 Scenario가 RadarModel 참조

03 § 3.2의 `Scenario` 최종 형태:

```python
@dataclass(frozen=True)
class Scenario:
    name: str
    origin: GeoOrigin
    terrain: TerrainLayer
    buildings: tuple[BuildingBlock, ...]
    sea_state: int
    radar_site: RadarSite

    radar_model_id: str                 # "fmcw_triangle_v1"
    waveform_params: WaveformParams     # 모델에 맞는 파라미터 세트

    rx_array: RXArrayConfig
    duration_s: float
    targets: tuple[TargetTrajectory, ...]
    seed: int
```

MVP에서 `radar_model_id`는 항상 `"fmcw_triangle_v1"`. 미래에 다른 모델이 추가되면 Scenario가 그 값을 가지면 됨.

### 8.2.4 레지스트리

```python
# src/workbench/domain/radar_model/__init__.py

RADAR_MODEL_REGISTRY: dict[str, type[RadarModel]] = {
    "fmcw_triangle_v1": FMCWTriangleRadar,
    # 미래 추가:
    # "hybrid_cw_fmcw_v1": HybridCwFmcwRadar,
    # "pulse_doppler_v1": PulseDopplerRadar,
}
```

사용자가 Scenario를 로드하면 Workbench가 `radar_model_id`로 이 레지스트리에서 찾아 Pipeline 구성.

---

## 8.3 FMCW Triangle Radar 상세

### 8.3.1 Waveform 파라미터

```python
@dataclass(frozen=True)
class FMCWTriangleParams(WaveformParams):
    """FMCW Triangle 파형 파라미터.

    참조: DSP 펌웨어 `signal_fmcw_t` 구조체.
    """
    f_tx_hz: float                      # 예: 10.5 GHz
    bandwidth_hz: float                 # 예: 30 MHz
    sweep_time_s: float                 # 한 방향 sweep 시간 (예: 21 ms)
    # Triangle FMCW 는 up = down sweep time 가정 (단일 필드로 통합)
    fft_bin: int                        # 예: 8192
```

### 8.3.2 Pipeline Slot 구성

```
전체 슬롯:

 1. Transmitter            → 두 램프(Up, Down) 각각에 대해 TX 빔 방사
 2. Environment            → 반사 계산 (두 램프 각각)
 3. Receiver               → RX 신호 + FFT (두 램프 각각)
 4. Detector (CFAR)        → 스펙트럼 → 피크 (두 램프 각각)
 5. AngleEstimator         → 4ch 위상 → az/el (두 램프 각각)
 6. Pairing                → Up 피크 × Down 피크 → PairedDetection (거리·속도)
 7. TargetGate  (옵션/조건부) → 멀티 타겟 상황에서 EKF 혼란 방지용 보조 필터
                              Tracker가 요구하고(requires_target_gate=True),
                              활성 트랙이 존재할 때만 실제로 동작
 8. Tracker                → PairedDetection → Track
 9. Classifier  (옵션)     → Track → 클래스

피드백 (Target Gate 활성 시에만):
  Tracker 출력 → TargetGate → 다음 프레임 Detector 검색 범위 제한
```

**Target Gate가 옵션인 이유는 § 8.3.5 참조.** 단순히 "켤 수도 끌 수도 있다"가 아니라
**Tracker의 설계에 따라 필요성이 달라지는 Tracker-보조 장치**이다.

### 8.3.3 Slot 간 데이터 타입

```python
# 각 램프(Up/Down)마다 나오는 것:
@dataclass(frozen=True)
class RampOutput:
    """한 램프(Up 또는 Down)의 처리 결과."""
    ramp_direction: str                 # "up" or "down"
    spectrum: FFTSpectrum               # 복소 4채널 + power (dB)
    peaks: tuple[Peak, ...]             # CFAR 후
    # Peak에는 이미 angle_estimator 결과 포함

# Pairing 입력/출력:
@dataclass(frozen=True)
class PairingInput:
    up: RampOutput
    down: RampOutput

@dataclass(frozen=True)
class PairedDetection:
    """Up/Down sweep 매칭 결과."""
    range_m: float
    velocity_mps: float
    up_peak: Peak
    down_peak: Peak
    snr_avg_db: float
    az_deg: float                       # Up/Down 평균 또는 Up 기준
    el_deg: float
```

### 8.3.4 Pipeline Graph (Triangle 한 가지)

```
                    ┌──> [Up 램프 처리 경로] ──┐
  Transmitter ──┤                               ├──> Pairing ──> Tracker ──> Track
                    └──> [Down 램프 처리 경로] ──┘                                │
                                                                                  │
          ┌──────────────────────────────────────────────┬──── (if present) ──── ┘
          │                                              │
          ▼                                              ▼
  [다음 프레임 Detector로 피드백]              Classifier (옵션)
          ▲
          │
    TargetGate  (옵션/조건부 — § 8.3.5)
          ▲
          │
      Track 출력
```

- 선형 시퀀스가 아니지만 **단순한 DAG** (경로 2개 + 합류 1번 + 조건부 피드백 1회)
- **TargetGate 피드백 엣지는 조건부 활성**. Tracker가 Gate를 요구하지 않거나 활성 트랙이 없을 때는
  실제로 엣지가 죽어 있어 기능적으로 선형 DAG로 동작.
- v0.5에서 상상했던 복잡한 "CW 경로 + FMCW 경로" 그래프는 **현재 필요 없음**

### 8.3.5 Target Gate의 역할 (왜 옵션인가)

**Target Gate의 목적** = *멀티 타겟 상황에서 EKF Tracker가 여러 탐지를 엉뚱한 트랙에
연관시키는 것을 방지*하기 위한 **Tracker 보조 장치**.

> 이 기능이 본 Workbench에서 중요한 이유: 프로젝트의 최종 목표가
> **"다중 표적 환경에서 선택 표적의 안정적 추적"** ([01 § 1.1](01_vision_scope.md#11-프로젝트-정체성))
> 이므로, 멀티 타겟 data association이 흔들리면 선택 표적 lock이 깨짐.
> Target Gate는 이 근본 이슈를 완화하는 여러 수단 중 하나이며,
> NN Tracker 등 **다른 해결책과 비교 가능**해야 한다는 것이 Workbench의 설계 요구사항.

#### 3가지 관찰

1. **멀티 타겟에서만 문제가 생김**
   단일 타겟이면 "이번 프레임에 들어온 이 탐지 = 하나뿐인 트랙"이라 연관 모호성이 없다.
   두 척 이상(`B_Conflict`, `C_Limit` 같은 시나리오)에서 트랙 간 거리·속도가 가까워지면
   EKF의 data association이 헷갈림 → 트랙 ID 스위칭, 트랙 소실 등.

2. **특정 Tracker가 쓰는 도구**
   Gate는 EKF 같은 **고전적 추적기의 data association을 돕기 위한 장치**.
   NN 기반 Tracker(RNN/Transformer)는 보통 data association을 모델 내부에서
   학습으로 해결하므로 외부 Gate가 불필요. 즉 Gate는 Tracker 선택에 종속적.

3. **초기 프레임에는 무의미**
   활성 트랙이 없으면 gate 영역을 정의할 수 없음 → 첫 몇 프레임은 자동 bypass.

#### 이 세 관찰이 설계에 주는 결과

Target Gate Slot을 "외부에서 켜고 끄는 옵션"으로만 두면 사용자가 잘못 켜거나 끄기 쉬움.
Tracker가 **자기 필요성을 스스로 선언**하게 한다:

```python
class TrackerContract(Protocol):
    requires_target_gate: bool          # 기본 False

    def update(
        self,
        detections: tuple[PairedDetection, ...],
        dt: float,
    ) -> tuple[Track, ...]:
        ...
```

**기본 구현들의 값**:

| Tracker | requires_target_gate | 이유 |
|---|---|---|
| `DefaultEKFTracker` | `True` | 멀티 타겟 연관 안정성 향상 |
| `MyRNNTracker` (예시) | `False` | 모델이 연관을 학습으로 해결 |
| `SingleTargetTracker` | `False` | 단일 타겟 전제라 연관 문제 없음 |

#### Workbench의 자동 동작

Pipeline 조립 시 Workbench가:

```
if tracker.requires_target_gate:
    TargetGate slot = 자동 활성화 (기본 구현 주입)
    사용자가 비활성화 시 경고:
        "현재 Tracker는 Gate를 요구합니다.
         멀티 타겟 시나리오에서 성능 저하 가능."
else:
    TargetGate slot = 비활성화 권장 (활성 시 안내만)
```

#### 런타임 토글 (사용자 제어)

Tracker가 Gate를 요구해도, 사용자는 디버깅·비교를 위해 **런타임에 Gate를 끌 수** 있다.
- UI 상의 "Gate Enable" 토글 버튼
- Command: `sim.toggle_target_gate`
- 이 상태는 Run Manifest에 기록되어 재현 가능

#### Scenario 단에서의 힌트

Scenario에 표적 수가 기록되므로, Workbench는 열릴 때:

- **단일 타겟 Scenario** + Gate-requiring Tracker → "단일 타겟이라 Gate 효과가 제한적입니다" 안내 가능
- **멀티 타겟 Scenario** + Gate 비활성 → "멀티 타겟입니다. Gate 활성화 권장" 안내 가능

이런 힌트는 **경고가 아닌 정보 제공** 수준으로, 강제하지 않음.

#### 멀티 타겟 지원이 계획서 전반에 미치는 영향

Target Gate의 존재 이유가 멀티 타겟이라는 점은 다음을 확인시켜줌:

- ✅ **멀티 타겟 시나리오는 1급 지원 요구사항**
- ✅ **Tracker 비교 시 멀티 타겟 성능이 주요 메트릭** — 07의 Metrics에 `track_id_switches`, `track_continuity`가 이미 있음
- ✅ 기존 `B_Conflict`, `C_Limit` 시나리오가 Gate 기능 검증의 표준 테스트베드

---

## 8.4 Pipeline 실행기 설계

### 8.4.1 단일 RadarModel 실행 모델

```python
class PipelineExecutor:
    """한 RadarModel 인스턴스의 파이프라인을 프레임마다 실행."""

    def __init__(self, radar_model: RadarModel, plugins: dict):
        self.graph = radar_model.build_pipeline_graph(plugins)
        self.frame_idx = 0
        self.last_gate: BinRange | None = None

    def step(self, scenario: Scenario, dt: float) -> FrameResult:
        """한 프레임 실행."""
        # 1. RadarModel이 정의한 graph를 따라 실행
        # 2. Target Gate가 있으면 last_gate를 Detector에 주입
        # 3. Tracker 결과로 last_gate 갱신
        ...
```

### 8.4.2 FMCW Triangle 실행 순서

```python
# FMCWTriangleRadar.build_pipeline_graph가 반환하는 실행 순서

frame execution:
  # Up 램프
  tx_up    = Transmitter.emit(ramp="up")
  refl_up  = Environment.reflect(tx_up)
  spec_up  = Receiver.receive(refl_up)
  peaks_up = Detector.detect(spec_up, gate=self.last_gate)
  peaks_up = AngleEstimator.annotate(peaks_up, spec_up)

  # Down 램프
  tx_down    = Transmitter.emit(ramp="down")
  refl_down  = Environment.reflect(tx_down)
  spec_down  = Receiver.receive(refl_down)
  peaks_down = Detector.detect(spec_down, gate=self.last_gate)
  peaks_down = AngleEstimator.annotate(peaks_down, spec_down)

  # 결합
  paired = Pairing.match_up_down(peaks_up, peaks_down)
  tracks = Tracker.update(paired, dt)

  # Target Gate 피드백 — 3가지 조건이 모두 만족될 때만
  gate_active = (
      tracker.requires_target_gate       # Tracker가 Gate를 요구
      and user_enabled_gate               # 사용자가 런타임에 enable
      and len(tracks) >= 1                # 활성 트랙 존재
  )
  if gate_active:
      self.last_gate = TargetGate.compute(tracks)
  else:
      self.last_gate = None               # 전체 검색

  # 옵셔널
  if Classifier is present:
      class_results = Classifier.classify(tracks)
```

위 3조건 중 하나라도 빠지면 Gate는 자동 bypass되어 Detector가 전체 스펙트럼을 검색.
즉 **Gate 로직 자체는 항상 실행되지만 효과는 조건부**. 이 로직이 Pipeline Executor 내부에
있지 않고 `TargetGate.compute()` 외부에 있는 이유: Gate 판정의 정책이 Tracker·Scenario·UI 토글에
걸쳐 있어 Gate Plugin 자신만으로는 결정할 수 없음.

### 8.4.3 미래 RadarModel을 위한 경계

현재 `PipelineExecutor`는 **RadarModel이 제공하는 `build_pipeline_graph` 결과에 의존**.
즉 FMCW Triangle 이외의 모델도 같은 Executor로 돌아감 — 각 모델이 자기 그래프만 정의하면 됨.

이 경계 덕분에:
- MVP에서는 FMCW Triangle 하나만 구현
- 미래에 Hybrid 레이더 추가 시 `HybridRadar.build_pipeline_graph()`만 구현
- Executor·UI·RunManager 등은 건드릴 필요 없음

---

## 8.5 DSP 코드와의 매핑 (FMCW Triangle 범위만)

> ⚠️ **v0.34 보강 정합**: 본 섹션은 v0.13 시점 DSP 매핑. v0.34에서 도입한 `detector_cfar.py`
> (CA/OS-CFAR 선택), `data_associator.py` (GNN), `tracker_ekf.py`/`tracker_ukf.py` 의 매핑은
> 03 § 3.2.1j (Tracker & Data Association) 와 02 § 2.3 디렉토리 구조 참조.

### 8.5.1 참조 소스

본 프로젝트의 FMCW Triangle 기준 DSP 코드:

- `rcs_monopulse_slave/Code/App/radar/app_sig_proc_r0.c` — 단일 램프 신호 처리
- `rcs_monopulse_slave/Code/App/radar/app_algo_proc.c` — 램프 결합 및 탐지/추적
- `rcs_monopulse_slave/Code/App/radar/detection/cfar.c` — CFAR
- `rcs_monopulse_slave/Code/App/radar/detection/findPeaks.c` — Peak 탐색
- `rcs_monopulse_slave/Code/App/radar/detection/alg_angle.c` — 4ch 위상 → 각도
- `rcs_monopulse_slave/Code/App/radar/pairing/target_pairing.c` — **Up/Down 매칭 자리 (설계 전)**
- `rcs_monopulse_slave/Code/App/radar/tracking_VT_EKF_MNKN/` — EKF 추적

### 8.5.2 참고 자료 (현재 범위 밖이지만 형식만 참조)

- `rcs_monopulse_slave/Code/App/radar/detection/alg_signal_pairing.c` — 다른 레이더(Hybrid)의 Pairing 코드. 본 프로젝트에서는 **사용하지 않지만**, 미래에 Hybrid 레이더 모델 구현 시 참고 자산.

### 8.5.3 타입 매핑 표 (FMCW Triangle 범위)

| DSP C struct | Workbench Python dataclass | 비고 |
|---|---|---|
| `signal_fmcw_t` | `FMCWTriangleParams` | Ftx, Fbw, sweep time, ramp mode |
| `signal_conf_t` | `WaveformParams` + `RXArrayConfig` | Fs, Fres, FFT bin, 채널 위상 오프셋 |
| `det_peak_info_t` | `DetPeakInfo` | CFAR 직후 원시 피크 |
| `appSigProcPeakInfo_t` | `Peak` | 각도·위상 포함 |
| `alg_angle_res_t` | `AngleEstimate` | (az, el, phases[4]) |
| **(TBD)** `target_pairing.c`의 Pairing 결과 구조체 | `PairedDetection` | **구현 시 같이 정의** |
| `target_gate_t` + `gate_binpoint_t` | `TargetGate` + `BinRange` | |
| `VelocityTrackerOut_t` | `Track` | |

### 8.5.4 Contract 메서드 시그니처 매핑

DSP 코드의 함수 시그니처를 Workbench Contract로:

```python
# alg_angle.h의 calcTargetAngle과 직접 매칭
class AngleEstimatorContract(Protocol):
    def calc_target_angle(
        self,
        phases_4ch_rad: np.ndarray,     # shape (4,)
        lambda_m: float,
        antenna_horizontal_m: float,
        antenna_vertical_m: float,
    ) -> tuple[float, float]:           # (az_deg, el_deg)
        ...

# cfar.h의 ca_cfar와 직접 매칭
class DetectorContract(Protocol):
    def ca_cfar(
        self,
        power_dbm: np.ndarray,          # shape (n_bins,)
        alpha: float,
        guard_cell_num: int,
        training_cell_num: int,
    ) -> np.ndarray:                    # CFAR result, shape (n_bins,)
        ...

# findPeaks.h의 findPeaks_fmcw와 매칭
class PeakFinderContract(Protocol):
    def find_peaks_fmcw(
        self,
        cfar_result: np.ndarray,
        power_dbm: np.ndarray,
        min_peak_distance: int,
        min_snr: float,
    ) -> tuple[Peak, ...]:
        ...
```

이 매핑 덕분에 사용자가 C 펌웨어 코드의 동일 함수를 Python으로 포팅해 Workbench에서 검증 가능.

---

## 8.5a Antenna Model — 형태와 채널 (v0.25 신설)

v0.24까지 RadarModel은 **빔 패턴이 sinc² 단일 빔**으로 가정됐다 (자함 함정의 파라볼릭
안테나 기준). v0.25에서 안테나 형태를 일반화해 **파라볼릭(parabolic)** + **평면 어레이
(planar array)** 둘 다 지원하며, RX 채널 구조를 **모노펄스 4채널** 까지 확장한다.

이 확장은 Editor Workspace의 Radar Editor를 통해 사용자가 편집할 수 있다 (05 § 5.x).

### 8.5a.1 Antenna 형태 추상

```python
class AntennaType(Enum):
    PARABOLIC = "parabolic"             # 파라볼릭 반사기 — 단일 빔, sinc²
    PLANAR_ARRAY = "planar_array"       # 평면 어레이 — array factor × element pattern
    # MVP+α:
    # SLOTTED_WAVEGUIDE = "slotted_waveguide"
    # HORN = "horn"


class AntennaConfig(Protocol):
    """안테나 형태별 빔 패턴 계산을 위한 공통 인터페이스."""
    type: AntennaType

    def beam_pattern(self, theta_deg: float, phi_deg: float) -> float:
        """빔 축 기준 (theta_az, phi_el) 방향의 정규화 이득 [0, 1].

        boresight (0,0) = 1.0, 사이드로브에서 감쇠.
        """
        ...

    def beamwidth_az_deg(self) -> float: ...
    def beamwidth_el_deg(self) -> float: ...
    def peak_gain_dbi(self) -> float: ...
```

### 8.5a.2 Parabolic (현재 MVP 동작 유지)

```python
@dataclass(frozen=True)
class ParabolicAntenna:
    """파라볼릭 반사기 — 단일 빔, sinc² 사이드로브 패턴."""
    type: AntennaType = AntennaType.PARABOLIC

    diameter_m: float                   # 안테나 지름
    frequency_hz: float                 # 동작 주파수
    efficiency: float = 0.6             # 개구면 효율

    # 빔폭은 lambda/D로 자동 계산 (편의 필드)
    @property
    def beamwidth_3db_deg(self) -> float:
        wavelength = c / self.frequency_hz
        # 3dB 빔폭 ≈ 70 * λ/D (deg)
        return 70.0 * wavelength / self.diameter_m

    def beam_pattern(self, theta_deg: float, phi_deg: float) -> float:
        # sinc² (현재 v0.18 사이드로브 모델)
        # 첫 사이드로브 -13.3 dB, 06 § 6.8.x 참조
        ...
```

빔폭 az = el (대칭 가정). 비대칭이 필요하면 `slot` 형태 또는 `planar_array`.

### 8.5a.3 Planar Array (v0.25 신설)

```python
@dataclass(frozen=True)
class PlanarArrayAntenna:
    """평면 어레이 — N×M 소자 격자.

    빔 패턴 = Array Factor × Element Pattern.
    MVP는 균일 배치 + 동일 가중 가정 (단순화).
    """
    type: AntennaType = AntennaType.PLANAR_ARRAY

    # 격자 구성
    n_elements_az: int                  # azimuth 방향 소자 개수
    n_elements_el: int                  # elevation 방향
    spacing_m: float = 0.5              # 보통 λ/2 — λ 기준 표현이 일반적이지만
                                        # 동작 주파수 알면 m로 변환

    # 동작
    frequency_hz: float
    element_pattern: str = "cos"        # "cos" / "isotropic" — 소자 자체 패턴 (단순)

    # 어레이 형상
    grid_shape: str = "rectangular"     # "rectangular" / "triangular"

    # 빔포밍 (MVP 단순화)
    weighting: str = "uniform"          # "uniform" / "taylor" / "chebyshev"
                                        # MVP는 uniform만, taper는 MVP+α

    @property
    def beamwidth_3db_az_deg(self) -> float:
        wavelength = c / self.frequency_hz
        L_az = (self.n_elements_az - 1) * self.spacing_m
        # 3dB 빔폭 ≈ 0.886 * λ/L (uniform array, deg)
        return degrees(0.886 * wavelength / L_az)

    @property
    def beamwidth_3db_el_deg(self) -> float:
        wavelength = c / self.frequency_hz
        L_el = (self.n_elements_el - 1) * self.spacing_m
        return degrees(0.886 * wavelength / L_el)

    def array_factor(self, theta_az_deg: float, phi_el_deg: float) -> complex:
        """N×M 어레이의 array factor (boresight 기준)."""
        # AF(θ,φ) = Σ_n Σ_m exp(j*k*(n*d*sin(θ) + m*d*sin(φ)))
        # uniform weighting 가정
        ...

    def beam_pattern(self, theta_deg: float, phi_deg: float) -> float:
        af = abs(self.array_factor(theta_deg, phi_deg))
        ep = element_factor(theta_deg, phi_deg, self.element_pattern)
        return (af * ep) / (self.n_elements_az * self.n_elements_el)
```

### 8.5a.4 RX 채널 구조 — 모노펄스 (v0.25 신설)

추적 레이더의 핵심은 **모노펄스 각도 추정**. v0.25에서 RX 채널을 4채널로 확장:

```python
class RXChannelKind(Enum):
    SUM = "sum"                         # Σ — 합 채널 (탐지·거리·도플러)
    DELTA_AZ = "delta_az"               # Δaz — 방위 오차 신호
    DELTA_EL = "delta_el"               # Δel — 고각 오차 신호
    DELTA_DELTA = "delta_delta"         # Δ² — 2차 오차 (선택)


@dataclass(frozen=True)
class MonopulseRXConfig:
    """모노펄스 4채널 수신 구성 (v0.25)."""
    n_channels: int = 4                 # sum + Δaz + Δel + (옵션) Δ²

    # 채널 구성: 안테나 타입에 따라 다름
    # PARABOLIC: 4-quadrant feed (단일 dish의 4-feed)
    # PLANAR_ARRAY: 어레이를 4 sub-array로 분할
    channel_setup: str                  # "quad_feed" / "subarray_partition"

    # 모노펄스 처리 모델
    error_slope_kaz: float              # error/sum/Δaz의 monopulse slope
    error_slope_kel: float              # error_az_rad ≈ kaz * Re(Δaz/Σ)
    boresight_calibration: dict         # 보정 데이터 (offset, slope linearity)
```

**RXArrayConfig 확장** (03 § 3.2.x 갱신):

```python
@dataclass(frozen=True)
class RXChannelSpec:
    """단일 RX 채널 정의."""
    kind: RXChannelKind
    label: str                          # UI 표시 이름
    # 채널별 추가 메타 (gain, noise_figure 등)


@dataclass(frozen=True)
class RXArrayConfig:
    """전체 RX 구성. v0.25에서 모노펄스로 확장."""
    channels: tuple[RXChannelSpec, ...]
    monopulse: MonopulseRXConfig | None = None  # 모노펄스인 경우만

    # 단일 채널 (디버그·간단 모델용)
    @classmethod
    def single_channel(cls) -> "RXArrayConfig":
        return cls(channels=(RXChannelSpec(RXChannelKind.SUM, "Σ"),))

    # 모노펄스 4채널 (MVP 표준)
    @classmethod
    def monopulse_4ch(cls, k_az: float, k_el: float,
                      antenna_type: AntennaType) -> "RXArrayConfig":
        setup = "quad_feed" if antenna_type == AntennaType.PARABOLIC \
                else "subarray_partition"
        return cls(
            channels=(
                RXChannelSpec(RXChannelKind.SUM, "Σ"),
                RXChannelSpec(RXChannelKind.DELTA_AZ, "Δaz"),
                RXChannelSpec(RXChannelKind.DELTA_EL, "Δel"),
                RXChannelSpec(RXChannelKind.DELTA_DELTA, "Δ²"),
            ),
            monopulse=MonopulseRXConfig(
                n_channels=4,
                channel_setup=setup,
                error_slope_kaz=k_az,
                error_slope_kel=k_el,
                boresight_calibration={},
            ),
        )
```

### 8.5a.5 안테나 타입과 채널 구성의 호환

| AntennaType | 채널 구성 | MVP |
|---|---|---|
| PARABOLIC | RXArrayConfig.single_channel() | ✅ (기존) |
| PARABOLIC | RXArrayConfig.monopulse_4ch (quad_feed) | ✅ (v0.25) |
| PLANAR_ARRAY | RXArrayConfig.single_channel() | ✅ (디지털 빔포밍 단순화) |
| PLANAR_ARRAY | RXArrayConfig.monopulse_4ch (subarray_partition) | ✅ (v0.25) |
| PLANAR_ARRAY | N채널 디지털 빔포밍 | ❌ MVP+α (DBF) |
| 모든 타입 | MIMO TX | ❌ MVP+α |

### 8.5a.6 모노펄스 각도 추정 (Monopulse Pipeline)

모노펄스 4채널이 활성이면 Pipeline에 **monopulse 각도 추정** 단계가 추가됨:

```
RX → IF → Mixer → ADC → FFT → CFAR (Σ 채널)
                         ↓
                       Detection (각 detection의 cell index 알려짐)
                         ↓
              ─────────┬───────────┬─────
              Δaz cell │  Δel cell │  ↓
              값 추출  │  값 추출   │
                       ↓           ↓
                   error_az = kaz * Re(Δaz/Σ)
                   error_el = kel * Re(Δel/Σ)
                       ↓
                   Detection에 (error_az_rad, error_el_rad) 추가
                       ↓
                   Tracker 입력 (기존보다 정확한 각도)
```

이건 **v0.13 4-error 진단**(07 § 7.4.5d)과 직접 연결: 모노펄스 error가 EKF Command Error의
근본 입력이 됨. 즉 v0.25 안테나 모델 확장은 추적 정확도 핵심 경로와 직결.

### 8.5a.7 MVP 빔 패턴 단순화 명시

이 확장은 **데이터 모델·Pipeline 구조의 일반화**이지 빔 패턴 정밀 합성은 아니다. MVP 단순화:

- Parabolic: sinc² 패턴 (현재 v0.18 그대로)
- Planar Array: uniform weighting array factor (taper·grating lobes 등 단순화)
- Element pattern: cos 또는 isotropic
- 사이드로브 -13.3 dB 가정 유지 (사용자 override 가능)
- MIMO·DBF 등 고급 기법은 MVP+α

정밀 빔 패턴 (실측 또는 EM 시뮬 데이터 import)은 **MVP+α** — 06 § 6.8 Deferred RF Suite.

### 8.5a.8 Radar Resource 파일 구조 (자원 라이브러리 통합)

10 § 10.9.4의 Radar 자원 TOML이 v0.25에서 확장:

```toml
# resources/radars/fmcw_corvette/radar.toml

name = "fmcw_corvette"
description = "FMCW Triangle radar on 500t corvette, monopulse"
version = "1.1"
content_hash = "sha256:..."

[platform]
platform_id = "corvette_500t"
category = "maritime"
# ... v0.18 Platform 필드들

[radar_model]
model_id = "fmcw_triangle_v1"
# ... 08 § 8.2 Waveform 필드들

# v0.25 신설
[antenna]
type = "parabolic"                  # parabolic / planar_array

# parabolic 일 때
diameter_m = 0.6
frequency_hz = 9.5e9
efficiency = 0.6

# planar_array 일 때 (type=planar_array면 위 4개 대신 아래)
# n_elements_az = 16
# n_elements_el = 16
# spacing_m = 0.0158                # λ/2 @ 9.5GHz
# element_pattern = "cos"
# weighting = "uniform"

[rx_array]
mode = "monopulse_4ch"              # single_channel / monopulse_4ch
monopulse_slope_kaz = 1.4           # mode=monopulse_4ch일 때
monopulse_slope_kel = 1.4
```

## 8.5b Propagation Effects — Multipath + Refraction (v0.34 신설)

베이스라인 점검(16 § 16.3) 결과 multipath와 refraction이 빠져 있어 v0.34에서 MVP 추가.

### 8.5b.1 Two-Ray Multipath (해상 시나리오 핵심)

**문제**: 해상에서 신호는 직접 경로(LOS) + 해수면 반사 두 경로로 옴. 거리·고도에 따라 phase 차이로 lobing pattern 발생. 함정 추적의 핵심.

**MVP 모델**:

```python
def two_ray_path_loss(
    radar_pos_m: vec3,
    target_pos_m: vec3,
    sea_surface_z_m: float,
    frequency_hz: float,
    polarization: Literal["V", "H"] = "V",
) -> complex:
    """Two-ray multipath. Returns complex gain (vs free-space).

    직접 경로 + sea bounce reflection 합성. grazing angle 작을 때
    reflection coefficient ≈ -0.95 (V/H polarization 모두).
    """
    # 1. Direct path
    R_direct = norm(target_pos_m - radar_pos_m)

    # 2. Sea-surface mirror image
    target_image = target_pos_m.copy()
    target_image[2] = 2 * sea_surface_z_m - target_pos_m[2]
    R_reflected = norm(target_image - radar_pos_m)

    # 3. Phase difference (왕복은 path loss에 따로 적용되므로 여기는 one-way)
    wavelength = 3e8 / frequency_hz
    delta_phase = 2 * np.pi * (R_reflected - R_direct) / wavelength

    # 4. Reflection coefficient (MVP는 단순화)
    rho = -0.95 + 0j   # near -1 at grazing angle

    # 5. Total field (각 경로의 1/R 가중)
    direct = 1.0 / R_direct
    reflected = rho * np.exp(-1j * delta_phase) / R_reflected

    return (direct + reflected) / direct  # complex gain factor
```

**효과**:
- 표적 고도·거리에 따라 신호 강해지거나 약해짐 (multi-path lobing)
- 추적 안정성 검증의 핵심 변수 — 안정 경로일 때 vs 노치(null)에 들어갔을 때의 추적 성능
- 빔이 sea bounce로 도래각 살짝 흔들리는 효과도 있지만 MVP는 amplitude만 (각도 영향은 MVP+α)

**Toggle**: Scenario에서 `multipath_enabled = true/false`. 디버그·교육용 free-space 비교 가능.

**MVP+α**:
- 토양·콘크리트 표면 반사 (지상 표적용)
- 다중 반사 (복잡한 지형)
- Rough surface scattering (sea state별 변형)
- Reflection coefficient의 정밀 Fresnel (incidence angle, polarization, surface roughness 의존)

### 8.5b.2 Atmospheric Refraction (4/3 Earth Radius)

**문제**: 빔이 표준 대기 중에서도 약간 휘어짐. 50km Simulation Domain에서 거리·각도 오차.

**MVP 모델**: 15 § 15.5.4 참조. Effective Earth Radius = 4/3 × 6378 km로 LOS 차폐·horizon 검사 보정.

**적용 위치** (RadarModel 안):
- `compute_los_obstruction()` — Earth curvature를 effective radius로 보정
- `compute_horizon_distance()` — 빔이 표적 위치에 도달 가능한지 판단

## 8.5c Detection — CFAR 알고리즘 (v0.34 보강)

베이스라인 점검 결과 CA-CFAR만으로는 클러터 환경 부족. OS-CFAR 추가.

### 8.5c.1 CA-CFAR (Cell-Averaging) — 기존 MVP

```python
def ca_cfar_threshold(
    cell_under_test_idx: int,
    range_doppler_map: np.ndarray,
    n_training: int,
    n_guard: int,
    pfa: float = 1e-6,
) -> float:
    """Cell-averaging CFAR. 균일 클러터 가정."""
    ...
```

**한계**: Edge of clutter, multiple target에서 false alarm rate 폭증.

### 8.5c.2 OS-CFAR (Ordered Statistics) — v0.34 MVP 추가

```python
def os_cfar_threshold(
    cell_under_test_idx: int,
    range_doppler_map: np.ndarray,
    n_training: int,
    n_guard: int,
    rank_k: int,                   # 보통 3N/4
    pfa: float = 1e-6,
) -> float:
    """Ordered Statistics CFAR. Multiple target / clutter edge에 robust.

    Training cell의 k-th order statistic을 noise 추정값으로 사용.
    """
    ...
```

**용도**:
- 클러터 environment에 multiple target 존재 시
- Clutter edge (해상↔육상 경계) 부근
- High clutter 환경의 일반 추적

### 8.5c.3 사용자 선택 가능

Editor의 Radar Editor (또는 Scenario Composer)에서:

```
┌─ Detector ────────────────────┐
│ Algorithm: [CA-CFAR ▾]         │
│            ├ CA-CFAR (default) │
│            └ OS-CFAR           │
│                                │
│ N_training: [16]               │
│ N_guard:    [4]                │
│ Pfa:        [1e-6]             │
│ rank_k:     [12] (OS-CFAR only)│
└────────────────────────────────┘
```

**MVP+α**:
- GO-CFAR (Greatest Of) — heterogeneous clutter
- SO-CFAR (Smallest Of) — multiple target 우선
- Adaptive CFAR



현재 `pairing/target_pairing.c`는 빈 파일이다. 이는 **Workbench 관점에서 기회**가 된다:

### 8.6.1 Workbench가 Pairing 알고리즘 개발 워크벤치가 됨

Pairing 알고리즘이 DSP 펌웨어에 아직 없다는 것은:

- 사용자가 **여러 Pairing 접근**을 Workbench에서 먼저 실험
- 최종 채택될 알고리즘을 찾은 후 C 코드로 포팅
- 이 과정이 **Workbench의 가장 명확한 가치 사례**

구체적 워크플로우:

```
1. Workbench에서 단순 기본 Pairing(예: 최소 주파수 차이) 구현 → DefaultPairing
2. NN 기반 Pairing Plugin 실험 → MyPairingNN
3. 여러 대안 비교 → 최적 알고리즘 선정
4. 선정된 알고리즘을 C로 포팅하여 target_pairing.c에 구현
5. C 구현과 Python 구현의 동등성 검증 (TF↔numpy 동치성 패턴 재활용)
```

### 8.6.2 07 NN 통합의 Pairing 예시가 특히 중요해짐

07 § 7.4.6 "케이스 0"의 Pairing NN 예시는 **가상의 시나리오가 아니라 실제 진행 중인 작업**.
MVP+α의 Wave 1 목표가 "Pairing NN 실험을 Workbench에서 완결"이 되는 이유가 여기 있음.

---

## 8.7 07 NN 통합 / 03 데이터 모델 갱신 지시

> ⚠️ **v0.35 정합**: 본 섹션은 v0.13 시점 작업 지시 — 대부분 처리 완료.
> v0.35 SDK Layer (02 § 2.6b) 도입 후 `RadarModelProtocol` 은 **MVP+α 비개방**
> (17 § 17.2.6 — DLC가 새 RadarModel 추가 못 함, MVP는 FMCW Triangle 단일).
> Domain Layer 핵심 안정성 위함. MVP+α 시점에 SDK Public API로 노출 검토.

### 8.7.1 07에 반영할 것

- "Hybrid Pairing NN" 항목 **삭제**. MVP 범위에서 이런 구분 필요 없음.
- Pairing NN은 **Triangle Up/Down 매칭 단일 Contract**.
- 템플릿 이름에서 `_triangle` suffix도 제거 가능 (Pairing이 하나뿐이므로).

### 8.7.2 03에 반영할 것

- `Scenario.waveform: WaveformConfig` → `Scenario.radar_model_id: str + waveform_params: WaveformParams`
- `WaveformKind` enum 제거, `RadarModel` 레지스트리로 대체

### 8.7.3 용어집 갱신

- "Waveform / WaveformKind" 항목 수정 — MVP는 FMCW Triangle 한정
- "RadarModel" 신규 용어
- "Triangle Pairing" 유지, "Hybrid Pairing" 항목 제거 또는 "미래 작업"으로 이동

---

## 8.8 MVP 범위 — 최종

### In Scope (MVP)

- ✅ FMCW Triangle 전용 RadarModel 구현
- ✅ Up/Down Pairing Contract 정의 및 기본 구현
- ✅ Target Gate Slot
- ✅ DSP C 코드 시그니처와 매칭되는 Python Contract
- ✅ **Two-ray multipath (sea bounce)** — 해상 시나리오 핵심 (v0.34)
- ✅ **Atmospheric refraction (4/3 earth)** — 장거리 정확도 (v0.34)
- ✅ **OS-CFAR detector** — 클러터 환경 (v0.34, CA-CFAR와 선택)

### Out of Scope (미래)

- 🔒 CW+FMCW Hybrid 레이더 (별개 RadarModel로 추가)
- 🔒 Pulse / PPI 등 다른 레이더 타입
- 🔒 실제 DSP 펌웨어와의 Bit-exact 검증 자동화 (수동 동치성 테스트는 가능)
- 🔒 **STAP** — 공중·우주 레이더 영역 (16 § 16.5)
- 🔒 **Massive MIMO / Hybrid beamforming** — 5G/SATCOM 영역 (16 § 16.5)
- 🔒 **SAR / ISAR** — 영상 영역 (16 § 16.5)

---

## 8.9 결정 사항 요약

### 확정

- ✅ **현재 타겟 레이더는 FMCW Triangle 하나**
- ✅ Pairing = Up/Down sweep 매칭 단일 정의
- ✅ RadarModel 추상화로 미래 다른 레이더 확장 여지만 마련
- ✅ MVP에는 `FMCWTriangleRadar` 한 개 구현, 다른 모델은 "자리만"
- ✅ 07 문서에서 "Hybrid Pairing" 언급 제거
- ✅ 03 Scenario 구조 개정 (radar_model_id 필드 도입)
- ✅ v0.5에서 도입한 복잡한 Waveform enum / 두 Pairing Contract / DAG 병렬 경로는 철회

### 미래 작업 (별도 기획 필요)

- ⏳ Hybrid CW+FMCW 레이더 모델 추가
- ⏳ Pulse/PPI 레이더 등
- ⏳ RadarModel 교체 시 Plugin 재사용성 검토 (어떤 Contract가 모델 간 공유 가능한가)

---

## 8.10 섹션 상태

- 8.1 용어 교정 — ✅
- 8.2 RadarModel 추상화 — ✅
- 8.3 FMCW Triangle 상세 — ✅
    - 8.3.1~8.3.4 ✅
    - **8.3.5 Target Gate의 역할 — ✅ (Tracker 의존적 옵션임을 명시)**
- 8.4 Executor 설계 — ✅ (Gate 조건부 실행 반영)
- 8.5 DSP 매핑 — ✅ (FMCW Triangle 범위로 한정)
- **8.5a Antenna Model — ✅ (v0.25 신설, 파라볼릭 + 평면 어레이 + 모노펄스 4채널)**
- **8.5b Propagation — ✅ (v0.34 신설, two-ray multipath + refraction)**
- **8.5c Detection CFAR — ✅ (v0.34 신설, CA + OS-CFAR 선택)**
- 8.6 target_pairing 미구현의 함의 — ✅
- 8.7 07/03 갱신 지시 — ✅
- 8.8 MVP 범위 — ✅
- 8.9 결정 사항 — ✅

---

👉 이전: [07_nn_integration.md](07_nn_integration.md)
👉 다음: [09_radar_platforms.md](09_radar_platforms.md)
