# 12. Placement & Motion — 정적 배치와 동적 운동의 분리

**최종 갱신**: 2026-04-28 (v0.35)

**관련 문서**: [11 coordinate_systems](11_coordinate_systems.md), [09 radar_platforms](09_radar_platforms.md), [10 workspaces](10_workspaces.md), [03 data_model](03_data_model.md)

## 12.1 핵심 통찰

> ⚠️ **v0.34 정합**: 본 문서는 표적의 **위치(placement)·운동(motion)** 이 주제.
> v0.34에서 도입한 **ExtendedTarget** (multi-scatterer + glint, 14 § 14.10, 03 § 3.2.1k)는
> 표적의 **레이더 신호 모델** — placement·motion 과 별개 차원. 통합 관계:
>
> - `TargetEntity` (PlacedEntity 상속, 위치·motion_kind) ← 본 문서
> - `RigidBodyState` (동역학 상태, 14 § 14.3) ← 14
> - `ExtendedTarget` (scatterer 분포, 14 § 14.10) ← 14, body frame
> - 받음 신호 = `compute_extended_target_return(radar_pos, target=ExtendedTarget,
>   target_state=RigidBodyState, frequency)` — 세 데이터의 합성
>
> 즉 placement(어디 있는가) · dynamics(어떻게 움직이는가) · scattering(어떻게 반사하는가)
> 가 분리된 추상. 본 문서는 첫 두 가지에 집중, scattering은 14 § 14.10 권위.

자원의 위치는 **두 종류로 분리**되어야 한다:

- **정적 배치 (Editor)**: 사용자가 Editor에서 결정한 기준 위치
- **동적 운동 (Simulator)**: 시뮬 진행 중 매 틱 업데이트되는 실제 위치

이전 프로젝트에서 이 둘을 혼용한 결과, "Editor에서 봤을 때와 시뮬에서 본 위치가 다른 이유"를
이해하기 어려웠다. v0.21에서 명시적으로 분리한다.

## 12.2 PlacedEntity — 공통 위치 정보

Map에 배치되는 모든 자원은 `PlacedEntity` 형식의 정적 위치를 가진다:

```python
@dataclass(frozen=True)
class PlacedEntity:
    """모든 배치 자원의 공통 정적 위치."""
    east_m: float                    # ENU 동쪽 (Map 기준)
    north_m: float                   # ENU 북쪽
    base_altitude_m: float           # 정적 z (Editor에서 배치한 위치)

    # 운동 종류 — Sim 진행 중 어떻게 움직이는가
    motion_kind: MotionKind

    # 자세 (정적 기준)
    heading_deg: float = 0.0
    base_pitch_deg: float = 0.0
    base_roll_deg: float = 0.0

    # 운동 모델 파라미터 (motion_kind별)
    motion_params: dict = field(default_factory=dict)
```

## 12.3 MotionKind — 7 카테고리 (v0.27 확장)

```python
class MotionKind(Enum):
    # 정적
    FIXED_GROUND = "fixed_ground"           # 지상 고정

    # 동적
    GROUND_VEHICLE = "ground_vehicle"       # 지상 이동 (MVP 후)
    SURFACE_VESSEL = "surface_vessel"       # 해상 이동 (항해)
    FLOATING_STATIC = "floating_static"     # 해상 정박 (xy 고정 + 출렁)

    # 항공 — v0.27에서 AIRBORNE을 3종으로 분리 (사실적 동역학)
    AIRCRAFT = "aircraft"                   # 일반 비행기, trajectory waypoint를 reference로 추적
    POWERED_FLIGHT = "powered_flight"       # 미사일·드론, thrust+drag 기반
    BALLISTIC = "ballistic"                 # 자유 낙하·탄도, 초기 조건만 사용
```

> **v0.27 변경**: 이전 `AIRBORNE` 단일 카테고리는 폐기. 항공 표적은 운동 특성이 다양해 사실적
> 추적 검증을 위해 3종으로 세분화. 동역학 모델 상세는 [14_dynamics_model.md](14_dynamics_model.md).

### 12.3.1 카테고리별 z 처리

