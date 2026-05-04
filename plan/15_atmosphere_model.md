# 15. Atmosphere Model — 시각·동역학·전파 영향

**최종 갱신**: 2026-04-28 (v0.34)

**관련 문서**: [12 placement_and_motion](12_placement_and_motion.md), [14 dynamics_model](14_dynamics_model.md), [08 radar_waveforms](08_radar_waveforms.md), [11 coordinate_systems](11_coordinate_systems.md)

## 15.1 왜 이 문서가 있나

추적 레이더 시뮬은 본질적으로 **레이더 신호가 대기 매질을 통해 전파**되는 환경에서 동작한다.
또한 표적은 **공기 중에서 동역학 운동**한다 (양력·항력은 공기 밀도 함수). 사용자는 또한
**시각적으로 환경 분위기**를 직관 얻기를 원한다.

v0.28에서 대기 상태를 **세 측면 모두** 다룬다 (Q-A1 결정):

| 측면 | 영향 받는 것 | 처리 |
|---|---|---|
| **시각적** (a) | 3D Scene View — fog, 하늘색, 시정 | PyVista 셰이더·post-process |
| **동역학** (b) | 표적 운동 — air_density (양력·항력) | 14 § 14.4 외력 계산 |
| **전파** (c) | 레이더 신호 — rain attenuation, ducting | 08 § 8.x 신호 모델 |

## 15.2 핵심 결정

### 15.2.1 단일 AtmosphereState 추상 (v0.28)

세 영향 모두를 하나의 데이터로 결정:

```python
@dataclass(frozen=True)
class AtmosphereState:
    """Map의 대기 상태. Scenario 단위로 1개 (시간 가변은 MVP+α)."""

    # 시정·시각 (a)
    visibility_km: float = 30.0          # 시정 거리 — fog density
    sky_condition: str = "clear"         # "clear" / "overcast" / "fog" / "rain" / "storm"

    # 공기 (b) — 동역학 영향
    sea_level_pressure_hpa: float = 1013.25
    sea_level_temperature_k: float = 288.15
    # 고도별은 ISA 모델로 계산 (15 § 15.3)

    # 전파 (c) — 신호 영향
    rain_rate_mmh: float = 0.0           # 강우율 0=없음, ITU-R P.838 모델
    refractivity_n: float = 313.0        # N-units, ducting 모델용 (15 § 15.5)
    ducting_enabled: bool = False        # MVP+α 토글

    # 외란 (MVP+α)
    wind_velocity_mps: vec3 = (0, 0, 0)  # 풍향·풍속 (동역학)
```

### 15.2.2 MVP 범위

✅ **MVP 포함**:
- ISA 표준 대기 (압력·온도·밀도의 고도 함수)
- visibility_km (시각용 — fog effect)
- sky_condition (시각용 — 하늘 색)
- rain_rate_mmh (전파용 — 강우 감쇠 ITU-R P.838)

❌ **MVP+α**:
- ducting (수직 굴절률 프로파일, beam bending)
- wind_velocity (동역학 외란)
- 시간 가변 atmosphere (시뮬 중 변화)
- 구름·번개·정밀 시각 효과

## 15.3 ISA 표준 대기 (Level 1 — MVP)

### 15.3.1 모델

International Standard Atmosphere (ISA) 1976. 본 워크벤치는 **트로포스피어**(0~11 km)만
지원 (대부분의 표적 시나리오 충분):

