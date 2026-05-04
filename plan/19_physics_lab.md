# 19. Physics Lab — 물리 모델 검증·디버깅·진화 환경 (v0.40 신설)

**최종 갱신**: 2026-05-02 (v0.40 신설)

**관련 문서**: [01 § 1.1 vision_scope](01_vision_scope.md), [02 § 2.3 architecture](02_architecture.md), [03 § 3.2.1o data_model](03_data_model.md), [04 § 4.3 Phase 9 migration](04_migration.md), [06 § 6.7 topics](06_topics.md), [16 baseline_audit](16_baseline_audit.md), [17 § 17.4.1 open_platform](17_open_platform.md)

---

## 19.1 왜 이 문서가 있나

TRsim 의 5번째 차별점 — **Physics Lab**. 물리 모델·코드를 한 곳에 모으고, 인터랙티브 3D 시각화로 검증·디버깅·진화.

### 통찰의 출처

사용자 통찰 13 (v0.40): "시뮬레이션의 핵심 = 물리. 물리 코드의 검증 환경 + 한 곳에 모음 필요."
사용자 통찰 14 (v0.40): "정지 상태만 다루면 가속도·중력 못 봄. 시간 1급 시민."
사용자 통찰 14b (v0.40): "Bret Victor 스타일 — 코드 + 시각화 + 파라미터 슬라이더. 모든 코드 파라미터 노출."

### 시나리오

```
[기존 — Physics Lab 없음]
물리 모델 코드 분산 (physics/, domain/dynamics/, domain/atmosphere/, domain/radar/...)
검증 = pytest 외부 도구 (tests/physics/, 17종)
디버깅 = 사용자가 코드 따라가며 print/breakpoint
진화 = 사용자가 IDE 외부에서 직접 코드 수정·검증
"이 모델 맞나?" 의문 = 외부 도구 + 분석 공식 외장

[Physics Lab — v0.40 후]
물리 모델 1 곳 (src/workbench/physics/)
검증 = IDE 안 인터랙티브 환경 (Lab Workspace)
디버깅 = 3-pane (Code | Visualization | Parameters), 시간 진화 시각화
진화 = 측정 데이터 → 파라미터 학습 → 사용자 검토 → 채택
"이 모델 맞나?" 의문 = 한 곳에서 분석 공식 + 시뮬 + 측정 데이터 비교
```

### 가치

| 측면 | 가치 |
|---|---|
| 검증 신뢰성 | 분석 공식 + 측정 데이터 + 17종 회귀를 한 곳에 |
| 디버깅 효율 | 3D 시각화로 물리 직관, 파라미터 슬라이더로 즉시 실험 |
| 학술 가치 | 학생·연구자가 물리 직접 보고 만짐 — 교육 도구 |
| 시장 차별 | 추적 IDE + 물리 시각화 + 측정 학습 통합은 시장에 부재 |
| 신뢰성 | Domain 에서 물리 분리로 추적 알고리즘 ↔ 물리 결합 약화 |

---

## 19.2 정체성·차별점에서의 위치

v0.39 까지 차별점 4 + 1.
v0.40 에서 **5 + 1** 로 확장:

1. 추적 알고리즘 검증 IDE
2. DSP ↔ NN 동일 인터페이스 비교
3. 4-error 진단
4. HIL 통합 (v0.38)
5. **Physics Lab** ⭐ v0.40 신규
6. ➕ DLC 에코시스템

### 한 줄 정의 (v0.40)

> **TRsim 은 추적 레이더 알고리즘·자원·시각화·물리 모델을 자유롭게 다루는 오픈소스 워크벤치 플랫폼이다.
> Apache 2.0 코어 + .trsim-pkg DLC 로 어떤 추적 시나리오라도 시뮬·검증·NN 학습 가능,
> HIL 통합으로 펌웨어·하드웨어 루프 검증, Reference Timing 으로 timing 정합,
> Physics Lab 으로 물리 모델 3D 시각화·검증·진화까지 지원한다.**

### 시장 비교

| 도구 | 추적 IDE | 물리 3D 시각화 | 측정 데이터 학습 | 비고 |
|---|---|---|---|---|
| MATLAB Phased Array | △ | △ | ❌ | Toolbox, commercial 비싼 |
| Stone Soup | ❌ | ❌ | ❌ | 라이브러리, 시각화 없음 |
| Ansys HFSS | ❌ | ⭐ | ❌ | RF 전용, 추적 X, 매우 비쌈 |
| AWR Visual System Sim | ❌ | ⭐ | ❌ | 시스템 시뮬, commercial |
| **TRsim Physics Lab** | ⭐ | ⭐ | ⭐ | 통합, 오픈소스 |

**시장 위치**: 추적 + 물리 시각화 + 측정 학습 통합은 **시장에 사실상 부재**. 5번째 차별점 명확.

---

## 19.3 핵심 설계 결정 (요약)

