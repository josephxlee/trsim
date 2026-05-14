# TRsim — MVP 전체 작업 매트릭스

**plan/04 § 4.3 의 Phase 0~9 list 와 실제 구현 상태의 cross-check
매트릭스**. 새 sub-step 시작 / 끝낼 때 이 파일이 권위. 매 sub-step
push 후 해당 행 ✓ 갱신 (`CLAUDE.md` § 3.6 자동 업데이트 규약).

| 상태 | 의미 |
|---|---|
| ✓ | 완료 |
| △ | 부분 완료 (skeleton / placeholder 만, 실 데이터 binding 또는 CLI 미구현) |
| ✗ | 미구현 |

**최종 갱신**: 2026-05-14 — Phase 4 sweep (L4 + L5 + L6 + Editor M1/M2) **모두 완료**.
**누적 test**: 2707 PASS local, 5 contracts KEPT.
**HEAD**: Simulator 8 panel 전체가 live data binding 끝났고, Editor 의 DEM import → Map bounds auto-wire + Composer Installation block (terrain altitude + coverage stats) 도 live. Phase 4 의 실 데이터 binding sweep 본격 마감.

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
| Profile 모드 toggle (off / explicit / live, Q4) | ✓ (P3 — `domain/timing/profile_mode.py` `ProfileMode` StrEnum + `ProfileGate` (LIVE / OFF / EXPLICIT 1-shot latch) + `trsim profile --mode --explicit-every` CLI flag + `recorded_frames` payload key) |
| Warmup discard | ✓ |

---

## Phase 4 — UI ✓ (실 데이터 binding sweep 완료, 2026-05-14)

| 영역 | 상태 |
|---|---|
| pyqtgraph + pyvista + pyvistaqt 의존성 | ✓ |
| Main Window / Workspace selector / Dock manager / Command palette / Toolbar / Menu | ✓ |
| Editor Activity Selector (5 Activity 좌측 아이콘) + Resource Browser sidebar | ✓ |
| Scenario Composer widget skeleton | ✓ (M2 ComposerInstallationController — `position_changed` → mock probe → 실 readouts) |
| **Scenario Composer Installation Panel** (DEM + 차폐 Preview + Coverage Stats) | ✓ (G4 layout + M2 live binding via `set_terrain_altitude` / `set_coverage_stats`) |
| Map Editor widget skeleton (Pan/Zoom + Land/Sea Brush + Spot Edit + Flatten + AddBuilding) | △ (skeleton, brush/spot edit 본격은 후속) |
| **Map Editor DEM Import Wizard** (7 step, v0.22) | ✓ (E1-E4 + M1 successful import → `set_map_bounds` 자동 호출) |
| **Map Editor Domain Settings panel** (Simulation Domain + Outside Environment, v0.29) | ✓ (G1-G3 + M1 live Map bounds readout) |
| Radar Editor widget skeleton (AntennaType 드롭다운 + 동적 폼 + Beam Pattern Preview) | ✓ (P7 — `_BeamPatternPreview` pyqtgraph PlotWidget + sinc^2 analytic 패턴, `update_pattern(beamwidth_deg)`) |
| Targets Editor widget skeleton (메타 + Trajectory Preview) | ✓ (P7 — `_TrajectoryPreview` pyqtgraph PlotWidget + 7 motion-kind 별 synthetic 2D path, motion_kind combo 가 preview 자동 swap, set_trajectory 명시 API) |
| Atmosphere Panel widget skeleton (sky / visibility / rain_rate 등) | ✓ (P7 — rain-attenuation vs frequency preview, `rain_attenuation_dbpkm` ITU-R P.838 simplified model 사용, rain_rate edit 시 자동 refresh) |
| Simulator panels (Run / FFT / RD / Scene3D / PluginMgr / StageIO / Properties / ScopePOV) | ✓ (L1 Run + L2 FFT + L3 RD + L4 Scene3D + L5 PluginMgr seed + StageIO live + L6 Scope/Properties primary-target — 모두 RunController.tick_completed 에 묶임) |
| Scene 3D PyVista (DEM / wave / atmosphere / actors / 3rd-person + Scope POV / F-key focus) | ✓ (L4 — radar/target sphere + terrain plane placeholder + `enable_3d_viewer` lazy + `trsim ui --no-3d-viewer` flag) |
| Profiler panel (timing breakdown / scale indicator / report) | ✓ |
| NN mode panels (Step 1 Dataset / Step 2 Eval / Training) | ✓ |
| 방향키 이벤트 / Mode 전환 UI (DSP ↔ NN) / 단축키 정책 | ✓ (P5 — SimulatorWorkspace.keyPressEvent: Left/Right ±AZ 0.5deg / Up/Down ±EL 0.5deg / Home·0 reset, blended into PrimaryTargetController's cross-hair + AZ readout via `manual_az_offset_deg`. Mode 전환은 bottom tabs 의 Run/StageIO/Profiler vs NN Step1/Step2/Training 이미 노출 — 단축 토글 후속.) |

---

## Phase 5 — 물리 검증 ✓

17 카테고리 + 이 세션 12 sub-step 후속 보강 + P4 #18/#19 재현성
정량 끝. plan/04 § 4.3 Phase 5 list 의 #18 (Reference Timing
재현성) + #19 (Frame Profiler 결과 재현성) ✓ — P4 신규
`tests/physics/test_reference_timing_reproducibility.py` +
`test_frame_profiler_reproducibility.py` (frozen dataclass 동일성 +
sample sequence 동일 → 동일 report + percentile 단조 + reset
idempotent + multi-stage 독립).

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
| Step 2 Tracker / Predictor / Classifier 행 dispatch framework (stub functions → `n/a` rendering) | ✓-MVP (P6 — stub `tracker_loss / predictor_loss / classifier_loss` raise `NotImplementedError("Phase 6 follow-up")`; Step 2 controller catches → renders "n/a (plugin unsupported)"; locked by `tests/unit/app/test_nn_evaluator_postmvp_stubs.py`. **Real loss는 TrackerNNPlugin / PredictorNNPlugin / ClassifierNNPlugin 출시 후 post-MVP**) |
| Step 2 multi-step rollout RMSE metric (stub `multi_step_rollout_rmse` with input validation) | ✓-MVP (P6 — `multi_step_rollout_rmse(n_steps=...)` validates `n_steps` then raises `NotImplementedError`. **실 구현은 sequence dataset spec + PredictorNNPlugin 후 post-MVP**) |