```python
def isa_density(altitude_m: float, atm: AtmosphereState) -> float:
    """ISA 표준 대기 밀도 (kg/m³). MVP는 troposphere만."""
    T0 = atm.sea_level_temperature_k        # 288.15 K
    P0 = atm.sea_level_pressure_hpa * 100   # Pa
    L = 0.0065                              # K/m, 표준 lapse rate
    R = 287.058                             # J/(kg·K), specific gas constant
    g = 9.80665

    if altitude_m < 11000:
        # Troposphere
        T = T0 - L * altitude_m
        P = P0 * (T / T0) ** (g / (R * L))
    else:
        # MVP는 11km 위는 11km 값 고정 (clamp)
        T = T0 - L * 11000
        P_11 = P0 * (T / T0) ** (g / (R * L))
        P = P_11
        # MVP+α: stratosphere model

    return P / (R * T)


def isa_temperature(altitude_m: float, atm: AtmosphereState) -> float:
    if altitude_m < 11000:
        return atm.sea_level_temperature_k - 0.0065 * altitude_m
    return atm.sea_level_temperature_k - 0.0065 * 11000
```

### 15.3.2 동역학 통합

14 § 14.4의 항력·양력 계산이 `air_density_kgm3 = 1.225` (sea level)에서 ISA 함수로 변경:

```python
def compute_drag(state: RigidBodyState, params: DynamicsParams,
                 atm: AtmosphereState) -> vec3:
    rho = isa_density(state.altitude_m, atm)
    v_norm = norm(state.velocity)
    drag_mag = 0.5 * rho * params.drag_coefficient * params.reference_area_m2 * v_norm**2
    return -drag_mag * state.velocity / v_norm
```

이로써 **고고도 표적은 항력·양력이 자동 감소**, 사실적.

## 15.4 시각적 표현 — PyVista 셰이더 (Level 1 — MVP)

### 15.4.1 Sky color & fog

```python
def setup_atmosphere_visuals(plotter: pv.Plotter, atm: AtmosphereState):
    # 1. Sky background
    sky_colors = {
        "clear":    ("lightblue", "white"),       # 위→아래
        "overcast": ("gray", "lightgray"),
        "fog":      ("lightgray", "lightgray"),
        "rain":     ("darkgray", "gray"),
        "storm":    ("dimgray", "darkgray"),
    }
    top, bottom = sky_colors[atm.sky_condition]
    plotter.set_background(bottom, top=top)

    # 2. Fog (visibility 기반)
    if atm.visibility_km < 50.0:
        plotter.enable_depth_of_field()  # 단순 fog approximation
        # 실제 fog 거리 = visibility_km × 1000 m
        plotter.set_fog(start=atm.visibility_km * 500,
                       end=atm.visibility_km * 1000)
```

### 15.4.2 Rain visualization (선택)

`rain_rate_mmh > 0` 면 비 입자 셰이더 (MVP+α). MVP는 **하늘 색만 변경**.

### 15.4.3 사용자 컨트롤

Editor의 Map Editor 또는 Scenario Composer에 atmosphere 패널:

```
┌─ Atmosphere ────────────────────────────────┐
│ Sky condition: [Clear ▾] (Clear/Overcast/   │
│                          Fog/Rain/Storm)     │
│ Visibility:    [30.0]  km                   │
│ Sea-level T:   [15.0]  °C  (288.15 K)        │
│ Sea-level P:   [1013.25] hPa                 │
│ Rain rate:     [0.0]   mm/h                  │
│ ☐ Enable ducting (MVP+α)                    │
│ ☐ Enable wind  (MVP+α)                      │
└─────────────────────────────────────────────┘
```

## 15.5 전파 영향 — 신호 모델 (Level 1 — MVP)

### 15.5.1 Rain attenuation (ITU-R P.838 단순화)

강우 감쇠는 주파수 의존:

```python
def rain_attenuation_dbpkm(frequency_ghz: float, rain_rate_mmh: float) -> float:
    """ITU-R P.838 specific attenuation. MVP는 X-band 영역만 정밀.

    Returns dB/km.
    """
    if rain_rate_mmh <= 0:
        return 0.0

    # X-band (8-12 GHz) 근사 계수
    if 8.0 <= frequency_ghz <= 12.0:
        k = 0.0117 * frequency_ghz - 0.0734  # 단순 선형 보간
        alpha = 1.097
    elif frequency_ghz < 8.0:
        # MVP는 X-band 외 단순화 (덜 정확)
        k = 0.001
        alpha = 1.0
    else:
        k = 0.05 * (frequency_ghz / 10.0)
        alpha = 1.1

    return k * (rain_rate_mmh ** alpha)
```

