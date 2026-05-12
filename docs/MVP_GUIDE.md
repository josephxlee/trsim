# TRsim MVP — 테스트 가이드 (2026-05-12 rev4)

`docs/MVP_USAGE.md` 가 "어떻게 쓰나" 라면, 이 가이드는 "어떻게
**확인** 하나" — MVP 가 정상 동작하는지 항목별 명령 + 기대 결과
+ 실패 시 조치. 모든 명령은 repo 루트
(`C:\Workspaces\Claude\Tracking Radar Simulator\trsim`) 에서 PowerShell.

각 섹션 끝의 ☐ 는 직접 체크. 전부 ✓ 면 MVP 가동 OK.

> **rev4 갱신점** (2026-05-12 ~ ): rev2 (단축키 + NN tab mount) +
> rev3 (BOM tolerance) + **rev4** (Training panel 의 `Backend` 콤보 =
> numpy_mlp 기본 + Step 2 자동 register: NumpyPairingNN + cwd/datasets
> auto-scan). § 5 의 Python fallback 모두 GUI 흐름으로 대체. pytest
> 1596 PASS 기대.

---

## 0. 사전 sanity check (1 분)

### 0.0 origin/main 동기화 (rev2 추가)

```powershell
git pull --ff-only
```

**기대**: `Already up to date.` 또는 fast-forward 메시지.

console-script wrapper 재생성이 필요할 때 (entry point 자체가 새로
추가됐을 때) `pip install -e . --no-deps` 도 함께 실행하면 좋지만,
editable install 의 entry point 가 `workbench.__main__:main` 으로
고정이라 **소스 변경만으로 trsim.exe 가 새 코드를 호출함** — pull 만
해도 대개 충분.

`No module named pip` 에러가 나는 venv (uv 로 만든 venv 등) 는 다음
중 하나:

```powershell
# (a) ensurepip — venv 안에 pip 부트스트랩
.\.venv\Scripts\python.exe -m ensurepip --upgrade

# (b) reinstall 없이 pull 만 — entry point 변동 없으면 OK
git pull --ff-only

# (c) venv 재생성 (Python 3.11+ 의 표준 venv 도구로 pip 포함)
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

실패 시: `git status` 로 local 미커밋 변경 있는지 확인 후 stash /
commit / rebase 선택.

### 0.1 venv + 실행파일 존재

```powershell
Test-Path .venv\Scripts\trsim.exe
Test-Path .venv\Scripts\python.exe
```

**기대**: 둘 다 `True`.

실패 시:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 0.2 PySide6 import sanity

```powershell
.\.venv\Scripts\python.exe -c "import PySide6; print(PySide6.__version__)"
```

**기대**: `6.11.x` 출력. import 에러 없음.

실패 시: `pip install -e ".[dev]"` 다시.

### 0.3 trsim 버전 출력

```powershell
.\.venv\Scripts\trsim.exe --version
```

**기대**: `trsim 0.X.Y` 한 줄.

☐ 환경 sanity 통과

---

## 1. 비-UI CLI 검증 (헤드리스 가능, ~ 30 초)

### 1.1 도움말

```powershell
.\.venv\Scripts\trsim.exe --help
.\.venv\Scripts\trsim.exe ui --help
```

**기대**: `usage:` 시작 메시지. `ui` 도움말에 `--workspace`, `--no-dlc`
두 옵션 표시.

### 1.2 FrameProfiler smoke

```powershell
.\.venv\Scripts\trsim.exe profile --scenario demo --frames 20
```

**기대**: JSON 한 덩어리 stdout. 안에 `stage_name: "detector"`,
`"tracker"` 두 entry. 각 entry 에 `avg_ms`, `p50_ms`, `p95_ms`,
`p99_ms` 숫자 (양수).

### 1.3 Run manifest smoke

데모 자원 임시 디렉토리 만들고 1회 실행:

```powershell
$tmp = "$env:TEMP\trsim_demo_run"
New-Item -ItemType Directory -Force -Path "$tmp\resources\maps","$tmp\resources\radars","$tmp\resources\targets" | Out-Null
'id = "demo_map"' | Out-File -Encoding utf8 "$tmp\resources\maps\demo_map.toml"
'id = "demo_radar"' | Out-File -Encoding utf8 "$tmp\resources\radars\demo_radar.toml"
'id = "demo_target"' | Out-File -Encoding utf8 "$tmp\resources\targets\demo_target.toml"

