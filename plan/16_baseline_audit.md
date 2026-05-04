# 16. Baseline Audit — 경쟁자 대비 베이스라인 점검 (v0.34)

**최종 갱신**: 2026-05-02 (v0.40 — § 16.9 Physics Lab 통합 신설, 17종 → 20+ 종 확장 + Validation Bench)

**관련 문서**: [01 vision_scope](01_vision_scope.md), [08 radar_waveforms](08_radar_waveforms.md), [14 dynamics_model](14_dynamics_model.md), [15 atmosphere_model](15_atmosphere_model.md)

## 16.1 왜 이 문서가 있나

차별점(추적 단일 표적 + DSP↔NN IDE + 4-error)에만 집중하면 **베이스라인이 부실해 신뢰를 못 얻는 위험**이 있다. MATLAB·Stone Soup·RadarSimPy·GPARM과 비교해 우리 시뮬의 RF/물리/동역학/추적 베이스라인을 점검하고, 부족한 점을 식별·결정한 결과를 정리한다.

비교 대상:
- **MATLAB Phased Array System Toolbox + Radar Toolbox + Sensor Fusion and Tracking Toolbox** — 사실상 업계 표준
- **Stone Soup** (UK Dstl, MIT 라이선스) — 추적·상태 추정 framework
- **RadarSimPy** (GPL+상용 dual) — 신호처리 라이브러리
- **GPARM (DSTO)** — 학술 참조 (RF environment + radar system)

## 16.2 점검 결과 요약

세 분류로 결정:

| 분류 | 개수 | 의미 |
|---|---|---|
| 🔴 **MVP 추가 필수** | 5 | 베이스라인 신뢰도 위해 필수, MATLAB 비교 demo의 최소 요건 |
| 🟡 **MVP+α 명시** | 10 | "알고 있고 계획에 있다"를 명시해 신뢰 회복 |
| ⚪ **의도적 제외** | 5 | "우리 niche 밖"을 명확히 |

## 16.3 MVP 추가 필수 (5종) — v0.34 결정

### 16.3.1 Two-ray Multipath (Q-BL1=a)

**문제**: 해상 시나리오에서 신호는 직접 경로(LOS) + 해수면 반사 경로 두 개로 와서 간섭. 거리·고도에 따라 lobing pattern 발생. 우리 핵심 시나리오가 함정 추적인데 빠져 있어 추적 안정성 검증의 의미가 약했다.

**MVP 사양**:
- 단순 평면 sea reflection 모델 (curvature 무시 — refraction이 별도 처리)
- Reflection coefficient: 단순화 — Fresnel from sea_surface 평균 (수직편파 -1, 수평편파 ≈ -1 at grazing angle)
- 직접 경로 vs 반사 경로의 phase 차 + amplitude 합성

**구현 위치**: `domain/propagation/multipath.py` (신규)

```python
def two_ray_path_loss(
    radar_pos_m: vec3,
    target_pos_m: vec3,
    sea_surface_z_m: float,
    frequency_hz: float,
    polarization: Literal["V", "H"] = "V",
) -> complex:
    """Two-ray multipath model. Returns complex path gain (vs free-space).

    직접 경로와 sea bounce reflection 경로의 phase 차를 계산해 합성.
    grazing angle 작을 때 reflection coefficient ≈ -1.
    """
    # Direct path
    R_direct = norm(target_pos_m - radar_pos_m)

    # Image of target under sea_surface
    target_image = target_pos_m.copy()
    target_image[2] = 2 * sea_surface_z_m - target_pos_m[2]
    R_reflected = norm(target_image - radar_pos_m)

    # Phase difference
    wavelength = 3e8 / frequency_hz
    delta_phase = 2 * np.pi * (R_reflected - R_direct) / wavelength

    # Reflection coefficient (단순화: grazing angle 가정)
    rho = -0.95  # near -1 at grazing angle for V/H polarization

    # Total field = direct + reflected (정규화)
    direct_field = 1.0 / R_direct
    reflected_field = rho * np.exp(-1j * delta_phase) / R_reflected

    total = direct_field + reflected_field
    free_space = 1.0 / R_direct  # reference
    return total / free_space  # complex gain (interference factor)
```

**Toggle 옵션**: Scenario에서 `multipath_enabled = true/false` 토글. 디버그·교육용 free-space 비교 가능.

