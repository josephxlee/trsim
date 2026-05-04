# 14. Dynamics Model — 사실적 표적 운동

**최종 갱신**: 2026-04-28 (v0.34)

**관련 문서**: [12 placement_and_motion](12_placement_and_motion.md), [03 data_model](03_data_model.md), [09 radar_platforms](09_radar_platforms.md)

## 14.1 왜 이 문서가 있나

v0.21에서 도입한 `MotionKind`는 운동 종류를 분류했지만, **실제 운동 방정식**은 단순 trajectory
보간(또는 sea_surface heave)에 머물렀다. 이 단순 모델은 MVP까지는 동작하지만 다음 한계가 있다:

- **AIRBORNE**: trajectory CSV의 z를 그대로 따라가면 비행기가 비현실적으로 출렁임 (중력 무시)
- **BALLISTIC 표적 부재**: 자유 낙하·탄도체를 표현 불가
- **추적 알고리즘 검증의 신뢰도 저하**: 실제 표적이 사실적으로 거동하지 않으면 추적 메트릭이 실측과 차이 큼

본 워크벤치의 **궁극 가치**는 "실제 추적 시나리오를 사실적으로 시뮬해 알고리즘을 검증"하는 것이다.
표적 운동이 사실적이지 않으면 가치가 떨어진다.

v0.27에서 **물리 기반 동역학 모델**을 도입한다.

## 14.2 핵심 결정

### 14.2.1 자유도 — 타입별 다름 (Q-E2-A 결정)

| MotionKind | 자유도 | 이유 |
|---|---|---|
| FIXED_GROUND | 0 | 정지 |
| GROUND_VEHICLE | 3DOF (x, y, heading) | DEM이 z 강제, 자세는 도로 따름 |
| SURFACE_VESSEL | 3DOF + heave/roll/pitch (wave) | 부력=중력 자동, 자세는 wave 응답 |
| FLOATING_STATIC | 0 + heave/roll/pitch | xy 고정 |
| **AIRCRAFT** (신설) | **6DOF** (x, y, z, roll, pitch, yaw) | RCS 모사 정확성 위해 자세 필요 |
| **POWERED_FLIGHT** (신설) | **6DOF** | 미사일·드론, 자세 빠르게 변함 |
| **BALLISTIC** (신설) | **3DOF point-mass** | 자유낙하·탄도, 자세는 단순 (회전 무시 또는 단순 spin) |

### 14.2.2 MVP 구현 전략 — 레벨링 (Q-E2-B 결정)

처음부터 풀 6DOF는 부담. **레벨링**으로:

- **Level 1 (MVP)**: 모든 동적 motion_kind에 **3DOF point-mass + 외력 모델**
  - 외력: gravity, drag, lift, thrust, control
  - AIRCRAFT/POWERED_FLIGHT의 자세는 **velocity vector로부터 추정** (coordinated flight 가정)
- **Level 2 (MVP+α)**: 6DOF (자세 동역학 추가) — RCS 모사 정확도 ↑
- **Level 3 (Future)**: 측정 기반 thrust curve, ISA atmosphere, 풍 외란

### 14.2.3 트라젝토리 = Reference, 실제 = 동역학

**핵심 원칙**: trajectory CSV는 **목표(reference)**이고, 실제 위치는 동역학 적분으로 결정.

- 사용자가 비현실적 trajectory(예: 50m 갑자기 점프)를 줘도 동역학이 부드럽게 추적
- 동역학 한계 (max climb rate, max bank angle, max thrust) 자동 적용
- 결과: **사용자가 정밀 물리 신경 안 써도 사실적 운동**

예외: BALLISTIC은 trajectory CSV 무시, **초기 조건만** 사용 (이후 자유 비행).

## 14.3 6DOF Rigid Body 표현 (Level 2 표준)

### 14.3.1 상태 (State)

```python
@dataclass(frozen=True)
class RigidBodyState:
    """6DOF 강체 상태. MVP는 자세 단순화(velocity vector 기반)."""
    # 위치 (Map ENU)
    east_m: float
    north_m: float
    altitude_m: float

    # 속도 (Map ENU 좌표계)
    velocity_east_mps: float
    velocity_north_mps: float
    velocity_up_mps: float

    # 자세 (오일러각, body frame ↔ ENU)
    roll_rad: float
    pitch_rad: float
    yaw_rad: float

    # 각속도 (body frame)
    angular_velocity_body_rad_s: tuple[float, float, float]

    # 시뮬 시간
    sim_t_s: float
```