.\.venv\Scripts\trsim.exe run --scenario demo --resources "$tmp\resources" `
  --map demo_map --radar demo_radar --target demo_target --out "$tmp\runs\demo"
```

**기대**: stdout 에 `run_id`, `out_dir`, `map_hash`, `radar`,
`target` 다섯 줄. `$tmp\runs\demo\manifest.json` + `traces.npz`
실제 생성.

```powershell
Get-ChildItem "$tmp\runs\demo"
```

→ 두 파일 보임.

☐ CLI 비-UI 3 명령 통과

---

## 2. 자동 검증 스위트 (~ 10 초)

### 2.1 pytest 전체

```powershell
$env:PYTHONUTF8 = "1"; $env:PYTHONPATH = "$(Get-Location)\src"
.\.venv\Scripts\python.exe -m pytest -q
```

**기대**: `1596 passed in X.Xs` (또는 그 이상). 0 fail, 0 error.

실패 시: 어느 테스트 깨졌는지 출력 보고 보고.

### 2.2 ruff

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m ruff format --check src tests
```

**기대**: 둘 다 `All checks passed!` 또는 `XXX files already formatted`.

### 2.3 mypy strict

```powershell
.\.venv\Scripts\python.exe -m mypy --strict src/workbench
```

**기대**: `Success: no issues found in N source files`.

### 2.4 import-linter (5 contracts)

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\lint-imports.exe
```

**기대**: `Contracts: 5 kept, 0 broken.`

☐ pytest / ruff / mypy / lint-imports 4 검증 통과

---

## 3. UI 가동 검증 (수동, ~ 3 분)

### 3.1 GUI 띄우기

```powershell
.\.venv\Scripts\trsim.exe ui
```

**기대**: 1280x800 창 열림. 타이틀 `TRsim 0.X.Y`.

### 3.2 Workspace 전환

| 행동 | 기대 |
|---|---|
| `Ctrl+Shift+E` | Editor workspace (좌측 vertical activity bar) |
| `Ctrl+Shift+S` | Simulator workspace (8 panel + 3 bottom tabs) |
| 상단 toolbar Editor/Simulator 라디오 클릭 | 위와 동일 |

### 3.3 Editor 5 activity 전환

Editor workspace 에서:

| 단축키 | 기대 activity |
|---|---|
| `Ctrl+1` | Composer (References / Installation / Composition / Validation) |
| `Ctrl+2` | Map (Tools palette: Pan / LandSeaBrush / SpotEdit / FlattenArea / AddBuilding) |
| `Ctrl+3` | Radar (Antenna type / Channel mode 폼) |
| `Ctrl+4` | Targets (Motion kind dropdown 7 종) |
| `Ctrl+5` | Browser (Resource Browser 풀스크린) |

### 3.4 Resource Browser sidebar

좌측 Activity bar 옆 always-on sidebar 에:
- `Scenarios (0)` / `Maps (0)` / `Radars (0)` / `Targets (0)` 4 카테고리
- 검색 입력란 + `+ New Resource` 버튼

`~/.trsim/resources/radars/<id>.toml` 가 있으면 Radars 카테고리에 자동
표시.

### 3.5 Simulator 8 panel 확인

Simulator workspace 진입 시 (Ctrl+Shift+S):
- 좌: PluginManager (5 stage QListWidget)
- 중상: Scene3D placeholder
- 중하: FFT | Range-Doppler
- 우중: Scope POV (cross-hair placeholder)
- 우: Properties (context-sensitive form)
- 하단 tabs: **6 개** — Run / Stage I/O / Profiler / NN Step 1 /
  NN Step 2 / NN Training. (DLC plugin tab 은 7 번째 이후로 추가됨.)

### 3.6 Command palette

| 행동 | 기대 |
|---|---|
| `Ctrl+Shift+P` | 검색 가능한 명령 palette 다이얼로그 |
| `editor` 입력 | "Workspace: Editor", "Activity: Composer", ... 항목 검색 |
| Enter | 해당 명령 실행 + 다이얼로그 닫힘 |

