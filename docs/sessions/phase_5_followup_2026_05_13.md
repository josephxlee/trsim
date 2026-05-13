# Phase 5 후속 (도메인 정량 보강) — 12 sub-step 인계 (2026-05-13)

이 세션에서 phase_9_3 complete handoff § 3 의 권고대로 **Phase 5
후속 (도메인 정량 보강)** 을 처음부터 끝까지 진행. 17 검증 카테고리
중 11개에 closed-form scaling invariant / boundary / multi-band /
monotonicity / cross-axis 정량 시험을 추가. src 변경 0, test-only.

## 0. 현재 상태 (한 줄)

- HEAD = `13210b3` (`test(physics): Phase 5.5b — drag-law scaling +
  gravity ENU invariants`)
- 누적 **2065 PASS** local (1986 → 2065, +79 신규 across 12 sub-steps)
- ruff / mypy --strict / import-linter 5 contracts KEPT 매 commit
- 이 세션 12 commits + handoff main 직접 push

## 1. 사용자 설계 우선순위 (변동 없음)

> **physics_lab > simulator > editor**
>
> Phase 9 전부 끝, **Phase 5 후속 끝** (이 세션). 다음 진입점:
> 1. **NN 보강** — Adam optimizer + workbench-train CLI external
>    subprocess + Step 2 Tracker/Predictor/Classifier 행 채우기.
> 2. Phase 8 HIL.
> 3. DLC CLI (install / sdk build).
> 4. UI 데이터 binding (Editor 5 activity / Simulator 8 panel 실 데이터).
> 5. Floating dock 옵션 B / Theme manager.

## 2. 이 세션 누적 push (12 commits + 1 handoff)

