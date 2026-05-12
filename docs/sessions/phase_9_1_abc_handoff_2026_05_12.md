# Phase 9.1a/b/c 인계 — Code highlight + Frame slider + Auto sliders (2026-05-12)

이 세션에서 plan/19 § 19.5.3 / § 19.5.4 / § 19.5.5 의 Code Pane
syntax highlight + Time controls Frame slider + Parameters Pane 자동
슬라이더 (`@physics_param` 인프라) 까지 완료. 다음 세션이 5분 안에
따라잡고 **Phase 9.1d/e 묶음** 부터 자동 진행하기 위한 짧은 인계.

## 0. 현재 상태 (한 줄)

- HEAD = `7f94e31` (`feat(physics-lab): Phase 9.1c — @physics_param
  decorator + auto sliders`)
- 누적 **1773 PASS** local (+81 신규: 31 highlighter + 14 frame
  slider + 36 auto sliders)
- ruff / mypy strict / import-linter 5 contracts KEPT 매 commit
- 이 세션 3 commits main 직접 push (f07781f → 2bbce62 → 7f94e31)

## 1. 사용자 설계 우선순위 (변동 없음)

> **physics_lab > simulator > editor**
>
> Physics Lab = 시뮬 물리 수식·개념의 **증명** + **시각 검증** +
> 사용자가 시뮬에 추가하고 싶은 수식 **시험**.
>
> 후속 Phase 우선순위:
> 1. Phase 9.1d / 9.1e / 9.1f / 9.1g (Physics Lab 본격 — 잔여 4
>    sub-step)
> 2. Phase 9.2 (외부 자료 + 학습 — Library Measured Data, Papers,
>    Lab-B Validation Bench, Lab-C Parameter Studio)
> 3. Phase 9.3 (고급 기능 — Code Pane Edit 강화, PhysicsModelProtocol
>    plugin, NN 으로 물리 대체, Symbolic regression, Test Object plugin)
> 4. Phase 5 후속 (도메인 정량 보강)
> 5. NN 보강 (Adam / workbench-train / Step 2 행)
> 6. Phase 8 HIL
> 7. DLC CLI (install / sdk build)
> 8. UI 데이터 binding (Editor 5 activity / Simulator 8 panel 실 데이터)
> 9. Floating dock 옵션 B / Theme manager

## 2. 이 세션 누적 push (3 commits)

| commit | 단계 |
|---|---|
| `f07781f` | Phase 9.1a — Code Pane Python syntax highlight |
| `2bbce62` | Phase 9.1b — Frame slider + step-by-step controls |
| `7f94e31` | Phase 9.1c — `@physics_param` decorator + auto sliders |

## 3. 다음 세션 진입점 — Phase 9.1d/e 묶음

`docs/sessions/phase_mvp_a_handoff_2026_05_12.md` § 3 의 표대로 잔여
sub-step:

| # | sub-step | 범위 | 추정 |
|---|---|---|---|
| **9.1d** | 9 Test Object 3D mesh | PyVista QtInteractor 임베드 + Sphere/Cube/.../Trihedral 각 mesh + 카메라 control. plan/19 § 19.7.3 의 `pv.Sphere/pv.Cube/...` 활용. Library 에서 Test Object row 클릭 시 viz panel 이 2D y(t) plot → 3D mesh 로 swap. | 2 sub-step |
| **9.1e** | 4 시간 모드 (Static / Run / Compare / Sweep) | 모드 selector QComboBox + Static (정지 상태 viz), Run (현재), Compare (분석 공식 overlay — plan/19 § 19.6.3 의 "BALLISTIC 분석 vs RK4"), Sweep (parameter range 자동 sweep + multi-trajectory plot). plan/19 § 19.6. | 2 sub-step |
| **9.1f** | Library 카테고리 분리 | Tests / Models / Saved Experiments 트리 + Save Experiment 기능 (현재 demo state → TOML 저장). | 1 sub-step |
| **9.1g** | "Free Fall with Air Drag" 두 번째 demo | Air drag toggle + drag coefficient slider. plan/19 § 19.12.1 의 첫 예시 완성 ("Gravity + Bouncing Ball + Air Drag"). | 1 sub-step |

