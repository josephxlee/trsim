# Phase 7 remainder — Editor Plugins menu wiring (2026-05-13)

직전 cycle (`phase_4_dem_import_wizard_2026_05_13.md`) 끝에 사용자
자동-진행 모드가 추천 1순위 후보로 지목한 작은 cycle. Plugins 메뉴가
처음으로 실제 동작.

## 0. 한 줄 요약

- HEAD = (F3 commit + docs).
- 누적 **2360 PASS** local (2326 → 2360, **+34 신규** in this cycle).
- 5 contracts KEPT 매 commit. ruff / mypy --strict / import-linter
  all clean.
- 3 sub-step push (F1 = `892d209`, F2 = `b94351e`, F3 = this commit).

## 1. 3 sub-step

| sub | commit | new | 내용 |
|---|---|---|---|
| F1 | `892d209` | +11 | `app/dlc/installer.py` — `install_package(pkg_path, packages_root=None, *, force=False) -> InstallResult` + `uninstall_package(package_id, packages_root=None) -> UninstallResult` + 3 typed errors (`PackageAlreadyInstalledError` / `PackageNotInstalledError` / `PackageEscapedRootError`, Error suffix for N818). CLI `_cmd_install` + `_cmd_uninstall` becomes thin stdout/exit-code wrapper. |
| F2 | `b94351e` | +17 | `ui/editor/package_manager_dialog.py` — `PackageManagerDialog(QDialog)` wrapping `PackageManagerPanel` + `PackageManagerController(QObject)` glueing 3 panel signals to installer service. 4 outgoing signals (`install_completed` / `install_failed` / `uninstall_completed` / `uninstall_failed`). All 4 runners + dialog factory + file picker inject-overridable. `install_via_file_picker()` 별도 메서드. |
| F3 | (this commit) | +6 | `ui/commands/builtin.py` + `ui/main_menu.py` 가 `plugins.install_package` 명령 추가 + Plugins 메뉴에 "Install Package..." entry. `ui/main_window.py` 가 `PackageManagerController` mount + `plugins.manage` / `plugins.install_package` hook routing. DLC runtime mount 시 그 `packages_root` 사용, 없으면 `~/.trsim/packages`. |

## 2. 도메인 결정

### Service vs UI 분리 (plan/17 § 17.5 enforcement)

CLI 와 UI 가 install/uninstall 로직 중복 회피. `app/dlc/installer.py`
가 single source of truth.

- 입력 validation 만 raise — typed errors.
- 출력은 `InstallResult` / `UninstallResult` frozen dataclass.
- print / sys.stderr / sys.exit 코드는 layer 외부 (CLI / Controller).

### Controller injection 패턴 (재사용)

`DEMImportController` 와 동일한 패턴. 4 inject 가능:

```python
PackageManagerController(
    packages_root=packages_root,
    parent=host,
    installer=install_package,         # default
    uninstaller=uninstall_package,      # default
    dialog_factory=PackageManagerDialog, # default
    file_picker=QFileDialog.getOpenFileName,  # default lambda
)
```

테스트는 4가지 다 override 가능 → file-touching 회피.

### packages_root precedence

`MainWindow.__init__` 에서:

1. `dlc_runtime` mount 됐으면 `dlc_runtime.app.paths.packages_root`.
2. 아니면 `~/.trsim/packages` (default_dlc_paths).

DLC 런타임과 메뉴 install 가 같은 디렉토리 보도록.

## 3. 학습 (3 trap)

### Trap 1: ruff N818 — Exception 이름은 Error suffix

`PackageAlreadyInstalled` → ruff N818 fail. Custom exception class
이름에 항상 `-Error` suffix. Subclass that extends builtin
exceptions (FileExistsError, ValueError) 인 경우에도 동일.

### Trap 2: `Edit replace_all=True` 의 토큰 중복 위험

`Foo` → `FooError` replace_all 시 이미 `FooError` 였던 부분이
`FooErrorError` 가 됨. Class def 를 manually 1번 rename + 그 후
`replace_all` 로 references rename 할 때 주의. Manual targeted Edit
3-4번이 안전하다.

### Trap 3: hook 등록 시 method binding 의 late attribute access

`register_builtin_commands(hooks)` 가 호출될 때 `self.
_dlc_manager_controller` 는 아직 존재 X. 그러나 `hook =
self._open_dlc_manager` (bound method) 는 등록 시점에 captured 되어도
실행 시점에서 `self._dlc_manager_controller` 를 access. `__init__`
후반에 controller 만들면 OK. 만약 hook 이 `lambda: self._dlc_manager_
controller.open_dialog()` 였다면 동일. 만약 `lambda: ctrl.open_dialog()`
처럼 closure 가 임시 변수 ctrl 잡으면 등록 시점 None 캡처 → 실패.

## 4. 다음 cycle 후보 (`docs/MVP_STATUS.md § "미구현 우선순위 리스트"`)

| 우선 | 작업 | 크기 | 비고 |
|---|---|---|---|
| 1 | Phase 4 UI domain_settings + installation_panel | 중 | Scenario Composer Installation panel + Map Editor Domain Settings panel — placeholder 만 있음. plan/13 § 13.3 + plan/11 § 11.6. |
| 2 | Phase 4 UI 실 데이터 binding | 대 | Editor 5 activity + Simulator 8 panel placeholder → 실 데이터. 여러 cycle 분할. |
| 3 | Phase 8 HIL 전체 | 매우 대 | 8.1 MVP → Lock-step → 8.2 L2/L4 → 8.3 L1+AWG. 새 protocol + 새 layer. |
| 4 | Phase 9 § 19.7.5+ 확장 (Validation Bench 일반화 / Library Models 동적) | 소-중 | 후속 polish. |

자동 진행 모드 다음 cycle 은 추천 1 (Phase 4 UI domain_settings) 부터.

## 5. 다음 세션 진입 명령 (PowerShell)

```powershell
cd "C:\Workspaces\Claude\Tracking Radar Simulator\trsim"
git pull --ff-only

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

& $PY -m pytest -q
# 2360 PASS expected

& ".\.venv\Scripts\lint-imports.exe"
# 5 contracts KEPT
```
