# 06. 기술 주제

**최종 갱신**: 2026-05-02 — v0.40: § 6.7a 사용자 물리 plugin 결정 변경 (영구 제외 → 가능, Physics Lab 안전망)

**상태**: 🟡 **참조 보존**. v0.15~v0.35 의 변경 (DLC 시스템·SDK Layer·v0.34 베이스라인 검증·Apache 2.0 등) 은 다음 문서가 권위:
- **플러그인 시스템·DLC**: [17 open_platform.md](17_open_platform.md) (v0.35) + [02 § 2.6b architecture.md](02_architecture.md) (SDK Layer)
- **테스팅·검증 카테고리**: [16 baseline_audit.md](16_baseline_audit.md) (v0.34, 11종 → 17종) + [04 § Phase 5 migration.md](04_migration.md)
- **라이선스 (Apache 2.0)**: [17 § 17.2.1 open_platform.md](17_open_platform.md) — 본 문서 § 6.5 도 정정됨

본 문서는 **v0.10~v0.14 시점 초기 컨셉 참조용**. 정합 노트 (⚠️) 가 § 6.2 에 있어 권위 위치 안내.

개별 섹션으로 다루기 애매하지만 **설계에 중요한 주제**들.
Probe/Trace 시스템, 테스팅 전략, 플러그인 시스템, 라이선스 등.

---

## 6.1 Probe / Trace 시스템 (깊이 있게)

데이터 모델(03)에서 개요만 봤던 것을 여기서 구현 수준으로 설명.

### 6.1.1 요구사항 다시 정리

디버깅+재현 워크플로에서 필요한 것:

1. 파이프라인의 **모든 중간 결과**를 관찰할 수 있어야 함
2. 특정 프레임으로 **시간 이동** 후 그 프레임의 상태를 정확히 재현
3. 두 Run의 같은 Probe를 **나란히 비교**
4. 사용자 플러그인이 **자체 Probe를 노출** 가능
5. 저장 비용이 커질 수 있으므로 **선택적 활성화**

### 6.1.2 Probe 등록 패턴

```python
# 코어 파이프라인의 Probe는 시스템이 자동 등록
class RadarPipeline:
    PROBES = {
        "tx_beam": TXBeam,
        "reflections": tuple[Reflection, ...],
        "rx_fft_spectrum": FFTSpectrum,
        "up_peaks": tuple[Peak, ...],
        "down_peaks": tuple[Peak, ...],
        "paired_detections": tuple[PairedDetection, ...],
        "detections": tuple[Detection, ...],
        "tracks": tuple[Track, ...],
        "positioner_state": JointState,
    }

# 플러그인은 declare_probes()로 노출
class MyDetector:
    @staticmethod
    def declare_probes() -> dict[str, type]:
        return {
            "my_threshold": float,
            "my_noise_floor": numpy.ndarray,
        }

    def detect_from_spectrum(self, spectrum):
        th = ...
        nf = ...
        # ProbeRecorder에 기록 (아래 설명)
        self._probe("my_threshold", th)
        self._probe("my_noise_floor", nf)
        ...
```

### 6.1.3 ProbeRecorder 구현

```python
class ProbeRecorder:
    """스레드 안전한 프레임별 Probe 캡처."""

    def __init__(self, config: ProbeConfig):
        self.config = config
        self._current_frame: dict[str, Any] = {}
        self._trace: list[TraceFrame] = []

    def begin_frame(self, frame_id: int, timestamp_s: float):
        self._current_frame = {"_meta": (frame_id, timestamp_s)}

    def capture(self, probe_name: str, value: Any):
        if probe_name not in self.config.enabled:
            return
        # ndarray는 설정에 따라 요약만
        if isinstance(value, numpy.ndarray) and not self.config.capture_ndarrays:
            self._current_frame[probe_name] = _summarize(value)
        else:
            self._current_frame[probe_name] = value

    def end_frame(self):
        frame_id, ts = self._current_frame.pop("_meta")
        self._trace.append(TraceFrame(
            frame_id=frame_id,
            timestamp_s=ts,
            probes=dict(self._current_frame),  # 불변 스냅샷
        ))

    def finalize(self) -> Trace:
        return Trace(
            run_id=...,
            scenario_name=...,
            frames=tuple(self._trace),
            probe_schema=_infer_schema(self._trace),
        )
```

파이프라인은 `probe_recorder` 주입받아 각 스테이지 후에 `capture()` 호출.
플러그인은 `_probe` 메서드로 간접 접근 (플러그인 기반 클래스에 편의 메서드 제공).

### 6.1.4 저장 포맷 — MVP 추천

**두 가지 모드 지원**:

**Mode A: 인메모리 전체** (디버깅 모드)
- Probe 전부 ndarray까지 메모리 유지
- 프레임 < 500개일 때 권장
- 종료 시 HDF5 덤프

**Mode B: 요약만** (기본)
- ndarray는 (shape, mean, std, min, max)만
- 특정 프레임의 상세가 필요하면 **재실행** (시드 고정으로 재현)