총 **6 sub-step**. 1 세션에 모두 끝내기 어려우니 9.1d / 9.1e 한 묶음,
9.1f / 9.1g 한 묶음 으로 2 commit 분할 권고.

## 4. 9.1c 구조 요점 (다음 세션이 활용)

### 4.1 `@physics_param` 인프라

```python
# domain/physics_lab/parameter_metadata.py
@physics_param("mass_kg", min_value=0.1, max_value=10.0, scale="log",
               unit="kg", default=1.0)
@physics_param("drag_coef", min_value=0.0, max_value=2.0, default=0.47)
def some_simulator_marker() -> None: ...

specs = get_physics_params(some_simulator_marker)
# (PhysicsParam('mass_kg', ...), PhysicsParam('drag_coef', ...))
```

- `SLIDER_TICK_RESOLUTION = 100` — 모든 slider 공통 (`linear` 100
  step, `log` 100 step per decade-span).
- 9.1d/e/g 가 새 simulator (예: Free Fall with Air Drag, Test Object
  RCS) 추가 시 같은 패턴으로 `@physics_param` 누적 → `AutoParametersWidget(spec)`
  → 자동 슬라이더.

### 4.2 `BouncingBallController.history`

- `_history: list[BouncingBallState]` + `_history_index: int` 가
  authoritative timeline.
- `step_forward_once / step_backward_once / seek_to_frame` 가 cursor
  이동 + plot 동기화.
- Compare 모드 (9.1e) 가 history 옆에 두 번째 history (예: analytic
  reference) 를 함께 plot 하는 패턴으로 확장 가능.

### 4.3 `BouncingBallPlot` (2D y(t))

- `append(t, y)` / `set_history(times, ys)` / `clear_history()` API.
- 9.1d 에서 3D mesh widget (예: `Test3DPanel`) 을 별도 클래스로 만들
  고, viz panel 이 `QStackedWidget` 에 둘 다 mount + Library 선택
  signal 로 switch.

### 4.4 `AutoParametersWidget` (4 param visible)

- ParametersWidget 이 자동 4 슬라이더 노출 — 다음 세션에서
  initial_height / initial_velocity 슬라이더를 simulator 재시작에
  연결하는 wiring 추가 권고 (현재는 표시만, 실제 simulator 미반영).

## 5. 후속 Phase 진입점 (변동 없음)

### Phase 9.1d/e/f/g — Lab 본체 마무리 (plan/19 § 19.5 / § 19.6 / § 19.7)
- 9.1d: PyVista QtInteractor 임베드 + 9 Test Object 3D mesh
- 9.1e: 4 시간 모드 (Static / Run / Compare / Sweep)
- 9.1f: Library 카테고리 분리 (Tests / Models / Saved Experiments)
- 9.1g: Free Fall with Air Drag 두 번째 demo

### Phase 9.2 — 외부 자료 + 학습 (plan/19 § 19.11.2)
- Library Measured Data 업로드 (CSV/HDF5)
- Library Papers (PDF) 업로드
- Lab-B Validation Bench (측정 vs 시뮬 RMSE)
- Lab-C Parameter Studio (scipy.optimize fit)
- 사용자 검토 → 채택 워크플로 (학습된 파라미터 → 시뮬 시나리오 사용)

### Phase 9.3 — 고급 기능
- Code Pane Edit mode 강화 (autocomplete + 다중 함수 + import +
  `@physics_param` 직접 작성)
- PhysicsModelProtocol plugin (사용자 정의, 11번째 SDK)
- NN 으로 물리 대체 (form 2, Phase 6 NN 결합)
- Symbolic regression (PySR)
- Test Object plugin

### 그 외 (변동 없음)
- Phase 5 후속, NN 보강 (Adam / workbench-train / Step 2 행), Phase
  8 HIL, DLC CLI, UI 실 데이터 binding, Floating dock 옵션 B, Theme
  manager — 전 세션 인계 § 4 그대로.

## 6. 작업 환경 (이미 검증된)

