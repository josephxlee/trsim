# TRsim — MVP 전체 작업 매트릭스

**plan/04 § 4.3 의 Phase 0~9 list 와 실제 구현 상태의 cross-check
매트릭스**. 새 sub-step 시작 / 끝낼 때 이 파일이 권위. 매 sub-step
push 후 해당 행 ✓ 갱신 (`CLAUDE.md` § 3.6 자동 업데이트 규약).

| 상태 | 의미 |
|---|---|
| ✓ | 완료 |
| △ | 부분 완료 (skeleton / placeholder 만, 실 데이터 binding 또는 CLI 미구현) |
| ✗ | 미구현 |

**최종 갱신**: 2026-05-13 — Phase 7 remainder F1~F3 모두 완료 후.
**누적 test**: 2360 PASS local, 5 contracts KEPT.
**HEAD**: F3 MainWindow Plugins > Install Package... + Manage Plugins... 메뉴 wiring.

이전 historical gap 보고 (2026-05-12 시점, 사용자가 MVP_GUIDE 따라
검증한 결과) 는 [`docs/sessions/mvp_status_gap_report_2026_05_12.md`]
(sessions/mvp_status_gap_report_2026_05_12.md) 에 archive.

---

## 한 줄 요약

**MVP frame (Phase 0~5) ✓** — 단 Phase 3/4 의 일부 secondary 모듈 미완.
**MVP+α 4 wave**: Wave 1 (NN) frame ✓, Wave 2 (DLC) runtime ✓ CLI ✗,
**Wave 3 (HIL) 전체 ✗**, Wave 4 (Physics Lab) ✓.

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
| Profile 모드 toggle (off / explicit / live, Q4) | △ |
| Warmup discard | ✓ |

---

## Phase 4 — UI △ (골격 ✓, 실 데이터 binding ✗)

| 영역 | 상태 |
|---|---|
| pyqtgraph + pyvista + pyvistaqt 의존성 | ✓ |
| Main Window / Workspace selector / Dock manager / Command palette / Toolbar / Menu | ✓ |
| Editor Activity Selector (5 Activity 좌측 아이콘) + Resource Browser sidebar | ✓ |
| Scenario Composer widget skeleton | △ (widget.py 만, 실 데이터 binding ✗) |
| **Scenario Composer Installation Panel** (DEM + 차폐 Preview + Coverage Stats) | **✗** |
| Map Editor widget skeleton (Pan/Zoom + Land/Sea Brush + Spot Edit + Flatten + AddBuilding) | △ |
| **Map Editor DEM Import Wizard** (7 step, v0.22) | ✓ (E1-E4, MVP 4-page distillation: Source/Land-Sea/Output/Summary) |
| **Map Editor Domain Settings panel** (Simulation Domain + Outside Environment, v0.29) | **✗** |
| Radar Editor widget skeleton (AntennaType 드롭다운 + 동적 폼 + Beam Pattern Preview) | △ |
| Targets Editor widget skeleton (메타 + Trajectory Preview) | △ |
| Atmosphere Panel widget skeleton (sky / visibility / rain_rate 등) | △ |
| Simulator panels (FFT / RD / Run / Properties / PluginMgr / StageIO) | △ (placeholder, 실 데이터 binding ✗) |
| Scene 3D PyVista (DEM / wave / atmosphere / actors / 3rd-person + Scope POV / F-key focus) | △ (Phase 4.10 lazy create) |
| Profiler panel (timing breakdown / scale indicator / report) | ✓ |
| NN mode panels (Step 1 Dataset / Step 2 Eval / Training) | ✓ |
| 방향키 이벤트 / Mode 전환 UI (DSP ↔ NN) / 단축키 정책 | △ |

---

## Phase 5 — 물리 검증 ✓

17 카테고리 + 이 세션 12 sub-step 후속 보강 끝 (2065 PASS).
plan/04 § 4.3 Phase 5 list 의 #18 (Reference Timing 재현성) +
#19 (Frame Profiler 결과 재현성) 의 본격 재현성 시험은 △
(정량 invariant 만 추가, 같은 seed/load → 같은 결과 검증 ✗).

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
| **SDK: manifest.py** | △ (domain/dlc/manifest.py 에 있음, sdk/ 이동 고려) |
| SDK: resource_schemas.py (`validate_resource_toml_blob`, 4 categories) | ✓ (C8) |
| SDK: package_builder.py + `trsim sdk build` CLI | ✓ (C2) |
| **SDK: package_validator.py** | **✗** |
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

## Phase 8 — HIL (Wave 3, v0.38) **전체 ✗**

`app/hil/` 디렉토리만 빈 상태 (`__init__.py` 만).

| 8.1 MVP HIL (TCP/JSON + L5 Track) | 상태 |
|---|---|
| domain/hil/dut_messages.py (DUTTrack L5 dataclass) | ✗ |
| domain/hil/tx_signal.py (TXSignalDigital) | ✗ |
| domain/hil/comparison.py (HILComparisonResult 3-way) | ✗ |
| sdk/protocols.py 에 DUTAdapter Protocol (10번째, v0.39 lock-step) | ✗ |
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
| **plan/19 § 19.7.5+ 확장** (Validation Bench 일반화 / Library Models 동적 채우기 / Plugin discovery via PluginLoader) | △ (후속 candidate) |

---

## 미구현 우선순위 리스트 (큰 덩어리 → 작은 덩어리)

다음 작업 결정 시 이 매트릭스 참조. 사용자 우선순위 (변동 없음):
**physics_lab > simulator > editor**.

| 우선 | 작업 | 크기 | 비고 |
|---|---|---|---|
| 1 | **Phase 6 NN 보강** (Adam / workbench-train CLI / Step 2 행) | 중 | 사용자 가시 UX, 작은 단위 분할 가능 |
| 2 | **Phase 5 추가 후속** (5.7b / 5.8b / 5.11b / 5.12b / #18 / #19 재현성) | 소 | test-only, 안전, src 변경 0 |
| 3 | **Phase 7 DLC CLI 완성** (sdk build / install / sdk test / io/package_io / package_manager_panel + sample DLC + tutorial) | 대 | DLC ecosystem 시작점 |
| 4 | **Phase 8 HIL 전체** (8.1 MVP → Lock-step → 8.2 L2/L4 → 8.3 L1+AWG) | 매우 대 | 새 protocol + 새 layer + UI panel + sample mock |
| 5 | **Phase 3 MVP 누락 4 모듈** (bundle_service / evaluator / physics_gate / io/dem_import) | 중 | "MVP" 정의에 포함된 항목 |
| 6 | **Phase 4 UI domain_settings + installation_panel** (dem_import_wizard ✓) | 중 | Editor activity 완성에 필요 |
| 7 | **Phase 4 UI 실 데이터 binding** (Editor 5 activity / Simulator 8 panel) | 대 | 골격 ✓, 후속 큰 작업 |
| 8 | **Phase 9 § 19.7.5+ 확장** (Validation Bench 일반화 / Library Models 동적) | 소-중 | 후속 polish |
| 9 | **Polish**: Floating dock 옵션 B / Theme manager / Stone Soup adapter | 소 | 미루기 가능 |

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