| ID | 결정 | 출처 |
|---|---|---|
| **PL-1** | Physics Layer 분리 — Domain 에서 물리 빼고 별도 계층 | v0.40 |
| **PL-2** | Physics Lab = 3번째 Workspace (Editor / Simulator / **Physics Lab**) | v0.40 |
| **PL-3** | 3-pane 인터랙티브 패턴 — Code / Visualization / Parameters | v0.40 |
| **PL-4** | 시간 1급 시민 — 4 모드 (Static / Run / Compare / Sweep) | v0.40 |
| **PL-5** | Test Objects 9 표준 — Sphere/Cube/Plate/Cylinder/Cone/Point/Plane/Wall/Trihedral | v0.40 |
| **PL-6** | 사용자 물리 plugin 가능 — PhysicsModelProtocol (11번째 SDK) | v0.40 |
| **PL-7** | Code Pane Hybrid — Read default, Edit mode toggle | v0.40 |
| **PL-8** | 파라미터 노출 — Decorator + type hints | v0.40 |
| **PL-9** | 외부 자료 = 측정 데이터 (CSV/HDF5) 우선 + 논문 PDF 참조 | v0.40 |
| **PL-10** | 형태 3 (논문 PDF → 자동 코드) 명시 제외 | v0.40 |
| **PL-11** | 06 § 6.7 영구 제외 결정 변경 — Test Bench 가 안전망 | v0.40 |
| **PL-12** | 17종 검증 시나리오 → Physics Lab 안으로 통합 (D-3=b) | v0.40 |
| **PL-13** | 차별점 5+1 (Q-PL-A=a) | v0.40 |
| **PL-14** | Phase 분산 — Phase 2 (코드 통합) + Phase 9 신설 (UI) | v0.40 |
| **PL-15** | 시각화 lib = pyqtgraph (2D) + PyVista (3D), 기존 활용 | v0.40 |

---

## 19.4 Physics Layer 분리

### 19.4.1 현재 분산 상태 (v0.39)

```
src/workbench/
├── physics/                  ← 좁은 의미 (FMCW, ray tracing)
├── domain/dynamics/          ← 사실 물리 (Newton, drag)
├── domain/atmosphere/        ← 사실 물리 (ISA, rain)
├── domain/radar/             ← 사실 물리 (multipath, RCS, antenna)
└── domain/platform.py        ← 사실 물리 (sea state)
```

**문제**: 물리가 5 군데 흩어져 있어 검증·디버깅·진화 어려움.

### 19.4.2 Physics Layer 통합 (v0.40)

```
src/workbench/physics/                ← 🆕 v0.40 통합 Physics Layer
├── propagation/                      ← RF 전파
│   ├── fmcw.py                       (← physics/ 기존)
│   ├── ray_tracing.py                (← physics/ 기존)
│   ├── multipath.py                  (← domain/radar/ 이동)
│   ├── refraction.py                 (← domain/atmosphere/ 이동)
│   ├── atmospheric_loss.py           (← domain/atmosphere/ 이동)
│   └── doppler.py                    (← domain/radar/ 이동)
│
├── reflection/                       ← RCS, 산란
│   ├── rcs_single.py
│   ├── rcs_aspect.py
│   ├── extended_target.py            (← domain/targets/ 이동)
│   └── glint.py                      (← domain/targets/ 이동)
│
├── dynamics/                         ← 표적·플랫폼 운동
│   ├── newton.py                     (← domain/dynamics/ 이동)
│   ├── aerodynamics.py               (← domain/dynamics/ 이동, lift+drag)
│   ├── motion_solver.py              (← domain/dynamics/ 이동, RK4)
│   └── platform_motion.py            (← domain/platform.py 이동, sea state)
│
├── atmosphere/                       ← 대기 모델
│   ├── isa.py                        (← domain/atmosphere/ 이동)
│   ├── rain.py                       (← domain/atmosphere/ 이동)
│   └── ducting.py                    (← domain/atmosphere/ 이동)
│
├── antenna/                          ← 빔 패턴
│   ├── parabolic.py                  (← domain/radar/ 이동)
│   ├── monopulse.py                  (← domain/radar/ 이동)
│   └── beam_pattern.py               (← domain/radar/ 이동)
│
├── geometry.py                       ← 좌표·방향 (← physics/ 기존)
│
└── _testbench/                       ← Physics Lab 검증 코드
    ├── analytic_reference.py         ← 분석 공식 reference
    ├── golden_dataset/               ← 알려진 reference 값 (Stone Soup, MATLAB 등)
    └── plot_helpers.py               ← 3D 시각화 헬퍼
```

### 19.4.3 Domain Layer 변경

```
src/workbench/domain/
├── radar/                  ← RadarConfig dataclass + DSP Pipeline metadata
│                              (물리 측 multipath/RCS/antenna 는 physics/ 로 이동)
├── targets/                ← Target dataclass + MotionKind enum
│                              (RCS 계산, dynamics 는 physics/ 로 이동)
├── tracker/                ← Tracker, Predictor, DataAssociator (DSP)
├── detector/               ← OS-CFAR, CA-CFAR (DSP)
├── pairing/                ← Up/down 매칭 (DSP)
├── platform/               ← Maritime / Fixed Ground 메타
│                              (운동은 physics/ 로 이동)
└── ... (자원·DSP 알고리즘만)
```

**원칙**:
- **Domain = 자원 모델 + DSP 알고리즘**
- **Physics = 물리 법칙·수식·시뮬**
- 명확 분리로 결합 약화

### 19.4.4 의존 방향

```
ui → app → domain → physics → primitives (numpy, scipy)
                       ↑
                       │
                  physics 는 domain 에 의존 X
                  (낮은 계층, 순수 함수 위주)
```

**원칙**:
- physics 는 domain 모름 (domain 객체 import X)
- physics 는 numpy/scipy/순수 Python 만
- domain 이 physics 함수 호출
- ui 와 app 은 physics 직접 사용 가능 (Physics Lab UI)

---

## 19.5 3-pane 인터랙티브 패턴

### 19.5.1 레이아웃

