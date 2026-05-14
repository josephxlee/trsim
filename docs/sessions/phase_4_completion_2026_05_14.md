# Phase 4 — UI 실 데이터 binding sweep 마감 handoff (2026-05-14)

L1 (Run panel) 부터 시작해 L2 → L3 → L4 → L5 → L6 + Editor M1 + M2 까지
6 cycle 묶음. Simulator 8 panel 전체가 `RunController.tick_completed`
신호에 묶여 live data binding 끝났고, Editor 의 DEM import → Map bounds
auto-wire + Composer Installation block (terrain altitude + coverage
stats) 도 live.

## 0. 한 줄 요약

- HEAD (예정) = (commit hash backfill).
- 누적 **2707 PASS** local (2518 → 2707, **+189 신규** across 8 cycle/sub-step).
- 5 contracts KEPT. ruff / mypy --strict / import-linter all clean.
- 8 commits direct push origin/main:
  - L1 `25db1ae` Run panel sim_time/frame_id
  - L2 `0d6b8db` FFT panel pyqtgraph + mock_spectrum
  - L3 `24d1894` RD panel pyqtgraph + mock_range_doppler
  - L4 `49cc19f` Scene 3D PyVista lazy + mock_scene
  - L5 `2c316bc` PluginMgr default seed + StageIO live + mock_stage_io
  - L6 `e3ec01f` Scope POV cross-hair + Properties form + mock_primary_target
  - M1 (이 cycle 묶음) DEMImportController auto-wires set_map_bounds
  - M2 (이 cycle 묶음) ComposerInstallationController

## 1. cycle 표 (8 sub-step 누적)

| sub | commit | +tests | 범위 |
|---|---|---|---|
| L1 | `25db1ae` | +28 | Run panel sim_time/frame_id readout + `SimulatorRunController` (16ms QTimer + SimulationClock + play/pause/stop/set_speed/tick) + workspace forward + MainWindow sim.start/pause/stop/speed hooks |
| L2 | `0d6b8db` | +41 | `app/simulator/mock_spectrum.py` (`MockSpectrumGenerator` deterministic sim_t_s → up/down sweep beat spectrum) + `panels/fft_panel.py` pyqtgraph PlotWidget + 2 curves + 2 InfiniteLine peak markers + `SimulatorFFTController` |
| L3 | `24d1894` | +48 | `app/simulator/mock_range_doppler.py` (`MockRangeDopplerGenerator` 2-D Gaussian + Lissajous trajectory) + `panels/range_doppler_panel.py` pg.ImageItem + viridis LUT + setRect axis calibration + cross-hair + `SimulatorRDController` |
| L4 | `49cc19f` | +28 | `app/simulator/mock_scene.py` (`MockSceneGenerator` radar + target orbit) + `panels/scene_3d_panel.py` lazy QtInteractor + radar/target sphere + terrain plane placeholder + `enable_3d_viewer` kwarg through workspace + MainWindow + `trsim ui --no-3d-viewer` CLI flag + `tests/unit/ui/simulator/conftest.py` pyvista OFF_SCREEN |
| L5 | `2c316bc` | +28 | `app/simulator/mock_stage_io.py` (`MockStageIOGenerator` per-stage IN/OUT + `DEFAULT_PLUGIN_NAMES`) + `SimulatorStageIOController` + workspace seeds plugin manager rows + Record toggle drives in-memory log |
| L6 | `e3ec01f` | +30 | `app/simulator/mock_primary_target.py` (`MockPrimaryTargetGenerator` orbit + servo lag + scope offset + lock flag) + ScopePOVPanel pyqtgraph cross-hair + ScatterPlotItem target marker + `SimulatorPrimaryTargetController` (Scope + Properties 두 panel 동시 push) |
| M1 | (이 commit) | +2 | DEMImportController `_on_import` 성공 시 grid_shape × cell_size → MapBounds → `MapEditor.set_map_bounds` 자동 호출 |
| M2 | (이 commit) | +12 | `ui/editor/composer/installation_controller.py` (`ComposerInstallationController`: composer.position_changed → mock probe → set_terrain_altitude + set_coverage_stats) + MainWindow mount |

총 8 sub-step, **+217 신규 test** (2518 → 2707; 일부 기존 test 갱신
포함하여 net +189 으로 보고).

## 2. MVP_STATUS 매트릭스 변경 요약

| 행 | before | after |
|---|---|---|
| Phase 4 — UI | △ (골격 ✓, 실 데이터 binding ✗) | **✓ (실 데이터 binding sweep 완료)** |
| Simulator panels | △ (Run ✓ L1; 나머지 5 placeholder) | **✓ (8 panel 전체 live binding L1-L6)** |
| Scene 3D PyVista | △ | **✓ (L4 lazy + headless toggle)** |
| Scenario Composer | △ | **✓ (M2 ComposerInstallationController)** |
| Composer Installation Panel | △ | **✓ (G4 layout + M2 live)** |
| Map Editor DEM Import Wizard | ✓ (E1-E4) | ✓ (E1-E4 + M1 bounds auto-wire) |
| Map Editor Domain Settings panel | ✓ (G1-G3) | ✓ (G1-G3 + M1 live bounds readout) |

