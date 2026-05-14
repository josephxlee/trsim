# TRsim MVP 검증 트리 (rev1, 2026-05-14)

MVP 완성 (2807 PASS) 후 사용자 hand-test base polish 단계에서
single-source-of-truth. `docs/MVP_GUIDE.md` rev11 이 "어떤 명령을
칠지" 라면, 이 문서는 "**무엇이 동작해야 하는지 + 지금 상태**" 의
계층 트리. 각 leaf 의 ☐ / ✓ / △ / ✗ 마크가 곧 to-do list.

---

## § 0. 사용법

### 마크 시맨틱

| 마크 | 의미 |
|---|---|
| ☐ | 미검증 (default) |
| ✓ | pass — 사용자가 hand-test 또는 unit test 로 확인 |
| △ | partial — 일부만 동작하거나 fix 진행 중, 재검증 필요 |
| ✗ | fail — 즉시 또는 후속 cycle fix 필요 |

각 ✓/△/✗ 옆에 commit hash 또는 메모 (예: `✓ ffe8538`).

### 검증 순서

1. **§ 1 Simulation** (이번 cycle 본격 작성, 1순위)
2. § 2 Physics Lab (다음 cycle 작성)
3. § 3 Editor (다음 cycle 작성)

각 § 안에서는 **1.F (Front) → 1.W (Wire) → 1.B (Back)** 순.

### 3-layer 계층 design

| Layer | 검증 대상 | 격리 방법 |
|---|---|---|
| **Front** | UI widget 자체 (layout, child 위젯, 기본 표시) | widget 단독 인스턴스화. controller 안 만듦. |
| **Wire** | Controller 의 signal routing + paint 로직 | 1 controller 만 enable, 나머지는 `set_enabled(False)` |
| **Back** | Mock generator / domain logic (pure Python) | GUI 없이 pytest / REPL |

Wire layer 의 격리 snippet 은 § 5 (Isolation API reference) 참조.

### 진행 흐름

- 사용자가 hand-test 진행 → leaf 마다 ☐ → ✓ / △ / ✗ in-place 갱신
- △ / ✗ 발견 시 즉시 fix 가능하면 commit, 후속이면 § 4 표에 추가
- Simulation 영역의 모든 ✗ leaf 가 ✓ 또는 △-acceptable 로 정리되면
  → Physics Lab 작성 신호

---

## § 1. Simulation (1순위)

### 1.F  Front — UI widget layer

각 widget 을 단독으로 인스턴스화한 상태에서 layout / child / 기본 표시
검증. controller 안 만듦.

#### 1.F.1 Workspace shell
- ☐ `trsim ui --workspace simulator` 진입 (process crash 없이 창
  표시)
- ☐ 1280x800 default layout — 5 nested splitter (outer / top_row /
  center / spectra / bottom_tabs)
- ☐ Sim toolbar (상단) — Play / Pause / Stop / Speed (x1/x2/x4/x8)
  4 group, Toggle 가능

#### 1.F.2 Run panel (RunPanel())
- ☐ "Simulation Time" GroupBox 4 readout (sim_t / frame / state /
  speed) — 기본 텍스트 `0.000 s / 0 / stopped / x1`
- ☐ "Primary Target" 6 row (Lock / Track continuity / ID switches /
  Range RMSE / AZ RMSE / Positioner lag) — 기본 `--`
- ☐ "Run History" QListWidget — 기본 빈 리스트

#### 1.F.3 FFT panel (FFTPanel())
- ☐ `pg.PlotWidget` mounted (objectName `FFTPanelPlot`)
- ☐ 2 PlotDataItem (`up_curve` red `#d62728`, `down_curve` blue
  `#1f77b4`) — 빈 데이터 OK
- ☐ 2 InfiniteLine peak marker — 기본 hidden

#### 1.F.4 RD panel (RangeDopplerPanel())
- ☐ `pg.PlotWidget` + `pg.ImageItem` (row-major + viridis LUT 또는
  fallback) — objectName `RangeDopplerPlot`
- ☐ 2 InfiniteLine cross-hair (vertical doppler + horizontal range,
  DashLine 노랑) — 기본 hidden
- ☐ 헤더 `frame: -` 라벨

