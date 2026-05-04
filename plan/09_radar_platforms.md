# 09. Radar Platforms & Installation

**최종 갱신**: 2026-04-28 (v0.35)

**관련 문서**: [01 vision_scope](01_vision_scope.md), [03 data_model § Platform](03_data_model.md), [05 ui_ux § 5.3.8 Installation](05_ui_ux.md), [06 topics § Deferred Physics](06_topics.md)

## 9.1 왜 이 문서가 있나

v0.17까지 계획서는 레이더가 **"자함(ownship)" — 해상 이동 플랫폼**에 탑재된다는 것을
암묵적으로 전제했다. 자함 동요(roll/pitch)가 MVP 물리 4종 중 하나로 포함된 것이 그 단서다.

하지만 실제 추적 레이더는 여러 플랫폼에 설치된다:

- 함선 탑재 (해상 이동)
- 차량 탑재 (지상 이동, MVP 후)
- 건물 옥상 / 타워 / 산정상 (지상 고정)

플랫폼에 따라 **추적 성능을 결정하는 조건**이 크게 달라진다:

- 설치 고도 → 수평선·지평선 한계, 저고도 표적 가시성
- 주변 지형·건물 → 빔 차폐, 멀티패스 반사
- 플랫폼 운동 → 함선 동요로 인한 포지셔너 보정 부담 vs 건물 정지
- 플랫폼 형상 → 자체 반사 (self-reflection), 안테나 높이

이 문서는 v0.18에서 도입되는 **플랫폼 다양화**의 설계 근거와 MVP 범위를 정리한다.

## 9.2 MVP 플랫폼 범위

MVP는 두 플랫폼 카테고리를 지원:

| 카테고리 | 포함 | MVP 구현 |
|---|---|---|
| **Maritime** (해상 이동) | 함선 (자함) | ✅ v0.1부터 있던 것. Sea State 기반 roll/pitch |
| **Fixed Ground** (고정 지상) | 건물 옥상, 타워, 산정상 | ✅ v0.18에서 신규. 운동 없음 |
| ~~Vehicle~~ (지상 이동) | ~~차량~~ | ❌ MVP 후. 주행 진동 모델 필요 |
| ~~Airborne~~ (공중) | ~~항공기~~ | ❌ Deferred Physics |

"고정 지상형"은 건물·타워·산정상을 **구분하지 않고** 하나의 플랫폼 카테고리로 묶는다.
레이더 관점에서 이들의 차이는 "설치 고도"와 "주변 차폐 형상"으로 수렴하며, 고유한 운동 모델이
필요없다. 구분이 필요한 미래 시점에는 서브타입으로 분리.

## 9.3 Platform Contract

플랫폼은 다음 네 가지 속성을 가진다:

```python
from typing import Protocol
from dataclasses import dataclass

class PlatformCategory(Enum):
    MARITIME = "maritime"               # 해상 이동 (함선)
    FIXED_GROUND = "fixed_ground"       # 지상 고정 (건물·타워·산정상)
    # 미래:
    # VEHICLE = "vehicle"
    # AIRBORNE = "airborne"


@dataclass(frozen=True)
class RadarPlatform:
    """레이더가 설치되는 플랫폼의 정의.
    Scenario 파일 [platform] 섹션에 해당.

    v0.21+: PlacedEntity 와 동일한 추상 위에 있음 — § 9.4.3 매핑 참조.
    """
    platform_id: str                    # 예: "corvette_500t", "building_rooftop"
    category: PlatformCategory
    display_name: str                   # UI 표시용

    # 설치 위치 (ENU 로컬 좌표, Scenario의 원점 기준)
    install_east_m: float
    install_north_m: float
    install_altitude_m: float           # DEM + 구조물 높이

    # 초기 안테나 보어사이트 방향
    initial_az_deg: float
    initial_el_deg: float

    # 운동 종류 (v0.21 신설) — § 9.4.3 매핑
    motion_kind: MotionKind             # FIXED_GROUND / SURFACE_VESSEL / FLOATING_STATIC / ...
                                        # category에서 자동 추론 가능 (FIXED_GROUND → FIXED_GROUND,
                                        # MARITIME 기본값 → FLOATING_STATIC)

    # 운동 모델 참조 (9.4 참조)
    motion_model: str                   # 예: "sea_state", "stationary"
    motion_params: dict                 # 모델별 파라미터 (wave_response 등 포함)

    # 형상 (3D 렌더링·self-reflection용)
    mesh_path: Path | None              # STL/OBJ. None이면 카테고리 기본 메시
    antenna_height_above_base_m: float  # 플랫폼 바닥에서 안테나까지

    # (MVP+α) 자체 반사·차폐 영역
    self_occlusion_cone_deg: float | None  # 플랫폼 자체가 가리는 원뿔 (예: 후방 mast)
```

