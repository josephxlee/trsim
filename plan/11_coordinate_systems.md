# 11. Coordinate Systems & Vertical Reference

**최종 갱신**: 2026-04-28 (v0.35)

**관련 문서**: [09 radar_platforms](09_radar_platforms.md), [10 workspaces](10_workspaces.md), [12 placement_and_motion](12_placement_and_motion.md), [03 data_model](03_data_model.md)

## 11.1 왜 이 문서가 있나

지형·건물·해상·표적의 좌표·고도가 **서로 다른 기준** (WGS84 / ENU / DEM 출처별 / Mean Sea Level 등) 으로 섞이면 다음 버그가 흔히 발생:

- 건물이 지형 위로 약간 떠오름
- 해안선과 해수면이 안 맞음
- DEM 출처에 따라 고도 의미가 달라 비교 불가
- 표적 trajectory가 해상에 있어야 하는데 음수 고도로 계산됨

원인은 **모든 자원이 "어떤 기준의 좌표인가"를 명시하지 않은 채** 섞여 들어오기 때문.
v0.21에서 좌표계 정책을 명시화해 이 문제를 근본 해결.

## 11.2 워크스페이스 기준 좌표 — Map의 Origin

본 Workbench는 한 시뮬레이션 안에서 **단일 Map**을 사용한다. Map의 Origin이 곧 **워크스페이스의
절대 기준점**이며, 모든 자원은 이 기준점에 묶인다.

```
[Workspace 기준]
    └─ Map.Origin (lat, lon, vertical_reference)
         ├─ DEM 데이터 (Map 안에 포함)
         ├─ 해수면 (Map의 sea_surface)
         ├─ 건물 (Map의 자식, anchor 시스템으로 부착)
         ├─ Radar Platform (Map 위에 설치, ENU + altitude)
         └─ Targets (Map 기준 좌표로 trajectory)
```

Map이 바뀌면 모든 자원의 좌표 의미가 새 Map 기준으로 재해석된다 (자동 변환 시도, 10 § 10.10
재현성 검증 동반).

## 11.3 수평 좌표계 — WGS84 + ENU

### 11.3.1 결정

- **사용자 입력·외부 데이터**: WGS84 위경도 (lat/lon)
- **내부 계산**: Map Origin 기준 ENU (East, North, Up) 미터 좌표
- **저장 포맷**: 모든 자원 파일에 ENU (m) 저장. 위경도는 Map.Origin에서만

### 11.3.2 ENU 변환 규칙

Map.Origin (lat0, lon0, alt0)을 기준으로:

```python
def wgs84_to_enu(lat, lon, alt, origin):
    # 표준 ENU 변환 (지구 곡률 무시 가능 범위에서 정확)
    # 일반적으로 < 100km 반경에서 < 0.01% 오차
    ...
```

- 평면 ENU 근사를 쓴다 (수십 km 반경의 시뮬에서 충분)
- 100 km 이상 반경이 필요한 시나리오는 MVP+α (구면 ENU 도입)

### 11.3.3 Origin은 불변 (v0.20 Q2 결정)

Map의 Origin은 **생성 시점에 결정되어 변경 불가**:
- 변경 시도 → "새 Map으로 Save As" 권장
- 이유: Origin이 바뀌면 Map의 모든 데이터(DEM, 건물, 해안선)의 좌표 의미가 달라짐 → 재계산 위험성 큼

### 11.3.4 외부 좌표계 import

DEM·건물 데이터가 다른 좌표계로 오면 import 시 자동 변환:

| 입력 형식 | 변환 |
|---|---|
| GeoTIFF (CRS 메타 포함) | CRS → WGS84 → Map ENU |
| UTM zone X | UTM → WGS84 → Map ENU |
| 사용자 CSV (위경도) | 위경도 → Map ENU |
| 사용자 CSV (ENU 직접) | Map Origin과 일치 가정, 그대로 |

CRS 메타가 없으면 **사용자 다이얼로그**로 묻는다 (§ 11.5.2).

## 11.4 수직 기준 — Vertical Reference (핵심)

### 11.4.1 왜 별도 다루나

xy(수평)는 비교적 안정적이지만 **z(고도)는 출처에 따라 의미가 다르다**. 같은 (lat, lon)에서도:

- WGS84 ellipsoid 기준 고도
- EGM96 geoid 기준 고도 (≈ MSL)
- 지역 평균해수면 (MSL local datum)
- NAVD88 (북미 한정)

이 차이는 한국 기준 약 **25m** 까지 난다. 시뮬에서 z=0이 무엇인지 정의하지 않으면 데이터 정합
실패가 누적된다.

### 11.4.2 Map의 Vertical Reference 명시 필수

Map은 vertical reference를 **반드시** 가진다:

```toml
[origin]
lat_deg = 37.5665
lon_deg = 126.9780
# ENU 기준점의 고도 (vertical_reference가 정의한 기준에서)
alt_m = 0.0

[vertical_reference]
# z=0 (즉 alt_m=0)이 가리키는 것
type = "egm96"                   # ellipsoid_wgs84 / egm96 / msl_local / unknown
local_datum = ""                 # type=msl_local일 때만 (예: "incheon_msl_2014")
geoid_accuracy_m = 1.0           # 모델 자체의 알려진 오차 (참고용)

[sea_surface]
# 시뮬이 그리는 해수면이 z=얼마인가
z_at_sea_m = 0.0                 # 보통 0
```

**MVP에서 지원하는 type**:
- `egm96` — EGM96 geoid 기준 (AWS·SRTM 일반, 추천 기본값)
- `ellipsoid_wgs84` — WGS84 타원체 기준 (드물게)
- `msl_local` — 지역 평균해수면 datum
- `unknown` — 명시 거부, 디버그용 (저장 시 경고)

**MVP 후**:
- `navd88`, `egm2008`, 더 정밀한 geoid 모델

### 11.4.3 z=0의 의미

- Map의 모든 z 값은 **vertical_reference type 기준**
- `sea_surface.z_at_sea_m`은 **그 기준에서의 해수면 고도** (보통 0)
- 시뮬의 해수면 평면은 정확히 이 z값에 그려진다

### 11.4.4 기본값 추천

새 Map 생성 시 기본:
- `vertical_reference.type = "egm96"`
- `sea_surface.z_at_sea_m = 0.0`

이는 AWS DEM 등 일반적 데이터 출처에 맞다. 예외 상황(정밀 측량, 항만 시설 등)에 한해 사용자가
변경.

## 11.5 DEM Import 파이프라인 — 외부 → Workbench Native (v0.22 재설계)

### 11.5.1 기본 원칙

외부 DEM (GeoTIFF, SRTM, CSV)은 **import 시점의 소스**일 뿐, 시뮬레이션은 **Workbench Native
지형 포맷**(§ 11.10)을 사용한다.

이유:
- 외부 DEM은 vertical reference·해상 영역·해상도가 제각각
- DEM의 부정확한 해저 z 값이 시뮬에 누설됨 (이전 프로젝트의 핵심 버그)
- 사용자가 지형을 편집해야 할 때 외부 포맷은 read-only가 일반적
- 자체 규격이 시뮬 성능·일관성·재현성에 유리

### 11.5.2 표준 파이프라인

```
[외부 DEM 파일 선택] (.tif, .hgt, .csv ...)
    ↓
[Step 1] 포맷 감지 + CRS·Vertical Datum 메타 읽기
    ↓
[Step 2] Vertical Reference 다이얼로그 (메타 누락 시)
    ↓
[Step 3] 영역 선택 (전체 vs Map Bounds로 crop)
    ↓
[Step 4] Land/Sea 구분 방식 선택 (§ 11.5.5)
    ↓
[Step 5] 좌표·고도 변환 (외부 CRS·datum → Map ENU·vertical_reference)
    ↓
[Step 6] 격자 보간 (해상도 통일, bilinear 기본)
    ↓
[Step 7] Workbench Native 저장 (terrain.npz, § 11.10)
    ↓
[원본 DEM은 source/에 보관] ← 재변환·다른 vertical reference 변환에 활용
```

이후 시뮬·편집은 자체 규격(terrain.npz)만 사용한다. 원본 DEM은 보관용·재import용.

### 11.5.3 Vertical Reference 다이얼로그

DEM 파일에 vertical reference가 명시되지 않은 경우:

```
┌─ DEM Vertical Reference 확인 ─────────────────────┐
│ "terrain_seoul.tif"의 수직 기준이 메타에 없습니다.  │
│                                                  │
│ 어떻게 처리할까요?                                 │
│  ( ) WGS84 ellipsoid 기준 (드물게)                  │
│  (•) EGM96 geoid 기준 (AWS·SRTM 일반) ← 추천        │
│  ( ) 지역 평균해수면 (MSL local)                   │
│  ( ) 보정 없음 — 그대로 사용 (디버그용)             │
│                                                  │
│  ☐ 이 데이터 출처에 대해 다시 묻지 않기             │
│                                                  │
│              [취소]   [적용]                       │
└──────────────────────────────────────────────────┘
```

**기본값은 EGM96** — 가장 흔한 데이터 (SRTM·AWS Terrain Tiles).

### 11.5.4 영역 선택

큰 DEM 파일(예: 한반도 전체)을 가져올 때 **Map Bounds 만큼만 잘라서** import:

```
영역 선택:
  ☑ 전체 영역 (~120 km × 120 km)
  ☐ 사용자 정의 (Map Bounds로 잘라내기)
      East:  -25000 m ~ +25000 m
      North: -25000 m ~ +25000 m
```

성능·디스크 절약. crop된 부분만 자체 규격에 저장.