### 3.7 종료

`File → Exit` 메뉴 또는 창 X 버튼. 프로세스 정상 종료 (exit code 0).

☐ UI 7 항목 통과

---

## 4. DLC 자동 로드 검증 (수동, ~ 3 분)

DLC 흐름은 4 layer 가 순차로 작동한다:

```
~/.trsim/packages/<id>/manifest.toml
  ↓ PackageManager.scan()                  (app.dlc.package_manager)
  ↓ PluginLoader.load_all()                (app.dlc.plugin_loader)
  ↓ PanelRegistry.register_dlc_plugins()   (ui.panel_registry)
  ↓ SimulatorWorkspace.mount_dlc_panels()  (ui.simulator.workspace)
       → bottom_tabs 에 "[DLC] pkg: Class" 라벨로 추가

~/.trsim/resources/<category>/<id>.toml
  ↓ ResourceLibrary.list_resources()       (app.resources.library)
  ↓ populate_resource_browser_from_library (ui.dlc_bootstrap)
       → Editor 사이드바 카테고리 트리에 leaf 추가
```

`trsim ui` 가 `build_dlc_runtime()` (default = `~/.trsim/`) 으로 위
파이프라인을 한 번에 실행. `--no-dlc` 는 runtime=None 으로 만들어
mount + populate 두 단계 모두 skip.

### 4.1 sample DLC 만들기

> **중요**: PowerShell 5.1 의 `Out-File -Encoding utf8` 은 UTF-8
> **with BOM** 으로 저장 → Python `tomllib` 가 `Invalid statement (at
> line 1, column 1)` 로 거부. 아래 명령은 `[System.IO.File]::
> WriteAllText` + `UTF8Encoding($false)` 로 BOM 없는 UTF-8 저장
> (PowerShell 5.1 / 7 양쪽 동작). DLC 매니페스트 reader 가 BOM 만나면
> 자동 strip 하지만, 일관성 위해 BOM 안 쓰는 게 표준.

```powershell
$pkg = "$env:USERPROFILE\.trsim\packages\demo-panel"
New-Item -ItemType Directory -Force -Path "$pkg\ui" | Out-Null

$manifest = @'
[package]
id = "demo-panel"
name = "Demo Panel DLC"
version = "1.0.0"
license = "MIT"

[compatibility]
trsim_min_version = "0.35.0"

[entry_points]
"trsim.ui.panels" = "ui/diagnostic_panel:DiagnosticPanel"
'@
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText("$pkg\manifest.toml", $manifest, $utf8NoBom)

$panel = @'
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

class DiagnosticPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Hello from demo-panel DLC"))
'@
[System.IO.File]::WriteAllText("$pkg\ui\diagnostic_panel.py", $panel, $utf8NoBom)
```

**BOM 확인** (선택):

```powershell
(Get-Content -Encoding Byte -TotalCount 3 "$pkg\manifest.toml") -join ','
```

`239,187,191` 이면 BOM 있음 (실패). 첫 글자의 ASCII 코드 (예: `91` =
`[`) 이면 BOM 없음 (정상).

**manifest 필드 의미**:
- `[package]` — 4 필드 필수 (id kebab-case / name / version SemVer /
  license). `[compatibility].trsim_min_version` 도 필수.
- `[entry_points]` 키:
  - `trsim.ui.panels` → Python `module:attr`, panel 클래스
  - `trsim.resources.<cat>` → 디렉토리 path, ResourceLibrary 의 PACKAGE 티어
  - `trsim.plugins.<role>` → Stage Slot plugin (tracker / detector 등)

### 4.2 UI 재가동 → Simulator 에서 DLC tab 확인

```powershell
.\.venv\Scripts\trsim.exe ui --workspace simulator
```

**기대**: Simulator bottom_tabs 가 **7 개**:

| index | label |
|---|---|
| 0 | Run |
| 1 | Stage I/O |
| 2 | Profiler |
| 3 | NN Step 1 |
| 4 | NN Step 2 |
| 5 | NN Training |
| 6 | **`[DLC] demo-panel: DiagnosticPanel`** |