## 9.4 Platform Motion Model (추상화)

> ⚠️ **v0.27 정합**: 본 섹션의 PlatformMotionModel (sea_state·stationary)은 v0.18 사고.
> v0.27 Dynamics 도입 (14 dynamics_model) 후 다음 통합 필요:
>
> - **MotionKind 7** (14 § 14.5, 03 § 3.2.1d): MARITIME → SURFACE_VESSEL(운항)/FLOATING_STATIC(정박),
>   FIXED_GROUND → FIXED_GROUND
> - **WaveResponseModel** (03 § 3.2.1e, v0.21): sea_state는 환경(SeaStateEnvironment),
>   플랫폼은 wave_response 프리셋 (large_ship/small_boat/buoy/none) 으로 응답
> - **RigidBodyState** (03 § 3.2.1i, v0.27): 함선·차량 동요는 6DOF 상태로 통합 가능 (MVP+α)
>
> 본 섹션의 MotionModel은 MVP 추상으로 유효. v0.27 통합은 09 § 9.4.3 매핑 표 참조.

운동 특성은 **설정에서 지정, 구현은 추상화**하는 구조:

```python
class PlatformMotionModel(Protocol):
    """플랫폼의 6자유도 운동을 Sim 시간에 따라 제공.

    Run 여부와 무관하게 Sim이 RUNNING이면 매 틱 업데이트.
    이 출력이 RadarPipeline의 기준 좌표계를 결정.
    """

    name: str                           # "sea_state_4", "stationary", ...

    def configure(self, params: dict) -> None: ...

    def update(self, sim_t_s: float) -> PlatformPose:
        """현재 시뮬 시각의 플랫폼 자세.
        플랫폼 설치 위치 자체는 고정이므로 여기선 회전(roll/pitch/yaw)만.
        """
        ...


@dataclass(frozen=True)
class PlatformPose:
    roll_deg: float                     # 좌우 기울어짐
    pitch_deg: float                    # 앞뒤 기울어짐
    yaw_deg: float                      # 수평 회전 (해상에서는 선회, 지상 고정은 0)

    # 미래: linear velocity (차량용)
    velocity_east_mps: float = 0.0
    velocity_north_mps: float = 0.0
    velocity_up_mps: float = 0.0
```

### 9.4.1 MVP에 포함되는 운동 모델

**`sea_state`** (Maritime 카테고리의 기본)
- 기존 자함 동요 모델. Sea State (0~9)에 따라 sinusoidal roll/pitch
- 파라미터: `sea_state`, `dominant_period_s`, `amplitude_deg`
- 해상 플랫폼은 기본값으로 이 모델 사용

**`stationary`** (Fixed Ground 카테고리의 기본)
- 움직이지 않음. roll/pitch/yaw = 0, velocity = 0
- 파라미터: 없음
- 지상 고정 플랫폼은 기본값으로 이 모델 사용

### 9.4.2 MVP 후 운동 모델 (Deferred)

- **`sea_state_advanced`**: 6자유도 시뮬레이션 (heave/sway/surge 포함)
- **`road_vibration`** (Vehicle): 도로 상태 기반 수직 진동 + 노면 기울기
- **`wind_tower_sway`** (Fixed Ground 변형): 바람에 의한 타워 진동 (소폭)
- **`flight_path`** (Airborne): 외부 비행 궤적 입력

새 운동 모델은 `PlatformMotionModel` Protocol만 구현하면 추가됨. 플러그인화도 가능하지만
MVP는 내장만.

### 9.4.3 PlatformCategory ↔ MotionKind 매핑 (v0.21+ 정합)