```
┌──────┬───────────────────────────┬──────────────────────────────────┐
│      │                           │                                   │
│      │   ┌─ Code Pane ─────────┐ │   ┌─ Visualization Pane ────────┐ │
│ Left │   │ (read/edit toggle)  │ │   │  (2D / 3D + animation)      │ │
│ Side │   │                     │ │   │                              │ │
│ Bar  │   │ def gravity_force:  │ │   │      ●                       │ │
│      │   │     g = 9.81        │ │   │      │ velocity              │ │
│ Tests│   │     return -m*g     │ │   │      ▼                       │ │
│      │   │                     │ │   │                              │ │
│ Models│  │ def update(s, dt):  │ │   │  ━━━━━━━━━━━━━━ ground       │ │
│      │   │     s.v += a*dt     │ │   │                              │ │
│ Library│ │     s.p += s.v*dt   │ │   │  Time controls               │ │
│      │   │                     │ │   │  [▶ Play] [⏸] [⏹]            │ │
│      │   │                     │ │   │  ◀━━━━━━━━━━━●━━━━━━━━━▶     │ │
│      │   │                     │ │   │  [◀] [▶] frame-by-frame      │ │
│      │   └─────────────────────┘ │   └──────────────────────────────┘ │
│      │                           │                                    │
│      ├───────────────────────────┴──────────────────────────────────┤ │
│      │   Parameters (모든 파라미터 슬라이더)                         │ │
│      │   Mass:   [─────●────] 1.0 kg     Radius: [─●──────] 0.1 m    │ │
│      │   Height: [───●──────] 5.0 m      Restit: [──────●─] 0.8       │ │
│      │   Gravity:[──────●───] 9.81 m/s²  Drag Cd: [●──────] 0.47      │ │
│      └────────────────────────────────────────────────────────────────┘
```

### 19.5.2 좌측 Sidebar — Test 선택

3 카테고리:

```
▼ Tests (현재 활성)
   ⬢ Gravity + Bouncing Ball ⭐
   ⬡ Aircraft Trim
   ⬡ FMCW Sweep
   ⬡ Two-ray Multipath
   ⬡ ExtendedTarget RCS
   ⬡ Sea State + Platform Motion
   ⬡ Atmospheric Refraction

▼ Models (사용 가능 물리)
   ☑ Gravity
   ☐ Air Drag
   ☐ Magnus Effect
   ☐ Lift
   (cycle 따라 다름)

▼ Library
   📊 Measured Data (3)
      - boeing_737_rcs.csv
      - rain_attenuation_meas.csv
      - drone_drag_coef.csv
   📄 Papers (5)
      - Smith2023_multipath.pdf
      - Knott_RCS_handbook.pdf
   ✓ Saved Experiments (2)
      - my_validation_run_001
      - drag_coef_fit_v2
```

### 19.5.3 Code Pane (PL-7 Hybrid)

#### Read mode (default)

```python
# physics/dynamics/aerodynamics.py
@physics_param(name="g", min=0, max=20, scale="linear", unit="m/s²")
@physics_param(name="m", min=0.1, max=100, scale="log", unit="kg")
def gravity_force(m: float, g: float = 9.81) -> float:
    """Gravity force on point mass.

    F = m * g (downward)
    """
    return -m * g
```

- syntax highlight
- 함수·docstring 표시
- 파라미터 (decorator) hover 시 tooltip
- 편집 X (read-only)

#### Edit mode (toggle 활성화)

```
[ Read ] | [ Edit ] ← toggle button
                ↓ click
[ Read ] | [ Edit ] ← active
                     ⚠ Warning: Edit mode 활성. 코드 변경 시 검증 필요.
```

- 편집 가능
- 파라미터 변경 (decorator min/max 등)
- 새 함수 추가
- 저장 시 validation (syntax / type / 파라미터 metadata)
- 위험 명시 (warning banner)

### 19.5.4 Visualization Pane

#### 2D / 3D 자동 선택

물리별 적합:
- Ball + Gravity → 3D (PyVista)
- FMCW signal → 2D (pyqtgraph)
- Antenna pattern → 3D (PyVista)
- Spectrum (FFT) → 2D (pyqtgraph)
- Multipath → 3D (ray tracing)

모델 metadata 에서 선택:
```python
@physics_test(name="gravity_bouncing", visualization="3d")
def gravity_bouncing_test(...):
    ...
```

#### 시간 컨트롤 (PL-4)

| 버튼 | 동작 |
|---|---|
| ▶ Play | 시뮬 진행 (real-time 또는 sim-time) |
| ⏸ Pause | 일시 정지 (frame 보존) |
| ⏹ Stop | 시작 시점 reset |
| ◀━━●━━▶ | 시간 슬라이더 (임의 시점 jump) |
| ◀ ▶ | Frame-by-frame (Left/Right arrow 단축키) |
| Speed | 0.5x / 1x / 2x / 5x |

#### 시각 요소

```
3D scene 의 표준 요소:
- Test Objects (Sphere, Cube, etc.)
- Trajectory (line, time 따라)
- Velocity vector (arrow, real-time)
- Force vectors (arrow, gravity / drag / lift)
- Coordinate axes (origin)
- Reference grid (option)
- 색: 시간·속도·magnitude 따라
```

### 19.5.5 Parameters Pane (PL-8)

#### 자동 노출 메커니즘

