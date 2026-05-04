# 18. HIL 통합 — Hardware-in-the-Loop 검증 (v0.38 신설, v0.39 Reference Timing 보강)

**최종 갱신**: 2026-04-29 (v0.39 — § 18.16 Reference Timing Mode + § 18.17 Frame Profiler 신설)

**관련 문서**: [02 § 2.6 architecture](02_architecture.md), [03 § 3.2.1m data_model](03_data_model.md), [04 § 4.3 Phase 8 migration](04_migration.md), [17 open_platform](17_open_platform.md)

---

## 18.1 왜 이 문서가 있나

TRsim 의 5번째 차별점 — **Hardware-in-the-Loop (HIL) 통합**. SIL (Software-in-the-Loop) 기반 시뮬에서 한 단계 확장하여, 실제 신호처리 장치 (펌웨어·FPGA·DSP 보드 등) 를 시뮬 루프에 직접 연결하여 검증.

### 시나리오

기존 (SIL):
```
시뮬(가상 표적·환경) → 가상 RF → SIL Pipeline (Python DSP/NN) → Track
```

확장 (HIL):
```
시뮬(가상 표적·환경) → 신호 (RF analog 또는 digital baseband)
                          ↓
                     실제 DUT (Device Under Test, 예: C6678 펌웨어)
                          ↓
                     DUT 출력 (각도/거리/속도 또는 중간 단계 결과)
                          ↓
                     TRsim 이 받아서 평가
                       ↓
                     GT vs SIL vs HIL 3-way 비교
```

### 가치

| 측면 | 가치 |
|---|---|
| 펌웨어 검증 | 실 펌웨어가 시뮬 시나리오에서 어떻게 동작하는지 즉시 평가 |
| 회귀 테스트 | 펌웨어 업데이트 후 회귀 테스트 자동화 |
| 알고리즘 비교 | Python DSP (SIL) ↔ 펌웨어 (HIL) 직접 비교 |
| 시장 차별화 | **MATLAB Phased Array 외 첫 오픈소스 추적 IDE+HIL** |

---

## 18.2 정체성·차별점에서의 위치

v0.38 에서 차별점이 3 + 1 → **4 + 1** 로 확장 (HIL 추가):

1. 추적 알고리즘 검증 IDE
2. DSP ↔ NN 동일 인터페이스 교체·비교
3. 4-error 진단 (Bayes/Training/Dev/Test)
4. **HIL 통합** ⭐ v0.38 신규 — GT/SIL/HIL 3-way 검증
5. ➕ DLC 에코시스템 — `.trsim-pkg`

> **v0.40 갱신 참고**: v0.40 에서 Physics Lab 추가로 차별점 4+1 → 5+1 (Physics Lab 이 5번째). HIL 은 4번째 유지. 19 § 19.2 참조.

> 한 줄 정의 (v0.38):
> **"TRsim은 추적 레이더 알고리즘·자원·시각화를 DLC 패키지로 자유롭게 확장하는 오픈소스 워크벤치 플랫폼이다.
> Apache 2.0 코어에 커뮤니티가 만든 `.trsim-pkg` 를 더해, 어떤 추적 시나리오라도 시뮬·검증·NN 학습이 가능하며,
> HIL 통합으로 실제 펌웨어·하드웨어를 시뮬 루프에 연결한 검증까지 지원한다."** (v0.40 갱신: 01 § 1.1 참조)

---

## 18.3 핵심 설계 결정 (요약)

| ID | 결정 | 출처 |
|---|---|---|
| **HIL-1** | HIL 은 MVP+α Phase 8 (Phase 6 NN, Phase 7 DLC 다음) | v0.38 |
| **HIL-2** | TX (TRsim → DUT): AWG analog + Digital baseband 양쪽 표준 | v0.38 |
| **HIL-3** | RX (DUT → TRsim): L1~L5 모두 형식 표준 + DUT 선택 송신 + MVP는 L5 우선 | v0.38 |
| **HIL-4** | Transport 추상화: DUTAdapter Protocol + 기본 구현 TCP/JSON | v0.38 |
| **HIL-5** | 시간 동기화: 시뮬 시간 + 실시간 둘 다 지원 (사용자 선택) | v0.38 |
| **HIL-6** | 검증 모델: 4-error 유지 + GT/SIL/HIL 3-way 비교 신설 | v0.38 |
| **HIL-7** | DUTAdapter는 SDK Layer 의 10번째 Plugin Protocol | v0.38 |

---