HDF5 구조 예시:
```
trace.h5
├── meta (attrs: run_id, scenario_name, created_at)
├── frames/
│   ├── 000000/
│   │   ├── tx_beam (group)
│   │   ├── rx_fft_spectrum/
│   │   │   ├── up (dataset, float32 n_bins)
│   │   │   └── down (dataset)
│   │   ├── up_peaks (group with index 0..N)
│   │   └── ...
│   ├── 000001/
│   └── ...
└── probe_schema (JSON string attr)
```

HDF5 선택 이유:
- 부분 로드 효율적 (특정 프레임만)
- Python h5py 안정적
- JSON보다 ndarray 저장 효율 훨씬 좋음
- 바이너리지만 HDFView 등 확인 도구 있음

#### CSV Export (v0.14 추가)

HDF5는 디버거용으로 완벽하지만 엑셀·다른 분석 도구에서 바로 보기엔 불편. 따라서 **CSV
Export 옵션**을 추가. Stage I/O Panel의 `📥 CSV` 버튼이 이를 호출.

```python
class ProbeCSVExporter:
    """Probe 데이터를 사람이 바로 읽을 수 있는 CSV로 변환.

    - 1차원 배열 (peak 목록 등): 행=인덱스, 열=필드
    - 2차원 배열 (스펙트럼 up/down): 행=bin, 열=amplitude
    - 스칼라/메타: 단일 행 key-value CSV
    """

    def export_frame(self, trace: Trace, frame_id: int, probe_names: list[str],
                     output_dir: Path) -> list[Path]:
        """한 프레임의 여러 probe를 CSV들로."""
        ...

    def export_full_run(self, trace: Trace, probe_names: list[str],
                        output_zip: Path) -> Path:
        """Run 전체를 ZIP 번들로 (프레임별 CSV 묶음)."""
        ...
```

**배열 형태별 CSV 규칙**:

| Probe 형태 | CSV 구조 |
|---|---|
| Peak list (N × fields) | `index, range_bin, velocity_bin, snr_db, phase_ch0, ...` |
| Spectrum (N_bins,) | `bin_index, amplitude_db` |
| Pairing matrix (N_up × N_down) | 행렬 그대로, 1행=up 인덱스, 헤더=down 인덱스 |
| Track list (N × fields) | `track_id, range_m, velocity_mps, az_deg, el_deg, lock_status, ...` |
| TXBeam / FFTSpectrum meta | key-value 세로 |

**CSV는 사용자용, HDF5는 Workbench 내부용**이라는 원칙. CSV로는 일부 메타를 잃을 수 있고(복원 불가), HDF5는 재생 가능한 완전 기록.

### 6.1.5 타임라인 스크럽 (MVP 후)

```
┌─ Timeline ─────────────────────────────────────────┐
│  [├──────●─────────────────────┤]                   │
│   0                127                        200   │
│   [⏮][◀][▶][⏭]    Frame: 127 (12.7 s)              │
│                                                    │
│   ┌─ Probe Values at Frame 127 ───────────────┐    │
│   │ tx_beam.az_deg    = 180.0                 │    │
│   │ tx_beam.el_deg    = 0.63                  │    │
│   │ up_peaks.count    = 3                     │    │
│   │ detections.count  = 2                     │    │
│   │ tracks.count      = 1                     │    │
│   │ my_threshold      = 12.3                  │    │
│   │ [Detail] [Compare with Run #41]           │    │
│   └───────────────────────────────────────────┘    │
└────────────────────────────────────────────────────┘
```

---

## 6.2 플러그인 시스템

> ⚠️ **v0.35 정합**: 본 섹션의 단일 `.py` 파일 동적 로드 모델은 **v0.13 시점 사고**.
> v0.35에서 도입한 DLC 시스템 (`.trsim-pkg` 패키지 + SDK Layer + PackageManager) 이
> **권위 정의** — [17 open_platform.md](17_open_platform.md), 02 § 2.6b 참조.
>
> 두 모델의 관계:
>
> - **단일 .py Plugin** (본 섹션, v0.13): MVP의 단순 모델. 개인 PC에서 사용자가 만든
>   plugin을 빠르게 등록·테스트. `~/my_workbench_project/plugins/` 등 자유 위치
> - **`.trsim-pkg` DLC** (v0.35, MVP+α Phase 7): 공식 패키지 형식.
>   `manifest.toml` + `plugins/` + `resources/` + `ui/` 묶음. `~/.trsim/packages/<id>/`
>   설치, SDK Plugin Protocol 9개 사용
>
> **MVP는 단일 .py로 충분**, MVP+α (Phase 7) 에서 DLC로 확장. 둘은 공존 가능 — Plugin Loader가 두 경로 모두 스캔.

### 6.2.1 로딩 메커니즘

```python
# app/plugin_loader.py

def load_plugin(path: Path, class_name: str) -> Any:
    """동적 .py 로드 + Contract 검증."""
    spec = importlib.util.spec_from_file_location(
        f"user_plugin_{path.stem}",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # 사용자 코드 실행

    cls = getattr(module, class_name)
    instance = cls()

    # Contract 검증
    _validate_contract(instance, expected_contract)

    return instance
```

