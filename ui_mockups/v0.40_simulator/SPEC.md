# UI Mockup Spec — Simulator Workspace (v0.40)

**최종 갱신**: 2026-05-02
**대상 plan**: 01 § 1.1 (정체성), 10 workspaces (3 Workspace 중 본체), 05 ui_ux, 02 § 2.2 블록도, 03 데이터 모델, 18 § 18.16 (Reference Timing 시각화 통합)
**대상 Phase**: Phase 4 (UI 기본) → Phase 5+ (베이스라인) → Phase 9 (Physics Lab 통합 시각화)

---

## 0. 의도

Simulator Workspace 는 **TRsim 의 본체** — 자원이 아니라 **시뮬 실행·관찰·진단**의 자리.
Editor 가 "무엇을 만들 것인가", Physics Lab 이 "물리가 정확한가" 라면, Simulator 는 **"만들어진 걸로 무엇을 관찰할까"**.

차별점 5+1 중 **3개가 여기서 보임**:
- **차별점 1 추적 IDE** — Pipeline + Stage Slot + Plugin
- **차별점 2 DSP↔NN 동일 인터페이스** — toggle 로 Pipeline 의 어느 Stage 든 NN 으로 교체
- **차별점 3 4-error 진단** — Andrew Ng 패턴 (Bayes/Training/Dev/Test)

(차별점 4 HIL, 5 Physics Lab 은 별도 영역에서 다룸)

핵심 사용자 흐름:
```
[1] Workspace = Simulator 선택
[2] Scenario 로드 (Editor 에서 만든 .toml — Maritime 함정 시나리오)
[3] Pipeline 의 Stage Slot 에 Plugin 꽂기 (Detector / Tracker / Predictor 등)
[4] Mode 선택: ⦿ DSP / ○ NN
[5] Run ▶ — 시뮬 진행
[6] 화면 관찰: 3D Map (함정·표적·빔) + Track 2D plot + DSP Pipeline + 메트릭 + 4-error 요약
[7] 결과 분석: 4-error 드릴 / Probe 탐색 / Run 비교
```

---

## 1. Screen SIM-1 — Main Layout ⭐ 핵심

**가장 자주 보는 화면.** 정체성의 본체.
**파일**: `ui/simulator/simulator_workspace.py`
**참조**: 02 § 2.2, 05 ui_ux

### 1.1 시나리오 — Maritime (Q-T2=a)

함정 위 추적 레이더 + 해상 표적. TRsim 의 정체성을 가장 잘 보여주는 시나리오.

```
시나리오: "Maritime · Anti-ship missile defense"

자원:
- Map: 동해 일부 해상 (Bathymetry + 해안선) — 30 km × 30 km
- Radar: 함정 X-band FMCW (9.4 GHz, 100 MHz BW)
- Platform: 구축함 (Sea State 4, roll ±5°, pitch ±3°)
- Targets:
  · Primary: 미사일 1발 (POWERED_FLIGHT, 500 m/s, range 12 km, descending)
  · Decoys: 함선 3척 (BALLISTIC, low velocity)
  · Clutter: 해면 클러터 (sea state 4)

추적 Goal:
- Primary missile 추적 안정성 검증
- 클러터 + decoy 환경에서 GNN data association
- Multi-scatterer ExtendedTarget RCS + glint 영향
- Sea bounce multipath (two-ray)
```

