# Phase 9.1 모두 완료 인계 — Physics Lab 본체 (2026-05-12)

이 세션에서 plan/19 § 19.5 / § 19.6 / § 19.7 / § 19.11.2 Phase 9.1 의
7 sub-step (9.1a~9.1g) 을 모두 끝냄. 다음 세션이 5분 안에 따라잡고
**Phase 9.2 (외부 자료 + 학습)** 부터 자동 진행하기 위한 짧은 인계.

## 0. 현재 상태 (한 줄)

- HEAD = `46e1d64` (`feat(physics-lab): Phase 9.1f/g — Library
  categories + Air Drag demo`)
- 누적 **1850 PASS** local (+158 신규 across 9.1a-g)
- ruff / mypy strict / import-linter 5 contracts KEPT 매 commit
- 이 세션 8 commits main 직접 push

## 1. 사용자 설계 우선순위 (변동 없음)

> **physics_lab > simulator > editor**
>
> Physics Lab = 시뮬 물리 수식·개념의 **증명** + **시각 검증** +
> 사용자가 시뮬에 추가하고 싶은 수식 **시험**.
>
> 후속 Phase 우선순위:
> 1. **Phase 9.2** (외부 자료 + 학습) — 다음 세션 진입점.
> 2. Phase 9.3 (고급 기능 — Code Pane Edit 강화, PhysicsModelProtocol
>    plugin, NN 으로 물리 대체, Symbolic regression, Test Object plugin).
> 3. Phase 5 후속 (도메인 정량 보강).
> 4. NN 보강 (Adam / workbench-train / Step 2 행).
> 5. Phase 8 HIL.
> 6. DLC CLI (install / sdk build).
> 7. UI 데이터 binding (Editor 5 activity / Simulator 8 panel 실 데이터).
> 8. Floating dock 옵션 B / Theme manager.

## 2. 이 세션 누적 push (8 commits)

| commit | 단계 |
|---|---|
| `f07781f` | Phase 9.1a — Code Pane Python syntax highlight |
| `2bbce62` | Phase 9.1b — Frame slider + step-by-step controls |
| `7f94e31` | Phase 9.1c — `@physics_param` decorator + auto sliders |
| `a50d7be` | docs handoff (9.1a/b/c 묶음) |
| `ac1b675` | Phase 9.1d — PyVista 3D Test Object viewer |
| `10811a9` | Phase 9.1e — 4 time modes (Static / Run / Compare / Sweep) |
| `46e1d64` | Phase 9.1f/g — Library categories + Air Drag demo |

## 3. 다음 세션 진입점 — Phase 9.2

plan/19 § 19.11.2 의 Phase 9.2 4 task:

| # | task | 범위 | 추정 |
|---|---|---|---|
| **9.2a** | Library Measured Data 업로드 | CSV/HDF5 파일 import → Library 4번째 카테고리로 추가 + 메타 (column/units/source). | 2 sub-step |
| **9.2b** | Library Papers (PDF) 업로드 | PDF 파일 import → Library 5번째 카테고리 + 메타 (title/year/authors). 미리보기는 외부 viewer launch. | 1 sub-step |
| **9.2c** | Lab-B Validation Bench | 측정 vs 시뮬 RMSE 계산 + overlay plot. | 2 sub-step |
| **9.2d** | Lab-C Parameter Studio | `scipy.optimize` (curve_fit / minimize) 로 시뮬 params 가 측정에 맞도록 fit. | 2 sub-step |

총 **7 sub-step**. plan/19 § 19.12.2 시나리오 2 (RCS 측정 검증) 가
9.2 end-to-end 의 reference example.

분할 권고:
- 9.2a + 9.2b 한 묶음 (Library 카테고리 확장 + 파일 import 기본 인프라).
- 9.2c 한 묶음 (Validation Bench 단독, RMSE + overlay).
- 9.2d 한 묶음 (Parameter Studio — scipy 통합 + 사용자 검토 워크플로).