v0.21에서 도입된 [`MotionKind`](12_placement_and_motion.md#123-motionkind--5-카테고리)는
**모든 배치 자원**(레이더 플랫폼 + 표적 + 건물)에 공통으로 적용되는 운동 추상화다. 따라서
v0.18의 `PlatformCategory`는 `MotionKind` 의 **부분집합**으로 해석된다.

#### 매핑 표

| PlatformCategory | 가능한 MotionKind | 운동 모델 (motion_model) | MVP |
|---|---|---|---|
| `MARITIME` | `SURFACE_VESSEL` (운항 중) | `sea_state` | ✅ |
| `MARITIME` | `FLOATING_STATIC` (정박) | `sea_state` (xy 고정) | ✅ |
| `FIXED_GROUND` | `FIXED_GROUND` | `stationary` | ✅ |
| `GROUND_VEHICLE` (미래) | `GROUND_VEHICLE` | `road_vibration` 등 | ❌ MVP 후 |
| `AIRBORNE` (미래) | `AIRCRAFT` / `POWERED_FLIGHT` / `BALLISTIC` | 동역학 모델 (14 참조) | ⚠ 표적은 MVP, 레이더 플랫폼은 MVP+α |

> **v0.27 변경**: 항공 motion_kind가 3종으로 분리됨 (AIRCRAFT / POWERED_FLIGHT / BALLISTIC).
> 표적은 사실적 동역학으로 시뮬되며 ([14_dynamics_model.md](14_dynamics_model.md)), 레이더 플랫폼이
> 항공기인 케이스는 MVP+α (운항 중 함정과 동일 이유 — 별도 platform_trajectory 필요).

#### MARITIME의 두 모드

레이더 플랫폼이 Maritime일 때 두 가지 운영 모드:

- **운항 중 (`SURFACE_VESSEL`)**: trajectory를 따라 이동 + wave 응답. 모바일 함정 기반 시나리오
- **정박 (`FLOATING_STATIC`)**: 위치 고정 + wave 응답. 정박 함정·해상 기지

Scenario `[platform]` 섹션에 명시:

```toml
[platform]
platform_id = "corvette_500t"
category = "maritime"
motion_kind = "floating_static"      # v0.21 신설 — 운항/정박 구분
motion_model = "sea_state"
motion_params = { sea_state = 4, dominant_period_s = 8.0,
                  wave_response = "large_ship" }   # v0.21 § 12.5 wave 응답 프리셋
```

MARITIME 카테고리지만 **운항 중**(SURFACE_VESSEL)이라면 trajectory 정보가 필요하므로 별도
`platform_trajectory.csv`를 같이 둔다. MVP에서는 거의 항상 `floating_static` (정박) — 운항
중 레이더는 MVP+α.

#### FIXED_GROUND의 motion_kind는 항상 동일

Fixed Ground 플랫폼은 `motion_kind = FIXED_GROUND` 로 자동 결정. 별도 명시 불필요.

```toml
[platform]
platform_id = "coastal_tower_50m"
category = "fixed_ground"
# motion_kind 명시 안 해도 FIXED_GROUND로 결정됨
motion_model = "stationary"
motion_params = {}
```

#### 표적과의 관계

표적도 동일한 `MotionKind` 체계를 사용한다 (12 § 12.7, 03 § 3.2.1g). 즉:

- 레이더와 표적이 **같은 운동 추상화** 위에 놓임
- 같은 wave 응답 모델을 공유 가능 (둘 다 `large_ship` 응답)
- 코드 재사용성 ↑

**플랫폼**과 **표적**의 차이는 motion_kind 자체보다 **자기가 추적하는가 / 추적당하는가**의 역할 차이.

#### Wave 응답은 별도 (v0.21 § 12.5 분리)

Maritime motion_model(`sea_state`)은 **파도 환경**을 정의하지만, **이 자원이 파도에 어떻게 반응하는가**(WaveResponseModel)는 별도 파라미터.

```toml
motion_params = {
    sea_state = 4,                      # 파도 환경 (Map의 SeaStateEnvironment 참조)
    wave_response = "large_ship",       # 이 함정의 응답 (12 § 12.5.2 프리셋)
}
```

함정·어선·부표 같이 같은 환경에서도 응답이 다른 경우 자연스럽게 표현.

## 9.5 Scenario 파일의 Platform 섹션

시나리오는 이제 표적만 아니라 **레이더 플랫폼도 포함**한다. TOML 메타 파일 예시:

```toml
# scenario_meta.toml

[platform]
platform_id = "corvette_500t"
category = "maritime"
display_name = "500t Corvette"

# 설치 위치 (ENU 로컬)
install_east_m = 0.0
install_north_m = 0.0
install_altitude_m = 12.5              # 갑판 위 안테나 높이 (바다 평면 기준)

initial_az_deg = 0.0
initial_el_deg = 0.5

# 운동 모델
motion_model = "sea_state"
motion_params = { sea_state = 4, dominant_period_s = 8.0, amplitude_deg = 3.5 }

# 형상
mesh_path = "platforms/corvette_500t.stl"
antenna_height_above_base_m = 8.0

# --- 또는 고정 지상 플랫폼 ---

[platform]
platform_id = "coastal_tower_50m"
category = "fixed_ground"
display_name = "Coastal Tower"

install_east_m = 1250.0
install_north_m = 3400.0
install_altitude_m = 87.3              # DEM 샘플(37.3m) + 타워 높이(50m)

initial_az_deg = 180.0
initial_el_deg = 0.0

motion_model = "stationary"
motion_params = {}

mesh_path = "platforms/tower_50m.stl"
antenna_height_above_base_m = 50.0
```

### 9.5.1 Platform Preset 라이브러리

MVP는 3~5개 프리셋을 내장:

- `corvette_500t` (함선, 중소형)
- `destroyer_5000t` (함선, 대형)
- `coastal_tower_50m` (고정 지상, 해안 타워)
- `rooftop_30m` (고정 지상, 도심 옥상)
- `hilltop_observatory` (고정 지상, 산정상)

사용자가 새 플랫폼을 만들 때 프리셋을 복사해 수정하는 흐름.

### 9.5.2 Installation 저장 정책 (v0.18)

**핵심 원칙**: Installation은 **Scenario의 일부**다. 별도 파일·별도 관리 없음.

- 한 Scenario = 한 `scenario_meta.toml` = 하나의 `[platform]` 섹션
- Scenario 이름 = Installation 이름 (매핑 관리 불필요)
- 사용자가 Installation을 수정하면 **자동으로 같은 파일에 저장**

#### 저장 흐름

**Case 1: 새 Scenario 생성**
```
[New Scenario] → Installation 화면 자동 진입
            → 사용자 입력
            → [Save & Continue] → scenarios/my_scenarios/<name>/scenario_meta.toml 생성
              (trajectory CSV는 별도로, [platform] 섹션은 여기에 포함)
```

**Case 2: 사용자 소유 Scenario 수정 (my_scenarios/)**
```
[Scenario Load] → [platform] 자동 적용
            → [Scenario > Edit Installation]
            → 사용자 수정
            → [Save & Continue] → 같은 scenario_meta.toml 덮어쓰기 (즉시)
```

**Case 3: Built-in Scenario 수정 시도**
```
[Built-in 시나리오 Load] → [platform] 자동 적용
            → [Scenario > Edit Installation]
            → 사용자 수정
            → [Save & Continue]
            → 경고 다이얼로그:
                "Built-in 시나리오는 수정할 수 없습니다.
                 새 이름으로 저장하시겠어요?"
            → 새 이름 입력 → my_scenarios/<new_name>/ 생성
```

**Case 4: 기존 Scenario를 기반으로 다른 Installation 실험**
```
[B_Conflict 로드]
    → [Save Scenario As...] (메뉴)
    → 새 이름 입력 ("B_Conflict_hilltop")
    → my_scenarios/B_Conflict_hilltop/ 복제 생성
      (trajectory CSV 동일, [platform] 동일)
    → 이후 [Edit Installation]에서 자유롭게 수정·저장
```

#### 이름 충돌 처리

같은 이름의 Scenario가 이미 있을 때:
- **사용자 Scenario간 충돌**: "덮어쓰시겠어요? / 이름 변경 / 취소" 3-way 다이얼로그
- **built-in 이름과 충돌**: 거부. "Built-in과 같은 이름은 사용할 수 없습니다" 에러
  - 이유: built-in은 Workbench 배포에 포함되므로 업데이트 시 덮어써질 수 있음

#### 파일 구조

```
~/my_workbench_proj/
├── scenarios/
│   ├── my_scenarios/
│   │   ├── B_Conflict_hilltop/
│   │   │   ├── scenario_meta.toml       ← [platform] 섹션 포함
│   │   │   ├── targets.csv              ← trajectory
│   │   │   └── terrain.tif              ← DEM (선택)
│   │   └── ...
│   └── (built-in은 Workbench 설치 경로에)
```

단일 Scenario = 단일 디렉토리. `scenario_meta.toml`에 모든 메타(Platform 포함), 주변 자료(CSV/DEM)는 같은 폴더 내. **디렉토리 이름 = Scenario 이름**.

## 9.6 Installation 필수 게이트

Scenario 로드 후 Target Run 전에 **설치 정보가 확정되어야 한다**.

### 9.6.1 워크플로

```
[Scenario Load]
    │
    ▼
  Installation 확인
    │
    ├── scenario_meta.toml에 [platform] 섹션 완비? ─ YES ─▶ 자동 적용
    │                                                         │
    │                                                         ▼
    │                                                   Target Run 가능
    │
    └── NO (또는 사용자가 수정하려 함)
            │
            ▼
        Installation 화면 진입 (자동 또는 메뉴)
            │
            ├── 레이더 Platform Preset 선택
            ├── DEM 위 설치 위치 지정 (클릭 또는 좌표 입력)
            ├── 안테나 높이·방향 설정
            ├── 주변 차폐 Preview
            ├── 저장 → scenario_meta.toml 갱신
            └── Target Run 가능 상태로 복귀
```

### 9.6.2 Installation 화면 요구사항

[05 § 5.3.8](05_ui_ux.md#538-installation-화면-v018-신설)에서 UI 상세.

핵심:
- DEM 2D 맵 (top-down view) + 3D 프리뷰
- 플랫폼 Preset 드롭다운
- 클릭·드래그로 위치 지정 (DEM에서 자동 고도 샘플)
- 안테나 높이 슬라이더/입력
- 초기 방향 (보어사이트) 회전 다이얼
- **차폐 Preview**: 선택한 위치에서의 시야각 cone (9.7 참조)
- Save / Cancel

### 9.6.3 Target Run 버튼 비활성화 조건

Target Run 버튼은 다음 중 하나라도 해당하면 비활성화:
- 플랫폼 정보 없음
- 설치 위치가 DEM 범위 밖
- 설치 고도가 DEM 지표면보다 낮음 (지하)

비활성화 시 툴팁: "Installation을 먼저 완료해주세요"

## 9.7 DEM 차폐 계산 (간단한 높이 기반)

> ⚠️ **v0.22~v0.34 정합**: 본 섹션의 LOS 차폐 알고리즘은 v0.18 시점 사고. 후속 변경:
>
> - **v0.22 land_mask** (11 § 11.5.5, 03 § 3.2.1c): `dem.sample()` 대신 `sample_terrain_safe()`
>   사용 — Map 안은 정밀 DEM, Map 밖은 OutsideEnvironment 정책 적용 (v0.29)
> - **v0.29 Simulation Domain** (11 § 11.11): Map > SimulationDomain 일 때 Map 밖 영역의
>   LOS는 outside_environment 의 자유 전파 가정
> - **v0.34 Refraction** (15 § 15.5.4, 16 § 16.3.5): 직선 빔 가정 → effective Earth radius
>   (4/3 × 6378 km) 보정. 장거리(>10km) 차폐 검사 정확도 ↑. `effective_earth_radius_m()` 사용
> - **v0.34 Two-ray multipath** (08 § 8.5b.1): 해상 시나리오에서 직접 경로 외 sea bounce
>   경로도 신호 전달 — LOS 차폐와 별개로 multipath 모델이 받음 신호 영향
>
> 본 섹션의 알고리즘은 MVP 단순 모델로 유효. 위 변경은 `compute_los_obstruction()` 구현 시
> 통합 필요.

### 9.7.1 원리

풀 LOS (Line-of-Sight) 레이트레이싱은 계산 비용이 크므로, MVP는 **직선 세그먼트 최고점
검사**만 수행:

```
레이더 위치 (R)                표적 위치 (T)
      *━━━━━━━━━━━━━━━━━━━━━━━━━━*
       \                        /
        \        차폐?          /
         \_____ _____ _____ ___/
               ↑
            DEM 최고점 M

차폐 판정:
  M의 고도 > R-T 직선 세그먼트에서 M의 x-y에 해당하는 고도
  → 차폐됨 (Target 보이지 않음)
```

알고리즘:

```python
def check_los_obstruction(
    radar_pos: tuple[float, float, float],    # (east, north, altitude)
    target_pos: tuple[float, float, float],
    dem: DEM,
    n_samples: int = 64
) -> LOSResult:
    """직선 세그먼트를 n_samples개 점으로 샘플링.
    각 점에서 DEM 고도가 세그먼트 고도보다 높은지 확인.
    """
    best_margin = float('inf')              # 최소 여유 고도 (음수면 차폐)
    obstruction_at = None

    for i in range(1, n_samples):
        t = i / n_samples
        e = radar_pos[0] * (1-t) + target_pos[0] * t
        n = radar_pos[1] * (1-t) + target_pos[1] * t
        segment_alt = radar_pos[2] * (1-t) + target_pos[2] * t

        dem_alt = dem.sample(e, n)
        margin = segment_alt - dem_alt

        if margin < best_margin:
            best_margin = margin
            if margin < 0:
                obstruction_at = (e, n, dem_alt)

    return LOSResult(
        obstructed=(best_margin < 0),
        margin_m=best_margin,
        obstruction_point=obstruction_at,
    )
```

**n_samples=64**가 MVP 기본. DEM 해상도에 따라 조정.

### 9.7.2 Scenario 실행 중 차폐 반영

각 프레임의 RadarPipeline 호출 전에:

1. Scenario의 각 표적에 대해 `check_los_obstruction()` 수행
2. **차폐된 표적은 Reflection 생성 안 함** (또는 Reflection에 `obstructed=True` 플래그)
3. Probe에 차폐 상태 기록 (디버깅·Stage I/O 패널용)

### 9.7.3 Installation 화면의 차폐 Preview

설치 위치 결정 시 **"이 위치에서 무엇이 보이는가"** 를 즉시 시각화:

```
┌─ Installation ─────────────────────────┐
│  DEM Map (top-down)                    │
│                                        │
│      ⬢ 설치 위치                       │
│     / │ \                              │
│    /  │  \   ← 가시 영역 (밝은색)      │
│   /___│___\                            │
│     음영 영역 ← 차폐 (어두운색)        │
│                                        │
└────────────────────────────────────────┘
```

360° 둘레를 N개 방위(예: 72개, 5° 간격)로 나눠 각 방위에서 **최대 가시 거리**를 계산.
지면 높이 이상에 있는 가상의 "기준 표적 고도"(예: 10m)까지 도달 가능한 최대 거리.

### 9.7.4 MVP 후 확장

- 건물 3D 메시를 차폐 계산에 포함 (DEM만 아니라)
- 회절 (diffraction)로 일부 차폐 영역에도 약한 신호 도달
- 대기 굴절률에 의한 LOS 휘어짐 (4/3 Earth model → 실제 프로파일)

자세한 내용은 [06 § 6.8 Deferred Physics — Advanced RF Suite](06_topics.md#68-deferred-physics--미래-확장-영역).

## 9.8 Coordinate System 정리

플랫폼 다양화로 좌표계를 다시 정리할 필요가 있다.

### 9.8.1 좌표계 계층

```
[Global (WGS84 또는 투영)]
       │
       │ Scenario 원점 (지정)
       ▼
[Scenario-local ENU]            East, North, Up (m)
       │
       │ Platform 설치 위치 (고정, Scenario 원점 기준)
       ▼
[Platform base frame]            플랫폼 바닥
       │
       │ Platform pose (roll/pitch/yaw — 운동 모델에서 갱신)
       ▼
[Platform instantaneous frame]   안테나 마운트 기준
       │
       │ Positioner 각도 (AZ/EL)
       ▼
[Radar boresight frame]          빔 축 기준
```

### 9.8.2 표적과의 상대 좌표

기존 코드에서 "표적의 range/az/el"은 대부분 **radar boresight frame** 기준이었다.
플랫폼 다양화 후에도 동일 — Radar Pipeline 입장에선 변화 없음. 플랫폼 운동은 Platform
instantaneous frame까지만 영향을 주고, 그 위에 Positioner가 얹힌다.

### 9.8.3 자함 동요와 플랫폼 Pose의 관계

v0.17 기준 `EnvironmentState.platform_roll_deg` / `platform_pitch_deg`는 사실상 함선 자세였다.
v0.18에서는:

- `EnvironmentState`는 여전히 roll/pitch/yaw를 가짐 — 하지만 이건 **현재 Platform의 Pose**
- 함선 플랫폼이면 sea_state 모델이 이 값을 채움
- 고정 지상 플랫폼이면 stationary 모델이 0으로 채움

코드 레벨에선 달라질 게 없지만, **의미가 "함선 자세" → "플랫폼 자세"로 일반화**된다.

## 9.9 기존 문서와의 관계

### 9.9.1 03 data_model

- `Platform`, `PlatformCategory`, `PlatformMotionModel`, `PlatformPose` 타입 추가
- `Scenario`에 `platform: Platform` 필드 추가 (기존엔 암묵적으로 자함)
- `EnvironmentState`의 roll/pitch/yaw 의미를 "플랫폼 자세"로 재해석

### 9.9.2 05 ui_ux

- § 5.3.8 Installation 화면 신규
- § 5.3.1 Scenario Explorer에 플랫폼 아이콘 표시 추가
- Run Panel에 현재 플랫폼 요약 표시

### 9.9.3 06 topics

- § 6.8 Deferred Physics에 "Advanced Platform Motion" (6자유도, 차량, 공중) 명시
- § 6.1 Probe에 LOS 차폐 결과도 probe 가능하도록

### 9.9.4 07 nn_integration

- NN Dataset Extraction의 SampleSpec에 플랫폼 정보 포함 (같은 표적이라도 플랫폼 따라 수신 신호 달라짐)
- NN 학습 시 다양한 플랫폼 조합으로 데이터 분산 확보

### 9.9.5 08 radar_waveforms

- RadarModel과 Platform은 **독립 축** — FMCW Triangle 레이더는 함선에도 건물에도 설치 가능

## 9.10 용어 정리

- **Platform**: 레이더가 설치되는 플랫폼 (상위 개념)
- **Ownship**: Maritime Platform의 관습적 별칭. 해상 시나리오에서 "자함"으로 부름
- **Installation**: 플랫폼을 DEM 상 특정 위치에 배치하는 작업·상태
- **Platform Pose**: 플랫폼의 현재 roll/pitch/yaw (운동 모델 출력)
- **LOS Obstruction**: 레이더-표적 직선에 지형·구조물이 끼어 차폐되는 현상

## 9.11 Open Questions

다음은 MVP 이후 또는 실사용 피드백 후 결정:

- Platform Motion Model을 플러그인화? (MVP는 내장만)
- DEM 포맷 지원 범위 (GeoTIFF, SRTM, ASTER, 사용자 CSV 그리드 등)
- Platform 3D 메시를 RCS self-reflection 계산에 포함?
- 차량 플랫폼의 주행 궤적은 Scenario에 어떻게 표현? (별도 trajectory?)
- 멀티 플랫폼 (여러 레이더 동시) 시나리오 지원?

## 섹션 상태

- 9.1~9.2 개요/범위 — ✅
- 9.3 Contract — ✅ (세부 필드는 구현 시 조정. v0.21에서 `motion_kind` 필드 추가)
- 9.4 Motion Model — ✅
  - 9.4.3 PlatformCategory ↔ MotionKind 매핑 — ✅ (v0.21 정합)
- 9.5 Scenario 파일 구조 — 🟡 (TOML 형식은 예시, 구현 시 확정)
- 9.6 Installation 게이트 — ✅
- 9.7 LOS 차폐 — ✅ (알고리즘 잠정)
- 9.8 좌표계 — ✅
- 9.9 기존 문서 영향 — ✅ (각 문서에서 세부 반영)
- 9.10 용어 — ✅
- 9.11 Open Questions — 🟡 (열린 채로 유지)

---

👉 다음: [10_workspaces.md](10_workspaces.md)
👉 이전: [08_radar_waveforms.md](08_radar_waveforms.md)