### 1.2 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Title bar: TRsim Workbench · Simulator                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Workspace tabs: 📐 Editor | ▶ Simulator [active] | 🔬 Physics Lab            │
├─────────────────────────────────────────────────────────────────────────────┤
│ Toolbar: [📂 Open] [💾 Save] | [▶ Run] [⏸] [⏹] | Mode: ⦿DSP ○NN | [📊] [⚠] │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tab: [ Maritime · Missile Defense * ] [ + ]                                  │
├─────────┬───────────────────────────────────┬────────────────┬──────────────┤
│         │                                   │                │              │
│ Pipeline│   3D Map (Maritime scene)         │  Tracks 2D     │ Run Manager  │
│ ──────  │                                   │   B-scope      │ (side panel) │
│ ☑ FMCW  │      ⛵ ship   ⛵ ship             │   Range vs     │              │
│ ☑ FFT   │           ╲╱                      │   Bearing      │ Current Run  │
│ ☑ CFAR  │  📡(RX) ━╱━━━╱━━━━━╱╮             │  ┌─────────┐   │ ▶ Run #042   │
│ ☑ Pair  │   │     ╲ ╱   ╱   ╲ │             │  │   ╱     │   │ ─────────── │
│ ☑ Track │   ▼      ╲   ╱     ╲│             │  │ ╱       │   │ t = 8.42s   │
│ ☑ Pred  │    🚢   target ●     │             │  │  ●      │   │ progress    │
│         │                       │             │  │   ●●    │   │ ▆▆▆▆░░░░    │
│ DSP Mode│  ━━━━━━━ sea ━━━━━━━━│             │  └─────────┘   │             │
│ ⦿ Active│       ░░░░░░░░░░░░░░░│             │                │ Recent Runs │
│         │                       │             │  Track ID      │ #041 ✓      │
│         │  [reset cam] [3D⇄2D] │             │  T1 (primary)  │ #040 ✓      │
│         │                       │             │  T2,T3 (ships) │ #039 ✗ FAIL │
├─────────┴───────────────────────┴─────────────┴────────────────┤             │
│ DSP Pipeline (Stage Slot)                                       │ History    │
│ ─────────────────────────────────────────────────────────────── │ ↓          │
│ [FMCW]→[FFT]→[CFAR/OS]→[Pair]→[Angle/Mono]→[Track/UKF]→[Pred]   │ ▷ Replay   │
│  Default Default Default  Default  Default   Default    Default │ □ Compare  │
│                                                                  │            │
├─────────────────────────────────────────────────────────────────┴────────────┤
│ Metrics + 4-error summary panel                                              │
│ ─────────────────────────────────────────────────────────────────────────── │
│ Track quality (T1):  RMSE 1.2m  · Lost? No · Latency 1.8ms                  │
│ ────────────────────────────────────────────────                            │
│ 4-error: Bayes 0.3 m | Train 0.5 m | Dev 0.9 m | Test 1.2 m | gap detected  │
│   (gap Train→Dev: variance · gap Dev→Test: distribution shift)              │
│   [📊 Drill into 4-error]   [Run history]   [Probe viewer]                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 핵심 영역 6개

#### A. 좌측 stripe — Pipeline Toggle + Mode

- **Pipeline Stage** ☑ 토글 (각 stage 활성/비활성)
- 7 표준 Stage: FMCW / FFT / CFAR / Pairing / Angle Estimator / Tracker / Predictor
- **DSP Mode** ⦿ 활성 (DSP / NN 전환은 Toolbar)

#### B. 중앙-좌 — 3D Map (Maritime scene)

- PyVista 3D — 해상 + 함정 + 빔 + 표적
- 함정 (Maritime platform) — roll·pitch 애니메이션 (sea state 4)
- 빔 (안테나 패턴) — 발사·수신
- 표적: 미사일 (primary, 빨강) + 함선 (decoy, 회색) + 해면 클러터
- Trajectory line (시간 따른 표적 궤적)
- [reset cam] [3D ⇄ 2D top-down] toggle

#### C. 중앙-우 — Tracks 2D B-scope

- pyqtgraph 2D — Range vs Bearing
- Track ID 별 색 (T1 = primary 빨강, T2/T3 = ships 회색)
- Detection 점 (작은 dot) + Track line
- Primary target 강조 (큰 ●)

#### D. 우측 — Run Manager (Side panel, Q-T5=b)