| MotionKind | x,y | z | 자세 | 비고 |
|---|---|---|---|---|
| FIXED_GROUND | 정적 | DEM 샘플링 또는 explicit | 정적 | 건물·고정 시설 |
| GROUND_VEHICLE | trajectory | DEM 샘플링 + 서스펜션 | 도로 기울기 + 진동 | MVP 후 |
| SURFACE_VESSEL | trajectory | sea_surface + wave heave | wave roll/pitch + heading | 항해 중 함정 |
| FLOATING_STATIC | 정적 | sea_surface + wave heave | wave roll/pitch | 정박 함정·부표 |
| AIRCRAFT | 동역학 (trajectory reference) | 동역학 (target alt 추적) | velocity vector 기반 | 일반 비행기 (v0.27) |
| POWERED_FLIGHT | 동역학 (thrust + reference) | 동역학 (thrust + drag) | velocity vector 기반 | 미사일·드론 (v0.27) |
| BALLISTIC | 동역학 (외력만) | 동역학 (gravity + drag) | spin 또는 무회전 | 자유낙하·탄도 (v0.27) |

> **v0.27 핵심 변경**: 항공·탄도 표적은 trajectory를 단순 보간하지 않고 [동역학 모델](14_dynamics_model.md)
> 로 적분. trajectory는 reference (목표), 실제 위치는 외력(중력·항력·양력·추력) 균형으로 결정.

### 12.3.2 v0.18 PlatformCategory와의 매핑

레이더 플랫폼의 카테고리(09 § 9.2)는 motion_kind 하위 집합과 자연스럽게 매핑:

| PlatformCategory | 가능한 motion_kind |
|---|---|
| MARITIME | SURFACE_VESSEL (운항 중) 또는 FLOATING_STATIC (정박) |
| FIXED_GROUND | FIXED_GROUND |
| (미래) GROUND_VEHICLE | GROUND_VEHICLE |
| (미래) AIRBORNE | AIRBORNE |

표적도 동일 카테고리 체계를 사용한다 — 레이더와 표적이 **같은 motion 추상화** 위에 놓인다.

## 12.4 정적 배치 (Editor) vs 동적 운동 (Simulator)

### 12.4.1 정적 상태 — `base_*` 필드

Editor에서 배치하면 `base_altitude_m`, `base_roll_deg`, `base_pitch_deg`가 결정된다.
이는 "운동 없는 기준 상태"의 위치·자세.

```python
@dataclass(frozen=True)
class PlacedEntity:
    base_altitude_m: float          # 정지 상태 z
    base_pitch_deg: float = 0.0     # 정지 상태 pitch (해상이면 0)
    base_roll_deg: float = 0.0      # 정지 상태 roll
    heading_deg: float = 0.0        # 정지 상태 heading (변하지 않으면 그대로)
```

### 12.4.2 동적 상태 — `current_*` (런타임만)

Sim Running 중 매 틱 업데이트되는 실제 상태:

```python
@dataclass(frozen=True)
class CurrentPose:
    """Sim Running 중 매 틱 계산되는 실제 위치/자세. 저장되지 않음 (Probe로만 기록)."""
    east_m: float
    north_m: float
    altitude_m: float

    roll_deg: float
    pitch_deg: float
    yaw_deg: float

    # 기준값 대비 변화량 (디버깅용)
    altitude_offset_m: float        # current - base
    roll_offset_deg: float
    pitch_offset_deg: float


def compute_current_pose(entity: PlacedEntity, sim_t_s: float,
                         env: EnvironmentState, map_: Map) -> CurrentPose:
    if entity.motion_kind == MotionKind.FIXED_GROUND:
        # 변화 없음
        return CurrentPose(
            east_m=entity.east_m, north_m=entity.north_m,
            altitude_m=entity.base_altitude_m,
            roll_deg=entity.base_roll_deg,
            pitch_deg=entity.base_pitch_deg,
            yaw_deg=entity.heading_deg,
            altitude_offset_m=0.0, roll_offset_deg=0.0, pitch_offset_deg=0.0,
        )

    if entity.motion_kind == MotionKind.FLOATING_STATIC:
        # xy 고정, wave 출렁
        wave = env.wave_response_for(entity, sim_t_s)
        return CurrentPose(
            east_m=entity.east_m, north_m=entity.north_m,
            altitude_m=entity.base_altitude_m + wave.heave_m,
            roll_deg=entity.base_roll_deg + wave.roll_deg,
            pitch_deg=entity.base_pitch_deg + wave.pitch_deg,
            yaw_deg=entity.heading_deg,
            altitude_offset_m=wave.heave_m,
            roll_offset_deg=wave.roll_deg, pitch_offset_deg=wave.pitch_deg,
        )

    if entity.motion_kind == MotionKind.SURFACE_VESSEL:
        # trajectory + wave
        traj_pos = entity.trajectory.interpolate(sim_t_s)
        wave = env.wave_response_for(entity, sim_t_s)
        return CurrentPose(
            east_m=traj_pos.east_m, north_m=traj_pos.north_m,
            altitude_m=map_.sea_surface.z_at_sea_m + wave.heave_m,
            roll_deg=wave.roll_deg, pitch_deg=wave.pitch_deg,
            yaw_deg=traj_pos.heading_deg,
            altitude_offset_m=wave.heave_m,
            roll_offset_deg=wave.roll_deg, pitch_offset_deg=wave.pitch_deg,
        )

    if entity.motion_kind in (MotionKind.AIRCRAFT, MotionKind.POWERED_FLIGHT):
        # v0.27: 동역학 모델 (14 참조)
        # trajectory를 reference로, 6DOF rigid body solver로 적분
        # MVP는 3DOF point-mass + velocity vector 기반 자세 추정
        rb_state = entity._dynamics_state  # RigidBodyState (지속 상태, 시뮬에서 관리)
        traj_ref = interpolate_reference(entity.trajectory, sim_t_s)
        rb_state = dynamics_step(rb_state, traj_ref, entity.motion_params,
                                 dt=sim_dt_s)  # RK4 + sub-step
        return CurrentPose(
            east_m=rb_state.east_m,
            north_m=rb_state.north_m,
            altitude_m=rb_state.altitude_m,
            roll_deg=degrees(rb_state.roll_rad),
            pitch_deg=degrees(rb_state.pitch_rad),
            yaw_deg=degrees(rb_state.yaw_rad),
            altitude_offset_m=rb_state.altitude_m - entity.base_altitude_m,
            roll_offset_deg=...,
            pitch_offset_deg=...,
        )

    if entity.motion_kind == MotionKind.BALLISTIC:
        # v0.27: trajectory CSV 무시, 초기 조건만 사용
        # gravity + drag만 작용, sim_t=0의 PlacedEntity.base_*에서 시작
        rb_state = entity._dynamics_state
        rb_state = ballistic_step(rb_state, entity.motion_params, dt=sim_dt_s)
        return CurrentPose(...)

    # GROUND_VEHICLE은 MVP 후
    raise NotImplementedError
```

### 12.4.3 Editor와 Simulator의 표시 차이

| 상태 | 표시되는 z | 표시되는 자세 |
|---|---|---|
| **Editor (항상)** | `base_altitude_m` | base 자세 |
| **Sim IDLE / PAUSED / ENDED** | `base_altitude_m` (모든 motion_kind) | base 자세 |
| **Sim RUNNING** | `current_altitude_m` (motion_kind 따라 계산) | current 자세 |

**즉**: Sim PAUSED 중에는 표적/레이더가 **현재 위치(직전 RUNNING 시점)에 정지**한다. 이건
v0.15 결정과 일관 (Sim PAUSED = 모든 물리 정지).

다만 명세상 **Sim PAUSED → 정지된 그 순간의 current_pose 유지**가 자연스러움:

```python
def pose_for_display(entity, sim_clock, sim_t_s, env, map_):
    if sim_clock.state == SimulationState.RUNNING:
        return compute_current_pose(entity, sim_t_s, env, map_)
    elif sim_clock.state == SimulationState.PAUSED:
        return entity._last_running_pose       # 정지 직전 pose
    else:  # STOPPED 또는 IDLE
        return base_pose(entity)               # base 위치
```

## 12.5 Wave 응답 — 환경(Map)과 응답(Entity) 분리

### 12.5.1 핵심 분리

파도는 **환경**(Map의 sea_state)이지만, 그에 대한 **응답**은 자원마다 다르다 (배 크기·형상).
둘을 명시적으로 분리:

```python
# 환경 (Map)
@dataclass(frozen=True)
class SeaStateEnvironment:
    """Map의 sea_state — 파도 자체 정의."""
    sea_state: int                  # Douglas 0~9
    dominant_period_s: float        # 주기
    significant_wave_height_m: float # 의미파고
    direction_deg: float            # 파도 진행 방향


# 응답 (Entity)
@dataclass(frozen=True)
class WaveResponseModel:
    """이 자원이 파도에 어떻게 반응하는가. motion_params로 지정."""
    name: str                       # "small_boat", "large_ship", "buoy", ...

    # 응답 함수 (간단한 sinusoidal 모델, MVP)
    heave_amplitude_m: float        # z 출렁 진폭
    roll_amplitude_deg: float
    pitch_amplitude_deg: float
    period_offset_s: float = 0.0    # 위상 차이


def wave_response_for(entity: PlacedEntity, sim_t_s: float,
                      env: SeaStateEnvironment) -> WaveDisplacement:
    response = entity.motion_params.get("wave_response", default_response_for(entity))
    omega = 2 * pi / env.dominant_period_s
    phase = omega * sim_t_s + response.period_offset_s

    return WaveDisplacement(
        heave_m=response.heave_amplitude_m * sin(phase),
        roll_deg=response.roll_amplitude_deg * sin(phase + pi/4),
        pitch_deg=response.pitch_amplitude_deg * sin(phase + pi/2),
    )
```

### 12.5.2 Preset 응답 모델 (MVP)

자주 쓸 만한 프리셋:

| Preset | heave | roll | pitch | 적용 |
|---|---|---|---|---|
| `large_ship` | sea_state × 0.4m | sea_state × 0.5° | sea_state × 0.3° | 함정·대형선 |
| `small_boat` | sea_state × 0.8m | sea_state × 1.5° | sea_state × 1.0° | 어선·소형선 |
| `buoy` | sea_state × 1.0m | 0° | 0° | 부표 |
| `none` | 0 | 0 | 0 | 응답 없음 (디버그용) |

사용자는 표적에 preset 지정 또는 직접 파라미터 입력.

### 12.5.3 Sim Pause 중 wave도 정지

Sim PAUSED → `sim_t_s`가 멈춤 → wave_displacement 입력값 멈춤 → 출렁임 멈춤.

Sim Stop → 모든 자원의 pose가 base로 복귀.

## 12.6 해수면 시각화 (MVP 포함)

### 12.6.1 정적 (Editor·IDLE) 표시

해수면은 **z = sea_surface.z_at_sea_m 평면**으로 그린다. Editor와 Sim IDLE에서는 정지.

### 12.6.2 동적 (Sim RUNNING) 표시

Sim RUNNING 중 해수면이 출렁이는 애니메이션:

- 해수면 메시를 격자로 분할 (예: 100×100 quads)
- 각 격자 점의 z를 `sea_surface.z_at_sea_m + sin/cos 함수`로 변동
- 파도 방향·주기는 `SeaStateEnvironment` 따라

```glsl
// 정점 셰이더 의사 코드
vec3 wave_displaced(vec3 pos, float t, SeaState s) {
    float k = 2.0 * PI / s.wavelength;
    float omega = 2.0 * PI / s.period;
    float phase = k * dot(pos.xy, s.direction) - omega * t;
    pos.z = s.z_at_sea + s.amplitude * sin(phase);
    return pos;
}
```

목적은 **시각적 이해 보조** — 메트릭 계산과 무관, 사용자가 "이 정도 파도구나" 직관 얻기.

### 12.6.3 옵션

- 토글로 끌 수 있음 (정적 평면이 더 깔끔할 때)
- 시각적 단순화 (실제 파동 방정식 아닌 sinusoidal)

## 12.7 표적 trajectory의 z 처리

### 12.7.1 trajectory CSV의 z 의미

Targets 자원의 trajectory 파일(CSV)에 `z` 또는 `altitude` 컬럼이 있으면 다음 규칙:

| motion_kind | z 컬럼의 해석 |
|---|---|
| FIXED_GROUND | z 그대로 (절대 고도) |
| GROUND_VEHICLE | 무시 (DEM 샘플링으로 결정) |
| SURFACE_VESSEL | **무시** (sea_surface + wave로 자동 결정) |
| FLOATING_STATIC | **무시** |
| AIRCRAFT | **목표 고도 (reference)** — 동역학이 max_climb_rate 내에서 추적 (v0.27) |
| POWERED_FLIGHT | **목표 고도** (use_trajectory_as_reference=true일 때, 14 § 14.5.2) |
| BALLISTIC | **무시** — trajectory 자체가 무시됨, initial_velocity_mps만 사용 (14 § 14.5.3) |