7 번째 (index 6) 탭 클릭 → "Hello from demo-panel DLC" 라벨 표시.

**실패 시**:
- DLC tab 자체가 없음 → `~/.trsim/packages/demo-panel/manifest.toml`
  존재 + 위 manifest schema 1:1 일치 확인
- DLC tab 라벨이 "[DLC] _GoodPanel" 처럼 package_id 없음 → manifest
  의 `[package].id` 가 비어있거나 kebab-case 위배
- 콘솔에 `package_manager.load_errors` 출력되면 → manifest 검증 실패

### 4.3 user resource 자동 등장 확인

```powershell
New-Item -ItemType Directory -Force -Path $env:USERPROFILE\.trsim\resources\radars | Out-Null
$radar = @'
id = "kuband_naval"
carrier_freq_hz = 9.4e9
'@
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText(
    "$env:USERPROFILE\.trsim\resources\radars\kuband_naval.toml",
    $radar,
    $utf8NoBom
)

.\.venv\Scripts\trsim.exe ui
```

**기대**: Editor workspace 좌측 Resource Browser sidebar 의 `Radars`
카테고리:
- 헤더가 `Radars (1)` 로 바뀜
- leaf 항목 `kuband_naval` 표시 (status prefix 없음 = USER 티어)
- 두 번 클릭 → Editor 가 자동으로 `Radar` activity (Ctrl+3) 로 전환

다른 카테고리도 동일 — `maps/`, `targets/`, `scenarios/` 디렉토리에
`.toml` 두면 각 카테고리 leaf 로 등장.

### 4.4 --no-dlc 격리 확인

```powershell
.\.venv\Scripts\trsim.exe ui --no-dlc --workspace simulator
```

**기대**:
- Editor sidebar 의 4 카테고리 모두 `(0)` 표시 (어떤 user resource
  도 안 보임)
- Simulator bottom_tabs 가 **6 개**: Run / Stage I/O / Profiler /
  NN Step 1 / NN Step 2 / NN Training. DLC tab 없음
- 종료 코드 0 (정상 종료)

**실패 시** (가동 자체 실패):
- `--no-dlc` 가 unknown option 으로 reject → 사용자 PC 의 trsim.exe
  가 옛 entry point. `0.0` 의 reinstall 실행. PowerShell 종료 후
  새 세션에서 다시 시도.

