# Phase 2.5 — physics/atmosphere.py

## Status
- 날짜: 2026-05-08
- CI: push 후 확인
- Test 추가: 22 (누적 ~297)

## Added

`src/workbench/physics/atmosphere.py` (단일 파일 — 디렉토리 분할은 Phase 6+
필요 시):
- `AtmosphereState` (frozen+slots, validation `__post_init__`)
- `isa_temperature(h, atm)`, `isa_pressure(h, atm)`, `isa_density(h, atm)`
- `rain_attenuation_dbpkm(f_GHz, R_mmh)` (ITU-R P.838 단순화)
- `two_way_loss_db(R_m, atm, f_Hz)`
- ISA 상수 6 개 `Final[float]`

`tests/unit/physics/test_atmosphere.py` — 22 tests.

`docs/matlab_validation/test_atmosphere.m` — Octave 짝꿍, base math only.

## 핵심 결정

- **단일 파일** — plan 표 `physics/atmosphere/` (디렉토리) 였지만 코드 양이
  적어 단일 파일 `atmosphere.py` 로 단순화. 다음 phase 에서 ducting / wind
  추가 시 디렉토리로 split 가능.
- `AtmosphereState` 가 physics 측에 위치 — domain 자원이 아니라 physics
  계산 input. import-linter 단순.
- 트로포스피어 위 clamp (MVP). v0.32 stratosphere model 은 Phase 6+.
- ITU-R P.838 X-band 정밀 / 외 단순화. 9.4 GHz @ 10 mm/h = 0.457345 dB/km.
- Python 정확값을 expected — Phase 1 패턴. tolerance 1e-5 ~ 1e-3.

## Octave / cross-validation

`test_atmosphere.m` — 6 sample 검증:
- rho_0 = 1.225 kg/m^3
- T_1km = 281.65 K
- P_1km = 89874.7555 Pa
- rho_1km = 1.111625
- rain_L_xband (9.4 GHz, 10 mm/h) = 0.457345 dB/km
- two_way_100km = 91.468951 dB

PASS 시 마지막 줄 `PASS`.

## 다음 sub-phase

phase_2_progress.md 우선순위:
1. **2.6** Antenna — parabolic / monopulse / beam_pattern 분석 공식
2. 2.4 Dynamics — 큰 모듈 (6 sub-modules)
