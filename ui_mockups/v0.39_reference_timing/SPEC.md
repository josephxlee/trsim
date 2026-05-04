# UI Mockup Spec — Reference Timing + Frame Profiler (v0.39)

**최종 갱신**: 2026-04-29 (v0.39 통찰 후 첫 UI mockup)
**대상 plan**: 18 § 18.16~18.17, 02 § 2.2c, 03 § 3.2.1n
**대상 Phase**: Phase 4 UI

---

## 0. 의도

이 문서는 v0.39 에서 추가된 Reference Timing Mode + Frame Profiler 의 UI 설계 spec.
HTML artifact 와 함께 본 docs.

핵심 사용자 흐름:
```
[1] Profile 버튼 → Frame Profiler 측정 (100 frames)
[2] 결과 표 표시 → 사용자가 stage 별 latency 인지
[3] "Set Reference Timing" → target_latency 입력 dialog
[4] Run → Reference Timing Mode 동작 (scale indicator + live breakdown)
```

이 흐름이 한 화면에서 시작 → 다른 화면에서 결과 확인 → 메인 시뮬에서 적용.

---

## 1. Screen RT-1 — Frame Profiler 결과 패널

**위치**: Simulator Workspace > Right Dock 또는 별도 모달
**호출**: "Profile" 버튼 (toolbar) 클릭 → 측정 진행 → 완료 후 표시
**파일**: `ui/simulator/profiler_panel/profile_report.py`

### 1.1 레이아웃

```
┌─────────────────────────────────────────────────────────────────┐
│ Frame Profiler Report — A_Base.toml                       [×]   │
├─────────────────────────────────────────────────────────────────┤
│ Frames: 100  (warmup 10 discarded)                              │
│ Duration: 12.3 sec                                              │
│ Context: Intel i9-13900K · Ubuntu 24.04 · load 0.3              │
│                                                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Stage         avg     p50     p95     p99     min     max  │ │
│ │─────────────────────────────────────────────────────────── │ │
│ │ detector     87ms    85ms   110ms   125ms    78ms   140ms  │ │ ← 행 클릭
│ │ pairing      12ms    11ms    15ms    18ms     9ms    22ms  │ │   가능
│ │ tracker      23ms    22ms    28ms    35ms    19ms    42ms  │ │
│ │─────────────────────────────────────────────────────────── │ │
│ │ pipeline    125ms   120ms   148ms   175ms   115ms   195ms  │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │  detector latency distribution (100 frames)                 │ │
│ │  ms    ▏                                                    │ │
│ │  140 ─┤█                                                    │ │
│ │  130 ─┤██                                                   │ │ ← 분포 그래프
│ │  120 ─┤████                                                 │ │   (선택 stage)
│ │  110 ─┤██████                                               │ │
│ │  100 ─┤██████████                                           │ │
│ │   90 ─┤████████████████                                     │ │
│ │   80 ─┤████                                                 │ │
│ │      └──────────────────────────────────────                │ │
│ │       0    20   40   60   80   100  count                   │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ [💾 Save Report]  [📋 Copy Markdown]  [⚙️ Set Reference Timing] │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 위젯 목록

| 위젯 | 타입 | 역할 |
|---|---|---|
| 헤더 정보 | QLabel × 3 | scenario / frames / duration / context |
| 통계 표 | QTableView | stage_stats + pipeline_stat 표시 |
| 분포 그래프 | pyqtgraph histogram | 선택 stage 의 latency 분포 |
| Save Report | QPushButton | JSON / Markdown 저장 |
| Copy Markdown | QPushButton | 클립보드 복사 |
| Set Reference Timing | QPushButton | RT-2 dialog 호출 |

### 1.3 인터랙션

- **표의 행 클릭** → 분포 그래프가 해당 stage 로 갱신
- **Save Report** → 파일 저장 dialog (`.json` / `.md` 선택)
- **Set Reference Timing** → Screen RT-2 다이얼로그 띄움, 측정값 자동 채워짐

### 1.4 데이터 출처

- `app/timing/frame_profiler.py` 의 `FrameTimingReport`
- 03 § 3.2.1n dataclass

---

## 2. Screen RT-2 — Set Reference Timing Dialog

**위치**: 모달 dialog (Screen RT-1 의 "Set Reference Timing" 클릭 시)
**파일**: `ui/simulator/profiler_panel/reference_timing_dialog.py`

### 2.1 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│ Set Reference Timing                                  [×]   │
├─────────────────────────────────────────────────────────────┤
│ Mode:  ⦿ Per-stage target_latency_ms                        │
│        ○ Pipeline scale_factor only                          │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Stage      Measured (avg)   Target (실 보드)   Scale    │ │
│ │ ─────────────────────────────────────────────────────── │ │
│ │ detector   87ms             [ 50 ] ms          0.57     │ │
│ │ pairing    12ms             [    ] ms          (auto)   │ │ ← 빈 칸은
│ │ tracker    23ms             [ 20 ] ms          0.87     │ │   scale=1.0
│ │ ─────────────────────────────────────────────────────── │ │
│ │ pipeline   125ms             ─                  0.66    │ │ ← 자동 계산
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Frame Unit:  ⦿ auto (track output trigger)                   │
│              ○ fmcw_sweep                                    │
│              ○ fft_window                                    │
│              ○ custom: [               ]                     │
│                                                              │
│ ☐ Save to scenario file (A_Base.toml)                        │
│                                                              │
│                              [ Cancel ]  [ Apply & Run ]    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 위젯 목록

| 위젯 | 타입 | 역할 |
|---|---|---|
| Mode radio | QRadioButton × 2 | per-stage vs pipeline-only |
| Stage 표 | QTableWidget | stage 별 target 입력 |
| Target 입력 | QSpinBox per row | target_latency_ms |
| Scale 표시 | QLabel per row | 자동 계산 (target / measured) |
| Frame Unit radio | QRadioButton × 4 | frame 정의 |
| Custom frame | QLineEdit | "custom" 선택 시 활성 |
| Save checkbox | QCheckBox | 시나리오에 저장 |
| Cancel / Apply & Run | QPushButton × 2 | |

### 2.3 인터랙션

- **target 입력 시** → scale 자동 계산 표시
- **빈 target** → scale=1.0 (보정 안 함)
- **target > measured** (PC 더 빠름) → "sleep으로 늦춤" 안내 tooltip
- **target < measured** (PC 더 느림) → "scale_factor 보정" 안내 tooltip
- **Save to scenario file** 체크 → TOML `[timing]` + `[[timing.profiles]]` 섹션 자동 생성
- **Apply & Run** → 시뮬 시작, Reference Timing Mode 활성

### 2.4 데이터 흐름

```
입력 (사용자) → StageTimingProfile 생성 → TimingConfig 에 추가
            → 시뮬 시작 시 PerformanceClock 에 주입
            → (옵션) scenario.toml 파일에 저장
