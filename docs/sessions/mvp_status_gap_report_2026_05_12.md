# MVP 가동 검증 결과 + Top-down Gap 보고 (2026-05-12)

사용자가 [`docs/MVP_GUIDE.md`](MVP_GUIDE.md) 따라 검증한 결과, 다수
항목 fail. 원인 분석 + 진짜 MVP 진행 상태 정리.

## 0. 사용자 보고 사항

| 항목 | 결과 | 1차 진단 |
|---|---|---|
| 1.1 `trsim ui --help` 에 `--no-dlc` 없음 | FAIL | 코드 = 동기화 |
| 2.1 pytest 1484 PASS (1570 기대) | FAIL | 코드 = 동기화 |
| 2.2 ruff 1 파일 재포맷 필요 | FAIL | 코드 = 동기화 |
| 3.2 Ctrl+Shift+E/S 단축키 안 됨 | FAIL | 단축키 충돌 (의심) |
| 3.6 Ctrl+Shift+P 안 됨 | FAIL | 단축키 충돌 (의심) |
| 4.2 DLC bottom tab 등장 안 함 | FAIL | 코드 = 동기화 |
| 4.3 user resource sidebar 등장 안 함 | FAIL | 코드 = 동기화 |
| 4.4 `--no-dlc` 실행 안 됨 | FAIL | 코드 = 동기화 |
| 5. NN 모드 없음 | FAIL | **진짜 누락** |
| 기타 1. 패널 floating | 미구현 | **설계 부재** |
| 기타 2. Physics workspace | 미구현 | **MVP+α (v0.40)** |

5 / 기타 1 / 기타 2 는 **동기화로 해결 안 되는 진짜 MVP 누락**.

---

## 1. 동기화 (사용자 측) — 가장 큰 단일 원인

### 1.1 증거

```
사용자 local main HEAD : 729875f (docs: session handoff)
worktree HEAD          : 41381b9 (MVP_GUIDE)
delta                  : 6 commits ahead on origin/main
```

사용자가 push 후 local main 으로 `git pull` 안 함. `trsim.exe` 가
`pip install -e .` editable mode 라 src/ 변경 자동 반영되지만,
src/ 가 옛 commit 그대로.

### 1.2 누락된 6 commits

| commit | 효과 |
|---|---|
| `c297800` Phase 7.6 | `MainWindow(dlc_runtime=...)` + Editor sidebar populate |
| `96842cd` Task B | Step 1 panel Build-mode 콤보 + variant chain |
| `d3c247e` Task C | TrainerService `backend="numpy_mlp"` |
| `025a168` Task D | Simulator bottom_tabs DLC mount + `--no-dlc` 인자 자체는 여기 미포함 |
| `ae960d4` MVP wrap-up | `trsim ui --no-dlc` 인자 + `build_ui_window` |
| `41381b9` docs MVP_GUIDE | 검증 가이드 |

### 1.3 사용자 측 조치 (3 명령)

```powershell
cd "C:\Workspaces\Claude\Tracking Radar Simulator\trsim"
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
```

`pip install -e . --no-deps` 가 console-script wrapper (`trsim.exe`)
재생성 + editable egg-link 갱신. dev extras 는 이미 깔려있으니
`--no-deps` 면 빠름.

이후:
- `trsim --version` → 새 trsim ui 헬프에 `--no-dlc` 표시
- `pytest -q` → 1570 PASS
- `trsim ui` → DLC 자동 mount + sidebar populate

이걸로 0.X, 1.x, 2.x, 4.x 다수 해결.

---

## 2. 진짜 MVP 누락 — 코드 자체에서 빠진 것

### 2.1 NN 모드 UI 진입경로 **0** ❌ ★

**현황**:
- `src/workbench/ui/simulator/nn_mode/` 안에 `Step1DatasetPanel`,
  `Step2EvalPanel`, `NNStep1Controller`, `NNStep2Controller` 모두
  존재 (Phase 4.11 + 6.4c + 6.8 + Task B 에서 만듦)
- `src/workbench/ui/nn_training/` 안에 `TrainingPanel` +
  `NNTrainingController` 존재 (task 3)
- **그러나** `SimulatorWorkspace` / `EditorWorkspace` / `MainWindow`
  어디에서도 이 panel 들을 instantiate 하지 않는다.
- `grep "Step1DatasetPanel("` → step1_dataset.py 본인 1 곳뿐
- `grep "TrainingPanel("` → training_panel.py + training_controller.py 만