### 11.5.5 Land/Sea 구분 방식 선택

**자원의 핵심**. 어떤 픽셀이 육상이고 어떤 픽셀이 해상인지 결정:

```
Land/Sea 구분:
  (•) 자동 (z < 0.5 m → 해상)
  ( ) Nodata 값 기준 (SRTM 등의 nodata를 해상으로)
  ( ) 외부 해안선 파일 사용 (GeoJSON, Shapefile)
      파일: [Browse...]
  ( ) 모두 육상으로 (해상 영역 없음)

  ☐ 가져온 후 Land/Sea Mask Brush로 직접 수정 (Editor)
```

각 방식의 결과는 `land_mask` 2D 배열 (boolean, True=육상). 자체 규격에 같이 저장.

### 11.5.6 좌표·고도 변환

수평:
- 외부 CRS → WGS84 위경도 → Map ENU (m)
- pyproj 또는 자체 변환 (수십 km 반경에서 평면 ENU 근사 충분)

수직 (§ 11.4.2 표 참조):
- EGM96 ↔ ellipsoid_wgs84: geoid 룩업 모델 사용
- msl_local 변환: 사용자 보정값 적용

### 11.5.7 격자 보간

외부 DEM과 Workbench Native의 **격자 해상도가 다를 수 있음** — 보간 필요.

- 기본 **bilinear**
- 사용자 선택: nearest (빠름) / bicubic (부드러움)
- Native 격자 해상도는 import 시 사용자 지정 (기본 외부 DEM과 일치)

### 11.5.8 저장

Workbench Native 포맷(§ 11.10)으로 저장:

```
resources/maps/EastCoast_50km/
├── map.toml              ← 메타데이터 + Origin + vertical_reference
├── terrain.npz           ← 자체 규격 지형 (격자 + land_mask)
└── source/
    ├── original_dem.tif  ← 원본 DEM (재import 가능)
    └── import_log.toml   ← 변환 이력 (vertical_ref 변환, crop 영역 등)
```



## 11.6 DEM 샘플링 규칙

### 11.6.1 Bilinear가 기본

```toml
[dem_settings]
sampling_method = "bilinear"     # nearest / bilinear / bicubic
edge_handling = "clamp"          # clamp / nodata / wraparound
nodata_value = -9999.0           # SRTM 등에서의 nodata 표식
```

- **`bilinear`**: 4픽셀 가중 평균 (MVP 기본). 픽셀 경계에서도 부드러움
- **`nearest`**: 가장 가까운 픽셀 (성능 우선, 정합성 떨어짐)
- **`bicubic`**: 16픽셀 가중. 부드럽지만 비용 큼 (MVP+α)

### 11.6.2 샘플링 결과 캐싱

- 자원 배치(예: 건물 위치 결정) 시 매번 DEM 샘플링 → 성능 부담
- Workbench는 자주 사용되는 위치에 대해 **메모이제이션 캐시** 유지
- Map의 DEM 자체가 변경되면 캐시 무효화

### 11.6.3 Edge handling

- **`clamp`**: Map 경계 밖은 가장 가까운 경계 값 사용 (기본)
- **`nodata`**: 경계 밖은 None 반환, 호출자가 처리
- **`wraparound`**: 경계 밖은 반대편으로 (전 지구 시뮬용, MVP 후)

## 11.7 Coherence Validator (일관성 검증)

좌표·고도 정합 문제는 사후 발견이 어렵다. **자원 변경 시점마다 자동 검증** 한다.

### 11.7.1 검증 시점

1. **DEM 로드 직후** — vertical reference, 샘플링 등 기본 정합성
2. **건물 배치/이동 시** — 건물 base가 지표면에 맞는지
3. **Targets 추가/수정 시** — waypoint가 Map 경계 안인지, 적절한 z인지
4. **Map 저장 시** — 종합 검증
5. **Simulator로 전환 시** — 종합 검증 (Run 시작 전 마지막 점검)

### 11.7.2 검증 항목 (MVP)