### 14.3.2 운동 방정식

```
Translational:
    m * a_world = F_gravity + F_drag + F_lift + F_thrust + F_control

Rotational (Level 2):
    I * ω̇ = M_aero + M_control - ω × (I·ω)
```

MVP (Level 1)는 회전 방정식 생략, 자세는 velocity vector로부터 추정:

```python
def attitude_from_velocity(state: RigidBodyState) -> tuple[float, float, float]:
    """coordinated flight 가정 — velocity vector가 곧 forward direction."""
    v = (state.velocity_east_mps, state.velocity_north_mps, state.velocity_up_mps)
    speed = norm(v)
    if speed < 0.01:
        return (0.0, 0.0, state.yaw_rad)  # 정지면 변화 없음
    yaw = atan2(v[1], v[0])
    pitch = asin(v[2] / speed)
    roll = 0.0  # MVP는 무회전 (Level 2에서 lateral acceleration 기반 계산)
    return (roll, pitch, yaw)
```

## 14.4 외력 모델 (Force Field)

### 14.4.1 중력 (Gravity)

```python
def gravity_force(mass_kg: float) -> tuple[float, float, float]:
    """Standard gravity, ENU frame (Up이 +z)."""
    g = 9.80665  # m/s²
    return (0.0, 0.0, -mass_kg * g)
```

MVP는 standard gravity (위도·고도 무관). MVP+α에서 위도·고도 함수.

### 14.4.2 항력 (Drag)

```python
def drag_force(velocity_mps: tuple[float, float, float],
               mass_kg: float, drag_coef: float, area_m2: float,
               altitude_m: float) -> tuple[float, float, float]:
    """공기 항력. F = -1/2 * ρ * v² * Cd * A * v̂"""
    speed = norm(velocity_mps)
    if speed < 0.01:
        return (0.0, 0.0, 0.0)
    rho = air_density(altitude_m)         # MVP: ISA atmosphere 또는 sea-level constant
    F_mag = 0.5 * rho * speed * speed * drag_coef * area_m2
    direction = tuple(-v / speed for v in velocity_mps)
    return tuple(F_mag * d for d in direction)


def air_density(altitude_m: float) -> float:
    """MVP: 단순 ISA 근사. MVP+α: 풀 ISA + 온도 변동."""
    if altitude_m < 11000:
        # Troposphere 근사
        return 1.225 * (1 - 2.25577e-5 * altitude_m) ** 4.2561
    else:
        return 0.36391  # 11km 근사값
```

### 14.4.3 양력 (Lift)

```python
def lift_force(velocity_mps, mass_kg, lift_coef, area_m2,
               altitude_m, target_altitude_m,
               attitude: tuple) -> tuple[float, float, float]:
    """양력. MVP: trim + reference 추적 컨트롤러로 단순화.

    Level 1 MVP: 비행기는 mg를 양력으로 받쳐주고, target_altitude로 부드럽게 수렴.
    Level 2: AoA·받음각 기반 정확한 양력.
    """
    g = 9.80665
    # 기본 양력 = mg (수평 비행 trim)
    F_lift_trim = mass_kg * g  # ENU의 +Up 방향

    # Reference 추적 컨트롤러 (PD)
    altitude_error = target_altitude_m - altitude_m
    velocity_up = velocity_mps[2]
    F_lift_control = lift_controller_kp * altitude_error - lift_controller_kd * velocity_up

    return (0.0, 0.0, F_lift_trim + F_lift_control)
```

이 단순화로 사용자가 trajectory 주면 비행기가 부드럽게 추적, 비현실 trajectory도 동역학 한계
내에서 처리.

### 14.4.4 추력 (Thrust)

```python
@dataclass(frozen=True)
class ThrustProfile:
    """시간 함수 또는 단계별 추력 프로파일."""
    type: str  # "constant" / "curve" / "stage"
    constant_thrust_N: float = 0.0  # type=constant
    curve: tuple[tuple[float, float], ...] = ()  # type=curve, [(t_s, thrust_N), ...]
    stages: tuple[ThrustStage, ...] = ()  # type=stage (다단 로켓 등)


def thrust_force(profile: ThrustProfile, sim_t_s: float,
                 forward_direction: tuple[float, float, float]) -> tuple[float, float, float]:
    F_mag = profile_value_at(profile, sim_t_s)
    return tuple(F_mag * d for d in forward_direction)
```

