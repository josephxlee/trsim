# TRsim MVP — 사용 가이드 (2026-05-11)

Phase 0~7 + Tasks A/B/C/D 완료 후 MVP 첫 가동을 위한 단축 안내.
누적 1570 PASS, 5 import-linter contracts KEPT, ruff/mypy strict
clean. 한국어 반말 톤은 CLAUDE.md § 2 약속에 따른다.

---

## 0. 환경 사전 조건

- Python 3.11 +
- `pip install -e ".[dev]"` (PySide6 6.11.x, numpy, h5py, pytest, ruff,
  mypy, import-linter 등 모두 dev extras 에 포함)
- Windows / macOS / Linux 어느 데스크탑 OS 든 가능. GUI 진입은
  PySide6 가 필요하므로 server-only 환경은 `trsim profile` / `trsim run`
  CLI 만 사용 가능.

`pyproject.toml` 의 `[project.scripts]` 에 `trsim = "workbench.cli.main:main"`
이 등록되어 있어 두 가지 진입점이 동일하게 동작한다:

| 진입점 | 비고 |
|---|---|
| `trsim <cmd>` | dev install 후 `pip install -e .` 한 PATH |
| `python -m workbench <cmd>` | venv 안에서 직접 호출 |

---

## 1. UI 가동 (가장 흔한 흐름)

```powershell
python -m workbench ui
```

자동으로 일어나는 일:

1. `~/.trsim/packages/` 디렉토리 스캔 — 설치된 `.trsim-pkg` 가 있으면
   manifest 검증 → 엔트리포인트 로드.
2. `~/.trsim/resources/` 디렉토리 스캔 — 사용자가 작성한 Map / Radar
   / Target / Scenario TOML 이 있으면 Editor 의 Resource Browser
   사이드바에 자동 표시.
3. DLC plugin 중 `trsim.ui.panels` 슬롯은 Simulator workspace 의 bottom
   tab 으로 "[DLC] pkg: ClassName" 라벨로 자동 mount.

옵션:

```powershell
# 시뮬레이터부터 띄우기
python -m workbench ui --workspace simulator

# DLC 자동 로드 끄기 (디버깅 / 격리 시)
python -m workbench ui --no-dlc
```

### 1.1 UI 안에서 무엇을 할 수 있나

**Editor workspace** (5 activity, Ctrl+1 ~ Ctrl+5)

- `Composer` — 시나리오 4 블록 (References / Installation /
  Composition / Validation)
- `Map` — 5 도구 (Pan / LandSeaBrush / SpotEdit / FlattenArea /
  AddBuilding) + 레이어 토글
- `Radar` — Parabolic / PlanarArray + Single Sum / Monopulse 4ch
- `Targets` — 메타 폼 + Motion kind 7종 + 산란체 수
- `Browser` — Resource Browser 풀스크린

좌측 vertical Activity bar 옆 사이드바는 Phase 7.6 부터 `~/.trsim/
resources/<category>/` 의 실제 파일 목록을 보여준다.

**Simulator workspace** (8 panel + 3 tabs)

- 상단 행: PluginManager / (Scene3D + FFT|RD 수직 split) / Scope POV /
  Properties
- 하단 tabs: Run / Stage I/O / Profiler + DLC 가 설치되어 있으면 추가
  탭들

**NN mode (Editor 내 별도 탭)**

- Step 1 Dataset Builder
- Step 2 Eval (Pairing/Tracker/Predictor/Classifier × RMSE/Bias 표)

---

## 2. NN dataset 만들기 (Step 1)

### 2.1 단일 variant 빌드

1. Simulator workspace → NN mode → `Step 1 - Dataset Builder` panel
2. Build mode = `Single variant`
3. Frames = 예: 200, Output path = `./datasets/demo.h5`
4. **Build Dataset** 클릭 → FMCW Triangle 닫힌형 GT 가 매 frame 채워짐

생성 결과:
- `./datasets/demo.h5` (HDF5: inputs/up_beats, inputs/down_beats,
  labels/pair_indices + meta_json / schema_json / variant_json attrs)

### 2.2 4-tier variant chain 빌드 (task B)

1. Build mode = `All 4 variants (A/B/C/D)`
2. Frames (per variant) = 예: 50
3. Output path = 디렉토리 (예: `./datasets/`)
4. **Build Dataset** 클릭

생성 결과:
```
./datasets/
├── pairing_variant_A.h5    (ideal: sea_state=0, no attitude, no sidelobe)
├── pairing_variant_B.h5    (attitude only)
├── pairing_variant_C.h5    (sidelobe only)
├── pairing_variant_D.h5    (full realistic)
└── pairing_variants_manifest.toml
```

Cancel 도중 누르면 현재 variant 까지만 manifest 에 등록.

---

## 3. NN 학습 (Task C — numpy MLP backend)

UI 의 Training Panel 이 아직 main_window 에 통합되지 않았으므로
지금은 Python REPL / 스크립트로 직접 호출.

```python
from pathlib import Path
from workbench.app.nn import TrainerService, TrainingJob

job = TrainingJob(
    job_id="pairing_v1",
    task="pairing",
    dataset_path=Path("./datasets/pairing_variant_A.h5"),
    weights_path=Path("./weights/pairing_v1.npz"),
    layer_sizes=(0, 32, 32, 0),     # 0 은 데이터 차원으로 자동 anchor
    activation="relu",
    learning_rate=0.05,
    batch_size=8,
    epochs=20,
    train_fraction=0.7,
    val_fraction=0.15,
)

trainer = TrainerService(backend="numpy_mlp")
result = trainer.run(job)

print(f"epochs={result.completed_epochs}  best_val={result.best_val_loss:.4f}")
print(f"weights -> {result.weights_path}")
```

