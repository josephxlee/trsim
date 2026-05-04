# 02. 아키텍처 설계

**최종 갱신**: 2026-05-02 (v0.40 — § 2.6c Physics Layer 분리 신설, physics/ 디렉토리 큰 재배치, app/physics_lab + ui/physics_lab Workspace)

## 2.1 설계 원칙 (가장 먼저 합의해야 할 것)

### 원칙 1: UI가 얇다 (Thin Shell)

GUI 시뮬레이터의 흔한 실패 패턴은 `MainWindow` 가 1,500줄+ God Class 가 되는 것. 이걸 반복하지 않는다.

**규칙**:
- `MainWindow`는 **조립과 레이아웃만** 한다. 비즈니스 로직 금지.
- 모든 "기능"은 Command, Panel, Service 중 하나에 속한다.
- 어떤 클래스도 300줄을 넘으면 리뷰 대상.

### 원칙 2: 의존 방향은 안쪽으로

```
   [UI Layer]          ← 가장 바깥, 의존 많음
       │ 의존
       ▼
   [Application Layer] ← Command, Service, Plugin Loader
       │ 의존
       ▼
   [Domain Layer]      ← Scenario, Radar Pipeline, Physics
       │ 의존
       ▼
   [Primitives]        ← 순수 함수, 데이터 클래스
```

**안쪽은 바깥쪽을 모른다.** Domain은 Qt를 import하지 않는다.

### 원칙 3: 플러그인이 일급 시민

사용자 DSP 코드가 "외부에서 주입되는 확장"이 아니라
**기본 구현과 동일한 취급**을 받도록 설계한다.
즉 기본 Detector도 Plugin 프로토콜로 구현되어 있다.

### 원칙 4: 모든 상태는 관찰 가능 (Observable)

Probe/Trace 시스템이 파이프라인의 모든 중간 결과를 기록할 수 있어야 한다.
이를 위해 **불변(immutable) 데이터 구조**를 기본으로 한다.
`@dataclass(frozen=True)` 원칙.

### 원칙 5: 실시간 가능, 하지만 실시간에 묶이지 않음

- 시뮬 계산은 최대 속도 가능
- 재생은 사용자가 속도 조절 가능 (0.1x ~ 10x)
- 렌더링과 계산은 **별도 스레드**
- 일시 정지/시크 자연스럽게 동작

### 원칙 6: HIL 통합 + AWG 확장 (v0.38)

신호 생성·수신 경계를 인터페이스로 노출:
- **TX 측 (SignalSink)**: SIL 기본, HIL 어댑터로 교체 가능
- **RX 측 (DUTAdapter)**: v0.38 신설 — 외부 DUT (펌웨어·FPGA·DSP) 의 결과 수신·평가
- **3-way 비교**: GT vs SIL vs HIL — 펌웨어 정확도 + DUT-Bias (펌웨어 vs Python gap) 정량화

상세: 18 hil_integration.md.

---

## 2.2 전체 블록도

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              UI Layer (Qt)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  WorkspaceManager 🆕 v0.19  (Editor / Simulator 전환)                │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ Editor Workspace 🆕 v0.19~v0.26 ────────────────────────────────────┐ │
│  │  ActivitySelector | ResourceBrowser (상시)                            │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │ │
│  │  │ Scenario │ │   Map    │ │  Radar   │ │ Targets  │ │ Resource │   │ │
│  │  │ Composer │ │  Editor  │ │  Editor  │ │  Editor  │ │  Browser │   │ │
│  │  │  (메인)  │ │  (경량)  │ │ (v0.25)  │ │ (메타)   │ │  (full)  │   │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │ │
│  │  Domain Settings 🆕 v0.29 | Atmosphere Panel 🆕 v0.28                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ Simulator Workspace ────────────────────────────────────────────────┐ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │ │
│  │  │ Scenario │ │  FFT /   │ │  Range-  │ │  Plugin  │ │   Run    │   │ │
│  │  │ Explorer │ │ Spectrum │ │ Doppler  │ │  Manager │ │  Panel   │   │ │
│  │  │ (Dock)   │ │ (Dock)   │ │ (Dock)   │ │ (Dock)   │ │ (Dock)   │   │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────────────────────────┐ │ │
│  │  │ Stage IO │ │Properties│ │  3D Scene View (PyVista) 🆕 v0.28    │ │ │
│  │  │ (v0.14)  │ │ (Dock)   │ │   DEM smooth + 파도 + atmosphere fog │ │ │
│  │  └──────────┘ └──────────┘ └──────────────────────────────────────┘ │ │
│  │  NN Mode (Step 1 Dataset / Step 2 Eval) 🆕 v0.13                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ToolBar (Sim Layer / Target Layer) v0.15                                  │
│  MenuBar | CommandPalette | StatusBar                                      │
│  DockManager (Workspace별 독립 저장) | ThemeManager                         │
│                                                                            │
│  Visualization stack: pyqtgraph (data) + PyVista (3D Scene) 🆕 v0.28      │
└────────┬─────────────────────────────────────────────────────────────────┘
         │ Signal/Slot, read-only data access
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          Application Layer                                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────┐    │
│  │ CommandRegistry  │  │  PluginLoader    │  │  RunManager         │    │
│  │  (모든 액션)      │  │  (DSP 동적로드)   │  │  (Target Run)       │    │
│  └──────────────────┘  └──────────────────┘  └─────────────────────┘    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────┐    │
│  │ ScenarioService  │  │ SimulationClock  │  │  ProbeRecorder      │    │
│  │  (로드·저장)      │  │  v0.15           │  │  (중간값 기록)       │    │
│  └──────────────────┘  └──────────────────┘  └─────────────────────┘    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────┐    │
│  │  Evaluator       │  │  PhysicsGate     │  │  EventBus            │    │
│  │  (GT 대비 메트릭) │  │  (건전성 체크)    │  │  (pub/sub)           │    │
│  └──────────────────┘  └──────────────────┘  └─────────────────────┘    │
│                                                                            │
│  ┌─────────────────────────────────────────┐  ┌─────────────────────┐   │
│  │         CommandBus v0.14                 │  │ InputBuffer          │   │
│  │  Tracker/Manual/InitialScan              │  │ (Sim PAUSED 중)      │   │
│  │         ↓ (유일한 경로)                   │  │ v0.15                │   │
│  │        Positioner                        │  └─────────────────────┘   │
│  └─────────────────────────────────────────┘                              │
│                                                                            │
│  ┌─ Resource & Workspace 🆕 v0.19~v0.20 ──────────────────────────────┐  │
│  │  WorkspaceManager       (Editor/Simulator 전환, DockLayout 저장)    │  │
│  │  ResourceLibrary        (maps/radars/targets 인덱스)                │  │
│  │  ResourceCache          (content_hash 기반 in-memory 캐시)          │  │
│  │  BundleService          (.scnbundle/.runbundle export·import)      │  │
│  │  CoherenceValidator     (6종 일관성 검사 v0.21~v0.29)               │  │
│  │  DEMImportPipeline      (외부 DEM → terrain.npz, v0.22)             │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌─ NN (MVP+α — Phase 6) ──────────────────────────────────────────────┐ │
│  │  DataExporter | DatasetBuilder (Variant 6) | TrainerService |        │ │
│  │  NNEvaluator (4-error 진단 v0.13)                                   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ DLC System 🆕 v0.35 (MVP+α — Phase 7) ─────────────────────────────┐ │
│  │  PackageManager        (.trsim-pkg install/uninstall, ~/.trsim/...)  │ │
│  │  PanelRegistry         (DLC가 추가한 UI 패널 등록·조회)               │ │
│  │  ResourceLibrary 확장  (User > Packages > Built-in 우선순위)         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└────────┬─────────────────────────────────────────────────────────────────┘
         │ method call (UI 무관)
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  Plugin SDK Layer 🆕 v0.35 (안정 API)                     │
│  protocols.py — 9 Plugin Protocol                                          │
│  (Detector / Pairing / AngleEstimator / Tracker / Predictor /              │
│   Classifier / DataAssociator / Resource / UIPanel)                        │
│  resource_schemas.py — TOML 스키마 (Map/Radar/Target)                      │
│  package_builder.py — `trsim sdk build` (디렉토리 → .trsim-pkg)            │
│  package_validator.py — manifest 검증                                      │
│  test_harness.py — `trsim sdk test` (DLC 로컬 테스트)                      │
│                                                                            │
│  의존: Domain만. App·UI·Physics 직접 참조 ❌                                │
│  DLC 코드는 SDK만 import (Core 변경에서 격리)                              │
└────────┬─────────────────────────────────────────────────────────────────┘
         │ method call
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            Domain Layer                                   │
│                                                                            │
│  ┌─ Pipeline ──────────────────┐  ┌─ Contracts ──────────────────────┐  │
│  │  Scenario (불변 문서)        │  │  6 Protocol:                     │  │
│  │  RadarPipeline (6 스테이지)  │  │    Detector / AngleEstimator /   │  │
│  │  Environment (반사·클러터)   │  │    Pairing / Tracker /           │  │
│  │                              │  │    Predictor / Classifier        │  │
│  │                              │  │  PositionerCommand·CommandSource │  │
│  └──────────────────────────────┘  └──────────────────────────────────┘  │
│                                                                            │
│  ┌─ Map & Coordinates 🆕 v0.21~v0.29 ──────────────────────────────────┐ │
│  │  GeoOrigin (불변) | VerticalReference (egm96/wgs84/...)              │ │
│  │  Map (id, bounds, terrain, sea_surface, buildings, content_hash)     │ │
│  │  WorkbenchTerrain (grid + land_mask, v0.22)                          │ │
│  │  CoastlinePolygon | SeaSurface                                       │ │
│  │  SimulationDomain + OutsideEnvironment 🆕 v0.29                      │ │
│  │  sample_terrain_safe()  ← Map 안 정밀 / 밖 outside 정책               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ Placement & Motion 🆕 v0.21~v0.27 ─────────────────────────────────┐ │
│  │  PlacedEntity (base_*) | CurrentPose (Sim 동적)                      │ │
│  │  MotionKind 7종 v0.27 (FIXED/GROUND_VEHICLE/SURFACE_VESSEL/          │ │
│  │                        FLOATING_STATIC/AIRCRAFT/POWERED_FLIGHT/      │ │
│  │                        BALLISTIC)                                    │ │
│  │  WaveResponseModel (4 프리셋) | SeaStateEnvironment                  │ │
│  │  BuildingEntity (Anchor 4 mode) | TargetEntity                       │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ Dynamics 🆕 v0.27 ──────────────────────────────────────────────────┐ │
│  │  RigidBodyState | Forces (gravity/drag/lift/thrust/control)          │ │
│  │  DynamicsParams (motion_kind별: Aircraft/PoweredFlight/Ballistic/...)│ │
│  │  DynamicsSolver (RK4 적분, dt=0.05s + sub 0.005s)                    │ │
│  │  motion_models.compute_forces_for_motion_kind()                      │ │
│  │  ImpactDetector (BALLISTIC 지면 충돌)                                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ Atmosphere 🆕 v0.28 ────────────────────────────────────────────────┐ │
│  │  AtmosphereState (visibility/sky/pressure/temp/rain_rate/...)        │ │
│  │  ISA density·temperature 함수 (Dynamics에 air_density 공급)          │ │
│  │  rain_attenuation_dbpkm() — ITU-R P.838 (RadarPipeline에 SNR 손실)   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ Antenna 🆕 v0.25 ───────────────────────────────────────────────────┐ │
│  │  AntennaType enum (PARABOLIC / PLANAR_ARRAY)                         │ │
│  │  AntennaConfig Protocol — beam_pattern(), beamwidth(), peak_gain()   │ │
│  │  ParabolicAntenna (sinc²) | PlanarArrayAntenna (array factor)        │ │
│  │  RXChannelKind (Σ/Δaz/Δel/Δ²) | MonopulseRXConfig                    │ │
│  │  monopulse error_az/el_rad 계산 (Σ·Δ 비율 → Tracker 입력)            │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ Platform 🆕 v0.18~v0.24 ────────────────────────────────────────────┐ │
│  │  RadarPlatform (Maritime / Fixed Ground / ...) + motion_kind         │ │
│  │  PlatformMotionModel (sea_state / stationary / ...)                  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ Propagation 🆕 v0.34 ──────────────────────────────────────────────┐ │
│  │  multipath.py (two-ray sea bounce)                                   │ │
│  │  refraction.py (4/3 earth radius)                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ Scattering & Extended Target 🆕 v0.34 ─────────────────────────────┐ │
│  │  Scatterer | ExtendedTarget (multi-scatterer + glint 자동 발생)       │ │
│  │  Monopulse extended-target 합성 (apparent_position·glint_offset)     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌─ Tracking 🆕 v0.34 ─────────────────────────────────────────────────┐ │
│  │  EKFTracker | UKFTracker (Stone Soup 호환, Editor 드롭다운 선택)      │ │
│  │  GNNDataAssociator (Hungarian, 다중 표적 1:1 매칭)                    │ │
│  │  CA-CFAR | OS-CFAR detector (선택 가능)                               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└────────┬─────────────────────────────────────────────────────────────────┘
         │ pure function call
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          Primitives Layer                                 │
│  Physics functions (ray_tracing, fmcw, reflections, geometry)              │
│  Data types (@dataclass frozen): Peak, Detection, Track, Reflection        │
│  Geo/Terrain primitives (numpy 배열 연산, 좌표 변환)                        │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2.0 블록도 변경 요약 (v0.16 → v0.35)