```

---

## 3. Screen RT-3 — Live Timing Breakdown (Run 중)

**위치**: Simulator Workspace > Right Dock (Run 중 표시)
**파일**: `ui/simulator/profiler_panel/timing_breakdown.py`

### 3.1 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│ Live Timing  [Profiling: ON ⓘ]                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Current scale: 0.57x ⓘ      Frame: 423 / running           │
│                                                              │
│  Stage         Last    Avg     p95   ▏ Target   Status     │
│  ───────────────────────────────────────────────────────    │
│  detector      82ms    87ms   110ms  ▏  50ms    ⚠ slow     │
│  pairing       11ms    12ms    15ms  ▏  ─       ─          │
│  tracker       21ms    23ms    28ms  ▏  20ms    ✓ OK       │
│  ───────────────────────────────────────────────────────    │
│  pipeline     114ms   125ms   148ms  ▏  ─       ─          │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ detector  ████████████████████████████  82ms        │    │
│  │ pairing   ███▏  11ms                                │    │ ← 막대 chart
│  │ tracker   ██████▏  21ms                             │    │   (live)
│  │ ─────────────────────────────────                   │    │
│  │ Frame total: 114ms (real)  / 65ms (reference)       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Latency over time (last 100 frames)                 │    │
│  │  ms  ▏                                              │    │
│  │ 130 ─┤    ╲     ╱╲      ╱╲                         │    │
│  │ 120 ─┤  ╱  ╲   ╱  ╲   ╱  ╲     ╱─── pipeline      │    │
│  │ 110 ─┤ ╱    ╲_╱    ╲_╱    ╲___╱                   │    │
│  │ 100 ─┤                                              │    │
│  │      └──────────────────────────  frame             │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 위젯 목록

| 위젯 | 타입 | 역할 |
|---|---|---|
| Profiling toggle | QToolButton (checkable) | live profile on/off |
| Scale label | QLabel | "0.57x" — toolbar indicator (Screen RT-3 별도) |
| Frame counter | QLabel | "423 / running" |
| Live 표 | QTableWidget | last / avg / p95 / target / status |
| Status icon | QLabel + emoji | ✓ OK / ⚠ slow / ─ unset |
| 막대 chart | pyqtgraph BarGraphItem | last frame stage 별 |
| Latency line plot | pyqtgraph PlotWidget | 시간에 따른 latency |

### 3.3 인터랙션

- **Profiling toggle off** → 측정 중지 (overhead 0), 표·차트 freeze
- **Stage 행 클릭** → line plot 이 그 stage 로 갱신
- **Status ⚠ slow** → tooltip 으로 "target 대비 X% 초과" 표시

### 3.4 toolbar 의 scale indicator (별도)

Run 중 main toolbar 우측에 작은 표시:

```
┌──────────────────────────────────────┐
│  [▶ Run] [⏸] [⏹]   ...    0.57x ⓘ   │ ← scale indicator
└──────────────────────────────────────┘
```

**호버 시 tooltip**:
```
Reference Timing Mode active
Pipeline reference: 65ms (target)
Pipeline measured: 114ms (real)
Scale factor: 0.57x