```python
def validate_map_coherence(m: Map) -> list[Warning]:
    warnings = []

    # 1. DEM과 Vertical Reference 일관성
    if m.dem.source_vertical_ref != m.vertical_reference:
        warnings.append(SeverityInfo(
            "DEM이 다른 vertical reference에서 변환됨 — 변환 정확도 ~1m 한계 있음"
        ))

    # 2. 해안선 z와 sea_surface 일치
    if m.has_coastline_data:
        coastline_z = m.coastline.mean_z
        if abs(coastline_z - m.sea_surface.z_at_sea_m) > 0.5:
            warnings.append(SeverityWarn(
                f"해안선 평균 z({coastline_z:.2f}m)와 시뮬 해수면(z={m.sea_surface.z_at_sea_m})이 차이 큼"
            ))

    # 3. 건물 base가 DEM과 정합
    for b in m.buildings:
        if b.anchor_mode == "explicit_alt":
            terrain_z = m.dem.sample(b.east, b.north)
            if b.base_altitude_m < terrain_z - 0.1:
                warnings.append(SeverityError(
                    f"건물 '{b.name}'이 지표면 아래 ({b.base_altitude_m:.2f} < {terrain_z:.2f})"
                ))
            elif b.base_altitude_m > terrain_z + 5.0:
                warnings.append(SeverityWarn(
                    f"건물 '{b.name}' base가 지표면 위로 떠있음 ({b.base_altitude_m:.2f} > {terrain_z:.2f}+5m)"
                ))

    # 4. 해상 영역에 land DEM
    if m.has_sea_region:
        sea_samples = m.dem.sample_below_z(m.sea_surface.z_at_sea_m)
        if sea_samples == 0:
            warnings.append(SeverityWarn(
                "해상 영역이 정의됐는데 DEM에 해수면 아래 고도가 없음 (DEM이 land-only?)"
            ))

    # 5. Vertical Reference 명시 안 됨
    if m.vertical_reference.type == "unknown":
        warnings.append(SeverityWarn(
            "Vertical Reference가 'unknown' — z 값 의미가 불명확합니다"
        ))

    return warnings


def validate_targets_coherence(targets: TargetsResource, map_: Map) -> list[Warning]:
    warnings = []
    for t in targets.targets:
        for wp in t.trajectory.waypoints:
            # Map 경계 밖
            if not map_.bounds.contains(wp.east_m, wp.north_m):
                warnings.append(SeverityError(
                    f"Target #{t.id}의 waypoint @t={wp.t_s}s가 Map 밖"
                ))
            # 해상 표적이 지하
            if t.motion_kind in (MotionKind.SURFACE_VESSEL, MotionKind.FLOATING_STATIC):
                terrain_z = map_.dem.sample(wp.east_m, wp.north_m)
                if wp.altitude_m < terrain_z:
                    warnings.append(SeverityWarn(
                        f"Target #{t.id} @t={wp.t_s}s가 지형 아래 (해상 표적이 land로?)"
                    ))
    return warnings
```

### 11.7.3 검증 결과 표시

저장 시 경고 다이얼로그:

```
┌─ Map 'EastCoast_50km' 검증 결과 ────────────────┐
│                                                 │
│ ⚠ 경고 2개:                                     │
│   • 해안선 평균 z(0.34m)와 시뮬 해수면(z=0)이     │
│     차이 큼                                     │
│   • Tower_5의 base가 지표면 아래 (87.0m < 87.4m) │
│                                                 │
│ 🔴 오류 1개:                                     │
│   • Target #2의 waypoint @t=15s가 Map 밖        │
│                                                 │
│  [수정 도구 열기]  [무시하고 저장]  [취소]         │
└─────────────────────────────────────────────────┘
```

오류(Error)가 있으면 저장은 가능하되 **Simulator 전환 차단**. 사용자가 이 자원으로 Run 시작
못 함.

## 11.10 Workbench Native Map Format (v0.22 신설)

### 11.10.1 왜 자체 규격인가

§ 11.5에서 선언한 대로, 외부 DEM은 import 소스이고 시뮬은 자체 규격을 사용한다. 이 자체 규격의
설계 이유:

- **시뮬에 필요한 것만**: 육상 고도 + 해상 마스크 + 해상도 통일
- **편집 가능**: DEM은 read-only인 경우 많지만 자체 규격은 사용자가 수정 가능
- **일관된 vertical reference**: import 시점에 한 번 변환, 이후 일관성 유지
- **성능**: numpy 친화적 (npz), 시뮬 런타임에 빠른 샘플링
- **재현성**: content hash 안정 (외부 DEM 라이브러리 의존성 제거)
- **패키징**: Bundle export 시 가벼움

### 11.10.2 디렉토리 구조

```
resources/maps/EastCoast_50km/
├── map.toml                ← 메타데이터 + Origin + vertical_reference + sea_surface
├── terrain.npz             ← 자체 규격 지형 데이터 (격자 + land_mask)
├── coastline.npz           ← 해안선 폴리곤 (선택, 자동 생성 가능)
├── buildings.toml          ← 건물 목록
└── source/                 ← 원본 자료 보관 (재import용)
    ├── original_dem.tif    ← 원본 DEM 파일
    └── import_log.toml     ← 변환·편집 이력
```

`source/`는 선택적 — 사용자가 디스크 절약 위해 삭제 가능. 단 삭제하면 재변환 불가.

### 11.10.3 terrain.npz 내용