- 현재 Run 상태 (#042, t=8.42s, progress)
- Recent Runs 목록 (✓ / ✗)
- ▷ Replay 버튼 → SIM-4 Run Manager 화면
- □ Compare 체크 → SIM-6 Multi-Run Compare

#### E. 중간-하 — DSP Pipeline 시각

- 7 Stage 가로 흐름: `[FMCW] → [FFT] → [CFAR/OS] → [Pair] → [Angle/Mono] → [Track/UKF] → [Pred]`
- 각 Stage 아래 **사용 중 plugin 명** (Default 또는 plugin 명)
- Stage 클릭 → Probe Viewer (SIM-5)
- DSP Mode 일 때: 모두 Default
- NN Mode 일 때: 일부 Stage 가 NN plugin (시각 다름)

#### F. 하단 — Metrics + 4-error summary

- **Track quality**: Primary target 의 RMSE / Lost / Latency
- **4-error 요약 1줄**: Bayes / Train / Dev / Test gap (Q-T4=c)
- gap detected 시 자동 hint
- 버튼: [📊 Drill into 4-error] → SIM-3 / [Run history] → SIM-4 / [Probe viewer] → SIM-5

### 1.4 색·시각

Simulator accent: **회색-청 (#7d8590 + #58a6ff)** — 중성 (Editor teal / Physics Lab purple / HIL orange / RT blue 와 구분).
- 하이라이트는 **표적 빨강** (primary missile) 으로 시선 집중
- 함선·decoy 회색
- Track line 흰색
- DSP Pipeline 각 Stage 색 (FFT 파란 / CFAR 노란 / Track 녹색 등)

대안: Simulator 가 본체라서 **accent 없음 + 표적 색 만 강조** 도 가능. UI 가 가장 차분.

내 추천: **회색-청 + 표적 빨강** — 차분함이 본체 답고, 표적 빨강이 정체성.

### 1.5 데이터 출처

- `domain/run_state.py` — RunState dataclass
- `domain/pipeline.py` — RadarPipeline + Stage Slot
- `app/run_supervisor.py` — Run 진행
- `app/metrics_collector.py` — 메트릭

---

## 2. Screen SIM-2 — DSP / NN Mode Toggle (Q-T3=b)

**같은 화면, Pipeline 시각만 바뀜.** 차별점 2 (동일 인터페이스).

### 2.1 의도

Toggle 로 같은 Pipeline 의 Stage 일부를 NN 으로 교체. Track 메트릭은 직접 비교 가능 — DSP A vs NN B 또는 DSP A vs DSP B 와 동일한 비교 환경.

### 2.2 시각 차이

```
DSP 모드 (default):
┌──[FMCW]──[FFT]──[CFAR/OS]──[Pair]──[Angle/Mono]──[Track/UKF]──[Pred]──┐
│  Default  Default  Default   Default  Default       Default     Default│
└────────────────────────────────────────────────────────────────────────┘

NN 모드 (Tracker stage 가 NN):
┌──[FMCW]──[FFT]──[CFAR/OS]──[Pair]──[Angle/Mono]──[Track/NN]──[Pred]──┐
│  Default  Default  Default   Default  Default     🧠 NN       Default│
│                                                   📦 trsim-pkg        │
│                                                   torch_lstm_v0.4    │
└──────────────────────────────────────────────────────────────────────┘
        ↑ 이 Stage 만 NN, 나머지는 동일
```

### 2.3 NN Stage 시각 차이

- NN 활성 Stage: 🧠 아이콘 + 보라 강조 + 사용 모델명 표시
- 학습 영역 vs 외삽 영역 hint (Physics Lab 의 Q-PL8 같은 패턴)
- Toggle 시 즉시 metrics 갱신 (재실행)

### 2.4 비교 모드

NN 활성 시 metrics 패널이 자동 비교:
```
Track quality (T1):
  DSP:   RMSE 1.2m  · Latency 1.8ms
  NN:    RMSE 0.9m  · Latency 4.2ms   ← 정확도↑, 지연↑
  Δ:     -0.3m / +2.4ms
```

### 2.5 핵심 — 동일 인터페이스

- Pipeline 의 다른 Stage 는 **그대로**
- 같은 시나리오, 같은 metric, 같은 Probe
- DSP ↔ NN 전환만 Stage 별로 가능 (전체 NN 아님)
- 학술 NN 연구 환경의 표준 부재 → TRsim 차별점

---

## 3. Screen SIM-3 — 4-error 진단 (드릴, Q-T4=c)

**Andrew Ng 의 4-error 패턴** 추적 레이더 적용. SIM-1 의 요약 1줄 → 클릭 → 이 화면.

### 3.1 4-error 정의

```
Bayes Error      (이론적 최소)
       ↑ avoidable bias gap
Training Error   (학습 데이터에서)
       ↑ variance gap
Dev Error        (검증 세트)
       ↑ distribution shift gap
Test Error       (실제 운용 세트)
```

각 gap → 다른 진단·처방.

### 3.2 시각 흐름

```
┌──────────────────────────────────────────────────────────────────┐
│ 4-error Diagnostic — T1 Primary Missile                       [×]│
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Error level (RMSE position)                                      │
│  ─────────────────────────────────────                            │
│                                                                   │
│  Bayes        ▆▆░░░░░░░░░░░░░░  0.3 m  ━━ avoidable bias 0.2 m   │
│  Training     ▆▆▆░░░░░░░░░░░░░  0.5 m                             │
│                                  ━━━━━━ variance 0.4 m            │
│  Dev          ▆▆▆▆▆▆░░░░░░░░░░  0.9 m                             │
│                                  ━━━ distrib shift 0.3 m          │
│  Test         ▆▆▆▆▆▆▆▆░░░░░░░░  1.2 m                             │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Gap analysis                                                 │ │
│  │ ───────────────────────────────────────                      │ │
│  │                                                              │ │
│  │ Avoidable bias 0.2m (small, OK)                              │ │
│  │   → 알고리즘 이론 한계 근접                                    │ │
│  │                                                              │ │
│  │ ⚠ Variance 0.4m (large)                                       │ │
│  │   → 학습 데이터에 과적합. EKF 의 Q matrix 너무 작거나         │ │
│  │     UKF 의 sigma point 부족                                   │ │
│  │   Suggestion: 학습 시 더 많은 trajectory variation             │ │
│  │                                                              │ │
│  │ Distribution shift 0.3m                                       │ │
│  │   → Dev/Test 의 표적 분포가 학습과 다름 (sea state ↑)          │ │
│  │   Suggestion: Dev/Test 시나리오를 학습 분포에 맞추기 또는      │ │
│  │              학습 분포 확장                                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  [📋 Export Report] [🔄 Re-run with suggestion] [← Back to Sim]   │
└──────────────────────────────────────────────────────────────────┘
```

### 3.3 핵심 인사이트

- 막대 길이로 4 error 비교
- **gap (avoidable bias / variance / distribution shift)** 시각화
- 자동 진단 + suggestion (어떤 파라미터·시나리오 변경)
- Re-run with suggestion → 자동 변경 + 재실행

### 3.4 NN 모드 일 때

NN 의 4-error 가 더 의미. DSP 일 때는 Bayes/Train 이 같은 값 (학습 X) 이라 더 단순.

### 3.5 데이터 출처

- `app/error_decomposer.py` — 4-error 분해
- `domain/metrics.py` — RMSE 계산
- `domain/scenarios/` — Dev / Test 시나리오 분리

---

## 4. Screen SIM-4 — Run Manager (드릴, Q-T5=b)

**Run history + Replay + 시간 scrubber.** SIM-1 의 side panel → 클릭 → 이 화면.

### 4.1 레이아웃

```
┌──────────────────────────────────────────────────────────────────┐
│ Run Manager                                                  [×] │
├──────────────────────────────────────────────────────────────────┤
│ Filter: [All] [Maritime] [Fixed Ground] | Search: [_______]      │
├──────────────────────────────────────────────────────────────────┤
│ # ID    Scenario       Mode  Result  RMSE   Date         Tags    │
│ ─────────────────────────────────────────────────────────────── │
│ ⦿ #042  Maritime/Miss  DSP   ✓       1.2m   today 14:23  current │
│ ○ #041  Maritime/Miss  DSP   ✓       1.5m   today 14:18  ─       │
│ ○ #040  Maritime/Miss  DSP   ✓       1.8m   today 14:10  ─       │
│ ○ #039  Maritime/Miss  DSP   ✗ FAIL  ─      today 14:02  lost T1 │
│ ○ #038  Maritime/Miss  NN    ✓       0.9m   today 13:55  nn_v0.4 │
│ ○ #037  Maritime/Miss  NN    ✓       1.1m   today 13:50  nn_v0.3 │
│ ○ #036  Fixed/Aircraft DSP   ✓       0.7m   yesterday    ─       │
│ ─────────────────────────────────────────────────────────────── │
│                                                                   │
│ Selected: #042 — Maritime · Missile Defense (current run)         │
│                                                                   │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ Replay timeline                                               │ │
│ │  t=0s ━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━ t=15s          │ │
│ │  ▶ Play   ⏸    [◀ −1s] [+1s ▶]   t = 8.42s                   │ │
│ │  Speed: 0.5x | 1x | 2x | 4x      Loop: ☐                     │ │
│ │                                                                │ │
│ │  Events on timeline:                                           │ │
│ │   t=2.3s — primary detected                                    │ │
│ │   t=5.1s — track established (T1)                              │ │
│ │   t=8.42s — current                                            │ │
│ │   t=11.8s — track lost (variance > threshold)                  │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ Run snapshot:                                                     │
│ - Tracks: 3 (T1 primary, T2/T3 ships)                             │
│ - Detections: 1247                                                │
│ - Plugin: Default DSP                                             │
│ - Pipeline trace: trace_042.h5 (12 MB)                            │
│                                                                   │
│ [📂 Open Trace] [📊 To Compare] [🔁 Re-run with same scenario]    │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 핵심

- Run history 표 (사용자 메타: Tags, FAIL 이유)
- Replay timeline — 시간 scrubber
- Event marker (detect/track/lost 등)
- Trace 파일 link (Phase 5 Probe Viewer 로)

### 4.3 데이터 출처

- `io/run_storage.py` — Run Manifest
- `io/trace_storage.py` — Trace HDF5
- 03 § 3.2 RunState dataclass

---

## 5. Screen SIM-5 — Probe / Trace Viewer

**DSP 중간 단계 검사.** SIM-1 의 Pipeline Stage 클릭 → 이 화면.

### 5.1 레이아웃

```
┌──────────────────────────────────────────────────────────────────┐
│ Probe Viewer · Stage: FFT (Range Doppler Map)                [×] │
├──────────────────────────────────────────────────────────────────┤
│ Run #042  ·  t=8.42s  ·  Stage: ⦿FFT ○CFAR ○Pair ○Angle ○Track    │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Range-Doppler Map                                                │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │ Doppler [m/s]                                             │    │
│  │  +500 ┤ . . . . . . . . . . . . . . . . . . . . . .       │    │
│  │  +300 ┤ . . . . . . . ▒▒ ─ T1 missile (closing)           │    │
│  │  +100 ┤ . . . . . . . . . . . . . . . . . . . . . .       │    │
│  │     0 ┤ ░░░░░░░░░░░░░░░ ─ ground/sea clutter              │    │
│  │  -100 ┤ . ░ . . . . . ▒ ─ T2 ship                          │    │
│  │  -300 ┤ . . . . . . . . . . . . . . . . . . . . . .       │    │
│  │  -500 ┤                                                    │    │
│  │       └─────────────────────────                          │    │
│  │        0   2   4   6   8   10  12  14  Range [km]          │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Cursor: range=11.8 km, Doppler=+250 m/s, magnitude=42.3 dB        │
│                                                                   │
│  [Heat] [Contour] [3D]   Color: [magnitude ▾]   Threshold: -10 dB │
│                                                                   │
│  Stage info:                                                      │
│  - FFT size: 4096                                                 │
│  - Window: Hamming                                                │
│  - Trace key: trace_042.h5 / fft_t8.42                            │
│                                                                   │
│  [⏪ Prev frame] [⏩ Next frame] [📋 Export NumPy]                  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Stage 별 시각

| Stage | 시각 |
|---|---|
| FFT | Range-Doppler Map (heatmap) |
| CFAR | Detection threshold + 검출 점 |
| Pairing | Up/down sweep 매칭 시각 |
| Angle | Mono-pulse Σ/Δ 비율 |
| Tracker | EKF/UKF state + covariance |
| Predictor | 예측 위치 + 신뢰 구간 |

### 5.3 데이터 출처

- 06 § 6.x Probe / Trace 시스템
- `io/trace_storage.py`

---

## 6. Screen SIM-6 — Multi-Run Compare

**여러 Run 동시 overlay.** SIM-4 의 □ Compare 체크 → 이 화면.

### 6.1 의도

DSP A vs DSP B vs NN C 직접 비교. 차별점 2 (동일 인터페이스 비교) 의 활용.

### 6.2 레이아웃

```
┌──────────────────────────────────────────────────────────────────┐
│ Multi-Run Compare                                            [×] │
├──────────────────────────────────────────────────────────────────┤
│ Selected runs (drag to reorder):                                  │
│ #042 (DSP, Default)  vs  #038 (NN, lstm_v0.4)  vs  #037 (NN, lstm_v0.3)│
│                                                                   │
│ Metric: ⦿RMSE  ○Latency  ○Detection rate  ○Track lost            │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Time series — RMSE (T1 primary)                                   │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │  RMSE [m]                                                  │    │
│  │   3 ┤                                                      │    │
│  │     │      ─#042 DSP                                       │    │
│  │   2 ┤    ╱╲          ╱╲     ╱╲                             │    │
│  │     │   ╱  ╲        ╱  ╲   ╱  ╲                            │    │
│  │   1 ┤  ╱    ╲╱╲    ╱    ╲ ╱                                │    │
│  │     │ ╱──────────╱──────╲╱─── #038 NN v0.4                 │    │
│  │     │              ─ ─ ─ ─ ─ #037 NN v0.3                  │    │
│  │   0 └──────────────────────────                           │    │
│  │     0    3    6    9    12   15  t [s]                     │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                   │
│ Summary:                                                           │
│ ┌──────────┬──────┬─────────┬──────────┬──────────┐              │
│ │ Run      │ Mean │ Max     │ Lost     │ Latency  │              │
│ ├──────────┼──────┼─────────┼──────────┼──────────┤              │
│ │ #042 DSP │ 1.2m │ 2.4m    │ 0        │ 1.8 ms   │              │
│ │ #038 NN  │ 0.9m │ 1.6m    │ 0        │ 4.2 ms   │              │
│ │ #037 NN  │ 1.1m │ 2.0m    │ 1        │ 4.0 ms   │              │
│ └──────────┴──────┴─────────┴──────────┴──────────┘              │
│                                                                   │
│ Insight: NN v0.4 RMSE -25%, latency +133% (trade-off)              │
│                                                                   │
│ [📋 Export Comparison] [📊 To 4-error compare] [+ Add Run]         │
└──────────────────────────────────────────────────────────────────┘
```

### 6.3 핵심

- 시간 시계열 metric overlay
- Summary 표
- 자동 insight (trade-off 인식)
- 4-error compare 화면 연계 (각 Run 의 4-error 비교)

---

## 7. 화면 간 흐름

```
[Workspace = Simulator]
       │
       ▼
[SIM-1 Main 3D Map + Track + Pipeline] ⭐ (default)
       │
       ├── Toolbar Mode toggle ─→ [SIM-2 NN Mode] (같은 화면, Pipeline 시각만)
       │
       ├── Pipeline Stage 클릭 ─→ [SIM-5 Probe Viewer]
       │
       ├── 4-error 요약 클릭 ─→ [SIM-3 4-error Drill]
       │
       ├── Run Manager 클릭 ─→ [SIM-4 Run Manager]
       │                          │
       │                          └── □ Compare ─→ [SIM-6 Multi-Run Compare]
       │
       └── Toolbar Run ▶ ─→ 시뮬 실행 + 메트릭 갱신
```

---

## 8. CLI 대응

```bash
# Run 시작
trsim sim run scenario.toml --output run_042.h5

# Run 비교
trsim sim compare run_042 run_038 --metric rmse

# 4-error 분해
trsim sim diagnose run_042 --target T1

# Probe export
trsim sim probe run_042 --stage fft --t 8.42 --output spectrum.npz
```

---

## 9. 영향 받는 plan 영역

| 영역 | 변경 |
|---|---|
| 02 § 2.2 블록도 | UI Layer 측 시각화 보강 |
| 05 ui_ux | Simulator Workspace dock 배치 |
| 03 § 3.2 dataclass | RunState / TrackState / Probe |
| 04 Phase 4 | Simulator Workspace UI 체크리스트 |
| 07 NN integration | NN Mode 시각 |

---

## 10. 미결정 사항 (UI 측)

- **SIM-U1**: Simulator accent 색 — 회색-청 (#7d8590 + #58a6ff) 추천. 변경 의향?
- **SIM-U2**: 3D Map 의 카메라 default (top-down vs perspective)
- **SIM-U3**: Pipeline Stage 의 색 (Stage 별 다른 색 vs 일관)
- **SIM-U4**: 4-error 의 Bayes 정의 (이론치 추정 방법 — Q-EW1 류)
- **SIM-U5**: Multi-Run Compare 의 max Run 개수 (2~4 ?)
- **SIM-U6**: Probe Viewer 의 stage 별 시각 표준 (per-stage spec 필요)
- **SIM-U7**: Replay 의 reverse playback 지원? (디버깅 가치)
- **SIM-U8**: Run history 의 자동 archive policy (모든 Run 저장 vs 명시 저장)

---

## 11. Phase 위치

- **Phase 4 MVP**: SIM-1 메인 + SIM-4 Run Manager (DSP only)
- **Phase 5**: SIM-5 Probe Viewer (검증 위해)
- **Phase 6 (NN MVP+α)**: SIM-2 DSP/NN Toggle + SIM-3 4-error 진단
- **Phase 6 보강**: SIM-6 Multi-Run Compare

---

## 12. 다음 (UI mockup 작업)

남은 영역:
- Plugin Manager UI (v0.35 DLC + v0.40 Physics plugin install)
- 옛 Screen 1~8 (필요 시)

---

👉 HTML artifact 동행 (인터랙티브 mockup, 6 화면)