### 6.2.2 Contract 검증

```python
def _validate_contract(instance, contract: type) -> None:
    """Protocol이 요구하는 메서드들이 구현되었는지 확인."""
    for method_name in _protocol_methods(contract):
        if not callable(getattr(instance, method_name, None)):
            raise ContractViolation(
                f"{instance.__class__.__name__} missing method {method_name}"
            )
    # 타입 시그니처는 런타임 강제 어려우므로 문서로
```

### 6.2.3 핫 리로드 (파일 변경 감지)

`watchdog` 라이브러리로 플러그인 파일 수정 감지:

```python
class PluginWatcher:
    def __init__(self, plugin_loader, event_bus):
        self.observer = Observer()
        ...

    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            plugin_ref = self._find_plugin(event.src_path)
            if plugin_ref:
                self.event_bus.emit("plugin.file_changed", plugin_ref)
                # UI가 "Reload?" 프롬프트, 또는 자동 재로드
```

- **자동 재로드는 기본 OFF** (Run 중 코드가 바뀌면 혼란)
- 수동 "Reload" 버튼이 기본
- 옵션으로 자동 재로드 가능

### 6.2.4 플러그인 격리

MVP는 **같은 프로세스**에서 플러그인 실행. 격리는:

- 예외는 try/except로 잡아 **Run만 중단**, 앱은 살아남음
- 플러그인끼리는 **모듈명 namespace 분리**
- 플러그인 간 상태 공유 금지 (이벤트 버스 미공유)

비신뢰 환경 대응(멀티프로세싱, 리소스 제한)은 배포 시점 논의.

### 6.2.5 플러그인 스냅샷 (Run 재현성)

Run 실행 시 사용된 플러그인 소스를 Run 디렉토리에 복사:

```
~/.workbench/runs/run_0042/
├── plugins/
│   ├── my_detector.py          ← 원본 복사본 (수정 불가로 둠)
│   └── source_hash.txt         ← SHA256, 무결성 검증
└── ...
```

"Replay Run"이면 원본 경로가 아니라 **이 스냅샷**을 로드.

---

## 6.3 테스팅 전략

### 6.3.1 계층별 테스트 피라미드

```
                   ┌────────────────┐
                   │  E2E UI tests  │  적음 (pytest-qt)
                   ├────────────────┤
                   │   Integration  │  중간
                   ├────────────────┤
                   │     Unit       │  많음
                   ├────────────────┤
                   │   Physics      │  ★ 별도 트랙
                   └────────────────┘
```

### 6.3.2 Unit Test

- 모든 Primitive 함수에 대해 기본 테스트
- `tests/unit/`
- 매 PR 통과 필수
- 실행 시간 목표: < 30초

### 6.3.3 Integration Test

- 파이프라인 한 바퀴 도는 시나리오 기반
- `tests/integration/`
- 실행 시간 목표: < 2분

예시:
```python
def test_pipeline_runs_basic_scenario():
    scenario = ScenarioLoader.load("tests/fixtures/minimal.toml")
    pipeline = create_default_pipeline()
    env = Environment(scenario)
    for frame in range(10):
        result = pipeline.step(0.1, env)
    # 최소 한 프레임에 탐지가 있어야 (GT 타겟 존재)
    assert any(r.detections for r in results)
```

### 6.3.4 Physics Validation Test — **이 프로젝트의 핵심**

별도 트랙으로 운영. `tests/physics/` 디렉토리.

#### 카테고리별 구조

```
tests/physics/
├── conftest.py
├── helpers.py                  ← 공통 유틸 (문헌값 로드, tolerance 체크)
├── golden/                     ← Golden Dataset (저장된 기대값)
│   ├── radar_equation/
│   │   ├── case_001_10km.toml
│   │   ├── case_002_50km.toml
│   │   └── ...
│   ├── fmcw/
│   ├── multipath/
│   └── ...
├── test_radar_equation.py
├── test_fmcw_signal.py
├── test_multipath.py
├── test_clutter.py
├── test_raytracing.py
├── test_rcs.py
├── test_positioner.py
└── test_conservation.py        ← 영역 교차 — 보존 법칙
```

#### 6 종류의 검증 방식

사용자가 선택한 6종류를 매트릭스로:

| 영역 | 문헌 | 보존 | 회귀 | 단위/차원 | 실측 | 극한 |
|---|---|---|---|---|---|---|
| Radar Equation | ✓ MVP | ✓ MVP | ✓ MVP | ✓ | 선택 | ✓ |
| FMCW Signal | ✓ | ✓ | ✓ | ✓ | 선택 | ✓ |
| Multipath | ✓ | ✓ | ✓ | ✓ | 어려움 | ✓ |
| Clutter | ✓ (문헌 경험식) | - | ✓ | ✓ | ✓ 권장 | ✓ |
| Ray Tracing | ✓ (기하) | - | ✓ MVP | ✓ | - | ✓ |
| RCS | 선택 | - | ✓ | ✓ | ✓ 권장 | ✓ |
| Positioner | ✓ (동역학 해석) | ✓ (에너지) | ✓ MVP | ✓ | 선택 | ✓ MVP |
| Sea Dielectric | ✓ | - | ✓ | ✓ | 선택 | ✓ |

