# 03. 데이터 모델 & Contract

**최종 갱신**: 2026-05-02 (v0.40 — § 3.2.1o Physics Lab dataclass 신설 — 9 Test Objects, ParamMetadata, ForceComposition, ValidationResult, ExternalDataset)

이 섹션이 제일 중요하다. 플러그인이 어떤 타입을 받고 뱉을지(Contract)를 여기서 못 박는다.
이후 리팩토링 시 이 타입들은 **가능한 한 변경하지 않는 것**을 원칙으로 한다.

---

## 3.1 설계 철학

### 불변(immutable) 우선

- `@dataclass(frozen=True)` 기본
- 상태 변화는 새 객체 생성 (copy-on-write)
- 이유: Probe 기록이 쉽고, 플러그인이 실수로 공유 상태를 더럽힐 수 없음

### 계층별 타입 분리

```
Scenario / RadarOutput / Run      ← 사용자가 저장·로드하는 상위 문서
        ↓
Detection / Track / Peak          ← 스테이지 간 주고받는 결과물
        ↓
FFTSpectrum / Reflection / TXBeam ← 스테이지 내부 중간 데이터
        ↓
numpy ndarray 원시 배열           ← 실제 숫자들
```

### JSON-Serializable First

- 모든 상위 구조는 **JSON으로 저장/로드 가능**해야 한다.
- 대용량 ndarray는 HDF5/Parquet 등 별도 포맷. JSON에는 참조 경로만.
- 이유: 나중에 다른 언어 플러그인 지원 여지를 열어둠.

---

## 3.2 Scenario (시나리오 문서)

시나리오가 CSV·argparse·하드코딩으로 흩어지면 재현성·검증·UI 모두 곤란해진다.
새 설계는 **하나의 Scenario 객체**로 통합한다.

### 3.2.1 Scenario 스키마