**검증**: `python -m workbench ui` 띄워도 NN Step 1/2 또는 Training
panel 에 접근할 UI 진입점 없음. `Simulator` 워크스페이스의 bottom
tabs 는 `Run / Stage I/O / Profiler` 3 개 (+ DLC 자동 tab) 만.

**원인**: Phase 4.11 commit message 가 명시함 — "Mode selector UI
통합은 Phase 4.12". 그런데 Phase 4.12 는 ProfilerPanel composite 가
되어버렸고 NN mode selector 미통합인 채 Phase 5+ 로 넘어감. 후속
sub-step (B/C/D, MVP wrap-up) 들도 panel mount 누락에 안 짚음.

**조치 옵션** (선택해야):
1. **(추천)** Simulator workspace bottom_tabs 에 NN Step1 / NN Step2
   / NN Training 3 개 tab 추가. 기존 Run/StageIO/Profiler 옆에.
2. Simulator workspace 에 "Mode" 라디오 (Operation vs NN) 추가하고
   NN mode 선택 시 별도 stack page 로 switch. plan/05 § 5.1 의
   principle 6 가 이걸 명시. 더 정석.
3. Editor 에 NN activity (Ctrl+6) 추가하고 Step1/Step2/Training 을
   sub-tab 으로. Editor 가 "데이터 만들기 + 학습 컨트롤" 에 자연.

### 2.2 단축키 충돌 의심 ⚠️

**현황**: `_build_workspace_actions` 가 toolbar QAction 에
`setShortcut("Ctrl+Shift+E/S")` + `MainMenuBar._attach` 가 같은
command 의 menu QAction 에도 같은 shortcut. **두 QAction 이 동일
shortcut 보유** → Qt 의 ambiguous shortcut 경고 + 둘 다 disable
가능성.

`palette.open` 도 `QShortcut(Ctrl+Shift+P, self)` + menu QAction
shortcut 중복.

**검증 필요**: 사용자 PC pull 후 재시도. 동기화로 어쩌면 해결될 수
도 있지만 (코드 변경 없음), 코드 자체 충돌이 그대로 남음. Qt 가
콘솔에 `"QAction::eventFilter: Ambiguous shortcut overload"` 경고
출력하면 확정.

**조치**: toolbar QAction 의 `setShortcut` 제거 (menu_bar 만 단독
보유) 또는 QShortcut 에 `setContext(Qt.ApplicationShortcut)`.

### 2.3 패널 floating 미구현 (설계 부재) 🟡

**현황**:
- `DockManager` (Phase 4.2d) 는 QDockWidget 으로 패널을 dock 으로
  등록 가능한 인프라.
- 그러나 실제 패널들 (Editor 5 activity, Simulator 8 panel) 은
  모두 `QSplitter` 안 fixed layout 으로 박혀있다.
- DockManager 가 어떤 패널도 실제로 dock 안 함 (register 호출 0).

**plan**: plan/05 § 5.2 + plan/13 § 13.2 에 floating dock window
관련 명시 0. 두 workspace 모두 fixed splitter layout 으로 설계됨.

**조치 옵션**:
- (MVP 외): 후속 phase 에서 DockManager 활용 → floating dock 지원.
- (MVP 가동 목표면): 현재 fixed layout 유지. 사용자 기대치 조정
  필요.

### 2.4 Physics Lab workspace = **MVP+α v0.40** 🟡

**plan/02 § 2.6c**: Physics Lab 은 **v0.40 신설** 디렉토리:
- `src/workbench/app/physics_lab/`
- `src/workbench/ui/physics_lab/`
- 3-pane 인터랙티브 + 9 Test Objects + 4 시간 모드 + 사용자 물리
  plugin (`PhysicsModelProtocol`)

**plan/04 § 4.3**: MVP 는 Phase 0~6. Phase 7 (DLC), Phase 8 (HIL),
Phase 9 (Physics Lab) 모두 MVP+α.

즉 Physics workspace 는 **의도된 부재** — MVP 후 v0.40 추가. 현
시점에서 없는 게 정상.

---

## 3. MVP 완성도 — 실제 layer 별 상태

