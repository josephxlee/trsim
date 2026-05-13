# Phase 6 NN 보강 (A1-a/b/c/d) — 4 sub-step 인계 (2026-05-13)

phase_5_followup handoff § 3 권고 "NN 보강 1 wave" 를 처음부터 끝까지
진행. Adam optimizer + workbench-train CLI 는 실 구현, Step 2 per-
category dispatch + multi-step rollout RMSE 는 framework + stub.

## 0. 현재 상태 (한 줄)

- HEAD = `d5ac835` (`A1-d multi-step rollout RMSE stub`)
- 누적 **2101 PASS** local (2065 → 2101, +36 across 4 sub-steps)
- ruff / mypy --strict / import-linter 5 contracts KEPT 매 commit
- 이 세션 4 feature commits + 1 handoff main 직접 push

## 1. 사용자 설계 우선순위 (변동 없음)

> **physics_lab > simulator > editor**
>
> Phase 9 ✓ + Phase 5 후속 ✓ + **Phase 6 NN 보강 ✓** (이 세션). 다음
> 진입점 후보:
> 1. **Phase 5 추가 후속** — 5.7b / 5.8b / 5.11b / 5.12b / #18 / #19
>    재현성. 가장 작은 단위, src 변경 0.
> 2. **Phase 7 DLC CLI 완성** — sdk build / install / sdk test +
>    io/package_io + package_manager_panel + sample DLC + tutorial.
> 3. Phase 8 HIL 전체 (큰 작업, 새 protocol + 새 layer).
> 4. Phase 3 MVP 누락 4 모듈 (bundle_service / evaluator (Command
>    Lineage) / physics_gate / io/dem_import).
> 5. Phase 4 UI 실 데이터 binding / dem_import_wizard / domain_settings
>    / installation_panel.

## 2. 이 세션 누적 push (4 commits + 1 handoff)

| sub | commit | new | 범위 |
|---|---|---|---|
| A1-a | `0e77448` | +13 | Adam optimizer (numpy 구현, backend="numpy_mlp_adam") |
| A1-b | `b122051` | +15 | `trsim train --job <toml>` CLI + load_training_job_from_toml |
| A1-c | `adb6027` | +6 | Step 2 per-category dispatch (Pairing 실 + Tracker/Predictor/Classifier n/a) |
| A1-d | `d5ac835` | +2 | multi_step_rollout_rmse stub + n_steps validation |
| (handoff) | (this) | — | 이 문서 |

## 3. A1-a — Numpy Adam Optimizer

`src/workbench/app/nn/numpy_mlp.py`:
- `AdamState` dataclass — per-parameter m / v + step counter `t`.
- `init_adam_state(params)` — zero-init factory.
- `train_one_epoch_adam(params, state, x, y, ...)` — full epoch
  Adam loop with default beta1=0.9 / beta2=0.999 / eps=1e-8. Full
  input validation (lr > 0, batch_size > 0, beta1 / beta2 in (0,1),
  eps > 0).
- `_adam_step` — Kingma & Ba bias-corrected `m_hat / (1 - beta1^t)`,
  `v_hat / (1 - beta2^t)`, `param -= lr * m_hat / (sqrt(v_hat) + eps)`.

`src/workbench/app/nn/trainer.py`:
- `TrainingBackend` literal extended to
  `("fake", "numpy_mlp", "numpy_mlp_adam")`.
- `_run_numpy_mlp(job, optimizer=)` keyword routes SGD vs Adam.

`src/workbench/ui/nn_training/training_panel.py`:
- `_BACKENDS` adds `numpy_mlp_adam` between `numpy_mlp` and `fake`.

13 신규 tests (8 helper + 4 trainer + 1 panel combo). Bias-correction
at t=1 lock confirms the Kingma & Ba formula bit-for-bit.

## 4. A1-b — workbench-train CLI

`src/workbench/app/nn/trainer.py`:
- `load_training_job_from_toml(path)` — TOML → TrainingJob loader
  with BOM strip + required-key check + relative-path resolution +
  invalid-UTF-8 rejection.
- `resolve_backend_from_optimizer(optimizer)` — `"adam"` ->
  `"numpy_mlp_adam"`, else `"numpy_mlp"`.

`src/workbench/cli/main.py`:
- New `trsim train --job <toml>` subparser with `--backend`
  (auto / fake / numpy_mlp / numpy_mlp_adam, default auto),
  `--seed`, `--output <json>`.
- Per-epoch JSON records stream to stdout (one document per line);
  final summary JSON written to `--output` or stdout.
- Non-zero exit codes on missing files / invalid TOML / training
  errors.

15 신규 tests covering TOML loader (5), backend resolver (3),
parser (2), end-to-end runs (3), error paths (2).

## 5. A1-c — Step 2 Per-Category Dispatch

`src/workbench/app/nn/evaluator.py`:
- `tracker_loss(plugin, dataset_path)` — stub raising
  `NotImplementedError`.
- `predictor_loss(plugin, dataset_path)` — same.
- `classifier_loss(plugin, dataset_path)` — same.

`src/workbench/ui/simulator/nn_mode/step2_controller.py`:
- `_on_run_eval` iterates `ERROR_CATEGORIES` and dispatches via
  `_eval_category(cat, plugin, path)`. Pairing -> real
  `pairing_loss`; others -> stub -> `n/a (plugin unsupported)`.