| 영역 | v0.16 → v0.35 |
|---|---|
| **UI Layer** | WorkspaceManager 추가, Editor/Simulator 분리 (5+5 패널), PyVista 3D Scene, NN Mode UI |
| **App Layer** | ResourceLibrary·BundleService·CoherenceValidator·DEMImportPipeline 추가 (자원·재현성·검증) |
| **App Layer** | NN 4종 (DataExporter/DatasetBuilder/TrainerService/NNEvaluator) — Phase 6 |
| **App Layer** 🆕 v0.35 | PackageManager·PanelRegistry·ResourceLibrary 확장 — Phase 7 DLC 시스템 |
| **Plugin SDK Layer** 🆕 v0.35 | 별도 계층 신설 (Domain 위, App 아래) — DLC 안정 API |
| **Domain Layer** | Map·Terrain·SimulationDomain (좌표 정합), Placement·MotionKind 7, Dynamics 6 모듈, Atmosphere, Antenna, Platform 모두 추가 |
| **Domain Layer** 🆕 v0.34 | Propagation (multipath/refraction), Scattering (multi-scatterer + glint), Tracking (EKF/UKF/GNN/CFAR) — 베이스라인 보강 |
| **Primitives** | 변화 없음 (가장 안정) |

핵심 원칙 유지: **Domain은 Qt·시각화·UI 모름. App는 UI 모름. UI는 Workspace별로 독립**.
**v0.35 추가**: SDK는 Domain만, DLC는 SDK만 — DLC 격리·안정 API 보장.

### 2.2a CommandBus — 포지셔너 명령의 유일한 경로 (v0.14)