**MVP에서 우선 구축할 것**: 각 영역에 대해 **문헌 비교 + 회귀** 최소 2종.
실측/극한은 추후 확장.

#### 개별 테스트 형태 (예시)

```python
# tests/physics/test_radar_equation.py

def test_radar_equation_far_field():
    """자유공간 10km 거리에서 레이더 방정식 해석식과 일치."""
    # 입력
    pt_dbm = 30.0
    gt_db = 30.0
    gr_db = 30.0
    freq_hz = 10.5e9
    rcs_dbsm = 10.0
    range_m = 10_000.0

    # 해석식 (Skolnik 2장)
    wavelength = 3e8 / freq_hz
    pr_dbm = (
        pt_dbm + gt_db + gr_db + rcs_dbsm
        + 20 * log10(wavelength)
        - 30 * log10(4 * pi)
        - 40 * log10(range_m)
    )

    # 구현
    result = compute_rx_power_dbm(
        pt_dbm=pt_dbm, gt_db=gt_db, gr_db=gr_db,
        freq_hz=freq_hz, rcs_dbsm=rcs_dbsm, range_m=range_m,
    )

    assert abs(result - pr_dbm) < 0.01, \
        f"레이더 방정식 편차 {result - pr_dbm:.3f} dB (허용 0.01)"


def test_radar_equation_conservation_energy():
    """입력 전력 증가 대비 출력 전력이 선형 스케일."""
    base = compute_rx_power_dbm(pt_dbm=30.0, ...)
    double = compute_rx_power_dbm(pt_dbm=33.0, ...)  # +3dB = 2x 전력
    assert abs((double - base) - 3.0) < 0.001


def test_radar_equation_regression(golden):
    """지난주 저장된 골든 데이터와 일치."""
    cases = golden.load("radar_equation")
    for case in cases:
        actual = compute_rx_power_dbm(**case.inputs)
        expected = case.expected_outputs["pr_dbm"]
        assert abs(actual - expected) < case.tolerances["pr_dbm"]


def test_radar_equation_range_zero():
    """극한: range=0 입력이 예외로 잡히거나 무한대 처리."""
    with pytest.raises(ValueError):
        compute_rx_power_dbm(..., range_m=0)
```

#### 단위/차원 검사

`pint` 라이브러리 도입 고려 (비용-효과 판단 필요):

```python
import pint
ureg = pint.UnitRegistry()

@ureg.check('[length]', '[frequency]', '[area]')
def radar_cross_section_to_power(r, f, rcs):
    ...
```

→ MVP에서는 **docstring에 단위 명시** + 네이밍 규약 (`_m`, `_hz`, `_dbsm`).
pint 도입은 후속 검토.

### 6.3.5 Golden Dataset 관리

#### 생성 방법

```python
# scripts/generate_goldens.py
cases = [
    GoldenCase(
        domain="radar_equation",
        case_id="case_001_10km",
        description="자유공간 10km 기본 케이스",
        inputs={"pt_dbm": 30, ...},
        expected_outputs=compute_expected_via_literature(...),
        tolerances={"pr_dbm": 0.01},
        references=("Skolnik 2008, Ch.2",),
    ),
    ...
]
for case in cases:
    save_golden(case)
```

#### 갱신 정책

- **물리 모델 수정 시** → 회귀 테스트가 깨질 수 있음
- **의도된 수정**이면 `physics.update_golden` 커맨드로 갱신
- **의도되지 않은 회귀**면 수정 롤백

#### CI 통합

- 매 PR에서 `pytest tests/physics/` 실행
- 실패 시 머지 차단
- Golden 갱신이 같이 온 PR은 리뷰 엄격

### 6.3.6 Physics Gate — 런타임 건전성 체크

DSP 평가 Run 시작 **전에** 수행하는 경량 체크:

```python
class PhysicsGate:
    def check(self, scenario, pipeline) -> list[PhysicsWarning]:
        warnings = []

        # 1. 노이즈 플로어 sanity
        test_spectrum = self._generate_empty_spectrum(scenario)
        expected_noise_dbm = kTB + scenario.fmcw.noise_figure_db
        if abs(test_spectrum.mean() - expected_noise_dbm) > 3.0:
            warnings.append(PhysicsWarning(
                "noise_floor_off",
                f"열잡음 레벨 이상: 기대 {expected_noise_dbm:.1f} dBm, "
                f"측정 {test_spectrum.mean():.1f} dBm",
            ))

        # 2. GT 가시성 sanity
        gt = GroundTruthLoader.load(scenario)
        if sum(t.is_visible for t in gt.targets) == 0:
            warnings.append(PhysicsWarning(
                "no_visible_targets",
                "GT 전체가 비가시 — 시나리오 구성 이상",
            ))

        # 3. 포지셔너 초기 위치가 한계 이내
        if not scenario.radar_site.initial_valid():
            warnings.append(...)

        return warnings
```