→ 시뮬 시간이 wall_clock 의 57% 속도로 흐름
```

### 3.5 데이터 출처

- `app/timing/performance_clock.py` 의 `ReferenceTimingState`
- `app/timing/stage_timing_probe.py` 의 백그라운드 측정값

---

## 4. 화면 간 흐름

```
[Simulator Toolbar]
       │
       │ "Profile" 버튼 클릭
       ▼
[Profile 측정 진행] (progress bar 100 frames)
       │
       ▼
[Screen RT-1] Frame Profiler Report
       │
       │ "Set Reference Timing" 버튼
       ▼
[Screen RT-2] Set Reference Timing Dialog
       │
       │ "Apply & Run" 버튼
       ▼
[Run 시작 + Screen RT-3 Live Timing 표시]
       │
       │ Run 중 toolbar 에 "0.57x" indicator
       ▼
[Run 종료] → 결과 metric + final timing summary
```

---

## 5. CLI 대응 (Phase 3)

UI 외 CLI 도 동일 기능 제공:

```bash
# Profile 측정
trsim profile A_Base.toml --frames 100 --output profile.json

# Reference Timing 설정 + Run
trsim run A_Base.toml --timing-mode reference \
                      --profile-config profile.json \
                      --frame-unit auto

# 출력
[Frame  100] detector=87ms pairing=12ms tracker=23ms scale=0.57x
[Frame  200] detector=85ms pairing=11ms tracker=22ms scale=0.59x
...
```

---

## 6. 영향 받는 plan 영역

| 영역 | 변경 |
|---|---|
| 13 editor_workspace | 변경 없음 (Editor 측 영향 없음) |
| 02 § 2.2c PerformanceClock | UI 측에서 ReferenceTimingState 구독 |
| 03 § 3.2.1n | FrameTimingReport / StageTimingStat → Screen RT-1 표 |
| 18 § 18.16.6 UI 시각화 | 본 mockup 으로 구체화 |
| 18 § 18.17.6 결과 표시 | 본 mockup 으로 구체화 |

---

## 7. 미결정 사항 (UI 측)

- **TI-U1**: Live Timing 의 line plot 갱신 빈도 (10Hz / 30Hz / per-frame)?
- **TI-U2**: 분포 그래프 bin size (자동 / 사용자 설정)?
- **TI-U3**: Profile 진행 중 cancel 가능성 (50 frames 만 측정 후 cancel)?
- **TI-U4**: Reference Timing dialog 의 "Save to scenario file" default 값 (체크 / 미체크)?
- **TI-U5**: scale 0.5x 미만일 때 시각적 경고 (시뮬이 너무 느려짐 신호)?

---

## 8. 다음 (UI mockup 작업)

- 다음 영역: HIL 통합 UI (Screen HIL-1~3)
  - DUT 연결 셋업
  - GT/SIL/HIL 3-way 비교 패널
  - DUT-Bias 시각화

---

👉 HTML artifact 동행 (인터랙티브 mockup)
