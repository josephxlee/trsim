# Phase 4 cycle — L2 Simulator FFT panel pyqtgraph live spectrum (2026-05-14)

직전 cycle (L1 Run panel 실 sim_time) 이어서 Simulator 8 panel 중 두 번째 panel
에 실 데이터 binding. plan/04 § 4.3 의 Phase 4 UI 실 데이터 binding 우선순위
첫 핵심 plot ("Simulation 가장 시급" 사용자 명시) 의 두 번째 sub-step.

## 0. 한 줄 요약

- HEAD = (이 cycle commit).
- 누적 **2559 PASS** local (2518 → 2559, **+41 신규**).
- 5 contracts KEPT. ruff / mypy --strict / import-linter all clean.
- 1 sub-step direct push origin/main.

## 1. sub-step 표

| sub | new tests | 범위 |
|---|---|---|
| L2 | +41 | (a) `app/simulator/mock_spectrum.py` 신규 — `MockSpectrumGenerator` (deterministic sim_t_s → up/down sweep beat spectrum, sinusoidal peak motion, Gaussian noise floor seeded by quantised sim_t_s ^ rng_seed) + `MockSpectrumFrame` frozen dataclass. (b) `panels/fft_panel.py` placeholder QFrame 제거 → `pg.PlotWidget` 임베드 + 2 PlotDataItem (up=#d62728 red, down=#1f77b4 blue) + 2 InfiniteLine peak markers (DashLine, hidden by default) + `set_spectrum(freqs_hz, up_mag_db, down_mag_db)` + `set_peak_freqs(up_hz, down_hz)` + `clear_peak_freqs()`. Phase 4.9 헤더 API (set_frame / set_peak_counts) 보존. (c) `ui/simulator/fft_controller.py` 신규 — `SimulatorFFTController(QObject)` (run_controller.tick_completed → mock generator → panel push, enabled toggle, paint_for headless 진입점). (d) SimulatorWorkspace 가 RunController 생성 직후 FFTController 인스턴스화 + `fft_controller()` accessor. |

## 2. MVP_STATUS 매트릭스 변경

| 행 | before | after |
|---|---|---|
| Simulator panels (FFT / RD / Run / Properties / PluginMgr / StageIO) | △ (Run panel ✓ L1; 나머지 5 panel placeholder) | △ (Run panel ✓ L1; FFT panel = pyqtgraph 2-curve + peak markers + MockSpectrumGenerator live binding ✓ L2; 나머지 4 panel placeholder) |

## 3. 사용자 우선순위 (변동 없음)

> **physics_lab > simulator > editor** — 사용자 "Simulation 가장 시급" 명시
> Simulator 8 panel 의 실 데이터 binding 이 잔여 작업 1순위.

이 cycle 후 잔여 L-series:
- L3: RD panel range-doppler matrix (pyqtgraph ImageItem)
- L4: Scene 3D 실 DEM + actor 위치 (PyVista QtInteractor lazy create)
- L5: PluginMgr stage slot list + StageIO record toggle
- L6: Properties context form + ScopePOV cross-hair

## 4. 운영 학습 (2개)

1. **PySide6 의 ``QPen.setStyle`` 가 raw int 거부** — `pyqtgraph.mkPen(..., style=2)`
   는 PySide6 6.11 의 strict-typed signature 에 의해 `TypeError: 'QPen.setStyle'
   called with wrong argument types: int`. `Qt.PenStyle.DashLine` (또는
   `Qt.PenStyle.SolidLine` 등) enum 사용 필수. ImageView / InfiniteLine 등
   pyqtgraph wrapper 도 동일.

2. **ruff RUF046 — Python 3 의 `round()` 는 이미 int 반환** — `int(round(x))`
   는 redundant cast. `round(x * 1.0e6)` 으로 충분 (np.int_ 호환). 만약
   진짜 float 결과가 필요하면 `round(x, ndigits=N)` 패턴.

## 5. 다음 cycle 후보 (자동 모드 계속이면)

| 우선 | 작업 | 크기 | 비고 |
|---|---|---|---|
| 1 | **L3: RD panel range-doppler 2D heatmap** | 중 | pyqtgraph ImageItem + 2D mock heatmap. L2 의 MockSpectrumGenerator 와 짝꿍 mock — `MockRangeDopplerGenerator` (range bins × doppler bins 2D, target peak 가 sim_t_s 따라 cell 이동). `RangeDopplerPanel` 갱신 + `SimulatorRDController`. |
| 2 | **L4: Scene 3D PyVista QtInteractor lazy create** | 큼 | 헤드리스 CI 회피 패턴은 Physics Lab 9.1d 의 ``enable_3d_viewer=False`` 동일. DEM mesh placeholder. |
| 3 | L5 / L6 | 큼 | 여러 cycle 분할. |

L3 가 가장 자연 — L2 의 mock generator + controller 패턴 그대로 재활용.

## 6. 이 cycle commit (origin/main)

```
(이 commit hash) feat(ui): Phase 4 L2 - Simulator FFT panel pyqtgraph live spectrum
```
