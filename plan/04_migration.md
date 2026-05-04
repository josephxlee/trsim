# 04. 구현 전략

**최종 갱신**: 2026-05-02 (v0.40 — Phase 2 끝 Physics Layer 통합 추가, Phase 9 Physics Lab 신설 — Wave 4 MVP+α)

v0.16~v0.35 계획서 기반으로 새 레포 `workbench`를 **신규 구현**하는 순서와 기준.

> ⚠️ **기존 `sim_3d` 프로토타입은 정상 동작이 검증되지 않은 코드** 입니다. 본 구현은 회귀 비교나
> 직접 이식 대상으로 삼지 않고, **계획서 기반 신규 작성**을 원칙으로 합니다. 검증은 분석 공식
> (수계산) + Stone Soup·MATLAB 비교로 합니다.

## 4.1 구현 원칙

### 원칙 1: 계층별 신규 작성 + 한 단계씩

한 번에 전체를 만들지 않는다. 각 모듈마다:
1. 계획서 기반 인터페이스 (Contract / Protocol) 먼저 정의
2. 분석 공식 (수계산) 또는 reference (Stone Soup 등) 로 검증
3. 단위 테스트 작성
4. 통합 테스트로 새 시스템에서 동작 확인

### 원칙 2: 검증 기준은 분석 공식 + 외부 reference

회귀 비교용 옛 코드 없음. 검증은:
- **분석 공식**: 레이더 방정식, FFT 의 수학적 특성, ENU↔WGS84 변환 (알려진 좌표쌍)
- **Stone Soup**: 같은 알고리즘 (EKF/UKF/GNN) 의 reference 라이브러리 비교
- **MATLAB Phased Array Toolbox**: 산업 표준 비교 (가능한 경우)
- **물리 한계**: 라이트 속도 / Earth radius / 대기 ISA 표준값

### 원칙 3: 의존성이 얕은 것부터

순서 규칙: **Primitives → Domain → Application → UI**.
가장 안쪽 계층부터 만들고 바깥으로.

### 원칙 4: 테스트 없이는 머지 안 함

모든 PR 은 단위 또는 통합 테스트 동반. CI 가 강제.

---

## 4.2 구현 대상 모듈 (계층별)

각 Phase 별 상세 체크리스트는 § 4.3 참조. 본 절은 전체 모듈 지도.

### Primitives Layer (`physics/`)

순수 함수 — Qt·domain 의존 없음.

| 모듈 | 역할 | 검증 |
|---|---|---|
| `physics/fmcw.py` | beat freq, FFT, range/velocity 변환 | 수계산: range 1km → beat 666.7Hz |
| `physics/ray_tracing.py` | LOS 차폐 검사, 빔-지형 교차 | 분석 공식: horizon distance |
| `physics/reflections.py` | RCS, 멀티패스 합성 | 문헌값 (Skolnik, Mahafza) |
| `physics/geometry.py` | 거리·각도·좌표 변환 | 알려진 좌표쌍 |

### Domain Layer (`domain/`)

상태·규칙·Contract — UI·시각화·플러그인 직접 의존 없음.

| 모듈 | 역할 | 출처 |
|---|---|---|
| `domain/geo.py` | GeoOrigin, VerticalReference | v0.21, 11 |
| `domain/map_resource.py` | Map, WorkbenchTerrain | v0.21~v0.22 |
| `domain/terrain_sampling.py` | sample_terrain_safe (land_mask, Domain 정책) | v0.22, v0.29 |
| `domain/simulation_domain.py` | SimulationDomain, OutsideEnvironment | v0.29 |
| `domain/placement.py` | PlacedEntity, MotionKind 7 | v0.21~v0.27 |
| `domain/wave_response.py` | WaveResponseModel + 4 프리셋 | v0.21 |
| `domain/building.py` | BuildingEntity, Anchor 4 mode | v0.21 |
| `domain/target.py` | TargetEntity, TargetWaypoint | v0.21 |
| `domain/dynamics/*` | 6 모듈 (state/params/forces/solver/motion_models/impact) | v0.27, 14 |
| `domain/atmosphere.py` | AtmosphereState, ISA | v0.28, 15 |
| `domain/rain_attenuation.py` | ITU-R P.838 단순화 | v0.28 |
| `domain/refraction.py` | 4/3 earth radius (effective) | v0.34, 15 § 15.5.4 |
| `domain/scattering.py` | Scatterer, ExtendedTarget (multi-scatterer + glint) | v0.34, 14 § 14.10 |
| `domain/multipath.py` | Two-ray sea bounce | v0.34, 08 § 8.5b.1 |
| `domain/antenna_config.py` | AntennaConfig + beam_pattern | v0.25 |
| `domain/platform.py` | RadarPlatform, motion_kind | v0.18~v0.24 |
| `domain/contracts.py` | 9 Pipeline Stage Slot Contract | 03 § 3.3, 07 § 7.2 |
| `domain/pipeline.py` | RadarPipeline + Stage Slot | v0.13/v0.27 |

### Application Layer (`app/`)

Domain 위에서 조립·실행.

| 모듈 | 역할 | 출처 |
|---|---|---|
| `app/command_bus.py` | Single Command Path (포지셔너 명령 단일 버스) | v0.14 |
| `app/simulation_clock.py` | Sim/Target 두 레이어 시간 제어 | v0.15 |
| `app/event_bus.py` | 모듈 간 통신 | v0.13 |
| `app/resource_library.py` | 자원 인덱스 (User > Packages > Built-in 우선순위) | v0.20, v0.35 |
| `app/resource_cache.py` | content_hash 캐시 | v0.20 |
| `app/bundle_service.py` | .scnbundle/.runbundle | v0.20 |
| `app/coherence_validator.py` | 6종 정합성 검사 | v0.21~v0.29 |
| `app/plugin_loader.py` | 동적 플러그인 로드 | v0.13 |
| `app/plugin_scanner.py` | AST 스캔 (GT Isolation) | v0.14 |
| `app/run_manager.py` | Run 생애주기 | v0.13 |
| `app/probe_recorder.py` | Stage I/O HDF5 기록 | v0.14 |
| `app/physics_gate.py` | 물리 건전성 자동 검사 | v0.13 |
| `app/package_manager.py` | .trsim-pkg install/load | v0.35, 17 |
| `app/panel_registry.py` | DLC UI 패널 등록 | v0.35, 17 |
| `app/nn/*` | NN 통합 4 모듈 (Phase 6) | v0.30, 07 |

### SDK Layer (`sdk/`)

DLC 작성자용 안정 Public API. Domain 만 import.