```python
# Decorator (명시적)
@physics_param(name="mass", min=0.1, max=100, scale="log", unit="kg")
@physics_param(name="radius", min=0.01, max=1.0, scale="linear", unit="m")
@physics_param(name="restitution", min=0.0, max=1.0, scale="linear", unit="-")
def bouncing_ball(mass, radius, restitution):
    ...

# Type hints (Python 표준)
from typing import Annotated
def free_space_loss(
    range_m: Annotated[float, PhysicsParam(min=1, max=100000, scale="log", unit="m")],
    freq_hz: Annotated[float, PhysicsParam(min=1e6, max=1e12, scale="log", unit="Hz")]
) -> float:
    ...
```

#### Slider scale 규칙

| 파라미터 type | 권장 scale | 비고 |
|---|---|---|
| Range, freq, time, power | log | 5+ decade 범위 흔함 |
| RCS | log | 0.001 ~ 1000 m² |
| Angle, ratio (0~1) | linear | 자연 스케일 |
| Mass, distance (좁은 범위) | linear | 5 decade 미만 |
| 정수 count | stepper (linear, integer step) | 1.7 의미 없음 |
| 음수 가능 | linear | log 부적합 |
| 0 가능 | linear | log(0) = -∞ |

#### 출력 plot axis 별도

- 입력 슬라이더 scale ≠ 출력 plot axis
- 출력 plot 우측 상단에 [Linear / Log] toggle
- 사용자가 plot axis 별도 선택

### 19.5.6 라이브 갱신

```
파라미터 슬라이더 변경
   ↓
on_change 트리거
   ↓
시뮬 다시 실행 (또는 incremental update)
   ↓
3D scene + 2D plot 갱신
   ↓
지연 < 100ms (UX 기준)
```

성능 고려:
- 단순 모델: 매 frame 재실행
- 복잡 모델 (sweep): debounce 적용
- 매우 복잡: 진행 표시 + cancel 가능

---

## 19.6 시간 차원 (PL-4) — 4 모드

### 19.6.1 모드 1: Static

- 시간 X, 정지 상태 한 점
- 예: "range 1km 에서 free space loss"
- 빠른 sanity check
- Time controls 비활성

### 19.6.2 모드 2: Single Run

- 시간 진화 한 trajectory
- 예: "0~10 초 자유낙하 + bouncing"
- Play/Pause/Stop/슬라이더 활성
- 가장 자주 사용

### 19.6.3 모드 3: Compare (Time-Series 비교)

- 두 모델의 시간 진화 동시
- 예: "BALLISTIC 분석 공식 vs RK4 구현"
- Overlay / Split / Diff 표시 (사용자 선택)
- 분석 vs 구현 검증

표시 옵션:
- Overlay: 한 plot 에 두 line (다른 색)
- Split: 좌우 또는 상하 분할
- Diff: 차이만 plot

### 19.6.4 모드 4: Sweep

- 파라미터 batch + 시간 진화
- 예: "초기 높이 1~10m sweep, 각 trajectory 표시"
- 결과: 다중 trajectory overlay 또는 heatmap (파라미터 × 시간)

### 19.6.5 PhysicsClock

```python
# domain/physics_lab/clock.py
class PhysicsClock:
    """Physics Lab 의 격리된 시간 인스턴스.
    SimulationClock 과 분리 — Physics Lab 만의 시뮬 진행."""
    sim_t_s: float
    state: Literal["STOPPED", "PLAYING", "PAUSED"]
    speed: float  # 0.5 / 1 / 2 / 5
    dt: float

    def play(self): ...
    def pause(self): ...
    def stop(self): ...
    def step_frame(self, direction: Literal["forward", "backward"]): ...
    def jump_to(self, t_s: float): ...
```

**메인 SimulationClock 과 별개** — Physics Lab 격리, 메인 시뮬 영향 X.

### 19.6.6 frame 단위 결정성

Reference Timing (v0.39) 의 같은 원칙:
- 같은 시드 + 같은 입력 + 같은 dt → 같은 결과
- frame 단위 snapshot
- 시간 슬라이더 jump 도 결정적

---

## 19.7 Test Objects (PL-5) — 9 표준

### 19.7.1 정의

각각 **분석 공식이 알려진** 단순 객체:

```python
# domain/physics_lab/test_objects.py

@dataclass(frozen=True)
class TestObject:
    """Physics Lab 의 표준 검증 객체."""
    name: str
    mass_kg: float
    visual: Literal["sphere", "cube", "plate", "cylinder", "cone",
                    "point", "plane", "wall", "trihedral"]

@dataclass(frozen=True)
class Sphere(TestObject):
    radius_m: float
    drag_coefficient: float = 0.47   # smooth sphere, Reynolds 따라
    visual: str = "sphere"

@dataclass(frozen=True)
class Cube(TestObject):
    side_length_m: float
    visual: str = "cube"

@dataclass(frozen=True)
class Plate(TestObject):
    width_m: float
    height_m: float
    normal_direction: tuple[float, float, float]  # 법선 벡터
    visual: str = "plate"

@dataclass(frozen=True)
class Cylinder(TestObject):
    radius_m: float
    length_m: float
    axis_direction: tuple[float, float, float]
    visual: str = "cylinder"

@dataclass(frozen=True)
class Cone(TestObject):
    base_radius_m: float
    height_m: float
    apex_direction: tuple[float, float, float]
    visual: str = "cone"

@dataclass(frozen=True)
class Point(TestObject):
    """무한소 점질량 — 순수 dynamics 용."""
    visual: str = "point"

@dataclass(frozen=True)
class Plane(TestObject):
    """무한 평면 — 지면, 반사면."""
    point: tuple[float, float, float]
    normal: tuple[float, float, float]
    mass_kg: float = 0  # 정지
    visual: str = "plane"

@dataclass(frozen=True)
class Wall(TestObject):
    """유한 사각 평면 — 벽, 장애물."""
    center: tuple[float, float, float]
    width_m: float
    height_m: float
    normal: tuple[float, float, float]
    mass_kg: float = 0
    visual: str = "wall"

@dataclass(frozen=True)
class Trihedral(TestObject):
    """3면 corner reflector — RCS 측정 표준."""
    center: tuple[float, float, float]
    side_length_m: float
    orientation: tuple[float, float, float, float]  # quaternion
    visual: str = "trihedral"
```

