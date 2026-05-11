# Phase 5 — 물리 검증 프레임워크 (kickoff + 마감)

**세션 후반부 (2026-05-10~11) — 5.1~5.22 + 5.15/5.16 모두 완료**.
**Phase 5 전체 마감**. 다음 세션은 Phase 6 (NN 통합) 진입.
**누적 test**: Phase 4 끝 998 → Phase 5 끝 1234 (+236 신규 tests).

## 0. 한 줄 정의

plan/04 § 4.3 Phase 5 = "물리 검증 프레임워크 뼈대 + 19 검증 카테고리".
이번 세션은 인프라 (5.1) + FMCW (5.2) + Parabolic antenna (5.3) 만.
**16+ 카테고리 남음**.

## 1. 진행한 sub-step

| sub | sha | 산출 |
|---|---|---|
| 5.1 | `1ec9cda` | `tests/physics/golden_dataset.py` — GoldenDatasetMeta + GoldenSample + GoldenDataset frozen+slots, JSON load/save (sorted keys), case(id) lookup. `tests/physics/golden/` 디렉토리 + sample reference. 9 tests. |
| 5.2 | `2a152b5` | `tests/physics/test_fmcw_propagation.py` + `golden/fmcw_propagation.json` — beat_freq / doppler / range_resolution / wavelength 4 함수 + UP/DOWN beats round-trip + zero-range / sign convention. 8 tests, rtol=1e-12. |
| 5.3 | `8a81e71` | `tests/physics/test_parabolic_antenna.py` + `golden/parabolic_antenna.json` — beamwidth (D=0.6/1.2m @ 9.5GHz) + 2x scaling + peak gain (eff=0.6) + pattern (boresight=1.0, half-bw=0.5) + 입력 검증 5종. 11 tests. |
| 5.4 | `0320aef` | `tests/physics/test_atmosphere_isa.py` + `golden/atmosphere_isa.json` — ISA temperature (sea/1km/11km) + pressure (sea/1km/5km) + density (sea/1km) + rain_attenuation_dbpkm (10GHz 4mm/h) + lapse linearity + tropopause clamp + zero-rain edge + 4 validation. 13 tests. |
| 5.5 | `5ede1c6` | `tests/physics/test_dynamics_forces.py` + `golden/dynamics_forces.json` — gravity 선형 mass scaling + drag zero-velocity / 100mps east 정확값 + 임의 3 velocity 에서 dot(F_drag, v) ≤ 0 invariant. 6 tests. |
| 5.6 | `2b4110f` | `tests/physics/test_monopulse_error.py` — pure-real ratio recovery, imaginary-delta zero error, sigma 위상 회전 invariant, slope 2배 → error 2배, slope≤0 / |sigma|=0 rejection, sum_amplitude=|sigma|. golden JSON 없음 (closed-form analytic). 9 tests. |
| 5.7 | `a3620a1` | `tests/physics/test_planar_array_element.py` — element_power isotropic unity / cos boresight / 30·45·60 deg 정확값 / 90+ back-hemisphere zero / off-axis hypot 회전 invariant / unknown kind rejection / monotonicity (itertools.pairwise). 22 tests. |
| 5.8 | `c73cbc6` | `tests/physics/test_ballistic_analytic.py` — vacuum free-fall position/velocity at 1s/2s rtol=1e-12 + 수직 fall horizontal invariant + sim_t 증가 + upward throw 왕복 + apex velocity 0 / 높이 v0²/(2g) + drag=0 atm 무관 + drag>0 vacuum 보다 천천히 + BallisticDynamics validation + 45° 사선 throw range. 12 tests. |
| 5.9 | `8298393` | `tests/physics/test_rcs_single.py` — sphere geometric πr² / Rayleigh + flat plate 4πA²/λ² (A² scaling) + cylinder broadside (L² scaling) + trihedral corner (a⁴ scaling) + dBsm round-trip. 14 tests. |
| 5.10 | `e646cfc` | `tests/physics/test_cfar_detector.py` — alpha_ca_for_pfa Skolnik closed-form 3 case + monotonicity + 입력 validation + ca_cfar_1d spike detection + 2048-cell noise false-alarm + edge cells False + os_cfar_1d clutter-edge spike + 2D shape rejection. 16 tests. |
| 5.11 | `890e148` | `tests/unit/app/timing/test_performance_clock.py` — PerformanceClock 생성자 reject + 두 factory + budget exhausted → sleep 0 + short frame pad ~budget + factory round-trip. 9 tests (app-layer 첫 시작). |
| 5.12 | `ea903bc` | `tests/unit/app/timing/test_frame_boundary_detector.py` — 기본 frame_id=0 + on_track_output 증가 + reset + 명시 frame_id 42 + 매 호출 True invariant. 6 tests. |
| 5.13 | `a1b8cd0` | `tests/unit/app/timing/test_frame_profiler.py` — FrameProfiler warmup / record/stages/report/reset + uniform distribution percentile = 2.0 ms + below-warmup NaN + StageTimingProbe 1ms sleep 측정 + 예외 발생 시에도 sample 기록. 12 tests. |
| 5.14 | `f41044f` | `tests/physics/test_extended_target_glint.py` + `golden/extended_target_glint.json` — 2-scatterer along-LOS amplitude(1e-6) / amp ratio((R0/R1)²) / centroid(1000.4995) / |sum|(1.2248e-6) / total_signal real+imag bit-for-bit. Skolnik invariants: apparent ∈ scatterer ENU bbox (5 attitude/freq cases) + |sum|≤Σamp triangle ineq + total_rcs_dbsm attitude-invariant (4 cases) + deterministic 반복 + body-x scatterers roll invariant + 대칭 paired scatterers freq sweep glint mean≈0. 19 tests. 기존 Phase 2.7 unit test (`tests/unit/physics/test_extended_target.py`) 와 중복 회피 — 5.14 는 closed-form golden + 회귀 invariant 만. |
| 5.15 | TBD | `src/workbench/domain/coherence_validator.py` 신규 구현 + `tests/unit/domain/test_coherence_validator.py` — ValidatorSeverity 3-rung + ValidatorMessage frozen + `validate_map` (terrain ⊂ bounds + sea cell <= sea_surface + all-land/all-sea INFO) + `validate_targets` (waypoint ∈ bounds + airborne > terrain + surface near sea ±1m tol) + `validate_buildings` (base ∈ bounds) + `has_errors` Run-gate. 15 tests. |
| 5.16 | TBD | `src/workbench/domain/simulation_domain.py` 신규 구현 + `tests/unit/domain/test_simulation_domain.py` — `sample_terrain_safe(map_, e, n)` bilinear interp + sea-cell snap to sea_surface.z + bounds-outside None. corner exact / midcell / 동쪽 slope linear / sea_corner / land-only invariant. 9 tests. |
| 5.17 | TBD | `tests/unit/domain/test_ekf_ukf_scenario.py` — F(dt) bit-for-bit on CV truth + 50-frame perfect-measurement 비발산 (pos<7.5m, vel<1.5m/s) + cov trace 매 update 감소 invariant + UKF predict ≡ EKF predict on linear CV (atol=1e-9) + UKF perfect-update pulls state + EKF innovation 노름 ½ 이하 + EKF/UKF predict negative dt reject. 9 tests. 기존 unit test (`tests/unit/domain/test_tracker.py`, 34 tests) 와 중복 회피 — 5.17 은 multi-frame scenario + UKF≡EKF 동치성. |
| 5.18 | `c9a68d2` | `tests/unit/domain/test_data_association_scenario.py` — close pair → assigned / far pair → gated / two-track-two-detection no-double-assignment + 가까운 짝 winner / two-track-one-detection closer winner / az ±pi wrap 경계 / Mahalanobis = 0 for perfect measurement / noise std + gating threshold rejection / DEFAULT_GATING_THRESHOLD_CHI2 ≈ 14.16. 12 tests. 기존 unit test 3 종 (empty/threshold) 과 중복 회피 — 5.18 은 multi-target Hungarian global optimum. |
| 5.19 + 5.20 | TBD | `tests/physics/test_multipath_horizon_golden.py` + `golden/multipath_horizon.json` — two-ray delta(0.250m) / phi(49.25) / F²·F⁴ (free 1.0 / PEC 0.943,0.889 / sea 0.898,0.807) rtol=1e-12 + lobing landmarks (last null 62710m, first peak 125420m = 2x) + 4/3 Re_eff(8494678) + horizon 10m geometric(11288) + radio two-point 10/50m(42180) + sum-of-singles invariant. 14 tests. 기존 multipath 15 + horizon 23 unit test 와 중복 회피 — 5.19~20 은 GoldenDataset reference layer. |
| 5.21 | TBD | `tests/physics/test_extended_target_glint_rms.py` — Skolnik rule σ_glint = L/(2√N) = 2.683m closed-form + 500-sample MC 5-pt aircraft cloud per-axis std < bound + |glint| < L=12m convex hull + L/R 대칭 body E-axis mean < 0.2σ + 같은 seed 동일 bit-for-bit + 다른 seed 다른 결과. 6 tests. 5.14 후속 (5.14 는 bound, 5.21 은 statistical). |
| 5.22 | TBD | `tests/unit/domain/test_tracker_maneuver_scenario.py` — 30 frame perfect-CV innovation < 1e-9 + 90도 velocity step 후 innov mean > 100x pre (maneuver detection signature) + EKF/UKF RMSE 비율 ∈ [0.95, 1.05] (linear F 지배) + sigma_a 1→10 m/s² 시 post-step RMSE 감소 + deterministic 재현. 5 tests. 5.17 후속 (5.17 은 CV, 5.22 는 maneuver). |