```python
# numpy savez로 저장
{
    # 격자 정의 (ENU 기준, m)
    "grid_east_m": np.ndarray,          # 1D, shape=(W,) — 동쪽 격자
    "grid_north_m": np.ndarray,         # 1D, shape=(H,) — 북쪽 격자
    "resolution_m": float,              # 픽셀 크기 (등간격 가정)

    # 고도 데이터
    "elevation_m": np.ndarray,          # 2D, shape=(H, W)
                                        # vertical_reference 기준 z (m)
                                        # 해상 영역의 값은 무시되지만 보존됨

    # Land/Sea 분류
    "land_mask": np.ndarray,            # 2D bool, shape=(H, W)
                                        # True=육상, False=해상

    # 메타
    "interpolation": str,               # "bilinear" / "nearest" / "bicubic"
    "edited": bool,                     # 사용자 편집 여부
    "source_dem_hash": str,             # 원본 DEM의 SHA-256 (재변환 검증)
}
```

### 11.10.4 샘플링 동작

`terrain.sample(east, north)` 호출 시:

```python
def sample_terrain(east: float, north: float,
                   terrain: WorkbenchTerrain,
                   sea_surface_z: float) -> tuple[float, str]:
    """
    Returns: (z, kind) where kind = "land" | "sea"
    """
    # 격자 좌표 계산
    e_idx, n_idx = world_to_grid(east, north, terrain)

    # Land/Sea 마스크 검사 (가장 가까운 픽셀)
    if not terrain.land_mask[n_idx, e_idx]:
        return sea_surface_z, "sea"     # 해상 영역은 항상 해수면 z

    # 육상 영역 → bilinear 샘플링
    z = bilinear_sample(terrain.elevation_m, e_idx, n_idx)
    return z, "land"
```

**핵심**: `land_mask`가 False인 픽셀은 `elevation_m` 값을 무시하고 **항상 sea_surface_z**를 반환.
→ DEM의 부정확한 해저 z 값이 시뮬에 영향 안 미침.

### 11.10.5 map.toml 예시

```toml
name = "EastCoast_50km"
description = "50km stretch of east coastline with harbor"
version = "1.0"
content_hash = "sha256:abc..."          # terrain.npz + buildings.toml 등 합산 hash

[origin]
lat_deg = 37.5665
lon_deg = 126.9780
alt_m = 0.0

[vertical_reference]
type = "egm96"
geoid_accuracy_m = 1.0

[sea_surface]
z_at_sea_m = 0.0

[bounds]
east_min_m = -25000.0
east_max_m =  25000.0
north_min_m = -25000.0
north_max_m =  25000.0

[terrain]
file = "terrain.npz"                    # 자체 규격
resolution_m = 30.0
grid_h = 1666                           # north 격자 수
grid_w = 1666                           # east 격자 수

[coastline]
file = "coastline.npz"                  # 선택
auto_generated = true                   # 자동 생성 여부

[edit_history]
last_edited = "2026-04-25T10:30:00Z"
total_edits = 12

[source]
original_dem = "source/original_dem.tif"   # 선택
preserved = true                            # 보관 여부
```

### 11.10.6 원본 DEM 보관·재변환

자체 규격을 주로 쓰되, 원본 DEM은 **유연성을 위해 보관**한다.

**가능한 작업**:
- 다른 vertical reference로 재변환 (예: EGM96 → MSL local)
- 다른 해상도로 재import (예: 30m → 10m)
- 다른 영역 crop으로 재import
- Land/Sea 구분 재분류 (다른 임계값 또는 새 해안선 파일)

**재변환 다이얼로그**:

```
┌─ Re-import from Source DEM ─────────────────┐
│ 원본: source/original_dem.tif (EGM96)        │
│ 현재 자체 규격: terrain.npz (EGM96, 30m)      │
│                                              │
│ 무엇을 변경하시겠어요?                          │
│  ☐ Vertical Reference 변경                    │
│  ☐ Land/Sea 구분 방식 재선택                   │
│  ☐ 해상도 변경                                │
│  ☐ 영역(Bounds) 변경                          │
│                                              │
│ ⚠ 사용자 편집 흔적이 있습니다 (12 edits).     │
│   재변환 시 편집 내용이 사라질 수 있습니다.    │
│                                              │
│      [취소]      [재변환 진행]                │
└──────────────────────────────────────────────┘
```

원본 DEM 디렉토리(`source/`)는 **자체 규격에서 독립** — 사용자가 디스크 절약을 위해 삭제 가능
하며, 그 경우 재변환은 불가하지만 자체 규격 자체는 그대로 사용 가능.

### 11.10.7 Content Hash 정책

- `content_hash`는 `terrain.npz` + `coastline.npz` + `buildings.toml` 등의 합산 hash
- `source/`는 hash 계산에서 **제외** (보관용일 뿐 시뮬 결과에 영향 없음)
- 사용자가 자체 규격을 편집하면 hash 자동 재계산
- v0.20 자원 재사용 hash 시스템과 일관

## 11.11 Simulation Domain — Map과 시뮬 영역의 분리 (v0.29 신설)

### 11.11.1 왜 필요한가