## 4. Phase 9.1 구조 요점 (다음 세션이 활용)

### 4.1 Physics Lab workspace 현재 위치

`PhysicsLabWorkspace` (`src/workbench/ui/physics_lab/workspace.py`)
는 다음 5 panel 을 host 한다:

1. **Library** (좌측) — QTreeWidget, 3 카테고리 + Save 버튼
2. **Code** (중앙 상단) — QTextEdit + PythonSyntaxHighlighter +
   Edit/Save&Reload/Revert 3 버튼
3. **Visualization** (중앙 하단) — QStackedWidget
   * idx 0: BouncingBallPlot (pyqtgraph 2D, multi-curve)
   * idx 1: TestObject3DPanel (pyvistaqt 3D, lazy-created)
4. **Parameters** (우측) — AutoParametersWidget (5 슬라이더 from
   BOUNCING_BALL_PARAM_SPECS)
5. **Time controls** (하단) — 2 row layout
   * Row 1: Mode combo (4 modes) + Play / Pause / Stop + status
   * Row 2: Prev | Frame slider | Next | frame readout

9.2 가 추가할 것:
- **Library 4번째 카테고리** "Measured Data" (CSV/HDF5)
- **Library 5번째 카테고리** "Papers" (PDF)
- 새 Workspace mode "Validation Bench" — viz_stack 에 3번째 widget
  (overlay + RMSE 표시 plot) 추가 권고.
- "Parameter Studio" workflow — Parameters Pane 우측에 fit 결과 패널
  추가.

### 4.2 LibraryWidget 확장 패턴

```python
# 신규 카테고리 추가 위치 (bouncing_ball_demo.py)
self._measured_item = QTreeWidgetItem(self._tree, [self.CATEGORY_MEASURED])
self._papers_item = QTreeWidgetItem(self._tree, [self.CATEGORY_PAPERS])
```

Save/load TOML 패턴 그대로 활용 가능 (예:
`domain/physics_lab/measured_data.py` 가 CSV 메타 → TOML 저장).
Saved Experiments 의 `set_saved_experiments` / `experiment_for` 패턴
재사용.

### 4.3 SavedExperiment 확장

현재 schema:
```toml
[experiment]
id = "..."
description = "..."
mode = "run"

[parameters]
gravity_m_s2 = 9.81
restitution = 0.7
initial_height_m = 5.0
initial_velocity_m_s = 0.0
drag_coefficient_k = 0.0
```

9.2 가 추가할 것: Parameter Studio fit 결과를 SavedExperiment 에
추가 필드로 저장 (예: `fit_rmse = 0.42`, `fit_target_dataset =
"..."`). Legacy fallback 패턴 그대로 (key 없으면 0.0).

### 4.4 BouncingBallSimulator 5 parameter

```
BOUNCING_BALL_PARAM_SPECS = (
    gravity_m_s2:        linear  [1, 30]    default 9.81  unit m/s^2
    restitution:         linear  [0, 1]     default 0.70  unit -
    initial_height_m:    log     [0.1, 50]  default 5.0   unit m
    initial_velocity_m_s: linear [-20, 20]  default 0.0   unit m/s
    drag_coefficient_k:  linear  [0, 1]     default 0.0   unit 1/m
)
```

9.2 Parameter Studio 의 scipy.optimize 가 이 5 차원 파라미터 공간에서
fit 수행. min/max 가 bounds, default 가 initial guess 권장.

### 4.5 4 time modes

- **Static**: transport disabled, 단일 frame 시각화.
- **Run**: 현재 PL-D 흐름.
- **Compare**: `analytic_peak` overlay curve 자동 생성 (h_n = r^(2n)·h0).
  9.2 Validation Bench 가 이 패턴 확장 — overlay 가 "measured" 또는
  "fit result" curve 가 됨.