### 19.7.2 분석 공식 reference

각 객체별로:

| 객체 | 분석 RCS | 분석 dynamics |
|---|---|---|
| Sphere | πr² (large), 2πr⁵/λ⁴ (Rayleigh) | drag = ½ρv²C_d πr² |
| Cube | aspect 별 면적 합 | drag with C_d ≈ 1.05 |
| Plate | 4πA²/λ² (broadside) | 1D 회전 |
| Cylinder | 2πrl²/λ (broadside) | 회전체 |
| Trihedral | 12πa⁴/λ² | 정지 (반사용) |

`physics/_testbench/analytic_reference.py` 에 구현.

### 19.7.3 시각화

PyVista 의 표준 메시:
```python
pv.Sphere(radius=r)
pv.Cube(x_length=s, y_length=s, z_length=s)
pv.Plane(center=p, direction=n, i_size=w, j_size=h)
pv.Cylinder(center=c, direction=d, radius=r, height=l)
pv.Cone(center=c, direction=d, radius=r, height=h)
# Point: 작은 sphere or marker
# Trihedral: 3 plates 조합
```

### 19.7.4 plugin 미래

PL-5 결정: 9 표준 + plugin 미래.

```python
# 미래 — 사용자 정의 Test Object
class CustomTestObject(TestObject):
    """플러그인 — 사용자 정의."""
    visual: str = "custom"
    def render(self, plotter): ...
```

MVP 에서는 9 표준만, MVP+α 에서 plugin 가능.

---

## 19.8 PhysicsModelProtocol (PL-6, 11번째 SDK)

### 19.8.1 정의

```python
# sdk/protocols.py

class PhysicsModelProtocol(Protocol):
    """Physics Lab 에서 호출 가능한 물리 모델 표준.
    11번째 Plugin Protocol (v0.40)."""

    @property
    def name(self) -> str:
        """모델 이름 (e.g., 'gravity', 'two_ray_multipath')."""
        ...

    @property
    def category(self) -> Literal["dynamics", "rf_propagation", "rcs", "atmosphere", "antenna", "other"]:
        """카테고리."""
        ...

    @property
    def parameters(self) -> list[PhysicsParam]:
        """파라미터 metadata (자동 슬라이더 생성용)."""
        ...

    @property
    def time_mode(self) -> Literal["static", "dynamic"]:
        """static = 정지 함수, dynamic = 시간 진화."""
        ...

    def compute(self, state: dict, params: dict, dt: float | None) -> dict:
        """물리 계산.

        Args:
            state: 현재 상태 (position/velocity 등)
            params: 사용자 슬라이더 파라미터
            dt: time step (static 모드 시 None)

        Returns:
            새 state (또는 결과)
        """
        ...

    @property
    def visualization(self) -> Literal["2d", "3d", "both"]:
        """기본 시각화 차원."""
        ...

    def render(self, state: dict, plotter) -> None:
        """3D 시각화 (PyVista plotter 활용)."""
        ...
```

### 19.8.2 분류 (12개로 확장 — 11 + DUTAdapter v0.38)

| # | Protocol | 역할 | 도입 |
|---|---|---|---|
| 1 | DetectorProtocol | CFAR detection | v0.13 |
| 2 | PairingProtocol | Up/down 매칭 | v0.13 |
| 3 | AngleEstimatorProtocol | sum-channel + monopulse | v0.25 |
| 4 | TrackerProtocol | EKF/UKF/etc. | v0.13 |
| 5 | PredictorProtocol | Track prediction | v0.13 |
| 6 | ClassifierProtocol | Track classification | v0.13 |
| 7 | DataAssociatorProtocol | GNN/JPDA | v0.34 |
| 8 | ResourceProtocol | Map/Radar/Target loader | v0.20 |
| 9 | UIPanelProtocol | DLC UI 패널 | v0.35 |
| 10 | DUTAdapterProtocol | HIL DUT 통신 + Lock-step | v0.38 |
| **11** | **PhysicsModelProtocol** | **Physics Lab 모델** | **v0.40** ⭐ |

### 19.8.3 06 § 6.7 결정 변경 (PL-11)

**기존 (v0.27 → v0.39)**: "사용자 정의 물리 모델 plugin — 영구 제외" (위험성 ↑).

**변경 (v0.40)**: "사용자 정의 물리 모델 plugin **가능** — Physics Lab Validation Bench 가 안전망".

근거:
- Physics Lab 의 17종 회귀 + 분석 공식 + 측정 데이터 비교가 안전망
- Test Bench 통과 plugin 만 시뮬에 적용 가능
- 학술·연구 가치 매우 높음

조건:
- PhysicsModelProtocol 구현
- Physics Lab Validation Bench 통과 (자동 17종 회귀)
- 측정 데이터 비교 (option)
- 사용자 검토 후 채택