- `_reset_row_with_error(category, message)` generalises the old
  `_reset_pairing_row_with_error` (which is now a backwards-compat
  alias).
- Missing dataset / plugin error now fills *all four* rows with the
  same diagnostic.

6 신규 tests (3 evaluator stubs + 3 controller dispatch).

## 6. A1-d — Multi-step Rollout RMSE (stub)

`src/workbench/app/nn/evaluator.py`:
- `multi_step_rollout_rmse(plugin, dataset_path, *, n_steps)` —
  raises `NotImplementedError` until the sequence dataset spec +
  Predictor / Tracker NN plugin ship.
- Input validation (`n_steps > 0`) fires *before* the
  NotImplementedError so callers get a deterministic ValueError
  for malformed input regardless of the stub state.

2 신규 tests (NotImplementedError + n_steps validation).

## 7. 정합성 검사 결과 (Phase 6 끝)

`docs/MVP_STATUS.md` Phase 6 매트릭스 모두 실제 코드와 일치:

| 항목 | 매트릭스 | 코드 |
|---|---|---|
| Adam optimizer | ✓ (A1-a) | `AdamState` + `train_one_epoch_adam` + `numpy_mlp_adam` backend + UI combo ✓ |
| workbench-train CLI | ✓ (A1-b) | `trsim train` subparser + `load_training_job_from_toml` ✓ |
| Step 2 per-category dispatch | △ (A1-c) | `_on_run_eval` 4-row loop ✓, real Tracker/Predictor/Classifier losses TBD |
| multi-step rollout RMSE | △ (A1-d) | stub function ✓, sequence dataset spec TBD |

Phase 6 frame ✓ + 4 보강 완료 (2 ✓ + 2 △).
5 contracts KEPT 매 commit. ruff / mypy --strict / import-linter 모두
clean.

## 8. 운영 학습 (이 세션 정리)

1. **mypy strict Protocol vs concrete type mismatch** (A1-c) — stub
   함수의 `plugin` 인자 타입을 `_TrackerPredictor` (별도 Protocol)
   으로 정의했더니 Step 2 controller 에서 `_PairingPredictor` 와의
   호환성 실패. 해결: stub 함수는 어차피 NotImplementedError 만
   raise 하므로 `plugin: object` 로 완화 — type narrow 가 의미 없는
   stub 에서는 가장 wide 한 타입이 가장 robust.
2. **JSON 출력 stream + summary 혼합** (A1-b) — `--output` 옵션 없이
   stdout 만 사용하면 per-epoch JSON line + indent=2 summary 가
   섞여 test 가 parse 못 함. 해결: stdout 은 line-by-line epoch
   stream 전용, summary 는 `--output` 파일로 분리. test 도 `--output`
   기반으로 작성.
3. **Stub vs ✓ vs △ 구분** — A1-c / A1-d 는 framework 완성 (✓ 가
   아님) + 실 구현 TBD. △ 마크가 정확함 (skeleton 만 있고 실 데이터
   binding 또는 CLI 미완). MVP_STATUS.md 의 △ semantics 가 이런
   "framework 마련, 구현 TBD" 케이스에 잘 맞음.
4. **plan/07 § 7.6 Tracker/Predictor/Classifier 가 카테고리별 plugin
   protocol 분리** (이미 sdk/protocols.py 에 정의됨) — 실 구현 시
   각 protocol 마다 sample plugin 1개씩 만들면 매트릭스 △ → ✓.

## 9. 다음 세션 진입 명령

```powershell
cd "C:\Workspaces\Claude\Tracking Radar Simulator\trsim"
git pull --ff-only

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

& $PY -m pytest -q
# 2101 PASS expected

& ".\.venv\Scripts\lint-imports.exe"
# 5 contracts KEPT
```

그 다음:
1. CLAUDE.md § 1 + 이 handoff (`docs/sessions/phase_6_augmentation_
   2026_05_13.md`) + `docs/MVP_STATUS.md` 정독 (5 분).
2. `docs/MVP_STATUS.md § "미구현 우선순위 리스트"` 참조해서 다음
   진입점 결정. 권고 순서:
   - **Phase 5 추가 후속** (5.7b / 5.8b / 5.11b / 5.12b) — 가장 작음.
   - **Phase 7 DLC CLI 완성** — 사용자 가시 큰 변화 (sdk build /
     install).
   - **Phase 3 누락 4 모듈** — bundle_service / evaluator / physics_
     gate / dem_import.
   - **Phase 8 HIL 전체** — 매우 큰 작업, 새 protocol + 새 layer.

세션 컨텍스트 80% 도달 시 새 handoff 작성 + 종료.

## 10. 문서 위치 정리

| 문서 | 용도 |
|---|---|
| `docs/sessions/phase_5_followup_2026_05_13.md` | Phase 5 후속 12 sub-step |
| `docs/sessions/phase_6_augmentation_2026_05_13.md` | **이 인계** (Phase 6 NN 보강 4 sub-step) |
| `docs/MVP_STATUS.md` | Phase 0~9 매트릭스 (이 세션 4 행 갱신됨) |
| `CLAUDE.md` § 1 | 누적 진행 log (이 세션 갱신됨) |
| `docs/agent_workflows/mvp_status_update.md` | 매트릭스 자동 갱신 워크플로 |
