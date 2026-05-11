# Phase 5 — 물리 검증 프레임워크 (kickoff)

**같은 세션 후반부 (2026-05-10) — 5.1~5.6 진행됨**.
**현재 commit**: `2b4110f` (Phase 5.6) → 5.7+ 가 다음 세션.
**누적 test**: Phase 4 끝 998 → Phase 5.6 끝 1054 (+56 신규 physics tests).

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

## 3. 남은 카테고리 (12+)

plan/04 § 4.3 Phase 5 list 에서 5.1~5.6 제외, **이번 세션에서 추가
완료**: 5.4 ISA atmosphere + rain, 5.5 dynamics forces, 5.6 monopulse
error. 남은:

4. `physics/planar_array.py` — array factor (unit test 있음, 골든 패턴 추가 권장)
8. `physics/dynamics/aircraft.py` — autopilot trajectory 추적 정확성 (Solver RK4 통과 필요)
9. `physics/dynamics/ballistic.py` — analytic 자유낙하 (analytic vs RK4)
10. `physics/reflection/extended_target.py` — multi-scatterer + glint
11. `physics/propagation/multipath.py` — Two-ray multipath lobing (이미 일부 unit test)
12. `physics/propagation/ray_tracing.py` horizon — refraction (4/3 earth radius)
13. `domain/tracker_ekf.py` vs UKF — 고기동 RMSE 비교 (가장 무거움)
14. `domain/data_associator.py` — GNN association 정확성
15. `domain/detector_cfar.py` — OS-CFAR vs CA-CFAR
16. `app/timing/performance_clock.py` — Reference Timing 재현성
17. `app/timing/frame_profiler.py` — percentile 재현성
18. `domain/coherence_validator.py` — 6종 검사 동작
19. `domain/simulation_domain.py` — sample_terrain_safe (Map 안/밖)

## 4. 다음 세션 시작점

```
git pull
PYTHONPATH=$(pwd)/src .venv/Scripts/python.exe -m pytest tests/physics/ -q
# 1026 PASS 확인
```

권고 다음 sub-step (가벼움):
- **5.7 planar_array array_factor** — module-level 함수 골든
- **5.8 ray_tracing horizon** — 4/3 earth radius refraction 표
- **5.9 ballistic analytic** — `z(t) = z0 - 0.5 g t^2` (RK4 짧은 시간 통합 후 analytic 과 비교, atol O(g·dt²·N))
- **5.10 extended target multi-scatterer** — apparent_position 가
  glint 한계 내에 있는지 (RNG seed 고정)

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

## 6. 한 세션 결과 종합 (2026-05-10)

총 **22 commits** main 직접 push:
- 4.2a~4.12 (12 sub-phase): UI 골격
- ci_log 갱신 + handoff docs
- 5.1, 5.2, 5.3, 5.4, 5.5, 5.6: 검증 프레임워크 6 카테고리

CI: 11 success 회수, 4.12+ in_progress (다음 세션에서 회수).
누적 1054 PASS local. 5 contracts KEPT.

## 7. 다음 세션 진입 권고 명령

```
git pull
PY=".venv/Scripts/python.exe"
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m pytest tests/physics/ -q
# 76 PASS (golden_dataset 9 + fmcw 8 + parabolic 11 + atm 13 + forces 6 + monopulse 9 + 기존 20)
PYTHONUTF8=1 PYTHONPATH="$(pwd)/src" "$PY" -m pytest -q
# 1054 PASS total
```

5.7 부터 빠르게 진입.