### 4.5 청소

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.trsim\packages\demo-panel"
Remove-Item -Force "$env:USERPROFILE\.trsim\resources\radars\kuband_naval.toml"
```

☐ DLC 자동 로드 4 항목 통과

---

## 5. NN 흐름 검증 (GUI 기반, ~ 3 분)

NN-mode 3 tab 이 Simulator bottom_tabs index 3/4/5 에 mount 되어 있다
(rev2). 모든 단계 GUI 클릭으로 가능. Python 스크립트 fallback 도
계속 동작 (Phase 6.4c controller 가 panel signal 에 hook).

`trsim ui --workspace simulator` 로 시작.

### 5.1 Step 1 — Single variant 빌드

bottom_tabs 의 `NN Step 1` (index 3) 클릭. panel 폼에 입력:

| 입력 | 값 |
|---|---|
| Build mode | `Single variant` |
| Frames (per variant) | `50` |
| Output path | `./datasets/demo_single.h5` |

`Build Dataset` 클릭.

**기대**:
- Status 라벨 `done: 50/50 samples -> demo_single.h5`
- Log 에 `Build started:` + `Build complete: 50 samples written to...`
- `./datasets/demo_single.h5` 파일 생성

`Cancel` 버튼은 frame loop 중간에 누르면 다음 frame 경계에서 멈춤
(`builder.is_cancelled` 가 True 가 되어 PipelineRunner 가 break).

### 5.2 Step 1 — 4-variant chain 빌드

같은 panel:

| 입력 | 값 |
|---|---|
| Build mode | `All 4 variants (A/B/C/D)` |
| Frames (per variant) | `30` |
| Output path | `./datasets/` |

`Build Dataset` 클릭.

**기대**:
- Status `done: 4/4 variants -> pairing_variants_manifest.toml`
- Log 4 줄: `variant A: 30 frames -> pairing_variant_A.h5` 등 4 개
- `./datasets/` 안에 4 개 h5 + 1 개 manifest TOML

```powershell
Get-ChildItem ./datasets/
```

→ `pairing_variant_A.h5`, `_B`, `_C`, `_D`,
   `pairing_variants_manifest.toml` 5 파일.

`Cancel` 을 중간 variant 시점에 누르면, 그 시점까지 완료된 variant
만 manifest entries 에 등록 + 그 다음 variant 는 시작도 안 함.

### 5.3 NN Training — numpy MLP 학습 (GUI 전용)

bottom_tabs 의 `NN Training` (index 5) 클릭. panel 폼 기본값:

| 필드 | 기본값 | 갱신 권장 |
|---|---|---|
| Job ID | `pairing_v1` | 그대로 |
| Dataset | `./datasets/pairing_variant_A.h5` | 그대로 (5.2 에서 만듦) |
| Weights | `./plugins/pairing/weights/v1.npz` | `./weights/v1.npz` |
| Epochs | `10` | `20` |
| LR | `1e-3` | `0.05` |
| Framework | `numpy_only` | 그대로 |
| **Backend** | **`numpy_mlp (real gradient descent)`** | 그대로 (rev4) |

`Run Training` 클릭.

**기대** (numpy_mlp 기본):
- Status `done: 20/20 epochs`
- Log: `Training started: pairing_v1 (backend=numpy_mlp)` + 매 epoch
  status 갱신
- `./weights/v1.npz` 생성 + 아래 sanity 통과

```powershell
.\.venv\Scripts\python.exe -c "import numpy as np; f=np.load('./weights/v1.npz'); print(list(f.files))"
```

**기대 출력**: `['layer_0_W', 'layer_0_b', 'layer_1_W', 'layer_1_b', 'layer_2_W', 'layer_2_b']`

Backend 콤보를 `fake (deterministic decay — smoke only)` 로 바꾸면:
- 데이터셋 없이도 동작 (HDF5 read 0)
- weights 파일은 `layer_0`, `layer_1`, ... (W/b 분리 X) 로 zero matrix
- training/val loss 가 결정적 exponential decay
- UI smoke 검증 용도 (실제 학습 X)

### 5.4 Step 2 — 4-error 평가 (GUI 전용)

bottom_tabs 의 `NN Step 2` (index 4) 클릭.

**기본 register 상태** (rev4):
- Plugin combo: `numpy_pairing_nn` (NumpyPairingNN baseline 자동 등록)
- Dataset combo: `<cwd>/datasets/*.h5` 자동 scan 결과. 5.2 에서 `./datasets/` 에 4 개 만들었으면 콤보에 `pairing_variant_A`, `_B`, `_C`, `_D` 등 등장 (`trsim ui` 시작 시점의 cwd 가 그 directory 의 parent 여야 함)

dataset 콤보 + plugin 콤보 선택 → `Run Eval` 클릭.

**기대**:
- 4-error 표의 `Pairing` 행 `RMSE` 셀에 0.0 ~ 1.0 사이 값
- `Bias` 셀 `0.000`
- 다른 task 행 (Tracker / Predictor / Classifier) 은 빈 상태 (MVP 미구현)

NumpyPairingNN 은 Hungarian 비학습 baseline. 4 variant 데이터 모두
closed-form GT 라 loss 가 작게 (수 % 이하) 나와야 정상.

**dataset 콤보가 비어있을 때**:
- `trsim ui` 띄운 시점 cwd 의 `./datasets/` 이 비어있음
- 해결: `trsim ui` 종료 → 그 directory 에서 다시 `trsim ui` 실행. 또는
  `NNStep2Controller.register_dataset(name, path)` 으로 명시 등록.

### 5.5 청소

```powershell
Remove-Item -Recurse -Force ./datasets, ./weights
```

☐ NN 흐름 5 항목 통과 (전부 GUI 클릭으로 가능 — rev4)

---

## 6. 전체 통과 체크리스트

| 섹션 | 항목 | 통과 |
|---|---|---|
| 0 | 환경 sanity + origin/main pull + editable reinstall | ☐ |
| 1 | CLI 비-UI 3 명령 (help / profile / run) | ☐ |
| 2 | pytest 1576 + ruff + mypy + lint-imports | ☐ |
| 3 | UI 가동 + workspace 전환 + 5 activity + sidebar + 6 bottom tabs | ☐ |
| 4 | DLC 자동 로드 (panel mount index 6 + resource sidebar + --no-dlc) | ☐ |
| 5 | NN Step 1 single + chain + numpy_mlp 학습 + 4-error eval (전부 GUI) | ☐ |

전부 ✓ 면 MVP 가동 검증 끝. 후속 개발은 [`docs/MVP_USAGE.md`](MVP_USAGE.md)
§ 8 + [`docs/MVP_STATUS.md`](MVP_STATUS.md) § 4.3 "MVP+α" 후보 리스트
참조.

---

## 7. 실패 모드별 대처

| 증상 | 원인 후보 | 조치 |
|---|---|---|
| `No module named pip` | uv venv 등 pip 없는 venv | § 0.0 (a) `ensurepip --upgrade` 또는 (c) venv 재생성 |
| `package error ... Invalid statement (at line 1, column 1)` | manifest.toml UTF-8 BOM | § 4.1 의 `[System.IO.File]::WriteAllText` + `UTF8Encoding($false)` 로 재작성. v0.X 부터 reader 가 BOM strip 하지만 일관성 위해 BOM 안 씀이 표준 |
| `trsim ui --help` 에 `--no-dlc` 없음 | trsim.exe 가 옛 entry point | § 0.0 의 `pip install -e . --no-deps` |
| pytest 1484 PASS (1576 기대) | local main 이 origin/main 뒤쳐짐 | § 0.0 의 `git pull --ff-only` |
| Ctrl+Shift+E/S/P 안 됨 | toolbar QAction + menu QAction 단축키 충돌 (rev1) | rev2 push 됐음. § 0.0 pull 으로 해결 |
| Simulator 하단 tab 이 3 개 (NN tab 없음) | local main 이 rev2 이전 | § 0.0 의 pull 으로 해결 |
| `trsim.exe: command not found` | venv 활성화 안 됨 | `.\.venv\Scripts\Activate.ps1` 또는 절대경로 |
| `ImportError: PySide6` | dev extras 미설치 | `pip install -e ".[dev]"` |
| GUI 가 안 뜸 (process 즉시 종료) | Qt platform plugin 누락 | 디버그: `$env:QT_DEBUG_PLUGINS = "1"` 후 재시도 |
| pytest 일부 깨짐 | 환경 불일치 | `PYTHONUTF8 / PYTHONPATH` 환경변수 + Python 3.11+ 확인 |
| `lint-imports` UnicodeDecodeError | cp949 codec | `PYTHONIOENCODING=utf-8 PYTHONUTF8=1` 명시 |
| Resource Browser sidebar 가 비어있음 | `~/.trsim/resources/<cat>/` 디렉토리 없거나 `--no-dlc` 켜짐 | 디렉토리 만들고 `--no-dlc` 없이 재가동 |
| DLC tab 이 안 보임 | manifest 잘못 / entry_point typo / `--no-dlc` 켜짐 | § 4.1 manifest 와 1:1 비교 + `--no-dlc` 끄기 |
| DLC tab 라벨이 `[DLC] _Cls` (pkg 없음) | manifest `[package].id` 가 비었음 | manifest 검증 (kebab-case + SemVer) |
| numpy_mlp 가 `ValueError "0 sample"` | h5 가 0 frame 으로 빌드됨 | Frames > 0 으로 Step 1 재실행 |
| Training panel `Run` 클릭 후 `error: ... No such file ...` | Backend = numpy_mlp (default rev4) 인데 dataset 경로가 없음 | dataset_edit 경로를 5.2 에서 빌드한 `.h5` 로 갱신. 또는 Backend 를 `fake` 로 토글 (smoke 용) |
| Step 2 dataset combo 비어있음 | `trsim ui` 가동 시점 cwd 의 `./datasets/` 이 빈 디렉토리 | 그 directory 안에서 `trsim ui` 다시 실행. 또는 controller 의 `register_dataset(name, path)` 명시 호출 |