#### 1.F.5 Scene 3D panel (Scene3DPanel(enable_3d_viewer=True))
- ☐ `pyvistaqt.QtInteractor` lazy mount — OpenGL 컨텍스트 성공
- ☐ Camera preset 4 라디오 (T / L / F / R)
- ☐ Layers 11 checkbox (TERRAIN/SEA/BUILDINGS/SHIPS/TX_BEAM_ACTUAL/
  TX_BEAM_COMMAND/GT_TARGETS/DETECTIONS/TRACKS/PRIMARY_HIGHLIGHT/
  MULTIPATH_RAYS) — 8 default on
- △ 마우스 휠 zoom / 좌클릭+drag camera 회전 / 우클릭+drag pan —
  `a8c75c6` setFocusPolicy(StrongFocus) 적용, **사용자 재검증 필요**

#### 1.F.6 PluginMgr panel (PluginManagerPanel())
- ☐ 5 stage QGroupBox (Detector / Pairing / Tracker / Predictor /
  Classifier) — objectName `PluginStage_<stage>`
- ☐ `+ Add Plugin` / `Reload All` 버튼 + signal 발화

#### 1.F.7 StageIO panel (StageIOPanel())
- ☐ 6 stage QGroupBox (Transmitter / Environment / Receiver /
  Detector / Pairing / Tracker)
- ☐ Record toggle 버튼 (objectName `StageIORecordBtn`) + Export 버튼
- ☐ 헤더 `frame: -` 라벨

#### 1.F.8 Properties panel (PropertiesPanel())
- ☐ 헤더 context 라벨 (기본 `(nothing selected)`)
- ☐ QFormLayout 본문 (기본 0 row)
- ✓ 텍스트 깜박임 없음 — `ffe8538` fast-path (label + key set 같으면
  setText 만, widget 재사용)

#### 1.F.9 ScopePOV panel (ScopePOVPanel())
- ☐ `pg.PlotWidget` aspect-locked 1:1, range `[-1, 1] × [-1, 1]`,
  axis hidden
- ☐ 2 InfiniteLine boresight cross-hair (회색, 0 위치)
- ☐ `pg.ScatterPlotItem` target marker (size 14, 빨강) — 기본 빈
  데이터
- ☐ AZ readout 라벨 (`AZ actual / cmd / lag: -- / -- / --`)
- ☐ hint 라벨 (`(no target — start the simulator)`) — 기본 visible

#### 1.F.10 Bottom tabs (DetachableTabWidget)
- ☐ 6 default tab — `Run / Stage I/O / Profiler / NN Step 1 /
  NN Step 2 / NN Training`
- ☐ Tab detach — tabBar 우클릭 → `Detach tab` → floating top-level
  window
- ☐ Floating 창 close → 원래 위치 + 라벨로 자동 복귀

#### 1.F.11 Resize / window 동작
- △ 창 maximize 시 splitter 비율 — `a8c75c6` top_row 1:3:1:1 +
  outer 3:1, **사용자 재검증 필요**
- ✗ Run 중 resize 시 panel paint conflict — P5c `c09cc88` revert →
  `5c3be82`, **후속 cycle**
- ✗ 창 maximize 시 FFT / RD 그래프 복사 잔상 — Qt repaint buffer
  잔상, **후속 cycle**

### 1.W  Wire — Controller wiring

각 controller 만 enable + 나머지 `set_enabled(False)` 격리.

#### 1.W.1 SimulatorRunController
- ✓ `play()` idempotent — `4bdf592` (already RUNNING 이면 no-op)
- ✓ `pause()` / `stop()` idempotent
- ☐ 30 Hz QTimer (33 ms) interval — `tick_interval_ms == 33`
- ☐ `tick(wall_dt_s)` 시 `sim_t_s` 와 `frame_id` 갱신
- ☐ `tick_completed(sim_t, frame_id)` signal 발화
- ☐ `set_speed(SpeedMultiplier.X4)` 시 sim_t 증가율 x4 배

```python
# 1.W.1 isolation — RunController only (다른 controller 모두 disable)
ws = SimulatorWorkspace(nn_datasets_root=None, autostart_run_timer=False,
                        enable_3d_viewer=False)
for ctl in (ws.fft_controller(), ws.rd_controller(),
            ws.scene_controller(), ws.stage_io_controller(),
            ws.primary_target_controller()):
    ctl.set_enabled(False)
ws.sim_play()
ws.run_controller().tick(0.033)
assert ws.run_panel().sim_time_label().text() == "0.033 s"
```