Map은 **정밀 지형이 정의된 영역**(예: 10×10 km)이지만, 레이더는 그보다 훨씬 멀리(예: 50 km)
빔을 쏘고 표적도 그 거리에서 들어올 수 있다. 시나리오:

- 사용자가 10×10 km Map을 만들었음
- 레이더 max range = 50 km
- 표적 trajectory가 Map 경계(5 km)를 넘어 30 km까지 감

Map만으로 다루면 발생하는 문제:
- 표적이 Map 밖일 때 DEM 샘플링 — clamp로 잘못된 값
- 레이더 빔이 Map 밖으로 — 차폐 검사 시 정보 없음
- 시각화에서 표적이 Map 가장자리에 박힘
- 자체 규격 land_mask가 Map 밖은 정의 안 됨 — 육상/해상 판단 불가

### 11.11.2 두 영역 분리

```
┌─────────────────────────────────────────────┐
│      Simulation Domain (전체 시뮬 영역)       │
│      레이더 빔·표적 동역학이 동작 가능          │
│      예: 50×50 km                            │
│                                              │
│    ┌─────────────────┐                       │
│    │  Map 영역 (DEM 정밀)│                    │
│    │  10×10 km        │                       │
│    │  지형·건물·해안선   │                      │
│    └─────────────────┘                       │
│                                              │
│    Map 밖 = Outside Environment 정책 적용     │
│    (open_sea / open_land / blocked / ...)    │
└─────────────────────────────────────────────┘
```

- **Map 영역**: 정밀 DEM·건물·차폐·자체 규격 — 모든 디테일
- **Map 밖, Simulation Domain 안**: 단순화된 outside_environment 적용
- **Simulation Domain 밖**: 시뮬 불가 (오류·경고)

### 11.11.3 데이터 모델

```python
@dataclass(frozen=True)
class SimulationDomain:
    """시뮬 동작 가능 전체 영역. Map보다 큰 외곽."""
    bounds_east: tuple[float, float]      # ENU 동쪽 경계 (m)
    bounds_north: tuple[float, float]     # ENU 북쪽 경계 (m)
    ceiling_alt_m: float = 30000.0        # 항공 표적 가능 최대 고도
    floor_alt_m: float = -100.0           # 해저 (음수 z 허용)

    def contains(self, east: float, north: float, alt: float | None = None) -> bool:
        if not (self.bounds_east[0] <= east <= self.bounds_east[1]):
            return False
        if not (self.bounds_north[0] <= north <= self.bounds_north[1]):
            return False
        if alt is not None:
            if not (self.floor_alt_m <= alt <= self.ceiling_alt_m):
                return False
        return True


class OutsideEnvironment(Enum):
    """Map 영역 밖 (Simulation Domain 안)의 처리 방식."""
    OPEN_SEA = "open_sea"              # 평탄 해수면, sea_surface.z 사용 (기본)
    OPEN_LAND = "open_land"            # 평탄 육상, z=0
    INFINITE_PLANE = "infinite_plane"  # 추상 평면 (디버그용)
    BLOCKED = "blocked"                # Map 밖 진입 시 오류 (엄격)
```

### 11.11.4 소속 — Map + Scenario override (Q-MS3 결정)

- **Map**이 SimulationDomain·OutsideEnvironment의 **기본값** 가짐
- **Scenario**가 자기 [composition]에서 override 가능 (같은 Map으로 다른 시나리오)

```python
@dataclass(frozen=True)
class Map:
    # ... 기존 필드
    simulation_domain: SimulationDomain = field(default_factory=...)
    outside_environment: OutsideEnvironment = OutsideEnvironment.OPEN_SEA


@dataclass(frozen=True)
class Scenario:
    # ... 기존 필드 (refs, composition, platform_install)
    # composition 안에 override 가능:
    simulation_domain_override: SimulationDomain | None = None
    outside_environment_override: OutsideEnvironment | None = None
```

**활용**: 같은 EastCoast_50km Map으로:
- Scenario A: outside=open_sea (해상 시나리오)
- Scenario B: outside=open_land (Map 밖이 모두 평지인 가정)
- Scenario C: outside=blocked (Map 안에서만 시뮬, 엄격)

### 11.11.5 sample_terrain_safe — Map 안/밖 통합