`backend="fake"` (default) 는 Phase 6.7 의 결정적 decay-loop — 데이터셋
없이 UI smoke 시 사용.

실제 numpy gradient descent 가 일어나는 backend 는 `"numpy_mlp"`. 합성
linear-regression 합성 데이터로는 train MSE 가 monotonic 하게 감소
하는 것이 검증됨 (`tests/unit/app/test_nn_numpy_mlp.py`).

---

## 4. NN 평가 (Step 2)

```python
from pathlib import Path
from workbench.app.nn import NumpyPairingNN, evaluate

plugin = NumpyPairingNN()
plugin.load_weights(Path("./weights/pairing_v1.npz"))   # numpy_mlp 는 no-op

result = evaluate(
    plugin,
    training=Path("./datasets/pairing_variant_A.h5"),
    dev=Path("./datasets/pairing_variant_B.h5"),
    test=Path("./datasets/pairing_variant_D.h5"),
    bayes_error=0.0,
)
print(result.diagnosis_hint)
# e.g. "variance high" / "data mismatch" / "balanced"
```

4-error diagnostic 은 Andrew Ng 의 ML 진단 프레임워크 그대로 — Bayes /
Training / Dev / Test 4 점 + 3 gap.

UI 의 Step 2 panel 에서도 dataset + plugin 콤보 선택 후 `Run Eval` 로
Pairing 행 RMSE 가 채워진다.

---

## 5. DLC 만들기 (Phase 7 — MVP+α 영역)

### 5.1 디렉토리 레이아웃

```
my_advanced_tracker/
├── manifest.toml
├── README.md
├── LICENSE
├── advanced_tracker.py
├── resources/
│   └── radars/
│       └── kuband_naval.toml
└── ui/
    └── diagnostic_panel.py
```

### 5.2 manifest.toml

```toml
[package]
id = "my-advanced-tracker"
name = "Advanced Tracker for Stealth Targets"
version = "1.0.0"
license = "MIT"

[compatibility]
trsim_min_version = "0.35.0"

[entry_points]
"trsim.plugins.tracker" = "advanced_tracker:AdvancedTracker"
"trsim.resources.radars" = "resources/radars/"
"trsim.ui.panels" = "ui/diagnostic_panel:DiagnosticPanel"
```

### 5.3 설치 (MVP 는 수동 압축 해제)

```powershell
# Windows
Copy-Item -Recurse my_advanced_tracker $env:USERPROFILE\.trsim\packages\
```

```bash
# macOS / Linux
cp -r my_advanced_tracker ~/.trsim/packages/
```

다음번 `python -m workbench ui` 실행 시:

- Resource Browser 의 Radars 카테고리에 `kuband_naval` 등장
- Simulator bottom_tabs 에 "[DLC] my-advanced-tracker: DiagnosticPanel"
  탭 등장

`trsim install <pkg>.trsim-pkg` 자동 압축 해제 CLI 는 후속 sub-step
(현재 미구현 — manifest 검증은 `workbench.sdk.manifest.load_manifest_
from_toml` 가 담당).

---

## 6. 비-UI CLI 명령

| 명령 | 용도 |
|---|---|
| `python -m workbench --version` | 버전 출력 |
| `python -m workbench run --scenario <id> --map <id> --radar <id> --target <id> --resources <dir>` | 시나리오 1회 실행 + Run manifest + traces.npz 저장 (frame loop 자체는 MVP placeholder, Phase 4 후속) |
| `python -m workbench profile --scenario <id> --frames 100 --output out.json` | FrameProfiler 통계 (avg/p50/p95/p99) JSON 출력 |

CI / 서버 환경은 PySide6 임포트 없이 위 두 명령만 사용 가능.

---

## 7. 검증 (개발자 기준)

```powershell
# pytest 전체
PYTHONUTF8=1 PYTHONPATH="$(Get-Location)\src" .venv\Scripts\python.exe -m pytest -q
# 1570 PASS expected

# ruff
.venv\Scripts\python.exe -m ruff check
.venv\Scripts\python.exe -m ruff format --check

# mypy strict
.venv\Scripts\python.exe -m mypy --strict src/workbench

# import-linter
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv\Scripts\lint-imports.exe
# 5 contracts KEPT
```

---

## 8. 다음 후속 (MVP+α)

이 가이드의 미흡 부분 + 사용자 결정 영역:

- NN Training Panel 을 main_window 에 정식 dock (현재는 Python REPL
  으로 trainer 호출)
- `trsim install <pkg>.trsim-pkg` CLI (zip 압축 해제 + manifest 검증)
- `trsim sdk build <dir>` CLI (디렉토리 → .trsim-pkg zip pack)
- ExtendedTarget σ_glint RMS 정량 회귀 (5.21 후속)
- High-g UKF/EKF RMSE 정량 회귀 (5.22 후속)
- Adam/AdaGrad/RMSProp optimiser (numpy_mlp backend 후속)
- `workbench-train` 외부 subprocess wrapping (Task C 후속, 멀티프로세스
  학습 용)

설계 정체성 (Primary Target / FMCW Triangle 단독 / Closed-loop 등) 은
[`AGENT_GUIDE.md`](../AGENT_GUIDE.md) § 1 의 불변 원칙 우선.