## 18.4 데이터 흐름 (전체)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              TRsim                                      │
│  ┌──────────────────┐                                                   │
│  │   시뮬 (Domain)  │                                                   │
│  │                  │                                                   │
│  │   가상 표적      │                                                   │
│  │   가상 환경      │                                                   │
│  │   가상 안테나    │                                                   │
│  └──────┬───────────┘                                                   │
│         │ TXSignal (시뮬이 합성한 신호)                                 │
│         ▼                                                               │
│  ┌──────────────────────────────────┐    ┌────────────────────────────┐ │
│  │     SignalSink (분기점)          │    │   GT (Ground Truth)        │ │
│  ├──────────────────────────────────┤    │   - 실제 가상 표적 위치    │ │
│  │  분기 1: SILSink → SIL Pipeline  │    │   - 시간별 plate truth     │ │
│  │  분기 2: HILSink → DUTAdapter    │    └────────────┬───────────────┘ │
│  └──────┬───────────────┬───────────┘                 │                 │
│         │               │                             │                 │
│         ▼               ▼                             │                 │
│  ┌──────────────┐  ┌─────────────────────────────┐    │                 │
│  │ SIL Pipeline │  │  DUTAdapter (sdk Protocol)  │    │                 │
│  │ (Python DSP) │  │  ├── TCPJsonDUTAdapter      │    │                 │
│  │ 9 Stage Slot │  │  ├── UDPBinaryDUTAdapter    │    │                 │
│  │              │  │  └── (사용자 작성 DLC)      │    │                 │
│  └──────┬───────┘  └────────────┬────────────────┘    │                 │
│         │                       │                     │                 │
│         │                       ▼                     │                 │
│         │            ┌──────────────────────┐         │                 │
│         │            │   외부 DUT 장치      │         │                 │
│         │            │   (펌웨어/FPGA/DSP)  │         │                 │
│         │            │   ────────────       │         │                 │
│         │            │   처리 후 결과       │         │                 │
│         │            │   L1~L5 중 일부      │         │                 │
│         │            └──────────┬───────────┘         │                 │
│         │                       │ DUTResult           │                 │
│         │                       ▼                     │                 │
│         │            ┌──────────────────────┐         │                 │
│         │            │   DUTAdapter 수신    │         │                 │
│         │            └──────────┬───────────┘         │                 │
│         ▼                       ▼                     ▼                 │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              HILEvaluator — 3-way 비교                           │   │
│  │                                                                  │   │
│  │   GT  ←→  SIL Track  ←→  HIL Track                               │   │
│  │   GT  ←→  SIL Paired ←→  HIL Paired (선택)                       │   │
│  │   SIL Spectrum ←→ HIL Spectrum (선택)                            │   │
│  │                                                                  │   │
│  │   결과 metrics:                                                  │   │
│  │   - SIL 정확도 (GT 대비)                                         │   │
│  │   - HIL 정확도 (GT 대비)                                         │   │
│  │   - DUT-Bias (HIL 과 SIL 의 gap)                                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 18.5 RX 표준 — L1~L5 5 단계

DUT 가 보낼 수 있는 결과를 단계별로 표준화. **모두 선택적** — DUT 가 자기 능력·선호 따라 보냄.

### L1 — ADC raw IQ samples

```python
@dataclass(frozen=True)
class DUTRawIQ:
    """ADC 직후 raw IQ samples. DUT 가 ADC 만 처리한 경우."""
    timestamp_ns: int
    sweep_id: int
    sweep_direction: Literal["up", "down"]
    sample_rate_hz: float
    samples_i: np.ndarray  # int16 또는 float32
    samples_q: np.ndarray
    metadata: dict = field(default_factory=dict)
```

- **언제**: DUT 가 "ADC 보드" 역할만 — 거의 모든 처리는 TRsim 이
- **분량**: 매우 큼 (수십 MB/s) — high-speed transport 필요
- **MVP**: 미지원 (Phase 8.3 확장)

### L2 — FFT spectrum

```python
@dataclass(frozen=True)
class DUTSpectrum:
    """FFT 결과. DUT 가 FFT 까지 처리한 경우."""
    timestamp_ns: int
    sweep_id: int
    sweep_direction: Literal["up", "down"]
    fft_bins_magnitude: np.ndarray   # shape: (N_bins,)
    fft_bins_phase: np.ndarray | None = None
    bin_width_hz: float = 0.0
    metadata: dict = field(default_factory=dict)
```

- **언제**: DUT 의 FFT 정확성 디버깅
- **분량**: 중 (수 KB/sweep, 일반적 100~1000Hz)
- **MVP**: Phase 8.2

### L3 — Detection peaks

```python
@dataclass(frozen=True)
class DUTDetection:
    """CFAR detection 결과."""
    timestamp_ns: int
    sweep_id: int
    sweep_direction: Literal["up", "down"]
    peaks: list[DetectionPeak]
    metadata: dict = field(default_factory=dict)

@dataclass(frozen=True)
class DetectionPeak:
    range_bin: int
    freq_hz: float
    amplitude_db: float
```

- **언제**: CFAR 알고리즘 비교
- **분량**: 작음
- **MVP**: Phase 8.2

### L4 — Paired detections

```python
@dataclass(frozen=True)
class DUTPairedDetection:
    """Up/down 매칭 후 pairing 결과."""
    timestamp_ns: int
    pairs: list[PairedTarget]
    metadata: dict = field(default_factory=dict)

@dataclass(frozen=True)
class PairedTarget:
    pair_id: int
    range_m: float
    velocity_m_s: float
    azimuth_offset_deg: float | None = None
    elevation_offset_deg: float | None = None
    snr_db: float
```

- **언제**: Pairing 알고리즘 검증 (target_pairing.c 같은 핵심 검증 영역)
- **분량**: 작음
- **MVP**: Phase 8.2

### L5 — Tracks (가장 중요, MVP HIL 의 베이스라인)

```python
@dataclass(frozen=True)
class DUTTrack:
    """추적 결과 — DUT 의 최종 출력."""
    timestamp_ns: int
    track_id: int
    range_m: float
    velocity_m_s: float
    azimuth_deg: float
    elevation_deg: float
    frequency_hz: float | None = None
    confidence: float | None = None
    quality_metric: float | None = None
    metadata: dict = field(default_factory=dict)
```

- **언제**: DUT 의 **최종 추적 결과** — 가장 자주, 가장 중요
- **분량**: 매우 작음 (수십 byte)
- **MVP**: ⭐ Phase 8.1 (HIL MVP의 핵심)

---

## 18.6 TX 표준 — 양방향

### TX-A: Digital baseband (MVP)