MVP에서 구현할 체크: 노이즈 플로어 / GT 가시성 / 포지셔너 한계 3종 정도.

### 6.3.6a Plugin 격리 검증 — GT Isolation & Command Lineage (v0.14 신설)

**동기**: DSP Plugin이 GT를 우회 접근하거나, 누군가 Tracker를 건너뛰고 포지셔너에
직접 명령을 보내면 시뮬 결과는 cheating으로 오염됨. 이를 세 단계로 방어:

#### Level 3-1: Plugin 정적 스캔 (Plugin 로드 시 실행)

```python
FORBIDDEN_SYMBOLS = [
    # GT 관련 타입·함수
    "GroundTruth", "GTLoader", "GTTarget",
    "ground_truth", "true_range", "true_az", "true_el", "true_velocity",
    # Primary 정보 (DSP Plugin은 Primary가 누군지 몰라야)
    "primary_target_id",
]

SUSPICIOUS_FILE_PATTERNS = [
    r"scenarios/.*\.csv",               # 시나리오 파일 접근
    r"ground_truth",                    # GT 파일 접근
]

ALLOWED_PLUGIN_LOCAL_PATTERNS = [
    r"^plugins/[^/]+/weights/.*\.npz$",  # 자기 Plugin 폴더의 가중치
    r"^plugins/[^/]+/lookup/.*\.csv$",   # 자기 Plugin 폴더의 참조 테이블
]


def scan_plugin_source(plugin_path: Path) -> list[ScanFinding]:
    """Plugin .py 파일을 AST로 파싱해 의심 패턴 찾기.
    정규식이 아니라 AST를 써야 문자열 안의 단어를 오탐하지 않음.
    """
    source = plugin_path.read_text()
    tree = ast.parse(source)
    findings = []

    # Name 노드로 심볼 참조 찾기 (getattr 등은 다른 handler)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_SYMBOLS:
            findings.append(ScanFinding(
                line=node.lineno, level="error",
                message=f"Forbidden symbol: {node.id}"
            ))
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_SYMBOLS:
            findings.append(...)
        # 파일 접근 패턴
        elif isinstance(node, ast.Call) and _looks_like_file_open(node):
            path_arg = _extract_path_argument(node)
            if path_arg and _matches_suspicious(path_arg):
                findings.append(...)

    return findings
```

**운용 정책**:

| 컨텍스트 | 의심 발견 시 동작 |
|---|---|
| Plugin Manager에서 로드 | **경고** 배너, 사용자가 "알고 쓰겠다" 확인 시 진행 |
| 공식 Compare Run | **거부** — 메트릭 비교의 무결성을 위해 |
| CI 테스트 | **거부** |

#### Level 3-2: Command Lineage 검증 (Run 후 자동 실행)

모든 `PositionerCommand`의 출처가 합법인지 사후 검증.

```python
@dataclass(frozen=True)
class CommandLineageReport:
    total_commands: int
    tracker_commands: int
    manual_commands: int
    scan_commands: int
    violations: list[LineageViolation]


def validate_command_lineage(trace: Trace) -> CommandLineageReport:
    violations = []
    for cmd in trace.positioner_commands:
        if cmd.source == CommandSource.TRACKER:
            # 해당 프레임의 Tracker 출력에 source_track_id가 실제 있어야 함
            tracker_out = trace.get_tracker_output(cmd.source_frame_id)
            if not any(t.track_id == cmd.source_track_id for t in tracker_out):
                violations.append(LineageViolation(
                    cmd=cmd,
                    reason=f"Track {cmd.source_track_id} not in Tracker output "
                           f"at frame {cmd.source_frame_id}"
                ))
        elif cmd.source == CommandSource.MANUAL_USER:
            # MANUAL은 사용자 조작 로그와 대조
            if not trace.has_user_input_at(cmd.issued_at_session_t_s):
                violations.append(...)
    return CommandLineageReport(...)
```

Run 결과 UI에 `Lineage: ✓ 127 commands verified` 또는 `Lineage: ⚠ 2 violations` 표시.

#### Level 3-3: GT Contamination Heuristic (MVP+α)

결과 레벨 통계 검사로 의심 사례 플래그.

```python
@dataclass(frozen=True)
class ContaminationReport:
    suspect_score: float                # 0~1, 1에 가까울수록 오염 의심
    signals: list[str]                  # 어떤 단서에서 의심되는지
    recommendation: str                 # "clean" / "review" / "rerun_fresh"


def check_gt_contamination(trace: Trace, gt: GroundTruth) -> ContaminationReport:
    signals = []
    score = 0.0

    # 1. 너무 완벽한 추적
    if trace.metrics.track_continuity > 0.999 and scenario.has_crossing:
        signals.append("Continuity too high (1.000) for crossing scenario")
        score += 0.3

    # 2. RMSE가 노이즈 플로어보다 작음 (물리적으로 불가능)
    if trace.metrics.range_rmse_m < theoretical_range_resolution / 10:
        signals.append("RMSE below theoretical resolution limit")
        score += 0.5

    # 3. Detection 위치가 GT와 bit-identical
    if _detection_matches_gt_exactly(trace.detections, gt.targets):
        signals.append("Detections bit-identical to GT")
        score += 0.8

    # 4. 다른 휴리스틱들 ...

    return ContaminationReport(suspect_score=score, signals=signals, ...)
```