**MVP+α 확장**: 토양·콘크리트 표면 반사, 다중 반사, rough surface scattering.

### 16.3.2 Multi-scatterer 표적 (Q-BL2=a) ⭐

**문제**: 점 표적이면 monopulse가 noise만 받음. 실제 추적의 핵심 어려움인 **glint** (extended target의 reflector 합성으로 도래각 흔들림)이 사라져 우리 차별점("단일 표적 추적 안정성")의 의미가 약하다.

**MVP 사양**:
- 표적은 **3~5개 reflector**로 구성 (Multi-scatterer point cloud)
- 각 reflector는 (offset_x, offset_y, offset_z, rcs_dbsm)
- 표적의 attitude (yaw/pitch/roll, v0.27 derived)에 따라 reflector 위치 회전
- 받음 신호 = 모든 reflector의 합성 (각 reflector마다 거리·phase 다름)
- **Glint 자동 발생**: reflector 간 phase 합성으로 monopulse error에 흔들림 생김

**구현 위치**: `domain/target_extended.py` (신규), `domain/scattering.py` (신규)

```python
@dataclass(frozen=True)
class Scatterer:
    offset_body_m: vec3       # 표적 body frame에서 위치
    rcs_dbsm: float           # 이 scatterer의 RCS (dBsm)


@dataclass(frozen=True)
class ExtendedTarget:
    """표적의 multi-scatterer 모델 (v0.34 MVP)."""
    target_id: str
    scatterers: tuple[Scatterer, ...]   # 보통 3~5개

    # Aspect-dependent RCS는 MVP+α — MVP는 각 scatterer 독립

def compute_extended_target_return(
    radar_pos_m: vec3,
    target: ExtendedTarget,
    target_state: RigidBodyState,    # v0.27, attitude 포함
    frequency_hz: float,
) -> complex:
    """모든 scatterer의 합성 받음 신호 (복소수). Glint 자동 발생."""
    total = 0j
    R_body_to_world = state_to_rotation_matrix(target_state)
    for s in target.scatterers:
        # body → world
        offset_world = R_body_to_world @ s.offset_body_m
        scatterer_pos = target_state.position_m + offset_world

        R = norm(scatterer_pos - radar_pos_m)
        wavelength = 3e8 / frequency_hz
        phase = 2 * np.pi * R / wavelength
        amplitude = np.sqrt(10**(s.rcs_dbsm / 10)) / R**2
        total += amplitude * np.exp(-1j * 2 * phase)  # round-trip
    return total
```

**표적 Preset 라이브러리 갱신** (v0.27 9종에 scatterer 분포 추가):
- `fighter_jet`: 5 scatterers (cockpit, nose, 양 wing tip, tail)
- `airliner`: 5 scatterers (cockpit, nose, 양 wing tip, tail)
- `missile_cruise`: 3 scatterers (nose, body, tail)
- `missile_ballistic`: 3 scatterers
- `drone`: 3 scatterers (body + 양 rotor)
- `artillery_shell`: 1 scatterer (작은 표적, 점에 가까움)
- `large_ship`: 5 scatterers (bow, midships, stern, mast, superstructure)
- `small_boat`: 3 scatterers
- `building`: 1 scatterer (점)

**MVP+α 확장**:
- Aspect-dependent RCS pattern (azimuth/elevation별 RCS 표)
- Frequency-dependent RCS
- Polarimetric scattering matrix
- Micro-Doppler (회전 부품)
- 더 많은 scatterer (10+개)

### 16.3.3 UKF + EKF/UKF 선택 가능 (Q-BL3=a + EKF 옵션)

**문제**: 현재 EKF만. 비선형성 큰 환경(고기동 표적·먼 거리)에서 EKF는 linearization 오차 누적. UKF는 sigma point로 더 안정. Stone Soup·MATLAB 모두 표준.

**MVP 사양**:
- `EKFTracker` (기존 v0.10) + `UKFTracker` (신규)
- 두 모두 동일 `Tracker` Protocol 구현
- Editor의 Radar Editor에서 **드롭다운으로 선택 가능** ("EKF / UKF")
- 기본값: EKF (역호환), 사용자 선택 시 UKF

**구현 위치**: `domain/tracker_ukf.py` (신규), `domain/tracker_ekf.py` (기존 리팩토링)

