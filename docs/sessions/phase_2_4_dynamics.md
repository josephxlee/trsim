# Phase 2.4 — physics/dynamics/ (6 sub-modules)

## Status

- 날짜: 2026-05-09
- CI: push 후 확인 (ci_status workflow)
- Test 추가: 180 (누적 478)

## Added (9 모듈)

`src/workbench/physics/dynamics/`:

| Sub | 모듈 | 핵심 |
|---|---|---|
| **2.4a** | `rigid_body.py` | `RigidBodyState` (frozen+slots, 6DOF) + `attitude_from_velocity` |
| **2.4b** | `forces.py` | gravity / drag / lift / `ThrustProfile`(constant+curve) / control PD |
| **2.4c** | `solver_rk4.py` | `rk4_step` + `integrate` (substep) — translational only, attitude는 post-step에서 `attitude_from_velocity` |
| **2.4d** | `reference.py` | `Waypoint` (physics-side, domain mirror) + `interpolate_reference` + `reference_velocity_enu` |
| **2.4d** | `aircraft.py` | `AircraftDynamics` + `forward_unit_vector` + `make_aircraft_force_fn` (gravity+drag+lift+thrust+control 합성) |
| **2.4e** | `ballistic.py` | `BallisticDynamics` + `make_ballistic_force_fn` (gravity+drag만) |
| **2.4e** | `powered_flight.py` | `PoweredFlightDynamics` + `make_powered_flight_force_fn` (옵셔널 trajectory tracking) |
| **2.4f** | `surface_vessel.py` | `SurfaceVesselDynamics` + `WaveCoupling` + `wave_oscillation` + `surface_vessel_pose` (kinematic, no RK4) |
| **2.4f** | `ground_vehicle.py` | `GroundVehicleDynamics` + `ground_vehicle_pose` (kinematic, DEM-driven z) |

`tests/unit/physics/`:

- `test_rigid_body.py` (24) / `test_forces.py` (39) / `test_solver_rk4.py` (17)
- `test_reference.py` (14) / `test_aircraft.py` (24)
- `test_ballistic.py` (13) / `test_powered_flight.py` (18)
- `test_surface_vessel.py` (20) / `test_ground_vehicle.py` (11)

`docs/matlab_validation/`:

- `test_rigid_body.m` / `test_forces.m` / `test_solver_rk4.m` / `test_reference.m` / `test_ballistic.m` / `test_surface_vessel.m`

## 핵심 결정

- **Layering 엄수** (plan/02 § 2.5) — physics → domain import 금지. `Waypoint` (physics) 가 domain `TargetWaypoint` 와 같은 shape이지만 별도 정의. `WaveCoupling` 도 domain `WaveResponseModel` 과 같은 factor 3개 mirror.
- **Heading convention 통일** — RigidBodyState.yaw_rad = CW from North = CurrentPose.heading_rad (project 표준). plan/14 의 yaw 공식 (`atan2(v[1], v[0])`)을 `atan2(velocity_east, velocity_north)` 로 적용.
- **RK4는 translational only** — Level 1 MVP. attitude는 post-step에 `attitude_from_velocity` (coordinated flight). 회전 적분은 Level 2.
- **AIRCRAFT/POWERED_FLIGHT** = force-based RK4. **SURFACE_VESSEL/GROUND_VEHICLE** = kinematic (plan/14 § 14.5.4/5 "단순 보간"). **BALLISTIC** = force-based but no thrust/lift/control.
- **Substep 표준** — `DEFAULT_SUBSTEP_COUNT = 10` (plan/14 § 14.6.2: main 0.05s / sub 0.005s).
- **`max_load_factor_g` 클램프** — control PD가 `m * g * max_load_factor_g` per axis로 saturate (aircraft 4g / missile 20g).
- **`ThrustProfile` MVP** — CONSTANT + CURVE (linear interp + endpoint clamp). STAGE는 MVP+α.
- **Level 1 단순화** — `lift_coef` 필드는 dataclass에 둠 (Level 2 대비) but Level 1에서는 lift_force가 mg + altitude PD만 사용 (AoA 무시).
- **Naming convention** — Newtons는 `_n` suffix (`thrust_n`, `max_accel_n`, `max_control_force_n`), 프로젝트 표준 `quantity_unit` snake_case 따름.

## 검증 (Octave 짝꿍 핵심 sample)

- `test_rigid_body.m`: attitude_from_velocity 6 케이스 (north/east/45deg/climb30deg/vertical/dive)
- `test_forces.m`: gravity 1000kg / drag at sea level + 1km / lift trim + below-ref + damped / thrust curve linear interp + clamp
- `test_solver_rk4.m`: free-fall closed-form / constant-force kinematic / substep 일치 / energy conservation
- `test_reference.m`: 2-waypoint mid + quarter / clamp below/above / multi-segment
- `test_ballistic.m`: 45° projectile R = v²/g + h_peak = v²sin²θ/(2g) + RK4 reproducing closed form
- `test_surface_vessel.m`: wave oscillation 0/peak / heave velocity 0/quarter / zero-amp guard

## 트랩 / 교정

- **N803/N806 lint** — 처음에 `vE/vN/vU` 변수명 사용 → ruff N806 fail. `v_east/v_north/v_up` snake_case로 수정.
- **frozen+slots 테스트** — `s.extra_attr = 1.0` 가 `TypeError: super(type, obj)...` 발생 (slots+frozen). `__dict__` 부재 직접 검사로 수정.
- **Layering 위반** — 처음 `reference.py`에 `from workbench.domain.target import TargetWaypoint` → import-linter contract 1 위반. 자체 `Waypoint` 정의로 회피.
- **Control clamp 테스트** — 작은 kp로는 clamp 발동 안함 (50000 N << 2.7M N clamp). kp_position=1e6로 강제 saturate.

## 다음 sub-phase

phase_2_progress.md 우선순위:

1. **2.6b** PlanarArray + Monopulse 4ch (plan/08 § 8.5a.3, 8.5a.4)
2. **2.7** Extended Target — Multi-scatterer + Glint (plan/14 § 14.10)
3. **2.8** Tracker — EKF/UKF/GNN (plan/03 § 3.2.1k)
4. **2.9** CFAR — CA/OS (plan/03 § 3.2.1j)
