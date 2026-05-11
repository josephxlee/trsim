# TRsim MVP — 테스트 가이드 (2026-05-11)

`docs/MVP_USAGE.md` 가 "어떻게 쓰나" 라면, 이 가이드는 "어떻게
**확인** 하나" — MVP 가 정상 동작하는지 항목별 명령 + 기대 결과
+ 실패 시 조치. 모든 명령은 repo 루트
(`C:\Workspaces\Claude\Tracking Radar Simulator\trsim`) 에서 PowerShell.

각 섹션 끝의 ☐ 는 직접 체크. 전부 ✓ 면 MVP 가동 OK.

---

## 0. 사전 sanity check (1 분)

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

**기대**: `1570 passed in X.Xs` (또는 그 이상). 0 fail, 0 error.

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
- 하단 tabs: Run / Stage I/O / Profiler (3 개)

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

## 4. DLC 자동 로드 검증 (수동, ~ 2 분)

### 4.1 sample DLC 만들기

```powershell
$pkg = "$env:USERPROFILE\.trsim\packages\demo-panel"
New-Item -ItemType Directory -Force -Path "$pkg\ui" | Out-Null

@'
[package]
id = "demo-panel"
name = "Demo Panel DLC"
version = "1.0.0"
license = "MIT"

[compatibility]
trsim_min_version = "0.35.0"

[entry_points]
"trsim.ui.panels" = "ui/diagnostic_panel:DiagnosticPanel"
'@ | Out-File -Encoding utf8 "$pkg\manifest.toml"

@'
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

class DiagnosticPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Hello from demo-panel DLC"))
'@ | Out-File -Encoding utf8 "$pkg\ui\diagnostic_panel.py"
```

### 4.2 UI 재가동 → Simulator 가서 확인

```powershell
.\.venv\Scripts\trsim.exe ui --workspace simulator
```

**기대**: 하단 tabs 가 4 개. `Run` / `Stage I/O` / `Profiler` 옆에
`[DLC] demo-panel: DiagnosticPanel` 탭 추가. 클릭하면 "Hello from
demo-panel DLC" 라벨 표시.

### 4.3 user resource 자동 등장 확인

```powershell
New-Item -ItemType Directory -Force -Path $env:USERPROFILE\.trsim\resources\radars | Out-Null
@'
id = "kuband_naval"
carrier_freq_hz = 9.4e9
'@ | Out-File -Encoding utf8 $env:USERPROFILE\.trsim\resources\radars\kuband_naval.toml

.\.venv\Scripts\trsim.exe ui
```

**기대**: Editor workspace 의 좌측 Resource Browser sidebar 의 Radars
카테고리에 `kuband_naval` 항목 표시. 두 번 클릭하면 Radar activity
로 자동 전환.

### 4.4 --no-dlc 격리 확인

```powershell
.\.venv\Scripts\trsim.exe ui --no-dlc
```

**기대**: sidebar 비어있음 (`Radars (0)` 등). Simulator bottom tabs
3 개 (DLC 탭 없음).

### 4.5 청소

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.trsim\packages\demo-panel"
Remove-Item -Force "$env:USERPROFILE\.trsim\resources\radars\kuband_naval.toml"
```

☐ DLC 자동 로드 4 항목 통과

---

## 5. NN 흐름 검증 (수동, ~ 2 분)

### 5.1 Step 1 — Single variant 빌드

`trsim ui` → Simulator → NN mode → Step 1 panel:

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

### 5.2 Step 1 — 4-variant chain 빌드

| 입력 | 값 |
|---|---|
| Build mode | `All 4 variants (A/B/C/D)` |
| Frames (per variant) | `30` |
| Output path | `./datasets/` |

`Build Dataset` 클릭.

**기대**:
- Status `done: 4/4 variants -> pairing_variants_manifest.toml`
- Log 4 줄: `variant A/B/C/D: 30 frames -> pairing_variant_X.h5`
- `./datasets/` 안에 4 개 h5 + 1 개 manifest TOML

```powershell
Get-ChildItem ./datasets/
```

→ `pairing_variant_A.h5`, `_B`, `_C`, `_D`, `pairing_variants_manifest.toml` 5 파일.

### 5.3 numpy MLP 학습

UI 닫고 PowerShell 에서:

```powershell
@'
from pathlib import Path
from workbench.app.nn import TrainerService, TrainingJob

job = TrainingJob(
    job_id="pairing_v1", task="pairing",
    dataset_path=Path("./datasets/pairing_variant_A.h5"),
    weights_path=Path("./weights/v1.npz"),
    layer_sizes=(0, 32, 32, 0),
    activation="relu",
    learning_rate=0.05,
    batch_size=8,
    epochs=20,
    train_fraction=0.7,
    val_fraction=0.15,
)