---

## 19.9 외부 자료 통합 (PL-9, 10)

### 19.9.1 측정 데이터 (CSV/HDF5) — 우선

```python
# 사용자 흐름
[1] Physics Lab > Library > Add Measured Data
[2] CSV 또는 HDF5 업로드
[3] Schema 자동 감지 또는 사용자 명시
   - 시계열: time, value
   - sweep: parameter, value
   - 다차원: multiple columns
[4] 메타 정보 입력 (출처, 측정 조건, 라이선스)
[5] Lab-A (Inspector) 또는 Lab-C (Studio) 에서 활용
```

표준 schema:
```yaml
# measured_data.yaml
name: "Boeing 737 RCS measurements"
source: "Knott RCS Handbook 1993, p.245"
measurement_conditions:
  freq_hz: 9.4e9
  angle_resolution_deg: 1.0
  range_m: 1000
data_file: "boeing_737_rcs.csv"
columns:
  - aspect_angle_deg
  - rcs_m2
license: "Public domain (textbook)"
```

### 19.9.2 논문 PDF — 참조용 (PL-10)

**명시 제외**: PDF → 자동 코드 생성 (형태 3).

**포함**: PDF 라이브러리 + 모델 metadata 인용.

```python
# physics 모델에 출처 명시
@physics_model(
    name="ITU-R rain attenuation",
    paper="ITU-R Recommendation P.838-3, 2005",
    paper_url="library/papers/itu-r_p838.pdf"
)
class ITURRainAttenuation:
    ...
```

Physics Lab Library 에서:
- PDF 업로드·검색·tag
- 모델별 출처 표시
- 참조 가능 (사용자가 보고 직접 구현)

### 19.9.3 형태 1 (파라미터 학습)

```
[사용자] 측정 데이터 업로드 (CSV)
   ↓
[Lab-C] 기존 모델 선택 (예: ExtendedTarget)
   ↓
[Lab-C] 측정 데이터 vs 모델 비교 plot
   ↓
[Lab-C] "Fit parameters" 버튼
   ↓
[Lab-C] scipy.optimize 또는 NN 으로 parameter fit
   ↓
[Lab-A] 3D 시각화 — 측정 vs fit 결과 overlay
   ↓
[사용자] 검토 → 채택 (학습된 파라미터 저장)
   ↓
[Editor Workspace] 채택된 파라미터 사용 가능
```

### 19.9.4 형태 5 (검증·비교)

```
[Lab-B] 측정 데이터 업로드
   ↓
[Lab-B] 시뮬 결과 계산 (현재 모델 + 파라미터)
   ↓
[Lab-B] Overlay plot — 측정 vs 시뮬
   ↓
[Lab-B] Metrics: RMSE, max diff, correlation
   ↓
[사용자] 정량적 평가 후 모델 신뢰성 판단
```

### 19.9.5 미래 형태들 (점진)

- **형태 2 (NN 대체)**: Phase 9.2~ — Phase 6 NN 통합과 결합
- **형태 4 (Symbolic regression)**: Phase 9.3+ — PySR 같은 도구 통합
- **형태 3 (논문 PDF → 자동 코드)**: 명시 제외 (현재 기술 한계)

---

## 19.10 17종 검증 시나리오 통합 (PL-12, D-3=b)

### 19.10.1 기존 (v0.39)

`tests/physics/` 에 17종:
1. Free space loss
2. Friis equation
3. Two-ray multipath
4. Multi-scatterer RCS
5. Glint
6. EKF vs UKF
7. GNN association
8. Refraction
9. Atmospheric attenuation
10. Doppler shift
11. FMCW signal
12. Pairing
13. Beam pattern
14. ExtendedTarget
15. Sea state
16. Aircraft dynamics
17. OS-CFAR vs CA-CFAR

→ pytest 외부 도구.

### 19.10.2 통합 (v0.40)

각 검증 시나리오 = Physics Lab 의 **Saved Test**.

```
Physics Lab > Library > Saved Tests (17 + α)
   ☐ Free space loss
   ☐ Friis equation (verify against analytic)
   ☐ Two-ray multipath
   ...
   [Run All] — 자동 회귀
```

흐름:
- Physics Lab 안에서 each test 시각화·검증
- 회귀 테스트는 자동 (Run All)
- 결과: pass/fail + 시각 비교

`tests/physics/` 는 보존 — pytest CI 에서도 동작 (Physics Lab UI 와 같은 데이터 사용).

### 19.10.3 사용 시나리오

```
사용자 = Physics Lab 의 다른 테스트 작성:
   - 새 multipath 모델 plugin
   - Library 에 추가
   - "Validate against Two-ray analytic" 자동 실행
   - 결과: ✓ pass / ✗ fail + diff plot

CI = Run All:
   - pytest tests/physics/ → 17 + α 모두 회귀
   - 회귀 시 알람
```

---

## 19.11 Phase 분산 (PL-14)

### 19.11.1 MVP (Phase 2 ~ 5)

#### Phase 2: Physics Layer 통합
- [ ] `src/workbench/physics/` 디렉토리 재배치
- [ ] domain 에서 물리 코드 이동 (dynamics / atmosphere / radar / platform)
- [ ] PhysicsModelProtocol 정의 (sdk/protocols.py)
- [ ] PhysicsParam metadata (decorator + type hints)
- [ ] Test Objects 9 dataclass

