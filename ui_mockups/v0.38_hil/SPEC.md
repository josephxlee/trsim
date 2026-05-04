# UI Mockup Spec — HIL 통합 (v0.38)

**최종 갱신**: 2026-04-29 (v0.38 + v0.39 통찰 후 HIL UI mockup)
**대상 plan**: 18 § 18.4 (데이터 흐름), § 18.5 (RX L1~L5), § 18.7 (DUTAdapter), § 18.9 (3-way), § 18.16.4 (Lock-step)
**대상 Phase**: Phase 4 UI (Phase 8 시점)

---

## 0. 의도

이 문서는 v0.38 HIL 통합의 UI 설계 spec.
HTML artifact 와 함께 본 docs.

핵심 사용자 흐름:
```
[1] Tools → HIL Connect → DUTAdapter 선택 (TCP/JSON 기본)
[2] DUT 연결 + supported levels 확인 (어떤 L 보낼 수 있나)
[3] Run 시작 → 시뮬 시나리오에서 GT 계산, SIL Pipeline 동작, DUT 응답 수신
[4] 메인 패널: GT/SIL/HIL 3-way 비교 (track / spectrum / paired)
[5] DUT-Bias metric — 펌웨어 vs Python gap 정량화
[6] (Phase 8.1) Lock-step Handshake — frame 단위 sync (Reference Timing 통합)
```

---

## 1. Screen HIL-1 — DUT 연결 셋업

**위치**: Tools 메뉴 → HIL Setup. 모달 dialog 또는 Right Dock 패널.
**파일**: `ui/simulator/hil_panel/dut_setup.py`
**호출**: 처음 HIL 사용 시 또는 다른 DUT 연결 시

### 1.1 레이아웃

```
┌─────────────────────────────────────────────────────────────────┐
│ HIL Setup — DUT Connection                              [×]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Adapter:   ⦿ TCPJsonDUTAdapter (built-in)                      │
│             ○ My-C6678-PCIe-Adapter (DLC: my-c6678 v0.2)        │
│             ○ Mock DUT (test only)                              │
│             [+ Browse plugins...]                                │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Connection (TCPJsonDUTAdapter):                                 │
│    Host:   [ 192.168.1.45        ]   Port: [ 5000 ]             │
│    Timeout: [ 5000 ] ms                                          │
│                                                                  │
│  Supported levels (from DUT):                                    │
│    ☐ L1 ADC raw IQ        (DUT not capable)                     │
│    ☑ L2 FFT spectrum                                            │
│    ☐ L3 Detection peaks                                          │
│    ☑ L4 Paired detections                                        │
│    ☑ L5 Tracks ⭐                                                │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Time Sync Mode:                                                 │
│    ⦿ sim_time   (PC waits for DUT, MVP)                         │
│    ○ real_time  (RT mode, Phase 8.3)                            │
│    ○ reference  (Reference Timing + Lock-step, v0.39) ⭐         │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Connection Status:                                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ● Connected                                               │   │
│  │   192.168.1.45:5000                                       │   │
│  │   Latency probe: 4.2 ms (10 round-trips)                  │   │
│  │   DUT version: "C6678-rcs-monopulse v1.4"                 │   │
│  │   Sync mode: sim_time                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│                          [ Test Connection ]    [ Disconnect ]   │
│                                            [ Apply & Close ]     │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 위젯 목록

| 위젯 | 타입 | 역할 |
|---|---|---|
| Adapter radio | QRadioButton + 동적 list | 설치된 DUTAdapter plugins (built-in + DLC) |
| Browse plugins | QPushButton | DLC plugin 추가 (Plugin Manager 호출) |
| Host / Port | QLineEdit + QSpinBox | 어댑터별 다름 (TCP는 host:port) |
| Timeout | QSpinBox | DUT 응답 대기 ms |
| Levels checkboxes | QCheckBox × 5 | 어떤 RX 레벨 받을지 (DUT 능력 따라) |
| Sync mode radio | QRadioButton × 3 | sim_time / real_time / reference |
| Status box | QGroupBox | 연결 상태·latency probe·DUT 버전 |
| Test Connection | QPushButton | round-trip 측정만 |
| Disconnect | QPushButton | 연결 해제 |
| Apply & Close | QPushButton | 적용 + dialog 닫기 |

### 1.3 인터랙션

- **Adapter 선택** → 어댑터별 connection 영역 갱신 (TCP는 host:port, PCIe는 device path 등)
- **Test Connection** → 10 round-trip ping 측정 → status box 에 latency 표시
- **DUT 능력 자동 감지** → 연결 후 DUT 가 "I support L2, L4, L5" 응답 → checkbox 자동 활성
  - 사용자가 더 끄거나 켤 수 있음 (선택적 송신 — 18 § 18.5)
- **Sync mode = "reference"** → Reference Timing dialog (RT-2) 호출 옵션 표시
- **Disconnect** → 안전한 종료 (현재 Run 진행 중이면 경고)

### 1.4 데이터 흐름

```
사용자 → DUTAdapter Protocol 구현체 인스턴스화
       → connect(config) 호출
       → DUT 가 supported_levels 응답
       → app/hil/dut_session_manager.py 가 connection 유지