#### 1.W.2 SimulatorFFTController
- ☐ `tick_completed` → `generator.spectrum_for(sim_t)` →
  `panel.set_spectrum(freqs, up, down)`
- ☐ `set_enabled(False)` → tick 무시 (panel 변화 0)

```python
# 1.W.2 isolation
for ctl in (ws.rd_controller(), ws.scene_controller(),
            ws.stage_io_controller(), ws.primary_target_controller()):
    ctl.set_enabled(False)
ws.sim_play()
ws.run_controller().tick(0.033)
xs, ys = ws.fft_panel().up_curve().getData()
assert xs.size > 0
```

#### 1.W.3 SimulatorRDController
- ☐ `tick_completed` → `generator.heatmap_for(sim_t)` →
  `panel.set_heatmap`
- ☐ `set_enabled(False)` → tick 무시

```python
# 1.W.3 isolation: fft/scene/stage_io/primary_target → set_enabled(False)
```

#### 1.W.4 SimulatorSceneController
- ☐ `tick_completed` → `generator.scene_for(sim_t)` →
  `panel.set_scene_frame`
- ☐ `set_enabled(False)` → tick 무시
- ☐ headless 모드 (`enable_3d_viewer=False`) 에서 status label 만
  갱신

#### 1.W.5 SimulatorStageIOController
- ☐ `tick_completed` → `generator.io_for(sim_t)` → panel 의 6 stage
  set_stage_io
- ☐ Record toggle ON 시 매 tick 마다 `MockStageIOFrame` 누적
- ☐ Record OFF → ON 재토글 → 이전 log clear
- ☐ `set_enabled(False)` → tick 무시

#### 1.W.6 SimulatorPrimaryTargetController (Scope + Properties)
- ☐ `tick_completed` → Scope `set_pointing(actual, cmd)` +
  `set_target_norm(x, y)`
- ☐ `tick_completed` → Properties `show_object("Primary Target",
  {Range / Azimuth / Elevation / RCS / Speed / Lock})`
- ☐ `add_manual_offset(d_az_deg, d_el_deg)` — 누적 + 즉시 repaint
- ☐ `reset_manual_offset()` — 둘 다 0 + 즉시 repaint
- ☐ 방향키 `←→↑↓` / `Home` / `0` (workspace.keyPressEvent 통해)

```python
# 1.W.6 isolation
for ctl in (ws.fft_controller(), ws.rd_controller(),
            ws.scene_controller(), ws.stage_io_controller()):
    ctl.set_enabled(False)
ws.sim_play()
ws.run_controller().tick(0.033)
assert ws.properties_panel().context_label().text() == "Primary Target"
# manual pointing
ws.primary_target_controller().add_manual_offset(d_az_deg=0.5, d_el_deg=0.0)
assert ws.primary_target_controller().manual_az_offset_deg == 0.5
```

#### 1.W.7 PluginMgr default seed
- ☐ Workspace 생성 시점 `set_stage_plugins` 5 회 호출 — Detector
  `default_cfar` / Pairing `default_pairing` / Tracker `default_ekf`
  / Predictor `default_cv` / Classifier `default_threshold`

#### 1.W.8 Workspace.keyPressEvent (manual pointing entry)
- ☐ Left → `add_manual_offset(d_az=-0.5)`
- ☐ Right → `add_manual_offset(d_az=+0.5)`
- ☐ Up → `add_manual_offset(d_el=+0.5)`
- ☐ Down → `add_manual_offset(d_el=-0.5)`
- ☐ Home / 0 → `reset_manual_offset()`
- ☐ 다른 키 → 무시 (super().keyPressEvent)

### 1.B  Back — Mock generator + domain (pure Python)

GUI 없이 pytest / REPL 검증.

#### 1.B.1 MockSpectrumGenerator
- ☐ deterministic — 같은 `sim_t_s` → bit-identical array
- ☐ peak 가 `sinusoidal sweep` 으로 이동 (period = sweep_period_s)
- ☐ noise 가 sim_t-derived seed 로 재현 — 같은 seed 면 같은 noise