| 항목 | 값 |
|---|---|
| OS | Windows |
| repo root | `C:\Workspaces\Claude\Tracking Radar Simulator\trsim` |
| Python | 3.13.3 (.venv) |
| 주요 의존 | PySide6 6.11.0, pyqtgraph 0.13.x, **pyvista 0.48.1**, **pyvistaqt 0.11.4**, numpy, h5py, scipy, pytest 9.0.3, pytest-qt 4.5.0, ruff, mypy 2.0, import-linter, typing_extensions |
| 실행파일 | `.venv\Scripts\trsim.exe` (= `python -m workbench`) |
| Push 권한 | `.claude/settings.local.json` `Bash(git push origin HEAD:main)` allow 등록 — 자동 push OK |

PyVista 가 설치돼 있으니 9.1d 의 PyVista QtInteractor 임베드는 환경
세팅 없이 진행 가능. import-linter Contract 5 (pyvista-isolation) 는
현재 비활성 — Contract 5 활성 여부는 plan/02 § 2.5 의 정책에 따라
9.1d 끝에 재검토 (현재 plan/19 / .importlinter 그대로 비활성 유지
권고).

## 7. 운영 학습 (이 세션)

1. **Docstring 안에 `"""` 가 들어가면 일찍 종료된다** — Python parser
   는 escape 없는 `"""` 를 docstring 닫는 토큰으로 간주. RST 표
   안에 `\`\`"""\`\`` 처럼 백틱으로 감싸도 raw bytes 에 `"""` 가
   3 consecutive 로 등장하므로 parser 가 깨짐. 회피: 표 row 를
   문장으로 풀어 쓰거나, `\"\"\"` escape 사용.
2. **mypy 2.0 + Python 3.13 `typing.override`** — mypy 가
   `typing.override` 를 인식 못함 (`Use 'typing_extensions.override'
   instead` 권고). 항상 `from typing_extensions import override`
   사용.
3. **QSyntaxHighlighter format inspection** — `block.layout().formats()`
   는 paint pass 후에만 채워짐. 테스트가 highlighter 적용을 확인
   하려면 `rehighlight()` 명시 호출 + `block.userState()` 검증 패턴
   사용 (pure-Python tokeniser 를 분리해 두면 Qt 없이 검증 가능).
4. **QSlider valueChanged 재귀 방지** — slider 값을 `setValue` 로
   되돌릴 때 `blockSignals(True)` 로 valueChanged 차단 후 복원.
5. **PhysicsParam tick 양자화** — 100 tick 으로 default 9.81 같은
   비정수 값을 표현하면 9.7 같은 미세 오차. 테스트에서 default
   round-trip 은 `pytest.approx(rel=0.02)` 정도 허용 권고.

## 8. 다음 세션 진입 명령

```bash
cd "C:/Workspaces/Claude/Tracking Radar Simulator/trsim"
git pull --ff-only
PY=".venv/Scripts/python.exe"
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m pytest -q
# 1773 PASS expected
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/lint-imports.exe
# 5 contracts KEPT
```

그 다음:
1. CLAUDE.md § 1 + 이 handoff (`docs/sessions/phase_9_1_abc_handoff_
   2026_05_12.md`) 정독 (5 분).
2. `plan/19_physics_lab.md` § 19.6 (4 시간 모드) + § 19.7 (9 Test
   Object) + § 19.7.3 (3D viz) 정독 (10 분).
3. **Phase 9.1d + 9.1e 한 묶음 진입** — PyVista 3D mesh + 4 시간
   모드. 약 2 commit.

세션 컨텍스트 80% 도달 시 또 새 handoff 작성 + 종료. 9.1d/e/f/g 모두
끝날 때까지 반복.

## 9. 문서 위치 정리

| 문서 | 용도 |
|---|---|
| `docs/MVP_USAGE.md` | 사용 가이드 |
| `docs/MVP_GUIDE.md` (rev8) | 검증 가이드 (7 섹션 + checklist) |
| `docs/MVP_STATUS.md` | top-down gap report |
| `docs/sessions/phase_5_6_7_2026_05_11_handoff.md` | 2 전 세션 인계 |
| `docs/sessions/phase_mvp_a_handoff_2026_05_12.md` | 직전 세션 인계 (PL-A~E + MVP wrap) |
| `docs/sessions/phase_9_1_abc_handoff_2026_05_12.md` | **이 인계** |
| `CLAUDE.md` § 1 | 누적 진행 log |
| `README.md` | status |
| `plan/19_physics_lab.md` | Physics Lab 설계 (1000+ 줄) |
