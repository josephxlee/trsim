# Phase 2.6 — physics/antenna.py (parabolic only, slice a)

## Status
- 날짜: 2026-05-08
- CI: push 후 확인
- Test 추가: 21 (누적 ~318)

## Added

`src/workbench/physics/antenna.py` (단일 파일, parabolic 만):
- `AntennaType` enum (PARABOLIC / PLANAR_ARRAY placeholder)
- `ParabolicAntenna` (frozen+slots) + properties (wavelength_m, beamwidth_3db_deg, peak_gain_dbi)
- `beam_pattern(theta, phi)` — sinc² 정규화 [0, 1]
- 모듈 함수 3 개 (`parabolic_beamwidth_3db_deg`, `parabolic_peak_gain_dbi`, `parabolic_beam_pattern`)
- 상수 3 개 (`C_LIGHT_M_S`, `_PARABOLIC_BEAMWIDTH_K = 70`, `_SINC_HALF_POWER_U = 1.391557377`)

`tests/unit/physics/test_antenna.py` — 21 tests.

`docs/matlab_validation/test_antenna.m` — Octave 짝꿍.

## 핵심 결정

- Phase 2.6 첫 slice 는 **Parabolic 만**. PlanarArray + Monopulse 는 **2.6b** 별도 sub-phase 로 분리 (plan/08 § 8.5a.3, 8.5a.4 미구현).
- Beam pattern 은 **회전 대칭 sinc²** — `alpha = hypot(theta, phi)` 사용. 정확히 `alpha = bw/2` 에서 0.5 가 되도록 `_SINC_HALF_POWER_U` 스케일링.
- 3-dB 빔폭 계수 `K = 70` (plan/08 § 8.5a.2 표준; Skolnik 70.5 와 약간 다름).
- 9.4 GHz / D=1m / eta=0.6 기준값 Python exact: λ=0.0318928147, bw=2.232497°, gain=37.6507 dBi.

## Octave / cross-validation

`test_antenna.m` 5 sample:
- lambda, bw_3db, peak gain, sinc²@u_half, boresight pattern.

## 다음 sub-phase

phase_2_progress.md 우선순위:
1. **2.4** Dynamics — 큰 모듈 (6 sub-modules: rigid_body / forces / solver_rk4 / ...)
   또는
2. **2.6b** PlanarArray + Monopulse 4ch (Phase 2.6 후속)
3. **2.8** Tracker — Phase 2 핵심 (EKF/UKF/GNN)