| Layer | 항목 | 상태 |
|---|---|---|
| **CLI** | `trsim --version` | ✅ |
| | `trsim profile` | ✅ |
| | `trsim run` (placeholder loop) | 🟡 frame loop = MVP placeholder |
| | `trsim ui` + `--no-dlc` + `--workspace` | ✅ (pull 후) |
| **Editor workspace** | 5 Activity (Ctrl+1~5) | ✅ |
| | Resource Browser sidebar | ✅ |
| | ScenarioComposer | 🟡 4 블록 골격, 실 데이터 binding 미 |
| | Map editor | 🟡 5 tool 골격, pyqtgraph canvas 미 |
| | Radar editor | 🟡 폼 골격, beam preview canvas 미 |
| | Targets editor | 🟡 폼 + CSV I/O 골격, trajectory preview 미 |
| | Atmosphere panel | ✅ schema round-trip |
| **Simulator workspace** | 8 built-in panel (FFT/RD/Run/Properties/...) | 🟡 widget 골격, 실 데이터 binding 미 |
| | Scene3D PyVista 임베드 | ❌ placeholder canvas |
| | Scope POV cross-hair | ❌ placeholder canvas |
| | Profiler tab (Timing/Scale/Report) | 🟡 widget OK, 실시간 binding 미 |
| | DLC panel mount (bottom_tabs) | ✅ (pull 후) |
| | **NN mode (Step 1 / Step 2 / Training)** | ❌ **UI 진입경로 0** |
| **App layer** | DatasetBuilder + PipelineRunner | ✅ |
| | VariantBuildRunner (4-tier chain) | ✅ |
| | TrainerService (fake + numpy_mlp) | ✅ |
| | NNEvaluator 4-error | ✅ |
| | NumpyPairingNN baseline | ✅ |
| | DLC PackageManager + PluginLoader + ResourceLibrary | ✅ |
| | UI PanelRegistry | ✅ |
| **Domain / Physics** | FMCW Triangle + multipath + horizon + glint | ✅ (golden + invariant tests) |
| | EKF / UKF / GNN | ✅ |
| | CFAR (OS + CA) | ✅ |
| | Tracker scenario regression | ✅ |
| | Coherence validator | ✅ |
| **Single-process** | pytest 1570 PASS | ✅ |
| | ruff format + check + mypy strict | ✅ |
| | import-linter 5 contracts | ✅ |
| **Floating / docking** | QDockWidget actual mount | ❌ 미구현 (plan 도 미설계) |
| **Physics Lab workspace** | v0.40 신설 | ❌ MVP+α 영역 |

**범례**: ✅ 완성 / 🟡 골격만 (binding 미) / ❌ 없음

---

## 4. 결론

### 4.1 사용자 주장 검증

> "MVP를 만들다 중단한 것 같아"

**부분 정확**. 더 정확히는:

- **개발 + 검증** 은 단단함 — 1570 PASS, contracts KEPT.
- **App + Domain + Physics layer** 는 MVP 가 의도한 모든 기능을 보유.
- **CLI + 비-UI 흐름** 은 동작.
- **UI shell + Editor + Simulator workspace** 는 widget 골격까지
  들어있음.
- **UI 의 실 데이터 binding + NN mode UI 진입점** 은 누락. 이 누락은
  Phase 4.11 commit message 에서 "Mode selector UI 통합은 Phase 4.12"
  로 미루었으나, Phase 4.12 가 ProfilerPanel 로 바뀐 후 잊혀짐.

### 4.2 즉시 조치 (사용자 측)

1. `cd "C:\Workspaces\Claude\Tracking Radar Simulator\trsim" && git pull --ff-only && .\.venv\Scripts\python.exe -m pip install -e . --no-deps`
2. `trsim ui` 재가동 → DLC sidebar / bottom_tab 동작 확인
3. `pytest -q` → 1570 PASS 확인

### 4.3 즉시 조치 (개발 측, 다음 sub-step 후보)

**우선순위 ★** = MVP 가동 완전성 회복:

1. ★ **NN mode UI 진입경로 추가** (§ 2.1) — Simulator bottom_tabs
   에 NN Step1 / NN Step2 / NN Training 3 tab 직접 mount. 한 sub-step.
2. ★ **단축키 충돌 해소** (§ 2.2) — toolbar QAction 의 setShortcut
   제거 또는 QShortcut context 변경. 한 commit.

**우선순위 보강** = MVP 완성도:

3. Editor 5 activity 의 실 데이터 binding (Composer ↔ Map/Radar/
   Targets resource 등록 + Validate 동작)
4. Simulator 8 panel 의 실 frame 데이터 binding (FFT/RD/Scene3D
   에 simulation_clock.tick + RadarPipeline.step 흐름 연결)
5. Phase 8 HIL / Phase 9 Physics Lab 은 MVP+α 일정 따라 별도

이 가이드 (`docs/MVP_STATUS.md`) 가 다음 세션 진입점. 사용자가 위
조치 1+2 동의 시 자동 진행 재개.