#### 1.B.2 MockRangeDopplerGenerator
- ☐ Lissajous trajectory (range × doppler 두 sinusoid)
- ☐ deterministic
- ☐ sweep amplitude 가 axis 안에서 capping

#### 1.B.3 MockSceneGenerator
- ☐ 고정 radar (default 원점)
- ☐ Target 이 horizontal circular orbit (radius + period 파라미터)
- ☐ deterministic — 같은 sim_t → 같은 target ENU

#### 1.B.4 MockStageIOGenerator
- ☐ 6 stage 별 IN/OUT 문자열 — pipeline pass-through
  (Environment.IN == Transmitter.OUT 등)
- ☐ deterministic
- ☐ reflections / detections / pairs / tracks 카운트 sin envelope

#### 1.B.5 MockPrimaryTargetGenerator
- ☐ Target orbit + altitude
- ☐ Servo lag 적용 (`actual_az = az - servo_lag_deg`)
- ☐ Cross-hair offset 가 `[-1, 1]` 클램핑
- ☐ Lock flag 가 `lock_after_s` 후 True

#### 1.B.6 SimulationClock
- ☐ State machine (STOPPED / RUNNING / PAUSED) 전이
- ☐ `advance(wall_dt_s)` 가 RUNNING 일 때만 `sim_t_s` 증가
- ☐ `start()` 가 already RUNNING 이면 RuntimeError (domain 불변)

#### 1.B.7 ProfileGate / ProfileMode (Phase 3 Q4, P3)
- ☐ ProfileMode StrEnum 3 값 (OFF / EXPLICIT / LIVE)
- ☐ ProfileGate LIVE → always record, OFF → never, EXPLICIT →
  one-shot latch
- ☐ `set_mode()` 가 pending one-shot 을 clear
- ☐ `trsim profile --mode --explicit-every` CLI flag 적용

---

## § 2. Physics Lab — placeholder

> 본격 작성은 사용자 신호 후 다음 cycle.
> 구조: § 1 과 동일한 3-layer (Front / Wire / Back).
> 후보 leaf 영역:
> - Front: PhysicsLabWorkspace, Library QTreeWidget, Code editor,
>   Visualization (pyqtgraph + 3D viewer), Parameters slider,
>   Time controls
> - Wire: BouncingBallController, Code edit signals, Time Mode combo,
>   Validation Bench (PL-9.2c + P2), Saved Experiments load/save
> - Back: BouncingBallSimulator, PhysicsClock, 9 Test Objects,
>   5 physics models, ValidationBench generic (P2)

---

## § 3. Editor — placeholder

> 본격 작성은 사용자 신호 후 다음 cycle.
> 구조: § 1 과 동일한 3-layer.
> 후보 leaf 영역:
> - Front: EditorWorkspace, 5 Activity bar, ScenarioComposer,
>   MapEditor, RadarEditor, TargetsEditor, AtmospherePanel,
>   ResourceBrowser sidebar, DEM Import wizard
> - Wire: ComposerInstallationController (M2), DEMImportController
>   (E4 + M1), motion_combo → TrajectoryPreview swap (P7),
>   rain_rate → attenuation refresh (P7), ResourceBrowser
>   double-click → activity 자동 전환
> - Back: domain.simulation_domain, domain.map_resource (MapBounds),
>   io.dem_import, physics.atmosphere, ResourceLibrary, sdk.manifest

---

## § 4. 잔여 이슈 한눈에 (Simulation 만)

| 이슈 | 트리 leaf | 마크 | 메모 / 다음 단계 |
|---|---|---|---|
| Scene 3D 마우스 휠 / drag | 1.F.5 마지막 leaf | △ | `a8c75c6` setFocusPolicy(StrongFocus) 적용. 사용자 재검증 후 ✓ 또는 환경 (OpenGL 드라이버 / GPU 가속) 의존 결론. |
| Properties 텍스트 깜박임 | 1.F.8 마지막 leaf | ✓ | `ffe8538` fast-path (label + key set 같으면 setText 만, widget 재사용). |
| Play 두번 클릭 traceback | 1.W.1 첫 leaf | ✓ | `4bdf592` 컨트롤러 idempotent. |
| 창 maximize 시 splitter 비율 안맞음 | 1.F.11 첫 leaf | △ | `a8c75c6` top_row 1:3:1:1 + outer 3:1. 사용자 재검증 후 ✓ 또는 추가 fix. |
| Run 중 resize 시 panel paint conflict | 1.F.11 두번째 leaf | ✗ | P5c (`c09cc88`) paint suppression 시도 → 더 이상해서 revert (`5c3be82`). **후속 cycle** — paint suppression 다른 접근 필요 (예: widget.setUpdatesEnabled(False) 활용 또는 tick rate 추가 감속). |
| 창 maximize 시 FFT / RD 그래프 복사 잔상 | 1.F.11 마지막 leaf | ✗ | Qt repaint buffer 의 stale graphic carry-over. PyVista QtInteractor + pyqtgraph 의 paint conflict 추정. **후속 cycle**. |