### 15.5.2 Two-way attenuation 적용

레이더 방정식에서 표적까지 거리 R, 그 경로의 감쇠:

```python
def two_way_loss_db(target_range_m: float, atm: AtmosphereState,
                    radar_freq_hz: float) -> float:
    range_km = target_range_m / 1000.0
    freq_ghz = radar_freq_hz / 1e9
    L_per_km = rain_attenuation_dbpkm(freq_ghz, atm.rain_rate_mmh)
    # 왕복이므로 ×2
    return 2.0 * L_per_km * range_km
```

이 손실은 **수신 신호 SNR**에서 빼짐 → 표적이 약하게 보임 → 추적 알고리즘이 더 어려운 환경.

08 § 8.x의 RadarModel.compute_received_power에서 호출.

### 15.5.3 Ducting (MVP+α)

대기 굴절률 N(h)이 표준에서 벗어나면 빔 경로가 휘어짐 (anomalous propagation).
MVP+α에서:
- 사용자가 N(h) 프로파일 입력
- ray tracing으로 빔 경로 계산
- 시각화에 굴곡 빔 표시

MVP는 ducting_enabled=False 고정 (직선 전파).

### 15.5.4 Atmospheric Refraction — 4/3 Earth Radius (v0.34 MVP)

**문제**: 빔이 표준 대기 중에서도 약간 휘어짐 (positive gradient of refractivity). 단순 기하 계산은 직선 빔 가정인데 장거리(>10km)에서 거리·고도 오차 발생. 50km Simulation Domain에서는 의미 있음.

**해결 — 4/3 Earth Trick** (Schelleng 1933, 표준):

대기 refraction을 Earth 곡률에 흡수해 **빔은 직선 + Earth는 4/3 배 큰 가짜 Earth** 로 처리.

```python
EARTH_RADIUS_M = 6378137.0           # WGS84
EFFECTIVE_EARTH_FACTOR = 4.0 / 3.0   # 표준 대기 (k-factor)

def effective_earth_radius_m(atm: AtmosphereState) -> float:
    """Effective Earth radius for refraction. v0.34 MVP는 4/3."""
    if atm.ducting_enabled:
        # MVP+α: 정밀 N(h) ray tracing
        return EARTH_RADIUS_M * EFFECTIVE_EARTH_FACTOR  # placeholder
    return EARTH_RADIUS_M * EFFECTIVE_EARTH_FACTOR


def horizon_distance_m(observer_height_m: float, atm: AtmosphereState) -> float:
    """레이더 horizon (radio horizon)."""
    R_eff = effective_earth_radius_m(atm)
    return np.sqrt(2 * R_eff * observer_height_m)


def line_of_sight_geometry(
    radar_pos_m: vec3,
    target_pos_m: vec3,
    atm: AtmosphereState,
) -> LOSResult:
    """Effective Earth로 LOS 거리·각도 계산."""
    R_eff = effective_earth_radius_m(atm)
    # Earth curvature 보정 (effective Earth surface 기준)
    ...
```

**효과**:
- 단거리 (< 5km): 영향 거의 없음
- 중거리 (5~20km): 약간의 elevation angle 보정 (~0.05°)
- 장거리 (> 20km): horizon distance 증가, 차폐 검사·빔 도달 거리 영향

**적용 위치**:
- LOS 차폐 검사 (11 § 11.11.6) — Earth curvature 보정으로 빔 도달 가능 영역 더 넓어짐
- Geometric range 계산 (직선 거리는 그대로지만 elevation angle 변화)
- Horizon distance (장거리 표적이 horizon 너머 가는지 판단)