MVP에선 score 표시만, MVP+α에서 자동 경고/차단 정책.

#### 왜 이 3단계로

- Level 3-1 **사전 차단** — 실수 방지 (가장 흔한 오염 경로)
- Level 3-2 **런 중 발행 검증** — 타입이 뚫린 경우 포착
- Level 3-3 **결과 분석** — 통계적 이상 포착

셋 다 완벽하지 않지만 **조합하면 상당히 강한 방어선**. 완전한 격리(Level 4-5)는 DX와 성능
비용이 너무 커서 MVP에서는 지양 (03 § 3.5.1d 참조).

### 6.3.7 UI 테스트

`pytest-qt`로:

```python
def test_scenario_explorer_loads_built_in(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    explorer = window.panel("scenario_explorer")
    assert "A_Base" in [item.text() for item in explorer.items()]

    # 더블클릭 시 시나리오 로드 이벤트
    with qtbot.wait_signal(explorer.event_bus, "scenario.loaded"):
        qtbot.mouseDClick(explorer.item("A_Base"), Qt.LeftButton)
```

MVP에서는 **주요 UX 플로우만** E2E 테스트. 과도하게 늘리면 느려짐.

---

## 6.4 로깅 & 진단

### 로그 출력 경로

- 콘솔 (개발 중)
- `~/.workbench/logs/workbench.log` — 회전 로그
- UI 내 **Log Panel** (선택적 도킹)

### 구조화 로깅

```python
log.info("run.started", run_id=run_id, scenario=scenario_name)
```

`structlog` 라이브러리 고려. 파싱/필터 편함.

### 예외 리포팅

앱이 크래시하면:
- 풀 트레이스백을 `crashes/` 디렉토리에 저장
- UI에 "크래시 리포트가 저장됨" 모달

---

## 6.5 라이선스 & 배포 (MVP 관점)

### 의존성 라이선스 매트릭스

| 라이브러리 | 라이선스 | 조건 |
|---|---|---|
| Python | PSF | ✅ 자유 |
| **PySide6** | LGPL-3 | 동적 링크 OK, 수정 시 공개 의무 |
| pyqtgraph | MIT | ✅ |
| **PyVista** (v0.28 채택) | MIT | ✅ — 3D Scene View, VTK 위에 |
| VTK (PyVista 의존) | BSD | ✅ |
| numpy | BSD | ✅ |
| scipy | BSD | ✅ — Hungarian (data_associator), UKF sigma point |
| pandas | BSD | ✅ |
| h5py | BSD | ✅ |
| pint (선택) | BSD | ✅ |
| watchdog | Apache-2 | ✅ |
| structlog | Apache-2 or MIT | ✅ |
| **tomli/tomllib** | MIT (Python 3.11+ 기본) | ✅ — manifest.toml (v0.35) |

**제거할 것**:
- ❌ PyQt5/PyQt6 fallback — GPL 오염 방지

### MVP 라이선스 정책 (v0.35 확정)

- **Workbench 자체 라이선스: Apache 2.0** (v0.35 — Q1-rev closed, 17 § 17.2.1)
- **근거**:
  - DLC 에코시스템 (`.trsim-pkg`) 와 정합 — DLC 작성자가 자유롭게 라이선스 선택 가능
  - 특허 grant 명시적 (MIT 대비)
  - PySide6 (LGPL) + numpy/scipy (BSD) + Apache 2.0 코어 호환
  - TensorFlow·PyTorch 채택, 기업 친화
- **DCO 기여자 동의**: GitHub 표준, CLA 안 채택 (17 § 17.2.2)
- **상세 호환성 매트릭스**: 17 § 17.6 참조

### 배포 형태 (MVP)

MVP는 **소스 배포 + Python 환경 설치** 가정:
```bash
pip install -e .
python -m workbench
```

패키징(PyInstaller, 설치 이미지)은 MVP 후.

---

## 6.6 미래 확장용 인터페이스 (AWG HIL)

MVP 범위 밖이지만 **코드 구조에 자리만 마련**해둠.

### 설계 의도

```python
# src/workbench/domain/signal_sink.py
class SignalSink(Protocol):
    """Receiver 직전 신호의 출력 목적지."""

    def emit(self, samples: numpy.ndarray, metadata: SignalMetadata) -> None:
        ...

# 기본: SIL — 시뮬 내부 RX로 바로
class SILSink:
    def emit(self, samples, metadata):
        self._receiver.receive(samples, metadata)

# 미래: HIL — AWG 스트리밍
class HILSink:
    def emit(self, samples, metadata):
        self._awg_driver.stream(samples, metadata)
        # 실제 ADC는 외부에서 수신 → Workbench는 결과만 받음
```