| sub | commit | new | 보강 카테고리 |
|---|---|---|---|
| 5.21b | `1588b1f` | +9 | ExtendedTarget glint — N=2/5/10 × L=4/12/40 scaling, plan/14 § 14.10.6 closed-form lock (missile/aircraft/ship examples) |
| 5.22b | `36f3e9c` | +6 | Tracker — Bar-Shalom coordinated-turn (0.157 rad/s, ~1.6 g) sustained maneuver, innovation plateau invariant (vs 5.22's single-step spike) |
| 5.19c/5.20c | `abfe398` | +12 | Multipath/horizon — S-band (constructive F^2~4) / Ku-band lobing landmarks / k=1/1.5 horizon |
| 5.18b | `e21ed86` | +5 | GNN — 4×4 dense / 3+1 clutter / boundary gating (calibrated offset) / chi^2 quadratic-in-radial-offset |
| 5.13b | `dab6492` | +6 | FrameProfiler — warmup off-by-one (N+1 / exactly N) / bimodal+ramp distribution / reset idempotent / report_all ordering |
| 5.4b | `452f079` | +7 | ISA — stratosphere T/rho clamp (15 km) / ideal gas law / rain monotonicity in freq+rate |
| 5.10b | `b76a695` | +5 | CFAR — alpha asymptotic `-ln(Pfa)` (Skolnik IRS § 7.4) / N-monotonic / CA-mask vs OS-recover (interferer scenario) |
| 5.9b | `2390ee2` | +6 | RCS — Rayleigh r^6 / lambda^-4 / cylinder linear-in-r / trihedral = 3x flat-plate / dBsm 6-decade round-trip |
| 5.2b | `f0139e4` | +7 | FMCW — beat linear in (R, B, 1/T_s) / doppler antisymmetric / range_resolution inverse-B / receding-target round-trip |
| 5.3b | `90635cb` | +5 | Parabolic — BW inverse-f / G_peak +6 dB on 2x D / +3 dB on 2x eff / radial symmetry / monotone descent |
| 5.6b | `17cca72` | +5 | Monopulse — axis decoupling / sign antisymmetry / Re(δ/σ) sigma-magnitude scaling / slope axis independence |
| 5.5b | `13210b3` | +6 | Drag — v^2 / area / Cd scaling / altitude monotone decrease / antiparallel-to-v / gravity ENU lock |
| (handoff) | (this) | — | 이 문서 |

## 3. 다음 세션 진입점 — NN 보강 (권고)

plan/07 § 7.5.3 + § 7.6 + § 7.5 후속. 현재 `app/nn/trainer.py` 의
TrainerService 는 `backend ∈ {"fake", "numpy_mlp"}` (mini-batch SGD).
보강 candidate:

| # | task | 범위 |
|---|---|---|
| 7.x | Adam optimizer | numpy 구현 (Phase 6.7+ trainer 의 `backend="numpy_mlp_adam"`). mini-batch + bias-corrected moments. |
| 7.x | workbench-train CLI | external subprocess (TrainingJob TOML 받아서 run). 분리된 process 라 GUI freeze 회피. |
| 7.x | Step 2 Tracker 행 | NNStep2Controller 가 현재 Pairing 만 채움. Tracker (RMSE on EKF/UKF residual) / Predictor (next-frame position) / Classifier (target type) 행 추가. |
| 7.x | NNStep2 dataset metric | live evaluation 의 `compute_pairing_loss` 외에 multi-step rollout RMSE. |

대안 — Phase 5 마지막 미완 (5.x 후속 변형이 많이 남음):
- 5.7b Planar array element_power 추가 (theta/phi 의 다른 kind, 입력 검증)
- 5.8b Ballistic 추가 (drag coefficient sensitivity, terminal velocity)
- 5.11b PerformanceClock 추가 (clock jitter, factory cross-check)
- 5.12b FrameBoundaryDetector 추가 (frame_id wrap, reset count)

또는 plan/04 § 4.3 Phase 5 list 의 #18 (Reference Timing 재현성)
+ #19 (Frame Profiler 결과 재현성) — 5.13b 가 distribution invariant
가 추가했지만, **재현성** 측면 (같은 seed/load → 같은 결과) 은 별
도. 외부 부하 의존성 때문에 까다로움.

## 4. 작업 환경 (이미 검증된)

| 항목 | 값 |
|---|---|
| OS | Windows 11 Pro |
| Python | 3.13.3 (.venv at main worktree root) |
| Worktree | `.claude/worktrees/optimistic-mayer-2c06ba` |
| Test count | 2065 PASS local |
| Contracts | 5 KEPT (Layer / Editor-Sim isolation / Domain ⊥ Qt / SDK ⊥ App+UI) |

## 5. 운영 학습 (이 세션 정리)

1. **measure-and-lock vs closed-form lock** (5.18b 발견) — implementation
   의 내부 scaling (예: `H P H^T + R` 의 track-position-dependent 변수)
   이 숨겨져 있으면 closed-form expected 가 fragile. 대신 unit-sigma
   에서 한 번 측정하고 그 비율로 target chi² 의 offset 을 역산하면
   robust.
2. **amplitude-weighted centroid 의 L² artifact** (5.21b 발견) —
   uniform RCS line target 의 glint std 가 ratio (L_large/L_small)²
   로 폭주. 균등 amplitude → centroid 가 geometric centroid (= target
   position) → glint 가 거의 0 → L-scaling 검증은 monotonicity 만,
   ratio 는 asymmetric RCS 필요.
3. **numpy.percentile linear-interp 의 tail sensitivity** (5.13b) —
   p99 가 1 outlier 안 잡힘 (101 samples 에서 sorted index 99 가
   여전히 fast cluster). 5 outliers 비율 필요. tail percentile
   regression 짤 때 outlier 비율 결정 핵심.
4. **RUF007 / unused-ignore** (5.5b) — itertools.pairwise 우선 +
   `zip(..., strict=False)` 도 RUF007. mypy --strict 에서 stale
   `# type: ignore[arg-type]` 가 `[unused-ignore]` 로 잡힘. 검증
   파일 손댈 때 함께 cleanup.
5. **plan/14 example 값 lock** — § 14.10.6 의 missile / aircraft /
   ship rule-of-thumb 예시 (1.4 / 3.4 / 22 m) 를 closed-form 으로
   먼저 lock-in 하면 future drift detection 가능.
6. **bimodal vs ramp distribution percentile** (5.13b) — 둘 다
   필요. bimodal 이 tail behavior 정량, ramp 가 monotone+positional
   accuracy 정량.

## 6. 다음 세션 진입 명령

```powershell
cd "C:\Workspaces\Claude\Tracking Radar Simulator\trsim"
git pull --ff-only

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

& $PY -m pytest -q
# 2065 PASS expected

& ".\.venv\Scripts\lint-imports.exe"
# 5 contracts KEPT
```

그 다음:
1. CLAUDE.md § 1 + 이 handoff (`docs/sessions/phase_5_followup_
   2026_05_13.md`) 정독 (5 분).
2. **NN 보강** 또는 **Phase 5 추가 후속** (5.7b/5.8b/5.11b/5.12b)
   결정.
   - NN: `plan/07 § 7.5.3` Adam optimizer + `app/nn/trainer.py` 의
     `backend` literal 에 `"numpy_mlp_adam"` 추가. workbench-train
     CLI 는 `cli/main.py` 에 새 subparser.
   - Phase 5 추가: 위 § 3 의 candidate 목록.

세션 컨텍스트 80% 도달 시 새 handoff 작성 + 종료.

## 7. 문서 위치 정리

| 문서 | 용도 |
|---|---|
| `docs/sessions/phase_9_3_complete_handoff_2026_05_12.md` | Phase 9 마감 |
| `docs/sessions/phase_5_followup_2026_05_13.md` | **이 인계** (Phase 5 후속 12 sub-step) |
| `docs/sessions/phase_5_verification_kickoff.md` | Phase 5 초기 마감 (1234 PASS 시점) |
| `CLAUDE.md` § 1 | 누적 진행 log (이 세션 갱신됨) |
| `plan/04 § 4.3` Phase 5 | 17 검증 카테고리 list |