result = TrainerService(backend="numpy_mlp", rng_seed=0).run(job)
print(f"epochs    = {result.completed_epochs}")
print(f"train     = {result.final_train_loss:.4f}")
print(f"val       = {result.final_val_loss:.4f}")
print(f"best_val  = {result.best_val_loss:.4f}")
print(f"weights   -> {result.weights_path}")
'@ | Out-File -Encoding utf8 _train_demo.py

$env:PYTHONUTF8 = "1"; $env:PYTHONPATH = "$(Get-Location)\src"
.\.venv\Scripts\python.exe _train_demo.py
```

**기대**:
- 5 줄 출력
- `epochs = 20`
- `best_val < final_val` 일 수도 (학습 곡선상 best epoch 가 마지막
  전이면)
- `./weights/v1.npz` 생성

```powershell
.\.venv\Scripts\python.exe -c "import numpy as np; f=np.load('./weights/v1.npz'); print(list(f.files))"
```

**기대**: `['layer_0_W', 'layer_0_b', 'layer_1_W', 'layer_1_b', 'layer_2_W', 'layer_2_b']`

### 5.4 Step 2 — 4-error 평가

UI 재가동 → Simulator → NN mode → Step 2 panel:

(controller 가 dataset / plugin 콤보를 받지만 현재는 stub registration
구조 — UI 에서는 콤보가 비어있을 수 있음. Python 스크립트로 직접 호출:)

```powershell
@'
from pathlib import Path
from workbench.app.nn import NumpyPairingNN, evaluate

plugin = NumpyPairingNN()
plugin.load_weights(Path("./weights/v1.npz"))

result = evaluate(
    plugin,
    training=Path("./datasets/pairing_variant_A.h5"),
    dev=Path("./datasets/pairing_variant_B.h5"),
    test=Path("./datasets/pairing_variant_D.h5"),
    bayes_error=0.0,
)
print(f"training = {result.training_error:.3f}")
print(f"dev      = {result.dev_error:.3f}")
print(f"test     = {result.test_error:.3f}")
print(f"hint     = {result.diagnosis_hint}")
'@ | Out-File -Encoding utf8 _eval_demo.py

.\.venv\Scripts\python.exe _eval_demo.py
```

**기대**:
- 4 줄 출력
- training / dev / test 모두 0.0 ~ 1.0 사이
- hint 는 `"balanced"` 또는 `"variance high"` / `"data mismatch"` /
  `"avoidable bias high"` 중 하나

NumpyPairingNN 은 Hungarian 비학습 baseline 이므로 4 variant 모두 비슷한
loss 가 나와야 정상 (variant 별 차이가 클 수 있음 — closed-form GT 와
다른 시나리오면).

### 5.5 청소

```powershell
Remove-Item _train_demo.py, _eval_demo.py
Remove-Item -Recurse -Force ./datasets, ./weights
```

☐ NN 흐름 5 항목 통과

---

## 6. 전체 통과 체크리스트

| 섹션 | 항목 | 통과 |
|---|---|---|
| 0 | 환경 sanity (venv / PySide6 / version) | ☐ |
| 1 | CLI 비-UI 3 명령 (help / profile / run) | ☐ |
| 2 | pytest 1570 + ruff + mypy + lint-imports | ☐ |
| 3 | UI 가동 + workspace 전환 + 5 activity + sidebar | ☐ |
| 4 | DLC 자동 로드 (panel mount + resource sidebar + --no-dlc) | ☐ |
| 5 | NN Step 1 single + chain + numpy_mlp 학습 + 4-error eval | ☐ |

전부 ✓ 면 MVP 가동 검증 끝. 후속 개발은 [`docs/MVP_USAGE.md`](MVP_USAGE.md)
§ 8 "MVP+α" 후보 리스트 참조.

---

## 7. 실패 모드별 대처

| 증상 | 원인 후보 | 조치 |
|---|---|---|
| `trsim.exe: command not found` | venv 활성화 안 됨 | `.\.venv\Scripts\Activate.ps1` 또는 절대경로 |
| `ImportError: PySide6` | dev extras 미설치 | `pip install -e ".[dev]"` |
| GUI 가 안 뜸 (process 즉시 종료) | Qt platform plugin 누락 | 디버그: `set QT_DEBUG_PLUGINS=1` 후 재시도 |
| pytest 일부 깨짐 | 환경 불일치 | `PYTHONUTF8 / PYTHONPATH` 환경변수 + Python 3.11+ 확인 |
| `lint-imports` UnicodeDecodeError | cp949 codec | `PYTHONIOENCODING=utf-8 PYTHONUTF8=1` 명시 |
| Step 1 빌드 후 sidebar 가 안 채워짐 | `~/.trsim/resources/` 디렉토리 없음 | `New-Item -ItemType Directory ...` 으로 만들고 재가동 |
| DLC 탭이 안 보임 | manifest 잘못 / entry_point typo | 위 § 4.1 와 1:1 비교 |
| numpy_mlp 가 ValueError "0 sample" | h5 가 0 frame 으로 빌드됨 | Frames > 0 으로 Step 1 재실행 |