지금은 `SILSink` 하나만. `hil/` 디렉토리에 설계 문서만 배치.

---

## 6.7 TBD 항목 정리

계획서 전체에서 ⏳ TBD로 남긴 것들 (v0.35 갱신):

| 번호 | 항목 | 상태 | 결정 |
|---|---|---|---|
| ~~T1~~ | ~~플랫폼 (Win/Lin/Mac)~~ | ✅ closed v0.27 | Q-P1: **크로스 플랫폼 (Win/Linux/Mac 모두)** |
| ~~T2~~ | ~~최종 라이선스~~ | ✅ closed v0.35 | Q1-rev: **Apache 2.0** (17 § 17.2.1) |
| ~~T3~~ | ~~VTK 도입 여부~~ | ✅ closed v0.28 | Q-P2: **PyVista (VTK 기반) 채택** (02 § 2.6a) |
| T4 | pint 도입 여부 | ⏳ TBD | 물리 검증 스위트 심화 시 |
| T5 | Trace 저장 포맷 (HDF5 고정? Parquet도?) | ⏳ TBD | Phase 3 중반 |
| T6 | 크래시 리포팅 세부 | ⏳ TBD | MVP 후 |
| T7 | 테마 (다크 외 추가?) | ⏳ TBD | MVP 후 |
| T8 | 커스터마이저블 툴바 범위 | ⏳ TBD | MVP 후 |
| T9 | 자동 핫 리로드 기본값 | ⏳ TBD | MVP 후 사용 피드백 |
| T10 | 시나리오 편집 UI | ⏳ TBD | MVP 후 사용 피드백 |

---

## 6.7a 사용자 물리 plugin — 결정 변경 (v0.40)

> **출처**: 19 § 19.7~19.8 Physics Lab (PL-6, PL-11)
> **권위**: 19 physics_lab

### 이전 결정 (v0.35~v0.39)

**"사용자 물리 plugin 영구 제외"** — Environment Contract 공개 X. DLC 는 DSP·자원만 (Tracker, Detector, Map, Radar, Target, etc.). 물리는 코어 만.

**근거 (당시)**: 잘못된 물리 모델 = 시뮬 전체 신뢰성 망침. 검증 인프라 부재.

### v0.40 변경

**"사용자 물리 plugin 가능, Physics Lab 검증 통과한 것만 시뮬에서 사용"**

근거:
1. **Physics Lab 의 Validation Bench 가 안전망** — 17종 회귀 자동 검증 + 분석 공식 비교 + 시각 검증
2. **PhysicsModelProtocol** (11번째 SDK Plugin Protocol) 정의 — 17 § 17.4.1
3. **Code Pane Read-only default** + Edit toggle — 사용자 인지 명시
4. **검증 통과 plugin 만** `.trsim-pkg` packaging → 시뮬 사용

### Plugin 카테고리

| 카테고리 | 예시 | 검증 reference |
|---|---|---|
| `propagation` | 새 multipath 모델 (e.g., 4-ray) | Two-ray analytic |
| `reflection` | 새 RCS 모델 (e.g., GTD-based) | 분석 공식 + 측정 데이터 |
| `dynamics` | 새 force model (e.g., Magnus effect) | Newton 분석 공식 |
| `atmosphere` | 새 굴절 모델 | ITU-R 표준 |
| `antenna` | 새 빔 패턴 (e.g., array taper) | sinc² / 분석 공식 |

### Plugin 검증 흐름

```
사용자 plugin 작성 (Python 파일 + manifest)
    ↓
Physics Lab > Validation Bench 에서 등록
    ↓
17종 + 추가 회귀 자동 실행
    ↓
분석 공식 비교 (해당 카테고리)
    ↓
사용자 검토 (3D 시각화)
    ↓
✓ PASS → .trsim-pkg packaging 가능
    ↓
시뮬에서 사용 가능
```

### 안전망의 한계 (정직)

- **검증 시나리오 외 영역**: Validation Bench 가 검증 안 한 영역에서는 plugin 의 동작 보장 X
- **외삽 영역**: 학습된 NN plugin (Phase 9.3) 의 학습 영역 밖 사용 시 위험 — 시각화로 명시
- **사용자 책임**: plugin 의 물리적 정확성은 작성자 책임. TRsim 은 검증 도구 제공만

### 영구 제외 조항 (v0.40 유지)

다음은 plugin 으로도 제외:
- 시뮬 코어 변경 (SimulationClock 의 dt 정책 등)
- DSP Pipeline 의 흐름 변경 (Stage 순서)
- 자원 dataclass 의 schema 변경 (Map, Radar 등)

이것들은 plugin 영역 X — 코어 변경은 fork·기여 통한 PR 권장.

상세: [19 physics_lab.md](19_physics_lab.md), [17 § 17.4.1 open_platform](17_open_platform.md).

---

## 6.8 Deferred Physics — 미래 확장 영역

