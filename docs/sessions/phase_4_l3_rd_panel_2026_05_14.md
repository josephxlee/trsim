# Phase 4 cycle — L3 Simulator RD panel pyqtgraph live heatmap (2026-05-14)

직전 cycle (L2 FFT panel pyqtgraph live spectrum) 이어서 Simulator 8 panel
중 세 번째 panel 에 실 데이터 binding. plan/04 § 4.3 의 Phase 4 UI 실 데이터
binding 우선순위 (사용자 "Simulation 가장 시급" 명시) 의 세 번째 sub-step.

## 0. 한 줄 요약

- HEAD = (이 cycle commit).
- 누적 **2607 PASS** local (2559 → 2607, **+48 신규**).
- 5 contracts KEPT. ruff / mypy --strict / import-linter all clean.
- 1 sub-step direct push origin/main.

## 1. sub-step 표

| sub | new tests | 범위 |
|---|---|---|
| L3 | +48 | (a) `app/simulator/mock_range_doppler.py` 신규 — `MockRangeDopplerGenerator` (deterministic sim_t_s → 2-D Gaussian heatmap, range/doppler 두 독립 sinusoid → Lissajous trajectory, range/doppler base+sweep 모두 axis-bound capping, Gaussian noise quantised by sim_t_s ^ rng_seed) + `MockRangeDopplerFrame` frozen dataclass. (b) `panels/range_doppler_panel.py` placeholder QFrame 제거 → `pg.PlotWidget` + `pg.ImageItem` (row-major + viridis LUT + ``setRect`` axis calibration) + 2 InfiniteLine cross-hair (vertical doppler + horizontal range, DashLine, hidden by default) + `set_heatmap(heatmap_db, range_axis_m, doppler_axis_mps, *, levels_db)` + `set_peak / clear_peak`. Phase 4.9 header API (set_frame) 보존. (c) `ui/simulator/rd_controller.py` 신규 — `SimulatorRDController(QObject)` (L2 의 FFTController 패턴 동일: run_controller.tick_completed → generator.heatmap_for → panel push + enabled toggle + `paint_for(sim_t_s, frame_id)` headless 진입점). (d) SimulatorWorkspace 가 FFTController 직후 RDController 자동 인스턴스화 + `rd_controller()` accessor. |

## 2. MVP_STATUS 매트릭스 변경

| 행 | before | after |
|---|---|---|
| Simulator panels (FFT / RD / Run / Properties / PluginMgr / StageIO) | △ (Run ✓ L1; FFT ✓ L2; 나머지 4 panel placeholder) | △ (Run ✓ L1; FFT ✓ L2; RD ✓ L3 — pyqtgraph ImageItem + viridis LUT + peak cross-hair + MockRangeDopplerGenerator live binding; 나머지 3 panel placeholder) |

## 3. 사용자 우선순위 (변동 없음)

> **physics_lab > simulator > editor** — 사용자 "Simulation 가장 시급"
> Simulator 8 panel 의 실 데이터 binding 이 잔여 작업 1순위.

L1+L2+L3 모두 같은 ``tick_completed`` 패턴 (mock generator + controller +
panel push) 으로 묶임. 잔여 L-series:
- L4: Scene 3D 실 DEM + actor 위치 (PyVista QtInteractor lazy create, headless CI 회피)
- L5: PluginMgr stage slot list + StageIO record toggle
- L6: Properties context form + ScopePOV cross-hair

## 4. 운영 학습 (1개)

1. **pyqtgraph ImageItem.boundingRect() 가 local pixel rect 반환** —
   `setRect(x, y, w, h)` 는 QTransform 으로 pixel→data 좌표 매핑하지만,
   `boundingRect()` 만 보면 (0, 0, n_cols, n_rows) 의 unit-pixel rect.
   데이터 좌표 검증은 `item.mapRectToParent(item.boundingRect())` 또는
   `item.mapRectToView()` 로 transform 적용 후 확인. ImageItem 의 axis
   calibration 검증 시 흔한 함정.

## 5. 다음 cycle 후보 (자동 모드 계속이면)

| 우선 | 작업 | 크기 | 비고 |
|---|---|---|---|
| 1 | **L4: Scene 3D PyVista QtInteractor + DEM mock** | 큼 | PhysicsLab 9.1d 의 ``enable_3d_viewer=False`` 패턴 (lazy create + headless CI bypass) 그대로 재활용. `MockSceneGenerator` (radar position + target position + DEM placeholder mesh). pyvistaqt 가 dependency. |
| 2 | **L5: PluginMgr stage list + StageIO record toggle 본격화** | 중 | tick_completed 무관 — Pipeline 의 PluginScanner 결과 받아 stage list 채우기 + StageIO 의 record 버튼이 ProbeRecorder 와 연결. Pipeline binding 필요해서 mock 가능. |
| 3 | **L6: Properties context form + ScopePOV cross-hair** | 중 | properties_panel 이 selection-driven, ScopePOV 가 boresight cross-hair canvas. |

L4 가 가장 사용자 가시 (3D 카메라 컨트롤). L5/L6 는 Pipeline 통합 후속에
더 자연스러움 — L4 먼저 가는 게 추천.

## 6. 이 cycle commit (origin/main)

```
(이 commit hash) feat(ui): Phase 4 L3 - Simulator RD panel pyqtgraph live heatmap
```