| 모듈 | 역할 | 출처 |
|---|---|---|
| `sdk/protocols.py` | 9 Plugin Protocol | v0.35, 17 § 17.2.6 |
| `sdk/manifest.py` | PackageManifest 7 dataclass | v0.35, 03 § 3.2.1l |
| `sdk/resource_schemas.py` | TOML 스키마 | v0.35 |
| `sdk/package_builder.py` | `.trsim-pkg` 빌드 CLI | v0.35 |
| `sdk/package_validator.py` | manifest 검증 | v0.35 |
| `sdk/test_harness.py` | DLC 로컬 테스트 | v0.35 |

### UI Layer (`ui/`)

Editor / Simulator / 공통.

| 영역 | 모듈 | 출처 |
|---|---|---|
| 공통 | main_window, workspace_selector, dock_manager, command_palette, toolbar, menu, theme | v0.13~v0.19 |
| Editor (`ui/editor/`) | activity_selector, resource_browser, scenario_composer/*, map_editor/* (Flatten Area v0.33), radar_editor, targets_editor, atmosphere_panel | v0.19~v0.33 |
| Simulator (`ui/simulator/`) | scenario_explorer, fft_panel, range_doppler_panel, plugin_manager_panel, run_panel, properties_panel, stage_io_panel, physics_validation_panel, scene_3d/* (PyVista), nn_mode/* (Phase 6) | v0.13~v0.34 |

### IO Layer (`io/`)

| 모듈 | 역할 |
|---|---|
| `io/scenario_loader.py` | TOML refs 해결 |
| `io/run_storage.py` | Run Manifest |
| `io/trace_storage.py` | Trace HDF5 |
| `io/dem_import.py` | DEM Import Wizard |
| `io/bundle_io.py` | tar.gz pack/unpack |
| `io/workbench_native.py` | terrain.npz |
| `io/package_io.py` | .trsim-pkg pack/unpack |
| `io/mesh_loader.py` | STL/OBJ |

### Plugins Built-in (`plugins_builtin/`)

기본 Plugin 구현체 — Domain Contract 직접 구현.

- default_detector (CA-CFAR + OS-CFAR)
- default_pairing (Triangle Up/Down 매칭)
- default_angle_estimator (sum-channel + monopulse 4ch)
- default_data_associator (GNN + Hungarian)
- default_tracker_ekf, default_tracker_ukf
- default_predictor
- default_classifier (스텁)

---

## 4.3 구현 순서 (Phase 0~7)

**마감이 없으므로 Phase 크기는 크게 잡음. 각 Phase는 "다음 Phase가 의존할 수 있는 상태"를 만드는 게 목표.**

### Phase 0: 레포 뼈대

목표: `pip install -e .` 로 빈 앱이 실행되는 상태 + **오픈소스 인프라 갖춤** (v0.35).

#### 코드
- [ ] 새 레포 생성, `pyproject.toml` 적용 (초안 `repo_root_drafts/pyproject.toml`)
- [ ] `.importlinter` 적용 (의존 규칙 자동 검사 — `repo_root_drafts/.importlinter`)
- [ ] 디렉토리 구조 생성 (빈 `__init__.py` 포함)
- [ ] `python -m workbench` 가 빈 QMainWindow 하나 띄움
- [ ] pytest 기본 세팅, "hello world" 테스트 하나
- [ ] `lint-imports` 통과 (Layer/Workspace/Domain 격리 검증)

#### 오픈소스 인프라 (v0.35)
- [ ] `LICENSE` — Apache 2.0 (전문)
- [ ] `NOTICE` — 서드파티 라이선스 목록
- [ ] `README.md` — 비전, 설치, Quick Start
- [ ] `CONTRIBUTING.md` — 기여 가이드 (DCO 명시)
- [ ] `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1
- [ ] `GOVERNANCE.md` — BDFL → Core team 진화 명시
- [ ] `SECURITY.md` — 취약점 신고 방법
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` — DCO 체크리스트
- [ ] `.github/ISSUE_TEMPLATE/{bug,feature,question}.md`
- [ ] `.github/workflows/ci.yml` — pytest + import-linter + ruff + mypy + DCO check

완료 기준: 사용자가 `clone → install → run`으로 빈 창 본다 + 외부인이 보면 "오픈소스 프로젝트로 보인다" + CI 가 모든 의존 규칙·lint·type 검사 통과.

### Phase 1: Primitives 구현

목표: 물리 함수들이 `workbench/physics/`에서 호출 가능 + 분석 공식 검증 통과.

- [ ] `physics/fmcw.py` 신규 작성 (수계산 검증: range 1km → beat 666.7Hz 등)
- [ ] `physics/ray_tracing.py` 신규 작성 (horizon distance, Two-ray geometry)
- [ ] `physics/reflections.py` 신규 작성 (Skolnik/Mahafza 문헌값 검증)
- [ ] `physics/geometry.py` 신규 작성 (알려진 좌표쌍 검증)
- [ ] `domain/geo.py`, `domain/terrain.py`, `domain/building.py` 신규 작성
- [ ] `domain/positioner_spec.py`, `domain/antenna_spec.py` 신규 작성
- [ ] 각 모듈에 **최소 스모크 테스트** 작성

완료 기준: `pytest tests/unit/physics/` 전부 통과.

### Phase 2: Domain — Contract 정의 + 기본 파이프라인

목표: Contract 정의 완료 + 기본 플러그인 6개 동작. **사실적 도메인 모델** 모두 포함.

#### 핵심 Contract·타입
- [ ] `domain/contracts.py` — 6 Protocol 정의 (Detector, AngleEstimator, Pairing, Tracker, Predictor, Classifier)
- [ ] `domain/contracts.py`에 **`PositionerCommand`, `CommandSource`** 타입 (v0.14)
- [ ] `PositionerController.set_target(cmd: PositionerCommand)` 시그니처
- [ ] `domain/types.py` — Peak, Detection, Track, **`RunState`/`RunTerminationReason`/`SimulationState`/`SpeedMultiplier`** (v0.14~v0.15)

#### Pipeline + 환경
- [ ] `domain/pipeline.py` — RadarPipeline (Contract 기반)
- [ ] `domain/environment.py` — sim_engine 물리 부분만
- [ ] `plugins_builtin/default_*.py` — 기본 구현 6개

#### Map + 좌표계 (v0.21~v0.22)
- [ ] `domain/geo.py` — `GeoOrigin`, `VerticalReference`, `VerticalRefType` (v0.21)
- [ ] `domain/map_resource.py` — `Map`, `MapBounds`, `SeaSurface`, `WorkbenchTerrain` (v0.21~v0.22)
- [ ] `domain/coastline.py` — `CoastlinePolygon` (v0.22)
- [ ] `domain/terrain_sampling.py` — `sample_terrain()` (land_mask 기반, v0.22)
- [ ] `domain/simulation_domain.py` — **`SimulationDomain`, `OutsideEnvironment` enum, `sample_terrain_safe()`** (v0.29)

#### Placement + Motion (v0.21~v0.27)
- [ ] `domain/placement.py` — `MotionKind` enum 7종 (v0.21+v0.27), `PlacedEntity`, `CurrentPose`
- [ ] `domain/wave_response.py` — `SeaStateEnvironment`, `WaveResponseModel`, 4 프리셋 (v0.21)
- [ ] `domain/building.py` — `AnchorMode` 4종 + `MeshOrigin` 3종 + `BuildingEntity` (v0.21)
- [ ] `domain/target.py` — `TargetWaypoint`, `TargetEntity` (v0.21)

#### Dynamics (v0.27)
- [ ] `domain/dynamics/state.py` — `RigidBodyState`, `Forces` (v0.27)
- [ ] `domain/dynamics/params.py` — `DynamicsParams`, `AircraftParams`, `PoweredFlightParams`, `BallisticParams`, `GroundVehicleParams`, `SurfaceVesselParams`
- [ ] `domain/dynamics/forces.py` — gravity / drag / lift / thrust / control 계산
- [ ] `domain/dynamics/solver.py` — `DynamicsSolver` (RK4)
- [ ] `domain/dynamics/motion_models.py` — motion_kind별 외력 계산
- [ ] `domain/dynamics/impact.py` — BALLISTIC 지면 충돌 처리

#### Atmosphere (v0.28 + v0.34 refraction)
- [ ] `domain/atmosphere.py` — `AtmosphereState`, ISA density·temperature 함수
- [ ] `domain/rain_attenuation.py` — ITU-R P.838 단순화
- [ ] `domain/propagation/refraction.py` — 4/3 earth radius (v0.34)

#### Propagation (v0.34 신설 — 베이스라인 보강)
- [ ] `domain/propagation/multipath.py` — Two-ray multipath (sea bounce)
- [ ] LOS 차폐 검사에 effective_earth_radius_m 통합

#### Antenna (v0.25)
- [ ] `domain/antenna.py` — `AntennaType` enum, `AntennaConfig` Protocol
- [ ] `domain/antenna.py` — `ParabolicAntenna`, `PlanarArrayAntenna`
- [ ] `domain/rx_channels.py` — `RXChannelKind`, `RXChannelSpec`, `MonopulseRXConfig`, `RXArrayConfig`
- [ ] `domain/monopulse.py` — error_az/el_rad 계산 (Σ·Δ 채널 비율)
- [ ] `domain/monopulse.py` — extended target 합성 (v0.34, glint 자동 발생)

#### Extended Target — Multi-scatterer + Glint (v0.34 신설)
- [ ] `domain/scattering.py` — `Scatterer`, `ExtendedTarget`, `ScatteringResult`
- [ ] `domain/scattering.py` — `compute_extended_target_return()`
- [ ] 표적 Preset 9종에 `scatterers.toml` 기본값 (3~5개씩)

#### Tracker — EKF + UKF + GNN (v0.34 신설)
- [ ] `domain/tracker_ekf.py` — `EKFTracker` (v0.10에서 리팩토링)
- [ ] `domain/tracker_ukf.py` — `UKFTracker` (Stone Soup 호환)
- [ ] `domain/data_associator.py` — `GNNDataAssociator` (Hungarian)
- [ ] `domain/contracts.py`에 `TrackerKind` enum 추가

#### Detection — CFAR (v0.34 보강)
- [ ] `domain/detector_cfar.py` — `CACFARDetector` (기존), `OSCFARDetector` (v0.34 신설)

#### Platform (v0.18~v0.24)
- [ ] `domain/platform.py` — `RadarPlatform`, `PlatformCategory`, `PlatformMotionModel`
- [ ] `domain/platform.py` — `motion_kind` 필드 (v0.24 매핑)

#### Scenario (v0.20+)
- [ ] `domain/scenario.py` — Scenario dataclass with `[refs]` + `[composition]` + `[platform_install]`
- [ ] `domain/scenario.py` — `simulation_domain_override`, `outside_environment_override` (v0.29)
- [ ] `domain/scenario.py` — `multipath_enabled`, `tracker_kind` (v0.34)
- [ ] `io/scenario_loader.py` — TOML 기반 ref 해결

#### Reference Timing + Frame Profiler 데이터 모델 (v0.39)
- [ ] `domain/timing/reference_timing.py` — StageTimingProfile / TimingConfig / ReferenceTimingState dataclass (03 § 3.2.1n)
- [ ] `domain/timing/frame_profiler.py` — StageTimingStat / FrameTimingReport dataclass
- [ ] Scenario TOML 에 `[timing]` + `[[timing.profiles]]` 섹션 파서

#### Physics Layer 통합 (v0.40, PL-1, PL-2)
- [ ] `domain/dynamics/` → `physics/dynamics/` 이동
- [ ] `domain/atmosphere/` → `physics/atmosphere/` 이동
- [ ] `domain/radar/` 의 multipath / antenna / RCS → `physics/{propagation,antenna,reflection}/` 이동
- [ ] `domain/platform.py` 의 sea state → `physics/dynamics/platform_motion.py` 이동
- [ ] `physics/test_objects.py` — 9 Test Objects dataclass (03 § 3.2.1o)
- [ ] `physics/_param_metadata.py` — ParamMetadata + `@physics_param` decorator
- [ ] `physics/_testbench/analytic_reference.py` — 분석 공식 reference
- [ ] `physics/_testbench/golden_dataset/` — 알려진 reference 값
- [ ] `sdk/protocols.py` 에 `PhysicsModelProtocol` 추가 (11번째)
- [ ] `domain/` import 정리 — Physics 참조는 `physics.X` 로
- [ ] `pyproject.toml` 의 `.importlinter` 갱신 — Physics → Domain 금지 규칙
- [ ] **검증**: 17종 회귀 모두 PASS (이동 후 회귀 없음 확인)

#### 검증
- [ ] **통합 테스트**: 시나리오 하나 로드 → 1프레임 돌려서 Track 나오는지
- [ ] **Coherence Validator** 6종 검사 (vertical_ref / 해안선 / 건물 / 해상 / vertical_명시 / **Simulation Domain**)
- [ ] **베이스라인 검증** (v0.34): two-ray multipath lobing, glint emergence, EKF vs UKF 비교, GNN association

완료 기준: **UI 없이도** `workbench-cli`로 `scenario + plugins → run → metrics.json` 파이프라인 완결. Physics Layer 분리 후 회귀 없음.

### Phase 3: Application 계층

목표: UI 이전에 Application이 완전히 동작. **자원 라이브러리·Bundle·재현성** 포함.

#### 명령 + 이벤트
- [ ] `app/command_registry.py`, `app/commands/` 기본 명령 세트
  - **Sim 명령**: `sim.start`, `sim.pause`, `sim.stop`, `sim.set_speed` (v0.15)
  - **Target 명령**: `target.run`, `target.pause`, `target.stop` (v0.14)
  - **Positioner 명령**: `positioner.toggle_mode`, `positioner.manual_adjust` (v0.14)
  - **Editor 명령**: `editor.save_resource`, `editor.validate`, `editor.export_bundle` (v0.19~v0.20)
  - **Workspace 명령**: `workspace.switch_to_editor`, `workspace.switch_to_simulator` (v0.19)
- [ ] `app/event_bus.py`
- [ ] `app/command_bus.py` — **포지셔너 명령 단일 경로, Lineage 기록** (v0.14)

#### Plugin
- [ ] `app/plugin_loader.py` — 동적 `.py` 로드
- [ ] `app/plugin_scanner.py` — **AST 정적 스캔, GT Isolation Level 3-1** (v0.14)

#### Workspace + 자원 (v0.19~v0.20)
- [ ] `app/workspace_manager.py` — Editor/Simulator 전환, DockLayout 저장 (v0.19)
- [ ] `app/resource_library.py` — `resources/maps/`, `resources/radars/`, `resources/targets/` 인덱스
- [ ] `app/resource_cache.py` — content_hash 기반 캐시 (v0.20)
- [ ] `app/bundle_service.py` — `.scnbundle` / `.runbundle` export·import (v0.20)
- [ ] `app/scenario_service.py`

#### 시간 제어 + Run
- [ ] `app/simulation_clock.py` — **두 레이어 시간 제어 Layer 1** (v0.15)
- [ ] `app/input_buffer.py` — **Sim PAUSED 중 UI 입력 버퍼** (v0.15)
- [ ] `app/probe_recorder.py` — **CSV export 지원** (v0.14)
- [ ] `app/run_manager.py` — Target Run State Machine + `RunTerminationReason`
- [ ] `app/evaluator.py` — **Command Lineage 검증** (v0.14 Level 3-2)
- [ ] `app/physics_gate.py` (MVP는 간단한 검사)

#### IO
- [ ] `io/run_storage.py` — Run Manifest with `resource_refs` (v0.20)
- [ ] `io/trace_storage.py`
- [ ] `io/dem_import.py` — **Import Wizard 백엔드, terrain.npz 변환** (v0.22)

#### CLI 검증
- [ ] **CLI로 Run 생성, 저장, 재실행** 가능

#### Reference Timing + Frame Profiler 구현 (v0.39)
- [ ] `app/timing/performance_clock.py` — SimulationClock 확장 (sleep / scale_factor 보정)
- [ ] `app/timing/frame_boundary_detector.py` — 자동 frame 추론 (TrackOutput trigger)
- [ ] `app/timing/stage_timing_probe.py` — Stage 시작·끝 perf_counter_ns 측정
- [ ] `app/timing/frame_profiler.py` — Pre-run 측정 + 백그라운드 통계 (avg / p50 / p95 / p99)
- [ ] CLI: `trsim profile <scenario> --frames 100 --output profile.json`
- [ ] Profile 모드 toggle (off / explicit / live, Q4)
- [ ] Warmup discard (첫 10 frames, Q-RT7)

완료 기준:
```
workbench-cli run --scenario A_Base --plugin examples/my_detector.py
→ Sim 자동 시작, Target Run 실행, 결과 생성, ~/.workbench/runs/ 에 저장됨
→ Command Lineage 검증 리포트 동반
→ Run Manifest에 resource_refs(map/radar/targets hash) 기록

trsim profile A_Base --frames 100
→ FrameTimingReport 생성, JSON 저장, Stage avg/p95/p99 stdout 출력
```

### Phase 4: UI 기본 레이아웃

목표: MVP UI 완성. **두 Workspace + Editor Activity 5종**.

#### 시각화 라이브러리 (v0.28)
- [ ] `pyqtgraph` 의존성 추가
- [ ] `pyvista` + `pyvistaqt` 의존성 추가 (3D Scene View 한정)

#### Main Window + Workspace (v0.19)
- [ ] `ui/main_window.py` — 얇은 조립자 (200줄 이하)
- [ ] `ui/workspace_selector.py` — Editor/Simulator 전환 UI (v0.19)
- [ ] `ui/dock_manager.py` — Workspace별 독립 레이아웃 저장
- [ ] `ui/command_palette.py`
- [ ] `ui/toolbar.py` — **두 레이어 구성** (Sim/Target) (v0.15)
- [ ] `ui/menu.py`

#### Editor Workspace (v0.26 — 13)
- [ ] `ui/editor/activity_selector.py` — 5 Activity 좌측 아이콘 (Composer / Map / Radar / Targets / Browser)
- [ ] `ui/editor/resource_browser.py` — 상시 사이드바, 자원 트리 + 상태 인디케이터
- [ ] `ui/editor/scenario_composer.py` — References + Installation 인라인 + Composition + Validation (v0.26 §13.3)
- [ ] `ui/editor/map_editor/` — Pan/Zoom + Land/Sea Brush + Spot Edit + **Flatten Area** + Add Building (v0.22, v0.26, v0.33)
- [ ] `ui/editor/map_editor/dem_import_wizard.py` — 7 step (v0.22 §11.5)
- [ ] `ui/editor/map_editor/domain_settings.py` — Simulation Domain + Outside Environment 패널 (v0.29)
- [ ] `ui/editor/radar_editor.py` — Antenna Type 드롭다운 + 동적 폼 + Beam Pattern Preview + RX 모드 (v0.25 §5.3.9)
- [ ] `ui/editor/targets_editor.py` — 메타 편집 + Trajectory Preview (편집은 CSV) (v0.26)
- [ ] `ui/editor/atmosphere_panel.py` — sky_condition + visibility + rain_rate 편집 (v0.28 §15.4.3)

#### Simulator Workspace 패널 (pyqtgraph)
- [ ] `ui/simulator/scenario_explorer.py`
- [ ] `ui/simulator/fft_panel.py` (pyqtgraph)
- [ ] `ui/simulator/range_doppler_panel.py` (pyqtgraph ImageView)
- [ ] `ui/simulator/run_panel.py` — Time Layers 블록, Target Run State 제어 (v0.14~v0.15)
- [ ] `ui/simulator/properties_panel.py` — EKF Command vs Positioner Actual 구분 (v0.10)
- [ ] `ui/simulator/plugin_manager_panel.py` — Workspace 경로 표시, New Plugin 마법사 (v0.10)
- [ ] `ui/simulator/stage_io_panel.py` — 각 스테이지 입출력 + CSV/HDF5 다운로드 (v0.14)

#### Simulator 3D Scene (PyVista — v0.28)
- [ ] `ui/simulator/scene_3d/qt_interactor.py` — PyVista QtInteractor 임베드
- [ ] `ui/simulator/scene_3d/dem_renderer.py` — DEM smooth shading mesh
- [ ] `ui/simulator/scene_3d/wave_renderer.py` — 해수면 sinusoidal 파도 셰이더
- [ ] `ui/simulator/scene_3d/atmosphere_visuals.py` — sky color, fog (v0.28 §15.4.1)
- [ ] `ui/simulator/scene_3d/target_actor.py`, `radar_actor.py`, `building_actor.py`
- [ ] **3rd-person + Scope POV** (v0.10), 휠 줌 + Unreal+Maya 조작 (v0.17)
- [ ] **F 키 포커스** — Lock 잃으면 직전 표적 위치 유지 (v0.17)

#### Installation 화면 (v0.18 — Scenario Composer 안에 통합)
- [ ] `ui/editor/scenario_composer/installation_panel.py` — DEM Map + 차폐 Preview + Coverage Stats

#### NN 모드 (v0.13 — Step 1/2)
- [ ] `ui/simulator/nn_mode_step1.py` — Dataset Builder
- [ ] `ui/simulator/nn_mode_step2.py` — Evaluation + 4-error 진단

#### Reference Timing + Frame Profiler UI (v0.39)
- [ ] `ui/simulator/profiler_panel/timing_breakdown.py` — Stage 별 timing 막대 chart
- [ ] `ui/simulator/profiler_panel/scale_indicator.py` — toolbar "0.57x" 시뮬 속도 표시
- [ ] `ui/simulator/profiler_panel/profile_report.py` — FrameTimingReport 표
- [ ] "Profile" 버튼 (Run controls 옆) — 100 frames 측정 → 결과 dialog
- [ ] "Set Reference Timing" 버튼 — Frame Profiler 결과 → Reference Timing target 입력 dialog

#### 입력
- [ ] **방향키 이벤트 핸들러**: AUTO/MANUAL 토글(`M`), 방향키 → CommandBus 또는 InputBuffer (v0.14~v0.15)
- [ ] **모드 전환 UI** (View > Mode): DSP ↔ NN (v0.13)
- [ ] **단축키 정책** (Ctrl+Shift+E/S Workspace 전환, Ctrl+1~5 Activity, F5 Run, etc.) (v0.19, v0.26)

완료 기준: 01 문서의 **MVP 완료 기준 시나리오** 전부 동작.

### Phase 5: 물리 검증 프레임워크 뼈대

목표: 테스팅 전략 섹션의 MVP 수준 구축. **사실적 동역학·대기 모델 검증 포함**.

- [ ] `tests/physics/` 구조
- [ ] Golden Dataset 포맷 정의 + 로더
- [ ] 기본 검증 카테고리 (확장):
  1. 레이더 방정식 (문헌 비교)
  2. FMCW IF 주파수 (보존/회귀)
  3. 포지셔너 동역학 (극한 상황)
  4. **Antenna 빔 패턴** — sinc² (parabolic) / array factor (planar) 검증 (v0.25)
  5. **Monopulse error 추정** — 합성 신호로 error_az/el 계산 정확성 (v0.25)
  6. **표적 동역학** — Aircraft autopilot trajectory 추적 정확성 (v0.27)
  7. **BALLISTIC 자유낙하** — 분석해와 비교 (v0.27)
  8. **ISA 대기 밀도** — 표준 표 일치 (v0.28)
  9. **Rain attenuation** — ITU-R P.838 표 비교 (v0.28)
  10. **sample_terrain_safe** — Map 안/밖 동작 일관성 (v0.29)
  11. **Coherence Validator** — 6종 검사 동작 (v0.21~v0.29)
  12. **Two-ray multipath lobing** — 표적 고도·거리에 따른 SNR 변화 (v0.34)
  13. **Glint emergence** — multi-scatterer 표적의 angle noise σ_glint 이론치 매칭 (v0.34)
  14. **EKF vs UKF 비교** — 고기동 시나리오 RMSE 비교 (v0.34)
  15. **GNN association 정확성** — 다중 표적 시나리오 (v0.34)
  16. **Effective Earth refraction** — horizon distance 표준 일치 (v0.34)
  17. **OS-CFAR vs CA-CFAR** — 클러터 환경 false alarm rate 비교 (v0.34)
  18. **Reference Timing 재현성** (v0.39) — 같은 시드 + 같은 input + 같은 frame 정의 → 같은 결과. wall_clock 변동·scale_factor 가 결과에 영향 X
  19. **Frame Profiler 결과 재현성** (v0.39) — 동일 PC 동일 부하에서 percentile 일관성, warmup 효과 검증
- [ ] `physics_validation_panel.py` — IDE에서 결과 표시
- [ ] CI 통합 (GitHub Actions 또는 로컬 스크립트)

완료 기준: 물리 코드를 수정했을 때 `pytest tests/physics/`가 **회귀를 자동 감지**.

### Phase 6: NN 통합 (MVP+α — Wave 1)

목표: 07 NN 통합 문서의 Wave 1 (Pairing NN 교체) 시나리오 동작.

- [ ] `domain/stage_slot.py` — Pipeline Stage Slot 시스템 (07 §7.2)
- [ ] `domain/nn_plugin.py` — `NNPluginMixin`, `Internal Probe`
- [ ] `app/data_exporter.py` — Sample 수집, SampleSpec 기반 H5 저장
- [ ] `app/dataset_builder.py` — 자동 Dataset 빌더, Variant 6종 (v0.30)
- [ ] `app/nn_evaluator.py` — 4-error 진단 (Bayes/Training/Dev/Test)
- [ ] `app/trainer_service.py` — 내부 간단 학습 (외부 CLI는 별도)
- [ ] `ui/simulator/nn_mode/dataset_builder_panel.py`
- [ ] `ui/simulator/nn_mode/training_panel.py`
- [ ] `ui/simulator/nn_mode/evaluation_panel.py` — 4-error 표시 + diagnosis_hint
- [ ] **Pairing NN 첫 구현 + 학습 + 비교** (07 §7.4.6 Wave 1 완료 기준)

완료 기준: 07 §7.7.0 Wave 1 시나리오 전부 동작.

### Phase 7: DLC 시스템 (MVP+α — Wave 2, v0.35)

목표: 17 open_platform.md 의 .trsim-pkg 시스템 동작.

#### SDK Layer
- [ ] `sdk/protocols.py` — 9개 Plugin Protocol (Tracker / Detector / Pairing / AngleEstimator / Predictor / Classifier / DataAssociator / Resource / UIPanel)
- [ ] `sdk/resource_schemas.py` — Map / Radar / Target jsonschema
- [ ] `sdk/package_builder.py` — `trsim sdk build` CLI
- [ ] `sdk/package_validator.py` — manifest.toml 검증
- [ ] `sdk/test_harness.py` — `trsim sdk test` CLI

#### App Layer
- [ ] `app/package_manager.py` — install / uninstall / load_all
- [ ] `app/panel_registry.py` — UI 패널 등록 (Built-in + DLC)
- [ ] `io/package_io.py` — .trsim-pkg pack/unpack

#### UI
- [ ] `ui/editor/package_manager_panel.py` — 설치된 DLC 목록·install·uninstall
- [ ] Editor 메뉴 "Install Package..." → file picker

#### Sample DLC
- [ ] **참조 구현** 1~2개 (예: Stone Soup adapter, IMM tracker)
- [ ] DLC 만드는 튜토리얼 (`docs/dev_guide/creating_dlc.md`)

#### 통합
- [ ] `ResourceLibrary`가 `~/.trsim/packages/` 자원 인덱스
- [ ] `PluginLoader`가 DLC plugins 로드
- [ ] `PanelRegistry`가 DLC UI 패널 등록

완료 기준:
```
$ trsim sdk build my_tracker/        # DLC 빌드
$ trsim install my_tracker.trsim-pkg  # install
$ python -m workbench                 # DLC 자동 로드
                                      # → Editor에 새 Tracker 옵션 보임
                                      # → 시뮬에서 사용 가능
```

---

### Phase 8: HIL 통합 (MVP+α — Wave 3, v0.38)

목표: 외부 DUT (펌웨어/FPGA/DSP) 를 시뮬 루프에 연결, GT/SIL/HIL 3-way 비교 가능.

상세: [18 hil_integration.md](18_hil_integration.md).

#### Phase 8.1 — MVP HIL (TCP/JSON + L5 Track)
- [ ] `domain/hil/dut_messages.py` — DUTTrack (L5) dataclass
- [ ] `domain/hil/tx_signal.py` — TXSignalDigital
- [ ] `domain/hil/comparison.py` — HILComparisonResult (GT/SIL/HIL 3-way)
- [ ] `sdk/protocols.py` 에 `DUTAdapter` Protocol 추가 (10번째) + sync 메서드 (v0.39 Lock-step)
- [ ] `plugins_builtin/tcp_json_dut_adapter.py` — 기본 sample
- [ ] `app/hil/hil_evaluator.py` — L5 비교
- [ ] `app/hil/time_synchronizer.py` — sim_time 모드
- [ ] `app/hil/dut_session_manager.py` — DUT 연결 관리
- [ ] `ui/simulator/hil_panel/comparison_view.py` — 3-way Track plot
- [ ] Mock DUT (Python 테스트용 sample)
- [ ] Scenario 측 `[hil]` 섹션 (sync_mode/dut_timeout_ms 등)
- [ ] HIL-A 검증 시나리오 (GT vs HIL Track)

#### Phase 8.1 — Lock-step Handshake (v0.39, Reference Timing HIL 측)
- [ ] DUTAdapter Protocol 의 `sync_frame_start(frame_id)` / `sync_frame_end(frame_id, timeout_ms)` 메서드
- [ ] frame ID 매칭 + timeout 처리
- [ ] PC ↔ DUT desync detection
- [ ] DUT 측 핸드쉐이크 구현 가이드 (펌웨어 sample, README)
- [ ] 검증: SIL Reference Timing 과 HIL Lock-step 의 결과 일치성

완료 기준: TCP 로 mock DUT 통신, GT/SIL/HIL 3-way 비교 가능. DUT-Bias metric 계산.

#### Phase 8.2 — 보강 (L2/L4)
- [ ] DUTSpectrum (L2), DUTPairedDetection (L4) dataclass
- [ ] hil_evaluator stage-by-stage 비교
- [ ] `ui/simulator/hil_panel/stage_compare.py`
- [ ] HIL-C/D 검증 시나리오 (Spectrum, Paired)

#### Phase 8.3 — 확장 (L1 + AWG + real_time)
- [ ] DUTRawIQ (L1) high-speed transport
- [ ] TXSignalAnalog (AWG analog)
- [ ] AWG vendor 어댑터 sample (Spectrum 또는 Keysight)
- [ ] real_time sync mode
- [ ] (옵션) C6678 PCIe 직접 어댑터 sample

---

### Phase 9: Physics Lab (MVP+α — Wave 4, v0.40)

> **출처**: 19 § 19.10~19.11 Physics Lab Phase 분산 (PL-15)
> **권위**: 19 physics_lab

#### Phase 9.1 — Physics Lab MVP (인터랙티브 환경 + 검증)

목표: 3-pane 인터랙티브 Workspace, 9 Test Objects, 4 시간 모드, 분석 공식 비교, 외부 데이터 검증, 17종 회귀 통합.

##### Application Layer (`app/physics_lab/`)
- [ ] `experiment_runner.py` — 4 시간 모드 (Static / Single Run / Compare / Sweep)
- [ ] `param_introspector.py` — `@physics_param` decorator + Annotated 자동 노출
- [ ] `validation_bench.py` — 분석 vs 구현 비교 + 17종 회귀 통합 (PL-12)
- [ ] `external_data_loader.py` — CSV / HDF5 / .npz 로더
- [ ] `parameter_fitter.py` — 형태 1: scipy.optimize.curve_fit 기반 파라미터 학습
- [ ] `physics_clock.py` — Physics Lab 격리 PhysicsClock (SimulationClock 의 격리 인스턴스)

##### UI Layer (`ui/physics_lab/`)
- [ ] `physics_lab_workspace.py` — 메인 Workspace (3-pane 레이아웃)
- [ ] `code_pane.py` — Read-only default + Edit toggle (PL-7)
  - [ ] Pygments syntax highlighting
  - [ ] 시간 진행 따라 current line highlight
- [ ] `visualization_pane.py` — 2D (pyqtgraph) / 3D (PyVista)
  - [ ] Test Object 시각화 (9 종)
  - [ ] Force vector 화살표
  - [ ] Trajectory line
  - [ ] Camera controls (3D)
- [ ] `parameters_pane.py` — 슬라이더 자동 생성 (decorator/type hint 기반)
  - [ ] Linear / Log scale (모델 metadata 기반, PL-14)
  - [ ] Min/Max 사용자 변경
  - [ ] Live update (입력 → 시뮬 재실행)
- [ ] `time_controls.py` — Play/Pause/Stop/Slider/Frame-by-frame
  - [ ] Speed control (0.5x / 1x / 2x)
  - [ ] Keyboard shortcuts (Space, ◀ ▶)
- [ ] `model_selector.py` — Force toggle (☑Grav ☐Drag etc.)
- [ ] `test_object_selector.py` — 9 Test Objects 선택 + 시각 미리보기
- [ ] `validation_panel.py` — Validation Bench 결과 + 17종 회귀
  - [ ] PASS/FAIL count
  - [ ] FAIL 시 드릴다운
- [ ] `data_overlay_panel.py` — 외부 측정 데이터 overlay + RMSE/일치도

##### WorkspaceManager 통합
- [ ] PhysicsLab Workspace 등록 (Editor / Simulator / **Physics Lab**)
- [ ] 단축키 (Ctrl+Shift+P 또는 Workspace 전환)

##### 17종 회귀 통합 (PL-12)
- [ ] `tests/physics/` 의 17종 시나리오를 `app/physics_lab/validation_bench.py` 가 호출 가능하게
- [ ] Phase 5 검증을 Physics Lab 안에서 GUI 로 실행
- [ ] CLI (`workbench-cli physics-lab validate`) 도 지원

##### 형태 1 + 5 (외부 데이터)
- [ ] CSV / HDF5 / .npz 업로드 UI (Library 탭)
- [ ] 형태 5: 시뮬 결과 vs 측정 overlay + RMSE
- [ ] 형태 1: 단일 모델 (RCS, ExtendedTarget 등) 의 파라미터 fit
- [ ] FittedParameters 결과 → Resource Library 저장 (Q-PL-I)

완료 기준: 사용자가 Physics Lab 열고 9 Test Objects 중 선택, force 활성, 파라미터 조정하면서 3D 애니메이션·검증 결과 실시간 확인. 외부 측정 데이터 업로드해서 시뮬과 비교 가능.

---

#### Phase 9.2 — 학습 보강 (Symbolic regression + 사용자 plugin 검증 흐름)

- [ ] PySR 통합 (Apache 2.0 호환, Q-PL7)
  - [ ] 의존성 추가 (pyproject.toml)
  - [ ] `app/physics_lab/symbolic_regression.py` — 측정 데이터 → 수식 발견
  - [ ] 발견 수식의 sympy 표현 + Python 코드 생성
- [ ] PhysicsModelProtocol plugin 검증 흐름 (PL-6)
  - [ ] Validation Bench 가 plugin 등록 후 17종 회귀 자동 실행
  - [ ] 분석 공식 비교 자동
  - [ ] PASS 한 plugin 만 시뮬에서 사용 가능
- [ ] Plugin → `.trsim-pkg` packaging 통합
- [ ] 논문 PDF 라이브러리 (참조용, PL-10)
  - [ ] PDF 업로드·관리 UI
  - [ ] 메타 정보 (저자·인용·모델 설명) 수동 입력
  - [ ] 각 물리 모델에 "출처 논문" metadata 연결
  - [ ] **자동 코드 생성 X** (명시적 제외)

완료 기준: 사용자가 측정 데이터로 새 수식 발견 가능. PhysicsModelProtocol plugin 작성·검증·packaging 가능.

---

#### Phase 9.3 — 고급 학습 (NN 대체 + Phase 6 NN 결합)

- [ ] 형태 2: NN 으로 물리 함수 대체 (Phase 6 NN 통합 인프라 활용)
  - [ ] 물리 함수의 NN wrapper Protocol 정의
  - [ ] 학습·평가 loop (Phase 6 의 trainer 활용)
  - [ ] 학습 영역 vs 외삽 영역 시각화 (Q-PL8)
    - [ ] 색·투명도로 "안전 영역" / "위험 영역" 표시
    - [ ] 외삽 시 경고 표시
- [ ] NN 결과 dataclass + 저장
- [ ] NN 모델 → `.trsim-pkg` plugin packaging
- [ ] 메인 시뮬 연동 옵션 (Q-PL-K)
  - [ ] 격리 default (Physics Lab 만)
  - [ ] 옵션: 메인 시뮬 진행 중 Physics Lab 에서 그 모델 실시간 검증

완료 기준: 사용자가 측정 데이터로 NN 학습한 물리 모델을 시뮬에 안전하게 사용 가능 (외삽 영역 명확). 메인 시뮬과 옵션 연동.

---

### Phase 순서에 대한 원칙

- **Phase 2 완료 전엔 UI 손대지 않음.** 이게 God Class 재발 방지의 핵심.
- **각 Phase는 "돌아가는 상태"로 끝남.** 중간에 멈춰도 쓸 수 있어야 함.
- **Phase 3에서 CLI를 먼저 만들어보는 것**이 강력히 권장. UI 없어도 기능 완결 — 이게 의존 방향 규칙 자동 강제.
- **Phase 6 (NN)은 MVP+α** — Phase 5 안정 후 진입. Pipeline Stage Slot은 Phase 2부터 인지하지만 NN Plugin 자체는 미루자.
- **사실적 도메인 모델 (v0.21~v0.29)은 Phase 2에 모두 포함** — 코드 안정성 위해 한 Phase에서 끝내는 게 안전.
- **Phase 7 (DLC)은 MVP+α** — Phase 5/6 안정 후. SDK Protocol은 Phase 2에서 정의되지만 Package Manager는 Phase 7. **Phase 0에서 오픈소스 인프라(LICENSE/CONTRIBUTING/GOVERNANCE)는 처음부터 갖춤**.
- **Phase 8 (HIL)은 MVP+α (Wave 3)** — Phase 7과 독립이라 병렬 가능. SignalSink + DUTAdapter Protocol은 Phase 2부터 정의 가능, HILEvaluator + UI는 Phase 8.
- **Phase 9 (Physics Lab)은 MVP+α (Wave 4, v0.40)** — Physics Layer 통합 자체는 Phase 2 (코드 정리·이동), 인터랙티브 UI 와 학습 기능은 Phase 9. PhysicsModelProtocol (11번째 SDK) 은 Phase 2 정의. 17종 회귀가 Physics Lab 안으로 통합 (Phase 5 검증 → Phase 9.1 의 Validation Bench).

---

## 4.4 자주 발생할 함정 (선제 경고)

> 이 함정 목록은 Python/Qt/numpy 기반 시뮬레이터 개발 일반에서 흔한 실수 패턴.
> 신규 구현 시 미리 인식하면 회피 가능.

### 함정 1: View ↔ Presenter 순환 의존

GUI 프레임워크에서 흔한 안티패턴: View가 Presenter를 보유하고, Presenter가 View를 직접 참조 (`self._win.xxx`).

→ **단방향 데이터 플로우**. View 는 EventBus 구독만, Command Bus 로 의도 전달.
   Presenter 개념 폐기, App Layer 가 직접 EventBus·CommandBus 로 통신.

### 함정 2: "필요할 것 같아서" 미리 구현

성능 최적화 (`lod_cache`, `chunk_lod` 등) 를 Domain·App 에 끌어올리는 유혹.
이것들은 **3D 뷰 패널 내부 문제**로 캡슐화하고, Domain/App은 몰라도 됨.

→ 각 Phase의 "최소 통과 조건"에 없는 기능은 **나중에**.

### 함정 3: `pandas`가 Domain을 오염시킴

CSV 로드 시 `pandas.read_csv` 결과가 Domain 까지 흘러감.
DataFrame이 Domain 타입에 섞이면 JSON 직렬화·재현성·Plugin 격리 모두 곤란해짐.

→ `io/` 레이어에서 **pandas 바운더리 종결**. Domain은 numpy + dataclass만.

### 함정 4: PySide6/PyQt5 이중 import

흔한 호환성 패턴:
```python
try:
    from PySide6 import QtWidgets
except ImportError:
    from PyQt5 import QtWidgets
```

→ **PyQt5 fallback 금지**. PyQt5가 한 번이라도 import되면 전체 GPL 오염
(우리는 Apache 2.0 + LGPL 호환만 허용). `PySide6` 단일 지원.

### 함정 5: 절대 경로/하드코딩

`DEFAULT_TERRAIN`, `DEFAULT_BUILDINGS` 같은 상수가 파일 경로로 박힘.

→ 경로는 **Scenario의 필드**로. 기본값은 데이터 파일 자체에 메타로.

### 함정 6: argparse 인자 UI로 튀어나옴

CLI 인자 (`--sea-state`, `--terrain-stride` 등) 를 UI에 똑같이 버튼/슬라이더로 달고 싶은 유혹.

→ **UI 워크플로를 기준으로 재정의**. 일부는 Scenario 필드로, 일부는 Preferences로, 일부는 임시 표시 옵션으로.

---

## 4.5 시나리오 형식

MVP 시나리오는 v0.20 자원 참조 모델 기준 신규 작성. 시나리오 디렉토리 구조:

```
scenarios/
└── A_Base/                      ← 시나리오 이름
    ├── scenario.toml            ← 메타·refs·composition (v0.20)
    ├── trajectory.csv           ← 표적 trajectory (reference, v0.27)
    └── gt_targets.csv           ← Ground Truth (Plugin이 못 봄, v0.13)
```

### scenario.toml 예시

```toml
# scenarios/A_Base/scenario.toml
[scenario]
name = "A_Base"
description = "Evasion — 12km 에서 좌회전"
version = "1.0"

[scenario.origin]
lat_deg = ...
lon_deg = ...
alt_m = 0

[refs]
# v0.20 자원 참조 — ResourceLibrary 가 해석
map = "maps/east_coast_50km"
radar = "radars/standard_xband"
targets = "targets/aircraft_evasion"

[composition]
# Map 위에 Radar·Target 어디에 배치하는가
radar_anchor = "buildings/radar_host_01"
radar_mount_height_m = 4.0

[scenario.environment]
sea_state = 3
atmosphere = "atmospheres/clear_day"   # v0.28

[scenario.targets]
trajectory_file = "trajectory.csv"
ground_truth_file = "gt_targets.csv"
primary_target_id = 0
```

### MVP 시나리오 7종 (제안)

| 이름 | 의도 | 검증 차원 |
|---|---|---|
| `A_Base` | 단일 표적 evasion (좌회전 12km) | Track 안정성 |
| `B_Conflict` | 두 표적 교차 항로 | ID switch, GNN |
| `C_Limit` | 거리 한계 추적 | SNR, multipath null |
| `D_Static` | 정지 표적 + 클러터 | OS-CFAR |
| `E_Decoy` | 디코이 (false target) | Pairing 강건성 |
| `F_Stealth` | 저 RCS + 저고도 | 탐지 한계 |
| `G_Maritime` | 해상 multi-scatterer ship + glint | v0.34 차별점 |

각 시나리오는 분석 공식 (예측되는 거동) 으로 검증.

---

## 4.6 체크리스트: 모듈 구현 시 점검 항목

각 모듈을 구현·머지할 때 확인:

- [ ] Import 방향이 계층 규칙을 지키는가? (Primitives ← Domain ← SDK ← App ← UI)
- [ ] Qt 의존이 Domain/Primitives에 없는가?
- [ ] `pandas` 의존이 Domain 밖(io 경계)에만 있는가?
- [ ] 최소 하나의 단위 테스트 + 분석 공식 검증이 있는가?
- [ ] `@dataclass(frozen=True)` 적용 가능한 곳에 적용했는가?
- [ ] 하드코딩 경로를 Scenario/Config로 뺐는가?
- [ ] 300줄을 넘는 클래스/함수가 있는가? (있으면 분할)
- [ ] docstring 에 단위 (m/s, deg, dB 등) 명시됐는가?
- [ ] `lint-imports` 통과하는가?

---

## 섹션 상태

- 4.1 원칙 — ✅ (v0.36 신규 구현 전제로 재작성)
- 4.2 모듈 지도 — ✅ (계층별 신규 모듈 정리)
- 4.3 Phase 순서 — ✅ (Phase 0~7, v0.34/v0.35 모듈 모두 반영)
- 4.4 함정 — ✅ (일반화)
- 4.5 시나리오 형식 — ✅ (7~8 MVP 시나리오 제안)
- 4.6 체크리스트 — ✅

---

👉 다음 섹션: [05_ui_ux.md](05_ui_ux.md)
