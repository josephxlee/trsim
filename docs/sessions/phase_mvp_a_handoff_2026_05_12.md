# MVP + α 진행 인계 — Physics Lab MVP-minimum 완료 후 (2026-05-12)

이 세션에서 Phase 7 MVP 완성 + 사용자 검증 gap fix 8건 + Physics Lab
MVP-minimum (PL-A~E + 옵션 A) 마침. 다음 세션이 5분 안에 따라잡고
**Phase 9.1 본격** 부터 자동 진행하기 위한 짧은 인계.

## 0. 현재 상태 (한 줄)

- HEAD = `b78e579`  (`fix(physics-lab): Revert restores scaffold ...`)
- 누적 **1692 PASS** local
- ruff / mypy strict / import-linter 5 contracts KEPT 매 commit
- 이 세션 18 commits main 직접 push

## 1. 사용자 설계 우선순위 (반드시 기억)

> **physics_lab > simulator > editor**
>
> Physics Lab = 시뮬 물리 수식·개념의 **증명** + **시각 검증** +
> 사용자가 시뮬에 추가하고 싶은 수식 **시험**. MVP 완료 후 가장
> 먼저 본격 다듬을 영역. plan/19 § 19.2 의 "5번째 차별점" 위치를
> 사용자가 명시적으로 **제 1 차별점** 으로 격상.
>
> 후속 Phase 우선순위:
> 1. Phase 9.1 / 9.2 / 9.3 (Physics Lab 본격)
> 2. Phase 5 후속 (도메인 정량 보강)
> 3. NN 보강 (Adam / workbench-train / Step 2 행)
> 4. Phase 8 HIL
> 5. DLC CLI (install / sdk build)
> 6. UI 데이터 binding (Editor 5 activity / Simulator 8 panel 실 데이터)
> 7. Floating dock 옵션 B / Theme manager

## 2. 이 세션 누적 push (18 commits)

| commit | 단계 |
|---|---|
| `c297800` | Phase 7.6 DLC runtime bootstrap |
| `96842cd` | Task B variant chain runner |
| `d3c247e` | Task C numpy MLP backend |
| `025a168` | Task D Simulator panel mount |
| `ae960d4` | MVP wrap-up CLI + docs |
| `41381b9` | docs MVP_GUIDE 작성 |
| `053c866` | docs MVP_STATUS top-down gap report |
| `87523d5` | fix Ctrl+Shift+E/S/P 단축키 충돌 해소 |
| `54ba70a` | feat NN Step1/Step2/Training mount in Simulator |
| `aa8c734` | docs MVP_GUIDE rev2 |
| `f526c7c` | fix DLC slash-path + load_errors stderr |
| `f8edb39` | fix TOML BOM tolerance + MVP_GUIDE rev3 |
| `eeb768e` | feat A1 backend toggle + A2 Step2 default register |
| `c6123ae` | fix Step1→Step2 auto-refresh + Refresh button |
| `07b5dd4` | docs MVP_GUIDE rev6 path semantics |
| `9a4bd84` | feat Step1 progress bar + DONE marker |
| `6b8f472` | feat floating dock 옵션 D (DetachableTabWidget) |
| `416f7d1` | fix FloatingPanel content visibility |
| `c215f24` | feat PL-A + PL-B + PL-C (Physics Lab + Test Objects 9) |
| `6ea1565` | feat PL-D Bouncing Ball demo |
| `1472f0c` | feat PL-E Code edit mode + 옵션 A toolbar visibility |
| `b78e579` | fix Revert restores scaffold (SyntaxError 회피) |

## 3. 다음 세션 진입점 — Phase 9.1 본격

plan/19 § 19.11.2 의 Phase 9.1 sub-step (PL-A~E 에서 끝난 것 빼고):

