# Phase 9.3 모두 완료 인계 — 고급 기능 (2026-05-12)

이 세션에서 plan/19 § 19.8 + § 19.9.5 + § 19.7.4 Phase 9.3 의 5 task
(a/b/c/d/e) 를 모두 끝냄. Phase 9 전부 완료. 다음 세션이 5분 안에
따라잡고 **Phase 5 후속 (도메인 정량 보강)** 부터 자동 진행하기 위한
짧은 인계.

## 0. 현재 상태 (한 줄)

- HEAD = `6d9e328` (`feat(physics-lab): Phase 9.3e — Test Object
  plugin registry`)
- 누적 **1986 PASS** local (+57 across 9.3a-e in 4 feature commits)
- ruff / mypy strict / import-linter 5 contracts KEPT 매 commit
- 이 세션 4 commits + handoff main 직접 push

## 1. 사용자 설계 우선순위 (변동 없음)

> **physics_lab > simulator > editor**
>
> Physics Lab 9.1 ✓ + 9.2 ✓ + 9.3 ✓ 모두 끝났으므로 다음 우선순위:
> 1. **Phase 5 후속 (도메인 정량 보강)** — 다음 세션 진입점.
> 2. NN 보강 (Adam / workbench-train / Step 2 행).
> 3. Phase 8 HIL.
> 4. DLC CLI (install / sdk build).
> 5. UI 데이터 binding (Editor 5 activity / Simulator 8 panel
>    실 데이터).
> 6. Floating dock 옵션 B / Theme manager.

## 2. 이 세션 누적 push (4 feature commits + 1 handoff)

| commit | 단계 |
|---|---|
| `95d7927` | Phase 9.3a — Code Pane autocomplete + multi-function |
| `fce9384` | Phase 9.3b — PhysicsModelProtocol (11th SDK) |
| `9095174` | Phase 9.3c/d — NN physics + polynomial regression |
| `6d9e328` | Phase 9.3e — Test Object plugin registry |
| (handoff)  | this document |

## 3. 다음 세션 진입점 — Phase 5 후속

plan/04 § 4.3 Phase 5 의 17 검증 카테고리 중 미완 항목 정량 보강.
이전 세션의 phase_9_2_complete handoff § 6 + CLAUDE.md 의 운영
학습들을 참고. 핵심 candidate:

| # | task | 범위 |
|---|---|---|
| **5.21+** | ExtendedTarget σ_glint Monte Carlo 회귀 추가 case | 다양한 attitude / freq 에 대한 정량 invariant. |
| **5.22+** | High-g UKF / EKF RMSE 정량 추가 | 9-G 기동 시나리오, RMSE 비율 invariant. |
| **5.19/5.20+** | Multipath / horizon golden 추가 case | 4/3-earth refraction + 4/3 + 다중-주파수. |
| **5.x** | 17종 검증의 새 변형 | plan/14 의 ExtendedTarget glint, plan/16 의 GNN association 다양한 입력 등. |

이 묶음은 **테스트 추가 위주** (사용자 가시 UX 변화 없음). UI 변화
없음 → 영향 범위 좁음. 1-3 commit 권고.

대안: **NN 보강** 으로 점프. Adam optimizer + workbench-train CLI
external subprocess + Step 2 Tracker/Predictor/Classifier 행
채우기. 더 큰 작업, 사용자 가시 UX 변화 있음 (NN tab 풍부함).

## 4. Phase 9.3 구조 요점 (재사용 가능 인프라)

### 4.1 Code Pane (9.3a)

```
PhysicsLabWorkspace
  └── CodePreview (with PythonSyntaxHighlighter + PythonCodeEditor)
       └── PythonCodeEditor(QTextEdit)
            └── QCompleter (case-insensitive)
                 └── default_completion_words() static list
```

다음 단계 후보: AST-based 동적 autocomplete (Phase 9.4+). 현재는
static word list만.

### 4.2 PhysicsModelProtocol (9.3b)

SDK 의 11번째 plugin protocol. 7 멤버:
- ``name`` / ``category`` / ``parameters`` / ``time_mode`` /
  ``visualization`` (property)
- ``compute(state, params, dt_s) -> Mapping`` (method)

3 built-in 구현 (`app/physics_lab/models.py`):
- ``GravityOnlyModel`` — analytic free-fall, dynamic.
- ``BouncingBallModel`` — PL-D step packaged.
- ``FreeSpaceLossModel`` — static Friis path-loss.

9.3+ 가능한 후속 작업:
- **Library Models 카테고리 동적 채우기**: 현재는 placeholder.
  `set_physics_models(models)` API 추가 + Library Models 분기에서
  AutoParametersWidget 자동 생성.
- **Validation Bench 일반화**: 현재 BouncingBall hardcoded; plugin
  의 ``compute`` 호출로 일반화.
- **PhysicsModel Parameter Studio**: scipy fit 이 plugin params 위
  자동 동작.

### 4.3 NN-as-physics + Polynomial fit (9.3c/d)

NumpyNNPhysicsModel + PolynomialFitModel 둘 다 PhysicsModelProtocol
구현. 9.2c Validation Bench / 9.2d Parameter Studio 와 결합 가능
(다음 단계).

### 4.4 Test Object plugin (9.3e)