> **v0.27 핵심**: trajectory CSV는 더 이상 단순 보간 위치가 아니라 **동역학 모델의 reference 입력**.
> 실제 위치는 동역학 적분으로 결정. 상세는 [14_dynamics_model.md](14_dynamics_model.md).

해상 표적의 trajectory CSV에 z가 있어도 **무시**된다 — sea_surface가 권위자.

### 12.7.2 Trajectory 데이터 형식

```csv
target_id,t_s,east_m,north_m,altitude_m,heading_deg
1,0.0,12000,5000,0,90
1,1.0,12010,5000,0,90
...
```

- `altitude_m`은 motion_kind에 따라 위 규칙 적용
- `heading_deg`은 모든 motion_kind에서 사용

### 12.7.3 MVP에서 표적 궤적 편집은 미포함

Trajectory 편집 GUI는 MVP 범위 밖. MVP에서는:

- **Targets는 자원 라이브러리에 import만** (CSV/TOML)
- Editor에서 메타 표시·편집만 (motion_kind, RCS 모델 등)
- Map 위 trajectory 시각화 (읽기 전용)
- 궤적 편집은 외부 도구 (Excel·Python·MATLAB) 또는 MVP 후

## 12.8 건물 anchor 시스템

### 12.8.1 anchor_mode

건물(과 일반 FIXED_GROUND 자원)이 어떻게 지면에 부착되는지:

```python
class AnchorMode(Enum):
    BASE_TO_TERRAIN = "base_to_terrain"     # DEM 샘플링 자동 (기본)
    EXPLICIT_ALT = "explicit_alt"           # 사용자가 z 직접 지정
    FLOOR_AT_MSL = "floor_at_msl"           # 1층 = 해수면 (항만 시설)
    TERRAIN_OFFSET = "terrain_offset"       # DEM + offset (다리·고가도로)


@dataclass(frozen=True)
class FixedGroundEntity(PlacedEntity):
    anchor_mode: AnchorMode = AnchorMode.BASE_TO_TERRAIN

    # mode별 추가 파라미터
    explicit_alt_m: float | None = None     # EXPLICIT_ALT일 때
    terrain_offset_m: float | None = None   # TERRAIN_OFFSET일 때

    # 메시 원점 정보
    mesh_origin: MeshOrigin = MeshOrigin.BASE_CENTER

    mesh_path: Path | None = None
```

### 12.8.2 mesh_origin

3D 메시 파일 안에서 (0,0,0)이 어디인가:

```python
class MeshOrigin(Enum):
    BASE_CENTER = "base_center"     # 메시 바닥 중심 (가장 흔함)
    BASE_CORNER = "base_corner"     # 메시 바닥 모서리
    VOLUME_CENTER = "volume_center" # 메시 중심 (드물게)
```

### 12.8.3 anchor 적용 결과

```python
def resolve_base_altitude(entity: FixedGroundEntity, map_: Map) -> float:
    """anchor_mode에 따라 base_altitude_m 결정."""
    if entity.anchor_mode == AnchorMode.BASE_TO_TERRAIN:
        return map_.dem.sample(entity.east_m, entity.north_m)  # DEM 자동 (bilinear)

    if entity.anchor_mode == AnchorMode.EXPLICIT_ALT:
        return entity.explicit_alt_m

    if entity.anchor_mode == AnchorMode.FLOOR_AT_MSL:
        return map_.sea_surface.z_at_sea_m

    if entity.anchor_mode == AnchorMode.TERRAIN_OFFSET:
        terrain = map_.dem.sample(entity.east_m, entity.north_m)
        return terrain + entity.terrain_offset_m

    raise NotImplementedError
```

### 12.8.4 mesh_origin 보정

렌더링 시 메시 원점에 따라 추가 보정:

```python
def render_position(entity: FixedGroundEntity, map_: Map) -> vec3:
    base_z = resolve_base_altitude(entity, map_)

    if entity.mesh_origin == MeshOrigin.BASE_CENTER:
        return vec3(entity.east_m, entity.north_m, base_z)
    elif entity.mesh_origin == MeshOrigin.BASE_CORNER:
        # 메시 bbox로 보정 (바닥 모서리를 base_z에 맞추되 시각적 중심은 ...)
        ...
    elif entity.mesh_origin == MeshOrigin.VOLUME_CENTER:
        bbox_height = entity.mesh.bbox.height
        return vec3(entity.east_m, entity.north_m, base_z + bbox_height/2)
```

### 12.8.5 결론: 건물이 더는 안 뜬다

`anchor_mode = BASE_TO_TERRAIN` (기본) + `mesh_origin = BASE_CENTER` (메시 표준)이면:

```
건물 base_altitude_m = DEM.sample(east, north) [bilinear]
렌더링 위치 = (east, north, base_altitude_m) [메시 원점 = 바닥 중심]
```

→ DEM과 정확히 정합. 픽셀 경계 부드러움. 사용자가 z 입력 안 해도 됨.

### 12.8.6 land_mask 검사 (v0.22)

자체 규격 지형(11 § 11.10)의 `land_mask`를 활용해 **해상에 건물 배치 방지**:

```python
def place_building(b: FixedGroundEntity, map_: Map) -> ValidationResult:
    if b.anchor_mode in (AnchorMode.BASE_TO_TERRAIN, AnchorMode.TERRAIN_OFFSET):
        # 육상 위에만 배치 가능 (해상은 의미 없음)
        is_land = map_.terrain.is_land_at(b.east_m, b.north_m)
        if not is_land:
            return ValidationError(
                f"건물 '{b.name}'이 해상 영역에 배치됨. "
                f"FLOOR_AT_MSL 또는 EXPLICIT_ALT 사용 권장 (항만 시설 등)"
            )

    elif b.anchor_mode == AnchorMode.FLOOR_AT_MSL:
        # 항만 시설 — 해안선 근처(육상·해상 경계)이면 자연스럽
        # 100% 육상이거나 100% 해상이면 경고
        if map_.terrain.is_far_from_coast(b.east_m, b.north_m, threshold_m=100):
            return ValidationWarning(
                f"건물 '{b.name}'이 해안선에서 멀음. FLOOR_AT_MSL 의도 확인 필요"
            )

    elif b.anchor_mode == AnchorMode.EXPLICIT_ALT:
        # 명시적 z — 검증은 하되 차단하지 않음 (사용자 책임)
        pass

    return ValidationOk()
```

이 검증은 § 11.7 Coherence Validator의 한 항목으로 통합된다.

## 12.9 Sim Pause 정지 명세 (재정리)

v0.15에서 잡은 두 레이어 시간 제어와 결합해 명세:

| 상태 | sim_t_s 진행 | wave 출렁 | 표적 trajectory | 건물 |
|---|---|---|---|---|
| Sim STOPPED | 0으로 리셋 | 정지 (base) | 시작 위치 (base) | base |
| Sim PAUSED | 정지 | 직전 위치 유지 | 직전 위치 유지 | base (변화 없음) |
| Sim RUNNING + Target IDLE | 진행 | 출렁임 | 시작 위치 (base) | base |
| Sim RUNNING + Target RUNNING | 진행 | 출렁임 | trajectory 진행 | base |

해수면 시각화도 동일 — Sim RUNNING일 때만 출렁이는 애니메이션.

## 12.10 자원 종속성 정리

자원이 다른 자원에 어떻게 의존하는지 명시:

| 자원 | 종속 | 이유 |
|---|---|---|
| Map | 없음 | 독립 (Origin·DEM·해안선·건물 포함) |
| Building | Map | 건물은 Map 안에 위치, anchor 모드로 부착 |
| Radar (Platform) | Map | 설치 위치는 Map 좌표 |
| Targets | 약한 종속 | Map 좌표로 표현되지만 다른 Map에서도 자동 변환 시도 가능 (10 § 10.10) |

**Building이 Map 안에 포함되는 이유**: Map 없이 건물만 있는 건 의미 없음. 같은 Map의 다양한 건물 배치는 **Map 내부에서 관리**, 다른 Map의 건물 셋을 같이 쓰는 건 지원 안 함.

**Targets가 Map 독립인 이유**: 같은 trajectory를 다른 지역(Map)에서 재생할 수 있어야 함 (어제 Q3 결정).

## 12.11 지형 편집 도구 (Editor Workspace, v0.22)