```python
def sample_terrain_safe(east: float, north: float,
                        map_: Map, scenario: Scenario) -> tuple[float, str]:
    """Map 안이면 정밀 샘플링, 밖이면 outside_environment 적용.

    Returns: (z_m, kind) where kind in {"land", "sea", "outside_sea", "outside_land"}
    """
    # Simulation Domain 검사 먼저
    domain = scenario.simulation_domain_override or map_.simulation_domain
    if not domain.contains(east, north):
        raise OutsideSimulationDomainError(
            f"Position ({east:.1f}, {north:.1f}) is outside Simulation Domain"
        )

    # Map 영역 안이면 정밀
    if map_.bounds.contains(east, north):
        return sample_terrain(east, north, map_.terrain, map_.sea_surface)

    # Map 밖, outside_environment 적용
    outside = scenario.outside_environment_override or map_.outside_environment
    if outside == OutsideEnvironment.OPEN_SEA:
        return map_.sea_surface.z_at_sea_m, "outside_sea"
    elif outside == OutsideEnvironment.OPEN_LAND:
        return 0.0, "outside_land"
    elif outside == OutsideEnvironment.BLOCKED:
        raise OutsideMapError(
            f"Position ({east:.1f}, {north:.1f}) is outside Map and Outside=BLOCKED"
        )
    elif outside == OutsideEnvironment.INFINITE_PLANE:
        return 0.0, "outside_land"
```

### 11.11.6 LOS 차폐 — Map 밖 처리

> ⚠️ **v0.34 정합**: 본 알고리즘은 **직선 빔 가정**. v0.34 Atmospheric Refraction
> (15 § 15.5.4, 16 § 16.3.5) 통합 시 `effective_earth_radius_m()` 사용 — 4/3 earth
> radius 보정으로 장거리(>10km) elevation/horizon 정확도 ↑.
> 09 § 9.7 LOS 차폐와 동일 갱신.

차폐 검사(09 § 9.7)는 Map 안 구간만:

```python
def check_los_obstruction(radar_pos, target_pos, map_, scenario,
                         n_samples=64) -> bool:
    for s in linspace(0, 1, n_samples):
        sample_pos = radar_pos + s * (target_pos - radar_pos)

        # Map 밖이면 차폐 검사 안 함 (지형 없다고 가정)
        if not map_.bounds.contains(sample_pos.east, sample_pos.north):
            continue

        terrain_z, _ = sample_terrain(sample_pos.east, sample_pos.north,
                                       map_.terrain, map_.sea_surface)
        if sample_pos.altitude < terrain_z:
            return True  # 차폐됨
    return False
```

**의미**: Map 밖 지형은 **자유 전파 가정**. 사용자가 "Map 밖에 산이 있어 차폐"를 원하면 Map을
더 크게 만들어야 함. 이는 outside_environment 의 한계 (단순화 트레이드오프).

### 11.11.7 Coherence Validator 6번째 검사 (§ 11.7 확장)

```python
def validate_simulation_domain(map_: Map, scenario: Scenario) -> list[Warning]:
    warnings = []
    domain = scenario.simulation_domain_override or map_.simulation_domain

    # 1. Map ⊂ Simulation Domain
    if not domain_contains_map(domain, map_.bounds):
        warnings.append(SeverityError(
            "Simulation Domain이 Map보다 작음 — Map의 일부 지점이 시뮬 불가"
        ))

    # 2. 레이더 max range가 Domain 안에 들어가는가
    radar = scenario.radar_resource
    install_pos = scenario.platform_install
    radar_max_range = radar.estimated_max_range_m  # 레이더 방정식 + SNR 임계
    diag = sqrt((domain.bounds_east[1] - domain.bounds_east[0])**2 +
                (domain.bounds_north[1] - domain.bounds_north[0])**2)
    if radar_max_range > diag:
        warnings.append(SeverityWarn(
            f"레이더 max range ({radar_max_range/1000:.1f}km)가 "
            f"Simulation Domain 대각선 ({diag/1000:.1f}km)을 넘음. "
            f"먼 표적 시각화 누락 가능"
        ))

    # 3. 표적 trajectory가 Domain 안인가
    for t in scenario.targets_resource.targets:
        for wp in t.trajectory.waypoints:
            if not domain.contains(wp.east_m, wp.north_m, wp.altitude_m):
                warnings.append(SeverityError(
                    f"Target #{t.id} waypoint @t={wp.t_s}s가 Simulation Domain 밖"
                ))

    # 4. outside_environment 일관성
    outside = scenario.outside_environment_override or map_.outside_environment
    if outside == OutsideEnvironment.OPEN_SEA and not map_.has_sea_region:
        warnings.append(SeverityInfo(
            "outside_environment=open_sea지만 Map 안에 해상 영역 없음 — 의도적이면 OK"
        ))
    elif outside == OutsideEnvironment.BLOCKED:
        # Map 밖 trajectory가 있으면 사용자에게 명시적 경고
        for t in scenario.targets_resource.targets:
            for wp in t.trajectory.waypoints:
                if not map_.bounds.contains(wp.east_m, wp.north_m):
                    warnings.append(SeverityError(
                        f"outside=BLOCKED인데 Target #{t.id} waypoint가 Map 밖"
                    ))

    return warnings
```

### 11.11.8 Editor UI — Domain 설정

Map Editor에 신설 패널 (13 § 13.4 갱신):