```python
# Plugin 작성 예
from workbench.sdk.protocols import TestObjectProtocol
from workbench.ui.physics_lab import register_visual_kind_builder

@dataclass(frozen=True)
class MyShape:
    name: str
    visual: str = "my_shape"
    radius_m: float = 1.0
    def analytic_rcs_m2(self, wl): return None

def _my_mesh(obj):
    return pv.Sphere(radius=obj.radius_m * 2.0)

# At plugin load:
register_visual_kind_builder("my_shape", _my_mesh)
```

Plugin discovery via Phase 17.4 PluginLoader 는 미래 작업
(DLC integration).

## 5. 작업 환경 (이미 검증된)

| 항목 | 값 |
|---|---|
| OS | Windows |
| Python | 3.13.3 (.venv) |
| 주요 의존 | PySide6 6.11.0, pyqtgraph 0.13.x, pyvista 0.48.1, pyvistaqt 0.11.4, numpy, h5py, scipy 1.17.1, pytest 9.0.3, pytest-qt 4.5.0, ruff, mypy 2.0, import-linter, typing_extensions |

## 6. 운영 학습 (이 세션 9.3 추가)

1. **typing.override 재발 (9.3a)** — mypy 2.0 + Python 3.13 에서
   `typing.override` 가 strict 모드에서 untyped-decorator 경고를
   유발. `typing_extensions.override` 사용해야 안전.
2. **Protocol class name + pytest collection** — 클래스 이름이
   "Test" 로 시작하면 pytest 가 test class 로 collect 시도.
   `__test__: bool = False` 를 **Protocol body 안**에 두면
   runtime_checkable 검사가 멤버로 인식해서 부수효과. 대신
   `ClassName.__test__ = False` post-class setattr 사용.
3. **scipy + Nelder-Mead bounds** (재발) — bounds 는 method-level
   미지원; loss 안 clamp 가 안전.
4. **mypy Literal 좁히기** — `act = "relu" if ... else "tanh"`
   는 mypy 가 그냥 `str` 로 추론. Activation 타입 alias 를 직접
   import + 인자 타입을 Literal 로 명시해야 통과.
5. **PolyData faces flat array** — `pv.PolyData(points, faces)`
   의 faces 는 (count, idx0, idx1, ...) 평탄화된 정수 배열.
   ruff format 이 multi-line list 로 풀어버려서 가독성 떨어짐 —
   `# fmt: off` 또는 numpy array 로 미리 빌드하는 게 깔끔.
6. **PowerShell vs Bash 셸 문법 (재발 방지)** — 사용자 기본 셸은
   PowerShell. Bash 의 `VAR=value cmd` 한 줄 prefix 패턴이
   PowerShell 에선 cmdlet 인식 실패로 죽음. 반드시 `$env:VAR =
   "value"` + `& $exe arg` 2-3 줄로 분리. handoff 의 명령 예시는
   **PowerShell 버전 우선**으로 작성하고 Bash 변형을 부가로 둘 것.

## 7. 다음 세션 진입 명령

사용자 기본 셸은 **PowerShell** — Bash 문법 (`VAR=value cmd`) 안
통하므로 PowerShell 버전 우선:

```powershell
cd "C:\Workspaces\Claude\Tracking Radar Simulator\trsim"
git pull --ff-only

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

& $PY -m pytest -q
# 1986 PASS expected

& ".\.venv\Scripts\lint-imports.exe"
# 5 contracts KEPT
```

Bash (Git Bash / WSL) 변형은 동일 변수를 line-prefix 로:

```bash
cd "C:/Workspaces/Claude/Tracking Radar Simulator/trsim"
git pull --ff-only
PY=".venv/Scripts/python.exe"
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m pytest -q
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/lint-imports.exe
```

그 다음:
1. CLAUDE.md § 1 + 이 handoff (`docs/sessions/phase_9_3_complete_
   handoff_2026_05_12.md`) 정독 (5 분).
2. **Phase 5 후속** 또는 **NN 보강** 진입 결정.
   - Phase 5: `plan/04 § 4.3 Phase 5` + `plan/14` (ExtendedTarget)
     + `plan/16` (GNN) 정독. 5.21~5.22 미완 회귀 추가.
   - NN 보강: `plan/07 § 7.5.3` Adam optimizer + workbench-train
     CLI external subprocess. `app/nn/trainer.py` 기존 인프라 확장.

세션 컨텍스트 80% 도달 시 새 handoff 작성 + 종료.

## 8. 문서 위치 정리

| 문서 | 용도 |
|---|---|
| `docs/sessions/phase_9_1_abc_handoff_2026_05_12.md` | 9.1a/b/c |
| `docs/sessions/phase_9_1_complete_handoff_2026_05_12.md` | 9.1 전체 |
| `docs/sessions/phase_9_2_complete_handoff_2026_05_12.md` | 9.2 전체 |
| `docs/sessions/phase_9_3_complete_handoff_2026_05_12.md` | **이 인계** (Phase 9 모두 끝) |
| `CLAUDE.md` § 1 | 누적 진행 log |
| `plan/19_physics_lab.md` | Physics Lab 설계 (1000+ 줄, 9.1~9.3 모두 구현 완료) |