**MVP+α**:
- Refractivity profile N(h) 기반 정밀 ray tracing
- Sub-refraction (negative gradient → k < 1, beam bending downward 반대)
- Super-refraction → ducting (15 § 15.5.3과 통합)
- 시간·공간 가변 N(h) (해상 vs 육상)

## 15.6 데이터 파일

Map의 `map.toml`에 atmosphere 섹션:

```toml
[atmosphere]
visibility_km = 30.0
sky_condition = "clear"
sea_level_pressure_hpa = 1013.25
sea_level_temperature_k = 288.15
rain_rate_mmh = 0.0
refractivity_n = 313.0
ducting_enabled = false
```

또는 Scenario `[composition]`에서 override 가능 (같은 Map에 다른 날씨 시나리오).

## 15.7 동역학·전파·시각 통합

세 측면이 동시에 영향:

**시나리오 예시: 폭우 시 함정 추적**
```toml
[atmosphere]
sky_condition = "storm"      # 시각: 어두운 하늘
visibility_km = 5.0          # 시각: fog 효과
rain_rate_mmh = 50.0         # 전파: rain attenuation 강함
sea_level_temperature_k = 285  # 동역학: 약간 낮은 air density
```

결과:
- 3D Scene View가 어둡고 fog 낀 분위기
- 표적 항공기는 air density가 약간 낮아 항력·양력 약간 변화 (작음)
- 레이더 SNR이 ~5 dB 손실 (X-band, 50 mm/h)
- 추적 알고리즘이 어려운 조건 — 검증 시나리오로 가치

## 15.8 검증 (Coherence Validator 확장)

11 § 11.7에 atmosphere 검사 추가:

- visibility_km == 0 → 오류 (의미 없음)
- rain_rate_mmh > 200 → 경고 ("비현실적")
- frequency 외 X-band 사용 시 rain attenuation 모델 정확도 경고

## 15.9 MVP 구현 우선순위

### MVP 핵심
- [ ] `AtmosphereState` 데이터 타입
- [ ] ISA density·temperature 함수
- [ ] 14 § 14.4 외력 계산을 ISA 기반으로 갱신
- [ ] 08 RadarModel에 rain_attenuation_dbpkm 통합
- [ ] PyVista sky_condition·fog 시각화
- [ ] Atmosphere 편집 UI (Scenario Composer)
- [ ] **Atmospheric refraction (4/3 earth radius)** — `effective_earth_radius_m()`, `horizon_distance_m()`, LOS 차폐 검사 보정 (v0.34)

### MVP+α
- [ ] Stratosphere ISA (11~50 km)
- [ ] Ducting 모델 (refractivity 프로파일, ray tracing)
- [ ] Wind 외란 (동역학)
- [ ] 시간 가변 atmosphere (시뮬 중 변화)
- [ ] 비·구름 입자 셰이더
- [ ] ITU-R P.838 풀 정밀도

## 15.10 Open Questions

- 풀 ISA (11+ km) 도입 시점 — 고고도 표적 시나리오 핵심?
- Ducting 모델 정밀도 — ray tracing 비용 vs 효과
- Wind을 motion_kind별로 다르게? (지상 vehicle은 무시 가능)
- Atmosphere가 시간 가변 시 GT 일관성 (NN 학습 데이터 영향)

## 섹션 상태

- 15.1 개요 — ✅
- 15.2 핵심 결정 (단일 추상, 세 측면) — ✅
- 15.3 ISA 표준 대기 — ✅ (MVP는 트로포스피어)
- 15.4 시각적 표현 — ✅ (PyVista)
- 15.5 전파 영향 — ✅ (ITU-R P.838 + Refraction 4/3 v0.34)
- 15.6 데이터 파일 — ✅
- 15.7 통합 시나리오 — ✅
- 15.8 검증 확장 — ✅
- 15.9 MVP 우선순위 — ✅
- 15.10 Open Questions — 🟡

---

👉 이전: [14_dynamics_model.md](14_dynamics_model.md)