## 3. 패턴 정착 — Mock Generator + Controller + Workspace wiring

L1-L6 의 8 panel 통합 모두 같은 패턴:

```
RunController.tick_completed(sim_t_s, frame_id)
        │
        ▼
SimulatorXController._on_tick(sim_t_s, frame_id)
        │
        ▼
generator.X_for(sim_t_s) → frame: MockXFrame
        │
        ▼
panel.set_X(frame.*)  (arrays / scene_frame / stage_io / ...)
```

각 controller 는 동일 5 메서드: `__init__(*, panel, run_controller,
generator, enabled, parent)` / `set_enabled(bool)` / `enabled` property
/ `paint_for(sim_t_s, frame_id)` (headless 진입점) /
`_on_tick(sim_t_s, frame_id)` (private slot). Mock generator 는
deterministic 하게 sim_t_s 만 받음 — 같은 sim_t_s 면 같은 frame.

Editor M1/M2 는 signal-driven (DEMImportController 의 import_requested
+ ComposerInstallationController 의 position_changed) 으로, 다른 패턴
이지만 같은 lazy-bind 원리.

## 4. 운영 학습 (cycle 전반)

1. **PySide6 6.11 `QPen.setStyle` raw int 거부** (L2/L3) — `pyqtgraph.
   mkPen(..., style=2)` → `TypeError`. `Qt.PenStyle.DashLine` enum 필수.
2. **ruff RUF046** (L2/L5) — Python 3 `round()` 는 이미 int 반환,
   `int(round(x))` 는 redundant cast.
3. **pyqtgraph `ImageItem.boundingRect()` 가 local pixel rect 반환** (L3) —
   `setRect(x, y, w, h)` 는 QTransform 만 깔고 boundingRect 는 unit
   pixel. 데이터 좌표 검증은 `mapRectToParent(boundingRect)` 또는
   `mapRectToView()`.
4. **PyVista QtInteractor + OpenGL 헤드리스 회피** (L4) — PhysicsLab 의
   `enable_3d_viewer=False` lazy 패턴을 Simulator 에 그대로 적용
   필요. `pyvista.OFF_SCREEN = True` 한 conftest 만으로는 부족 —
   workspace tests 가 명시적으로 `enable_3d_viewer=False` 받아야 함.
5. **PySide6 QObject signal 소유권** (L5) — `SimulatorXController(...)`
   를 변수 없이 호출하면 garbage-collected. Test 에서는 `parent=panel`
   명시 또는 변수 보관 필수.
6. **regex 함정 — `MainWindow` vs `QMainWindow`** (L4 bulk patch) —
   `re.sub(r'MainWindow\(...)', ...)` 가 word-boundary 없이 `QMainWindow`
   도 잡음. `\b` 로 word-boundary 강제 또는 패치 후 revert.

## 5. 다음 cycle 후보 (잔여 우선순위)

`docs/MVP_STATUS.md § "미구현 우선순위 리스트"` 갱신 결과:

| 우선 | 작업 | 크기 |
|---|---|---|
| 1 | **Phase 8 HIL 전체** (8.1 MVP → Lock-step → 8.2 L2/L4 → 8.3 L1+AWG) | 매우 대 |
| 2 | Phase 9 § 19.7.5+ Validation Bench 일반화 | 소-중 |
| 3 | Phase 6 Step 2 per-category real dispatch | 중 |
| 4 | Phase 6 multi-step rollout RMSE real | 중 |
| 5 | Phase 3 Profile 모드 toggle | 소 |
| 6 | Phase 5 #18/#19 재현성 정량 검증 | 소 |
| 7 | Phase 4 UI 잡 (방향키 / Mode / 단축키) | 소 |
| 8 | Phase 4 Editor remainder (Radar / Targets / Atmosphere preview) | 중 |
| 9 | Phase 4 L-series 후속 (mock generators → 실 Pipeline probe) | 큼 |
| 10 | SDK manifest.py 이동 | 잡 |
| 11 | Polish (Theme / Stone Soup / Floating dock B) | 소 |

L-series 의 mock generators 는 향후 Phase 6+ probe recorder 와 묶여
실 Pipeline 으로 교체 가능. 그때까지는 사용자 가시 데모로 충분.

## 6. 이 묶음 commit (origin/main)

```
25db1ae L1 (직전 cycle)
0d6b8db L2
24d1894 L3
49cc19f L4
2c316bc L5
e3ec01f L6
(이 commit) Phase 4 wrap (M1 + M2)
```