| # | sub-step | 범위 | 추정 |
|---|---|---|---|
| **9.1a** | Code Pane syntax highlight | QSyntaxHighlighter Python keywords / strings / comments 기본 색상. autocomplete 는 9.3 으로 미룸 | 1 sub-step |
| **9.1b** | Time controls 의 Frame slider + Frame-by-frame 버튼 | PhysicsClock 의 frame_id seek + 단일 step 버튼 | 1 sub-step |
| **9.1c** | Parameters Pane 자동 슬라이더 | `@physics_param(min, max, step)` decorator + introspection → 자동 QSlider 생성. 현재는 Restitution 1 개만 수동. | 2 sub-step |
| **9.1d** | 9 Test Object 3D mesh | PyVista QtInteractor 임베드 + Sphere/Cube/...각 mesh + 카메라 control. plan/19 § 19.7.3 의 pv.Sphere/Cube/...활용 | 2 sub-step |
| **9.1e** | 4 시간 모드 (Static / Run / Compare / Sweep) | 모드 선택 콤보 + Static (정지 상태 viz), Run (현재), Compare (분석 공식 overlay), Sweep (parameter range 자동 sweep + plot) | 2 sub-step |
| **9.1f** | Library 카테고리 분리 | Tests / Models / Saved Experiments 트리 + Save Experiment 기능 (현재 demo state → TOML 저장) | 1 sub-step |
| **9.1g** | "Free Fall with Air Drag" 두 번째 demo | Air drag toggle + drag coefficient slider. plan/19 § 19.12.1 의 첫 예시 완성 ("Gravity + Bouncing Ball + Air Drag") | 1 sub-step |

총 **10 sub-step**. 1 세션에 모두 끝내기 어려우니 9.1a / 9.1b / 9.1c
한 묶음, 9.1d / 9.1e 한 묶음, 9.1f / 9.1g 한 묶음 으로 3 commit
분할 권고.

## 4. 후속 Phase 진입점

### Phase 9.2 — 외부 자료 + 학습 (plan/19 § 19.11.2)
- Library Measured Data 업로드 (CSV/HDF5)
- Library Papers (PDF) 업로드
- Lab-B Validation Bench (측정 vs 시뮬 RMSE)
- Lab-C Parameter Studio (scipy.optimize fit)
- 사용자 검토 → 채택 워크플로 (학습된 파라미터 → 시뮬 시나리오 사용)

### Phase 9.3 — 고급 기능
- Code Pane Edit mode 강화 (autocomplete + 다중 함수 + import)
- PhysicsModelProtocol plugin (사용자 정의, 11번째 SDK)
- NN 으로 물리 대체 (form 2, Phase 6 NN 결합)
- Symbolic regression (PySR)
- Test Object plugin

### Phase 5 후속 (도메인 정량 보강)
- ExtendedTarget σ_glint RMS 정량 회귀 (Phase 5.21)
- High-g UKF/EKF RMSE 정량 (Phase 5.22)
- Multipath/horizon golden 추가 case (Phase 5.19/5.20)

### Phase 8 HIL (plan/04 § 4.3)
- TCP/JSON DUTAdapter + Lock-step Handshake
- L5 비교 (GT/SIL/HIL 3-way)
- 자세한 sub-step plan/04 § 4.3 Phase 8.1~8.3

### NN 보강
- Adam optimiser (numpy_mlp 후속)
- workbench-train 외부 subprocess wrapping
- Step 2 Tracker/Predictor/Classifier 행 채우기
- NN mode "DSP / NN Development" mode selector (plan/05 § 5.1 principle 6)

### DLC CLI
- trsim install <pkg>.trsim-pkg (zip → ~/.trsim/packages/)
- trsim sdk build <dir> (디렉토리 → .trsim-pkg)
- Editor "Install Package..." 메뉴

### UI 실 데이터 binding (큰 phase)
- Editor 5 activity ↔ ResourceLibrary
- Simulator 8 panel ↔ SimulationClock + RadarPipeline.step
- Scene3D PyVista 임베드 (placeholder → 실 canvas)
- Scope POV cross-hair canvas
- FFT / Range-Doppler pyqtgraph binding

### 부수
- Floating dock 옵션 B (nested QMainWindow)
- Theme manager (ui/theme.py 중앙 다크 팔레트, plan/05 § 5.6)

## 5. 작업 환경 (이미 검증된)