```python
@dataclass(frozen=True)
class TXSignalDigital:
    """DUT 측 ADC 가 변환할 수 있는 형식. Ethernet/TCP 으로 전송."""
    timestamp_ns: int
    sweep_id: int
    sweep_direction: Literal["up", "down"]
    sample_rate_hz: float
    samples_i: np.ndarray
    samples_q: np.ndarray
```

- 인코딩: numpy → JSON (base64) 또는 binary
- transport: TCP/JSON (기본) 또는 사용자 어댑터

### TX-B: AWG analog (MVP+α)

```python
@dataclass(frozen=True)
class TXSignalAnalog:
    """AWG 가 출력할 baseband signal. AWG SCPI 또는 vendor SDK 통해 전송."""
    timestamp_ns: int
    sweep_id: int
    sample_rate_hz: float
    samples_i: np.ndarray
    samples_q: np.ndarray
    output_voltage_v: float
    output_impedance_ohm: float = 50.0
```

- 인코딩: AWG vendor 별 (Spectrum, Keysight 등)
- transport: SCPI / vendor SDK
- MVP+α 시점에 추가

---

## 18.7 DUTAdapter Protocol (SDK)

10번째 Plugin Protocol. DLC 또는 plugins_builtin/ 에 작성.

```python
# sdk/protocols.py
from typing import Protocol, Iterator
from sdk.dut_messages import DUTResult, TXSignal

class DUTAdapter(Protocol):
    """DUT 통신 추상화. transport 자유."""

    def connect(self, config: dict) -> None:
        """DUT 와 연결 수립. config는 어댑터 specific."""
        ...

    def send_signal(self, signal: TXSignal) -> None:
        """TRsim → DUT 신호 전송."""
        ...

    def receive_results(self) -> Iterator[DUTResult]:
        """DUT → TRsim 결과 수신 (streaming)."""
        ...

    def disconnect(self) -> None:
        """연결 종료."""
        ...

    @property
    def supported_levels(self) -> set[Literal["L1", "L2", "L3", "L4", "L5"]]:
        """이 DUT 가 지원하는 RX 레벨."""
        ...

    @property
    def transport_info(self) -> dict:
        """디버깅용 — transport 정보 (TCP host:port 등)."""
        ...
```

### 기본 구현체: `TCPJsonDUTAdapter`

`plugins_builtin/tcp_json_dut_adapter.py` 에 위치. MVP 의 sample.

```python
class TCPJsonDUTAdapter(DUTAdapter):
    """기본 어댑터 — TCP socket + JSON encoding.

    펌웨어 측은 lwIP·NDK 같은 임베디드 TCP stack 으로 충분.
    JSON 은 펌웨어에서 sprintf 로도 생성 가능.
    """
    def __init__(self, host: str, port: int, supported_levels: set[str]):
        ...
```

### 사용자 어댑터 예시

DLC 또는 plugins_builtin/ 에 추가 가능:
- `UDPBinaryDUTAdapter` — 실시간 streaming
- `gRPCDUTAdapter` — 큰 시스템
- `PCIeDUTAdapter` — C6678 직접 연결 (vendor 라이브러리 필요)
- `CustomBinaryDUTAdapter` — 고성능 specific

---

## 18.8 시간 동기화 (HIL-5)

DUT 는 외부 하드웨어. 처리 latency 와 wall-clock 동기 필요. 3개 모드 지원.

### 모드 1: 시뮬 시간 기준 + timestamp 매칭 (MVP, 추천)

```python
# 시뮬 sim_time 기준
sim_time = 0.000s → TRsim 이 TX signal 합성 (timestamp_ns = sim_time)
                    → DUT 로 전송
sim_time = pause   → DUT 응답 기다림 (real wall-clock)
DUT 응답 도착 (timestamp_ns = 시뮬이 보낸 그것) → TRsim 매칭
sim_time = 0.001s → 다음 sample
```

- **장점**: 재현성, 시뮬이 DUT 처리 완료 보장 후 다음 step
- **단점**: 시뮬 wall-clock 처리 시간 ↑ (DUT 응답 기다림)
- **적합**: 디버깅·검증, MVP

### 모드 2: 실시간 RT 모드 (Phase 8.3)

```python
# wall-clock 기준
wall_time = T0 → TRsim 이 TX signal 합성 + DUT 전송 (timestamp_ns = T0)
wall_time = T0 + Δ → DUT 응답 도착 (TRsim 은 sim_time T0 결과로 매칭)
wall_time = T0 + dt → 다음 sample (DUT 응답 안 와도 진행)
```

- **장점**: 실시간 동작 가능 (live demo), Stream 시뮬
- **단점**: 재현성 ↓, DUT 응답 늦으면 sample loss
- **적합**: 라이브 데모, 실시간 시연

### 모드 3: Reference Timing Mode (v0.39 신설, Phase 8.1)

> **출처**: 사용자 통찰 12 (v0.39) — "테스트 코드의 러닝 시간이 PC 보다 느려질 수 있다 → 시뮬 시간을 보정. Vivado simulation 같은 느낌"
> **자세히**: § 18.16 Reference Timing Mode + Frame Profiler

```
사용자 명시: detector 의 실 보드 target_latency_ms = 50
PC 측정:    detector 실측 latency = 100ms
계산:       scale_factor = 50/100 = 0.5
효과:       시뮬 시간이 wall_clock 의 절반 속도로 흐름
            → 사용자 시각엔 detector 가 50ms 만 걸린 것처럼 동작

frame N 시작:
  HIL 시: Lock-step Handshake (DUT 와 frame 단위 sync barrier)
  SIL 시: 다음 sample 으로 진행 (보정된 시뮬 시간)
```