```

---

## 2. Screen HIL-2 — GT/SIL/HIL 3-way 비교 패널 (⭐ 핵심)

**위치**: Simulator Workspace 메인. Run 중 Right Dock 또는 Center 영역.
**파일**: `ui/simulator/hil_panel/comparison_view.py`
**가장 자주 보는 화면.**

### 2.1 레이아웃 (Run 중)

```
┌───────────────────────────────────────────────────────────────────────┐
│ GT/SIL/HIL 3-way Comparison        [Live]  Frame: 423          [×]    │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│ ┌──── DUT info ─────┐ ┌──── Time Sync ────┐ ┌──── Sample Status ───┐ │
│ │ TCPJsonDUTAdapter │ │ Mode: sim_time    │ │ Frames: 423/∞        │ │
│ │ 192.168.1.45:5000 │ │ DUT latency: 4 ms │ │ Lock-step: in_sync   │ │
│ │ ● Connected       │ │ Levels: L4,L5     │ │ Loss: 0              │ │
│ └───────────────────┘ └───────────────────┘ └──────────────────────┘ │
│                                                                        │
│ ┌─── Track 비교 (L5) ──────────────────────────────────────────────┐  │
│ │  Range [m]                                                        │  │
│ │  1500 ┤                                                           │  │
│ │  1400 ┤              ╲╲ GT (truth)                                │  │
│ │  1300 ┤             ●●━●●━●●━●●━●●                                │  │
│ │  1200 ┤             ●●━●●━●●━●●━●● ← SIL (Python DSP)            │  │
│ │  1100 ┤            ●●━●●━●●━●●━●● ← HIL (DUT firmware)           │  │
│ │  1000 ┤                                                           │  │
│ │       └──────────────────────────────────────                     │  │
│ │        0    5    10   15   20   25   30  time [s]                 │  │
│ └───────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│ ┌──── Current Frame Detail (frame 423) ──────────────────────────────┐ │
│ │ Metric            GT          SIL          HIL          Bias       │ │
│ │ ─────────────────────────────────────────────────────────────────  │ │
│ │ range [m]      1234.5      1233.2       1230.7       Δ_SIL 1.3   │ │
│ │                                                       Δ_HIL 3.8   │ │
│ │                                                       BIAS  2.5   │ │
│ │ ─────────────────────────────────────────────────────────────────  │ │
│ │ velocity [m/s]   85.2        85.3         85.0       Δ_SIL 0.1   │ │
│ │                                                       Δ_HIL 0.2   │ │
│ │                                                       BIAS  0.3   │ │
│ │ ─────────────────────────────────────────────────────────────────  │ │
│ │ az [deg]         12.3        12.4         12.7       Δ_SIL 0.1   │ │
│ │                                                       Δ_HIL 0.4   │ │
│ │                                                       BIAS  0.3 ⚠ │ │
│ │ ─────────────────────────────────────────────────────────────────  │ │
│ │ el [deg]          5.7         5.7          5.8       Δ_SIL 0.0   │ │
│ │                                                       Δ_HIL 0.1   │ │
│ │                                                       BIAS  0.1   │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ View: [ Range ] [ Velocity ] [ AZ ] [ EL ] [ All ]                    │
│ Show: ☑ GT  ☑ SIL  ☑ HIL                                              │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
```

### 2.2 위젯 목록

| 위젯 | 타입 | 역할 |
|---|---|---|
| DUT info / Time sync / Sample status | QGroupBox × 3 | 상단 상태 패널 |
| Track 비교 plot | pyqtgraph PlotWidget | 시간에 따른 GT/SIL/HIL line plot |
| Current Frame Detail | QTableWidget | frame 단위 GT vs SIL vs HIL 수치 + Δ_SIL, Δ_HIL, BIAS |
| View 버튼 그룹 | QButtonGroup | range / velocity / az / el / all |
| Show checkboxes | QCheckBox × 3 | line plot 의 GT/SIL/HIL 표시 토글 |

### 2.3 색상 의미 (HIL 컬러 시스템)

- **GT**: 흰색·실선 (ground truth, reference)
- **SIL**: 파란색·실선 (Python DSP)
- **HIL**: 주황색·실선 (DUT firmware)
- **Δ_SIL** = `|SIL - GT|` — SIL 정확도
- **Δ_HIL** = `|HIL - GT|` — HIL 정확도
- **BIAS** = `|HIL - SIL|` — DUT-Bias (펌웨어 vs Python gap, ⭐ HIL 만의 metric)
- BIAS 임계값 초과 → 🟠 표시 (Q-HIL4)

### 2.4 인터랙션

- **View 버튼** → plot 의 y축 변경 (range/velocity/az/el)
- **Show toggle** → line plot 의 GT/SIL/HIL 보이기/숨기기
- **timeline 클릭** → 해당 frame 의 Detail 표 갱신
- **BIAS 셀 호버** → tooltip 으로 "펌웨어가 Python 대비 X% 차이"

### 2.5 데이터 출처

- `domain/hil/comparison.py` 의 `HILComparisonResult` (per-frame)
- `app/hil/hil_evaluator.py` 가 매 frame 생성

---

## 3. Screen HIL-3 — Stage Compare (L2/L4/L5, Phase 8.2)

**위치**: Simulator Workspace > tabs (Track 비교 패널과 형제 탭)
**파일**: `ui/simulator/hil_panel/stage_compare.py`
**Phase**: 8.2 (보강) — DUT 가 L2/L4 도 보낼 때 활성

### 3.1 레이아웃

```
┌───────────────────────────────────────────────────────────────────────┐
│ Stage Compare — SIL vs HIL                                     [×]    │
├───────────────────────────────────────────────────────────────────────┤
│ Stage:  [ L2 Spectrum ] [ L4 Paired ] [ L5 Track ]                    │
│                                                                        │
│ ┌───── L2 FFT Spectrum (frame 423, up sweep) ─────────────────────┐   │
│ │  Magnitude [dB]                                                  │   │
│ │   60 ┤                                                           │   │
│ │   40 ┤        ●━━━━━╲                                            │   │
│ │   20 ┤      ╱╳     ╲╲╲                                           │   │
│ │    0 ┤   ╱╱╱        ╲╲╲╲╲╲                                       │   │
│ │  -20 ┤━╱╱╱            ╲╲╲╲╲╲╲                                    │   │
│ │      └───────────────────────────────                            │   │
│ │       0    1k   2k   3k   4k   5k  range bin                     │   │
│ │                                                                  │   │
│ │   ─── SIL spectrum    ─── HIL spectrum  (overlaid)              │   │
│ │   max delta: 0.4 dB at bin 1825 (target peak)                    │   │
│ └──────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│ ┌──── L4 Paired Detection (frame 423) ────────────────────────────┐    │
│ │ Pair ID   Range     Velocity    Az offset    Source             │    │
│ │ ──────────────────────────────────────────────────────────────  │    │
│ │   1       1234.5 m   +85.2 m/s   +0.12°      SIL ─── matched   │    │
│ │   1       1234.7 m   +85.3 m/s   +0.13°      HIL ─── Δ 0.01°   │    │
│ │ ──────────────────────────────────────────────────────────────  │    │
│ │   2       2105.3 m   −34.1 m/s   −2.35°      SIL ─── matched   │    │
│ │   2       2105.8 m   −34.0 m/s   −2.30°      HIL ─── Δ 0.05°   │    │
│ │ ──────────────────────────────────────────────────────────────  │    │
│ │   ─       3500.0 m   +12.8 m/s   +0.45°      SIL only ⚠ missed │    │
│ │ ──────────────────────────────────────────────────────────────  │    │
│ │ Total SIL: 3 pairs, HIL: 2 pairs, Matched: 2, Missed: 1         │    │
│ └─────────────────────────────────────────────────────────────────┘    │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
```

### 3.2 위젯 목록

| 위젯 | 타입 | 역할 |
|---|---|---|
| Stage tab | QTabWidget | L2 / L4 / L5 |
| L2 spectrum plot | pyqtgraph PlotWidget | overlay (SIL + HIL) |
| max delta indicator | QLabel | "0.4 dB at bin X" |
| L4 paired table | QTableWidget | pair-by-pair SIL ↔ HIL match |
| Match status | QLabel | "Total SIL: N, HIL: M, Matched: K, Missed: L" |

### 3.3 인터랙션

- **Stage tab** → L2 / L4 / L5 전환
- **timeline cursor** (HIL-2 와 sync) → 같은 frame 의 stage 데이터
- **Pair row 클릭** → 3D Scene 에서 해당 표적 highlight (옵션)

---

## 4. Screen HIL-4 — DUT-Bias 분석

**위치**: Simulator Workspace > Right Dock 또는 별도 탭
**파일**: `ui/simulator/hil_panel/dut_bias_plot.py`
**시점**: Run 중 + Run 후 분석

### 4.1 레이아웃

```
┌───────────────────────────────────────────────────────────────────────┐
│ DUT-Bias Analysis                                              [×]    │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│ Metric: [ Range ] [ Velocity ] [ Azimuth ] [ Elevation ]              │
│                                                                        │
│ ┌─── DUT-Bias over time (Range, frame 0~423) ───────────────────┐    │
│ │  Bias [m]                                                      │    │
│ │   8 ┤                                                          │    │
│ │   6 ┤             ╱╲              ╱╲                           │    │
│ │   4 ┤        ╱─╱   ╲ ╱╲╱─╲    ╱╱  ╲   ⚠ threshold             │    │
│ │   2 ┤━━╱━━━━╱─────╱──────╲──╱────╲╱──━━━━━━━━━━━━━━━━━━━━━━━  │    │
│ │   0 ┤━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │    │
│ │  -2 ┤                                                          │    │
│ │  -4 ┤                                                          │    │
│ │     └──────────────────────────────────────                   │    │
│ │      0    100   200   300   400  frame                         │    │
│ └────────────────────────────────────────────────────────────────┘    │
│                                                                        │
│ ┌─── Bias Statistics ─────────────────────────────────────────┐       │
│ │   Metric          mean       std       max       p95         │       │
│ │  ────────────────────────────────────────────────────────── │       │
│ │   Range  [m]      2.5       1.4       7.8       5.2         │       │
│ │   Velocity [m/s]  0.3       0.2       1.1       0.7         │       │
│ │   Az [deg]        0.18      0.12      0.51      0.38 ⚠      │       │
│ │   El [deg]        0.07      0.05      0.22      0.16        │       │
│ │  ────────────────────────────────────────────────────────── │       │
│ │   Frames: 423    Threshold violations: 12  (Az exceeded p95) │       │
│ └─────────────────────────────────────────────────────────────┘       │
│                                                                        │
│ ┌─── Bias Distribution (Range) ────────────────────────────┐          │
│ │  count  ▏                                                │          │
│ │  120 ──┤  ████                                           │          │
│ │   90 ──┤  ████████                                       │          │
│ │   60 ──┤   ████████████                                  │          │
│ │   30 ──┤    ████████████████                             │          │
│ │     0 ──┤_____████████████████████___                    │          │
│ │        -2  0   2   4   6   8   10  bias [m]              │          │
│ └──────────────────────────────────────────────────────────┘          │
│                                                                        │
│ Threshold:  [ 5.0 ] m   ⚠ Alert when |bias| > threshold (Q-HIL4)      │
│                                                                        │
│ [ 💾 Export Bias Report ]    [ 🔍 Drill into frames... ]              │
└───────────────────────────────────────────────────────────────────────┘
```

### 4.2 위젯 목록

| 위젯 | 타입 | 역할 |
|---|---|---|
| Metric tab | QButtonGroup | Range / Velocity / AZ / EL |
| Bias over time | pyqtgraph PlotWidget | line plot + threshold line |
| Bias Stats | QTableWidget | mean / std / max / p95 |
| Bias distribution | pyqtgraph histogram | overall 분포 |
| Threshold input | QSpinBox | 사용자 설정 임계값 (Q-HIL4) |
| Export Bias Report | QPushButton | JSON / Markdown |
| Drill into frames | QPushButton | violation frame 만 필터해서 HIL-2 이동 |

### 4.3 인터랙션

- **Metric tab** → plot + dist + stats 모두 갱신
- **Threshold 입력** → plot 의 ⚠ 라인 위치 + violation 카운트 갱신
- **Drill into frames** → HIL-2 가 violation frame 만 필터해서 표시

---

## 5. 화면 간 흐름

```
[Tools 메뉴 → HIL Setup]
       │
       ▼