MVP 설계 검토 중 식별된 **의도적으로 미래로 미룬 물리/환경 요소들**. 계획서에 명시적으로
기록해 "왜 안 했는지"가 나중에 헷갈리지 않게 한다. 관련 항목끼리 **Suite로 그루핑**해
미래에 하나의 프로젝트로 다루기 쉽게.

### 6.8.1 MVP에 포함된 것 (참고)

- 함선 자세 (roll/pitch, Sea State 기반 간단 sinusoidal)
- RCS aspect angle 의존성 (SimpleAspectRCSModel, 문헌 기반 코사인 로브)
- 안테나 사이드로브 (sinc² 기본 가정, -13dB)
- 자함 동요 (함선 자세와 동일 모델 재사용)
- 포지셔너 동역학 (AL-4018D ±30°/s)

### 6.8.2 Advanced RF Suite

전파 고급 효과. 현재 MVP는 LOS + 기본 경로손실 + 멀티패스(해면·지면·건물 반사)까지.

- **회절 (diffraction)** — 지형·건물 가장자리 너머로의 신호 감쇠. Knife-edge, GTD 등
- **대기 흡수** — 산소·수증기 감쇠 (X-band X 11 GHz에서 보통 < 0.02 dB/km이라 영향 작음)
- **교차 편파·편파 다양성** — HH/VV/교차편파. Hybrid 레이더 추가 시 연계
- **지구 곡률 정밀화** — 현재 4/3 Earth model, 더 정밀하려면 실제 굴절률 프로파일 사용

### 6.8.3 Weather Suite

- **강우 감쇠** (ITU-R P.838) — X-band에서 40mm/h 시 ~0.4 dB/km
- **안개·구름 감쇠** (ITU-R P.840)
- **대기 굴절·Ducting** — 해상 레이더의 중요 현상 (수평선 너머 탐지, 또는 레이더 사각)
- **3D 시각화** — 비/안개 파티클 렌더링 (VTK/shader)

**Weather와 Sea Clutter Suite는 물리적으로 연결**되어 있어 같이 다루는 것이 자연스럽다
(바람 → 파도 → 클러터, 기상 → 감쇠 → SNR).

### 6.8.4 Sea Clutter Suite

- **K-distribution, Weibull 등 통계 모델**
- **파도 스펙트럼** (Pierson-Moskowitz, JONSWAP)
- **파도 방향 (wind direction)**
- **σ⁰ 문헌 모델** (GIT, TSC, Morchin 등 empirical)
- **주파수·편파 의존성**

### 6.8.5 Interference Suite

- **재머 (jammer)** — 광대역 노이즈, 기만 재머, 딥 쿼리 응답 등
- **다른 레이더와의 상호 간섭** — 동일 대역 사용 시
- **LO 위상잡음** — 실 하드웨어의 위상잡음 모델 (Leeson's formula 등)

### 6.8.6 Target Signature Suite

- **Micro-Doppler** — 함선의 회전 구조물, 헬기 로터 등 미세 도플러
- **Decoy·Flare·Chaff** — 기만용 소형 반사체
- **Corner Reflector 같은 부가 반사체**

### 6.8.7 RF Hardware Suite

실 하드웨어의 비이상성. 현재는 이상적 송수신 가정.

- **ADC 양자화 (bit 수)**
- **I/Q 불균형 (amplitude, phase imbalance)**
- **송신기 비선형성**
- **타이밍 jitter**
- **안테나 채널 간 커플링**
- **포지셔너 엔코더 측정 오차**

### 6.8.8 Hybrid Radar Suite

08 문서에서 미래 레이더 모델로 예약된 것들. Suite 관점으로 다시 묶으면:

- **CW + FMCW Hybrid** — 조직의 기존 다른 제품. RadarModel 추가 필요
- **Pulse / PPI** — 구조적으로 다른 파형
- **편파 다양성 지원** — Suite 간 연계

### 6.8.9 Suite 진입 우선순위 (참고용)

미래 작업이 시작될 때 고려할 순서. 확정 아님.

```
High    : Hybrid Radar Suite (8.8) — 조직의 실제 다음 과제
High    : Target Signature Suite 중 Micro-Doppler — NN 분류에 유용
Medium  : Weather + Sea Clutter 통합 (물리 연결성)
Medium  : Advanced RF Suite 중 회절
Low     : RF Hardware Suite (실제 HIL 시점에 필요)
Low     : Interference Suite (운용 환경 구체화되면)
```

---

## 섹션 상태

- 6.1 Probe/Trace — ✅ (구현 수준까지)
- 6.2 Plugin 시스템 — ✅
- 6.3 Testing — ✅ (핵심 섹션)
- 6.4 Logging — 🟡
- 6.5 License — ✅
- 6.6 HIL — ✅ (자리만)
- 6.7 TBD — ✅
- **6.8 Deferred Physics — ✅ 신규 (v0.11)**

---

👉 다음: [appendix_A_code_audit.md](appendix_A_code_audit.md) — 🚫 DEPRECATED (sim_3d 평가 무효)
👉 또는: [07_nn_integration.md](07_nn_integration.md) — NN 통합