- **장점**: Vivado simulation 패턴 — 실 보드 timing 처럼 동작, 재현성 ⭐ (frame 단위)
- **단점**: 사용자 입력 필요 (target_latency 또는 scale_factor)
- **적합**: 실 보드 대비 timing 평가, 알고리즘 timing 검증
- **빠른 PC**: sleep 으로 늦춤
- **느린 PC**: scale_factor 로 시뮬 시간 보정
- **HIL Lock-step**: § 18.16.4 참조

### Run Config

```toml
[hil]
sync_mode = "sim_time"  # "sim_time" | "real_time" | "reference"
dut_timeout_ms = 100    # 모드 1: DUT 응답 timeout
expected_dut_latency_ms = 5  # 모드 2: 예상 latency (warning threshold)

[timing]  # 모드 3 활성화 시
mode = "reference"
frame_unit = "fmcw_sweep"  # "fmcw_sweep" | "fft_window" | "auto" | "custom"

[[timing.profiles]]
target_name = "detector"
target_latency_ms = 50.0

[[timing.profiles]]
target_name = "tracker"
scale_factor = 0.5  # 보조 입력 — target 모호 시
```

---

## 18.9 검증 모델 — GT/SIL/HIL 3-way (HIL-6)

### 4-error 진단은 NN 모드의 영역으로 유지

기존 Andrew Ng 패턴 (Bayes/Training/Dev/Test) 은 NN 학습 진단용. HIL 과 별개 차원.

### HIL 검증은 별도 차원: 3-way 비교

```python
@dataclass(frozen=True)
class HILComparisonResult:
    """한 시점·한 표적의 3-way 비교."""
    timestamp_ns: int
    target_id: int

    # GT (실제 가상 표적 위치)
    gt_range_m: float
    gt_velocity_m_s: float
    gt_azimuth_deg: float
    gt_elevation_deg: float

    # SIL (Python DSP 결과)
    sil_track: TrackState | None  # SIL pipeline 의 track

    # HIL (DUT 결과)
    hil_track: DUTTrack | None  # DUT 의 L5 결과

    # 비교 metrics
    sil_error_range_m: float | None      # |sil - gt|
    hil_error_range_m: float | None      # |hil - gt|
    dut_bias_range_m: float | None       # |hil - sil| — 펌웨어 vs Python 차이

    # ... velocity, azimuth, elevation 동일
```

### 시각화 (Simulator Workspace 신규 패널)

`ui/simulator/hil_panel/`:
- **HIL Comparison Panel** — GT/SIL/HIL 3-way 트랙 plot
- **DUT-Bias Plot** — 시간에 따른 펌웨어 vs SIL gap
- **Stage-by-Stage Compare** — L2/L4/L5 각 단계 비교 (능력 따라)

### Phase 5 검증 시나리오 추가 (17 → 17+α)

기존 17종 검증 시나리오에 HIL 추가:
- HIL-A: GT vs HIL Track (펌웨어 정확도)
- HIL-B: SIL vs HIL Track (펌웨어 vs Python — DUT-Bias)
- HIL-C: SIL Spectrum vs HIL Spectrum (FFT 정확도)
- HIL-D: SIL Paired vs HIL Paired (Pairing 정확도)
- HIL-E: 시나리오 전체 회귀 — 펌웨어 업데이트 후 자동 검증

---

## 18.10 디렉토리 구조 (02 § 2.3 영향)

```
src/workbench/
├── domain/
│   └── hil/                              ← 🆕 v0.38
│       ├── dut_messages.py               ← DUTRawIQ/Spectrum/Detection/Paired/Track
│       ├── tx_signal.py                  ← TXSignalDigital/Analog
│       └── comparison.py                 ← HILComparisonResult, evaluator
│
├── sdk/
│   ├── protocols.py                      ← DUTAdapter Protocol 추가 (10번째)
│   └── ...
│
├── plugins_builtin/
│   ├── tcp_json_dut_adapter.py           ← 🆕 기본 sample
│   └── ...
│
├── app/
│   └── hil/                              ← 🆕 v0.38
│       ├── hil_evaluator.py              ← 3-way 비교
│       ├── time_synchronizer.py          ← 시뮬 시간 + 실시간 동기화
│       └── dut_session_manager.py        ← DUT 연결 생애주기
│
├── ui/
│   └── simulator/
│       └── hil_panel/                    ← 🆕 v0.38
│           ├── comparison_view.py        ← GT/SIL/HIL 3-way
│           ├── dut_bias_plot.py
│           └── stage_compare.py
│
└── hil/                                   ← 기존 빈 디렉토리 (v0.35)
                                           v0.38 에서 src/workbench/{domain,app,ui}/hil/ 로 분산
                                           이 위치는 보존 (외부 HIL 도구 연동용)
```

---

## 18.11 Phase 8 구현 순서

### Phase 8.1 — MVP HIL (가장 단순)

목표: TCP/JSON 어댑터 + L5 Track 비교 + GT/SIL/HIL 3-way 시각화 가능.

체크리스트:
- [ ] `domain/hil/dut_messages.py` — L5 dataclass 정의 (DUTTrack)
- [ ] `domain/hil/tx_signal.py` — TXSignalDigital 정의
- [ ] `sdk/protocols.py` 에 DUTAdapter Protocol 추가
- [ ] `plugins_builtin/tcp_json_dut_adapter.py` — 기본 sample 구현
- [ ] `app/hil/hil_evaluator.py` — L5 만 비교
- [ ] `app/hil/time_synchronizer.py` — sim_time 모드만
- [ ] `ui/simulator/hil_panel/comparison_view.py` — 3-way Track plot
- [ ] HIL Run Config (Scenario 측에 hil 섹션 추가)
- [ ] DUT 시뮬레이터 (테스트용 mock — Python 으로 펌웨어 흉내내는 sample)
- [ ] HIL-A 검증 시나리오 (GT vs HIL)