자체 규격 지형(11 § 11.10)은 **사용자 편집 가능**. Editor Workspace의 Map Editor 안에서.

### 12.11.1 MVP 도구 (경량)

MVP에서는 **세 가지 핵심 도구**:

#### Land/Sea Mask Brush

`land_mask` 픽셀을 직접 페인트로 수정:

```
도구 사용:
  - 좌클릭 드래그: 육상으로 칠하기
  - Shift + 드래그: 해상으로 칠하기
  - 브러시 크기: 1×1 ~ 50×50 픽셀 (스크롤로 조절)

결과:
  - terrain.npz의 land_mask 즉시 갱신
  - 해안선 자동 재계산 (요청 시)
  - edit_history에 기록
```

용도:
- DEM이 잘못 분류한 영역 수정 (예: 항구를 해상으로 분류해버림)
- 인공 섬·매립지 추가
- 디테일 조정

#### Spot Edit (Z 값 직접 수정)

특정 위치의 elevation 값을 직접 입력:

```
사용:
  1. Map 위 클릭
  2. 다이얼로그: "현재 z = 87.34 m. 새 값:"
  3. 입력 → 즉시 반영
```

용도:
- 건물 base가 DEM과 0.5m 안 맞을 때 정확히 맞춤
- 측량 데이터로 특정 점 보정
- 디버깅용 정확한 값 설정

#### Flatten Area (영역 평탄화) — v0.33 신설

영역을 선택해 elevation을 단일 값으로 통일.

```
사용:
  1. 도구 선택 → 사각형 드래그로 영역 선택 (MVP는 사각형만)
  2. 패널에서 target z 입력 (예: 15.0 m)
  3. 옵션 선택 (constraints 등)
  4. Apply → 영역 안 elevation 일괄 변경
```

**파라미터** (MVP):

| 항목 | MVP | MVP+α |
|---|---|---|
| 영역 선택 방식 | 사각형 드래그 | + 폴리곤 클릭, + Brush 반경 |
| Target z 모드 | 구체 값 입력 | + min/avg/max/주변 평균 |
| Edge handling | hard (경계 sharp) | feather (부드러운 경계) |
| Constraints | Land only / Preserve buildings | + 더 정밀 |

**구현**:

```python
def flatten_area(terrain: WorkbenchTerrain,
                 east_min: float, east_max: float,
                 north_min: float, north_max: float,
                 target_z_m: float,
                 land_only: bool = False) -> WorkbenchTerrain:
    """사각형 영역의 elevation을 단일 값으로 통일."""
    # 영역 grid 인덱스 변환
    e_idx_min = world_to_grid_east(east_min, terrain)
    e_idx_max = world_to_grid_east(east_max, terrain)
    n_idx_min = world_to_grid_north(north_min, terrain)
    n_idx_max = world_to_grid_north(north_max, terrain)

    new_elevation = terrain.elevation_m.copy()

    # 영역 마스크
    region = np.zeros_like(terrain.elevation_m, dtype=bool)
    region[n_idx_min:n_idx_max+1, e_idx_min:e_idx_max+1] = True

    # land_only 옵션
    if land_only:
        region = region & terrain.land_mask

    new_elevation[region] = target_z_m

    return replace(terrain, elevation_m=new_elevation, edited=True)
```

**용도** (본 프로젝트 핵심):
- **함정 정박지 평탄화** — 정박지 z를 sea_surface 수준으로 (해상 영역이 아닌 매립지 등)
- **활주로 부지** — 항공 시나리오의 평평한 활주로
- **건물 부지 정리** — Add Building 전에 평평한 base 만들기 (anchor BASE_TO_TERRAIN의 정합성 ↑)
- **기지 부지** — 군 시설 평탄화

**검증·경고** (Coherence Validator):
- 영역에 land_mask=False(해상) 포함 → 경고 ("해상 z 변경 — 의도적이면 OK")
- 영역에 BASE_TO_TERRAIN building 있음 → 자동 anchor 재계산 + 알림
- 영역이 Map의 50% 이상 → 확인 다이얼로그
- target_z_m이 sea_surface.z_at_sea_m 보다 낮으면 land_mask 자동 갱신 제안