[03 § 3.5.1c Single Command Path](03_data_model.md#351c-포지셔너-지휘-경로의-유일성-single-command-path)의
아키텍처 수준 구현. 포지셔너 명령이 **여러 경로에서 올 수 있지만 모두 CommandBus를 거쳐야**
하며, 각 명령의 출처가 타입으로 구분됨.

```
  [Tracker]                [UI 방향키 입력]           [RunManager]
      │                         │                         │
      │ PositionerCommand(       │ PositionerCommand(       │ PositionerCommand(
      │  source=TRACKER,         │  source=MANUAL_USER,     │  source=INITIAL_SCAN)
      │  source_track_id,        │  ...)                    │
      │  source_frame_id)        │                         │
      │                         │                         │
      ▼                         ▼                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │                    CommandBus                           │
  │  • 단일 입력 지점                                         │
  │  • source별 권한 체크 (TRACKER만 Run 중 허용 등)          │
  │  • 발행된 명령 전체를 Trace에 기록 (Lineage 검증용)       │
  │  • 빈도 제한 (동역학적으로 불가능한 연속 명령 거부)        │
  └─────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌────────────────────┐
                    │ PositionerController│
                    │ (Domain 레이어)     │
                    └────────────────────┘
```

**중요한 성질**:
- `GTLoader`, `ScenarioService` 등은 **CommandBus에 write 권한이 없다**. 타입이 `PositionerCommand`인 객체를 만들 수 없거나, 만들어도 CommandBus가 송신자를 화이트리스트로 검증해 거부.
- Run 중 `TRACKER` 소스 외의 명령이 들어오면 **Run State와 교차 검증** (MANUAL_USER는 AUTO 모드일 때 무시, INITIAL_SCAN은 Run 시작 순간에만 허용 등)
- 발행된 모든 명령은 `Trace.positioner_commands`에 기록 → Run 후 Lineage 검증([06 § 6.3.6a](06_topics.md#636a-plugin-격리-검증--gt-isolation--command-lineage-v014-신설)) 재료

### 2.2b SimulationClock — 모든 물리의 기반 시간 (v0.15)

[03 § 3.5.0b 두 레이어 시간 제어](03_data_model.md#3505b-두-레이어-시간-제어-v015-재설계)의
아키텍처 수준 위치.

```
┌──────────────────────────────────────────────────────────────┐
│                    SimulationClock                           │
│  상태: STOPPED / RUNNING / PAUSED                            │
│  Speed: ×1/2/4/8 (actual multiplier 별도)                    │
│  sim_t_s: 시뮬 시간 [s]                                      │
└──────────────┬───────────────────────────────────────────────┘
               │ tick (Sim RUNNING일 때만)
               ▼
        [Environment]  ─ 환경 상태 업데이트 (바람·파도·자함 동요)
        [RadarPipeline] ─ TX → RX → FFT → Detector → Pairing → Tracker
        [PositionerController] ─ 동역학 적분
        [RunClock] ─ Target RUNNING 이면 run_t_s 증가, trajectory 재생
```

**원칙**:
- **Sim Clock이 모든 물리의 기반**. Wall clock은 사용자에게 보여주는 것 외엔 안 씀
- Sim PAUSED 중 UI 입력은 `InputBuffer`에 축적. Sim RUNNING 복귀 시 일괄 소비
- Speed Multiplier는 wall clock 대비 비율. tick 간격(dt)은 유지, wall clock 동기화만 빠르게
- 실제 달성 배수(actual)는 계산량에 따라 설정 배수보다 낮을 수 있음 → UI에 표기

#### 두 레이어 상호작용

```
[Simulation Layer]   SimulationClock (STOPPED/RUNNING/PAUSED)
        │
        │ 시간 공급
        ▼
[Target Run Layer]   RunClock (IDLE/RUNNING/PAUSED/ENDED)
                     └ Sim이 RUNNING일 때만 run_t_s 증가
                     └ Sim이 STOPPED 되면 강제 IDLE + termination=SIM_STOPPED
```

Target Run은 Sim 시간 위에 올라탄 **상위 레이어**. 독립적 상태 머신이지만 실제 진행은
Sim에 종속. UI 툴바도 이 계층 구조를 반영해 Sim 제어와 Target 제어를 **시각적으로 분리**
([05 § 5.5.1](05_ui_ux.md#551-mvp-툴바-구성--두-레이어-제어-반영-v015)).

### 2.2c PerformanceClock — Reference Timing 보정 (v0.39 신설)

> **출처**: 18 § 18.16 Reference Timing Mode

SimulationClock 의 **확장 컴포넌트**. Reference Timing Mode 활성화 시 **wall_clock ↔ reference_time ↔ sim_time** 3 시간 매핑.

```
┌──────────────────────────────────────────────────────────────┐
│                    SimulationClock                           │
│   상태: STOPPED / RUNNING / PAUSED                           │
│   Speed Multiplier: ×1/2/4/8                                 │
│   sim_t_s: 시뮬 시간 [s]                                     │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼ (Reference Timing Mode 활성 시)
┌──────────────────────────────────────────────────────────────┐
│              PerformanceClock (v0.39)                        │
│                                                              │
│  입력: StageTimingProfile (사용자 명시 target_latency_ms)    │
│  측정: wall_clock 으로 stage 실측 latency                    │
│  계산: scale_factor = target / measured                      │
│                                                              │
│  PC 빠름 (measured < target): sleep 으로 늦춤                │
│  PC 느림 (measured > target): scale_factor 로 시뮬 시간 보정 │
│                                                              │
│  frame 단위 결정성 보장:                                     │
│  - 같은 시드 + 같은 input + 같은 frame 정의 → 같은 결과      │
│  - wall_clock 변동은 결과에 영향 X                           │
└──────────────────────────────────────────────────────────────┘
```

**원칙**:
- **PerformanceClock 은 SimulationClock 의 옵션 layer** — Reference Timing Mode 시만 활성
- **frame 단위로 결정적** — frame 경계에서 시뮬 state snapshot, 보정 적용
- **Speed Multiplier vs scale_factor** — 둘 독립
  - Speed Multiplier (v0.15): 사용자가 시뮬 빠르게/느리게 보고 싶음 (×2, ×4)
  - scale_factor (v0.39): 시뮬 시간이 wall_clock 의 비율로 흐름 (자동 계산)
- **HIL Lock-step Handshake** (Phase 8.1): frame 경계에서 DUT 와 sync barrier — § 18.16.4

상세: [18 § 18.16 Reference Timing Mode](18_hil_integration.md#1816-reference-timing-mode-v039-신설), [03 § 3.2.1n](03_data_model.md#321n-reference-timing--frame-profiler--시뮬-시간-보정-데이터-모델-v039-신설).

### 왼쪽에 붙는 별도 축: HIL 통합 (v0.38)

```
  [Application Layer]
         │
         ▼ SignalSink interface (TX 측)
  ┌─────────────────┐
  │   SIL Sink      │  ← MVP: 시뮬 내부에서 RX로 직접
  │   (default)     │
  └─────────────────┘
         │
         ▼ 또는 (Phase 8 — MVP+α)
  ┌─────────────────┐    ┌──────────────────┐
  │   HIL Sink      │───▶│  외부 DUT 장치   │
  │   (plug-in)     │    │  (펌웨어/FPGA/   │
  │                 │    │   DSP 보드)      │
  └─────────────────┘    └────────┬─────────┘
                                  │
                                  ▼ DUT 결과 (L1~L5)
                         ┌─────────────────┐
                         │  DUTAdapter     │  ← v0.38 신설
                         │  Protocol (SDK) │     (10번째 Plugin Protocol)
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────────┐
                         │  HILEvaluator       │  ← GT/SIL/HIL 3-way 비교
                         │  (App Layer)        │
                         └─────────────────────┘
```

**MVP HIL (Phase 8.1)**: TCPJsonDUTAdapter (기본 sample) + L5 Track 비교 + sim_time 동기화.
**MVP+α 확장 (Phase 8.2~8.3)**: L2/L4 stage-by-stage + L1 ADC raw + AWG analog.

상세: [18 hil_integration.md](18_hil_integration.md).

---

## 2.3 디렉토리 구조 (제안)

🟡 **Proposed** — v0.35 기준으로 v0.18~v0.35 모듈 모두 반영 (v0.34 베이스라인 5종 + v0.35 SDK Layer 포함).

```
workbench/                          ← 새 레포 루트
├── pyproject.toml                  ← 단일 패키지 빌드 정의
├── README.md
├── LICENSE                         ← Apache 2.0 (v0.35)
├── NOTICE                          ← 서드파티 라이선스 목록
│
├── src/
│   └── workbench/                  ← import workbench
│       ├── __init__.py
│       ├── __main__.py             ← python -m workbench 진입점
│       │
│       ├── app/                    ← Application Layer
│       │   ├── commands/           ← Command 구현체들 (sim.*/target.*/editor.*/workspace.*)
│       │   ├── command_registry.py
│       │   ├── command_bus.py      ← v0.14: 포지셔너 명령 단일 버스
│       │   ├── input_buffer.py     ← v0.15: Sim PAUSED 중 입력 버퍼
│       │   ├── plugin_loader.py
│       │   ├── plugin_scanner.py   ← v0.14: AST 정적 스캔 (GT Isolation)
│       │   ├── workspace_manager.py    ← 🆕 v0.19: Editor/Simulator 전환
│       │   ├── resource_library.py     ← 🆕 v0.20: 자원 인덱스
│       │   ├── resource_cache.py       ← 🆕 v0.20: content_hash 캐시
│       │   ├── bundle_service.py       ← 🆕 v0.20: .scnbundle/.runbundle
│       │   ├── coherence_validator.py  ← 🆕 v0.21~v0.29: 6종 검사
│       │   ├── package_manager.py      ← 🆕 v0.35: .trsim-pkg install/load
│       │   ├── panel_registry.py       ← 🆕 v0.35: UI 패널 등록 (DLC 패널 포함)
│       │   ├── run_manager.py
│       │   ├── scenario_service.py
│       │   ├── simulation_clock.py ← v0.15
│       │   ├── probe_recorder.py
│       │   ├── evaluator.py
│       │   ├── physics_gate.py
│       │   ├── event_bus.py
│       │   └── nn/                 ← 🆕 NN 통합 (Phase 6, MVP+α)
│       │       ├── data_exporter.py
│       │       ├── dataset_builder.py     ← Variant 6종 생성 (v0.30)
│       │       ├── trainer_service.py
│       │       └── nn_evaluator.py        ← 4-error 진단
│       │   ├── hil/                 ← 🆕 v0.38: HIL 통합 (Phase 8, MVP+α)
│       │   │   ├── hil_evaluator.py       ← GT/SIL/HIL 3-way 비교
│       │   │   ├── time_synchronizer.py   ← sim_time + real_time 모드
│       │   │   └── dut_session_manager.py ← DUT 연결 생애주기
│       │   │
│       │   ├── timing/               ← 🆕 v0.39: Reference Timing + Frame Profiler
│       │   │   ├── performance_clock.py    ← SimulationClock 의 보정 layer
│       │   │   ├── frame_boundary_detector.py ← 자동 frame 추론 (Q-RT1)
│       │   │   ├── stage_timing_probe.py   ← Stage 시작·끝 측정
│       │   │   └── frame_profiler.py       ← Pre-run + 백그라운드 통계
│       │   │
│       │   └── physics_lab/          ← 🆕 v0.40: Physics Lab Application Layer
│       │       ├── experiment_runner.py    ← 시뮬 진행 (4 시간 모드)
│       │       ├── param_introspector.py   ← 파라미터 자동 노출 (decorator/type hint)
│       │       ├── validation_bench.py     ← 분석 vs 구현 비교 + 17종 통합
│       │       ├── external_data_loader.py ← CSV/HDF5/.npz 로더
│       │       ├── parameter_fitter.py     ← 형태 1: 파라미터 학습
│       │       └── physics_clock.py        ← Physics Lab 격리 PhysicsClock
│       │
│       ├── domain/                 ← Domain Layer
│       │   ├── scenario.py         ← Scenario (refs+composition+install, v0.20)
│       │   ├── contracts.py        ← Protocol 정의 + PositionerCommand
│       │   ├── pipeline.py         ← RadarPipeline + Stage Slot (v0.13/0.27)
│       │   ├── environment.py
│       │   ├── types.py            ← Peak, Detection, Track, RunState 등
│       │   │
│       │   ├── geo.py                  ← 🆕 v0.21: GeoOrigin, VerticalReference
│       │   ├── map_resource.py         ← 🆕 v0.21~v0.22: Map, WorkbenchTerrain
│       │   ├── coastline.py            ← 🆕 v0.22: CoastlinePolygon
│       │   ├── terrain_sampling.py     ← 🆕 v0.22: sample_terrain() (land_mask)
│       │   ├── simulation_domain.py    ← 🆕 v0.29: SimulationDomain, OutsideEnvironment, sample_terrain_safe()
│       │   │
│       │   ├── placement.py            ← 🆕 v0.21~v0.27: PlacedEntity, MotionKind 7
│       │   ├── wave_response.py        ← 🆕 v0.21: WaveResponseModel + 4 프리셋
│       │   ├── building.py             ← 🆕 v0.21: BuildingEntity, Anchor 4 mode
│       │   ├── target.py               ← 🆕 v0.21: TargetEntity, TargetWaypoint
│       │   │
│       │   ├── dynamics/               ← 🆕 v0.27: 동역학 모듈
│       │   │   ├── state.py            ← RigidBodyState, Forces
│       │   │   ├── params.py           ← DynamicsParams, AircraftParams 등
│       │   │   ├── forces.py           ← gravity/drag/lift/thrust/control 계산
│       │   │   ├── solver.py           ← DynamicsSolver (RK4)
│       │   │   ├── motion_models.py    ← motion_kind별 외력 모델
│       │   │   └── impact.py           ← BALLISTIC 지면 충돌
│       │   │
│       │   ├── atmosphere.py           ← 🆕 v0.28: AtmosphereState, ISA 함수
│       │   ├── rain_attenuation.py     ← 🆕 v0.28: ITU-R P.838 단순화
│       │   │
│       │   ├── propagation/            ← 🆕 v0.34: 베이스라인 보강
│       │   │   ├── multipath.py        ← Two-ray (sea bounce)
│       │   │   └── refraction.py       ← 4/3 earth radius
│       │   │
│       │   ├── antenna.py              ← 🆕 v0.25: ParabolicAntenna, PlanarArrayAntenna
│       │   ├── rx_channels.py          ← 🆕 v0.25: RXChannelKind, MonopulseRXConfig
│       │   ├── monopulse.py            ← 🆕 v0.25: error_az/el_rad 계산 (v0.34 extended target)
│       │   ├── scattering.py           ← 🆕 v0.34: Scatterer, ExtendedTarget, Glint
│       │   │
│       │   ├── tracker_ekf.py          ← 🆕 v0.34: EKFTracker (v0.10에서 리팩토링)
│       │   ├── tracker_ukf.py          ← 🆕 v0.34: UKFTracker (Stone Soup 호환)
│       │   ├── data_associator.py      ← 🆕 v0.34: GNN + Hungarian
│       │   ├── detector_cfar.py        ← 🆕 v0.34: CA/OS-CFAR 선택
│       │   │
│       │   ├── platform.py             ← 🆕 v0.18~v0.24: RadarPlatform, motion_kind
│       │   ├── platform_motion.py      ← 🆕 v0.18: PlatformMotionModel (sea_state/stationary)
│       │   │
│       │   ├── hil/                    ← 🆕 v0.38: HIL DUT 데이터 모델
│       │   │   ├── dut_messages.py     ← L1~L5 dataclass (RawIQ/Spectrum/Detection/Paired/Track)
│       │   │   ├── tx_signal.py        ← TXSignalDigital/Analog
│       │   │   └── comparison.py       ← HILComparisonResult (3-way)
│       │   │
│       │   └── timing/                 ← 🆕 v0.39: Reference Timing 데이터 모델
│       │       ├── reference_timing.py ← StageTimingProfile / TimingConfig / ReferenceTimingState
│       │       └── frame_profiler.py   ← StageTimingStat / FrameTimingReport
│       │
│       ├── sdk/                    ← 🆕 v0.35: Plugin SDK Layer (DLC 작성용)
│       │   ├── __init__.py         ← public API (sdk.TrackerProtocol 등)
│       │   ├── protocols.py        ← Plugin Protocol 11개 (v0.40: PhysicsModelProtocol 추가)
│       │   ├── resource_schemas.py ← TOML 스키마 (Map/Radar/Target)
│       │   ├── package_builder.py  ← 디렉토리 → .trsim-pkg
│       │   ├── package_validator.py← manifest 검증
│       │   └── test_harness.py     ← DLC 로컬 테스트
│       │
│       ├── physics/                ← ⭐ v0.40: 모든 물리 통합 (Physics Layer)
│       │   ├── propagation/        ← ← FMCW, ray tracing, multipath, refraction, atm loss
│       │   │   ├── fmcw.py
│       │   │   ├── ray_tracing.py
│       │   │   ├── multipath.py    ← (v0.40 이동: domain/radar/ 에서)
│       │   │   ├── refraction.py   ← (v0.40 이동: domain/atmosphere/ 에서)
│       │   │   └── atmospheric_loss.py
│       │   ├── reflection/         ← RCS, scattering
│       │   │   ├── rcs_single.py
│       │   │   ├── rcs_aspect.py
│       │   │   ├── extended_target.py  ← (v0.40 이동: domain/targets/ 에서)
│       │   │   └── glint.py
│       │   ├── dynamics/           ← (v0.40 이동: domain/dynamics/ 에서)
│       │   │   ├── newton.py
│       │   │   ├── aerodynamics.py
│       │   │   ├── motion_solver.py
│       │   │   └── platform_motion.py  ← (v0.40 이동: domain/platform.py 에서)
│       │   ├── atmosphere/         ← (v0.40 이동: domain/atmosphere/ 에서)
│       │   │   ├── isa.py
│       │   │   ├── rain.py
│       │   │   └── ducting.py
│       │   ├── antenna/            ← (v0.40 이동: domain/radar/ 에서)
│       │   │   ├── parabolic.py
│       │   │   ├── monopulse.py
│       │   │   └── beam_pattern.py
│       │   ├── geometry.py         ← 기존 유지
│       │   ├── reflections.py      ← (v0.40: 일부 reflection/ 으로 흡수, 점진)
│       │   ├── render/             ← 메시 생성 보조
│       │   ├── test_objects.py     ← 🆕 v0.40: 9 표준 (Sphere/Cube/Plate/Cylinder/Cone/Point/Plane/Wall/Trihedral)
│       │   └── _testbench/         ← 🆕 v0.40: Physics Lab 검증 코드
│       │       ├── analytic_reference.py
│       │       ├── golden_dataset/
│       │       └── plot_helpers.py
│       │
│       ├── io/                     ← 외부 I/O
│       │   ├── scenario_loader.py  ← TOML 기반 ref 해결 (v0.20)
│       │   ├── run_storage.py      ← Run Manifest with resource_refs (v0.20)
│       │   ├── trace_storage.py
│       │   ├── dem_import.py       ← 🆕 v0.22: DEM Import Wizard 백엔드
│       │   ├── bundle_io.py        ← 🆕 v0.20: tar.gz pack/unpack
│       │   ├── workbench_native.py ← 🆕 v0.22: terrain.npz 읽기·쓰기
│       │   └── package_io.py       ← 🆕 v0.35: .trsim-pkg pack/unpack
│       │
│       ├── plugins_builtin/        ← 기본 제공 플러그인
│       │   ├── default_detector.py
│       │   ├── default_tracker.py
│       │   ├── tcp_json_dut_adapter.py ← 🆕 v0.38: HIL 기본 어댑터 (TCP/JSON sample)
│       │   └── ...
│       │
│       ├── ui/                     ← UI Layer
│       │   ├── main_window.py      ← 얇은 조립자 (< 300줄 목표)
│       │   ├── workspace_selector.py   ← 🆕 v0.19: Editor/Simulator 전환 UI
│       │   ├── dock_manager.py     ← Workspace별 독립 레이아웃
│       │   ├── command_palette.py
│       │   ├── toolbar.py          ← 두 레이어 (Sim/Target) (v0.15)
│       │   ├── menu.py
│       │   ├── theme.py
│       │   │
│       │   ├── editor/             ← 🆕 v0.19~v0.26: Editor Workspace
│       │   │   ├── activity_selector.py
│       │   │   ├── resource_browser.py     ← 상시 사이드바
│       │   │   ├── scenario_composer/
│       │   │   │   ├── main.py
│       │   │   │   ├── references_panel.py
│       │   │   │   ├── installation_panel.py  ← v0.18 Installation 인라인
│       │   │   │   ├── composition_panel.py
│       │   │   │   └── validation_panel.py
│       │   │   ├── map_editor/
│       │   │   │   ├── main.py
│       │   │   │   ├── canvas.py            ← pyqtgraph ImageItem 기반
│       │   │   │   ├── tools.py             ← Land/Sea Brush, Spot Edit, Flatten Area (v0.33)
│       │   │   │   ├── building_panel.py
│       │   │   │   ├── domain_settings.py   ← 🆕 v0.29: Simulation Domain 패널
│       │   │   │   └── dem_import_wizard.py ← v0.22: 7 step
│       │   │   ├── radar_editor.py          ← v0.25: 통합 폼 (드롭다운)
│       │   │   ├── targets_editor.py        ← v0.26: 메타 + Trajectory Preview
│       │   │   └── atmosphere_panel.py      ← 🆕 v0.28: 대기 편집
│       │   │
│       │   └── simulator/          ← Simulator Workspace 패널
│       │       ├── scenario_explorer.py
│       │       ├── fft_panel.py             ← pyqtgraph
│       │       ├── range_doppler_panel.py   ← pyqtgraph ImageView
│       │       ├── plugin_manager_panel.py
│       │       ├── run_panel.py             ← Time Layers (Sim/Target)
│       │       ├── properties_panel.py      ← EKF Cmd vs Actual
│       │       ├── stage_io_panel.py        ← 🆕 v0.14: 각 스테이지 I/O
│       │       ├── physics_validation_panel.py
│       │       ├── scene_3d/               ← 🆕 v0.28: PyVista 3D Scene
│       │       │   ├── qt_interactor.py    ← QtInteractor 임베드
│       │       │   ├── dem_renderer.py     ← smooth shading
│       │       │   ├── wave_renderer.py    ← 파도 셰이더
│       │       │   ├── atmosphere_visuals.py ← sky color, fog
│       │       │   ├── target_actor.py
│       │       │   ├── radar_actor.py
│       │       │   └── building_actor.py
│       │       ├── nn_mode/                ← 🆕 v0.13: NN 모드
│       │       │   ├── step1_dataset_builder.py
│       │       │   ├── step2_evaluation.py  ← 4-error 진단 표시
│       │       │   └── training_panel.py
│       │       │
│       │       ├── hil_panel/               ← 🆕 v0.38: HIL 통합 UI
│       │       │   ├── comparison_view.py   ← GT/SIL/HIL 3-way Track plot
│       │       │   ├── dut_bias_plot.py     ← 펌웨어 vs Python gap 시각화
│       │       │   └── stage_compare.py     ← L2/L4/L5 단계별 비교
│       │       │
│       │       └── profiler_panel/          ← 🆕 v0.39: Reference Timing + Frame Profiler UI
│       │           ├── timing_breakdown.py  ← Stage 별 timing 막대 chart
│       │           ├── scale_indicator.py   ← "0.57x" 시뮬 속도 표시
│       │           └── profile_report.py    ← Frame Profiler 결과 표
│       │
│       ├── physics_lab/              ← 🆕 v0.40: Physics Lab Workspace (3번째)
│       │   ├── physics_lab_workspace.py    ← 메인 Workspace (3-pane)
│       │   ├── code_pane.py                ← Read-only / Edit toggle
│       │   ├── visualization_pane.py       ← 2D (pyqtgraph) / 3D (PyVista)
│       │   ├── parameters_pane.py          ← 슬라이더 자동 생성
│       │   ├── time_controls.py            ← Play/Pause/Stop/Slider/Frame
│       │   ├── model_selector.py           ← Force toggle (☑Grav ☐Drag etc.)
│       │   ├── test_object_selector.py     ← 9 Test Objects 선택
│       │   ├── validation_panel.py         ← Validation Bench 결과 + 17종 회귀
│       │   └── data_overlay_panel.py       ← 외부 측정 데이터 overlay
│       │
│       └── hil/                    ← 🆕 v0.35 명시: HIL 외부 도구 자리 (보존)
│           ├── .gitkeep             ← Phase 0에서 빈 디렉토리 유지
│           └── README.md           ← AWG SDK 등 외부 라이브러리 자리
│                                     v0.38: 실제 코드는 src/workbench/{domain,app}/hil/ + ui/simulator/hil_panel/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── physics/                    ← 물리 검증 스위트 (Phase 5, 11종)
│       ├── test_radar_equation.py
│       ├── test_fmcw_signal.py
│       ├── test_antenna_pattern.py        ← 🆕 v0.25
│       ├── test_monopulse_error.py        ← 🆕 v0.25
│       ├── test_aircraft_dynamics.py      ← 🆕 v0.27
│       ├── test_ballistic_trajectory.py   ← 🆕 v0.27
│       ├── test_isa_atmosphere.py         ← 🆕 v0.28
│       ├── test_rain_attenuation.py       ← 🆕 v0.28
│       ├── test_sample_terrain_safe.py    ← 🆕 v0.29
│       ├── test_coherence_validator.py    ← 🆕 v0.21~v0.29 (6종)
│       ├── test_two_ray_multipath.py      ← 🆕 v0.34
│       ├── test_glint_emergence.py        ← 🆕 v0.34 (multi-scatterer)
│       ├── test_ekf_vs_ukf.py             ← 🆕 v0.34
│       ├── test_gnn_association.py        ← 🆕 v0.34
│       ├── test_refraction_horizon.py     ← 🆕 v0.34
│       ├── test_os_cfar.py                ← 🆕 v0.34
│       ├── test_multipath.py
│       ├── test_clutter.py
│       ├── test_raytracing.py
│       ├── test_positioner.py
│       └── golden/                 ← Golden Dataset
│
├── data/                           ← 샘플 데이터
│   ├── resources/                  ← 🆕 v0.20: 자원 라이브러리 샘플
│   │   ├── maps/
│   │   ├── radars/
│   │   └── targets/
│   ├── terrain/                    ← 원본 DEM 샘플
│   └── ships/
│
├── scenarios/                      ← 샘플 시나리오 (refs 기반)
│
├── docs/
│   ├── plan/                       ← 이 계획서 (17개 + 부록 2)
│   ├── user_guide/
│   ├── dev_guide/
│   └── physics_reference/
│
└── examples/
    └── plugins/                    ← 사용자 작성 예시
        ├── my_detector.py
        ├── my_tracker.py
        └── my_pipeline.py
```

### 디렉토리 결정에 대한 주석

- `src/workbench/` 레이아웃 — `pip install -e .` 개발 시 가장 깔끔
- `domain/dynamics/` 서브패키지 — 6 모듈이 응집도 높아 묶음 (v0.27)
- `ui/editor/` vs `ui/simulator/` 분리 — Workspace 분리(v0.19) 반영, 직접 참조 금지 강제하기 쉬움
- `ui/simulator/scene_3d/` 별도 서브패키지 — PyVista 의존성을 한 곳으로 격리 (v0.28)
- `ui/simulator/nn_mode/` — NN 패널들 (Phase 6 분리)
- `app/nn/` — NN 백엔드 (DataExporter/DatasetBuilder/Trainer/Evaluator)
- `data/resources/` 신설 — v0.20 자원 라이브러리의 샘플
- `hil/` 디렉토리 — 지금은 비워두지만, "여기가 HIL 자리"라고 명시해 설계 의도 전달
- `physics/` 를 `domain/`과 분리한 이유 — 물리 함수들은 순수 함수라서 domain보다 더 낮은 계층

---

## 2.4 스레드 / 프로세스 모델

### 스레드 구성

```
┌─────────────────────────────────────────────────────────┐
│  Main Thread (Qt GUI)                                   │
│    - 렌더링, 사용자 입력, 위젯 업데이트                 │
│    - Signal/Slot 수신                                    │
│    - 방향키 입력 → InputBuffer 또는 CommandBus          │
└─────────────────────────────────────────────────────────┘
                    ▲ signal (queued)
                    │
┌─────────────────────────────────────────────────────────┐
│  Simulation Thread (QThread)                            │
│    - SimulationClock 기반 루프 (Sim RUNNING일 때만)      │
│    - RadarPipeline.step(dt) 호출                        │
│    - EnvironmentState 업데이트                           │
│    - PositionerController.step(dt) 동역학 적분          │
│    - RunClock 업데이트 (Target RUNNING이면)             │
│    - 결과를 EventBus로 emit                              │
│    - Speed Multiplier에 따라 wall clock 동기화          │
└─────────────────────────────────────────────────────────┘
                    ▲ method call
                    │
┌─────────────────────────────────────────────────────────┐
│  ThreadPool (numpy 작업 분산)                           │
│    - CFAR, FFT, 레이트레이싱 등 CPU-heavy 작업          │
└─────────────────────────────────────────────────────────┘
```

### 주요 결정

- **Sim 스레드에서 Qt 위젯을 직접 건드리지 않는다.** 결과는 Signal/Slot으로 Main 스레드에 전달.
- **SimulationClock이 유일한 시간 소스.** Qt 의 여러 QTimer 가 분산된 fps 로 도는 흔한 패턴 대신 Sim 스레드 내부 이벤트 루프 하나로 통합.
- **numpy GIL 해제**를 적극 활용. pandas보다는 numpy 직접 사용 선호.
- **플러그인 실행은 sim 스레드에서**. 플러그인이 오래 걸리면 actual multiplier가 설정치보다 낮아지지만 UI는 멈추지 않음 (멀티프로세싱은 배포 시 고려).
- **Sim PAUSED 중엔 루프가 wait.** UI 입력은 Main 스레드에서 InputBuffer에 축적되다가 Sim RUNNING 복귀 시 소비.

### 상태 흐름 (v0.15 개편)

#### Sim Start

```
User clicks "Sim Start"
    → Command "sim.start"
    → SimulationClock.start()  (state: STOPPED/PAUSED → RUNNING)
    → Sim 스레드 loop 시작 (이미 돌고 있으면 wait 해제)
```

#### Target Run

```
User clicks "Target Run"
    → Command "target.run"
    → RunManager.start_target_run()
        ↳ Sim이 STOPPED/PAUSED면 자동 sim.start
        ↳ InitialScan PositionerCommand 발행 (CommandBus 경유)
        ↳ RunClock.state = RUNNING
```

#### Sim Thread Main Loop

```python
while not thread_stop:
    if sim_clock.state != RUNNING:
        wait_until_sim_running()    # PAUSED/STOPPED 상태면 대기
        continue

    # 1. InputBuffer 소비 (Sim PAUSED 중 누적된 UI 입력)
    if input_buffer.has_pending():
        cmd = input_buffer.flush_to_command()
        command_bus.publish(cmd)

    # 2. 시뮬 틱 (sim_t 기반)
    dt = sim_clock.advance_tick()            # sim_t_s += tick_dt
    environment.update(dt, sim_t_s)          # 환경 (바람·파도·자함)

    if run_clock.state == RUNNING:
        run_clock.run_t_s += dt              # Target 재생 시간
        scenario.update_targets(run_clock.run_t_s)

    # 3. RadarPipeline step
    frame_result = pipeline.step(dt, environment, scenario_state)

    # 4. Tracker 출력 → CommandBus (AUTO 모드일 때)
    if positioner_mode == AUTO and run_clock.state == RUNNING:
        cmd = build_tracker_command(frame_result.tracks, primary_target_id)
        command_bus.publish(cmd)

    # 5. Positioner 동역학 적분 (CommandBus의 최신 명령 적용)
    positioner.step(dt)

    # 6. Probe 기록
    probe_recorder.capture(frame_result, probes)

    # 7. EventBus emit → Main 스레드 UI 갱신
    eventbus.emit("frame_complete", frame_result)

    # 8. Wall clock 동기화 (Speed Multiplier 반영)
    sim_clock.sleep_to_match_wall_clock()
    # actual_multiplier 계산 (실제 wall dt / 설정 sim dt)

Main thread:
    eventbus.on("frame_complete") → panels update
```

#### Sim Pause

```
User clicks "Sim Pause"
    → Command "sim.pause"
    → SimulationClock.pause()  (state: RUNNING → PAUSED)
    → Sim 스레드가 wait 상태로 진입 (sim_t 멈춤)
    → 이후 방향키 입력은 InputBuffer에 축적됨 (Main 스레드에서)
```

#### Sim Stop

```
User clicks "Sim Stop"
    → Command "sim.stop"
    → [다이얼로그 — Target RUNNING이면 결과 저장 여부]
    → SimulationClock.stop()  (state → STOPPED, sim_t_s = 0)
    → RunClock 강제 IDLE, termination=SIM_STOPPED
    → 환경 상태 초기화, 표적 시작 위치로
```

---

## 2.5 의존성 규칙 (엄격히 지킨다)

### 허용 의존 방향

```
ui        → app → domain → physics/primitives
                    ↓           ↑
                  ✗ (금지)     ✓
```

### 금지 항목

| 금지 | 예시 | 왜 |
|---|---|---|
| `domain/` → `PySide6` | `from PySide6 import Qt` in domain/contracts.py | UI 교체 불가능해짐 |
| `domain/` → `ui/` | domain에서 panel 참조 | 순환 의존 |
| `physics/` → anything | physics가 domain 참조 | physics는 가장 순수한 계층 |
| `app/` → `ui/` | app이 위젯 알고 있음 | UI 교체 불가 |
| UI 간 직접 참조 | panel A가 panel B를 import | EventBus를 통해 느슨하게 |
| `scenario_service.py` → `CommandBus.publish` | v0.14: Scenario Service가 포지셔너 직접 명령 | Single Command Path 위반 |
| `io/` → `CommandBus` | v0.14: GT·Scenario 로더가 포지셔너에 write | Single Command Path 위반 |
| `domain/` → `pyqtgraph` / `pyvista` | 🆕 v0.28: 시각화 라이브러리 직접 참조 | UI에서만 — Domain 순수성 |
| `ui/editor/*` ↔ `ui/simulator/*` 직접 참조 | 🆕 v0.19: Editor 패널이 Simulator 패널 import | Workspace 분리 위반 — EventBus·WorkspaceManager 경유 |
| `domain/` 자기 검증 | 🆕 v0.21: Map.validate() 같은 self-check | CoherenceValidator는 App Layer (검증은 외부 책임) |
| `domain/dynamics/` → `SimulationClock` | 🆕 v0.27: Solver가 시뮬 시간 직접 참조 | Solver는 dt만 받음 (시간 모름, 순수 함수) |

### Single Command Path 강제 (v0.14)

`CommandBus.publish()` 호출 권한은 다음 3곳만:
- `RunManager` (TRACKER 명령, INITIAL_SCAN 명령)
- `UI 방향키 입력 핸들러` (MANUAL_USER 명령)
- `InputBuffer 소비 루틴` (Sim 재개 시 누적 MANUAL_USER 명령)

그 외 모듈이 `CommandBus`를 import하면 CI 검사 실패. `import-linter` 규칙에 명시.

### Workspace 분리 강제 (v0.19)

Editor / Simulator Workspace 간 통신은 **WorkspaceManager + EventBus 경유**만 허용:
- ❌ `ui/editor/scenario_composer.py` → `ui/simulator/run_panel.py` 직접 import
- ✅ `ui/editor/scenario_composer.py` → `event_bus.publish("editor.open_in_simulator", scenario_id)` → `WorkspaceManager` 가 Simulator 활성화

이로써 Workspace 한쪽 리팩토링이 다른 쪽에 영향 안 줌.

### Resource & Validation 책임 분리 (v0.20~v0.29)

- **Domain Layer**: 자원 *형태* 만 정의 (`Map`, `RadarConfig`, `TargetEntity` 등 dataclass). content_hash 계산 함수는 정적 함수로 제공 (Domain 순수)
- **App Layer**: 자원 *관리* — `ResourceLibrary` 가 디렉토리 스캔, `ResourceCache` 가 in-memory 캐시, `BundleService` 가 export/import
- **App Layer**: 자원 *검증* — `CoherenceValidator` 가 6종 검사 수행. Domain 객체를 입력으로 받지만 Domain이 자기 검증 안 함

### Visualization 격리 (v0.28)

시각화 라이브러리는 UI Layer 안에서만 import:
- `ui/editor/map_editor/canvas.py` 가 pyqtgraph 사용 — OK
- `ui/simulator/scene_3d/*` 가 pyvista 사용 — OK
- `domain/map_resource.py` 가 pyqtgraph import — **금지** (UI 교체 불가능해짐)

이로써 향후 다른 라이브러리(matplotlib·Vispy·Three.js wrapper 등)로 교체할 때 Domain 안 건드림.

### NN Plugin 격리 (Phase 6)

NN Plugin은 사용자 작성 코드 — 동적 로드되며 다음 격리 보장:
- `app/plugin_scanner.py` 가 AST 정적 스캔으로 GT 직접 import 검출 (v0.14 Level 3-1)
- `app/nn/data_exporter.py` 만이 GT에 read 권한 (sample 생성 시점)
- NN Plugin은 Pipeline의 Stage Slot에만 등록됨 — Domain·App 코어 변경 불가

### SDK Layer 격리 (v0.35)

DLC 시스템의 안정성을 위한 추가 규칙:

| 금지 | 예시 | 왜 |
|---|---|---|
| `sdk/` → `app/`, `ui/` | SDK가 RunManager, 위젯 import | SDK는 Domain·Physics만 알아야 (안정적 API) |
| `domain/` → `sdk/` | Domain이 SDK 함수 import | SDK는 Domain 위 계층 (반대 방향) |
| DLC `package` → `app/`, `ui/` 직접 import | Plugin이 RunManager 직접 호출 | Plugin은 SDK Protocol만 사용 (호환성) |
| DLC `package` → `domain/` 직접 import | Plugin이 Domain 내부 모듈 직접 사용 | Domain refactor 시 DLC 깨짐 |

**효과**: DLC가 잘못 만들어져도 Core는 안정. Domain refactor가 DLC를 깨지 않음 (SDK가 호환 layer).

### 강제 수단

MVP 후에 추가:
- `import-linter` 설정으로 CI에서 검사
- 모듈 헤더 주석에 "이 파일이 의존해도 되는 계층" 명시
- v0.31 추가: Workspace 분리·Visualization 격리·NN 격리 검사도 같은 도구로
- v0.35 추가: SDK·DLC 격리 검사

---

## 2.6 Qt 객체 모델 통합 정책

### QObject 상속

- Panel, Command 등 **Qt가 직접 다루는 객체만** QObject/QWidget 상속
- Domain/App 객체는 일반 Python 클래스

### Signal / EventBus 분리

| 용도 | 도구 |
|---|---|
| Qt 위젯 간 로컬 통신 | Qt Signal/Slot |
| 앱 전반 이벤트 (frame, run, plugin 변경) | EventBus (자체 pub/sub) |
| 스레드 경계 넘는 통신 | Qt Signal (queued) |

EventBus를 직접 만드는 이유: domain/app 계층이 Qt 몰라도 되게 하려고.
Qt Signal에만 의존하면 도메인이 Qt 오염됨.

---

## 2.6a 시각화 라이브러리 스택 (v0.28)

UI Layer는 두 라이브러리를 **하이브리드**로 사용한다 (Q-P2-rev 결정):

### 분류 A — pyqtgraph (데이터 시각화 메인)

빠른 데이터 시각화·실시간 그래프에 사용. 본 프로젝트의 대부분 패널이 여기 속함:

- **2D 데이터 패널**: FFT spectrum, Range-Doppler heatmap, 시계열, 메트릭 차트
- **Editor의 Map Editor (top-down 2D)** — `ImageItem` + 오버레이
- **Beam Pattern Preview** — polar/cartesian plot
- **Run Panel time series**

장점: 빠름 (GPU 가속), Qt 네이티브, 의존성 작음, 실시간 데이터에 강함.

### 분류 B — PyVista (3D Scene View 한정)

VTK 위 친화 wrapper. 본 프로젝트의 **3D 환경 시각화**에만 사용:

- **Simulator의 3D Scene View**: 지형 (DEM smooth shading) + 건물 mesh + 해수면 (파도 셰이더) + 표적·레이더 mesh
- **대기 효과**: fog, sky color, visibility (15 § 15.4)
- **Editor의 Map Editor 3D Preview** (선택, 사용자 토글)

장점: smooth shading, 셰이더, 대기 fog, 메시 처리 편함, Qt 통합 가능 (`QtInteractor`).

### 둘의 통합

Qt Main Window 안에:
- `QDockWidget`에 pyqtgraph 위젯 배치 (FFT, scope, etc.)
- `QDockWidget`에 PyVista `QtInteractor` 배치 (3D Scene View)
- 같은 EventBus 구독, 동기화

```python
# UI Layer 구조 예시
class SimulatorWorkspace(QMainWindow):
    def __init__(self):
        # 데이터 패널들 (pyqtgraph)
        self.fft_panel = FFTPanel()           # pyqtgraph.PlotWidget
        self.range_doppler = RDPanel()        # pyqtgraph.ImageView
        self.time_series = TimeSeriesPanel()  # pyqtgraph

        # 3D Scene View (PyVista)
        from pyvistaqt import QtInteractor
        self.scene_3d = SceneView3D(QtInteractor(self))

        # 모두 같은 EventBus 구독
```

### 의존성 영향

`pyproject.toml`:
```toml
[tool.poetry.dependencies]
PySide6 = "^6.5"
pyqtgraph = "^0.13"
pyvista = "^0.43"
pyvistaqt = "^0.11"      # PyVista의 Qt 통합
numpy = "^1.24"
# ... 기타
```

VTK는 PyVista의 의존성으로 자동 설치 (~80MB). 의존성 부담은 있지만 **3D 품질을 위한 가치
충분** (DEM smooth shading + 파도 셰이더 + 대기 fog).

### 분리 원칙

- **Domain·App Layer**는 둘 다 모름 (UI Layer 안에서만 import)
- pyqtgraph 패널과 PyVista Scene은 **EventBus 경유로만 통신** (직접 참조 금지)
- 한쪽 라이브러리 교체 가능성 보존 (예: PyVista → 다른 3D 라이브러리)

### MVP+α 후보

- **Open3D**, **trimesh** 등을 PyVista 대안으로 검토 (성능·기능 차이)
- **Vispy** 검토 (pyqtgraph 후보 중 일부 케이스에 유리)
- 풀 게임엔진 (Panda3D 등)은 본 프로젝트 범위 밖

---

## 2.6b Plugin SDK Layer (v0.35)

DLC 에코시스템(17 open_platform)을 위한 새 계층. **Domain Layer 위, App Layer 아래**.

### 책임

- DLC가 사용할 **Plugin Protocol** 정의 (Tracker, Detector, Pairing, AngleEstimator 등)
- **Resource 스키마 검증** (Map / Radar / Target TOML)
- **Package Builder** (디렉토리 → .trsim-pkg 압축)
- **Package Validator** (manifest 검증, 호환성 체크)
- **Local Test Runner** (DLC 작성자가 자기 패키지 테스트)

### 위치 및 의존

```
src/workbench/sdk/
├── __init__.py               ← public API (sdk.TrackerProtocol 등)
├── protocols.py              ← Plugin Protocol 정의
├── resource_schemas.py       ← TOML 스키마 (jsonschema 기반)
├── package_builder.py        ← 디렉토리 → .trsim-pkg
├── package_validator.py      ← manifest 검증
└── test_harness.py           ← DLC 로컬 테스트
```

**의존**: `domain/`만. App·UI·Physics 직접 참조 금지.

### 의존 흐름

```
ui → app → sdk → domain → physics
              ↑
        DLC packages (.trsim-pkg)
```

DLC는 **sdk만** 참조. App·UI 코어 변경에 영향 받지 않음 (안정성 보장).

### Public API 설계

```python
# 사용자(DLC 작성자)가 import
import trsim.sdk as sdk

# Plugin 만들기
class MyTracker(sdk.TrackerProtocol):
    def predict(self, state, dt): ...
    def update(self, state, meas): ...

# Resource 검증
sdk.validate_radar_resource("./my_radar.toml")

# DLC 빌드
sdk.build_package(
    package_dir="./my_tracker",
    output="my_tracker.trsim-pkg",
)

# 로컬 테스트
sdk.test_package("my_tracker.trsim-pkg")
```

### Plugin Protocol 분류 (v0.35)

| Protocol | 설명 | DLC 가능? |
|---|---|---|
| `DetectorProtocol` | CFAR 등 검출 알고리즘 | ✅ |
| `PairingProtocol` | FMCW Up/Down 매칭 | ✅ |
| `AngleEstimatorProtocol` | Monopulse 등 각도 추정 | ✅ |
| `TrackerProtocol` | EKF/UKF/Particle Filter 등 | ✅ |
| `PredictorProtocol` | 예측기 (NN 통합 표준) | ✅ |
| `ClassifierProtocol` | 표적 분류 | ✅ |
| `DataAssociatorProtocol` | GNN/JPDA 등 | ✅ |
| `ResourceProtocol` | Map/Radar/Target 자원 | ✅ |
| `UIPanelProtocol` | pyqtgraph/PyVista 패널 | ✅ |
| `MotionKindProtocol` | 새 동역학 타입 | ❌ MVP+α |
| `RadarModelProtocol` | 새 RadarModel | ❌ MVP+α |

**핵심 계층 (알고리즘 + 자원 + 시각화)** 만 DLC 가능. Domain Layer 핵심(MotionKind/RadarModel)은 안정성 위해 비개방.

### Plugin Loader 갱신

기존 v0.13의 단일 `.py` 파일 로드 → v0.35는 `.trsim-pkg` 포함:

```python
# src/workbench/app/package_manager.py (v0.35 신규, app 계층)
class PackageManager:
    """DLC 통합 관리. ~/.trsim/packages/<id>/ 관리."""

    def install(self, package_path: Path) -> InstallResult:
        """1. manifest.toml 검증
           2. compatibility 체크 (TRsim 버전)
           3. ~/.trsim/packages/<id>/ 에 압축 해제
           4. entry_points 등록 (Stage Slot, Resources, UI)
        """
        ...

    def uninstall(self, package_id: str) -> None: ...
    def list_installed(self) -> list[PackageInfo]: ...
    def load_all(self) -> None:
        """앱 시작 시 모든 설치된 패키지 로드."""
        ...
```

### MVP 범위

✅ MVP:
- SDK Plugin Protocol 정의 (위 9개 ✅)
- Resource 스키마 검증
- Package Builder (CLI: `trsim sdk build`)
- Package Validator
- Local Test Runner (`trsim sdk test`)

❌ MVP+α:
- MotionKind / RadarModel plugin
- DLC 의존성 해석 (다른 DLC에 의존)
- DLC 자동 업데이트
- Marketplace 통합

상세: [17 open_platform.md](17_open_platform.md).

---

## 2.6c Physics Layer — 물리 코드 통합 (v0.40 신설)

> **출처**: 19 § 19.4 Physics Layer 분리 (PL-1, PL-2)
> **권위**: 19 physics_lab

### 의도

v0.39 까지 물리 코드가 5 군데 분산: `physics/` (FMCW, ray) + `domain/dynamics/` + `domain/atmosphere/` + `domain/radar/` (RCS, multipath) + `domain/platform.py` (sea state). v0.40 에서 **단일 Physics Layer 로 통합** — 검증·디버깅·진화 용이성 ↑.

### 새 계층 모델

```
┌───────────────────────────────────────────┐
│ UI Layer        (Qt 위젯)                  │
└────────────┬──────────────────────────────┘
             │
             ▼
┌───────────────────────────────────────────┐
│ App Layer       (조율, 명령, 학습)          │
│   + app/physics_lab/  (v0.40 신설)         │
└────────────┬──────────────────────────────┘
             │
             ▼
┌───────────────────────────────────────────┐
│ Domain Layer    (자원 + DSP 알고리즘 만)    │
│   - 물리 코드 빠짐 (Physics Layer 로 이동)  │
└────────────┬──────────────────────────────┘
             │
             ▼
┌───────────────────────────────────────────┐
│ Physics Layer   (모든 물리 법칙) ⭐ v0.40   │
│   - propagation / reflection / dynamics    │
│   - atmosphere / antenna / platform_motion │
│   - test_objects / _testbench              │
└────────────┬──────────────────────────────┘
             │
             ▼
┌───────────────────────────────────────────┐
│ Primitives      (numpy, scipy 만)          │
└───────────────────────────────────────────┘
```

### 원칙

- **Physics Layer 의 의존**: `numpy`, `scipy` 만. Qt X, domain X.
- **Domain → Physics**: 한 방향 (Domain 의 Tracker 가 Physics 의 함수 호출 가능)
- **Physics → Domain**: 금지 (Physics 가 Tracker 모름)
- **App → Physics**: 직접 호출 가능 (Physics Lab 에서)
- **미래 분리 가능**: `pyproject.toml` 별도 entry point — 미래 별도 PyPI 패키지 가능

### Domain 의 정체성 (분리 후)

```
Domain Layer = 자원 모델 + DSP 알고리즘 + 상태
  - dataclass: Map / Radar / Target / Scenario / TrackState
  - 알고리즘: Tracker / Detector / Pairing / Predictor / DataAssociator (DSP)
  - 상태: TrackState / RunState

Physics Layer = 물리 법칙
  - propagation: FMCW, ray tracing, multipath, refraction, atm loss
  - reflection: RCS (single, aspect, ExtendedTarget, glint)
  - dynamics: Newton, drag, lift, aerodynamics
  - atmosphere: ISA, rain, ducting
  - antenna: parabolic, monopulse, beam pattern
  - platform_motion: sea state, function motion
  - test_objects: 9 표준 (Sphere/Cube/Plate/Cylinder/Cone/Point/Plane/Wall/Trihedral)
  - _testbench: analytic_reference, golden_dataset, plot_helpers
```

### 06 § 6.7 결정 변경 (PL-11)

기존 (v0.39): 사용자 물리 plugin 영구 제외.
**v0.40 (변경)**: 사용자 물리 plugin 가능, **Physics Lab 검증 통과한 것만 시뮬에서 사용**.
- Validation Bench 가 안전망
- 17종 회귀 자동 검증
- 분석 공식 비교 가능
- PhysicsModelProtocol (11번째 SDK Plugin Protocol) 정의 — 17 § 17.4.1

상세: [19 physics_lab.md](19_physics_lab.md), [06 § 6.7 topics](06_topics.md).

---

## 2.7 오류 처리 & 로깅

### 로그 레벨 정책

- DEBUG: 개발 시 상세 추적
- INFO: 주요 사용자 행동 (Scenario 로드, Run 시작/완료)
- WARNING: 비정상이지만 계속 진행 (Plugin 로드 실패 시 기본 사용)
- ERROR: 사용자에게 알려야 함 (시나리오 파일 파싱 실패)
- CRITICAL: 앱 종료 수준

### 플러그인 에러 격리

사용자 플러그인 예외가 Workbench 전체를 죽이지 않게:

```python
try:
    peaks = plugin.detect(spectrum)
except Exception as e:
    log.error(f"Plugin {plugin.name} raised: {e}", exc_info=True)
    event_bus.emit("plugin_error", plugin, e)
    # → UI에 오류 표시, Run은 중단
```

MVP에서는 **Run 중단 + 오류 리포트**만. 샌드박싱은 비신뢰 환경 때.

---

## 2.8 설정 (Config) 관리

### 3단 구조

```
1. 코드 기본값 (하드코딩된 상수, Physics 파라미터 등)
2. 시스템 설정 (사용자 PC 고유, ~/.workbench/config.toml)
3. 워크스페이스 설정 (프로젝트별, .workbench/workspace.toml)
```

### 포맷

- TOML (Python 표준 `tomllib`, 사람이 읽기 좋음)
- 사용자 편집용 값은 TOML, 내부 직렬화는 JSON (Run 결과 등)

### QSettings는 쓰지 않는다

이유: 플랫폼별로 저장 위치 달라서 "내 설정 어디 있지?" 문제 발생.
직접 TOML 파일을 지정된 경로에 둠.

---

## 2.9 모듈 도입 이력 (v0.18~v0.35)

본 워크벤치 설계는 v0.16 이후 빠르게 확장됐다. 새 Claude·새 개발자가 **각 모듈이
어느 버전·어느 통찰에서 도입됐는지** 한눈에 파악할 수 있게 정리.

### App Layer 신규 모듈

| 모듈 | 도입 | 통찰 / 트리거 | 핵심 책임 |
|---|---|---|---|
| `WorkspaceManager` | v0.19 | "프로그램은 두 갈래" | Editor/Simulator 전환, DockLayout 저장 |
| `ResourceLibrary` | v0.20 | "맵·레이더·표적 따로 로드" | maps/radars/targets 디렉토리 인덱스 |
| `ResourceCache` | v0.20 | "자원 수정해도 과거 Run 재현" | content_hash 기반 in-memory 캐시 |
| `BundleService` | v0.20 | "다른 PC에서 재현" | .scnbundle/.runbundle export·import |
| `CoherenceValidator` | v0.21~v0.29 | "이전 프로젝트 건물이 떴어" | 6종 일관성 검사 |
| `DEMImportPipeline` | v0.22 | "DEM은 육상만 쓰니까 자체 규격으로" | 외부 DEM → terrain.npz |
| `app/nn/DataExporter` | v0.13 | NN 통합 | Pipeline에서 sample 수집 |
| `app/nn/DatasetBuilder` | v0.13 / v0.30 | NN 통합 + Variant 확장 | Variant 6종 자동 빌드 |
| `app/nn/TrainerService` | v0.13 | NN 통합 | 내부 간단 학습 |
| `app/nn/NNEvaluator` | v0.13 | NN 통합 | 4-error 진단 |

### Domain Layer 신규 모듈

| 모듈 | 도입 | 통찰 / 트리거 | 핵심 책임 |
|---|---|---|---|
| `geo.py` (GeoOrigin, VerticalReference) | v0.21 | "맵 기준 좌표 중요" | 좌표계 정합성 — 불변 Origin + 명시적 vertical |
| `map_resource.py` (Map, WorkbenchTerrain) | v0.21~v0.22 | DEM 한계 + 자체 규격 | terrain.npz + land_mask 구조 |
| `coastline.py` | v0.22 | 해안선 명시 필요 | CoastlinePolygon |
| `terrain_sampling.py` | v0.22 | "land_mask=False면 해수면" | sample_terrain() — DEM 부정확 차단 |
| `simulation_domain.py` | v0.29 | "맵 10km인데 빔이 50km" | SimulationDomain + OutsideEnvironment + sample_terrain_safe() |
| `placement.py` (PlacedEntity, MotionKind) | v0.21~v0.27 | base/current 분리 + motion_kind 7 | 모든 자원 공통 위치 추상 |
| `wave_response.py` | v0.21 | 환경/응답 분리 | 4 프리셋 (large_ship 등) |
| `building.py` (Anchor 4 mode) | v0.21 | DEM 자동 정합 | base_to_terrain 기본 |
| `target.py` (TargetWaypoint, TargetEntity) | v0.21 | reference 도입 전 단순 보간 | (v0.27에서 reference로 의미 변경) |
| `dynamics/state.py` | v0.27 | "중력이 모든 동적 오브젝트에" | RigidBodyState, Forces |
| `dynamics/params.py` | v0.27 | 표적별 파라미터 | AircraftParams/PoweredFlightParams/BallisticParams 등 |
| `dynamics/forces.py` | v0.27 | 외력 모델 | gravity/drag/lift/thrust/control |
| `dynamics/solver.py` | v0.27 | 동역학 적분 | RK4, dt=0.05s |
| `dynamics/motion_models.py` | v0.27 | motion_kind별 외력 | compute_forces_for_motion_kind() |
| `dynamics/impact.py` | v0.27 | BALLISTIC 충돌 | 지면 ↔ 자유낙하 종료 |
| `atmosphere.py` | v0.28 | "대기 상태 표현" | AtmosphereState + ISA |
| `rain_attenuation.py` | v0.28 | 폭우 시 SNR 영향 | ITU-R P.838 단순화 |
| `antenna.py` | v0.25 | "안테나 형태도 편집" | Parabolic/PlanarArray |
| `rx_channels.py` | v0.25 | 추적 표준 모노펄스 | RXChannelKind, MonopulseRXConfig |
| `monopulse.py` | v0.25 | error_az/el → Tracker | Σ·Δ 비율 → angle error |
| `platform.py` (motion_kind 추가) | v0.18~v0.24 | Radar Platform 다양화 | Maritime/Fixed Ground + motion_kind 매핑 |
| `platform_motion.py` | v0.18 | 플랫폼별 운동 | sea_state / stationary |
| `propagation/multipath.py` | v0.34 | "MATLAB·Stone Soup 비교 시 sea bounce 빠짐" | Two-ray multipath (해상 시나리오 핵심) |
| `propagation/refraction.py` | v0.34 | 장거리 추적 정확도 | 4/3 earth radius (베이스라인 표준) |
| `scattering.py` (Scatterer, ExtendedTarget) | v0.34 | "단일 표적 추적 안정성의 핵심 변수 glint 부재" | Multi-scatterer → glint 자동 발생 |
| `tracker_ekf.py` (리팩토링) | v0.34 (v0.10에서) | EKF/UKF 선택 가능 분리 | 기존 EKF를 별도 모듈로 |
| `tracker_ukf.py` | v0.34 | "Stone Soup·MATLAB 표준" | UKF (sigma point) — 비선형성 큰 환경 |
| `data_associator.py` | v0.34 | "다중 환경에서 단일 표적 선택 시뮬 필수" | GNN + Hungarian (다중 표적 1:1 매칭) |
| `detector_cfar.py` (OS 추가) | v0.34 | 클러터 환경 표준 | CA-CFAR + OS-CFAR 선택 가능 |

### SDK Layer 신규 모듈 (v0.35)

| 모듈 | 도입 | 통찰 / 트리거 | 핵심 책임 |
|---|---|---|---|
| `sdk/protocols.py` | v0.35 | "DLC 작성자가 사용할 안정 API 필요" | 9 Plugin Protocol 정의 |
| `sdk/resource_schemas.py` | v0.35 | "TOML 검증 표준화" | Map/Radar/Target jsonschema |
| `sdk/package_builder.py` | v0.35 | ".trsim-pkg 빌드" | 디렉토리 → 압축 |
| `sdk/package_validator.py` | v0.35 | "manifest 검증" | manifest.toml + entry_points |
| `sdk/test_harness.py` | v0.35 | "DLC 작성자가 로컬 테스트" | `trsim sdk test` CLI |
| `app/package_manager.py` | v0.35 | "DLC install/load 통합 관리" | ~/.trsim/packages/ 관리 |
| `app/panel_registry.py` | v0.35 | "DLC UI 패널 등록" | Built-in + DLC 패널 통합 |
| `io/package_io.py` | v0.35 | ".trsim-pkg 압축 형식" | zip pack/unpack |

### UI Layer 신규 모듈

| 영역 | 도입 | 통찰 / 트리거 | 모듈 |
|---|---|---|---|
| Editor Workspace | v0.19~v0.26 | 두 Workspace 구조 | `ui/editor/*` 전체 |
| Resource Browser | v0.20 | 자원 라이브러리 | `resource_browser.py` |
| Scenario Composer | v0.26 | 메인 활동 | `scenario_composer/*` |
| Map Editor (경량) | v0.22~v0.26 | 자체 규격 편집 | `map_editor/*` |
| DEM Import Wizard | v0.22 | 7 step 변환 | `dem_import_wizard.py` |
| Domain Settings | v0.29 | Simulation Domain | `domain_settings.py` |
| Radar Editor | v0.25 | 안테나 편집 | `radar_editor.py` |
| Targets Editor (메타) | v0.26 | trajectory CSV import | `targets_editor.py` |
| Atmosphere Panel | v0.28 | 대기 편집 | `atmosphere_panel.py` |
| Range-Doppler Panel | v0.13 | 검출 시각화 | `range_doppler_panel.py` |
| Stage I/O Panel | v0.14 | 스테이지 디버그 | `stage_io_panel.py` |
| 3D Scene (PyVista) | v0.28 | smooth shading + 셰이더 | `scene_3d/*` |
| NN Mode UI | v0.13 / v0.30 | NN 통합 + Variant 확장 | `nn_mode/*` |
| Package Manager UI | v0.35 | DLC install/uninstall | `package_manager_panel.py` |

### IO Layer 신규 모듈

| 모듈 | 도입 | 핵심 책임 |
|---|---|---|
| `dem_import.py` | v0.22 | DEM Wizard 백엔드 |
| `bundle_io.py` | v0.20 | tar.gz pack/unpack |
| `workbench_native.py` | v0.22 | terrain.npz 읽기/쓰기 |

### 핵심 통찰의 흐름 (요약)

1. v0.13 — NN 통합 (Step 1/2 + 4-error)
2. v0.14 — Run·시간 모델 + CommandBus
3. v0.15 — SimulationClock + InputBuffer
4. v0.18 — Radar Platforms (Maritime + Fixed Ground)
5. **v0.19 — "프로그램은 두 갈래"** → 두 Workspace
6. **v0.20 — "맵·레이더·표적 따로"** → 자원 참조 + Bundle
7. **v0.21 — "맵 기준 좌표 중요"** → 좌표계 정합 + base/current
8. **v0.22 — "DEM 부정확"** → 자체 규격 terrain.npz + land_mask
9. **v0.25 — "안테나도 편집"** → Antenna 일반화 + 모노펄스
10. **v0.27 — "중력이 적용되어야"** → 사실적 동역학 + MotionKind 7
11. **v0.28 — "파도·표적 출렁·대기 표현"** → 시각화 하이브리드 + 대기 모델
12. **v0.29 — "맵 10km인데 빔이 50km"** → Simulation Domain
13. v0.30 — NN Variant 확장 (v0.25~v0.29 정합)
14. v0.31 — 04 migration Phase 갱신
15. v0.32 — 02 architecture 갱신 + 모듈 도입 이력 신설
16. v0.33 — Map Editor Flatten Area (정박지·활주로·부지)
17. **v0.34 — "이 프로그램이 생명력을 얻으려면 베이스라인 점검이 필요해"** → MATLAB·Stone Soup·RadarSimPy 비교 → 5종 MVP 추가 (Two-ray multipath / Multi-scatterer + Glint / EKF+UKF / GNN / Refraction) + 16 baseline_audit 신규
18. **v0.35 — "오픈소스로 공개 + DLC 같은 확장"** → 정체성 전환: "검증 도구 → 확장 가능 플랫폼". Apache 2.0, GitHub public, .trsim-pkg DLC, SDK Layer 신설, 17 open_platform 신규

이 패턴 지속: **사용자가 "왜 이게 안 되지?" 짚으면 → 진단 → 추상 일반화 → 모듈 추가**.

---

## 섹션 상태

- 2.1 설계 원칙 — ✅
- 2.2 블록도 — ✅ (v0.35 갱신 — v0.34 베이스라인 + v0.35 SDK Layer 모두 반영)
- 2.2a CommandBus — ✅ (v0.14)
- 2.2b SimulationClock — ✅ (v0.15)
- 2.3 디렉토리 — ✅ (v0.34 갱신 — propagation/scattering/tracker_ukf/data_associator 추가, v0.35 sdk/ 추가)
- 2.4 스레드 모델 — ✅ (v0.15 Sim 스레드 루프 재작성)
- 2.5 의존 규칙 — ✅ (v0.35 SDK Layer 격리 추가, v0.31 Workspace 분리·Visualization 격리·NN 격리)
- 2.6 Qt 통합 — ✅
- 2.6a 시각화 라이브러리 스택 — ✅ (v0.28)
- 2.6b Plugin SDK Layer — ✅ (v0.35 신설, DLC 시스템)
- 2.7 오류 처리 — 🟡
- 2.8 Config — 🟡
- 2.9 모듈 도입 이력 — ✅ (v0.31 신설, v0.34/v0.35 모듈 추가됨)

---

👉 다음 섹션: [03_data_model.md](03_data_model.md)