완료 기준: TCP 로 mock DUT 와 통신, GT/SIL/HIL 3-way 비교 가능.

### Phase 8.2 — 보강 (L2/L4 추가)

- [ ] L2 (Spectrum), L4 (Paired) dataclass 추가
- [ ] hil_evaluator 에 stage-by-stage 비교 추가
- [ ] UI 에 stage_compare 패널 추가

### Phase 8.3 — 확장 (L1 + AWG)

- [ ] L1 ADC raw IQ 표준 (high-speed transport)
- [ ] TXSignalAnalog (AWG analog)
- [ ] AWG vendor 어댑터 sample (Spectrum 또는 Keysight)
- [ ] real_time sync mode

---

## 18.12 MVP 범위 (HIL 측면)

### Phase 8.1 (MVP HIL) ✅
- TCP/JSON DUTAdapter
- L5 Track 비교
- sim_time 동기화
- GT/SIL/HIL 3-way 시각화
- Mock DUT (Python 으로 흉내, 테스트용)

### Phase 8.2 (보강) ⏳
- L2 Spectrum / L4 Paired 비교
- Stage-by-stage 시각화

### Phase 8.3 (확장) ⏳
- L1 ADC raw IQ
- AWG analog (Spectrum/Keysight)
- real_time sync mode
- C6678 PCIe 직접 어댑터 (sample)

### MVP+α 외 (의도적 제외)
- 자동 펌웨어 deploy (펌웨어 컴파일·load 자동화)
- DUT discovery (네트워크에서 자동 발견)
- 실시간 fault injection (RF noise 주입)
- 다중 DUT 동시 비교 (DUT A vs DUT B vs SIL)

---

## 18.13 영향 문서

| 문서 | 갱신 내용 |
|---|---|
| 00 README | 핵심 방향 표 + 차별점 5개 |
| 01 vision_scope | 한 줄 정의·차별점·MVP+α |
| 02 architecture | § 2.6 SignalSink → SignalSink + DUTAdapter, 디렉토리 hil/ 구체화 |
| 03 data_model | § 3.2.1m DUTAdapter Manifest 신규 |
| 04 migration | Phase 8 신설 |
| 17 open_platform | SDK Layer Protocol 9 → 10 (DUTAdapter 추가) |
| AGENT_GUIDE | 5번째 차별점 |
| TRsim_README | 한 줄 정의·차별점 |
| COWORK_HANDOFF | HIL 항목 |
| ROADMAP | 6단계 → 7단계 (Phase 8 추가) |
| OPEN_QUESTIONS | Q-HIL1~N 신규 카테고리 |
| SESSION_SUMMARY | v0.38 행 + 통찰 11번 |
| appendix_B | HIL 신규 용어 |

---

## 18.14 Open Questions (Q-HIL 시리즈)

### Q-HIL1. 첫 sample 어댑터는 TCP/JSON 외 추가 필요?
- 출처: 18 § 18.7
- 결정 시점: Phase 8.1 후
- 현재 가정: TCP/JSON 만, 사용자 어댑터 작성 가이드 충실

### Q-HIL2. C6678 PCIe 어댑터 sample 우선순위
- 출처: 18 § 18.10
- 결정 시점: Phase 8.3 또는 사용자 요청 시
- 현재 가정: C6678 어댑터는 사용자(너)의 펌웨어 환경에 맞게 별도 작성

### Q-HIL3. AWG vendor 우선순위 (Spectrum / Keysight / Rohde&Schwarz)
- 출처: 18 § 18.6 TX-B
- 결정 시점: Phase 8.3
- 현재 가정: 미결정 — Phase 8.3 시점에 보유 장비 따라

### Q-HIL4. DUT-Bias 임계값 자동 알람
- 출처: 18 § 18.9
- 결정 시점: Phase 8.1 후 운영 경험 후
- 현재 가정: MVP는 시각화만, 임계값 알람 후속

### Q-HIL5. 다중 DUT 동시 비교 (DUT A vs DUT B vs SIL)
- 출처: 18 § 18.12 MVP+α 외
- 결정 시점: 산업 사용자 요청 시
- 현재 가정: 단일 DUT 만, 다중은 미래

### Q-HIL6. 펌웨어 자동 deploy / DUT discovery
- 출처: 18 § 18.12 MVP+α 외
- 결정 시점: 산업 deployment 시점
- 현재 가정: 수동 셋업 (사용자가 펌웨어 load 후 IP 알려줌)

### Q-HIL7. real_time sync mode 의 sample loss 정책
- 출처: 18 § 18.8 모드 2
- 결정 시점: Phase 8.3
- 현재 가정: warning + skip, sample loss 통계 기록

### Q-RT1. Frame 정의 — 자동 추론 vs 사용자 명시

- **출처**: 18 § 18.16.2
- **결정 시점**: Phase 3 SIL Reference Timing 구현 시
- **현재 가정**: 둘 다 지원 — Scenario `frame_unit` 명시 우선, 없으면 자동 추론 (테스트 코드 최종 결론(AZ/EL 출력) 시점)

### Q-RT2. Lock-step Handshake protocol (frame ID 매칭)

- **출처**: 18 § 18.16.4
- **결정 시점**: Phase 8.1 HIL 구현 시
- **현재 가정**: frame_id (uint64) + ack_required + timeout 표준. DUT 측 구현 가이드 별도

### Q-RT3. 빠른 PC 의 sleep 정밀도 (OS jitter)