### 다음 cycle 우선 fix 후보

1. 1.F.11 두번째 leaf (Run 중 resize paint conflict) — P5c 와 다른
   접근. 후보:
   - `setUpdatesEnabled(False)` 를 splitter resize 시 토글
   - Tick interval 추가 감속 (33ms → 50ms 20Hz)
   - Resize 중 widget paint event 별도 batch
2. 1.F.11 마지막 leaf (그래프 복사 잔상) — 1번 fix 후 자연 해결될
   가능성 있음 (paint conflict 가 잔상의 원인일 수 있음). 1 번 후
   재검증.

---

## § 5. Isolation API reference

### Controller `set_enabled` 토글 표

| Controller | Workspace accessor | 다음 leaf 검증 시 disable 권장 |
|---|---|---|
| SimulatorRunController | `ws.run_controller()` | 거의 모든 검증의 driver — 보통 enable 유지 |
| SimulatorFFTController | `ws.fft_controller()` | 1.W.3 / 1.W.4 / 1.W.5 / 1.W.6 |
| SimulatorRDController | `ws.rd_controller()` | 1.W.2 / 1.W.4 / 1.W.5 / 1.W.6 |
| SimulatorSceneController | `ws.scene_controller()` | 1.W.2 / 1.W.3 / 1.W.5 / 1.W.6 |
| SimulatorStageIOController | `ws.stage_io_controller()` | 1.W.2 / 1.W.3 / 1.W.4 / 1.W.6 |
| SimulatorPrimaryTargetController | `ws.primary_target_controller()` | 1.W.2 / 1.W.3 / 1.W.4 / 1.W.5 |

각 controller 의 `set_enabled(value)` API + `enabled` property:
- True 시 `RunController.tick_completed` 에 connect
- False 시 disconnect (다음 tick 부터 panel 갱신 0)
- 토글이 idempotent — 같은 값 두번 호출 시 변화 없음

### 격리 검증 패턴

```python
# Python REPL 또는 ad-hoc pytest 안에서
from workbench.ui.simulator.workspace import SimulatorWorkspace

ws = SimulatorWorkspace(
    nn_datasets_root=None,
    autostart_run_timer=False,  # QTimer 가동 X, manual tick
    enable_3d_viewer=False,      # OpenGL 부담 X (headless)
)

# 검증할 controller 하나만 남기고 나머지 비활성
target = ws.fft_controller()  # 예: FFT 검증
for ctl in (ws.rd_controller(), ws.scene_controller(),
            ws.stage_io_controller(), ws.primary_target_controller()):
    ctl.set_enabled(False)

# 시뮬레이션 가동 + 수동 tick
ws.sim_play()
ws.run_controller().tick(0.033)  # 1 frame

# target panel 만 갱신됐는지 확인
xs, ys = ws.fft_panel().up_curve().getData()
assert xs.size > 0  # FFT 만 paint 됨
# 나머지 panel 의 marker / curve 는 비어있어야 함
```

### Pytest unit test 의 격리 패턴 (이미 존재)

`tests/unit/ui/simulator/test_*_controller.py` 의
`test_disabled_controller_does_not_paint` 가 같은 패턴을 단위
테스트로 검증 — controller 가 enabled=False 일 때 panel 의 시각화
요소가 갱신 안 되는지 assert.

---

## 변경 이력

- **rev1** (2026-05-14) — 신규 작성. § 1 Simulation 본격 + § 2 / § 3
  placeholder. 잔여 이슈 6 건 매핑 (1.F.5, 1.F.8, 1.W.1, 1.F.11 × 3).