#### Phase 4: Physics Lab Workspace 기본
- [ ] `ui/physics_lab/` 디렉토리
- [ ] WorkspaceManager 에 Physics Lab 추가 (Editor / Simulator / Physics Lab)
- [ ] 기본 3-pane 레이아웃 (빈 상태)

#### Phase 5: 17종 검증 통합
- [ ] 17종 시나리오 → Physics Lab Saved Tests 로 마이그레이션
- [ ] Run All UI

### 19.11.2 MVP+α (Phase 9 신설)

#### Phase 9.1 — Lab 본체 (3-pane 풀)
- [ ] Code Pane (Read mode)
- [ ] Visualization Pane (PyVista 3D + pyqtgraph 2D)
- [ ] Parameters Pane (자동 슬라이더 생성)
- [ ] Time controls (Play/Pause/Stop/Slider/Frame-by-frame)
- [ ] Test Objects 9 시각화 구현
- [ ] PhysicsClock 인스턴스
- [ ] 4 모드 (Static / Run / Compare / Sweep)
- [ ] Library — Tests / Models / Saved Experiments
- [ ] **첫 예시: Gravity + Bouncing Ball + Air Drag toggle**

#### Phase 9.2 — 외부 자료 + 학습
- [ ] Library — Measured Data 업로드 (CSV/HDF5)
- [ ] Library — Papers (PDF) 업로드
- [ ] Lab-B Validation Bench (측정 vs 시뮬)
- [ ] Lab-C Parameter Studio (form 1: scipy.optimize fit)
- [ ] 사용자 검토 → 채택 워크플로

#### Phase 9.3 — 고급 기능
- [ ] Code Pane Edit mode
- [ ] PhysicsModel plugin (사용자 정의, PhysicsModelProtocol)
- [ ] NN 으로 물리 대체 (form 2, Phase 6 NN 결합)
- [ ] Symbolic regression (form 4, PySR)
- [ ] Test Object plugin

---

## 19.12 사용 시나리오 — 전체 흐름

### 19.12.1 시나리오 1 — Gravity 검증 (Phase 9.1)

```
[1] 사용자가 Physics Lab Workspace 열음
[2] Library > Tests > "Gravity + Bouncing Ball" 선택
[3] Code Pane: gravity_force 함수 표시 (read-only)
[4] Visualization Pane: 공 + 지면 (3D)
[5] Parameters Pane: mass / radius / restitution / gravity / initial height 슬라이더
[6] [▶ Play] 클릭 → 공이 떨어지고 튕김 (애니메이션)
[7] 사용자가 "Restitution" 슬라이더 0.8 → 0.5 변경 → 즉시 재시뮬, 덜 튕김
[8] Mode: Compare → 분석 공식 (피크 높이) vs 시뮬 비교 → 99.8% 일치 ✓
```

### 19.12.2 시나리오 2 — RCS 측정 데이터 검증 (Phase 9.2)

```
[1] Library > Measured Data > "Add" → "boeing_737_rcs.csv" 업로드
[2] Schema: aspect_angle [deg], rcs [m²]
[3] Lab-B Validation Bench
[4] 모델 선택: "ExtendedTarget" (multi-scatterer)
[5] 시뮬 vs 측정 overlay plot
[6] RMSE: 4.2 dB
[7] [Fit parameters] → scipy.optimize 로 산란점 위치·강도 fit
[8] 새 RMSE: 0.8 dB ✓
[9] 사용자 검토 → "Accept" → 학습된 파라미터 저장
[10] Editor Workspace 의 ExtendedTarget 모델에서 사용 가능
```

### 19.12.3 시나리오 3 — 새 multipath 모델 plugin (Phase 9.3)

```
[1] 사용자가 새 multipath 모델 작성 (4-ray, plate-edge)
[2] PhysicsModelProtocol 구현, .trsim-pkg 패키지
[3] Plugin Manager 에서 install
[4] Physics Lab Library > Models 에 자동 등록
[5] Lab-A Inspector 에서 시각화 (4 ray 3D)
[6] Lab-B Validation Bench → "Validate against Two-ray analytic"
   - Far-field 영역: ✓ pass (4-ray ≈ 2-ray)
   - Near-field 영역: 다름 (예상)
[7] Saved Tests > "4-ray multipath validation" 저장
[8] CI 회귀 통과
[9] 시뮬 시나리오에서 사용 가능
```

---

## 19.13 디렉토리 구조 영향

### 19.13.1 src/workbench/physics/ (재배치)

§ 19.4.2 참조.

### 19.13.2 src/workbench/domain/physics_lab/ (신규)

```
domain/physics_lab/
├── physics_clock.py      ← 격리된 시간
├── time_modes.py         ← 4 모드 (Static / Run / Compare / Sweep)
├── test_objects.py       ← 9 표준 dataclass
├── parameter_metadata.py ← @physics_param decorator
├── lab_session.py        ← Lab 세션 상태
└── library/              ← Library 관리
    ├── measured_data.py
    ├── papers.py
    └── saved_experiments.py
```

### 19.13.3 src/workbench/app/physics_lab/ (신규)

```
app/physics_lab/
├── lab_runner.py          ← 시뮬 실행
├── parameter_fitter.py    ← form 1 (scipy.optimize)
├── validator.py           ← form 5 (측정 vs 시뮬)
└── data_importer.py       ← CSV/HDF5 import
```

### 19.13.4 src/workbench/ui/physics_lab/ (신규)