```python
class UKFTracker:
    """Unscented Kalman Filter. Sigma point 기반 비선형 추적."""

    def __init__(self, alpha: float = 1e-3, beta: float = 2.0, kappa: float = 0.0):
        # UKF 표준 파라미터 (Wan & van der Merwe 2000)
        ...

    def predict(self, state: TrackState, dt: float) -> TrackState: ...
    def update(self, state: TrackState, measurement: Detection) -> TrackState: ...
```

Stone Soup의 `UnscentedKalmanFilter`와 동일 알고리즘으로 (호환성 검증 가능).

**선택 가능 UI** (13 § 13.5 Radar Editor 갱신):

```
┌─ Tracking ───────────────────────────────┐
│ Tracker:  [EKF ▾]                        │
│           ├ EKF (default)                │
│           └ UKF (recommended for high    │
│                 maneuverability)         │
│                                          │
│ Process noise: [0.5] m/s²                │
│ Measurement noise: auto from radar       │
└──────────────────────────────────────────┘
```

**MVP+α**: Particle Filter, IMM (multiple model 평행 실행).

### 16.3.4 GNN 다중 표적 데이터 연관 (Q-BL4=a)

**문제**: 우리 추적은 단일 표적이지만 **환경에 다중 표적이 있어야 시뮬 의미** ("다중 환경에서 사용자가 선택한 단일 표적 추적"). 다중 표적이 있을 때 어느 detection이 우리 표적인지 판단해야 함.

**MVP 사양**:
- **GNN (Global Nearest Neighbor)** with Hungarian/Auction algorithm
- 모든 active detection과 모든 active track을 매트릭스로 cost (Mahalanobis distance) 계산
- 1:1 최적 assignment
- Stone Soup의 `GlobalNearestNeighbour` 와 동일 알고리즘

**구현 위치**: `domain/data_associator.py` (신규)

```python
class GNNDataAssociator:
    """Global Nearest Neighbor with Hungarian algorithm.

    추적 안정성 검증 시 다중 표적 환경의 최소 요건.
    """

    def associate(
        self,
        tracks: list[Track],
        detections: list[Detection],
        gating_threshold_sigma: float = 3.0,
    ) -> dict[Track, Optional[Detection]]:
        # 1. Cost matrix: Mahalanobis distance
        cost = np.full((len(tracks), len(detections)), np.inf)
        for i, t in enumerate(tracks):
            for j, d in enumerate(detections):
                m_dist = mahalanobis(d, t)
                if m_dist < gating_threshold_sigma:
                    cost[i, j] = m_dist

        # 2. Hungarian assignment (scipy.optimize.linear_sum_assignment)
        from scipy.optimize import linear_sum_assignment
        row_ind, col_ind = linear_sum_assignment(cost)

        # 3. 결과 dict
        result = {}
        for i, j in zip(row_ind, col_ind):
            if cost[i, j] < np.inf:
                result[tracks[i]] = detections[j]
            else:
                result[tracks[i]] = None
        return result
```

**Single-target 모드** (TRsim의 핵심): 사용자가 선택한 표적의 track만 active, 나머지 detection은 "clutter / 다른 표적"으로 무시. 그러나 **시뮬 자체는 다중 표적·detection 환경**.

**MVP+α**: JPDA (확률적 association), MHT (multi-hypothesis), IMM 결합.

### 16.3.5 Atmospheric Refraction (4/3 Earth Radius) (Q-BL5=a)

**문제**: 빔이 대기 중에서 휘어짐 (atmospheric refraction). 단순화로 "지구 반경의 4/3" 가정해 직선 빔으로 처리. MATLAB·GPARM 표준. 50km Simulation Domain에서 거리·고도 계산에 영향.

**MVP 사양**:
- Effective Earth Radius = 4/3 × 6378 km = 8504 km
- 기하 계산(LOS 차폐, range, elevation angle) 시 effective Earth 사용
- 빔 자체는 직선 (refraction을 Earth 곡률로 흡수)

**구현 위치**: `domain/propagation/refraction.py` (신규), `domain/geo.py` 갱신