- **Sweep**: 4 sibling simulator (r=0.3/0.5/0.7/0.9) 동시 실행.
  Parameter Studio 의 fit 진행 시각화에 활용 가능.

## 5. 9.2 진입 시 우선 검토 사항

1. **CSV/HDF5 로더 표준**: NN dataset 의 HDF5 read_dataset 패턴
   (`app/nn/data_exporter.py`) 재사용 가능. CSV 는 numpy.loadtxt
   또는 pandas (이미 의존성?). 의존성 확인 필요.
2. **scipy.optimize**: 이미 의존성 (Phase 5 사용 중). curve_fit
   API 로 5-param fit 가능. Parameter Studio 는 별도 controller
   클래스로 빼는 게 좋음.
3. **PDF 표시**: PyMuPDF (fitz) 또는 외부 viewer launch. plan/19
   는 외부 viewer launch 권고 (간단). MVP 는 그대로 가자.
4. **Library 카테고리 N=5** 가 너무 많아지면 scroll 부담. 9.2 시점에
   "기본 펼침/접힘" 정책 결정 필요.

## 6. 후속 Phase 진입점 (변동 없음)

### Phase 9.3 — 고급 기능 (plan/19 § 19.11.2)
- Code Pane Edit mode 강화 (autocomplete + 다중 함수 + import +
  `@physics_param` 직접 작성)
- PhysicsModelProtocol plugin (사용자 정의, 11번째 SDK protocol)
- NN 으로 물리 대체 (form 2, Phase 6 NN 결합)
- Symbolic regression (PySR)
- Test Object plugin

### Phase 5 후속 (도메인 정량 보강)
- ExtendedTarget σ_glint RMS 정량 회귀
- High-g UKF/EKF RMSE 정량
- Multipath/horizon golden 추가 case

### NN 보강
- Adam optimiser (numpy_mlp 후속)
- workbench-train 외부 subprocess wrapping
- Step 2 Tracker/Predictor/Classifier 행 채우기
- NN mode "DSP / NN Development" mode selector

### Phase 8 HIL
- TCP/JSON DUTAdapter + Lock-step Handshake
- L5 비교 (GT/SIL/HIL 3-way)

### DLC CLI
- trsim install <pkg>.trsim-pkg
- trsim sdk build <dir>
- Editor "Install Package..." 메뉴

### UI 실 데이터 binding (큰 phase)
- Editor 5 activity ↔ ResourceLibrary
- Simulator 8 panel ↔ SimulationClock + RadarPipeline.step
- Scene3D PyVista 임베드 (placeholder → 실 canvas)
- Scope POV cross-hair canvas
- FFT / Range-Doppler pyqtgraph binding

### 부수
- Floating dock 옵션 B (nested QMainWindow)
- Theme manager (ui/theme.py 중앙 다크 팔레트)

## 7. 작업 환경 (이미 검증된)

| 항목 | 값 |
|---|---|
| OS | Windows |
| repo root | `C:\Workspaces\Claude\Tracking Radar Simulator\trsim` |
| Python | 3.13.3 (.venv) |
| 주요 의존 | PySide6 6.11.0, pyqtgraph 0.13.x, **pyvista 0.48.1**, **pyvistaqt 0.11.4**, numpy, h5py, scipy, pytest 9.0.3, pytest-qt 4.5.0, ruff, mypy 2.0, import-linter, typing_extensions |
| 실행파일 | `.venv\Scripts\trsim.exe` (= `python -m workbench`) |
| Push 권한 | `.claude/settings.local.json` `Bash(git push origin HEAD:main)` allow 등록 — 자동 push OK |

## 8. 운영 학습 (이 세션 9.1d~g 추가)