[Screen HIL-1] DUT 연결 셋업 → connected
       │
       │ Apply & Close
       ▼
[Run 시작]
       │
       ▼
[Screen HIL-2] 3-way Track 비교 (메인, 항상 보이는)
       │  ◄────────  toolbar 의 HIL 버튼으로 토글
       │
       ├→ [Screen HIL-3] Stage Compare (탭 전환, L2/L4)
       │
       └→ [Screen HIL-4] DUT-Bias 분석 (탭 전환)
                            │
                            │ Drill into frames
                            ▼
                       [HIL-2 로 복귀, violation frame 필터]
```

---

## 6. CLI 대응

```bash
# DUT 연결 테스트
trsim hil test-connection --adapter tcp_json --host 192.168.1.45 --port 5000

# Run + HIL 비교
trsim run A_Base.toml --hil --adapter tcp_json --host 192.168.1.45

# DUT-Bias 보고서
trsim hil bias-report runs/2026-04-29-x123/ --metric range --threshold 5.0
```

---

## 7. 영향 받는 plan 영역

| 영역 | 변경 |
|---|---|
| 18 § 18.4 데이터 흐름 | 본 mockup 으로 구체화 |
| 18 § 18.5 RX L1~L5 | DUT supported_levels (HIL-1) 시각화 |
| 18 § 18.7 DUTAdapter | Adapter 선택 UI (HIL-1) |
| 18 § 18.9 GT/SIL/HIL | HIL-2, HIL-4 메인 시각화 |
| 18 § 18.16.4 Lock-step | sync mode = "reference" 옵션 (HIL-1) |

---

## 8. 미결정 사항 (UI 측)

- **HI-U1**: HIL-1 의 "DUT 능력 자동 감지" — handshake protocol 구체 (Q-RT2 와 연계)?
- **HI-U2**: HIL-2 의 timeline 길이 (실 시뮬은 수천 frames — 모두 표시 vs viewport)?
- **HI-U3**: BIAS threshold 자동 학습? 사용자 명시? (Q-HIL4)
- **HI-U4**: HIL-3 L2 spectrum overlay 의 차이 강조 (둘 색 차이? difference line 추가?)
- **HI-U5**: Run 후 분석 모드 — Run 종료 시 자동으로 HIL-4 띄울지?

---

## 9. 다음 (UI mockup 작업)

- 다음 영역: Editor Workspace UI (Screen E-1~5)
  - Scenario / Map / Radar / Targets / Composer 5 Activity
  - 13 editor_workspace.md 본문이 자세히 있음 → 시각화로 보강

---

👉 HTML artifact 동행 (인터랙티브 mockup)
