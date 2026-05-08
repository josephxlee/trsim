# Phase 2.3d — domain/target.py

## Status
- 날짜: 2026-05-08
- CI: push 후 확인
- Test 추가: 17 (누적 ~275)

## Added

`src/workbench/domain/target.py` —
- `TargetWaypoint` (frozen+slots): t_s / east_m / north_m / altitude_m / heading_rad
- `TargetEntity` (frozen+slots): placement / target_id / trajectory / rcs_model / wave_response
- `_FORBIDDEN_TARGET_MOTION = frozenset({FIXED_GROUND})`
- `make_default_aircraft_target(...)` factory

`tests/unit/domain/test_target.py` — 17 tests.

## 핵심 결정

- `TargetEntity` 도 composition (PlacedEntity 상속 X) — building.py 와 동일 패턴
- `target_id: int` (>= 0) 와 `placement.entity_id: str` 둘 다 — Tracker 알고리즘용 정수 ID
- trajectory `t_s` strictly increasing 강제 (`__post_init__`)
- `rcs_model: str` 는 placeholder — Phase 2.7 ExtendedTarget 도입 시 별도 type 으로 교체
- `wave_response` 는 SURFACE_VESSEL/FLOATING_STATIC 외에서도 허용 (강제 X, Editor 유연성)
- `make_default_aircraft_target` heading: `atan2(v_east, v_north)` — radar AZ convention

## Octave / cross-validation

N/A — dataclass-only.

## 다음 sub-phase

phase_2_progress.md 우선순위 그대로:
1. **2.5** Atmosphere — ISA + rain attenuation. 독립 모듈. .m 짝꿍 부활.
2. 2.6 Antenna — parabolic + monopulse. 분석 공식 검증.
3. 2.4 Dynamics — 큰 모듈 (6 sub-modules).