- **출처**: 18 § 18.16.1
- **결정 시점**: Phase 3 측정 후
- **현재 가정**: time.sleep() 충분 (ms 단위). 더 정밀 필요 시 spin-wait 옵션

### Q-RT4. Stage 단위 측정 overhead

- **출처**: 18 § 18.16.3, 18 § 18.17
- **결정 시점**: Phase 3 PerformanceClock 구현 시
- **현재 가정**: 측정 모드 toggle — 평소 off, profiling 시 on. perf_counter_ns ~200ns/call

### Q-RT5. DUT-Bias 와 Reference Timing 결합

- **출처**: 18 § 18.9 + 18 § 18.16
- **결정 시점**: Phase 8.1 후 운영 경험
- **현재 가정**: 별개 metric — DUT-Bias 는 "결과 정확도", Reference Timing 은 "처리 시간". 같이 표시

### Q-RT6. Profile 미명시 stage 의 default 동작

- **출처**: 18 § 18.16.3
- **결정 시점**: Phase 3 구현 시
- **현재 가정**: scale_factor=1.0 (보정 안 함, wall_clock 그대로)

### Q-RT7. Frame Profiler warmup 프레임 수

- **출처**: 18 § 18.17
- **결정 시점**: Phase 3 후 측정 안정성 확인
- **현재 가정**: 첫 10 프레임 warmup discard, 실제 측정은 11번째부터 (JIT/cache 효과 제외)

### Q-RT8. Frame Profiler 결과의 재현성 (PC 부하 변동)

- **출처**: 18 § 18.17
- **결정 시점**: Phase 3 후 운영 경험
- **현재 가정**: 동일 PC·동일 부하에서 percentile 일관성 명시. 결과에 measurement context (CPU·load) 기록

---

## 18.16 Reference Timing Mode (v0.39 신설)

> **출처**: 사용자 통찰 12 (v0.39) — "테스트 코드의 러닝 시간이 PC 보다 느려질 수 있다 → 시뮬 시간을 보정. Vivado simulation 같은 느낌"

### 18.16.1 동기·시나리오

추적 레이더 신호처리 코드 (이하 "테스트 코드") 를 시뮬 PC 에서 돌릴 때, **PC 가 실 보드보다 느릴 수 있다**. 예:
- 사용자 가정 (실 C6678 보드): detector 는 50ms 에 동작
- 시뮬 PC 측정: detector 가 100ms 걸림 (Python overhead, 비최적)
- 시뮬 시간이 wall_clock 그대로 흐르면 → 시뮬 결과가 실 보드 timing 과 어긋남

**Reference Timing Mode**: 시뮬 시간을 **사용자 명시 target_latency 기준** 으로 보정.
- PC가 더 느리면 시뮬 시간을 그 비율로 느리게 (위 예: 0.5x)
- PC가 더 빠르면 sleep 으로 늦춤 (Vivado simulation 패턴)

**Vivado simulation 비교**: HDL 시뮬레이터가 clock cycle 정확도로 동작 — wall_clock 무관. 우리는 그 패턴을 추적 레이더 IDE 에 적용.

### 18.16.2 frame 정의 (Q-RT1)

Reference Timing 의 단위는 **frame**. 한 frame 내에서는 PC 자유 페이스, frame 경계에서 보정·sync.

#### 사용자 명시 (기본)

```toml
[timing]
frame_unit = "fmcw_sweep"  # 또는 "fft_window" | "custom"
```

옵션:
- **fmcw_sweep**: FMCW Triangle 의 한 sweep (up + down)
- **fft_window**: 한 FFT window 단위
- **custom**: 사용자가 별도 frame boundary 명시

#### 자동 추론 (D3 답변)

`frame_unit = "auto"` 시 시뮬이 자동 frame 경계 추론:
- 테스트 코드의 **최종 결론** (표적 AZ/EL 출력) 이 나올 때마다 frame 갱신
- 즉 "한 frame = 한 표적 추적 결과 cycle"
- 별도 명시 없어도 동작

자동 추론 구현:
- TrackOutputProbe 의 출력 시점 감지
- 감지 시 frame_id 증가 + 측정 latency 누적·보정

### 18.16.3 측정·보정 로직 (Q3=a,b)

#### Stage 단위 + Pipeline 전체 (둘 다)

사용자가 시나리오에 명시한 profile 단위로 측정:

```toml
[[timing.profiles]]
target_name = "detector"           # Stage 단위
target_latency_ms = 50.0

[[timing.profiles]]
target_name = "tracker"
target_latency_ms = 30.0

[[timing.profiles]]
target_name = "pipeline_total"     # Pipeline 전체
target_latency_ms = 100.0
```

#### PerformanceClock 동작 (사용자 의도 의사코드)

```python
# Phase 3 구현
class PerformanceClock:
    """SimulationClock 의 wall_clock ↔ reference_time 보정 컴포넌트."""

    def on_stage_start(self, stage_name: str):
        self._stage_start_ns[stage_name] = time.perf_counter_ns()

    def on_stage_end(self, stage_name: str):
        measured_ns = time.perf_counter_ns() - self._stage_start_ns[stage_name]
        profile = self._profiles.get(stage_name)
        if profile:
            self._apply_correction(stage_name, measured_ns, profile)

    def _apply_correction(self, stage_name, measured_ns, profile):
        target_ns = profile.target_latency_ms * 1_000_000
        if measured_ns < target_ns:
            # PC 가 빠름 — sleep 으로 늦춤 (Q4=a)
            sleep_ns = target_ns - measured_ns
            time.sleep(sleep_ns / 1_000_000_000)
            self._sim_advance_ns(target_ns)  # 시뮬 시간은 target 만큼
        else:
            # PC 가 느림 — 시뮬 시간을 비율로
            # measured > target 이면 시뮬 시간이 더 많이 흐른 것처럼
            # 단 결과 sample 은 target 단위로 매핑
            self._sim_advance_ns(target_ns)
            # wall_clock 은 measured_ns 만큼 사용됨, 사용자에게 scale_factor 표시
```