> **v0.20 이후 권위 위치**: Scenario는 더 이상 모든 자원을 직접 포함하지 않고 **참조** 한다.
> 권위 정의는 [10 § 10.9.3](10_workspaces.md#1093-자원-식별참조)의 `[refs]` 섹션. 아래 dataclass는
> 메모리 표현 — 디스크 저장은 `[refs] + [composition] + [platform_install]` 분리.

> ⚠️ **이 dataclass 본문은 v0.13~v0.18 시점 사고**입니다. v0.20+ 자원 참조 도입과 v0.21~v0.34
> 다음 변경들로 **실제 구조가 바뀌었습니다**:
>
> - `terrain: TerrainLayer` → `Map` 안 `WorkbenchTerrain` (§ 3.2.1c, v0.21~v0.22)
> - `buildings: tuple[BuildingBlock, ...]` → `Map` 안 (§ 3.2.1c)
> - `sea_state: int (Douglas)` → `SeaStateEnvironment` (§ 3.2.1e, v0.21)
> - `targets: tuple[TargetTrajectory, ...]` → `TargetEntity` + `TargetWaypoint` (§ 3.2.1g, v0.21, v0.27 motion_kind 포함)
> - 동역학·대기·도메인 분리 (§ 3.2.1d~k, v0.27~v0.34)
>
> **새 Claude·기여자는 § 3.2.1c~k 의 권위 정의를 보세요**. 아래 본문은 역사적 맥락 보존용.

```python
# src/workbench/domain/scenario.py

@dataclass(frozen=True)
class Scenario:
    """하나의 시뮬레이션 시나리오."""
    name: str                           # "A_Base"
    description: str
    version: str                        # "1.0"

    # 공간 원점 (ENU 기준)
    origin: GeoOrigin                   # 위도/경도/고도

    # 환경
    terrain: TerrainLayer               # DEM 포인트들
    buildings: tuple[BuildingBlock, ...]
    sea_state: int                      # Douglas 0-9

    # 레이더 배치 (v0.18에서 Platform으로 확장)
    platform: RadarPlatform             # 🆕 플랫폼 + 설치 정보 (함선/고정 지상)
    radar_site: RadarSite | None = None # 레거시 호환. 없으면 platform에서 파생

    # 레이더 모델 및 파형 (08 § 8.2)
    radar_model_id: str                 # "fmcw_triangle_v1"
    waveform_params: WaveformParams     # 모델에 맞는 파라미터 세트

    rx_array: RXArrayConfig
    duration_s: float
    frame_rate_hz: float                # trajectory 샘플링 주기

    # 표적
    targets: tuple[TargetTrajectory, ...]
    primary_target_id: int | None       # 🆕 선택 표적 기본값
                                        # None이면 Run 설정에서 반드시 지정해야 함

    # 메타
    seed: int                           # 재현용 RNG 시드
    created_at: datetime
    source_files: dict[str, Path]       # 원본 CSV 경로 등 추적용
```

### 3.2.1a Platform — 레이더 플랫폼 (v0.18 신설)

**상세는 [09_radar_platforms.md](09_radar_platforms.md) 참조.** 여기는 핵심 타입 요약.

```python
class PlatformCategory(Enum):
    MARITIME = "maritime"               # 해상 이동 (함선)
    FIXED_GROUND = "fixed_ground"       # 지상 고정 (건물·타워·산정상)
    # 미래: VEHICLE, AIRBORNE


@dataclass(frozen=True)
class RadarPlatform:
    """레이더가 설치되는 플랫폼. Scenario의 일부."""
    platform_id: str                    # "corvette_500t", "coastal_tower_50m"
    category: PlatformCategory
    display_name: str

    # 설치 위치 (ENU 로컬)
    install_east_m: float
    install_north_m: float
    install_altitude_m: float           # DEM + 구조물 높이

    # 초기 안테나 보어사이트
    initial_az_deg: float
    initial_el_deg: float

    # 운동 모델 참조
    motion_model: str                   # "sea_state", "stationary"
    motion_params: dict                 # 모델별 파라미터

    # 형상·자체 차폐
    mesh_path: Path | None
    antenna_height_above_base_m: float
    self_occlusion_cone_deg: float | None = None  # MVP+α


class PlatformMotionModel(Protocol):
    """플랫폼 6자유도 운동. Sim이 RUNNING일 때만 업데이트."""
    name: str
    def configure(self, params: dict) -> None: ...
    def update(self, sim_t_s: float) -> PlatformPose: ...


@dataclass(frozen=True)
class PlatformPose:
    """플랫폼 현재 자세. EnvironmentState에 이 값이 반영됨 (v0.18에서 자함 자세의 일반화)."""
    roll_deg: float
    pitch_deg: float
    yaw_deg: float
    velocity_east_mps: float = 0.0
    velocity_north_mps: float = 0.0
    velocity_up_mps: float = 0.0
```

**MVP 제공 Motion Model 2종**:
- `sea_state`: 기존 자함 동요 (Maritime 기본). Sea State 기반 sinusoidal roll/pitch
- `stationary`: 움직임 없음 (Fixed Ground 기본)

### 3.2.1b Platform과 EnvironmentState의 관계 (v0.18)

v0.17까지 `EnvironmentState.platform_roll_deg` / `platform_pitch_deg`는 사실상 함선 자세를
의미했다. v0.18에서는 **의미가 일반화**된다:

- 필드는 동일 (`platform_roll_deg`, `platform_pitch_deg`, `platform_yaw_deg`)
- 하지만 이제 "현재 활성 Platform의 Pose"를 가리킴
- Maritime 플랫폼 → sea_state 모델이 채움
- Fixed Ground 플랫폼 → 항상 0
- 코드상 호환되나 **의미론적으로 "자함" → "플랫폼"으로 확장**됨

### 3.2.1c Map & Workbench Native Terrain (v0.21~v0.22 신설)

**상세**: [11 § 11.4 Vertical Reference](11_coordinate_systems.md#114-수직-기준--vertical-reference-핵심),
[11 § 11.10 Workbench Native Map Format](11_coordinate_systems.md#1110-workbench-native-map-format-v022-신설),
[12 § 12.8 건물 anchor](12_placement_and_motion.md#128-건물-anchor-시스템).

```python
# src/workbench/domain/map_resource.py

class VerticalRefType(Enum):
    EGM96 = "egm96"                     # AWS·SRTM 일반 (기본)
    ELLIPSOID_WGS84 = "ellipsoid_wgs84"
    MSL_LOCAL = "msl_local"             # 지역 평균해수면
    UNKNOWN = "unknown"                 # 디버그용, 저장 시 경고


@dataclass(frozen=True)
class VerticalReference:
    type: VerticalRefType
    local_datum: str = ""               # type=MSL_LOCAL일 때만 (예: "incheon_msl_2014")
    geoid_accuracy_m: float = 1.0       # 모델 알려진 오차


@dataclass(frozen=True)
class GeoOrigin:
    """Map의 절대 기준점. 생성 후 변경 불가 (v0.21)."""
    lat_deg: float
    lon_deg: float
    alt_m: float                        # vertical_reference 기준
    vertical_reference: VerticalReference


@dataclass(frozen=True)
class SeaSurface:
    """Map의 해수면 정의."""
    z_at_sea_m: float = 0.0             # 시뮬이 해수면을 그리는 z 값
    dem_z_offset_m: float = 0.0         # DEM 보정 (필요 시)


@dataclass(frozen=True)
class WorkbenchTerrain:
    """자체 규격 지형 — terrain.npz 의 메모리 표현 (v0.22 핵심).

    저장은 numpy savez (npz). 시뮬은 외부 DEM이 아닌 이걸 사용.
    """
    grid_east_m: np.ndarray             # 1D, shape=(W,) — ENU 동쪽 격자
    grid_north_m: np.ndarray            # 1D, shape=(H,) — ENU 북쪽 격자
    resolution_m: float                 # 등간격 격자 픽셀 크기

    elevation_m: np.ndarray             # 2D, shape=(H, W) — vertical_reference 기준
                                        # 해상 영역의 값은 무시되지만 보존됨
    land_mask: np.ndarray               # 2D bool, shape=(H, W) — True=육상 (v0.22 핵심)

    interpolation: str = "bilinear"     # "bilinear" / "nearest" / "bicubic"
    edited: bool = False                # 사용자 편집 흔적 있음
    source_dem_hash: str = ""           # 원본 DEM의 SHA-256 (재변환 검증)


def sample_terrain(east: float, north: float,
                   terrain: WorkbenchTerrain,
                   sea_surface: SeaSurface) -> tuple[float, str]:
    """지형 샘플링. 핵심: land_mask=False 영역은 sea_surface.z_at_sea_m 반환.

    Returns:
        (z_m, kind) where kind in {"land", "sea"}
    """
    e_idx, n_idx = world_to_grid(east, north, terrain)
    if not terrain.land_mask[n_idx, e_idx]:
        return sea_surface.z_at_sea_m, "sea"
    # bilinear 등 샘플링
    z = bilinear_sample_elevation(terrain, east, north)
    return z, "land"


@dataclass(frozen=True)
class SimulationDomain:
    """시뮬 동작 가능 전체 영역 (v0.29 신설). 11 § 11.11."""
    bounds_east: tuple[float, float]
    bounds_north: tuple[float, float]
    ceiling_alt_m: float = 30000.0
    floor_alt_m: float = -100.0


class OutsideEnvironment(Enum):
    """Map 영역 밖 처리 방식 (v0.29)."""
    OPEN_SEA = "open_sea"              # 기본
    OPEN_LAND = "open_land"
    INFINITE_PLANE = "infinite_plane"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Map:
    """워크스페이스의 단일 절대 기준. v0.21~v0.22 통합 정의 + v0.29 SimulationDomain.

    파일 시스템 표현: resources/maps/<map_id>/{map.toml, terrain.npz, ...}
    """
    map_id: str                         # 디렉토리 이름 = ID
    name: str
    description: str

    origin: GeoOrigin                   # 불변 (v0.21)
    bounds: MapBounds                   # ENU 정밀 영역 (DEM 정의)

    terrain: WorkbenchTerrain           # 자체 규격 지형 (v0.22)
    sea_surface: SeaSurface

    coastline: CoastlinePolygon | None = None  # 자동 생성 가능
    buildings: tuple[BuildingEntity, ...] = ()  # Map의 자식 (12 § 12.10)

    # v0.29 — Simulation Domain 분리
    simulation_domain: SimulationDomain = field(
        default_factory=lambda: SimulationDomain((-50000, 50000), (-50000, 50000))
    )
    outside_environment: OutsideEnvironment = OutsideEnvironment.OPEN_SEA

    # 메타
    content_hash: str = ""              # 자동 계산 (v0.20 § 10.10)
    edit_history: tuple[EditOp, ...] = ()  # 편집 이력 (12 § 12.11.3)
    has_source_dem: bool = False        # source/ 폴더에 원본 DEM 있는지


def sample_terrain_safe(east: float, north: float,
                        map_: Map, scenario: "Scenario") -> tuple[float, str]:
    """Map 안이면 정밀, 밖이면 outside_environment 적용 (v0.29).

    상세: 11 § 11.11.5.
    """
    domain = scenario.simulation_domain_override or map_.simulation_domain
    if not domain.contains(east, north):
        raise OutsideSimulationDomainError(...)

    if map_.bounds.contains(east, north):
        return sample_terrain(east, north, map_.terrain, map_.sea_surface)

    outside = scenario.outside_environment_override or map_.outside_environment
    if outside == OutsideEnvironment.OPEN_SEA:
        return map_.sea_surface.z_at_sea_m, "outside_sea"
    elif outside == OutsideEnvironment.OPEN_LAND:
        return 0.0, "outside_land"
    elif outside == OutsideEnvironment.BLOCKED:
        raise OutsideMapError(...)
    elif outside == OutsideEnvironment.INFINITE_PLANE:
        return 0.0, "outside_land"
```

### 3.2.1d Placement & Motion (v0.21 신설)

**상세**: [12 § 12.2~12.5](12_placement_and_motion.md#122-placedentity--공통-위치-정보).

```python
# src/workbench/domain/placement.py

class MotionKind(Enum):
    """배치된 자원의 운동 종류 (v0.27 — 7종)."""
    FIXED_GROUND = "fixed_ground"           # 지상 고정
    GROUND_VEHICLE = "ground_vehicle"       # 지상 이동 (MVP 후)
    SURFACE_VESSEL = "surface_vessel"       # 해상 이동 (항해)
    FLOATING_STATIC = "floating_static"     # 해상 정박 (xy 고정 + 출렁)
    AIRCRAFT = "aircraft"                   # 일반 비행기 (v0.27)
    POWERED_FLIGHT = "powered_flight"       # 미사일·드론 (v0.27)
    BALLISTIC = "ballistic"                 # 자유낙하·탄도 (v0.27)


@dataclass(frozen=True)
class PlacedEntity:
    """모든 배치 자원의 공통 정적 위치 (Editor 결정)."""
    east_m: float
    north_m: float
    base_altitude_m: float              # 정적 z (Editor 시점)

    motion_kind: MotionKind

    # 정적 자세 (해상이면 0, 사용자 지정 가능)
    heading_deg: float = 0.0
    base_pitch_deg: float = 0.0
    base_roll_deg: float = 0.0

    motion_params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CurrentPose:
    """Sim RUNNING 중 매 틱 계산되는 동적 위치/자세 (저장 안 함, Probe로만)."""
    east_m: float
    north_m: float
    altitude_m: float
    roll_deg: float
    pitch_deg: float
    yaw_deg: float

    # base 대비 변화량 (디버깅용)
    altitude_offset_m: float
    roll_offset_deg: float
    pitch_offset_deg: float


# Sim 상태별 표시용 pose 결정 (12 § 12.4.3)
def pose_for_display(entity: PlacedEntity, sim_clock: SimulationClock,
                     sim_t_s: float, env: EnvironmentState, map_: Map) -> Pose:
    if sim_clock.state == SimulationState.RUNNING:
        return compute_current_pose(entity, sim_t_s, env, map_)
    elif sim_clock.state == SimulationState.PAUSED:
        return entity._last_running_pose       # 정지 직전 pose 유지
    else:  # STOPPED 또는 IDLE
        return base_pose(entity)               # base 위치
```

### 3.2.1e Wave Response — 환경 vs 응답 분리 (v0.21 신설)

**상세**: [12 § 12.5](12_placement_and_motion.md#125-wave-응답--환경map과-응답entity-분리).

파도 자체(Map) 와 자원의 반응(Entity)을 분리:

```python
# 환경 — Map의 sea_state
@dataclass(frozen=True)
class SeaStateEnvironment:
    """Map의 파도 환경 정의."""
    sea_state: int                      # Douglas 0~9
    dominant_period_s: float
    significant_wave_height_m: float
    direction_deg: float                # 파도 진행 방향


# 응답 — 각 Entity의 motion_params에 들어가는 모델
@dataclass(frozen=True)
class WaveResponseModel:
    """이 자원이 파도에 어떻게 반응하는가."""
    name: str                           # "large_ship" / "small_boat" / "buoy" / "none"
    heave_amplitude_m: float
    roll_amplitude_deg: float
    pitch_amplitude_deg: float
    period_offset_s: float = 0.0


# MVP 프리셋
WAVE_RESPONSE_PRESETS = {
    "large_ship": WaveResponseModel(
        name="large_ship",
        heave_amplitude_m=0.4,           # sea_state별 스케일 곱
        roll_amplitude_deg=0.5,
        pitch_amplitude_deg=0.3,
    ),
    "small_boat": WaveResponseModel(
        name="small_boat",
        heave_amplitude_m=0.8,
        roll_amplitude_deg=1.5,
        pitch_amplitude_deg=1.0,
    ),
    "buoy": WaveResponseModel(
        name="buoy",
        heave_amplitude_m=1.0,
        roll_amplitude_deg=0.0,
        pitch_amplitude_deg=0.0,
    ),
    "none": WaveResponseModel(
        name="none",
        heave_amplitude_m=0.0,
        roll_amplitude_deg=0.0,
        pitch_amplitude_deg=0.0,
    ),
}


@dataclass(frozen=True)
class WaveDisplacement:
    """매 틱 wave가 entity에 가하는 변위."""
    heave_m: float
    roll_deg: float
    pitch_deg: float
```

### 3.2.1f Building Anchor 시스템 (v0.21 신설)

**상세**: [12 § 12.8](12_placement_and_motion.md#128-건물-anchor-시스템).

```python
class AnchorMode(Enum):
    BASE_TO_TERRAIN = "base_to_terrain"   # DEM 자동 (기본)
    EXPLICIT_ALT = "explicit_alt"         # z 직접 지정
    FLOOR_AT_MSL = "floor_at_msl"         # 1층 = 해수면
    TERRAIN_OFFSET = "terrain_offset"     # DEM + offset


class MeshOrigin(Enum):
    BASE_CENTER = "base_center"           # 메시 바닥 중심 (기본)
    BASE_CORNER = "base_corner"
    VOLUME_CENTER = "volume_center"


@dataclass(frozen=True)
class BuildingEntity(PlacedEntity):
    """건물 — Map의 자식, anchor 시스템으로 부착 (v0.21).

    PlacedEntity 상속 — motion_kind는 항상 FIXED_GROUND.
    """
    name: str
    mesh_path: Path | None = None

    anchor_mode: AnchorMode = AnchorMode.BASE_TO_TERRAIN
    mesh_origin: MeshOrigin = MeshOrigin.BASE_CENTER

    # mode별 추가 파라미터
    explicit_alt_m: float | None = None     # EXPLICIT_ALT일 때
    terrain_offset_m: float | None = None   # TERRAIN_OFFSET일 때


def resolve_base_altitude(b: BuildingEntity, map_: Map) -> float:
    """anchor_mode에 따라 base_altitude_m 결정. v0.22의 land_mask 검사 포함."""
    if b.anchor_mode == AnchorMode.BASE_TO_TERRAIN:
        z, kind = sample_terrain(b.east_m, b.north_m, map_.terrain, map_.sea_surface)
        if kind == "sea":
            raise InvalidPlacement(f"Building '{b.name}'을 해상 영역에 배치할 수 없음")
        return z
    elif b.anchor_mode == AnchorMode.EXPLICIT_ALT:
        return b.explicit_alt_m
    elif b.anchor_mode == AnchorMode.FLOOR_AT_MSL:
        return map_.sea_surface.z_at_sea_m
    elif b.anchor_mode == AnchorMode.TERRAIN_OFFSET:
        z, _ = sample_terrain(b.east_m, b.north_m, map_.terrain, map_.sea_surface)
        return z + b.terrain_offset_m
```

### 3.2.1g 표적 Trajectory (v0.21 갱신, v0.27 의미 변경)

**상세**: [12 § 12.7](12_placement_and_motion.md#127-표적-trajectory의-z-처리),
[14 § 14.7](14_dynamics_model.md#147-trajectory-reference).

> **v0.27 핵심**: trajectory는 더 이상 단순 보간 위치가 아니라 **동역학 모델의 reference 입력**.
> 사용자가 입력한 waypoint는 목표(target)이고, 실제 위치는 외력 균형으로 적분 결정.

**상세**: [12 § 12.7](12_placement_and_motion.md#127-표적-trajectory의-z-처리).

```python
@dataclass(frozen=True)
class TargetWaypoint:
    t_s: float
    east_m: float
    north_m: float
    altitude_m: float                   # motion_kind에 따라 해석 (12 § 12.7.1)
    heading_deg: float


@dataclass(frozen=True)
class TargetEntity(PlacedEntity):
    """표적. PlacedEntity 상속.

    base_* 는 trajectory의 첫 번째 waypoint로 자동 결정.
    motion_kind에 따라 altitude_m 해석이 다름:
      - SURFACE_VESSEL/FLOATING_STATIC: altitude_m 무시 (sea_surface 사용)
      - AIRBORNE: altitude_m 그대로 (절대값)
      - FIXED_GROUND: altitude_m 그대로
      - GROUND_VEHICLE: 무시 (DEM 샘플링)
    """
    target_id: int
    rcs_model: str                      # "simple_aspect" / ...
    rcs_params: dict

    trajectory: tuple[TargetWaypoint, ...]

    # motion_kind 별 추가 (motion_params에 들어가지만 명시):
    # - SURFACE_VESSEL/FLOATING_STATIC: motion_params["wave_response"] = "large_ship" 등
    # - AIRBORNE: motion_params["flight_model"] = "trajectory_only" (MVP) 등

    # Multi-scatterer 모델 (v0.34) — Glint 자동 발생
    # None이면 점 표적 (역호환)
    extended_model: "ExtendedTarget | None" = None


@dataclass(frozen=True)
class Scatterer:
    """표적의 한 reflector. v0.34 MVP. 14 § 14.10."""
    offset_body_m: vec3        # body frame 위치 (forward, right, down)
    rcs_dbsm: float            # 이 scatterer의 RCS
    label: str = ""            # 디버그용


@dataclass(frozen=True)
class ExtendedTarget:
    """Multi-scatterer 표적 모델. 14 § 14.10.

    각 Preset (fighter_jet/airliner/missile_*/etc)별로
    `resources/targets/<preset>/scatterers.toml`에 기본 scatterer 분포 제공.
    """
    target_id: str
    scatterers: tuple[Scatterer, ...]   # MVP: 3~5개

    @property
    def total_rcs_dbsm(self) -> float:
        rcs_linear = sum(10 ** (s.rcs_dbsm / 10) for s in self.scatterers)
        return 10 * np.log10(rcs_linear)


@dataclass(frozen=True)
class ScatteringResult:
    """Extended target의 받음 신호 합성 결과."""
    total_signal: complex          # 모든 scatterer 합성 (Σ 채널 ref)
    apparent_position_m: vec3      # amplitude-weighted center (glint 영향)
    glint_offset_m: vec3           # apparent - actual (측정·디버그용)
```

### 3.2.1h Antenna Configuration (v0.25 신설)

**상세**: [08 § 8.5a Antenna Model](08_radar_waveforms.md#85a-antenna-model--형태와-채널-v025-신설).
여기는 핵심 타입 요약.

```python
# src/workbench/domain/antenna.py

class AntennaType(Enum):
    PARABOLIC = "parabolic"
    PLANAR_ARRAY = "planar_array"
    # MVP+α: SLOTTED_WAVEGUIDE, HORN


class AntennaConfig(Protocol):
    type: AntennaType
    def beam_pattern(self, theta_deg: float, phi_deg: float) -> float: ...
    def beamwidth_az_deg(self) -> float: ...
    def beamwidth_el_deg(self) -> float: ...
    def peak_gain_dbi(self) -> float: ...


@dataclass(frozen=True)
class ParabolicAntenna:
    type: AntennaType = AntennaType.PARABOLIC
    diameter_m: float
    frequency_hz: float
    efficiency: float = 0.6


@dataclass(frozen=True)
class PlanarArrayAntenna:
    type: AntennaType = AntennaType.PLANAR_ARRAY
    n_elements_az: int
    n_elements_el: int
    spacing_m: float                    # 보통 λ/2 (frequency_hz로 결정)
    frequency_hz: float
    element_pattern: str = "cos"        # "cos" / "isotropic"
    grid_shape: str = "rectangular"
    weighting: str = "uniform"          # MVP는 uniform만 (taper는 MVP+α)


# RX 채널 구조 (v0.25 모노펄스 확장)
class RXChannelKind(Enum):
    SUM = "sum"
    DELTA_AZ = "delta_az"
    DELTA_EL = "delta_el"
    DELTA_DELTA = "delta_delta"


@dataclass(frozen=True)
class RXChannelSpec:
    kind: RXChannelKind
    label: str


@dataclass(frozen=True)
class MonopulseRXConfig:
    n_channels: int = 4
    channel_setup: str = ""             # "quad_feed" / "subarray_partition"
    error_slope_kaz: float = 1.0
    error_slope_kel: float = 1.0
    boresight_calibration: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RXArrayConfig:
    """전체 RX 구성. v0.25에서 모노펄스 확장."""
    channels: tuple[RXChannelSpec, ...]
    monopulse: MonopulseRXConfig | None = None  # 모노펄스인 경우만
```

**호환 매트릭스**:

| AntennaType | 가능한 RX 채널 구성 | MVP |
|---|---|---|
| PARABOLIC | single SUM | ✅ |
| PARABOLIC | monopulse 4ch (quad_feed) | ✅ |
| PLANAR_ARRAY | single SUM (DBF 단순화) | ✅ |
| PLANAR_ARRAY | monopulse 4ch (subarray_partition) | ✅ |
| PLANAR_ARRAY | N채널 DBF | ❌ MVP+α |
| 모든 타입 | MIMO TX | ❌ MVP+α |

### 3.2.1i Dynamics State (v0.27 신설)

**상세**: [14 § 14.3 6DOF Rigid Body 표현](14_dynamics_model.md#143-6dof-rigid-body-표현-level-2-표준).
사실적 동역학 모델의 핵심 타입.

```python
# src/workbench/domain/dynamics.py

@dataclass(frozen=True)
class RigidBodyState:
    """6DOF 강체 상태. MVP는 자세 단순화(velocity vector 기반)."""
    east_m: float
    north_m: float
    altitude_m: float

    velocity_east_mps: float
    velocity_north_mps: float
    velocity_up_mps: float

    roll_rad: float
    pitch_rad: float
    yaw_rad: float

    angular_velocity_body_rad_s: tuple[float, float, float]

    sim_t_s: float


@dataclass(frozen=True)
class TrajectoryReference:
    """동역학이 추적하는 목표 (trajectory CSV에서 보간)."""
    east_m: float
    north_m: float
    altitude_m: float
    heading_deg: float
    sim_t_s: float


@dataclass(frozen=True)
class ThrustProfile:
    """시간 함수 또는 단계별 추력."""
    type: str  # "constant" / "curve" / "stage"
    constant_thrust_N: float = 0.0
    curve: tuple[tuple[float, float], ...] = ()  # [(t_s, thrust_N), ...]
    stages: tuple = ()  # MVP+α


# 모델별 동역학 파라미터
@dataclass(frozen=True)
class AircraftDynamics:
    mass_kg: float
    drag_coef: float = 0.04
    reference_area_m2: float = 30.0
    lift_coef: float = 0.4
    kp_position: float = 0.5
    kd_position: float = 0.3
    kp_altitude: float = 1.0
    kd_altitude: float = 0.5
    max_climb_rate_mps: float = 25.0
    max_bank_deg: float = 60.0
    max_load_factor_g: float = 4.0
    thrust_profile: ThrustProfile | None = None


@dataclass(frozen=True)
class PoweredFlightDynamics:
    mass_kg: float
    drag_coef: float = 0.3
    reference_area_m2: float = 0.1
    thrust_profile: ThrustProfile  # 필수
    lift_coef: float = 0.0
    max_load_factor_g: float = 20.0
    use_trajectory_as_reference: bool = True


@dataclass(frozen=True)
class BallisticDynamics:
    mass_kg: float
    drag_coef: float = 0.4
    reference_area_m2: float = 0.05
    initial_velocity_mps: tuple[float, float, float] = (0.0, 0.0, 0.0)
    spin_rate_rps: float = 0.0


# 적분
def dynamics_step(state: RigidBodyState, ref: TrajectoryReference,
                  motion_params: dict, dt: float) -> RigidBodyState:
    """RK4 적분, 메인 step 1회 = sub-step 10회 (dt/10)."""
    ...


def ballistic_step(state: RigidBodyState, motion_params: dict,
                   dt: float) -> RigidBodyState:
    """trajectory 무시, 외력만 작용."""
    ...
```

### 3.2.1j Tracker & Data Association (v0.34 신설)

**상세**: [16 § 16.3.3](16_baseline_audit.md), [16 § 16.3.4](16_baseline_audit.md).
베이스라인 점검 결과 EKF만으로는 부족, UKF + GNN 추가.

```python
# src/workbench/domain/tracker_ekf.py (기존 v0.10에서 리팩토링)
class EKFTracker:
    """Extended Kalman Filter (기본). 약한 비선형성에 적합."""
    process_noise_std: float
    measurement_noise: dict   # 거리·각도별 noise

    def predict(self, state: TrackState, dt: float) -> TrackState: ...
    def update(self, state: TrackState, meas: Detection) -> TrackState: ...


# src/workbench/domain/tracker_ukf.py (v0.34 신설)
class UKFTracker:
    """Unscented Kalman Filter. Sigma point 기반.

    강한 비선형성 (고기동 표적, 먼 거리)에서 EKF 대비 안정.
    Stone Soup의 UnscentedKalmanFilter와 동일 알고리즘.
    """
    alpha: float = 1e-3       # Sigma point spread
    beta: float = 2.0         # Gaussian distribution prior
    kappa: float = 0.0        # Secondary scaling

    def predict(self, state: TrackState, dt: float) -> TrackState: ...
    def update(self, state: TrackState, meas: Detection) -> TrackState: ...


class TrackerKind(Enum):
    """추적기 선택 (v0.34)."""
    EKF = "ekf"
    UKF = "ukf"
```

**Editor UI**: Radar Editor에서 드롭다운으로 선택 가능. 기본값 EKF (역호환).

```python
# src/workbench/domain/data_associator.py (v0.34 신설)
class GNNDataAssociator:
    """Global Nearest Neighbor + Hungarian assignment.

    다중 표적 환경에서 모든 detection ↔ active track의 1:1 최적 매칭.
    추적 안정성 검증의 다중 표적 환경 시뮬에 필수.
    """
    gating_threshold_sigma: float = 3.0

    def associate(
        self,
        tracks: list[Track],
        detections: list[Detection],
    ) -> dict[Track, Detection | None]:
        """Hungarian (scipy.optimize.linear_sum_assignment) 기반."""
        ...
```

**Single-target mode**: 사용자가 선택한 표적의 track만 active, 나머지 detection은 clutter로 무시. 그러나 시뮬 자체는 다중 detection 환경 (단일 표적의 안정성 검증).

### 3.2.1k Propagation Effects (v0.34 신설)

**상세**: [08 § 8.5b](08_radar_waveforms.md), [15 § 15.5.4](15_atmosphere_model.md).

```python
# src/workbench/domain/propagation/multipath.py (v0.34 신설)
def two_ray_path_loss(
    radar_pos_m: vec3,
    target_pos_m: vec3,
    sea_surface_z_m: float,
    frequency_hz: float,
    polarization: Literal["V", "H"] = "V",
) -> complex:
    """Two-ray multipath (sea bounce)."""
    ...


# src/workbench/domain/propagation/refraction.py (v0.34 신설)
EARTH_RADIUS_M = 6378137.0
EFFECTIVE_EARTH_FACTOR = 4.0 / 3.0

def effective_earth_radius_m(atm: AtmosphereState) -> float:
    """4/3 earth (표준 대기 refraction)."""
    return EARTH_RADIUS_M * EFFECTIVE_EARTH_FACTOR


def horizon_distance_m(observer_height_m: float, atm: AtmosphereState) -> float:
    """Radio horizon distance."""
    R_eff = effective_earth_radius_m(atm)
    return np.sqrt(2 * R_eff * observer_height_m)
```

### 3.2.1l Plugin Manifest — DLC 패키지 메타데이터 (v0.35 신설)

`.trsim-pkg` DLC 패키지의 `manifest.toml` 메모리 표현. 17 § 17.2.4 의 TOML 구조와 1:1 대응.

```python
# src/workbench/sdk/manifest.py (v0.35, SDK Layer)

@dataclass(frozen=True)
class PackageInfo:
    """[package] 섹션."""
    id: str                              # "advanced-tracker" (kebab-case, 전역 고유)
    name: str                            # 사람 읽기용 이름
    version: str                         # SemVer "1.2.0"
    author: str                          # "Researcher Kim <kim@univ.ac.kr>"
    description: str
    license: str                         # SPDX ID — "MIT" / "Apache-2.0" / "GPL-3.0" 등
    homepage: str | None = None


@dataclass(frozen=True)
class Compatibility:
    """[compatibility] 섹션 — TRsim Core 버전 호환."""
    trsim_min_version: str               # "0.35.0" — 최소 호환
    trsim_max_version: str | None = None # "1.x" 또는 None (상한 없음)


@dataclass(frozen=True)
class PackageDependency:
    """다른 .trsim-pkg에 대한 의존."""
    package_id: str                      # "glint-modeling-extras"
    version_spec: str                    # ">=1.0.0" (PEP 440 호환)


@dataclass(frozen=True)
class EntryPoint:
    """[entry_points] 한 항목.

    type 별 target 의미:
      - "trsim.plugins.tracker"  → "module:Class" (Python import path)
      - "trsim.plugins.detector" → "module:Class"
      - "trsim.plugins.pairing"  → "module:Class"
      - ... (9 Plugin Protocol 모두)
      - "trsim.resources.maps"   → "resources/maps/" (디렉토리 경로, 패키지 root 기준)
      - "trsim.resources.radars" → "resources/radars/"
      - "trsim.resources.targets" → "resources/targets/"
      - "trsim.ui.panels"        → "module:PanelClass"
    """
    type: str                            # "trsim.plugins.tracker" 등
    target: str                          # "module:Class" 또는 디렉토리 경로


@dataclass(frozen=True)
class PythonRequires:
    """[python] 섹션 — 추가 Python 의존성."""
    extra_requires: tuple[str, ...] = ()  # ("torch>=2.0", "scikit-learn>=1.3")


@dataclass(frozen=True)
class PackageManifest:
    """`.trsim-pkg`의 manifest.toml 메모리 표현.

    SDK가 읽고 검증, App Layer의 PackageManager가 사용.
    """
    package: PackageInfo
    compatibility: Compatibility
    entry_points: tuple[EntryPoint, ...]
    dependencies: tuple[PackageDependency, ...] = ()
    python: PythonRequires | None = None

    # 패키지 출처 추적 (SDK가 채움)
    source_path: Path | None = None      # 원본 .trsim-pkg 경로 (디버그용)
    install_path: Path | None = None     # ~/.trsim/packages/<id>/ (설치 후)


@dataclass(frozen=True)
class InstalledPackage:
    """설치된 DLC의 런타임 표현 (App Layer 가 보유).

    PackageManager가 ~/.trsim/packages/ 스캔 시 생성.
    """
    manifest: PackageManifest
    install_path: Path                   # ~/.trsim/packages/<id>/
    enabled: bool = True                 # 사용자가 disable 가능 (MVP+α)
    install_time: datetime = ...

    @property
    def id(self) -> str:
        return self.manifest.package.id
```

**검증 — `validate_manifest()` 함수 (SDK 제공)**:
- `package.id` 가 kebab-case (정규식)
- `version` 이 SemVer 형식
- `license` 가 SPDX 식별자 (whitelist)
- `compatibility.trsim_min_version` 이 현재 TRsim 버전과 호환
- `entry_points[].type` 이 9 Plugin Protocol + Resource·UIPanel 중 하나
- `entry_points[].target` 의 경로/모듈 존재 검증
- `dependencies[].version_spec` 이 PEP 440 호환

**상세 처리 흐름**: 17 § 17.2.4 (manifest.toml 구조), 02 § 2.6b (SDK Layer), 17 § 17.4.1 (PackageManager).

**MVP 범위**:
- ✅ PackageInfo / Compatibility / EntryPoint / PackageManifest / InstalledPackage dataclass
- ✅ `validate_manifest()` 검증 함수 (SDK)
- ✅ `read_manifest_toml()` 로더 (TOML → PackageManifest)
- ❌ DLC 간 의존성 해석 (MVP+α — 17 § 17.11)
- ❌ 코드 서명·sandbox (MVP+α — Q-OP2)



### 3.2.1m HIL DUT Messages — DUT 통신 데이터 모델 (v0.38 신설)

> **출처**: 18 § 18.5 (RX 표준 L1~L5), 18 § 18.6 (TX 표준)
> **권위**: 18 hil_integration

HIL 통합에서 TRsim ↔ DUT 사이 흐르는 데이터의 **형식 표준**. 5단계 RX (L1~L5) + 양방향 TX (Digital + AWG).

#### 5단계 RX 메시지 (DUT → TRsim, 모두 선택적)

```python
# domain/hil/dut_messages.py

@dataclass(frozen=True)
class DUTRawIQ:
    """L1 — ADC raw IQ samples. DUT 가 ADC 만 처리한 경우.
    분량 매우 큼 (수십 MB/s). MVP 미지원 (Phase 8.3)."""
    timestamp_ns: int
    sweep_id: int
    sweep_direction: Literal["up", "down"]
    sample_rate_hz: float
    samples_i: np.ndarray
    samples_q: np.ndarray
    metadata: dict = field(default_factory=dict)

@dataclass(frozen=True)
class DUTSpectrum:
    """L2 — FFT spectrum. DUT 가 FFT 까지 처리한 경우. (Phase 8.2)"""
    timestamp_ns: int
    sweep_id: int
    sweep_direction: Literal["up", "down"]
    fft_bins_magnitude: np.ndarray
    fft_bins_phase: np.ndarray | None = None
    bin_width_hz: float = 0.0
    metadata: dict = field(default_factory=dict)

@dataclass(frozen=True)
class DUTDetection:
    """L3 — CFAR detection peaks. (Phase 8.2)"""
    timestamp_ns: int
    sweep_id: int
    sweep_direction: Literal["up", "down"]
    peaks: list["DetectionPeak"]
    metadata: dict = field(default_factory=dict)

@dataclass(frozen=True)
class DUTPairedDetection:
    """L4 — Up/down 매칭 후 pairing 결과. (Phase 8.2)
    `target_pairing.c` 같은 핵심 검증 영역."""
    timestamp_ns: int
    pairs: list["PairedTarget"]
    metadata: dict = field(default_factory=dict)

@dataclass(frozen=True)
class DUTTrack:
    """L5 — DUT 의 최종 추적 결과. ⭐ MVP HIL 의 베이스라인 (Phase 8.1).
    분량 매우 작음, 가장 자주 보내짐."""
    timestamp_ns: int
    track_id: int
    range_m: float
    velocity_m_s: float
    azimuth_deg: float
    elevation_deg: float
    frequency_hz: float | None = None
    confidence: float | None = None
    quality_metric: float | None = None
    metadata: dict = field(default_factory=dict)
```

DUT 가 자기 능력·선호 따라 **L1~L5 중 일부만** 보냄. TRsim 의 `HILEvaluator` 가 받은 레벨에 따라 자동 비교 활성화.

#### TX 메시지 (TRsim → DUT)

```python
# domain/hil/tx_signal.py

@dataclass(frozen=True)
class TXSignalDigital:
    """Digital baseband. Ethernet/TCP 으로 전송. MVP 표준."""
    timestamp_ns: int
    sweep_id: int
    sweep_direction: Literal["up", "down"]
    sample_rate_hz: float
    samples_i: np.ndarray
    samples_q: np.ndarray

@dataclass(frozen=True)
class TXSignalAnalog:
    """AWG analog. SCPI / vendor SDK 통해 전송. MVP+α (Phase 8.3)."""
    timestamp_ns: int
    sweep_id: int
    sample_rate_hz: float
    samples_i: np.ndarray
    samples_q: np.ndarray
    output_voltage_v: float
    output_impedance_ohm: float = 50.0
```

#### 비교 결과

```python
# domain/hil/comparison.py

@dataclass(frozen=True)
class HILComparisonResult:
    """한 시점·한 표적의 GT/SIL/HIL 3-way 비교."""
    timestamp_ns: int
    target_id: int
    # GT
    gt_range_m: float
    gt_velocity_m_s: float
    gt_azimuth_deg: float
    gt_elevation_deg: float
    # SIL (Python DSP 결과)
    sil_track: TrackState | None
    # HIL (DUT 결과)
    hil_track: DUTTrack | None
    # 비교 metrics
    sil_error_range_m: float | None
    hil_error_range_m: float | None
    dut_bias_range_m: float | None  # |hil - sil| — 펌웨어 vs Python gap
    # ... velocity/azimuth/elevation 동일
```

#### 직렬화·전송

데이터 형식은 표준이지만 **transport 는 자유** (DUTAdapter Protocol — 18 § 18.7, 17 § 17.2.6).

- 기본: TCP/JSON (TCPJsonDUTAdapter, plugins_builtin/)
- 옵션: UDP/Binary, gRPC, Custom — 사용자 어댑터 또는 DLC

#### MVP 범위

- ✅ DUTTrack (L5) — Phase 8.1 핵심
- ✅ TXSignalDigital
- ✅ HILComparisonResult
- ⏳ DUTSpectrum (L2) / DUTPairedDetection (L4) — Phase 8.2
- ❌ DUTRawIQ (L1) — Phase 8.3
- ❌ TXSignalAnalog — Phase 8.3
- ❌ DUTDetection (L3) — 표준 정의는 하나 MVP 미지원



### 3.2.1n Reference Timing + Frame Profiler — 시뮬 시간 보정 데이터 모델 (v0.39 신설)

> **출처**: 18 § 18.16 Reference Timing Mode + 18 § 18.17 Frame Profiler
> **권위**: 18 hil_integration

사용자가 "테스트 코드의 실 보드 target latency" 를 명시 → 시뮬 PC 의 실측 latency 를 그 기준으로 보정 (Vivado simulation 패턴). SIL + HIL 둘 다 적용.

#### Reference Timing 입력 (사용자 명시)

```python
# domain/timing/reference_timing.py

@dataclass(frozen=True)
class StageTimingProfile:
    """한 Stage 또는 Pipeline 전체의 timing 명세.

    사용자가 시나리오 [timing.profiles] 섹션에 명시.
    target_latency_ms 우선, scale_factor 는 보조 (target 모호 시).
    """
    target_name: str  # "detector" / "tracker" / "pairing" / "pipeline_total" 등
    target_latency_ms: float | None = None  # 사용자 명시: "실 보드에서 X ms"
    scale_factor: float | None = None        # 보조: "wall_clock 의 N배 속도"
    measurement_unit: Literal["stage", "pipeline"] = "stage"

    def __post_init__(self):
        # 둘 중 하나만 명시되어야 함
        has_target = self.target_latency_ms is not None
        has_scale = self.scale_factor is not None
        if has_target == has_scale:
            raise ValueError("target_latency_ms 또는 scale_factor 중 하나만 명시")


@dataclass(frozen=True)
class TimingConfig:
    """Scenario [timing] 섹션 전체."""
    mode: Literal["sim_time", "real_time", "reference"] = "sim_time"
    frame_unit: Literal["fmcw_sweep", "fft_window", "auto", "custom"] = "auto"
    profiles: list[StageTimingProfile] = field(default_factory=list)
```

#### Reference Timing 런타임 상태

```python
@dataclass
class ReferenceTimingState:
    """Run 중 PerformanceClock 의 측정 상태."""
    sim_frame: int  # 현재 frame ID (frame 단위 재현성)
    reference_time_ns: int  # 누적 reference 시간
    wall_clock_ns: int      # 누적 wall clock
    last_measured_latencies: dict[str, float]  # stage_name → 직전 frame 측정 ms
    handshake_state: Literal["pc_waiting", "dut_waiting", "in_sync", "n/a"] = "n/a"
    # n/a 는 SIL 모드 (handshake 없음)
```

#### Frame Boundary Detector (자동 추론, Q-RT1)

```python
class FrameBoundaryDetector:
    """frame_unit='auto' 시 frame 경계 추론.

    테스트 코드의 최종 결론 (표적 AZ/EL 출력) 시점마다 frame 갱신.
    TrackOutputProbe 의 출력 시점을 감지.
    """
    def on_track_output(self, track: TrackState) -> bool:
        """track 출력 시 호출 → frame 경계인지 판단.

        Returns:
            True 면 새 frame 시작 (frame_id 증가).
        """
        ...
```

#### Frame Profiler 결과

```python
# domain/timing/frame_profiler.py

@dataclass(frozen=True)
class StageTimingStat:
    """한 Stage 의 측정 통계."""
    stage_name: str
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    sample_count: int


@dataclass(frozen=True)
class FrameTimingReport:
    """Frame Profiler 의 결과.

    Pre-run profiling 또는 백그라운드 측정 후 생성.
    """
    scenario_name: str
    profile_frames: int      # 측정한 프레임 수 (warmup 제외)
    warmup_frames: int       # 버린 warmup 수 (Q-RT7)
    measurement_context: dict  # CPU info, OS, load (Q-RT8)
    stage_stats: dict[str, StageTimingStat]  # stage_name → 통계
    pipeline_stat: StageTimingStat            # pipeline_total
    timestamp: datetime  # 측정 시각
```

#### 직렬화·전송

- TOML: 사용자 입력 (`[timing]` + `[[timing.profiles]]`)
- JSON: Frame Profiler 보고서 (`profile.json`)
- Markdown: Frame Profiler 보고서 사람 읽기용 (`profile.md`)

#### Probe 통합

기존 ProbeRecorder (06 § 6.x, v0.13) 가 stage I/O 기록. v0.39 에서 timing 도 같이 기록:

```python
# 기존 (Phase 2~3, v0.13)
class ProbeRecorder:
    def record_stage_io(self, stage_name: str, input, output): ...

# 신규 (Phase 3, v0.39)
class StageTimingProbe(ProbeRecorder):
    """Stage 시작·끝 timestamp 기록 — Frame Profiler 의 입력."""
    def on_stage_start(self, stage_name: str): ...
    def on_stage_end(self, stage_name: str): ...

    @property
    def measured_latencies(self) -> dict[str, list[float]]:
        """stage_name → 측정 latency 리스트 (frame 별)."""
        ...
```

#### MVP 범위

- ✅ StageTimingProfile / TimingConfig dataclass — Phase 2
- ✅ ReferenceTimingState — Phase 3
- ✅ StageTimingStat / FrameTimingReport — Phase 2~3
- ✅ FrameBoundaryDetector (자동 추론) — Phase 3
- ✅ StageTimingProbe — Phase 3
- ⏳ Lock-step Handshake (HIL only) — Phase 8.1 (DUTAdapter sync 메서드)
- ⏳ scale_factor 보조 입력 — Phase 3 (target_latency_ms 와 같이 구현)



### 3.2.1o Physics Lab — 인터랙티브 물리 실험실 데이터 모델 (v0.40 신설)

> **출처**: 19 § 19.4~19.7 Physics Lab
> **권위**: 19 physics_lab

Physics Lab 의 3-pane 인터랙티브 환경 + 9 Test Objects + 4 시간 모드 + 사용자 plugin 지원 dataclass.

#### 9 Test Objects (PL-5)

```python
# physics/test_objects.py

@dataclass(frozen=True)
class Sphere:
    """구 — 점질량 + 반지름. 가장 핵심 (분석 공식 풍부)."""
    radius_m: float
    mass_kg: float
    drag_coefficient: float = 0.47
    restitution: float = 0.8

@dataclass(frozen=True)
class Cube:
    side_m: float
    mass_kg: float
    drag_coefficient: float = 1.05

@dataclass(frozen=True)
class Plate:
    """평판. RCS = 4πA²/λ² (analytic)."""
    width_m: float
    height_m: float
    thickness_m: float = 0.001

@dataclass(frozen=True)
class Cylinder:
    radius_m: float
    length_m: float
    mass_kg: float
    drag_coefficient: float = 0.82

@dataclass(frozen=True)
class Cone:
    """미사일 노즈 단순화."""
    base_radius_m: float
    height_m: float
    mass_kg: float

@dataclass(frozen=True)
class Point:
    """무한소 점. 순수 dynamics 검증."""
    mass_kg: float

@dataclass(frozen=True)
class Plane:
    """무한 평면 (지면)."""
    normal: tuple[float, float, float] = (0, 1, 0)
    height_m: float = 0
    reflection_coefficient: float = 0.5

@dataclass(frozen=True)
class Wall:
    width_m: float
    height_m: float
    thickness_m: float = 0.1

@dataclass(frozen=True)
class Trihedral:
    """RCS 측정 표준 (corner reflector). RCS = 4π·a⁴/(3λ²) at boresight."""
    edge_length_m: float
```

#### 파라미터 metadata (PL-8)

```python
# physics/_param_metadata.py

@dataclass(frozen=True)
class ParamMetadata:
    """슬라이더 노출용 parameter metadata.
    Decorator (@physics_param) 또는 type hint (Annotated) 로 명시."""
    name: str
    min_value: float
    max_value: float
    default_value: float
    unit: str  # "kg", "m", "s", "dB", "deg", etc.
    scale: Literal["linear", "log"] = "linear"
    is_integer: bool = False
    description: str = ""

# decorator 사용 예
@physics_param(name="mass", min=0.1, max=100, scale="log", unit="kg")
@physics_param(name="radius", min=0.01, max=10, scale="log", unit="m")
def gravity_force(mass: float, radius: float, ...): ...

# type hint 사용 예 (Python 3.9+)
from typing import Annotated
def drag_force(
    velocity: Annotated[float, ParamMetadata("velocity", 0, 1000, scale="linear", unit="m/s")],
    cd: Annotated[float, ParamMetadata("Cd", 0, 2, scale="linear")],
): ...
```

#### Force Composition (PL-3 의 부분)

```python
@dataclass(frozen=True)
class ForceModel:
    """단일 force (gravity, drag, lift, etc.)."""
    name: str
    category: Literal["dynamics", "propagation", "reflection", "antenna", "atmosphere"]
    enabled: bool = True
    params: dict[str, float] = field(default_factory=dict)

@dataclass(frozen=True)
class ForceComposition:
    """다중 force 의 조합 — Physics Lab 의 모델 활성화 상태."""
    forces: list[ForceModel]
    integration_method: Literal["euler", "rk4", "verlet"] = "rk4"

    def total_force(self, state: PhysicsState) -> np.ndarray:
        """활성화된 모든 force 합산."""
        return sum(f.evaluate(state) for f in self.forces if f.enabled)
```

#### Physics Lab 실험 상태

```python
# app/physics_lab/experiment_state.py

@dataclass(frozen=True)
class PhysicsState:
    """Test Object 의 시간별 상태 (Single Run 모드)."""
    t_s: float
    position: np.ndarray  # shape (3,) ENU
    velocity: np.ndarray  # shape (3,)
    orientation: np.ndarray  # quaternion (4,)
    angular_velocity: np.ndarray  # shape (3,)
    accumulated_force: np.ndarray  # 누적 force (시각화용)

@dataclass
class PhysicsExperiment:
    """Physics Lab 의 한 실험."""
    name: str
    test_object: Sphere | Cube | Plate | Cylinder | Cone | Point | Plane | Wall | Trihedral
    composition: ForceComposition
    initial_state: PhysicsState
    duration_s: float
    dt_s: float
    time_mode: Literal["static", "single_run", "compare", "sweep"] = "single_run"
    seed: int | None = None  # 재현성

    # 결과
    states_history: list[PhysicsState] | None = None
    analytic_reference: np.ndarray | None = None  # 분석 공식 결과 (있으면)
```

#### Validation Result

```python
# app/physics_lab/validation_bench.py

@dataclass(frozen=True)
class ValidationResult:
    """단일 검증 시나리오 결과."""
    scenario_name: str  # "two_ray_lobing", "sphere_freefall", ...
    analytic_values: np.ndarray  # 분석 공식
    implementation_values: np.ndarray  # 구현
    rmse: float
    max_diff: float
    threshold: float
    passed: bool  # rmse < threshold

@dataclass(frozen=True)
class ValidationReport:
    """전체 회귀 결과 (17~20+ 시나리오)."""
    total: int
    passed: int
    failed: int
    results: list[ValidationResult]
    timestamp: datetime
```

#### 외부 데이터

```python
# app/physics_lab/external_data_loader.py

@dataclass(frozen=True)
class ExternalDataset:
    """업로드된 측정 데이터."""
    name: str
    source_path: str
    format: Literal["csv", "hdf5", "npz"]
    independent_var: str  # "range", "time", "angle"
    independent_values: np.ndarray
    dependent_vars: dict[str, np.ndarray]  # name → values
    metadata: dict  # source, conditions, license
    license: str | None = None
```

#### 학습 결과 (형태 1)

```python
# app/physics_lab/parameter_fitter.py

@dataclass(frozen=True)
class FittedParameters:
    """파라미터 학습 결과 (형태 1)."""
    model_name: str
    fitted_params: dict[str, float]
    fit_quality: float  # R², RMSE 등
    measurement_dataset: str  # ExternalDataset 참조
    fit_method: str  # "least_squares", "scipy.optimize.curve_fit", etc.
    timestamp: datetime
```

#### MVP 범위

- ✅ 9 Test Objects dataclass — Phase 2
- ✅ ParamMetadata + decorator/type hint — Phase 2
- ✅ ForceModel / ForceComposition — Phase 2
- ✅ PhysicsState / PhysicsExperiment — Phase 2~3
- ✅ ValidationResult / ValidationReport — Phase 2~3 (Phase 5 대신 Physics Lab 안)
- ⏳ ExternalDataset / FittedParameters — Phase 9.1
- ⏳ NN 대체 결과 dataclass — Phase 9.3 (Phase 6 NN 결합)
- ⏳ Symbolic regression 결과 — Phase 9.2



### 3.2.2 선택 표적 (Primary Target)

본 워크벤치의 최우선 지표가 "선택 표적의 안정적 추적"이므로, 선택 표적은 **1급 개념**이다.

**지정 우선순위** (높은 것 우선):

1. **Run 설정** (`RunConfig.primary_target_id_override`) — 실행 시 명시적 덮어쓰기
2. **Scenario 기본값** (`Scenario.primary_target_id`) — 시나리오 파일에 기록
3. **(MVP+α)** 런타임 UI 클릭 — 3D 뷰에서 표적 클릭으로 실시간 변경

**값의 의미**:
- `int`: `targets` 내 해당 `target_id`. 유효성은 로드 시 검증
- `None`: 시나리오에 기본값 없음 → Run 설정 또는 UI 선택 필수

**포지셔너 Closed-Loop 규약**:
- Tracker는 모든 표적의 트랙을 유지하되, **선택 표적 트랙의 위치**를 포지셔너 컨트롤러에 전달
- 포지셔너는 동역학 한계(예: AL-4018D 기준 ±30°/s) 안에서 그 방향으로 회전
- 선택 표적이 트랙에서 누락되면(lost) 포지셔너는 마지막 예측 위치를 유지하거나 scan 모드로 전환 — 상세 정책은 Tracker Plugin이 결정

### 3.2.3 하위 타입들

> ⚠️ **이 섹션은 v0.13~v0.18 시점의 옛 표현**입니다. v0.21+ 권위 정의로 대체됨:
>
> - `RadarSite` → `RadarPlatform` + `PlatformInstallation` (§ 3.2.1a, 09 radar_platforms)
> - `TargetTrajectory` → `TargetEntity` + `TargetWaypoint` (§ 3.2.1g, motion_kind 포함, v0.27)
> - `TargetSample` → `CurrentPose` (§ 3.2.1d, 동역학 적분 결과, v0.27)
> - 함선 자세 (roll/pitch/yaw_rate) → `WaveResponseModel` (§ 3.2.1e, v0.21에서 환경 vs 응답 분리)
>
> 아래 본문은 역사적 맥락 보존. **새 Claude·기여자는 § 3.2.1a~g 를 보세요**.

```python
@dataclass(frozen=True)
class RadarSite:
    east_m: float
    north_m: float
    altitude_m: float
    host_building_label: str | None     # "building_42" or None (지표 위)
    mount_height_m: float

@dataclass(frozen=True)
class TargetTrajectory:
    target_id: int
    ship_class: str                     # "corvette_1000t"
    mesh_path: Path                     # STL 경로
    rcs_model: RCSModel                 # 🆕 스칼라 대신 모델 참조 (§ 3.2.3a)
    samples: tuple[TargetSample, ...]   # 프레임별

@dataclass(frozen=True)
class TargetSample:
    frame_id: int
    time_s: float
    east_m: float
    north_m: float
    z_m: float
    heading_deg: float
    speed_mps: float

    # 🆕 함선 자세 (파도·바람에 의한 roll/pitch, 기본 0.0)
    # MVP의 간단 모델: Sea State 기반 sinusoidal (시나리오 로드 시 계산)
    roll_deg: float = 0.0               # 좌우 기울기 (port/starboard)
    pitch_deg: float = 0.0               # 전후 기울기 (bow/stern)
    yaw_rate_dps: float = 0.0           # yaw 속도 (heading 변화율)
```

### 3.2.3a RCS 모델 (자세·각도 의존)

> ⚠️ **v0.34 정합 노트**: 이 `RCSModel` Protocol은 **점 표적의 aspect-dependent RCS** 모델.
> v0.34에서 도입한 `ExtendedTarget` (§ 3.2.1k, multi-scatterer + glint, 14 § 14.10)이
> **MVP 권위 표적 모델**. 둘의 관계:
>
> - **MVP** (v0.34): 표적은 `ExtendedTarget` (3~5 scatterers). 각 scatterer는 `Scatterer.rcs_dbsm` 스칼라
> - **MVP+α**: 각 Scatterer 가 자체 `RCSModel` (aspect-dependent) 가질 수 있음 — Aspect-dependent RCS pattern (16 § 16.4 #3)
> - **점 표적의 단순 모델**로 RCSModel 자체는 보존 가치 있음 — 작은 표적 (artillery_shell, building) 또는 디버그용
>
> 즉 RCSModel 추상은 **유효하지만 권위는 ExtendedTarget**, 추후 둘 합성 가능.

함선은 **관측 방향에 따라 RCS가 크게 변한다** (brodside 방향 10+ dB, bow 방향 수 dB 등).
또한 파도에 의한 roll/pitch가 관측 aspect angle을 시시각각 바꾼다. 이를 반영하려면 RCS가
**스칼라가 아닌 함수**여야 한다.

```python
from typing import Protocol

class RCSModel(Protocol):
    """표적의 RCS 계산 인터페이스.

    aspect angle (관측자 기준 표적의 헤딩), roll/pitch 자세,
    그리고 주파수를 입력받아 dBsm 단위 RCS 반환.
    """
    def compute_dbsm(
        self,
        aspect_az_deg: float,       # 관측자→표적의 방위 (표적 헤딩 기준)
        aspect_el_deg: float,       # 관측자→표적의 앙각
        roll_deg: float,
        pitch_deg: float,
        frequency_hz: float,
    ) -> float:
        ...
```

**MVP 기본 구현**: `SimpleAspectRCSModel` — 문헌 기반의 단순 코사인 로브 모델:

```python
@dataclass(frozen=True)
class SimpleAspectRCSModel:
    """간단한 aspect 의존 RCS. Step 4의 3D 메시 기반 모델이 준비되기 전 임시."""
    broadside_dbsm: float               # 측면 (최대)
    bow_dbsm: float                     # 전방 (최소)
    stern_dbsm: float                   # 후방
    # compute_dbsm은 aspect_az를 roll/pitch로 보정 후 세 값 사이 보간
```

**미래 구현**: `MeshRCSModel` (Step 4) — STL 기반 PO/SBR/학습 모델. 같은 Contract를 따름.

**Swerling 등 확률적 요동**: Contract가 이미 함수이므로, Swerling 모델도 `RCSModel` 구현체
하나로 추가 가능. MVP 기본은 deterministic.

### 3.2.3b 사이드로브 (Antenna Pattern 확장)

> ⚠️ **v0.25 권위**: 안테나 빔 패턴 (사이드로브 포함)은 v0.25에서 도입한 `AntennaConfig`
> Protocol과 `beam_pattern()` 메서드가 권위. § 3.2.1h Antenna Configuration 참조.
> 본 섹션은 **v0.13~v0.18 시점 단순 사이드로브 파라미터** 사고 — 보존되지만 갱신은 § 3.2.1h.

기존 RXArrayConfig가 단순 빔 모델만 가졌던 것을 사이드로브 파라미터로 확장:

```python
@dataclass(frozen=True)
class RXArrayConfig:
    # 기존 필드들 (채널 수, antenna 간격 등) ...

    # 🆕 안테나 패턴 파라미터
    beamwidth_az_deg: float             # -3dB 빔 폭 (방위)
    beamwidth_el_deg: float             # -3dB 빔 폭 (앙각)
    first_sidelobe_db: float = -13.3    # 첫 사이드로브 상대 레벨 (sinc² 기준 기본값)
    # MVP: sinc² 패턴 가정. 더 정밀한 패턴은 미래 확장
```

이 파라미터가 있으면 Environment에서 반사 계산 시 **빔 패턴을 적용**해 메인빔 밖 표적도
사이드로브 레벨만큼 신호가 잡힘. 멀티 타겟이 가까우면 강한 Secondary가 사이드로브로
Primary를 오염시키는 현상을 시뮬 가능.

### 3.2.3c 자함 동요 (Platform Stabilization State)

RadarSite에 파도에 의한 흔들림 상태 추가. 함선 자세(TargetSample.roll/pitch)와 같은 모델
재사용:

```python
@dataclass(frozen=True)
class RadarSite:
    # 기존 필드들 ...

    # 🆕 자함 동요
    platform_dynamics: PlatformDynamics | None = None
    # None이면 고정 플랫폼(육상) 가정.
    # 있으면 매 프레임 Positioner가 명령한 각도에 platform_roll/pitch가 더해짐.

@dataclass(frozen=True)
class PlatformDynamics:
    sea_state: int                      # 이 값에서 유도 (중복이지만 명시적)
    stabilization: str                  # "none" / "mechanical" / "gyro"
    # MVP 기본: 레이더 사이트의 실시간 roll/pitch는 Sea State 기반 간단 sinusoidal
```

### 3.2.4 Scenario 저장 포맷

기존 CSV와의 호환성을 위해:

```
scenarios/
└── A_Base/
    ├── scenario.toml       ← 메타·설정 (신규)
    ├── trajectory.csv      ← 표적 경로 (기존 호환)
    ├── gt_targets.csv      ← Ground Truth (기존 호환)
    └── environment.toml    ← 지형/건물 참조 (신규)
```

로더는 `scenario.toml`을 읽고 거기에 명시된 CSV들을 후속 로드.
**기존 시나리오는 `scenario.toml`만 추가하면 호환**.

### 3.2.5 Ground Truth 분리

**중요한 변경**: Ground Truth(`gt_targets.csv`)는 **Scenario에 들어가지 않는다**.
별도의 `GroundTruthTrack` 객체로 분리, 평가자(Evaluator)만 접근 가능.

이유: 플러그인이 GT를 못 보게 해야 정직한 검증이 됨.

```python
@dataclass(frozen=True)
class GroundTruthTrack:
    """평가용 정답. 플러그인은 이 타입을 볼 수 없음."""
    scenario_name: str
    targets: tuple[GTTarget, ...]

@dataclass(frozen=True)
class GTTarget:
    frame_id: int
    target_id: int
    true_range_m: float
    true_az_deg: float
    true_el_deg: float
    true_velocity_mps: float
    is_visible: bool
    is_in_beam: bool
```

Scenario와 GroundTruth는 같은 디렉토리에 있지만 **로더가 다름**:
- `ScenarioLoader.load(path)` → 플러그인에 전달 가능
- `GroundTruthLoader.load(path)` → Evaluator만 사용

---

## 3.3 DSP Pipeline Contract

### 3.3.1 파이프라인 구조

표준 추적 레이더 파이프라인 (Skolnik 등 문헌 표준) 의 9-스테이지 구조 (v0.34 갱신):

```
1. Transmitter       : emit() → TXBeam
2. Environment       : compute_reflections(beam) → list[Reflection]
3. Receiver          : receive_and_fft(reflections) → FFTSpectrum
                       compute_angle(spectrum, sweep, bin) → (az_res, el_res)
4. Detector          : detect_from_spectrum(spectrum) → (up_peaks, down_peaks)
5. Pairing           : match(up_peaks, down_peaks) → list[PairedDetection]
6. Tracker           : update(detections, dt) → list[Track]
+ PositionerController : set_target, get_state, step(dt) → JointState
```

### 3.3.2 Contract를 Protocol로 정의

> ⚠️ **v0.35 정합**: v0.35에서 도입한 SDK Layer (02 § 2.6b, 17 § 17.2.6) 가
> **DLC 작성자용 안정 Public API**. 본 섹션의 Contract는 **Domain 내부 정의** —
> 둘의 관계:
>
> - **Domain Contract** (본 섹션): Domain Layer 내부에서 Pipeline·Stage 간 결합용. 자유 변경 가능
> - **SDK Protocol** (`trsim.sdk.protocols`): DLC 안정 API. semver, 호환성 보장
> - 일반적으로 SDK Protocol은 Domain Contract를 **재export** 하거나 얇게 wrap
> - DLC는 SDK Protocol만 사용. Core 코드는 Domain Contract 직접 사용 가능
>
> 9개 SDK Protocol (Detector/Pairing/AngleEstimator/Tracker/Predictor/Classifier/
> DataAssociator/Resource/UIPanel) 정의는 § 3.2.1l 또는 02 § 2.6b 참조.

```python
# src/workbench/domain/contracts.py
from typing import Protocol

class DetectorContract(Protocol):
    """CFAR 혹은 그와 등가의 검출기."""

    name: str                           # 플러그인 식별용 (필수)
    version: str                        # 재현성 추적용

    def configure(self, config: DetectorConfig) -> None:
        """Run 시작 전 1회 호출. 파라미터 주입."""
        ...

    def detect_from_spectrum(
        self, spectrum: FFTSpectrum
    ) -> tuple[tuple[Peak, ...], tuple[Peak, ...]]:
        """한 프레임 스펙트럼 → (up_peaks, down_peaks). Pure function 권장."""
        ...

    def reset(self) -> None:
        """Run 간 상태 초기화 (있을 경우)."""
        ...
```

나머지 Contract(Tracker, Pairing, ...)도 같은 패턴.

### 3.3.3 스테이지 간 데이터 타입

```python
@dataclass(frozen=True)
class Peak:
    bin_idx: int
    freq_hz: float
    amplitude_db: float
    snr_db: float
    sweep_type: str                     # "up" or "down"
    # 4채널 위상 정보 (각도 추정용, 선택)
    phases_rad: tuple[float, float, float, float] | None

@dataclass(frozen=True)
class FFTSpectrum:
    up: numpy.ndarray                   # shape (n_bins,), dB
    down: numpy.ndarray                 # shape (n_bins,), dB
    up_channels: numpy.ndarray          # shape (4, n_bins), complex - 4채널 원시
    down_channels: numpy.ndarray
    fft_config: FMCWConfig              # 역산용 참조

@dataclass(frozen=True)
class PairedDetection:
    range_m: float
    velocity_mps: float
    up_peak: Peak
    down_peak: Peak
    snr_avg_db: float

@dataclass(frozen=True)
class Detection:
    range_m: float
    az_deg: float                       # absolute (world)
    el_deg: float
    velocity_mps: float
    snr_db: float
    timestamp_s: float

@dataclass(frozen=True)
class Track:
    track_id: int
    state: TrackState
    cov: numpy.ndarray                  # 공분산
    confidence: float
    history: tuple[Detection, ...]      # 최근 N개
```

### 3.3.4 플러그인 교체 범위

사용자는 다음 **6개 Contract** 중 원하는 조합을 구현해 제출:

| Contract | 필수 여부 | 기본값 사용 가능 |
|---|---|---|
| Transmitter | 선택 | ✓ 항상 기본값 권장 |
| Environment | 선택 | ✓ (물리 모델이므로 사용자 수정은 🔒 Out of scope) |
| Receiver | 선택 | ✓ |
| Detector | 🎯 MVP 주 타겟 | ✓ |
| Pairing | 🎯 MVP 주 타겟 | ✓ |
| Tracker | 🎯 MVP 주 타겟 | ✓ |
| PositionerController | 선택 | ✓ |

**MVP 범위**: Detector / Pairing / Tracker 3개 Contract에 대해서만 플러그인 교체 UI 완비.
나머지는 코드로 교체 가능하지만 UI 워크플로우는 후속.

---

## 3.4 Probe / Trace 시스템

**디버깅+재현**을 위해 모든 중간 결과를 기록할 수 있어야 한다.

### 3.4.1 Probe 개념

Probe = 파이프라인의 특정 지점에 부착된 **관찰점**.
각 Probe는 이름을 가지고, 매 프레임 값을 캡처할 수 있다.

```
Frame ─┬─ probe "tx_beam" ──── TXBeam
       ├─ probe "reflections" ── list[Reflection]
       ├─ probe "rx_fft" ────── FFTSpectrum
       ├─ probe "up_peaks" ──── tuple[Peak, ...]
       ├─ probe "down_peaks" ── tuple[Peak, ...]
       ├─ probe "paired" ────── list[PairedDetection]
       ├─ probe "detections" ── list[Detection]
       ├─ probe "tracks" ────── list[Track]
       └─ probe "positioner" ── JointState
```

사용자 플러그인도 자체 Probe를 노출 가능:
```python
class MyDetector:
    def __init__(self):
        self.probes = {
            "my_threshold": None,  # 매 프레임 내가 쓴 threshold
        }

    def detect_from_spectrum(self, spectrum):
        th = self._compute_threshold(spectrum)
        self.probes["my_threshold"] = th
        ...
```

### 3.4.2 Trace Record

한 Run의 모든 Probe 캡처 = **Trace**.

```python
@dataclass(frozen=True)
class TraceFrame:
    frame_id: int
    timestamp_s: float
    probes: dict[str, Any]              # probe name → captured value

@dataclass(frozen=True)
class Trace:
    run_id: str
    scenario_name: str
    frames: tuple[TraceFrame, ...]
    probe_schema: dict[str, type]       # name → type (검증용)
```

### 3.4.3 저장 포맷

**MVP**: 단순함 우선
- 작은 시나리오(< 1000 프레임) → 단일 JSON (ndarray는 base64 인코딩)
- 큰 시나리오 → HDF5 하나의 파일 (프레임/Probe 계층)

**후속 고려**:
- Parquet (프레임 단위 컬럼 저장, 부분 로드 효율)
- 청크 스트리밍 (실시간 기록, 앱 종료 전 확정)

### 3.4.4 Probe on/off 제어

Probe 캡처는 비용이 있다 (메모리, 저장 시간). 사용자가 선택적으로 켜야 함.

```python
# 기본: 모든 기본 Probe 켜짐, 단 ndarray는 요약(shape/mean)만
probe_config = ProbeConfig(
    enabled={"tx_beam", "up_peaks", "down_peaks", "tracks"},
    capture_ndarrays=False,  # 대용량 배열은 저장 안 함 (디버깅 시에만 켜기)
)
```

---

## 3.5 Program Session & Run 생애주기 (v0.14 신설)

### 3.5.0a 왜 이 구분이 필요한가

기존 계획서는 "Run = 시뮬 실행" 으로 뭉뚱그렸으나, 실제로는 **두 개의 독립된 생애주기**가
존재한다:

- **Program Session**: Workbench 앱 실행~종료. 환경·레이더·Pipeline은 **이 내내 계속 동작**.
  Real-world처럼 바람·파도·자함 동요·기상이 시시각각 변하며, 레이더는 신호를 계속 송수신.
- **Run**: **표적 trajectory 재생** 구간. 환경은 항상 돌아가지만, 표적은 Run 상태일 때만
  움직인다. 메트릭 기록도 Run 구간에서만 유의미.

이 구분이 중요한 이유:

1. **사용자가 Pre-Run 상태에서 관찰·조정 가능** — FFT 확인, 방향키로 포지셔너 수동 조작,
   잡음·정지 표적 에코 관찰 등 Run 시작 전 준비 단계가 필요
2. **Tracker 격리 보장의 일부** — Tracker는 Run 진행 중 "그 순간까지의 측정값"만 알 수 있음.
   표적 미래 움직임(trajectory)은 Tracker 입력에 절대 흘러가지 않음
3. **재현성** — Run은 반복 실행 가능하되 환경은 계속 변하므로, 완전 재현은 시드 포함해 별도
   관리

### 3.5.0b Target Run State 머신 상세 (Layer 2)

Layer 2의 상태 전이를 구체적으로:

```
[Scenario Load]
      │
      ▼
  ┌────────┐
  │  IDLE  │ ◀──────────────────┐
  │ 표적   │                     │
  │ 정지   │                     │
  └────┬───┘                     │
       │                         │
       │ [▶ Run]                 │ [⏹ Stop] + 저장 확인 다이얼로그
       ▼                         │
  ┌───────────┐                  │
  │  RUNNING  │──[자연 종료]──▶ ┌───────┐
  │ 표적 재생 │                  │ ENDED │──[▶ Run]──▶ RUNNING (처음부터)
  └─┬───────┬─┘                  └───────┘
    │       │                        │
    │[Pause]│                        │ [⏹ Stop] → IDLE
    ▼       │                        │
  ┌────────┐│
  │ PAUSED ││
  │ 표적   │└──[▶ Run]── RUNNING (재개)
  │ 정지   │
  └────┬───┘
       │
       │ [⏹ Stop] + 저장 확인
       ▼
     IDLE
```

#### 각 상태의 의미 (Sim Clock=RUNNING 전제)

| Target 상태 | 표적 | 메트릭 기록 | Sim이 PAUSED가 되면? |
|---|---|---|---|
| **IDLE** | 시작 위치 정지 | ❌ | 모든 것 정지 (표적은 이미 정지 상태) |
| **RUNNING** | trajectory 재생 | ✅ | 표적 재생도 실질적으로 정지 (Sim 시간 기반이므로) |
| **PAUSED** | 현재 위치 정지 | 일시중지 | 영향 없음 (이미 표적 정지) |
| **ENDED** | 마지막 위치 정지 | 저장 완료 | 영향 없음 |

#### Target 버튼별 동작 상세

- **Run 버튼 (IDLE → RUNNING)**: 표적 trajectory 재생 시작. 포지셔너를 시나리오에 정의된
  기본 포지션으로 **자동 배치**. 메트릭 기록 시작. Sim Clock이 STOPPED/PAUSED였다면 자동으로 Sim Start.
- **Run 버튼 (PAUSED → RUNNING)**: 일시정지된 trajectory 재개.
- **Run 버튼 (ENDED → RUNNING)**: 처음부터 다시 시작 (새 Run ID).
- **Pause 버튼 (RUNNING → PAUSED)**: 표적 trajectory 정지, 현재 위치 유지. Sim은 계속 RUNNING일 수 있음 (환경은 계속 변함).
- **Stop 버튼 (RUNNING/PAUSED → IDLE)**:
  - **저장 확인 다이얼로그**: "이 Run 결과를 저장하시겠습니까?". 기본 저장
  - 저장 선택 → `RunResult(termination=ABORTED)` 기록
  - 폐기 선택 → `RunResult` 생성 안 됨
  - 표적은 시작 위치로 복귀
- **자연 종료 (RUNNING → ENDED)**: trajectory 파일 마지막 시점 도달. `RunResult(termination=COMPLETED)` 자동 저장.


class RunTerminationReason(Enum):
    COMPLETED = "completed"     # trajectory 끝까지 진행
    ABORTED = "aborted"         # 사용자 Target Stop
    ERROR = "error"             # Pipeline 예외
    SIM_STOPPED = "sim_stopped" # 🆕 Sim Clock이 Stop되어 Run도 강제 종료

---

### 3.5.0c 두 레이어 시간 제어 (v0.15 재설계)

시간 제어는 **두 개의 독립된 레이어**로 구성된다. v0.14에서는 Run/Pause/Stop이 시뮬 시간과
표적 움직임을 동시에 제어하는 것처럼 섞여 있었는데, v0.15에서 명확히 분리한다.

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Simulation Clock (바깥 레이어)                          │
│  • 시뮬 시간 자체를 제어                                         │
│  • 환경·레이더·Pipeline·포지셔너 동역학의 기반 시간              │
│  • Start / Pause / Stop + Speed Multiplier (×1/2/4/8)            │
│  • 상태: STOPPED / RUNNING / PAUSED                              │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ (Simulation이 RUNNING일 때만 아래 레이어 의미 있음)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 2: Target Run (안쪽 레이어)                                │
│  • 표적 trajectory 재생만 제어                                   │
│  • Run / Pause / Stop                                            │
│  • 상태: IDLE / RUNNING / PAUSED / ENDED                         │
└─────────────────────────────────────────────────────────────────┘
```

두 레이어는 독립이다. 예를 들어:

- **Sim RUNNING + Target IDLE**: 환경·레이더는 동작, 표적은 정지 상태 (Pre-Run 상태 — Run 시작 전 FFT 관찰 가능)
- **Sim RUNNING + Target RUNNING**: 모든 것이 진행 중 (정상 Run)
- **Sim PAUSED + Target RUNNING**: 시뮬 시간이 멈춰 있어 실제로 아무것도 안 움직임 — 이 상태 의미 있음 (frame-by-frame 분석)
- **Sim STOPPED + Target *** : 시뮬이 리셋됐으므로 Target도 강제로 IDLE로

#### Layer 1: Simulation Clock

```python
class SimulationState(Enum):
    STOPPED = "stopped"     # 시뮬 시간 정지, 모든 것이 초기 상태
    RUNNING = "running"     # 시뮬 시간 흐름, 모든 물리 진행
    PAUSED = "paused"       # 시뮬 시간 정지, 상태는 보존 (재개 가능)


class SpeedMultiplier(Enum):
    """시뮬 시간을 wall clock 대비 몇 배로 진행할지.
    ×1이면 real-time, ×2 이상이면 레이더 계산을 wall clock보다 빠르게 수행 ('시간 와프').
    실제 달성 배수는 계산량에 따라 설정 배수보다 낮을 수 있음.
    """
    X1 = 1.0
    X2 = 2.0
    X4 = 4.0
    X8 = 8.0


@dataclass(frozen=True)
class SimulationClock:
    """Layer 1. 시뮬 시간의 주인.

    상태 전이:
      STOPPED ─[Start]─▶ RUNNING
      RUNNING ─[Pause]─▶ PAUSED ─[Start]─▶ RUNNING
      RUNNING ─[Stop]──▶ STOPPED (리셋)
      PAUSED  ─[Stop]──▶ STOPPED (리셋)
    """
    state: SimulationState
    sim_t_s: float                      # 시뮬 시간 (정지·일시중지 상태에서도 값은 유지)
    session_wall_start_utc: datetime    # Session 시작 wall clock
    speed_multiplier: SpeedMultiplier   # ×1/2/4/8

    # 실제 달성 배수 (계산 능력에 따라 설정보다 낮을 수 있음)
    actual_multiplier: float            # 예: 8.0 설정했지만 실제 3.7x만 나오면 3.7
```

#### Layer 2: Target Run Clock (v0.14에서 용어 변경)

```python
class RunState(Enum):
    """Target trajectory 재생 상태."""
    IDLE = "idle"              # Scenario 로드됨, 표적 정지, Run 시작 대기
    RUNNING = "running"        # 표적 재생 중 (Sim이 RUNNING일 때만 실질 진행)
    PAUSED = "paused"          # 표적 일시정지
    ENDED = "ended"            # trajectory 자연 종료


@dataclass(frozen=True)
class RunClock:
    """Layer 2. 표적 trajectory 재생 시간.
    Sim Clock과 독립적 상태 머신이지만, Sim이 PAUSED/STOPPED면 실제 진행하지 않음.
    """
    run_id: str
    run_started_at_sim_t_s: float       # Sim 시간축에서 이 Run이 시작된 시점
    run_t_s: float                      # Run 시작 후 경과 시간 (Sim이 진행할 때만 증가)
    state: RunState
```

**중요**: `run_t_s`는 **Sim 시간 기반**. Sim이 Pause 상태면 `run_t_s`도 증가 안 함.
Wall clock이 아니라 시뮬 시간을 기준으로 trajectory 재생.

#### 두 레이어 상호작용 규칙

| 상황 | 동작 |
|---|---|
| Sim STOPPED + Target Run 버튼 | **자동으로 Sim Start 후 Target Run** (편의) |
| Sim PAUSED + Target Run 버튼 | **자동으로 Sim Start 후 Target Run** (편의) |
| Sim Stop | Target 상태도 IDLE로 강제 리셋 (Run 결과 저장 여부 다이얼로그) |
| Sim Pause | Target은 현재 상태 유지 (RUNNING이었으면 계속 RUNNING 상태 flag, 실제 진행만 멈춤) |
| Target Run 중 Sim Pause | Target state=RUNNING 유지, 실제 trajectory는 Sim과 함께 멈춤 |
| Target Stop 중 Sim Pause | 이미 정지 상태, 영향 없음 |

#### Speed Multiplier 의미

**"시간이 와프된 것처럼"** — 내부 틱 간격은 유지하되 wall clock보다 빠르게 실행.

```python
# 개념적 루프 (실제 구현은 이벤트 기반)
while sim_clock.state == RUNNING:
    tick_dt = 1.0 / TICK_HZ           # 예: 0.01s (100Hz)
    process_frame(dt=tick_dt)          # 레이더·환경·포지셔너 다 계산
    sim_clock.sim_t_s += tick_dt

    # wall clock과 동기화
    expected_wall_elapsed = (sim_t_s - start_sim_t) / speed_multiplier
    actual_wall_elapsed = time() - start_wall_t
    if actual_wall_elapsed < expected_wall_elapsed:
        sleep(expected_wall_elapsed - actual_wall_elapsed)
    # 못 따라가면 sleep 안 하고 바로 다음 틱 (actual_multiplier < 설정값)
```

계산량이 많은 Plugin(무거운 NN 추론 등)이 있으면 x8 설정해도 실제로 x3 밖에 안 나올 수 있음.
UI에는 **actual multiplier** 병기 (`x8 → actual x3.2`).

#### Simulation Pause 중 동작 규칙

- **레이더 물리**: 완전 정지 (Pipeline 호출 없음, 환경 업데이트 없음, 포지셔너 동역학 없음)
- **UI 입력 (방향키 수동 조작)**: **버퍼링** — 사용자가 방향키 누르면 "재개 시 이만큼 돌려라" 큐에 축적
- **UI 관찰성 (Stage I/O 스크롤, 히스토리 조회 등)**: 정상 동작 (레이더 정지와 무관)
- Sim Start하면 버퍼링된 입력이 한번에 반영되어 포지셔너가 그 방향으로 회전 시작

```python
@dataclass
class BufferedInputs:
    """Sim Pause 중 누적된 사용자 입력. Sim Start 시 반영."""
    positioner_delta_az_deg: float = 0.0
    positioner_delta_el_deg: float = 0.0
    # 기타 버퍼링 가능 입력들
```

---


### 3.5.0d Environment vs Scenario의 생애주기 분리

```python
@dataclass(frozen=True)
class EnvironmentState:
    """Sim Clock에 연동. Sim이 RUNNING일 때만 업데이트."""
    sim_t_s: float                      # Sim 시간 (Simulation Clock의 sim_t_s와 일치)
    wind_speed_mps: float               # 바람 (시간에 따라 변화 가능)
    wind_direction_deg: float
    sea_state: int                      # 파도
    platform_roll_deg: float            # 자함 roll (파도에 의한 흔들림)
    platform_pitch_deg: float           # 자함 pitch
    # 미래 확장: weather_profile, etc.

@dataclass(frozen=True)
class ScenarioRuntimeState:
    """Scenario 로드~언로드 생애주기. Target Run 상태와 함께 동작.

    Target state = IDLE/PAUSED/ENDED: 표적 정지
    Target state = RUNNING + Sim state = RUNNING: 표적 trajectory 재생
    Target state = RUNNING + Sim state = PAUSED: 표적 실질 정지 (Sim이 멈춰서)
    """
    scenario_name: str
    run_state: RunState
    targets_current_positions: tuple[TargetCurrentState, ...]

@dataclass(frozen=True)
class TargetCurrentState:
    """각 표적의 현재 상태 (정지/이동)."""
    target_id: int
    east_m: float
    north_m: float
    z_m: float
    heading_deg: float
    is_moving: bool                     # False면 정지 (IDLE/PAUSED/ENDED 또는 Sim PAUSED)
    roll_deg: float                     # 파도에 의한 자세 (정지 중에도 흔들림, Sim RUNNING일 때만)
    pitch_deg: float
```

**핵심 변경 (v0.15)**: 기존 `SessionClock.current_t_s`를 `SimulationClock.sim_t_s`로 대체.
Session 시간(wall clock 기반)과 Sim 시간(시뮬 내부 시간)은 다른 개념이며, 이전 v0.14의
`SessionClock`은 Sim 시간과 wall clock을 혼용했음. v0.15는 **Sim 시간**이 모든 물리의 기반임을 명확히 한다.

---

## 3.5 Evaluation Run

### 3.5.1 Run 정의

한 번의 평가 실행 단위.

```python
class RunMode(Enum):
    """Workbench의 두 운용 모드 중 어느 것으로 실행된 Run인지."""
    DSP = "dsp"                         # DSP 모드: 추적 성능 평가
    NN_STEP1_DATASET = "nn_step1"       # NN 모드 Step 1: 학습 데이터 추출
    NN_STEP2_EVAL = "nn_step2"          # NN 모드 Step 2: NN 평가

@dataclass(frozen=True)
class RunConfig:
    """DSP 모드의 Run 설정."""
    mode: RunMode = RunMode.DSP         # 🆕 어느 모드의 Run인지
    scenario_name: str
    scenario_version: str
    plugins: dict[str, PluginRef]       # "detector" → ref("./my_det.py", version)
    probe_config: ProbeConfig
    seed: int
    metric_config: MetricConfig

    # 선택 표적 지정 (None이면 Scenario.primary_target_id 사용)
    # 시나리오 기본값을 덮어쓰려면 여기에 target_id 지정
    primary_target_id_override: int | None = None

    # 옵션: Target Gate 런타임 enable (Tracker가 요구해도 사용자가 끌 수 있음)
    target_gate_enabled: bool = True

    # 🆕 초기 포지셔너 위치 정책 (v0.14)
    initial_positioner_policy: InitialPositionerPolicy = (
        InitialPositionerPolicy.SCENARIO_DEFAULT
    )
    # SCENARIO_DEFAULT: 시나리오에 정의된 기본 방향으로 자동 배치
    # KEEP_CURRENT: 현재 포지셔너 방향 유지 (사용자가 방향키로 잡아둔 상태)

    # 🆕 수동 조작 허용 여부 (v0.14)
    # True면 Run 중에도 사용자가 AUTO↔MANUAL 토글 가능
    # False면 Run 시작하면 AUTO 고정 (엄격 평가 모드)
    allow_manual_positioner_during_run: bool = True


class InitialPositionerPolicy(Enum):
    SCENARIO_DEFAULT = "scenario_default"   # 시나리오 정의 기본 포지션
    KEEP_CURRENT = "keep_current"           # 현재 위치 유지 (사용자 수동 조작 결과)


@dataclass(frozen=True)
class PluginRef:
    path: Path
    class_name: str
    version: str
    source_hash: str                    # 재현성 — 파일 내용 해시
```

### 3.5.1b Run 결과 종료 상태 (v0.14)

`RunResult`에 종료 이유가 추가됨:

```python
@dataclass(frozen=True)
class RunResult:
    run_id: str
    config: RunConfig

    # 🆕 종료 상태 (v0.14)
    termination: RunTerminationReason   # COMPLETED / ABORTED / ERROR
    duration_s: float                   # 실제 진행된 Run 시간
    aborted_at_run_t_s: float | None    # Stop으로 중단된 경우 그 시각

    # 메트릭·데이터
    metrics: Metrics
    trace_path: Path | None             # Trace 파일 (있으면)
    manifest_path: Path                 # 재현용 Manifest
```

**Stop 시 사용자 선택**:
- "저장" → `termination=ABORTED`, `RunResult` 저장됨. Run 비교 등에서 "중단된 Run" 으로 표시
- "폐기" → `RunResult` 생성 안 됨. Trace·메트릭 파일 작성하지 않고 종료

### 3.5.1b.1 Run Manifest 스키마 (v0.20 — 자원 hash 추가)

Run Manifest는 **재현성의 핵심 기록**. 실행 시 사용된 모든 자원의 content hash를 담아
나중에 동일 조건 재실행 가능성을 검증.

```python
@dataclass(frozen=True)
class RunManifest:
    """재현용 Manifest. runs/<run_id>/manifest.toml 로 저장."""
    run_id: str
    started_at: datetime
    completed_at: datetime | None
    termination: RunTerminationReason

    workbench_version: str              # 예: "0.20"

    # Scenario 참조
    scenario_id: str
    scenario_hash: str                  # scenario.toml의 content hash

    # 자원 참조 (v0.20)
    resource_refs: ResourceRefs

    # Plugin 참조 (v0.14에서 도입, v0.20에서 manifest로 포함)
    plugins: dict[str, PluginRef]       # stage_name → PluginRef

    # Simulation 설정
    seed: int
    speed_multiplier_at_start: SpeedMultiplier
    initial_positioner_policy: InitialPositionerPolicy

    # Run 경과
    duration_s: float
    aborted_at_run_t_s: float | None


@dataclass(frozen=True)
class ResourceRefs:
    """Run 실행 시점에 사용된 자원들의 ID + content hash."""
    map_id: str
    map_hash: str                       # "sha256:..."

    radar_id: str
    radar_hash: str

    targets_id: str
    targets_hash: str
```

**재실행 검증 로직**:

```python
def verify_reproducibility(manifest: RunManifest, library: ResourceLibrary) -> VerifyResult:
    """현재 라이브러리가 Manifest와 동일 상태인지 확인."""
    mismatches = []
    for res_type in ["map", "radar", "targets"]:
        current_hash = library.get_current_hash(res_type, getattr(manifest.resource_refs, f"{res_type}_id"))
        manifest_hash = getattr(manifest.resource_refs, f"{res_type}_hash")
        if current_hash != manifest_hash:
            mismatches.append(ResourceMismatch(res_type, manifest_hash, current_hash))

    return VerifyResult(
        reproducible=(len(mismatches) == 0),
        mismatches=mismatches,
    )
```

상세 동작은 [10 § 10.10.5](10_workspaces.md#10105-과거-run-재실행-시-동작).

### 3.5.1c 포지셔너 지휘 경로의 유일성 (Single Command Path)

Tracker가 GT를 안 봐도, 만약 Positioner가 GT를 직접 구독한다면 전체 시스템은 여전히 cheating.
이를 막기 위해 **포지셔너 명령의 유일한 출처**를 타입으로 강제한다.

```python
class CommandSource(Enum):
    TRACKER = "tracker"             # 자동 추적 — 정상 경로
    MANUAL_USER = "manual"          # 방향키 수동 조작
    INITIAL_SCAN = "scan"           # Run 시작 자동 배치, 초기 scan 패턴 등

@dataclass(frozen=True)
class PositionerCommand:
    """포지셔너 목표 각도. 이 타입을 거치지 않으면 포지셔너는 안 움직인다.

    CommandSource.TRACKER일 때는 반드시 source_track_id·source_frame_id를 제공해야 하며,
    Run 후 검증에서 실제 그 프레임 Tracker 출력에 해당 트랙이 있었는지 확인된다.
    """
    az_deg: float
    el_deg: float
    source: CommandSource

    # TRACKER일 때 필수 (다른 source는 None)
    source_track_id: int | None = None
    source_frame_id: int | None = None

    # 메타
    issued_at_session_t_s: float        # 언제 발행됐나


class PositionerController(Protocol):
    """포지셔너 제어 Contract. set_target의 인자 타입이 PositionerCommand로 고정되어
    GT에서 직접 오는 경로를 타입 레벨에서 차단.
    """
    def set_target(self, cmd: PositionerCommand) -> None: ...
    def get_state(self) -> JointState: ...
    def step(self, dt: float) -> JointState: ...
```

**원칙**:
1. Positioner는 `PositionerCommand` 객체로만 지시받음
2. `CommandSource.TRACKER` 명령은 반드시 Track에서 파생된 증거를 가짐
3. GT·Scenario에서 직접 `PositionerCommand`를 만드는 코드는 CI에서 차단 (06 § 6.3)
4. Run 후 검증에서 모든 `TRACKER` 명령의 `source_track_id`가 실제 Tracker 출력에 있었는지 확인

### 3.5.1d GT 격리 강화 (v0.14)

계획서 v0.13까지는 "GT는 Plugin에 전달 안 함" 수준(Level 2)이었으나, 사용자 실수로 GT가
플러그인에 흘러갈 가능성을 막기 위해 **Level 3 정적 스캔**을 추가:

```python
# Plugin 로드 시 자동 실행되는 검증
FORBIDDEN_SYMBOLS = [
    # GT 관련
    "GroundTruth", "GTLoader", "GTTarget",
    "ground_truth", "true_range", "true_az", "true_el", "true_velocity",
    "is_visible", "is_in_beam",
    # Primary 정보
    "primary_target_id",
]

SUSPICIOUS_FILE_ACCESS = [
    r"scenarios/.*\.csv",               # 시나리오 파일 직접 접근
    r"ground_truth",                    # GT 파일
]

ALLOWED_PLUGIN_LOCAL_FILES = [
    r"^plugins/[^/]+/weights/.*\.npz$",  # 자기 폴더 가중치
    r"^plugins/[^/]+/lookup/.*\.csv$",   # 자기 폴더 참조 테이블
]
```

**운용**:
- **Plugin Manager 로드 시**: 의심 패턴 발견 시 **경고** 표시 (사용자가 의식적으로 허용하면 진행)
- **공식 Compare Run**: 의심 패턴 발견 시 **거부** — 공식 메트릭 비교에 오염 차단
- **CI 테스트**: 거부

**GT Contamination Check** (MVP+α, 휴리스틱):

```python
def check_gt_contamination(trace: Trace, gt: GroundTruth) -> ContaminationReport:
    """Run 결과가 너무 완벽하면 의심.
    - 검출 위치가 GT와 거의 100% 일치
    - 노이즈 시나리오에서도 RMSE ≈ 0
    - 추적 Continuity = 1.0 (한 번도 안 끊김)
    """
    ...
```

상세: [06 § 6.3 테스팅](06_topics.md#63-테스팅-전략)

---

### 3.5.1a NN 모드 Step 2 — NN Evaluation

NN 모드 Step 2에서는 RunConfig 대신 **NNEvalJob**을 사용.
Scenario를 여러 개 돌려 여러 Error를 한 번에 집계.

```python
@dataclass(frozen=True)
class NNEvalJob:
    """NN 모드 Step 2: 학습된 NN Plugin을 평가.

    Training/Dev/Test 셋으로 분리된 Dataset(들)과 NN Plugin을 받아
    4-error 분석 결과를 산출.
    """
    job_id: str
    nn_plugin: PluginRef                # 평가 대상 NN (.py + weights)

    # 3개 데이터셋 (필수)
    training_dataset: Path              # 학습에 사용된 셋
    dev_dataset: Path                   # 검증셋 (하이퍼파라미터 튜닝용)
    test_dataset: Path                  # 미지 시나리오

    # Bayes error 추정 (선택적, 고급 모드)
    bayes_estimator: BayesEstimator | None = None

    # Variant 격자 분석 (있으면 각 Variant에서의 성능도 기록)
    variant_datasets: dict[str, Path] | None = None
    # 예: {"A_ideal": ..., "B_attitude": ..., "C_sidelobe": ..., "D_full": ...}


@dataclass(frozen=True)
class BayesEstimator:
    """Bayes error 추정 방법. 선택적."""
    method: str                         # "variant_a" / "human_label" / "large_model"
    reference_dataset: Path | None      # 예: Variant_A dataset
    reference_value: float | None       # 직접 수치 제공 (사람이 추정한 경우)


@dataclass(frozen=True)
class NNEvalResult:
    """NN 평가 결과 — 4-error 분석."""
    job_id: str
    nn_plugin_ref: PluginRef

    # 핵심 4 error (Bayes는 선택적)
    bayes_error: float | None
    training_error: float
    dev_error: float
    test_error: float

    # 진단 결과 — 위 error들 간의 gap 해석
    # avoidable_bias = training - bayes (bayes가 있을 때만)
    # variance = dev - training
    # data_mismatch = test - dev
    avoidable_bias: float | None
    variance: float
    data_mismatch: float

    # 진단 서술 (Workbench가 자동 생성)
    # 예: "Variance 큼 → overfitting, Dev set 늘리거나 regularization"
    diagnosis_hint: str

    # Variant 격자 결과 (있으면)
    variant_errors: dict[str, float] | None

    # 메타
    loss_fn_name: str                   # "pairing_cross_entropy" 등
    metric_unit: str                    # "fraction" / "percent" / "rmse" 등
```

@dataclass(frozen=True)
class RunResult:
    run_id: str                         # UUID
    config: RunConfig
    started_at: datetime
    ended_at: datetime
    metrics: Metrics
    trace_path: Path                    # 별도 저장된 Trace 파일
    status: str                         # "success" / "failed" / "cancelled"
    error: str | None

    # 파이프라인 매니페스트 — 어느 slot이 NN이고 어느 것이 기본인지
    # 원칙 6(NN 부분 교체) 지원의 저장소 레벨 반영
    # 세부: 07 § 7.6.4
    pipeline_manifest: dict[str, SlotManifest]
```

```python
@dataclass(frozen=True)
class SlotManifest:
    """한 Pipeline Slot에 대한 Run 시점 구성 기록."""
    slot_id: str                        # "pairing", "detector" 등
    plugin_name: str                    # "default_pairing" or "my_pairing_nn"
    plugin_version: str
    is_nn: bool                         # NN Plugin이면 True
    weights_hash: str | None            # NN일 때만
    training_dataset_ref: str | None    # NN일 때만, 학습에 쓴 Dataset 식별자
```

### 3.5.2 메트릭 목록 (MVP)

```python
@dataclass(frozen=True)
class Metrics:
    """Run의 성능 지표.

    본 Workbench는 '선택 표적 안정 추적'이 최우선 목표이므로,
    메트릭도 그 구조를 따른다:
      - primary_target: 선택 표적 기준 (가장 중요)
      - secondary_targets: 다른 표적 기준 (멀티 타겟 혼선 여부 평가용)
      - overall: 전체 탐지 성능 (보조)
      - system: 성능/건전성
    """

    # ── 선택 표적 기준 (🎯 최우선 지표) ──
    primary: PrimaryTargetMetrics

    # ── 다른 표적 기준 ──
    secondary: tuple[SecondaryTargetMetrics, ...]

    # ── 전체 탐지 (보조 지표) ──
    overall: OverallDetectionMetrics

    # ── 시스템 ──
    system: SystemMetrics


@dataclass(frozen=True)
class PrimaryTargetMetrics:
    """선택 표적 하나에 대한 추적 품질."""
    target_id: int

    # 추적 연속성
    track_continuity: float             # 0~1, 전체 프레임 중 트랙이 살아있던 비율
    longest_lock_s: float               # 가장 길게 유지된 lock 구간 (초)
    lock_acquisition_time_s: float      # Run 시작 ~ 첫 lock까지 걸린 시간
    lost_count: int                     # 트랙이 끊긴 횟수
    id_switch_count: int                # ID가 다른 표적으로 바뀐 횟수 (낮을수록 좋음)

    # 추적 정확도 (lock 기간 동안만 집계)
    range_rmse_m: float
    velocity_rmse_mps: float
    az_rmse_deg: float
    el_rmse_deg: float

    # 포지셔너 추종 품질 (Closed-Loop 특성)
    positioner_az_lag_mean_deg: float   # 포지셔너 위치와 GT 위치의 AZ 오차 평균
    positioner_el_lag_mean_deg: float
    positioner_az_lag_max_deg: float    # 최악 순간 (예: 교차 시)
    positioner_el_lag_max_deg: float
    in_beam_ratio: float                # 선택 표적이 TX 빔 내에 있었던 비율


@dataclass(frozen=True)
class SecondaryTargetMetrics:
    """선택되지 않은 다른 표적들의 추적 상태.
    선택 표적 추적에 방해가 되었는지 평가용."""
    target_id: int
    track_continuity: float
    crossed_primary_at_frame: int | None  # 선택 표적과 공간적으로 교차한 순간


@dataclass(frozen=True)
class OverallDetectionMetrics:
    """전체 탐지 성능 (선택 표적 포함 모든 GT 대비)."""
    pd: float                           # detection probability
    pfa: float                          # false alarm rate


@dataclass(frozen=True)
class SystemMetrics:
    """계산 성능 및 시뮬 건전성."""
    total_frames: int
    avg_stage_ms: dict[str, float]      # 스테이지별 평균 처리 시간
    physics_warnings: tuple[str, ...]   # Physics Gate가 낸 경고
```

### Metrics 설계 포인트

- **`primary`가 최우선**: Run 결과 비교 UI도 이걸 상단에 배치
- **`secondary`는 혼선 평가용**: "다른 표적 때문에 선택 표적이 흔들렸는지" 판단 근거
- **`positioner_*_lag`**: Closed-Loop 추적 레이더 특유의 품질 지표. 동역학이 느려 표적을 놓치는지 확인
- **`overall.pd/pfa`는 MVP에서도 유지**: 탐지 단계의 건전성 확인용. 하지만 이것만 좋아도 의미 없음 — 추적이 중요

### ID Switch 판정 규약

ID Switch는 **선택 표적의 관점**에서 정의:
- 프레임 t에서 "track #5 = primary target"
- 프레임 t+1에서 "track #5 = different GT target"
- → id_switch_count += 1

GT와 Track의 연관은 **최근접 매칭(Hungarian 등)**으로 판정. 정확한 규약은 Evaluator 구현체가 담당.

### 3.5.3 Run 저장 구조

```
~/.workbench/runs/
├── 20260422_143501_a_base_mydet/      ← 타임스탬프 + 시나리오 + 플러그인
│   ├── run.json                       ← RunResult
│   ├── trace.h5                       ← Trace (선택적)
│   ├── metrics.json                   ← 빠른 조회용 요약
│   └── plugins/                       ← 사용된 플러그인 스냅샷 (재현용)
│       └── my_detector.py
└── ...
```

**중요**: 플러그인 소스 자체를 Run 디렉토리에 복사 저장.
사용자가 원본을 수정해도 이 Run은 항상 같은 코드로 재실행 가능.

---

## 3.6 물리 검증 데이터 (Golden Dataset)

테스팅 전략은 06에서 자세히 다루지만, 데이터 구조만 여기 정리.

```python
@dataclass(frozen=True)
class GoldenCase:
    """한 물리 영역의 한 테스트 케이스."""
    domain: str                         # "radar_equation" / "fmcw" / "multipath" ...
    case_id: str                        # "case_001_far_field"
    description: str

    inputs: dict[str, Any]              # 입력 파라미터
    expected_outputs: dict[str, Any]    # 기대값
    tolerances: dict[str, float]        # 허용 오차

    references: tuple[str, ...]         # "Skolnik Ch.2", "doi:..."

@dataclass(frozen=True)
class GoldenReport:
    case: GoldenCase
    actual_outputs: dict[str, Any]
    passed: bool
    deltas: dict[str, float]
```

저장 위치: `tests/physics/golden/<domain>/<case_id>.toml`

---

## 3.7 Event Bus 메시지 카탈로그

App 전반에서 사용되는 이벤트 목록.

| Event | Payload | Emitter | Listener (예) |
|---|---|---|---|
| `scenario.loaded` | Scenario | ScenarioService | 3D View, Explorer |
| `scenario.unloaded` | None | ScenarioService | 모든 패널 |
| **Simulation Clock (Layer 1, v0.15)** | | | |
| `sim.started` | None | SimulationClock | UI 툴바, StatusBar |
| `sim.paused` | None | SimulationClock | UI 툴바, StatusBar |
| `sim.stopped` | None | SimulationClock | UI 툴바, StatusBar, RunManager |
| `sim.speed_changed` | SpeedMultiplier, actual | SimulationClock | UI 툴바 |
| `sim.tick` | sim_t_s | SimulationClock | ProbeRecorder |
| `sim.frame_complete` | TraceFrame | Simulation | 3D View, FFT, Stage I/O |
| **Target Run (Layer 2, v0.14)** | | | |
| `target.run.started` | RunConfig, RunClock | RunManager | Run Panel |
| `target.run.paused` | None | RunManager | Run Panel |
| `target.run.progress` | run_t_s, total | RunManager | Run Panel |
| `target.run.completed` | RunResult | RunManager | Run Panel, Notifications |
| `target.run.aborted` | RunResult (termination=ABORTED/SIM_STOPPED) | RunManager | Run Panel |
| **Command & Positioner (v0.14)** | | | |
| `command.published` | PositionerCommand | CommandBus | Trace, Lineage 검증 |
| `positioner.mode_changed` | "AUTO" / "MANUAL" | CommandBus | UI 툴바, 3D View |
| **Plugin & Physics** | | | |
| `plugin.registered` | PluginRef | PluginLoader | Plugin Manager |
| `plugin.error` | PluginRef, Exception | Plugin Runtime | Notifications |
| `plugin.scan_warning` | ScanFinding | PluginScanner | Plugin Manager (v0.14) |
| `physics_gate.warning` | PhysicsWarning | PhysicsGate | Physics Panel, Notifications |

### 이벤트 설계 원칙

- 이벤트는 **과거형** (`loaded`, `completed`) — "이미 일어난 일"의 통보
- Command는 **명령형** (`load`, `run`) — Event와 구분
- 이벤트 payload는 **불변 객체** — 구독자가 수정할 수 없어야 함
- 네임스페이스는 `sim.*`(Layer 1), `target.*`(Layer 2)로 분리 (v0.15)

---

## 섹션 상태

- 3.1 철학 — ✅
- 3.2 Scenario — 🟡 (세부 필드는 구현 중 조정 가능)
  - 3.2.1a Platform — ✅ (v0.18)
  - 3.2.1b Platform과 EnvironmentState — ✅ (v0.18)
  - 3.2.1c Map & Workbench Native Terrain — ✅ (v0.21~v0.22)
  - 3.2.1d Placement & Motion — ✅ (v0.21)
  - 3.2.1e Wave Response — ✅ (v0.21)
  - 3.2.1f Building Anchor — ✅ (v0.21)
  - 3.2.1g Target Trajectory — ✅ (v0.21, v0.27 의미 재정의 — reference)
  - 3.2.1h Antenna Configuration — ✅ (v0.25, 파라볼릭+평면어레이+모노펄스 4ch)
  - 3.2.1i Dynamics State — ✅ (v0.27, RigidBodyState + AIRCRAFT/POWERED_FLIGHT/BALLISTIC dynamics)
- 3.3 Contract — ✅ (가장 중요한 결정)
- 3.4 Probe — 🟡
- 3.5 Run — 🟡
  - 3.5.1b.1 RunManifest + ResourceRefs — ✅ (v0.20)
- 3.6 Golden — ⏳ (물리 검증 섹션과 연계)
- 3.7 Event Bus — 🟡

---

👉 다음 섹션: [04_migration.md](04_migration.md)