MVP는 `constant` + `curve` 두 타입. `stage` (다단 로켓)는 MVP+α.

### 14.4.5 제어 입력 (Control)

Reference 추적용 추가 가속도. AIRCRAFT/POWERED_FLIGHT는 trajectory를 reference로
PD 컨트롤러가 부드럽게 추적:

```python
def control_force(state: RigidBodyState, ref: TrajectoryReference,
                  params: ControlParams) -> tuple[float, float, float]:
    # x, y, z 각 축에 PD 컨트롤러
    F_x = params.kp * (ref.east_m - state.east_m) - params.kd * state.velocity_east_mps
    F_y = params.kp * (ref.north_m - state.north_m) - params.kd * state.velocity_north_mps
    F_z = ...  # 양력에 통합

    # 동역학 한계 적용 (max accel, max climb rate)
    F_x = clamp(F_x, -params.max_accel_N, params.max_accel_N)
    F_y = clamp(F_y, -params.max_accel_N, params.max_accel_N)

    return (F_x, F_y, 0.0)  # z는 lift_force가 처리
```

## 14.5 motion_kind별 모델 사양

### 14.5.1 AIRCRAFT (신설)

```python
@dataclass(frozen=True)
class AircraftDynamics:
    """일반 비행기. trajectory를 waypoint reference로 추적."""
    mass_kg: float
    drag_coef: float = 0.04
    reference_area_m2: float = 30.0  # 윙 면적 등
    lift_coef: float = 0.4

    # 컨트롤러 (PD)
    kp_position: float = 0.5
    kd_position: float = 0.3
    kp_altitude: float = 1.0
    kd_altitude: float = 0.5

    # 동역학 한계
    max_climb_rate_mps: float = 25.0
    max_bank_deg: float = 60.0
    max_load_factor_g: float = 4.0  # max maneuver g

    thrust_profile: ThrustProfile  # 보통 constant (auto-balance with drag)
```

trajectory 입력: waypoint (t, east, north, altitude). 동역학이 부드럽게 추적.

### 14.5.2 POWERED_FLIGHT (신설)

```python
@dataclass(frozen=True)
class PoweredFlightDynamics:
    """미사일·드론. 추력 명령 + trajectory waypoint 둘 다 가능."""
    mass_kg: float
    drag_coef: float = 0.3
    reference_area_m2: float = 0.1

    thrust_profile: ThrustProfile  # 시간 함수, 자유롭게

    # Lift는 일반적으로 0 또는 작음 (미사일은 양력보다 추력)
    lift_coef: float = 0.0

    max_load_factor_g: float = 20.0  # 기동 g 큼

    # Trajectory를 reference로 쓸지 또는 thrust curve만 쓸지
    use_trajectory_as_reference: bool = True
```

특징: AIRCRAFT보다 drag 큼, lift 작음, 추력 변화 큼, 기동 g 큼.

### 14.5.3 BALLISTIC (신설)

```python
@dataclass(frozen=True)
class BallisticDynamics:
    """자유 낙하·탄도. 초기 조건만, 이후 외력만으로 결정."""
    mass_kg: float
    drag_coef: float = 0.4  # 공기 저항 있음
    reference_area_m2: float = 0.05

    # Trajectory CSV 무시. 초기 조건이 전부.
    initial_velocity_mps: tuple[float, float, float] = (0.0, 0.0, 0.0)
    # 초기 위치는 PlacedEntity의 base_*로

    # 단순 spin (선택)
    spin_rate_rps: float = 0.0  # 자체 회전, RCS 영향
```

CSV 무시 — `trajectory` 필드 비어 있어도 됨. **초기 조건만으로 시뮬**.

### 14.5.4 SURFACE_VESSEL (기존, v0.21 그대로)

이미 잘 정의됨. 14에서 추가 변경 없음:
- xy: trajectory waypoint (사용자 입력)
- z: sea_surface + wave heave (자동)
- 자세: wave roll/pitch + heading (자동)