```python
EARTH_RADIUS_M = 6378137.0   # WGS84
EFFECTIVE_EARTH_FACTOR = 4.0 / 3.0   # standard atmosphere

def effective_earth_radius_m(atm: AtmosphereState) -> float:
    """Effective Earth radius for refraction (4/3 standard).

    Future: refractivity_n에서 정밀 계산.
    """
    if atm.ducting_enabled:
        # MVP+α: ray tracing
        return EARTH_RADIUS_M * EFFECTIVE_EARTH_FACTOR  # placeholder
    # Standard: 4/3 earth
    return EARTH_RADIUS_M * EFFECTIVE_EARTH_FACTOR


def horizon_distance_m(observer_height_m: float, atm: AtmosphereState) -> float:
    """Distance to radio horizon."""
    R_eff = effective_earth_radius_m(atm)
    return np.sqrt(2 * R_eff * observer_height_m)
```

**LOS 차폐 검사 갱신** (11 § 11.11.6): Earth 곡률을 effective Earth로 보정. 단거리(< 5km)에서는 영향 작음, 장거리(> 10km)에서 의미 있음.

**MVP+α**:
- Refractivity profile N(h) 기반 정밀 ray tracing
- Ducting (anomalous propagation)
- Sub-refraction (negative gradient)

## 16.4 MVP+α 명시 (10종) — 차후 보강 항목

명시만 해도 "알고 있고 계획에 있다"로 신뢰 회복. 각 항목은 **트리거 시점**과 함께 명시.

| # | 항목 | 트리거 |
|---|---|---|
| 1 | **K-distribution sea clutter** | 고분해능 해상 시나리오 도입 시 (현재 단순 noise floor) |
| 2 | **Land clutter (gamma value)** | 지상 표적 시나리오 본격 도입 시 |
| 3 | **Aspect-dependent RCS pattern** | extended target에 polarimetric 추가 시 |
| 4 | **Frequency-dependent RCS** | 다중 주파수 시뮬 시 |
| 5 | **Micro-Doppler** | 표적 분류·식별 NN 학습 데이터 수요 시 |
| 6 | **Glint statistical model** (multi-scatterer 외 단순 모델) | 더 정밀한 glint 시나리오 시 |
| 7 | **Range glint** (range jitter) | 고정밀 거리 추적 시 |
| 8 | **DOA estimation (MUSIC, Root-MUSIC)** | DOA 별도 평가 모드 도입 시 |
| 9 | **Phase noise + ADC quantization** | RF 비이상성 본격 시뮬 시 |
| 10 | **Barrage / Spot jammer** | 추적 안정성 검증의 EW 시나리오 도입 시 |

## 16.5 의도적 제외 (5종) — Out of Scope 명시

"우리 범위가 아니다"를 명확히 해야 사용자 혼동 없음:

| # | 제외 항목 | 사유 |
|---|---|---|
| 1 | **STAP** (Space-Time Adaptive Processing) | 공중·우주 레이더 영역. 우리 niche(추적·해상·지상)와 다름. MATLAB Phased Array에 풍부 |
| 2 | **Massive MIMO / Hybrid beamforming** | 5G/SATCOM 통신 영역. 추적 레이더 niche 밖 |
| 3 | **SAR / ISAR** | 영상 영역 (Synthetic Aperture). 추적 도메인 아님 |
| 4 | **PHD / GM-PHD / LMB** (Random Finite Set 다중 표적) | 다중 표적 우선순위 낮음. Stone Soup·MATLAB 풍부 |
| 5 | **RIS** (Reconfigurable Intelligent Surface) | 신기술 통신 영역 |

이들이 필요하면 사용자는 MATLAB·Stone Soup을 써야 함. TRsim은 이 영역 추격 안 함.

## 16.6 Open Questions

- Q-BL6. Extended target에 Frequency-dependent RCS 추가 시점 — MVP+α 어디?
- Q-BL7. UKF의 sigma point 파라미터 (alpha/beta/kappa) UI 노출 여부
- Q-BL8. GNN의 gating threshold 자동 vs 수동
- Q-BL9. Two-ray multipath의 reflection coefficient 모델 정밀도 (MVP는 단순화 -0.95, 정밀은 Fresnel)
- Q-BL10. Refraction의 ducting 트리거 시점 (해상 시나리오에서 자주 발생)

## 16.7 베이스라인 점검 — 영향 받는 문서