## 2. 검증 패턴 (5.2/5.3 confirmed)

각 카테고리:
1. `tests/physics/golden/<category>.json` — closed-form reference 값
   (Python 으로 한 번 계산해서 hardcode, plan/04 § 4.4 함정 #3 회피).
2. `tests/physics/test_<category>.py` — `_DATASET = GoldenDataset.load(...)`
   모듈 레벨, 각 함수가 case 별 검증.
3. tolerance 기본 rtol=1e-9 (closed-form), 1e-12 (bit-for-bit), 1e-7
   (numerical inverse 같은 곳).

함수 명명 규칙:
- `test_<함수>_matches_golden_<case>` — 직접 비교
- `test_<함수>_<scaling_or_invariant>` — 회귀 invariant
- N802 회피: 숫자 앞에 `_`/snake (`9_5_ghz` not `9_5GHz`).

## 3. Phase 5 마감 — 18 카테고리 모두 완료

plan/04 § 4.3 Phase 5 list **5.1~5.22 + 5.15/5.16** 전부 완료.

Physics (golden + invariant + RMS):
- 5.1 Golden infra, 5.2 FMCW, 5.3 Parabolic, 5.4 ISA atm+rain
- 5.5 Dynamics forces, 5.6 Monopulse, 5.7 Planar element_power
- 5.8 Ballistic analytic, 5.9 Single-scatterer RCS, 5.10 CFAR
- 5.14 ExtendedTarget multi-scatterer + glint (bound)
- 5.19 + 5.20 Multipath + horizon golden 회귀
- 5.21 ExtendedTarget σ_glint Monte Carlo (statistical)

App layer (timing):
- 5.11 PerformanceClock, 5.12 FrameBoundaryDetector, 5.13 FrameProfiler

Domain:
- 5.15 coherence_validator (src 신규 + verification)
- 5.16 simulation_domain.sample_terrain_safe (src 신규 + verification)
- 5.17 EKF + UKF CV scenario
- 5.22 EKF + UKF maneuver scenario
- 5.18 GNN data association

추가로 다음 phase 들 큰 단위 작업 가능:
- **Phase 6** NN 통합 — Pairing NN MVP, Step 1/2 wiring.
- **Phase 7** DLC 시스템 — `.trsim-pkg` + PackageManager.

## 4. 다음 세션 시작점

```
git pull
PYTHONPATH=$(pwd)/src .venv/Scripts/python.exe -m pytest tests/physics/ -q
# 1026 PASS 확인
```

권고 다음 진입점:
- **Phase 6 (NN 통합)** — Pairing NN MVP, Step 1 (Dataset Builder)
  + Step 2 (Eval) wiring. UI 는 4.11 끝, 도메인 + dataset 형식 +
  variant axis 6 plan/07.
- **5.15 + 5.16 도메인 코드 구현** — coherence_validator + simulation_
  domain 가 plan 만 있고 src 미존재. Phase 6+ 어디서 구현해도 OK.

Phase 5 후속 후보 (선택, 시간 여유 시):
- 5.17 후속: high-g maneuvering target 에서 UKF RMSE < EKF RMSE
  정량 회귀 — 시나리오 의존, RNG seed 고정 + truth turning rate.
- 5.14 후속: ExtendedTarget Skolnik σ_glint ≈ L/(2√N) RMS 회귀.
- 5.19/5.20: multipath/horizon golden JSON 재정렬 (기존 test 보강).

함수 시그니처 트랩 누적 (5.5/5.7/5.10 발견):
- `drag_force` 는 `velocity_mps` (not `velocity_enu_mps`).
- `BallisticDynamics.initial_velocity_mps` 는 `tuple[float, float, float]`.
- `monopulse_error_from_channels` 는 `complex` 채널 + keyword-only slopes.
- `element_power` positional/keyword 둘 다, kind `{"isotropic","cos"}`.
- `os_cfar_1d` 는 `k_index` (not `k`).
- `FrameProfiler.record_sample(stage_name, elapsed_ns)` — elapsed_ns
  는 정수 ns. negative reject.
- `zip(strict=True)` 대신 `itertools.pairwise` (RUF007 ruff rule).

함수 시그니처 트랩 (5.5 발견):
- `drag_force` 는 `velocity_mps` 키워드 (not `velocity_enu_mps`).
- `BallisticDynamics.initial_velocity_mps` 는 `tuple[float, float, float]`.
- `monopulse_error_from_channels` 는 `complex` 채널 + keyword-only
  slopes.

가장 무거운 카테고리 (후순위):
- 13 EKF vs UKF — full RMSE 시나리오 필요
- 14 GNN association — 다중 표적 시나리오 필요
- 16/17 Reference Timing / Profiler 재현성 — 같은 시드 + 같은 frame 정의 → 같은 결과 검증, 부하 의존

## 5. Phase 6 / 7 후속

- **Phase 6** NN 통합 — Pairing NN MVP, Step 1/2 wiring (UI 는 Phase
  4.11 끝, 도메인 + dataset 형식 + variant axis 6).
- **Phase 7** DLC 시스템 — `.trsim-pkg` packaging, PackageManager,
  ResourceLibrary 3-source (User / Package / Built-in) 통합.

## 6. 한 세션 결과 종합 (2026-05-10~11) — Phase 5 마감

main 직접 push 누적:
- 4.2a~4.12 (12 sub-phase): UI 골격, +190 ui tests
- ci_log + handoff docs (5)
- 5.1~5.14: physics 검증 12 카테고리, +166 verification tests
- 5.17~5.18: tracker scenario (domain), +21 verification tests
- 5.19~5.22: multipath/horizon golden + glint RMS + maneuver
  scenario, +25 verification tests
- 5.15 + 5.16: coherence_validator + simulation_domain src 신규
  구현 + verification, +24 tests
- **Phase 5 전체 마감** (18 카테고리 done)

CI: 다수 success 회수, 마지막 몇 개 in_progress (다음 세션에서 회수).
누적 **1234 PASS** local. 5 contracts KEPT 매 commit.

## 7. 다음 세션 진입 권고 명령

```
git pull
PY=".venv/Scripts/python.exe"
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m pytest tests/physics/ -q
# 200 PASS (golden 9 + fmcw 8 + parabolic 11 + atm 13 + forces 6
#  + monopulse 9 + planar 22 + ballistic 12 + rcs 14 + cfar 16
#  + extended_target_glint 19 + extended_target_glint_rms 6
#  + multipath_horizon_golden 14 + 기존 47)
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m pytest tests/unit/app/timing/ -q
# 27 PASS
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m pytest tests/unit/domain/ -q
# tracker scenario 9 + data assoc 12 + maneuver scenario 5 + 기존
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m pytest -q
# 1234 PASS total
```

**Phase 6 (NN 통합)** 부터 진입.