1. **pyvistaqt QtInteractor + pytest** — 단일 instance 는 OK 지만
   pytest-qt 의 `_process_events` 가 다중 instance 의 GL 컨텍스트와
   race 해서 `vtkWin32OpenGLRenderWindow: failed to get valid pixel
   format` access violation 을 발생시킴. 회피: workspace 에
   `enable_3d_viewer=False` kwarg 추가 + 테스트 default False +
   3D panel **lazy creation** (첫 클릭 시). conftest 에서
   `pyvista.OFF_SCREEN = True` 셋팅 필수.
2. **TestObject3DPanel 클래스명 + pytest 충돌** — 클래스 이름이
   `Test` 로 시작하면 pytest 가 test class 로 collect 시도. `__test__
   = False` 클래스 변수로 suppress.
3. **inspect.getsource + method form** (PL-E 재확인) — `inspect.
   getsource(Cls.method)` 는 indented method (with `self`), module-
   level exec 불가. Code edit mode 에서 scaffold form 으로 변환 필요.
4. **TestObject Union 타입** — domain layer 에서 정의해야 UI 가
   pyvistaqt import 없이 type alias 사용 가능. 도메인이 시각화
   의존 안 한다는 Contract 3 도 유지.
5. **multi-curve plot 백워드 호환** — `BouncingBallPlot.append /
   set_history / clear_history` 가 primary curve 에 delegate. 새
   `add_overlay_curve / append_to / set_history_of` API 추가. 기존
   API 사용 코드 무수정.
6. **decorator stacking + insert(0, ...)** — `@physics_param` 가
   `insert(0, param)` 으로 prepend 하면 outer decorator 가 나중에
   실행되며 결과 list 는 source-line order. 5번째 spec 추가 시 새
   decorator 만 stack 맨 위에 추가하면 자동 끝에 추가됨.
7. **SavedExperiment legacy fallback** — `read_saved_experiment` 가
   key 누락 시 default 값 (0.0 등) 사용 → backward compat. 9.2/9.3
   가 새 field 추가 시 같은 패턴.

## 9. 다음 세션 진입 명령

```bash
cd "C:/Workspaces/Claude/Tracking Radar Simulator/trsim"
git pull --ff-only
PY=".venv/Scripts/python.exe"
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m pytest -q
# 1850 PASS expected
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/lint-imports.exe
# 5 contracts KEPT
```

그 다음:
1. CLAUDE.md § 1 + 이 handoff (`docs/sessions/phase_9_1_complete_
   handoff_2026_05_12.md`) 정독 (5 분).
2. `plan/19_physics_lab.md` § 19.9 (Library) + § 19.10 (Lab-B/C) +
   § 19.12.2 (RCS 측정 검증 시나리오) 정독 (10 분).
3. **Phase 9.2a + 9.2b 한 묶음 진입** — Library Measured Data + Papers
   카테고리 + import 인프라. 약 2 commit.

세션 컨텍스트 80% 도달 시 또 새 handoff 작성 + 종료. 9.2 / 9.3 모두
끝날 때까지 반복.

## 10. 문서 위치 정리

| 문서 | 용도 |
|---|---|
| `docs/MVP_USAGE.md` | 사용 가이드 |
| `docs/MVP_GUIDE.md` (rev8) | 검증 가이드 (7 섹션 + checklist) |
| `docs/MVP_STATUS.md` | top-down gap report |
| `docs/sessions/phase_5_6_7_2026_05_11_handoff.md` | 3 전 세션 인계 |
| `docs/sessions/phase_mvp_a_handoff_2026_05_12.md` | 2 전 세션 인계 (PL-A~E + MVP wrap) |
| `docs/sessions/phase_9_1_abc_handoff_2026_05_12.md` | 직전 핵심 인계 (9.1a/b/c 묶음) |
| `docs/sessions/phase_9_1_complete_handoff_2026_05_12.md` | **이 인계** (Phase 9.1 전부) |
| `CLAUDE.md` § 1 | 누적 진행 log |
| `README.md` | status |
| `plan/19_physics_lab.md` | Physics Lab 설계 (1000+ 줄) |