MVP+α에서 가속·감속 동역학 (현재는 단순 보간)을 추가할 수 있음.

### 14.5.5 GROUND_VEHICLE (MVP 후, v0.21 그대로)

MVP에서 미구현. v0.21의 단순 모델 유지.

### 14.5.6 FIXED_GROUND, FLOATING_STATIC (정적, 변경 없음)

## 14.6 적분 (Integration)

### 14.6.1 RK4 (4차 Runge-Kutta) 권장

수치 안정성과 정확도 균형:

```python
def rk4_step(state: RigidBodyState, force_fn, dt: float) -> RigidBodyState:
    k1 = force_fn(state)
    k2 = force_fn(advance(state, k1, dt/2))
    k3 = force_fn(advance(state, k2, dt/2))
    k4 = force_fn(advance(state, k3, dt))

    delta = (k1 + 2*k2 + 2*k3 + k4) * (dt / 6)
    return apply_delta(state, delta)
```

### 14.6.2 Time Step 권장

- 시뮬 메인 step: 0.05 s (20 Hz, frame_rate와 일치)
- 동역학 step: 0.005 s (적분 안정성)
- 즉 **메인 1 step에 동역학 10 sub-step**

너무 빠른 표적 (예: 미사일)은 sub-step 더 작게 (자동 조정 MVP+α).

### 14.6.3 Sim Pause / Stop과의 일관성

- Sim PAUSED → 동역학 적분 정지, 마지막 상태 유지
- Sim STOPPED → 모든 표적이 base 상태로 복귀 (PlacedEntity의 base_*)

## 14.7 Trajectory Reference

### 14.7.1 Reference의 의미

```python
@dataclass(frozen=True)
class TrajectoryReference:
    """동역학 모델이 추적하는 목표. trajectory CSV에서 보간."""
    east_m: float
    north_m: float
    altitude_m: float
    heading_deg: float
    sim_t_s: float


def interpolate_reference(trajectory: tuple[TargetWaypoint, ...],
                          sim_t_s: float) -> TrajectoryReference:
    # 시간 기준 선형 보간
    ...
```

### 14.7.2 Reference 사용 여부

| MotionKind | trajectory 사용 |
|---|---|
| AIRCRAFT | reference로 (PD 추적) |
| POWERED_FLIGHT | reference로 또는 thrust curve만 (옵션) |
| BALLISTIC | **무시** (초기 조건만) |
| SURFACE_VESSEL | reference로 (xy만) |
| GROUND_VEHICLE | reference로 (xy만, MVP 후) |

### 14.7.3 Trajectory CSV의 z 의미 — 최종 확정

| MotionKind | z 컬럼 의미 |
|---|---|
| AIRCRAFT | **목표 고도 (절대값)** — 동역학이 부드럽게 추적, max_climb_rate 적용 |
| POWERED_FLIGHT | **목표 고도** (use_trajectory_as_reference=true일 때) |
| BALLISTIC | **무시** (초기 조건은 별도) |
| SURFACE_VESSEL | **무시** (sea_surface + wave 강제) |
| FLOATING_STATIC | **무시** |
| GROUND_VEHICLE | **무시** (DEM 강제) |
| FIXED_GROUND | 절대값 (anchor 시스템과 협업) |

이 표가 사용자에게 가장 자주 헷갈리는 부분 → Targets Editor UI에서 motion_kind 선택 시
"이 motion_kind는 z 컬럼이 어떻게 해석됩니다" 라벨 표시 (13 § 13.6 갱신).

## 14.8 표적 Preset 라이브러리

자주 쓰는 표적의 동역학 파라미터 묶음:

| Preset | MotionKind | 특징 |
|---|---|---|
| `aircraft_fighter_jet` | AIRCRAFT | F-16급, mass=10000kg, max climb 250m/s, max g 9 |
| `aircraft_airliner` | AIRCRAFT | A320급, mass=70000kg, max climb 15m/s, max g 2.5 |
| `missile_cruise` | POWERED_FLIGHT | mass=1000kg, drag 0.3, thrust=20kN, max g 10 |
| `missile_ballistic` | BALLISTIC | mass=500kg, 초기 속도 1500m/s |
| `drone_quadcopter` | POWERED_FLIGHT | mass=5kg, 호버 가능, max climb 5m/s |
| `artillery_shell` | BALLISTIC | mass=40kg, 초기 속도 800m/s |
| `large_ship` | SURFACE_VESSEL | (v0.21 기존) |
| `small_boat` | SURFACE_VESSEL | (v0.21 기존) |
| `fixed_tower` | FIXED_GROUND | (v0.21 기존) |