#### scale_factor 보조 입력 (Q2=c)

target 모호한 경우 (정수 배수 아님 등):

```toml
[[timing.profiles]]
target_name = "tracker"
scale_factor = 0.5  # measured 의 0.5배가 reference time
# 즉 PC 100ms → reference 50ms
```

### 18.16.4 Lock-step Handshake (HIL 측, D2=c)

HIL 모드에서 Reference Timing 활성화 시 frame 단위 sync barrier.

#### 구조

```
Frame N 시작 (sync barrier):
  PC: signal 합성 + DUT로 전송
  DUT: signal 받기 + 처리 + 결과 보내기
  PC: 결과 수신 + 비교 + scale_factor 반영
  → 둘 다 done → barrier 통과
Frame N+1 (sync barrier): ...
```

#### Protocol (Q-RT2)

```python
# DUTAdapter Protocol 에 sync 메서드 추가 (v0.39, 17 SDK 갱신)
class DUTAdapter(Protocol):
    # 기존 (v0.38)
    def send_signal(self, signal: TXSignal) -> None: ...
    def receive_results(self) -> Iterator[DUTResult]: ...

    # 신규 (v0.39)
    def sync_frame_start(self, frame_id: int) -> None:
        """Frame 시작 — DUT 에 frame_id 알리고 ready 대기."""
        ...

    def sync_frame_end(self, frame_id: int, timeout_ms: float) -> bool:
        """Frame 끝 — DUT 의 done ack 대기. timeout 시 False."""
        ...
```

DUT 측 구현 가이드:
- frame_id 매칭 (PC 보낸 ID 와 일치)
- frame_start 받으면 처리 시작
- 결과 송신 후 frame_end ack
- 누적 frame_id 불일치 시 desync detection

### 18.16.5 재현성 (Q5)

**프레임 단위 결정성**:
- 같은 시드 + 같은 input + 같은 frame 정의 → 같은 결과
- wall_clock latency 변동은 결과에 영향 X
- scale_factor 가 결과를 바꾸지 않음 — 진행 속도만 바꿈

**보장 조건**:
- frame 경계에서 시뮬 state snapshot
- frame 내 stage 실행 순서 결정적
- frame 끝에서 보정 적용 (scale_factor 또는 sleep)

### 18.16.6 UI 시각화 (Phase 4)

- **현재 시뮬 속도 표시**: 상단 toolbar 에 "0.57x" indicator (scale_factor)
- **Stage 별 timing breakdown 패널**: 매 frame 의 stage timing 막대
- **Reference vs Measured 그래프**: 시간에 따른 wall ↔ ref 비율
- **Lock-step 상태**: HIL 모드 시 sync barrier 상태 (in_sync / pc_waiting / dut_waiting)

### 18.16.7 Phase 위치 (D4=D)

| Phase | Reference Timing 영역 |
|---|---|
| **Phase 2 (Domain)** | StageTimingProfile dataclass 정의 (03 § 3.2.1n) |
| **Phase 3 (App)** | PerformanceClock 구현, Frame Boundary Detector, StageTimingProbe |
| **Phase 4 (UI)** | Timing breakdown 패널, scale indicator |
| **Phase 5 (검증)** | Reference Timing 검증 시나리오 |
| **Phase 8.1 (HIL MVP)** | Lock-step Handshake, DUTAdapter sync 메서드 |

**즉 Reference Timing 자체는 MVP 기능 (SIL), HIL Lock-step 만 Phase 8.**

### 18.16.8 차별점 위치 (D1=c)

이번 추가는 **차별점 4+1 유지** — Reference Timing 은 당연한 기능 (Vivado simulation 같은 도구의 표준 패턴), 별도 차별점 추가 X. 기존 차별점 (HIL 통합) 의 검증 깊이를 보강하는 기능.

---

## 18.17 Frame Profiler (v0.39 신설)

> **출처**: 사용자 통찰 12-1 (v0.39) — "테스트 코드를 미리 동작해서 한 프레임 당 걸리는 시간을 사용자에게 알려주는 기능"

Reference Timing 의 짝꿍 기능. 사용자가 target_latency_ms 입력 전에 PC 측 실측치 알 수 있게 함.

### 18.17.1 Vivado timing report 와의 비교

Vivado 는 합성 후 timing report 자동 생성 → 사용자가 보고 동작 가능 여부 판단.
Frame Profiler 는 시뮬 실행 전·중에 stage·pipeline 별 timing 측정 → 사용자가 보고 Reference Timing target 입력 가능.

### 18.17.2 측정 시점·방식 (Q1=a+c)

#### (a) 명시적 명령

```bash
trsim profile scenarios/A_Base.toml --frames 100 --output profile.json
```

또는 UI 에서 "Profile" 버튼:
- 100 프레임 (사용자 입력) 측정
- warmup 첫 10 frames discard (Q-RT7)
- 통계 계산 + 표시

#### (c) 백그라운드 지속

Run 중 매 frame 의 latency 누적:
- 평균·percentile 실시간 갱신
- 시뮬 toolbar 에 평균 latency 표시
- 옵션: "Live profile" toggle

### 18.17.3 측정 대상 (Q2=c) — Stage + Pipeline