| 항목 | 값 |
|---|---|
| OS | Windows |
| repo root | `C:\Workspaces\Claude\Tracking Radar Simulator\trsim` |
| worktree | `.claude/worktrees/elastic-moser-89c4b3` (Cowork) |
| Python | 3.13.3 (.venv) |
| 주요 의존 | PySide6 6.11.0, pyqtgraph 0.13.x, numpy, h5py, scipy, pytest 9.0.3, pytest-qt 4.5.0, ruff, mypy, import-linter |
| 실행파일 | `.venv\Scripts\trsim.exe` (= `python -m workbench`) |
| Push 권한 | `.claude/settings.local.json` 에 `Bash(git push origin HEAD:main)` allow 등록 — 자동 push OK. `.claude/` 자체는 gitignored. |

## 6. 운영 학습 (이 세션)

1. **사용자 우선순위 통찰 반영** — Physics Lab 을 5번째 차별점 → 1번째
   로 격상. 다음 세션이 이 ranking 따라 phase 진행.
2. **PowerShell 5.1 UTF-8 BOM** — `Out-File -Encoding utf8` 는 BOM
   추가. tomllib reject. fix: `[System.IO.File]::WriteAllText` +
   `UTF8Encoding($false)`. 코드 reader 도 BOM strip.
3. **inspect.getsource = method form** — `inspect.getsource
   (Cls.method)` 는 indented method (with `self`). module-level
   exec 불가. Code edit mode 같은 데서 scaffold form 으로 변환 필요.
4. **detach widget visibility** — QTabWidget.removeTab() 후 widget
   hidden. setCentralWidget 만으로는 보이지 않음. `content.show()` +
   `Qt.WindowFlag.Window` 명시.
5. **QAction shortcut 충돌** — toolbar QAction + menu QAction +
   QShortcut 셋이 같은 shortcut 가지면 Qt ambiguous shortcut
   suppression 으로 둘 다 disable. 한 곳에서만 등록.
6. **register_default_setup pattern** — controller 가 default 데이터
   자동 등록 + 외부 dataset_root 가 build 후에 변경되면 refresh 메서드
   호출. signal/slot 으로 다른 controller 와 wire.
7. **Auto mode push allowlist** — main 직접 push 자동 차단. settings.local.json
   에 `Bash(git push origin HEAD:main)` allow rule 추가 후 자동 통과.

## 7. 다음 세션 진입 명령

```bash
cd "C:/Workspaces/Claude/Tracking Radar Simulator/trsim"
git pull --ff-only
PY=".venv/Scripts/python.exe"
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m pytest -q
# 1692 PASS expected
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/lint-imports.exe
# 5 contracts KEPT
```

그 다음:
1. CLAUDE.md § 1 + `docs/MVP_STATUS.md` 읽기 (5 분)
2. 이 handoff `docs/sessions/phase_mvp_a_handoff_2026_05_12.md` 정독
3. `plan/19_physics_lab.md` § 19.5 / § 19.7 / § 19.11 (10 분)
4. **Phase 9.1a + 9.1b + 9.1c 한 묶음 진입** — Code syntax highlight +
   Frame slider + 자동 슬라이더 generator. 약 3 commit.

세션 컨텍스트 80% 도달 시 또 새 handoff 작성 + 종료. MVP+α 모두 끝날
때까지 반복.

## 8. 문서 위치 정리

| 문서 | 용도 |
|---|---|
| `docs/MVP_USAGE.md` | 사용 가이드 |
| `docs/MVP_GUIDE.md` (rev8) | 검증 가이드 (7 섹션 + checklist) |
| `docs/MVP_STATUS.md` | top-down gap report (사용자 검증 후 진단) |
| `docs/sessions/phase_5_6_7_2026_05_11_handoff.md` | 이전 세션 인계 |
| `docs/sessions/phase_mvp_a_handoff_2026_05_12.md` | **이 인계** |
| `CLAUDE.md` § 1 | 누적 진행 log |
| `README.md` | status |
| `plan/19_physics_lab.md` | Physics Lab 설계 (1000+ 줄) |