사용자는 Targets Editor에서 preset 복제 후 수정.

## 14.9 검증·디버깅 도구

### 14.9.1 Energy 보존 점검 (BALLISTIC)

BALLISTIC 표적은 보존력만 작용 (drag 제외) → 운동 에너지 + 위치 에너지 시간 함수
검증 가능. 디버그 모드에서 표시:

```
Energy at t=10s:
  Kinetic: 12,450 kJ
  Potential: 8,720 kJ
  Total: 21,170 kJ (drag 손실 1,830 kJ — 적분 오차 < 0.1%)
```

### 14.9.2 Reference 추적 오차 (AIRCRAFT/POWERED_FLIGHT)

```
Tracking error at t=10s:
  Position: 12.3 m (target_pos vs current_pos)
  Altitude: 5.1 m
  ΔV: 8.4 m/s (max climb rate 적용 결과)
```

이 정보는 Stage I/O Panel에 새 stage로 추가 가능 (06 Probe 시스템 활용).

### 14.9.3 동역학 한계 도달 알림

```
⚠ Aircraft #1 hit max climb rate (25 m/s) at t=15s
ℹ Reference altitude was 1500m, achieved 1430m (delayed by ~3s)
```

추적 알고리즘 검증 시 이게 중요 — 표적이 실제로 어떻게 거동했는지 명확.

## 14.10 표적 모델 정밀도 — Multi-scatterer + Glint (v0.34 MVP)

### 14.10.1 왜 점 표적이 부족한가

v0.27까지 표적은 동역학적으로는 정밀(6DOF, 외력 등) 했지만 **레이더 신호 측면에서는 단일 점**이었다. 실제 추적 레이더의 핵심 어려움은:

- 항공기·함정 같은 **extended target은 여러 reflector**의 합성으로 받음 신호 형성
- 표적 회전·이동 시 reflector 간 **phase 합성이 변하면서 도래각이 흔들림** — 이게 **glint** (각도 noise, 영문 "angle noise" 또는 "scintillation noise")
- Glint 크기는 표적 크기·거리·주파수·자세에 의존, mm~m 수준
- Monopulse error는 이 흔들림을 **실제 표적 이동으로 오인** → 추적 안정성 저하

우리 차별점 ("단일 표적 추적 안정성 검증") 의 핵심 변수가 **glint** 인데, 점 표적이면 자동으로 사라진다. 따라서 v0.34에서 **multi-scatterer 표적**을 MVP로 도입.

### 14.10.2 Multi-scatterer 표적 모델

```python
@dataclass(frozen=True)
class Scatterer:
    """표적의 한 reflector. v0.34 MVP."""
    offset_body_m: vec3        # 표적 body frame에서 위치 (x_forward, y_right, z_down)
    rcs_dbsm: float            # 이 scatterer의 RCS (dBsm)
    label: str = ""            # "nose" / "wing_tip_left" / "tail" 등 (디버그용)


@dataclass(frozen=True)
class ExtendedTarget:
    """Multi-scatterer 표적 모델 (v0.34 MVP).

    각 scatterer는 표적 body frame에서 위치·RCS를 가짐.
    표적의 attitude (yaw/pitch/roll)에 따라 reflector 위치 회전.
    Glint는 scatterer 간 phase 합성으로 자동 발생.
    """
    target_id: str
    scatterers: tuple[Scatterer, ...]      # MVP: 3~5개

    @property
    def total_rcs_dbsm(self) -> float:
        """모든 scatterer의 합산 RCS (incoherent average)."""
        rcs_linear = sum(10 ** (s.rcs_dbsm / 10) for s in self.scatterers)
        return 10 * np.log10(rcs_linear)
```

### 14.10.3 표적 Preset 라이브러리 갱신 (v0.27 9종 + scatterer)