```
┌─ Domain Settings ─────────────────────────────┐
│                                                │
│ Map bounds (정밀):  ±5 km E/N (terrain.npz)    │
│                                                │
│ Simulation Domain (시뮬 가능 전체):              │
│   East:   [±50000] m   (50 × 50 km)             │
│   North:  [±50000] m                            │
│   Ceiling:[30000]  m   (항공 표적 최대 고도)      │
│   Floor:  [-100]   m   (해저 허용)               │
│                                                │
│ Outside Map Environment:                       │
│   (•) Open Sea                                 │
│   ( ) Open Land                                │
│   ( ) Blocked  (Map 밖 진입 시 오류)             │
│   ( ) Infinite Plane (디버그용)                  │
│                                                │
│ ┌─ Coverage Preview ─────────────────────┐     │
│ │  [Simulation Domain]                    │     │
│ │      ┌─────────┐                       │     │
│ │      │  Map    │      ⬢ Radar          │     │
│ │      │ 10×10  │ 〰〰〰  Beam range arc  │     │
│ │      └─────────┘                       │     │
│ │   ●━━━●━━●  Target trajectory          │     │
│ │  (Map 밖 구간 — outside=open_sea)       │     │
│ └────────────────────────────────────────┘     │
└────────────────────────────────────────────────┘
```

Scenario Composer (13 § 13.3)에도 override 옵션:

```
┌─ Domain Override (선택) ───────────────────┐
│ ☐ Override SimulationDomain                │
│   (체크하면 Map 기본값 대신 사용자 정의)      │
│                                            │
│ ☐ Override Outside Environment             │
│   [Inherit from Map: open_sea ▾]            │
└────────────────────────────────────────────┘
```

### 11.11.9 MVP 범위

✅ **MVP**:
- Map의 SimulationDomain·OutsideEnvironment 필드
- Scenario override (composition에서)
- sample_terrain_safe 통합 함수
- 6번째 Validator 검사
- Map Editor·Scenario Composer UI

❌ **MVP+α**:
- Map 밖 영역도 단순 메시(cylinder·cone) 자동 생성 시각화
- Multi-Map (Simulation Domain 안에 여러 정밀 Map 영역)
- 영역별 다른 outside_environment (예: 동쪽은 sea, 서쪽은 land)

### 11.11.10 시각화 (PyVista 통합)

3D Scene View(02 § 2.6a)에서:
- Map 영역: 정밀 DEM mesh (smooth shading)
- Map 밖 ~ Simulation Domain: 단순 평면
  - open_sea면 sea_surface 평면 연장
  - open_land면 z=0 평지 연장
- Simulation Domain 경계: 흐릿한 박스 (선택, 디버그용)



- **EGM2008** 더 정밀한 geoid 모델 추가 (정확도 ~수십 cm)
- **시간 가변 datum** — 지각 변동 보정 (장기 시뮬에서)
- **Tide model** — 만조/간조 변동, sea_surface.z_at_sea_m이 시간 함수
- **다중 Map** — 한 시뮬에 여러 Map 영역 (전 지구 시뮬)
- **로컬 측지 datum** 라이브러리 (한국 KGD2002 등)

## 11.9 Open Questions

> 📍 **참고**: 본 § 11.9 와 § 11.8 미래 확장 은 § 11.10·§ 11.11 (v0.22~v0.29 신설) 보다
> 먼저 작성됐기 때문에 위치는 끝이지만 번호는 작음. 향후 재배치 시 § 11.12 / § 11.13 으로
> 이동 가능.

- DEM 해상도 표준 — 10m, 30m, 100m 중 기본? 사용자 선택?
- Map Origin을 변경하는 fork 작업 시 자동 변환 도구 (어제 Q3 자동 변환의 풀 구현)
- Vertical reference type별 변환 정확도 명시 — 어떻게 사용자에게 알릴까
- DEM 시각화의 z 과장 (verical exaggeration) 옵션? (산이 너무 평탄해 보일 때)
- 자체 규격 격자 해상도가 다른 Map 끼리 호환성 (예: 10m 격자 Map과 30m 격자 Map 사이 자원 이동)

## 섹션 상태

- 11.1~11.2 개요 — ✅
- 11.3 수평 좌표계 — ✅
- 11.4 수직 기준 — ✅ (핵심)
- 11.5 DEM Import 파이프라인 — ✅ (v0.22에서 외부 → 자체 규격 변환 흐름으로 재작성)
- 11.6 DEM 샘플링 — ✅
- 11.7 Coherence Validator — ✅ (MVP 검증 항목 6종, v0.29에서 Domain 검사 추가)
- 11.8 미래 확장 — 🟡
- 11.9 Open Questions — 🟡
- 11.10 Workbench Native Map Format — ✅ (v0.22 신설)
- 11.11 Simulation Domain — ✅ (v0.29 신설, Map + Outside Environment)

---

👉 다음: [12_placement_and_motion.md](12_placement_and_motion.md)
👉 이전: [10_workspaces.md](10_workspaces.md)