---

## Phase 7 — DLC (Wave 2, v0.35) △

| 영역 | 상태 |
|---|---|
| SDK: protocols.py (11 Plugin Protocol) | ✓ |
| **SDK: manifest.py** | △ (domain/dlc/manifest.py 에 있음, sdk/ 이동 고려) |
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

## Phase 8 — HIL (Wave 3, v0.38) — **POST-MVP**, 자리만 예약

> **사용자 결정 (2026-05-14)**: HIL 은 MVP 이후 별도 cycle 에서
> 본격 작업. MVP 작업 중에는 디렉토리 + Protocol shell 자리만
> 남겨두고 진행하지 않음.

placeholder 상태:
- `src/workbench/app/hil/__init__.py` — docstring 만, 모듈 0개
- `src/workbench/domain/hil/__init__.py` — docstring 만, 모듈 0개
- `src/workbench/ui/simulator/hil_panel/__init__.py` — docstring 만, panel 0개
- `src/workbench/sdk/protocols.py` 의 `DUTAdapterProtocol` —
  `@runtime_checkable` class + post-MVP 안내 docstring, 멤버 0개

전체 Phase 8 행렬 (14 ✗ + 1 △, 본격 작업은 post-MVP):

| 8.1 MVP HIL (TCP/JSON + L5 Track) | 상태 |
|---|---|
| domain/hil/dut_messages.py (DUTTrack L5 dataclass) | ✗ |
| domain/hil/tx_signal.py (TXSignalDigital) | ✗ |
| domain/hil/comparison.py (HILComparisonResult 3-way) | ✗ |
| sdk/protocols.py 에 DUTAdapter Protocol (10번째, v0.39 lock-step) | △ (post-MVP placeholder shell — `@runtime_checkable Protocol` 자리만, plan/18 § 18.7 의 메소드 시그니처 post-MVP) |
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
| **plan/19 § 19.7.5+ 확장** (Validation Bench 일반화 / Library Models 동적 채우기 / Plugin discovery via PluginLoader) | ✓ (H+I+J Library Models 동적 + PluginLoader discovery + MainWindow auto-register + P2 `app/physics_lab/validation_bench.py`: 임의 PhysicsModelProtocol 받는 `ValidationBench` + `ValidationConfig` (dynamic/static 둘 다 지원, GravityOnly + BouncingBall + FreeSpaceLoss 자체 검증)) |

---

## 미구현 우선순위 리스트 (큰 덩어리 → 작은 덩어리)

다음 작업 결정 시 이 매트릭스 참조. 사용자 우선순위 (변동 없음):
**physics_lab > simulator > editor**.

**Phase 4 UI 실 데이터 binding sweep 마감** (L1-L6 + M1+M2). HIL 은
사용자 결정으로 **post-MVP** (자리만 예약, 위 § "Phase 8 — HIL"
참조). MVP 잔여 항목:

| 우선 | 작업 | 크기 | 비고 |
|---|---|---|---|
| 1 | **SDK manifest.py 이동** (domain/dlc → sdk/) | 잡 | 위치만 옮김 + import 갱신 + test 갱신. |
| 2 | **Polish**: Floating dock 옵션 B / Theme manager / Stone Soup adapter | 소 | 미루기 가능. |
| post-MVP | **Phase 6 Step 2 real Tracker/Predictor/Classifier loss** + **multi-step rollout** | 중 | TrackerNNPlugin / PredictorNNPlugin / ClassifierNNPlugin Protocol + sequence dataset spec 출시 후. 현재 stub + "n/a (plugin unsupported)" UI surface 가 MVP-acceptable. |
| post-MVP | **Phase 8 HIL 전체** (8.1 MVP → Lock-step → 8.2 L2/L4 → 8.3 L1+AWG) | 매우 대 | MVP 완성 후 별도 cycle. 자리만 예약, 작업 시작은 사용자 신호 후. |
| post-MVP | **Phase 4 L-series 후속**: Pipeline 실 연결 (mock generators 교체) | 큼 | 8 panel 의 mock generator 들을 실 `Pipeline.step()` probe 로 교체. Phase 6+ probe recorder 와 짝. |

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
- 2026-05-14 L2 — Phase 4 cycle: Simulator FFT panel pyqtgraph 통합 (2 curve up/down sweep + InfiniteLine peak markers) + `app/simulator/mock_spectrum.py` (`MockSpectrumGenerator` deterministic sim_t_s → 곡선) + `SimulatorFFTController` (RunController.tick_completed → mock generator → panel) + SimulatorWorkspace 자동 wiring (2518 → 2559 PASS). Simulator FFT panel 실 데이터 binding ✗ → ✓.
- 2026-05-14 L3 — Phase 4 cycle: Simulator Range-Doppler panel pyqtgraph 통합 (`pg.ImageItem` row-major + viridis LUT + InfiniteLine cross-hair + axis 캘리브레이션 via `setRect`) + `app/simulator/mock_range_doppler.py` (`MockRangeDopplerGenerator` deterministic + 2-D Gaussian peak, Lissajous trajectory) + `SimulatorRDController` (tick_completed → heatmap_for → panel) + SimulatorWorkspace 자동 wiring (2559 → 2607 PASS). Simulator RD panel 실 데이터 binding ✗ → ✓.
- 2026-05-14 L4 — Phase 4 cycle: Simulator Scene 3D panel pyvistaqt QtInteractor lazy mount + `MockSceneGenerator` (radar sphere + target sphere on circular orbit + terrain plane placeholder) + `SimulatorSceneController` + `enable_3d_viewer` kwarg propagation through `Scene3DPanel` / `SimulatorWorkspace` / `MainWindow` + `trsim ui --no-3d-viewer` CLI flag + `tests/unit/ui/simulator/conftest.py` pyvista OFF_SCREEN setup (2607 → 2635 PASS). Simulator Scene 3D 실 데이터 binding ✗ → ✓.
- 2026-05-14 L5 — Phase 4 cycle: Simulator Stage I/O panel live + Plugin Manager default seed. `app/simulator/mock_stage_io.py` (`MockStageIOGenerator` per-stage IN/OUT strings + `DEFAULT_PLUGIN_NAMES`) + `SimulatorStageIOController` (tick_completed → panel + Record toggle → in-memory log) + workspace seeds plugin rows once via `set_stage_plugins` (2635 → 2663 PASS). Simulator StageIO/PluginMgr 실 데이터 binding ✗ → ✓.
- 2026-05-14 L6 — Phase 4 cycle: Simulator Scope POV cross-hair canvas + Properties primary-target form. `app/simulator/mock_primary_target.py` (`MockPrimaryTargetGenerator`: orbit-driven range/az/el/RCS/speed + servo lag + scope cross-hair offset + lock flag) + ScopePOVPanel pyqtgraph PlotWidget + cross-hair InfiniteLine + ScatterPlotItem target marker + `SimulatorPrimaryTargetController` 가 Scope + Properties 두 panel 에 동시 push (2663 → 2693 PASS). Simulator Scope/Properties 실 데이터 binding ✗ → ✓. **Simulator 8 panel 전체 live binding 완료**.
- 2026-05-14 M1 — Phase 4 cycle: Editor `DEMImportController._on_import` 성공 시 grid_shape × cell_size 으로 `MapBounds` 계산 → `MapEditor.set_map_bounds` 자동 호출 → Domain Settings tab readout live (2693 → 2697 PASS). Map Editor DEM import → bounds live wire ✗ → ✓.
- 2026-05-14 M2 — Phase 4 cycle: `ComposerInstallationController` (composer.position_changed → mock probe → composer.set_terrain_altitude + set_coverage_stats) + MainWindow 자동 mount (2697 → 2707 PASS). Composer Installation 실 데이터 binding ✗ → ✓. **Phase 4 UI 실 데이터 binding sweep 본격 마감**.