```python
@dataclass(frozen=True)
class FrameTimingReport:
    """Frame Profiler 의 결과."""
    scenario_name: str
    profile_frames: int
    warmup_frames: int  # discarded
    measurement_context: dict  # CPU info, OS, load (Q-RT8)
    stage_stats: dict[str, StageTimingStat]  # stage_name → 통계
    pipeline_stat: StageTimingStat  # pipeline_total

@dataclass(frozen=True)
class StageTimingStat:
    stage_name: str
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    sample_count: int
```

### 18.17.4 통계 (Q3=b)

평균 + percentile (50/95/99) — 표준 profiler 패턴.

표시 예:
```
Frame Profiler Report (100 frames, 10 warmup discarded)

Stage         avg     p50     p95     p99     min     max
detector      87ms    85ms    110ms   125ms   78ms    140ms
pairing       12ms    11ms    15ms    18ms    9ms     22ms
tracker       23ms    22ms    28ms    35ms    19ms    42ms
─────────────────────────────────────────────────────────
pipeline_total 125ms  120ms   148ms   175ms   115ms   195ms
```

### 18.17.5 측정 모드 toggle (Q4)

평소엔 측정 off (overhead 회피, Q-RT4):

```toml
[profiling]
mode = "off"  # "off" | "explicit" | "live"
warmup_frames = 10
target_frames = 100  # 명시적 프로파일링 시
```

- **off**: 측정 안 함 (overhead 0)
- **explicit**: `trsim profile` 명령 시만 활성
- **live**: Run 동안 백그라운드 누적

### 18.17.6 결과 표시 (Q5=d) — 모두

#### UI 패널

`ui/simulator/profiler_panel/`:
- Stage 별 timing 표 (위 예시)
- 시간에 따른 latency 분포 그래프
- "Set Reference Timing" 버튼 → 측정값 기반 target 입력 dialog

#### CLI

```bash
trsim profile <scenario> --frames 100 --output profile.json
trsim profile <scenario> --stage detector --frames 200
trsim profile <scenario> --live  # 백그라운드 모드
```

#### 보고서 파일

JSON / Markdown 출력. 재현·공유 가능:
```json
{
  "scenario": "A_Base.toml",
  "frames": 100,
  "warmup": 10,
  "context": {"cpu": "Intel i9-13900K", "os": "Ubuntu 24.04"},
  "stages": {
    "detector": {"avg_ms": 87.2, "p95_ms": 110.5, ...},
    ...
  }
}
```

### 18.17.7 Reference Timing 과의 짝꿍 흐름

```
1. 사용자가 시나리오 만듦
2. "Profile" 버튼 클릭 → 100 프레임 측정
3. 결과 표시:
     detector  avg=87ms  p95=110ms  p99=125ms
     pairing   avg=12ms  p95=15ms   p99=18ms
     tracker   avg=23ms  p95=28ms   p99=35ms
     pipeline  avg=125ms p95=148ms  p99=175ms
4. "Set Reference Timing" 버튼 → 사용자 입력 dialog
     - "detector 의 실 보드 target latency 입력" → 50ms
     - 자동으로 scale_factor = 50/87 = 0.57 계산
5. Run → Reference Timing Mode 동작
     - 시뮬이 실 보드 timing 처럼 동작 (0.57x 속도)
```

### 18.17.8 Phase 위치

| Phase | Frame Profiler 영역 |
|---|---|
| **Phase 2 (Domain)** | FrameTimingReport / StageTimingStat dataclass (03 § 3.2.1n) |
| **Phase 3 (App)** | StageTimingProbe + 통계 계산 + 백그라운드 누적 |
| **Phase 4 (UI)** | Profiler 패널, "Profile" 버튼, "Set Reference Timing" 통합 |
| **Phase 5 (검증)** | Frame Profiler 결과 재현성 검증 |

**MVP 기능** — Reference Timing 과 같이 Phase 2~4 분산.

---

## 18.15 한 문장 요약

**TRsim 의 5번째 차별점 — HIL 통합으로 실제 펌웨어·하드웨어를 시뮬 루프에 직접 연결, GT/SIL/HIL 3-way 비교로 펌웨어 정확도와 DUT-Bias (펌웨어 vs Python DSP gap) 를 정량화. DUTAdapter Protocol (SDK 10번째) + 기본 TCP/JSON 어댑터로 단순 시작, L1~L5 5단계 RX 표준 + 양방향 TX (digital + AWG) 로 확장 여지 보존. v0.39: Reference Timing Mode (Vivado simulation 패턴) + Frame Profiler 추가로 실 보드 timing 평가 가능. 오픈소스 추적 IDE+HIL+Reference Timing 의 첫 사례.**

---

## 섹션 상태

- 18.1 동기·시나리오 — ✅
- 18.2 정체성 위치 — ✅
- 18.3 핵심 결정 — ✅
- 18.4 데이터 흐름 — ✅
- 18.5 RX 표준 L1~L5 — ✅
- 18.6 TX 표준 — ✅
- 18.7 DUTAdapter Protocol — ✅
- 18.8 시간 동기화 (3 모드) — ✅ (v0.39 모드 3 추가)
- 18.9 GT/SIL/HIL 3-way — ✅
- 18.10 디렉토리 구조 — ✅
- 18.11 Phase 8 구현 순서 — ✅
- 18.12 MVP 범위 — ✅
- 18.13 영향 문서 — ✅
- 18.14 Open Questions (Q-HIL + Q-RT) — ✅
- 18.15 요약 — ✅
- **18.16 Reference Timing Mode** — ✅ (v0.39 신설)
- **18.17 Frame Profiler** — ✅ (v0.39 신설)

---

👉 다음: [00_README.md](00_README.md) (계획서 진입점)
👉 이전: [17_open_platform.md](17_open_platform.md)
