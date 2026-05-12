# Phase 9.2 모두 완료 인계 — 외부 자료 + 학습 (2026-05-12)

이 세션에서 plan/19 § 19.9 Phase 9.2 의 4 task (a/b/c/d) 를 모두 끝냄.
다음 세션이 5분 안에 따라잡고 **Phase 9.3 (고급 기능)** 부터 자동
진행하기 위한 짧은 인계.

## 0. 현재 상태 (한 줄)

- HEAD = `5de15a0` (`feat(physics-lab): Phase 9.2d — Lab-C Parameter
  Studio (scipy fit)`)
- 누적 **1929 PASS** local (+79 신규 across 9.2a-d)
- ruff / mypy strict / import-linter 5 contracts KEPT 매 commit
- 이 세션 4 commits main 직접 push (9.2)

## 1. 사용자 설계 우선순위 (변동 없음)

> **physics_lab > simulator > editor**
>
> 후속 Phase 우선순위:
> 1. **Phase 9.3** (고급 기능) — 다음 세션 진입점.
> 2. Phase 5 후속 (도메인 정량 보강).
> 3. NN 보강 (Adam / workbench-train / Step 2 행).
> 4. Phase 8 HIL.
> 5. DLC CLI (install / sdk build).
> 6. UI 데이터 binding (Editor 5 activity / Simulator 8 panel 실 데이터).
> 7. Floating dock 옵션 B / Theme manager.

## 2. 이 세션 누적 push (4 commits)

| commit | 단계 |
|---|---|
| `a199e3a` | Phase 9.2a/b — Measured Data + Papers Library |
| `43153f9` | Phase 9.2c — Lab-B Validation Bench (RMSE overlay) |
| `5de15a0` | Phase 9.2d — Lab-C Parameter Studio (scipy fit) |
| (handoff)  | this document |

## 3. 다음 세션 진입점 — Phase 9.3

plan/19 § 19.11.2 의 Phase 9.3 5 task:

| # | task | 범위 | 추정 |
|---|---|---|---|
| **9.3a** | Code Pane Edit mode 강화 | autocomplete (jedi) + 다중 함수 + import + `@physics_param` 직접 작성 | 2~3 sub-step |
| **9.3b** | PhysicsModelProtocol plugin (11번째 SDK) | `sdk/protocols.py` 신규 protocol + Physics Lab Library plugin load | 2 sub-step |
| **9.3c** | NN 으로 물리 대체 (form 2) | Phase 6 NN 통합 + PhysicsModelProtocol 의 NN 구현 | 2 sub-step |
| **9.3d** | Symbolic regression (form 4) | PySR 통합 — measured data → 수식 추출 | 1~2 sub-step |
| **9.3e** | Test Object plugin | TestObject Protocol + 사용자 정의 도형 | 1 sub-step |

총 **8~10 sub-step**. plan/19 § 19.8 (PhysicsModelProtocol) 가 핵심
설계 reference. plan/19 § 19.12.3 시나리오 3 (새 multipath 모델
plugin) 가 9.3 end-to-end 예시.

분할 권고:
- 9.3a 한 묶음 (Code Pane autocomplete + 검증)
- 9.3b 한 묶음 (PhysicsModelProtocol — 인프라가 클 가능성)
- 9.3c + 9.3d 한 묶음 (NN/PySR 결합)
- 9.3e 한 묶음 (Test Object plugin)

## 4. Phase 9.2 구조 요점 (다음 세션이 활용)

### 4.1 Library 5 카테고리

```
▼ Tests           ← BOUNCING_BALL_ROW + 9 Test Objects
▼ Models          ← Gravity / Air Drag (placeholders)
▼ Saved Experiments  ← user TOML snapshots (9.1f)
▼ Measured Data   ← CSV/HDF5 + sidecar TOML (9.2a)
▼ Papers          ← PDF + sidecar TOML (9.2b)
```

9.3 가 추가할 위치 (예상):
- "User Plugins" 6번째 카테고리 (PhysicsModelProtocol plugins +
  TestObject plugins)

### 4.2 Validation + Fit workflow (9.2c/d)

```
[User] Library > Measured Data > select <dataset>
   ↓
[Workspace] measured_dataset_selected signal
   ↓
[Controller] run_validation_from_dataset → overlay 2 curves + emit
   metrics
   ↓
[User] inspect status bar (RMSE, max|err|, corr)
   ↓
[User] click "Fit to selected measurement"
   ↓
[Workspace] fit_requested signal
   ↓
[Controller] fit_to_measurement → scipy Nelder-Mead → emit FitResult
   ↓
[Workspace] auto-update sliders + status bar
   ↓
[User] iterate or save SavedExperiment with fitted params
```

9.3 가 확장할 부분:
- PhysicsModelProtocol plugin 이 Library "Models" 카테고리에 등록
- Validation Bench 가 plugin 의 `compute()` 호출 (현재는 Bouncing
  Ball 하드코딩)
- Parameter Studio fit 이 plugin 의 `parameters` metadata 자동 활용

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

9.3 가 추가할 가능성: `[fit_result]` 섹션 — Parameter Studio 결과
(target_dataset, final_rmse, fit_config, fit_iterations) 저장.

### 4.4 도메인 layer 모듈 분포

```
domain/physics_lab/
├── test_objects.py        (9.1c)
├── parameter_metadata.py  (9.1c — @physics_param)
├── time_modes.py          (9.1e)
├── saved_experiments.py   (9.1f)
├── measured_data.py       (9.2a)
├── papers.py              (9.2b)
└── validation.py          (9.2c)

app/physics_lab/
├── bouncing_ball.py       (PL-D + 9.1g drag)
├── clock.py               (PL-D)
└── parameter_fitter.py    (9.2d — scipy wrapper)

ui/physics_lab/
├── workspace.py           (PL-A + ... + 9.2c/d wiring)
├── bouncing_ball_demo.py  (Library + Code + Plot + Parameters +
│                          Controller — single ~1300-line module)
├── python_highlighter.py  (9.1a)
├── auto_parameters.py     (9.1c)
└── test_object_view.py    (9.1d)
```