| Preset | scatterers 수 | 위치 (대략) |
|---|---|---|
| `fighter_jet` | 5 | cockpit, nose, 양 wing tip, tail |
| `airliner` | 5 | cockpit, nose, 양 wing tip, tail |
| `missile_cruise` | 3 | nose, body mid, tail fin |
| `missile_ballistic` | 3 | nose, body, base |
| `drone` | 3 | body + 양 rotor (rotor는 mini scatterer) |
| `artillery_shell` | 1 | 단일 scatterer (작아서 점에 가까움) |
| `large_ship` | 5 | bow, midships, stern, mast, superstructure |
| `small_boat` | 3 | bow, mid, stern |
| `building` | 1 | 단일 scatterer (건물은 점) |

각 Preset의 scatterer offset·RCS는 `resources/targets/<preset>/scatterers.toml`에 기본값 제공. 사용자가 편집 가능 (Targets Editor).

### 14.10.4 받음 신호 합성 (Glint 자동 발생)

```python
def compute_extended_target_return(
    radar_pos_m: vec3,
    target: ExtendedTarget,
    target_state: RigidBodyState,    # v0.27, attitude 포함
    frequency_hz: float,
) -> ScatteringResult:
    """모든 scatterer의 복소 합성. Glint는 이 합성으로 자동 발생.

    Returns: 총 받음 신호 + apparent center (glint shift).
    """
    R_body_to_world = state_to_rotation_matrix(target_state)

    coherent_sum = 0j
    weighted_position = np.zeros(3)
    total_amplitude = 0.0

    for s in target.scatterers:
        # body → world
        offset_world = R_body_to_world @ s.offset_body_m
        scatterer_pos = target_state.position_m + offset_world

        R = norm(scatterer_pos - radar_pos_m)
        wavelength = 3e8 / frequency_hz

        # round-trip phase
        phase = 2 * (2 * np.pi * R / wavelength)
        amplitude = np.sqrt(10 ** (s.rcs_dbsm / 10)) / R**2

        # Coherent contribution
        contribution = amplitude * np.exp(-1j * phase)
        coherent_sum += contribution

        # Apparent center (amplitude-weighted)
        weighted_position += np.abs(contribution) * scatterer_pos
        total_amplitude += np.abs(contribution)

    apparent_center = weighted_position / total_amplitude if total_amplitude > 0 else target_state.position_m

    return ScatteringResult(
        total_signal=coherent_sum,
        apparent_position_m=apparent_center,
        glint_offset_m=apparent_center - target_state.position_m,  # 측정용
    )
```

### 14.10.5 Glint의 Monopulse 영향

Monopulse (v0.25) 의 angle error는 Σ·Δ 채널의 비율에서 옴. extended target의 경우:

- Σ 채널: 모든 scatterer 합성
- Δ 채널: scatterer마다 빔 중심 대비 offset에 따라 다른 weight
- 합성 결과의 **angle error는 표적 중심이 아닌 apparent_center를 가리킴**
- apparent_center는 표적 attitude·거리에 따라 흔들림 → **glint**

Monopulse 모델 (`domain/monopulse.py`) 갱신 필요:

```python
def compute_monopulse_error_extended(
    target: ExtendedTarget,
    target_state: RigidBodyState,
    radar_pos_m: vec3,
    monopulse_config: MonopulseRXConfig,
    frequency_hz: float,
) -> tuple[float, float]:
    """Extended target에 대한 monopulse error.

    각 scatterer마다 Σ·Δ 응답 계산하고 합성. Glint 자동 발생.
    Returns: (error_az_rad, error_el_rad).
    """
    sigma_total = 0j
    delta_az_total = 0j
    delta_el_total = 0j

    for s in target.scatterers:
        # ... 각 scatterer의 azimuth/elevation 계산
        # ... beam pattern으로 Σ·Δ 가중치
        # ... 합성

    error_az = (delta_az_total / sigma_total).real / monopulse_slope_az
    error_el = (delta_el_total / sigma_total).real / monopulse_slope_el
    return error_az, error_el
```

### 14.10.6 Glint 강도 — 표적 크기·거리·자세 의존

이론적 glint RMS 크기 (rule of thumb):

```
σ_glint ≈ L_target / (2·sqrt(N_scatterers))
```

- L_target: 표적의 typical 길이 (m)
- N_scatterers: 효과적 reflector 수