```
ui/physics_lab/
├── workspace.py           ← Workspace 진입
├── code_pane.py           ← Code Pane (read/edit)
├── viz_pane/              ← Visualization Pane
│   ├── pyvista_view.py
│   ├── pyqtgraph_view.py
│   └── time_controls.py
├── params_pane.py         ← Parameters Pane (자동 슬라이더)
└── library_panel.py       ← Library sidebar
```

---

## 19.14 Open Questions (Q-PL 시리즈)

### Q-PL1. 시각화 라이브러리 일관성
- **출처**: § 19.5.4
- **결정 시점**: Phase 9.1 구현 시
- **현재 가정**: 2D = pyqtgraph, 3D = PyVista (TRsim 기존 일관)

### Q-PL2. 측정 데이터 표준 형식
- **출처**: § 19.9.1
- **결정 시점**: Phase 9.2
- **현재 가정**: CSV (간단) + HDF5 (복잡) 둘 다, 메타 YAML 동행

### Q-PL3. 분석 공식 reference 출처 우선
- **출처**: § 19.7.2
- **결정 시점**: Phase 5 통합 시
- **현재 가정**: 표준 / 책 / 논문 — 표준 (ITU-R 등) 우선

### Q-PL4. 사용자 plugin 검증 임계값
- **출처**: § 19.8.3
- **결정 시점**: Phase 9.3
- **현재 가정**: 분석 공식과 95%+ 일치 후 채택 권장 (모델별 조정)

### Q-PL5. 17종 통합 시 plot 형태
- **출처**: § 19.10
- **결정 시점**: Phase 5
- **현재 가정**: 자동 시각화 (각 test 의 visualization metadata 따라)

### Q-PL6. Phase 6 NN 결합 시점
- **출처**: § 19.9.5
- **결정 시점**: Phase 6 ~ 9.2 사이
- **현재 가정**: NN 통합 안정 후 Phase 9.2 또는 9.3

### Q-PL7. Symbolic regression 도구
- **출처**: § 19.9.5
- **결정 시점**: Phase 9.3
- **현재 가정**: PySR (Python 친화) 우선, 대안 AI Feynman

### Q-PL8. 학습 vs 외삽 영역 표시
- **출처**: § 19.9.5
- **결정 시점**: Phase 9.2
- **현재 가정**: 시각적 (학습 영역 = 진한 색, 외삽 = 흐림 + 경고)

### Q-PL9. 논문 PDF 검색·tag 시스템
- **출처**: § 19.9.2
- **결정 시점**: Phase 9.2
- **현재 가정**: 텍스트 검색 + 사용자 정의 tag (간단)

### Q-PL10. PhysicsModelProtocol 의 보안
- **출처**: § 19.8.1
- **결정 시점**: Phase 9.3
- **현재 가정**: DLC 시스템과 같은 sandbox 정책 (17 § 17.10)

### Q-PL11. Code Pane Edit 의 hot reload
- **출처**: § 19.5.3
- **결정 시점**: Phase 9.3
- **현재 가정**: importlib.reload + 단순 재실행 (복잡 hot reload X)

### Q-PL12. PhysicsClock 과 메인 SimulationClock 연동
- **출처**: § 19.6.5
- **결정 시점**: Phase 9.1 후
- **현재 가정**: 기본 격리, 옵션으로 메인 시뮬과 sync (Q-PL-K=c)

### Q-PL13. Sweep 모드의 결과 저장
- **출처**: § 19.6.4
- **결정 시점**: Phase 9.1
- **현재 가정**: Saved Experiment 로 저장, library 에서 재로드

### Q-PL14. Test Object plugin 시점
- **출처**: § 19.7.4
- **결정 시점**: Phase 9.3
- **현재 가정**: MVP+α 후, 사용자 요청 시

### Q-PL15. 측정 데이터의 시간 시계열 형식
- **출처**: § 19.9.1
- **결정 시점**: Phase 9.2
- **현재 가정**: CSV 첫 컬럼 = time (단순), HDF5 의 time dataset (구조화)

---

## 19.15 한 문장 요약

**TRsim 의 5번째 차별점 — Physics Lab 으로 흩어진 물리 코드를 한 곳에 모으고, Bret Victor 스타일 3-pane 인터랙티브 환경 (Code | Visualization | Parameters) + 시간 1급 시민 + 9 표준 Test Objects + 측정 데이터 학습 + 사용자 plugin 으로 물리 모델을 검증·디버깅·진화 가능. Domain 에서 물리 분리 (Physics Layer 신설), 17종 검증 통합, 06 § 6.7 영구 제외 결정 변경. 추적 IDE + 물리 시각화 + 측정 학습 통합은 시장 부재 — 학술·교육·산업 모두 가치.**

---

## 섹션 상태

- 19.1 동기·시나리오 — ✅
- 19.2 정체성 위치 — ✅
- 19.3 핵심 결정 (PL-1~15) — ✅
- 19.4 Physics Layer 분리 — ✅
- 19.5 3-pane 패턴 — ✅
- 19.6 시간 4 모드 — ✅
- 19.7 Test Objects 9 — ✅
- 19.8 PhysicsModelProtocol (11번째) — ✅
- 19.9 외부 자료 통합 — ✅
- 19.10 17종 검증 통합 — ✅
- 19.11 Phase 분산 — ✅
- 19.12 사용 시나리오 — ✅
- 19.13 디렉토리 영향 — ✅
- 19.14 Open Questions — ✅
- 19.15 요약 — ✅

---

👉 다음: [00_README.md](00_README.md)
👉 이전: [18_hil_integration.md](18_hil_integration.md)