### 4.5 9.2c/d 가 9.3 에 전달하는 API

- `compute_validation_metrics` — pure domain function, plugin-friendly.
  9.3 의 PhysicsModelProtocol 도 같은 metric 사용 권장.
- `fit_bouncing_ball` — 시뮬레이터-specific. 9.3 가 plugin 의 fit
  도 같은 scipy.optimize 패턴으로 wrap 가능 — `fit_physics_model
  (plugin, measured_x, measured_y, ...)` 같은 일반화 함수 권장.

## 5. Phase 9.3 진입 시 우선 검토 사항

1. **jedi 의존성**: Code Pane autocomplete 에 사용. 가벼움
   (~5 MB), pyproject 에 추가 필요. 또는 Qt 내장 QCompleter +
   tokenize-based 직접 구현 (외부 의존성 회피).
2. **PhysicsModelProtocol 의 위치**: `sdk/protocols.py` 가 기존
   10 protocol + PhysicsModelProtocol = 11번째. plan/02 § 2.4 의
   SDK 의존성 매트릭스 갱신 필요.
3. **plugin 안전망**: plan/19 § 19.8.3 — Physics Lab Validation
   Bench 통과 plugin 만 시뮬에 적용. 9.2c 인프라가 이미 있으므로
   9.3 plugin 은 자동으로 Validation Bench 회귀 통과해야 등록.
4. **PySR**: Julia 의존성 (sub-process). 무거움. plan/19 § 19.11.2
   는 9.3+ 로 명시 — MVP 는 skip 또는 scipy.curve_fit 으로 단순화.
5. **TestObject plugin**: 현재 9 표준만. plan/19 § 19.7.4 가 plugin
   가능성 명시. domain layer 의 `TestObject` Union 을 확장 가능한
   Protocol 로 변경 필요.

## 6. 작업 환경 (이미 검증된)

| 항목 | 값 |
|---|---|
| OS | Windows |
| Python | 3.13.3 (.venv) |
| 주요 의존 | PySide6 6.11.0, pyqtgraph 0.13.x, pyvista 0.48.1, pyvistaqt 0.11.4, numpy, h5py, **scipy 1.17.1**, pytest 9.0.3, pytest-qt 4.5.0, ruff, mypy 2.0, import-linter, typing_extensions |
| 실행파일 | `.venv\Scripts\trsim.exe` (= `python -m workbench`) |
| Push 권한 | `.claude/settings.local.json` `Bash(git push origin HEAD:main)` allow 등록 |

## 7. 운영 학습 (이 세션 9.2 추가)

1. **np.genfromtxt structured array** — `names=True` 는 structured
   dtype 반환. plain 2D float64 로 변환은 `genfromtxt(skip_header=1,
   dtype=np.float64)` 가 명확. 회귀 회피.
2. **tomllib 반환 타입 `dict[str, object]`** — mypy strict 가
   `str(meta.get("x", ""))` 명시 cast 요구. 직접 단언 패턴 정착.
3. **scipy Nelder-Mead + bounds** — 구버전 scipy 는 method-level
   bounds 미지원. Loss 안 clamp 가 안전.
4. **Test trajectory generation** — 측정 vs 시뮬 일치 검증 시
   같은 dt_s 권장 (sub-step discretization mismatch 가 RMSE 키움).
5. **scipy.optimize.minimize Nelder-Mead `xatol`/`fatol`** — 기본값이
   너무 큰 경우 (1e-4) 수렴이 너무 빠름. 1e-5 권장 (Bouncing Ball
   의 ground bounce discontinuity 가 작은 시간 step 에서 RMSE 변동
   유발).

## 8. 다음 세션 진입 명령

```bash
cd "C:/Workspaces/Claude/Tracking Radar Simulator/trsim"
git pull --ff-only
PY=".venv/Scripts/python.exe"
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m pytest -q
# 1929 PASS expected
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 .venv/Scripts/lint-imports.exe
# 5 contracts KEPT
```

그 다음:
1. CLAUDE.md § 1 + 이 handoff (`docs/sessions/phase_9_2_complete_
   handoff_2026_05_12.md`) 정독 (5 분).
2. `plan/19_physics_lab.md` § 19.8 (PhysicsModelProtocol) +
   § 19.12.3 (새 multipath 모델 plugin 시나리오) 정독 (10 분).
3. **Phase 9.3a 진입** — Code Pane Edit 강화 (autocomplete 우선).
   또는 9.3b 부터 (PhysicsModelProtocol 인프라).

세션 컨텍스트 80% 도달 시 또 새 handoff 작성 + 종료.

## 9. 문서 위치 정리

| 문서 | 용도 |
|---|---|
| `docs/MVP_USAGE.md` | 사용 가이드 |
| `docs/MVP_GUIDE.md` (rev8) | 검증 가이드 |
| `docs/sessions/phase_9_1_abc_handoff_2026_05_12.md` | 9.1a/b/c |
| `docs/sessions/phase_9_1_complete_handoff_2026_05_12.md` | 9.1 전체 |
| `docs/sessions/phase_9_2_complete_handoff_2026_05_12.md` | **이 인계** |
| `CLAUDE.md` § 1 | 누적 진행 log |
| `plan/19_physics_lab.md` | Physics Lab 설계 (1000+ 줄) |