**예시**:
- 항공기 (L=15m, N=5): σ_glint ≈ 3.4m
- 함정 (L=100m, N=5): σ_glint ≈ 22m
- 미사일 (L=5m, N=3): σ_glint ≈ 1.4m

거리에 따른 angle glint:
```
σ_angle ≈ σ_glint / R   (rad)
```

5km 거리에서 항공기 angle glint: 3.4m / 5000m ≈ 0.7 mrad — **monopulse 정밀도(보통 0.1~1 mrad) 와 같은 크기**라 추적 안정성 직접 영향.

### 14.10.7 MVP 사양 vs MVP+α

✅ **MVP** (v0.34):
- Multi-scatterer 모델 (각 scatterer 독립 RCS)
- Body frame offset + 표적 attitude 회전
- Coherent sum → glint 자동 발생
- Monopulse 모델 확장
- Preset 9종에 scatterer 분포 기본값

❌ **MVP+α**:
- **Aspect-dependent RCS pattern** (각 scatterer가 자세별 RCS 다름)
- **Frequency-dependent RCS**
- **Polarimetric scattering matrix** (각 scatterer가 V/H 응답 다름)
- **Micro-Doppler** (회전 부품 — 프로펠러·로터가 rotation 따라 phase modulation)
- **Range glint** (range jitter from extended target)
- 더 많은 scatterer (10+개, 정밀 CAD 기반)
- Stochastic Swerling fluctuation 위에 결합

### 14.10.8 검증 — Glint 자동 발생 시각화

`physics_validation_panel.py` (Phase 5) 에 Glint 검증 카테고리 추가:

```
Test: glint_emerges_from_extended_target
─ Given: 5-scatterer fighter_jet (L=15m), R=5km, 정지 자세
─ When: monopulse error 계산
─ Then: σ_angle ≈ 0.7 mrad (이론치 매칭)
─ Visualize: monopulse error 시계열 — 점 표적은 0, multi-scatterer는 흔들림
```

이 검증으로 우리 차별점 ("단일 표적 추적 안정성")의 **시뮬 기반이 견고함을 증명**.

## 14.11 미래 확장 (MVP+α)

- **Level 2 6DOF**: 자세 동역학, AoA·sideslip, lateral 양력
- **Level 3**: 풍·외란, 측정 기반 thrust curve, Mach number 효과
- **Level 4**: ISA atmosphere 풀 모델, 중력 anomaly, 코리올리
- **다단 로켓**: ThrustProfile.stages 활성
- **Aerodynamic database**: CFD 결과 import (격자형 lift/drag 표)
- **Closed-loop guidance**: 표적이 능동적으로 회피 기동 (NN-driven AI)
- **Multi-body**: 표적 분리 (탄두-부스터)

## 14.12 Open Questions

- 풀 6DOF 도입 시점 (MVP+α의 어느 Wave?)
- ISA atmosphere 정밀도 (sea-level constant vs full ISA vs measured)
- Sub-step 자동 조정 (빠른 표적 처리)
- BALLISTIC의 자체 회전(spin) 모델 — RCS 영향
- POWERED_FLIGHT에서 thrust curve와 trajectory 둘 다 줄 때 우선순위
- 6DOF 도입 시 Aircraft Coordinated Flight 가정 강화 vs 풀 lateral 동역학
- 동역학 적분 라이브러리 — scipy.integrate 또는 자체 RK4

## 섹션 상태

- 14.1~14.2 개요·핵심 결정 — ✅
- 14.3 6DOF 표현 — ✅ (MVP는 단순화)
- 14.4 외력 모델 — ✅ (gravity/drag/lift/thrust/control)
- 14.5 motion_kind별 사양 — ✅ (AIRCRAFT, POWERED_FLIGHT, BALLISTIC 신설)
- 14.6 적분 — ✅ (RK4, sub-step)
- 14.7 Trajectory Reference — ✅ (z 의미 최종 확정)
- 14.8 Preset 라이브러리 — ✅
- 14.9 검증·디버깅 — ✅
- 14.10 Multi-scatterer + Glint — ✅ (v0.34 신설)
- 14.11 미래 확장 — 🟡
- 14.12 Open Questions — 🟡

---

👉 이전: [13_editor_workspace.md](13_editor_workspace.md)
