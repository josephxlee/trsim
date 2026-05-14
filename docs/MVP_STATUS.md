# TRsim — MVP 전체 작업 매트릭스

**plan/04 § 4.3 의 Phase 0~9 list 와 실제 구현 상태의 cross-check
매트릭스**. 새 sub-step 시작 / 끝낼 때 이 파일이 권위. 매 sub-step
push 후 해당 행 ✓ 갱신 (`CLAUDE.md` § 3.6 자동 업데이트 규약).

| 상태 | 의미 |
|---|---|
| ✓ | 완료 |
| △ | 부분 완료 (skeleton / placeholder 만, 실 데이터 binding 또는 CLI 미구현) |
| ✗ | 미구현 |

**최종 갱신**: 2026-05-13 — Phase 4 L1 (Simulator Run panel 실 sim_time) 완료 후.
**누적 test**: 2518 PASS local, 5 contracts KEPT.
**HEAD**: L1 Simulator Run panel 의 첫 실 데이터 binding — sim_t_s / frame_id / state / speed live readout.

이전 historical gap 보고 (2026-05-12 시점, 사용자가 MVP_GUIDE 따라
검증한 결과) 는 [`docs/sessions/mvp_status_gap_report_2026_05_12.md`]
(sessions/mvp_status_gap_report_2026_05_12.md) 에 archive.

---

## 한 줄 요약

**MVP frame (Phase 0~5) ✓** — Phase 3 의 Profile 모드 toggle (△) +
Phase 4 의 실 데이터 binding (△ 골격만) 만 secondary 미완.
**MVP+α 4 wave**: Wave 1 (NN) frame ✓ + Adam/CLI ✓ (Step 2 일부 △),
Wave 2 (DLC) runtime ✓ + CLI ✓ + Plugins menu wiring ✓,
**Wave 3 (HIL) 전체 ✗**, Wave 4 (Physics Lab) ✓ + 후속 polish (Library
Models 동적 + PluginLoader discovery + MainWindow auto-register) ✓.

---

## Phase 0 — 레포 뼈대 + OSS 인프라 ✓

| 영역 | 상태 |
|---|---|
| pyproject.toml + .importlinter + 디렉토리 구조 | ✓ |
| `python -m workbench` 빈 창 + pytest "hello world" | ✓ |
| lint-imports 5 contracts KEPT | ✓ |
| LICENSE / NOTICE / README / CONTRIBUTING / CODE_OF_CONDUCT / GOVERNANCE / SECURITY | ✓ |
| .github/PULL_REQUEST_TEMPLATE.md + 3 ISSUE templates + ci.yml | ✓ |

---

## Phase 1 — Primitives ✓

| 영역 | 상태 |
|---|---|
| physics/fmcw / ray_tracing / reflection / geometry | ✓ |
| domain/geo / terrain / building / positioner_spec / antenna_spec | ✓ |
| 최소 스모크 테스트 | ✓ |

---

## Phase 2 — Domain ✓

| 영역 | 상태 |
|---|---|
| contracts.py 6 Protocol + PositionerCommand / CommandSource / types | ✓ |
| pipeline.py + environment.py + plugins_builtin/default_* | ✓ |
| Map + 좌표계 (geo / map_resource / coastline / terrain_sampling / simulation_domain) | ✓ |
| Placement + Motion (placement / wave_response / building / target) | ✓ |
| Dynamics 6 모듈 (state / params / forces / solver / motion_models / impact) | ✓ |
| Atmosphere (ISA + rain + refraction) | ✓ |
| Propagation/multipath (two-ray sea bounce) | ✓ |
| Antenna (Parabolic / PlanarArray / RXChannelSpec / MonopulseRXConfig) | ✓ |
| Monopulse (extended target 합성) | ✓ |
| Extended Target (Scatterer / ExtendedTarget / glint) | ✓ |
| Tracker (EKF / UKF / GNN Hungarian) + TrackerKind | ✓ |
| Detection (CACFAR + OSCFAR) | ✓ |
| Platform + Scenario + io/scenario_loader | ✓ |
| Reference Timing 데이터 모델 (domain/timing/reference_timing.py) | ✓ |
| Physics Layer 통합 (PL-1/PL-2 — physics/ 분리, 11번째 PhysicsModelProtocol) | ✓ |
| 17종 회귀 + Phase 5 후속 보강 | ✓ |