| 문서 | 변경 |
|---|---|
| 01 vision_scope.md | MVP 표 5개 추가, Out of Scope 섹션 강화 |
| 02 architecture.md | § 2.9 모듈 도입 이력에 5개 신규 추가 |
| 03 data_model.md | `Scatterer`, `ExtendedTarget`, `EKFTracker`/`UKFTracker` Protocol |
| 04 migration.md | Phase 2에 5개 새 모듈 (multipath/scattering/tracker_ukf/data_associator/refraction) |
| 08 radar_waveforms.md | Two-ray multipath, OS-CFAR, refraction 섹션 추가 |
| 14 dynamics_model.md | Multi-scatterer 표적 모델 + Glint 자동 발생 섹션 |
| 15 atmosphere_model.md | § 15.x Refraction 추가 (4/3 earth) |

## 16.8 한 문장 요약

베이스라인 5개(Two-ray multipath / Multi-scatterer 표적 + Glint / UKF + EKF 선택 / GNN / Refraction) 추가로 MATLAB·Stone Soup 비교 demo의 신뢰 기반 확보. MVP+α 10개 명시 + 의도적 제외 5개 명시로 "알고 있고 결정했다"의 인식 확립. 차별점(추적 IDE + DSP↔NN + 4-error)에 자원 집중하면서도 베이스라인 부실 위험 회피.

## 16.9 Physics Lab 통합 (v0.40 신설)

> **출처**: 19 § 19.10 17종 검증 시나리오 통합 (PL-12)
> **권위**: 19 physics_lab

### 17종 검증 시나리오의 Physics Lab 안 통합

v0.39 까지: `tests/physics/` 의 pytest 로 Phase 5 에서 회귀 실행.
**v0.40 변경**: 검증 시나리오를 **Physics Lab > Validation Bench** 안에서 GUI + CLI 둘 다 실행 가능. Phase 5 의 검증 인프라 → Phase 9.1 의 Physics Lab 안으로 통합.

### 통합 후 시나리오 목록 (v0.40 기준)

#### 베이스라인 5종 (v0.34, MVP)
1. Two-ray multipath lobing
2. Multi-scatterer ExtendedTarget + glint emergence
3. EKF vs UKF tracking 비교
4. GNN data association
5. Refraction (4/3 earth)

#### MVP 추가 검증 (v0.34)
6. OS-CFAR vs CA-CFAR detection
7. Antenna sinc² pattern (-13 dB sidelobe)
8. Free space loss (Friis)
9. Doppler shift accuracy
10. Range bin resolution

#### Reference Timing 검증 (v0.39)
11. Stage timing 측정 정확도
12. Frame Profiler percentile 안정성

#### HIL 통합 검증 (v0.38)
13. GT vs SIL accuracy
14. SIL vs HIL bias
15. L4 paired matching

#### 합 17 + Physics Lab 신규 (v0.40)
16. Sphere free-fall (analytic vs RK4)
17. Trihedral RCS (boresight analytic)
18. ⭐ Force composition (gravity + drag)
19. ⭐ Test object dynamics (sphere bouncing)
20. ⭐ ExtendedTarget RCS (analytic vs Monte Carlo)

### Validation Bench 의 시각화 형식

각 시나리오 결과:
- **Analytic** (분석 공식, white line) vs **Implementation** (blue line) overlay
- RMSE / Max diff / Threshold 표시
- ✓ PASS / ✗ FAIL 상태
- FAIL 시 드릴다운 (해당 시점 시각화)

### CLI 대응 (Phase 9.1)

```bash
# 전체 회귀
trsim physics-lab validate --all

# 특정 시나리오
trsim physics-lab validate --scenario sphere_freefall

# Threshold 갱신 (의도된 수정)
trsim physics-lab validate --update-golden two_ray_multipath
```

### MVP 영향

- Phase 2: 17 ~ 20+ 시나리오 정의 (analytic_reference.py + golden_dataset/)
- Phase 5: 기본 회귀 가능 (CLI 만)
- Phase 9.1: Physics Lab GUI 통합 + 시각화

상세: [19 § 19.9 physics_lab.md](19_physics_lab.md).

## 섹션 상태

- 16.1 개요 — ✅
- 16.2 점검 결과 요약 — ✅
- 16.3 MVP 추가 5종 (Q-BL1~5 결정) — ✅
- 16.4 MVP+α 10종 — ✅
- 16.5 의도적 제외 5종 — ✅
- 16.6 Open Questions — 🟡
- 16.7 영향 문서 — ✅
- 16.8 요약 — ✅

---

👉 다음: [01_vision_scope.md](01_vision_scope.md) (MVP 표 갱신)
