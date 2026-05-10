# Phase 4 — UI 기본 레이아웃 (ALL DONE)

**기간**: 2026-05-08 (Phase 4.1) → 2026-05-10 (Phase 4.2~4.12, 한 세션)
**최종 commit**: `86df20b` (Phase 4.12) → ci_log 갱신 `0768374`
**누적 test**: 4.1 baseline 808 → 4.12 끝 998 (+190 신규 ui tests)

## 0. 한 줄 정의

plan/04 § 4.3 Phase 4 = "MVP UI 완성, 두 Workspace + Editor Activity
5종". 이번에 12 sub-phase (4.1~4.12) 모두 commit + main push, CI 11
success / 1 in_progress, ruff/mypy strict/import-linter 5 contracts
KEPT 매 단계 통과.

## 1. Sub-phase 산출물 매핑

| sub | sha | 모듈 | 핵심 |
|---|---|---|---|
| 4.1 | `f530cee` | `ui/main_window.py`, `workspace_selector.py` | MainWindow shell + WorkspaceSelector StrEnum + Editor/Simulator stub + `trsim ui` CLI |
| 4.2a | `e99c73d` | `ui/commands/{registry,palette,builtin}.py` | WorkbenchCommand (frozen+slots) + Registry (substring fuzzy, title>id ranking) + CommandPalette QDialog (Ctrl+Shift+P) |
| 4.2b | `9fa0ffd` | `ui/toolbars/{simulation,target_run}_toolbar.py` | Sim/Target 두 레이어 toolbar + SIM_SPEEDS x1/x2/x4/x8 radio + State 라벨 |
| 4.2c | `24e6d8b` | `ui/main_menu.py` | MainMenuBar(QMenuBar) 7 menus + Speed submenu, strong-ref 정책 (libshiboken 회피) |
| 4.2d | `cacdb17` | `ui/dock_manager.py` | DockManager (register/toggle/save_state/restore_state) |
| 4.3 | `b213163` | `ui/editor/{activities,activity_pages,workspace}.py` | Activity StrEnum + ActivitySelector + 5 placeholder + Ctrl+1~5 + 5 WorkbenchCommand |
| 4.4 | `0929c71` | `ui/editor/resource_browser/` | ResourceBrowserSidebar (트리 4 카테고리 + ASCII status prefix + 검색 + 더블클릭 라우팅) |
| 4.5 | `bbb91db` | `ui/editor/composer/` | ScenarioComposer 4 block 골격 (References/Installation/Composition/Validation) |
| 4.6 | `4066d36` | `ui/editor/map_editor/` | MapEditor (Tools 5 + canvas placeholder + Layers 5 + History + Save/Import/Validate) |
| 4.7 | `6154738` | `ui/editor/radar_editor/` | RadarEditor (AntennaType QStackedWidget 동적 폼 + RXChannelMode + Beam Pattern Preview placeholder) |
| 4.8 | `57e7395` | `ui/editor/{targets_editor,atmosphere_panel}/` | TargetsEditor (motion_kind 7 + CSV import) + AtmospherePanel (5 field form + AtmosphereState round-trip) |
| 4.9 | `8cbfeb2` | `ui/simulator/panels/` (6) | FFT/RD/Run/Properties/PluginManager/StageIO + composite SimulatorWorkspace 3-col splitter |
| 4.10 | `9577545` | `ui/simulator/panels/{scene_3d,scope_pov}_panel.py` | Scene3DPanel (CameraPreset T/L/F/R + 11 SceneLayer toggle) + ScopePOVPanel (AZ readout) |
| 4.11 | `c6f2f25` | `ui/simulator/nn_mode/` | Step1DatasetPanel + Step2EvalPanel (4-error diagnostic table) |
| 4.12 | `86df20b` | `ui/simulator/profiler_panel/` | TimingBreakdownPanel + ScaleIndicator (color band 0.9/0.5) + ProfileReport + composite ProfilerPanel |

## 2. 주요 결정사항

- **Activity StrEnum 패턴 = WorkspaceSelector 와 동일**. `set_xxx` 가
  bool 반환, signal 은 enum 값만 carry. 구현 일관성 유지.
- **Strong-ref 정책 (Phase 4.2c)** — `MainMenuBar(QMenuBar)` 가 자기
  sub-menu dict 를 attribute 로 잡고 있어야 PySide6 가 GC 안 함.
  `bar.actions()[i].menu()` 만으로 access 하면 mid-test 에서 deleted.
- **DockManager 는 Phase 4.2d 인프라만**. Phase 4.3+ 패널들은
  `QSplitter` / `QTabWidget` 로 직접 mount, dock 통합은 후속.
- **Activity 5 (ResourceBrowser full-screen) placeholder 유지** —
  사이드바가 MVP 충분히 cover. 표 형태 후속 (plan/13 § 13.7).
- **canvas placeholder 패턴** — pyqtgraph/PyVista 임베드 는 매 panel
  의 4.x.x 후속. Phase 4.X 단계는 layout shell + signal/slot 만.
- **ASCII confusable 일괄 정리 (Phase 4.2b 사례)** — `×` → `x`,
  `—` → `-`. CLAUDE.md § 3.4 RUF002 가 docstring 도 검사.
- **mypy lambda 함정** — Qt method 가 bool 반환 시 `Callable[[], None]`
  과 호환 안 됨. helper method 로 wrap (`_exit_app`, `_activate_editor`).

## 3. 함정 / 트랩 누적

1. **bind FS LF/CRLF 경고 무해** — 매 commit 마다 warning, 무시 OK.
2. **pre-commit `ruff 설치 안 됨`** — uv venv + repo 외부 PATH 문제.
   실제 검증은 manual 로 통과 확인하고 commit.
3. **worktree `.venv` editable .pth** — 메인 repo src 가리킴. PYTHONPATH
   prefix 또는 conftest.py 의 sys.path 조작 필요.
4. **N802 Qt camelCase override** — `eventFilter` 등에 `# noqa: N802`
   per-line. (4.2a 의 `palette.py`).
5. **RUF012 mutable class default** — `_CATEGORY_TO_ACTIVITY` 등 dict
   class attr 는 `ClassVar[dict[...]]` annotation 필수.

## 4. CI 결과

`docs/sessions/_ci_log.md` 마지막 12 줄:

- 4.2a~4.11 (10 commits): success 6/6 매 commit
- 4.12 / 5.3: in_progress (회수 미완)

## 5. 다음 단계 — Phase 5 진입

**같은 세션 안에서 Phase 5.1~5.3 까지 시작**. 별도 인계 문서:
`docs/sessions/phase_5_verification_kickoff.md`.