**edit_history 기록**:
```toml
[[edit_history]]
op = "flatten_area"
time = "2026-04-27T15:30:00Z"
east_min = 1200.0
east_max = 1500.0
north_min = 3300.0
north_max = 3500.0
target_z_m = 15.0
land_only = false
```

### 12.11.2 MVP+α 도구

MVP 포함 안 함. 후속 작업으로:

- **Flatten Area 확장**: 폴리곤 영역, Brush 반경, min/avg/max 모드, feather edges
- **Smooth/Sharpen**: 지역 선택해 Gaussian blur 또는 sharpening
- **Coastline Polygon Edit**: 해안선 폴리곤을 드래그해 직접 조정
- **Crop/Resize**: Map 영역 변경
- **Resolution change**: 격자 다운/업샘플링
- **Layer 합성**: 여러 DEM 합치기 (예: 해상 bathymetry 추가)
- **Cut/Fill**: 임계 z 위는 깎고 아래는 채움 (산 정상 처리)
- **Slope (Ramp)**: 시작점·끝점 z 기울기 (활주로 토목)

### 12.11.3 편집 이력 추적

자체 규격이라 편집 이력 관리 가능:

```toml
# map.toml의 [edit_history]
last_edited = "2026-04-25T10:30:00Z"
total_edits = 12

[[edit_history.entries]]
time = "2026-04-25T09:15:23Z"
op = "land_mask_paint"
area = "polygon[(1200,3400)-(1250,3450)]"
value = "land"

[[edit_history.entries]]
time = "2026-04-25T10:30:00Z"
op = "spot_edit"
location = [1245.0, 3422.0]
old_z = 87.34
new_z = 87.52
note = "Tower_A base 정합"
```

Undo/Redo는 마지막 편집 N개에 대해 가능 (MVP는 50개 제한).

### 12.11.4 원본 DEM 재import 시 편집 흔적 처리

원본 DEM에서 재변환하면 편집 흔적이 사라질 수 있음. **재변환 다이얼로그** (§ 11.10.6)에서:

- "Land/Sea Mask 편집 보존"
- "Spot Edit 보존"
- "모든 편집 폐기 (원본대로)"

선택 가능. 기본은 "보존 시도" — 가능한 한 옛 편집을 새 격자에 매핑.

## 12.12 Open Questions

- **GROUND_VEHICLE의 도로 정보**: 별도 자원 (RoadNetwork)? Map 안 포함? (MVP 후)
- **AIRBORNE의 비행 모델**: 단순 trajectory만 vs 6자유도 비행 동역학?
- **Wave 응답 모델 자유도**: MVP는 sinusoidal로 충분한가? 측정 데이터 기반은 미래?
- **표적 trajectory 편집 UI**: MVP+α에서 어떤 형태? (그래픽? 표? 둘 다?)
- **Tide model**: sea_surface.z_at_sea_m이 시간 함수가 되는 시점?
- **자세 운동학**: SURFACE_VESSEL의 wave 응답이 자체 회전 동역학을 가질지 (현재는 단순 sinusoidal)
- **지형 편집 Smooth/Sharpen**: MVP+α 도입 시 사용자 인터페이스 (브러시? 영역 선택? 강도 슬라이더?)
- **Coastline 자동 생성 알고리즘**: marching squares vs contour tracing — 어느 쪽이 적절한가

## 섹션 상태

- 12.1 핵심 통찰 — ✅
- 12.2 PlacedEntity — ✅
- 12.3 MotionKind 5 카테고리 — ✅
- 12.4 정적 vs 동적 — ✅ (Sim 상태별 처리)
- 12.5 Wave 응답 분리 — ✅
- 12.6 해수면 시각화 — ✅ (MVP 포함)
- 12.7 표적 trajectory z — ✅ (편집 UI는 MVP 후)
- 12.8 건물 anchor 시스템 — ✅ (12.8.6 land_mask 검사 v0.22 추가)
- 12.9 Sim Pause 정지 명세 — ✅
- 12.10 자원 종속성 — ✅
- 12.11 지형 편집 도구 — ✅ (v0.22 신설, MVP는 경량 — Land/Sea Mask Brush + Spot Edit + **Flatten Area** v0.33)
- 12.12 Open Questions — 🟡

---

👉 다음: [appendix_A_code_audit.md](appendix_A_code_audit.md)
👉 이전: [11_coordinate_systems.md](11_coordinate_systems.md)