---

## Phase 3 — Application △

| 모듈 | 상태 |
|---|---|
| command_bus / command_registry / commands (5 카테고리: sim/target/positioner/editor/workspace) | ✓ |
| event_bus / plugin_loader / plugin_scanner (AST GT Isolation) | ✓ |
| workspace_manager / resource_library / resource_cache / scenario_service | ✓ |
| simulation_clock (두 레이어 Layer 1) | ✓ |
| input_buffer / probe_recorder / run_manager | ✓ |
| bundle_service (.scnbundle / .runbundle export·import + tar-slip defence + manifest probe) | ✓ (D1) |
| command_evaluator (Command Lineage Level 3-2: monotonic_sim_time / tracker_source_provenance / initial_scan_single_dispatch) | ✓ (D3) |
| physics_gate (velocity<c / mass>0 / altitude / radar freq / finite position checks + PhysicsGateReport) | ✓ (D2) |
| io/run_storage / trace_storage | ✓ |
| io/dem_import (ESRI ASCII grid → terrain.npz, NODATA→NaN, north-up flip, land_mask default) | ✓ (D4) |
| CLI: `trsim run` / `trsim profile` / `trsim ui` | ✓ |
| Reference Timing v0.39 (performance_clock / frame_boundary / stage_probe / frame_profiler) | ✓ |
| Profile 모드 toggle (off / explicit / live, Q4) | ✓ (Phase 9 sidequest #6 — `domain/timing/profile_mode.py` ProfileMode StrEnum + `trsim run --profile-mode` CLI flag + manifest metadata 기록. Pipeline / probe runtime gating 은 Pipeline.step 본격 wire 시 후속) |
| Warmup discard | ✓ |

---

## Phase 4 — UI △ (골격 ✓, 실 데이터 binding ✗)

| 영역 | 상태 |
|---|---|
| pyqtgraph + pyvista + pyvistaqt 의존성 | ✓ |
| Main Window / Workspace selector / Dock manager / Command palette / Toolbar / Menu | ✓ |
| Editor Activity Selector (5 Activity 좌측 아이콘) + Resource Browser sidebar | ✓ |
| Scenario Composer widget skeleton | △ (widget.py + ResourceLibrary-driven 드롭다운 ✓ + Validate button → `ScenarioComposerController` (combo shape check 진짜 동작, OK/WARN/ERROR status 갱신) ✓; 도메인 coherence_validator 통합 + save/load round-trip ✗ — 후속 cycle) |
| **Scenario Composer Installation Panel** (DEM + 차폐 Preview + Coverage Stats) | △ (G4, Position 5 row + DEM preview placeholder + Coverage Stats 3-readout + Domain Override block + `CoverageStats` dataclass + `set_terrain_altitude` / `set_coverage_stats` API; 실 Map/Radar/Validator binding ✗) |
| Map Editor widget skeleton (Pan/Zoom + Land/Sea Brush + Spot Edit + Flatten + AddBuilding) | △ |
| **Map Editor DEM Import Wizard** (7 step, v0.22) | ✓ (E1-E4, MVP 4-page distillation: Source/Land-Sea/Output/Summary) |
| **Map Editor Domain Settings panel** (Simulation Domain + Outside Environment, v0.29) | ✓ (G1-G3, dataclass + `DomainSettingsPanel` widget + Map Editor QTabWidget mount as "Domain" tab; live data binding via `set_map_bounds` is later cycle) |
| Radar Editor widget skeleton (AntennaType 드롭다운 + 동적 폼 + Beam Pattern Preview) | △ (widget ✓ + `RadarEditorController` (parabolic/planar live computed-values: Az BW / El BW / Peak gain via `physics.antenna` helpers, 매 field edit 갱신) ✓; Save/Validate + 실 ScenarioService 연동 미) |
| Targets Editor widget skeleton (메타 + Trajectory Preview) | △ (widget + Validate button → `TargetsEditorController` (name/motion/RCS/scatterers shape check, OK/WARN/ERROR status) ✓; trajectory CSV / preview / save 미) |
| Atmosphere Panel widget skeleton (sky / visibility / rain_rate 등) | △ |
| Simulator panels (FFT / RD / Run / Properties / PluginMgr / StageIO) | △ (Run ✓ L1; PluginManager ✓ L2 baseline; FFT/RD/StageIO frame_label ✓ L3 fan-out; Properties ✓ L4 snapshot + selection pin; StageIO 6 box IN/OUT ✓ L5 deterministic placeholder text. FFT spectrum / RD heatmap data binding은 실 pipeline 후 후속.) |
| Scene 3D PyVista (DEM / wave / atmosphere / actors / 3rd-person + Scope POV / F-key focus) | △ (Phase 4.10 lazy create) |
| Profiler panel (timing breakdown / scale indicator / report) | ✓ |
| NN mode panels (Step 1 Dataset / Step 2 Eval / Training) | ✓ |
| 방향키 이벤트 / Mode 전환 UI (DSP ↔ NN) / 단축키 정책 | △ |

---

## Phase 5 — 물리 검증 ✓

17 카테고리 + 이 세션 12 sub-step 후속 보강 끝.
plan/04 § 4.3 Phase 5 list 의 #18 (Reference Timing 재현성) +
#19 (Frame Profiler 결과 재현성): ✓ 정량 reproducibility tests
(`tests/unit/app/timing/test_reference_timing_reproducibility.py` —
PerformanceClock factory 결정성 / FrameProfiler 동일 sample sequence
→ 동일 StageReport / 순서 독립성 / reset replay invariant / 손계산
percentile golden).

---

## Phase 6 — NN MVP (Wave 1) △

| 항목 | 상태 |
|---|---|
| domain/stage_slot + nn_plugin (NNPluginMixin runtime_checkable Protocol) | ✓ |
| app/nn/data_exporter (HDF5 round-trip) | ✓ |
| app/nn/dataset_builder (streaming + cancel + finalize) | ✓ |
| app/nn/evaluator (4-error 진단 + diagnosis_hint) | ✓ |
| app/nn/trainer (TrainerService, backend ∈ {fake, numpy_mlp}) | ✓ |
| app/nn/pipeline_runner (Stage probe wire) | ✓ |
| app/nn/variant_runner (4-tier preset) | ✓ |
| app/nn/pairing_nn (NumpyPairingNN — Pairing NN 첫 구현) | ✓ |
| nn_mode panels: Step 1 Dataset Builder + Step 2 Eval + Training | ✓ |
| Adam optimizer (numpy 구현, backend="numpy_mlp_adam") | ✓ (A1-a) |
| workbench-train CLI (`trsim train --job <toml>`, in-process subprocess-ready) | ✓ (A1-b) |
| Step 2 Tracker / Predictor / Classifier 행 dispatch framework (stub functions → `n/a` rendering) | △ (A1-c, real loss functions TBD when Tracker/Predictor/Classifier NN plugins ship) |
| Step 2 multi-step rollout RMSE metric (stub `multi_step_rollout_rmse` with input validation) | △ (A1-d, sequence dataset spec + Predictor NN plugin TBD) |

---

## Phase 7 — DLC (Wave 2, v0.35) △

| 영역 | 상태 |
|---|---|
| SDK: protocols.py (11 Plugin Protocol) | ✓ |
| **SDK: manifest.py** | ✓ (sdk/manifest.py 로 이동 — Phase 9 sidequest #9, plan/02 § 2.6b: SDK 가 DLC author 의 단일 surface) |
| SDK: resource_schemas.py (`validate_resource_toml_blob`, 4 categories) | ✓ (C8) |
| SDK: package_builder.py + `trsim sdk build` CLI | ✓ (C2) |
| SDK: test_harness.py + `trsim sdk test` CLI | ✓ (C3) |
| SDK: package_validator.py (`validate_entry_point_slots` + curated KNOWN_ENTRY_POINT_SLOTS) | ✓ (C8) |
| `trsim uninstall` CLI (`--package-id` + path-escape defence) | ✓ (C7) |
| App: dlc/package_manager + dlc/plugin_loader + panel_registry + dlc_runtime | ✓ |
| App: resources/library (User > Package > Built-in priority) | ✓ |
| io/package_io.py (.trsim-pkg pack/unpack + zip-slip defence + manifest probe) | ✓ (C1) |
| `trsim install` CLI (`~/.trsim/packages/<id>/` + --force overwrite) | ✓ (C4) |
| ui/editor/package_manager_panel.py (Install/Uninstall/Refresh signals, no I/O coupling) | ✓ (C5) |
| Editor 메뉴 "Install Package..." + file picker | ✓ (F3, Plugins menu: Manage Plugins... opens PackageManagerDialog + Install Package... runs direct file picker) |
| ResourceLibrary / PluginLoader / PanelRegistry runtime 통합 | ✓ |
| Sample DLC 참조 구현 (`examples/dlc/simple_pairing_demo/` — manifest + maps resource + demo UI panel + end-to-end round-trip test) | ✓ (C6) |
| DLC 만드는 튜토리얼 ([`docs/dev_guide/creating_dlc.md`](dev_guide/creating_dlc.md)) | ✓ (C6) |

---

## Phase 8 — HIL (Wave 3, v0.38) **전체 ✗** (단 SDK Protocol stub 만 △)

`app/hil/` + `domain/hil/` + `ui/simulator/hil_panel/` 모두 `__init__.py`
만 (빈 디렉토리). `sdk/protocols.py` 에 `DUTAdapterProtocol` declaration
shell 만 (members 없음).

| 8.1 MVP HIL (TCP/JSON + L5 Track) | 상태 |
|---|---|
| domain/hil/dut_messages.py (DUTTrack L5 dataclass) | ✗ |
| domain/hil/tx_signal.py (TXSignalDigital) | ✗ |
| domain/hil/comparison.py (HILComparisonResult 3-way) | ✗ |
| sdk/protocols.py 에 DUTAdapter Protocol (10번째, v0.39 lock-step) | △ (class declaration + docstring 만 — `@runtime_checkable Protocol` shell, plan/18 § 18.7 의 메소드 시그니처 미선언) |
| plugins_builtin/tcp_json_dut_adapter.py | ✗ |
| app/hil/hil_evaluator.py (L5 비교) | ✗ |
| app/hil/time_synchronizer.py (sim_time 모드) | ✗ |
| app/hil/dut_session_manager.py | ✗ |
| ui/simulator/hil_panel/comparison_view.py (3-way Track plot) | ✗ |
| Mock DUT (Python sample) | ✗ |
| Scenario `[hil]` 섹션 (sync_mode / dut_timeout_ms) | ✗ |
| HIL-A 검증 시나리오 | ✗ |
| 8.1 Lock-step Handshake (v0.39) | ✗ |
| 8.2 L2/L4 보강 (DUTSpectrum / DUTPairedDetection / stage_compare UI) | ✗ |
| 8.3 L1 + AWG + real_time (DUTRawIQ / TXSignalAnalog / AWG 어댑터) | ✗ |

---

## Phase 9 — Physics Lab (Wave 4, v0.40) ✓

| 영역 | 상태 |
|---|---|
| 9.1 MVP — 3-pane Workspace + 9 Test Objects + 4 time mode + Code Pane + Parameters | ✓ |
| 9.2 — Measured Data + Papers Library + Validation Bench + Parameter Studio (scipy fit) | ✓ |
| 9.3 — Code autocomplete + PhysicsModelProtocol (11번째 SDK) + NN-as-physics + Polynomial fit + Test Object plugin registry | ✓ |
| **plan/19 § 19.7.5+ 확장** (Validation Bench 일반화 / Library Models 동적 채우기 / Plugin discovery via PluginLoader) | ✓ (H1-H2 + I1-I2 + J1 + M1 layer + M2 BouncingBallController refactor + **M3 임의 PhysicsModelProtocol UI dispatch** — LibraryWidget `physics_model_selected` signal 을 PhysicsLabWorkspace 가 받아 measured-row 클릭 시 모델 종류별 분기: BouncingBall = 기존 controller path, 그 외 = `run_validation_for_model` + `default_validation_fields` 룩업 + `install_validation_overlay`. 9 신규 tests.) |

---

## 미구현 우선순위 리스트 (큰 덩어리 → 작은 덩어리)

다음 작업 결정 시 이 매트릭스 참조. 사용자 우선순위 (변동 없음):
**physics_lab > simulator > editor**.

**사용자 결정 (2026-05-13, L1 직후)**: Phase 8 HIL 은 **MVP 공간만 두고
실 작업 하지 않음**. `domain/hil/` + `app/hil/` + `ui/simulator/hil_panel/`
빈 디렉토리 + `sdk/DUTAdapterProtocol` declaration shell (△) 유지.
아래 우선순위에서 제외.

| 우선 | 작업 | 크기 | 영역 | 비고 |
|---|---|---|---|---|
| ~~1~~ | ~~Phase 9 § 19.7.5+ Validation Bench 일반화~~ | — | physics_lab | **이 cycle M1+M2+M3 으로 종결**. (M3 = 임의 PhysicsModelProtocol UI dispatch.) 후속 polish (auto-parameters 슬라이더가 선택된 model 의 PhysicsParam 으로 swap / plot axis labels per-model / column selector UI) 만 남음 — 향후 cycle 자율. |
| 2 | **Simulator 8 panel 실 데이터 binding 잔여 5개** (FFT / RD / Properties / PluginMgr / StageIO) | 대 (여러 cycle) | simulator | L1 으로 Run panel 만 ✓. 직전 cycle 사용자 "Simulation 가장 시급" 명시. 여러 sub-step 분할. |
| 3 | **Phase 6 Step 2 per-category real dispatch** (Tracker / Predictor / Classifier loss) | 중 | simulator/NN | A1-c stub 만 있음. Tracker / Predictor / Classifier NN plug-in 출시 후. |
| 4 | **Phase 6 multi-step rollout RMSE real** | 중 | simulator/NN | A1-d stub. Sequence dataset spec + Predictor NN plug-in 후. |
| 5 | **Editor 5 activity 실 데이터 binding** (Composer / Map / Radar / Targets / Atmosphere wiring) | 대 (여러 cycle) | editor | 골격 ✓, G3-G4 의 `set_map_bounds` / `set_terrain_altitude` / `set_coverage_stats` API 가 준비 — wiring 만 남음. |
| ~~6~~ | ~~Phase 3 Profile 모드 toggle~~ | — | app | **이 세션 처리됨** — ProfileMode enum + CLI flag + manifest metadata. Runtime gating 은 후속. |
| ~~7~~ | ~~Phase 5 #18/#19 재현성 정량 검증~~ | — | physics | **이 세션 처리됨** — `tests/unit/app/timing/test_reference_timing_reproducibility.py` (9 tests). |
| 8 | **Phase 4 UI 잡** (방향키 이벤트 / Mode 전환 UI / 단축키 정책) | 소 | UI | △ — workspace 안 키 routing 정리. |
| ~~9~~ | ~~SDK manifest.py 이동~~ | — | refactor | **이 세션 처리됨** — sdk/manifest.py + sdk/__init__.py re-export + 6 callers + 2 tests + 1 integration test 갱신. domain/dlc/ 디렉토리 삭제. |
| 10 | **Polish**: Floating dock 옵션 B / Theme manager / Stone Soup adapter | 소 | optional | 미루기 가능. |
| — | ~~Phase 8 HIL 전체~~ | — | — | **사용자 결정 (2026-05-13): MVP 공간만, 실 작업 ✗**. Phase 8 행 (전체 ✗) 유지. |

---

## 갱신 규약

매 sub-step push 후 이 파일의 해당 행 ✓ 또는 △ 갱신. 같은 commit
에 묶거나 직후 commit. 자세한 절차는
[`docs/agent_workflows/mvp_status_update.md`](agent_workflows/mvp_status_update.md).

## 진입점

사용자가 "다음 작업?" / "남은 작업?" / "MVP 상태?" 등을 묻거나 새
세션 시작 시 이 파일 § "미구현 우선순위 리스트" 가 첫 참조.

## 변경 이력 footer

- 2026-05-13 초기 작성 (Phase 5 후속 12 sub-step 마감 시점, 2065 PASS).
- 2026-05-13 A1-a — Phase 6 Adam optimizer ✗ → ✓ (2065 → 2078 PASS).
- 2026-05-13 A1-b — Phase 6 workbench-train CLI ✗ → ✓ (2078 → 2093 PASS).
- 2026-05-13 A1-c — Phase 6 Step 2 per-category dispatch ✗ → △ (2093 → 2099 PASS).
- 2026-05-13 A1-d — Phase 6 multi-step rollout RMSE stub ✗ → △ (2099 → 2101 PASS).
- 2026-05-13 5.7b — Phase 5 Planar array sign/quadrant/boundary invariants △ (2101 → 2112 PASS).
- 2026-05-13 5.8b — Phase 5 Ballistic drag/mass/v0/theta scaling invariants △ (2112 → 2117 PASS).
- 2026-05-13 5.11b + 5.12b — Phase 5 timing (PerformanceClock factory + FrameBoundaryDetector monotonicity) △ (2117 → 2131 PASS).
- 2026-05-13 C1 — Phase 7 io/package_io ✗ → ✓ (2131 → 2146 PASS).
- 2026-05-13 C2 + C3 + C4 — Phase 7 sdk build / sdk test / install CLI ✗ → ✓ (2146 → 2163 PASS).
- 2026-05-13 C5 + C6 — Phase 7 PackageManagerPanel + Sample DLC + tutorial ✗ → ✓ (2163 → 2182 PASS).
- 2026-05-13 C7 + C8 — Phase 7 uninstall CLI + resource_schemas + package_validator ✗ → ✓ (2182 → 2198 PASS).
- 2026-05-13 D1 — Phase 3 bundle_service ✗ → ✓ (2198 → 2214 PASS).
- 2026-05-13 D2 — Phase 3 physics_gate ✗ → ✓ (2214 → 2251 PASS).
- 2026-05-13 D3 — Phase 3 command_evaluator ✗ → ✓ (2251 → 2266 PASS).
- 2026-05-13 D4 — Phase 3 io/dem_import ✗ → ✓ (2266 → 2280 PASS).
- 2026-05-13 E1 — Phase 4 LandSeaMode + compute_land_mask (2280 → 2288 PASS).
- 2026-05-13 E2 — Phase 4 DEMImportRequest + run_dem_import orchestrator (2288 → 2295 PASS).
- 2026-05-13 E3 — Phase 4 DEMImportWizard QDialog ✗ → ✓ (2295 → 2316 PASS).
- 2026-05-13 E4 — Phase 4 DEMImportController + MainWindow wiring (2316 → 2326 PASS).
- 2026-05-13 F1 — Phase 7 app/dlc/installer service extraction (2326 → 2337 PASS).
- 2026-05-13 F2 — Phase 7 PackageManagerDialog + Controller (2337 → 2354 PASS).
- 2026-05-13 F3 — Phase 7 MainWindow Plugins menu wiring (Manage + Install Package) ✗ → ✓ (2354 → 2360 PASS).
- 2026-05-13 G1 — Phase 4 cycle: `SimulationDomain` + `OutsideEnvironment` dataclass (Domain layer prep for Domain Settings panel) (2360 → 2384 PASS).
- 2026-05-13 G2 — Phase 4 cycle: `DomainSettingsPanel` widget (I/O-free, validates via SimulationDomain.__post_init__) (2384 → 2402 PASS).
- 2026-05-13 G3 — Phase 4 cycle: Map Editor right-panel → QTabWidget (Layers + Domain), DomainSettingsPanel 통합 ✓ (2402 → 2413 PASS). Map Editor Domain Settings panel ✗ → ✓.
- 2026-05-13 G4 — Phase 4 cycle: ScenarioComposer Installation block 본격 layout (Position 5 row + DEM preview + Coverage Stats) + Domain Override block (2413 → 2434 PASS). Scenario Composer Installation Panel ✗ → △.
- 2026-05-13 H1 — Phase 9 cycle: LibraryWidget `set_physics_models` + Models 카테고리 동적 (2434 → 2446 PASS).
- 2026-05-13 H2 — Phase 9 cycle: `app/physics_lab/model_registry.py` + PhysicsLabWorkspace `physics_models` kwarg (default = 3 built-in) (2446 → 2468 PASS). Phase 9 § 19.7.5+ Library Models 동적 채우기 ✗ → ✓.
- 2026-05-13 I1 — Phase 9 cycle: PluginLoader `_PYTHON_IMPORT_EXACT_SLOTS` 신설, `trsim.physics_model` 등 9 singleton 슬롯 지원 (2468 → 2472 PASS).
- 2026-05-13 I2 — Phase 9 cycle: `app/physics_lab/discovery.py` (LoadedPlugin → PhysicsModelProtocol → registry, bridge) (2472 → 2486 PASS). Phase 9 § 19.7.5+ Plugin discovery via PluginLoader ✗ → ✓.
- 2026-05-13 J1 — Phase 9 cycle: MainWindow auto-register `trsim.physics_model` plug-ins → PhysicsLabWorkspace Library 표시 (2486 → 2490 PASS). H+I 결과 사용자 GUI visible.
- 2026-05-13 cross-check retro-update — Phase 7 `SDK: package_validator.py | ✗` 행 (row 159 의 ✓ row 와 duplicate, 모순) 제거. § 한 줄 요약 갱신 (Wave 2 CLI ✗ → ✓). § 미구현 우선순위 리스트 9 → 10 행 재작성 (직전 1/2/3/5/6 다 완료 반영). Phase 9 § 19.7.5+ 행에 J1 추가. Phase 8 row 4 (DUTAdapter Protocol) ✗ → △ (declaration shell 만, members ✗).
- 2026-05-13 L1 — Phase 4 cycle: Simulator Run panel 실 sim_time/frame_id binding + `SimulatorRunController` (16ms QTimer + SimulationClock) + MainWindow sim.start/pause/stop/speed hooks (2490 → 2518 PASS). Simulator Run panel 실 데이터 binding ✗ → ✓.
- 2026-05-13 user decision — Phase 8 HIL "MVP 공간만, 실 작업 하지 않음" 결정 → 우선순위 리스트 재정렬 (HIL 제외, physics_lab > simulator > editor 적용). Validation Bench 일반화 가 1순위.
- 2026-05-13 M1 — Phase 9 cycle: Validation Bench 일반화 layer (`app/physics_lab/validation_runner.py` + `ValidationRun` dataclass) — dynamic / static dispatch on `model.time_mode`. 17 신규 tests (사용자 PC verify 대기). UI 통합은 후속 M2.
- 2026-05-13 M2 — Phase 9 cycle: `BouncingBallController.run_validation_from_dataset` 가 `run_validation_for_model(BouncingBallModel(), ...)` 위임으로 refactor. obsolete `_simulate_for_validation` 제거. 1 parity regression test (controller path == direct layer call). Production code 에서 일반화 layer 첫 사용 — 임의-model UI selector 통합만 후속에 남음. plan/19 § 19.7.5+ ✗ → ✓.
- 2026-05-13 M3 — Phase 9 cycle: `domain/physics_lab/validation_defaults.py` 신규 (`default_validation_fields` — 3 built-in 모델 매핑). PhysicsLabWorkspace 가 `LibraryWidget.physics_model_selected` 연결 + `_current_physics_model` track + `_on_measured_dataset_selected` 분기 (BouncingBall vs generic) + `_run_generic_validation` (defaults 룩업 + `run_validation_for_model` + `install_validation_overlay` + status bar 갱신). `BouncingBallController` 에 public `install_validation_overlay` 추가. 9 신규 tests (4 defaults helper + 5 workspace dispatch). 우선순위 #1 종결.
- 2026-05-13 L2 — Phase 4 cycle: `ui/simulator/builtin_pipeline_plugins.py` 신규 (`BUILTIN_SIMULATOR_PLUGINS` 매핑, 5 stage curated baseline) + SimulatorWorkspace `_populate_builtin_pipeline_plugins` (init 후 PluginManager 채움). 5 신규 tests (전체 stage 매핑 / 중복 없음 / CFAR variant / Predictor·Classifier 빈 상태).
- 2026-05-13 L3 — Phase 4 cycle: SimulatorWorkspace `_on_run_tick_completed` 슬롯 (controller.tick_completed → FFT/RD/StageIO 의 `set_frame(frame_id)` fan-out). 5 신규 tests (defaults dash / 단일 tick / pause invariant / stop replay 1 부터 / 5 lock-step). Run panel + downstream panel frame_id 항상 일치 invariant.
- 2026-05-13 L4 — Phase 4 cycle: SimulatorWorkspace Properties panel 도 tick handler 가 paint (sim_t_s/frame_id/state/speed 4-row form 자동 갱신) + `show_selected_in_properties(label, properties)` / `clear_property_selection()` public API (user selection pin 시 tick handler 가 안 덮어씀). `_properties_owned_by_selection` 플래그. 5 신규 tests (initial nothing-selected / tick paints simulator context / selection pin invariant / clear returns to live / sim_t_s 매 tick 갱신).
- 2026-05-13 L5 — Phase 4 cycle: SimulatorWorkspace tick handler 가 StageIO 6 box (Transmitter / Environment / Receiver / Detector / Pairing / Tracker) IN/OUT 자리에 deterministic placeholder text 채움 (frame_id + sim_t_s 인코딩). Detector·Pairing·Tracker 는 "pipeline pending" 으로 명시 — 실 pipeline 후 swap. 4 신규 tests (default dash / 첫 tick / 3 tick 진행 / pause freeze).
- 2026-05-13 Sidequest #7 — Phase 5 #18/#19 reproducibility tests ✗ → ✓. `tests/unit/app/timing/test_reference_timing_reproducibility.py` 신규 (9 tests: PerformanceClock factory bit-identical state / round-trip ms↔Hz / FrameProfiler 동일 sequence → 동일 report / 순서 independent / reset replay invariant / 손계산 percentile golden).
- 2026-05-13 Sidequest #9 — SDK manifest.py 이동 △ → ✓. `src/workbench/sdk/manifest.py` 신규 + sdk/__init__.py re-export. domain/dlc/ 패키지 전체 삭제 (manifest.py + __init__.py). 6 callers 갱신 (app/dlc/installer.py, app/dlc/package_manager.py, io/package_io.py, sdk/package_validator.py, app/nn/trainer.py docstring, app/dlc/__init__.py docstring). tests/unit/domain/test_dlc_manifest.py → tests/unit/sdk/test_manifest.py 이동 (git mv) + import 갱신. integration test 갱신. plan/02 § 2.6b — SDK 가 DLC author 단일 surface 원칙 정렬.
- 2026-05-13 Sidequest #6 — Phase 3 Profile mode toggle △ → ✓. `src/workbench/domain/timing/profile_mode.py` 신규 (ProfileMode StrEnum + DEFAULT_PROFILE_MODE=OFF + PROFILE_MODES_IN_DISPLAY_ORDER tuple + parse_profile_mode helper). CLI `trsim run --profile-mode {off,explicit,live}` flag 추가 (default off) + manifest metadata 에 profile_mode 기록. `trsim profile` 도 explicit/live 선택 (default explicit). 9 신규 enum tests + 7 신규 CLI tests. Runtime probe gating 은 Pipeline.step 본격 wire 후 후속.
- 2026-05-13 Editor Composer dropdown wiring — `populate_composer_options_from_library` 신규 헬퍼 + MainWindow 가 dlc_runtime 있을 때 `populate_resource_browser_from_library` 옆에서 같이 호출. Composer 의 Map / Radar / Targets 콤보가 처음으로 실 ResourceLibrary 항목으로 채워짐. 3 신규 tests (빈 library / 3 카테고리 round-trip / scenarios 무시).
- 2026-05-13 Editor Composer validation controller — `ui/editor/composer/controller.py` 신규 (`ScenarioComposerController`). MainWindow 가 dlc_runtime 무관 wire. `validate_requested` 신호 받아 combo shape check + OK/WARN/ERROR 분류 + `set_validation(status, messages)` 호출. 5 신규 tests (OK / Map 누락 ERROR / Radar 누락 ERROR / targets 만 누락 WARN / signal end-to-end).
- 2026-05-14 Editor TargetsEditor validation controller — `ui/editor/targets_editor/controller.py` 신규 (`TargetsEditorController`). TargetsEditor 에 `rcs_edit()` / `scatterers_edit()` accessor 추가. MainWindow 에서 wire. shape check (name/motion/RCS/scatterers) + OK/WARN/ERROR + `set_validation_status` 호출. 8 신규 tests.
- 2026-05-14 Editor RadarEditor live computed-values controller — `ui/editor/radar_editor/controller.py` 신규 (`RadarEditorController`). RadarEditor 에 carrier/bandwidth/sweep/power/beamwidth/peak_gain 7 accessor 추가. carrier / antenna form 필드 editingFinished 마다 refresh — parabolic 은 `parabolic_beamwidth_3db_deg` / `parabolic_peak_gain_dbi` 사용, planar array 는 0.886λ/aperture + N_az×N_el + cos element 3 dB bonus. MainWindow 에서 wire. 9 신규 tests.
**최종 갱신**: 2026-05-14 — Composer + Targets + Radar editor controllers ✓.
