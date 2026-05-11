# CLAUDE.md — TRsim 새 Cowork 세션 진입점

이 파일은 새 Cowork 세션이 자동 로드한다. 짧게 유지 (≤ 200 lines).
설계 단계 가이드는 `AGENT_GUIDE.md` (295 줄, 정체성·17 plan 진입점)
참고 — 이 파일은 **Cowork 구현 단계** 의 작업 규약만 담는다.

## 0. 새 세션이 가장 먼저 읽을 것 (5 분 안에)

1. `SESSION_SUMMARY.md` — 최근 milestone (Phase 단위) 누적 로그
2. `docs/sessions/` 안의 **가장 최근** `phase_*.md` — sub-step 상태
3. `AGENT_GUIDE.md` — 정체성 + 불변 원칙 (필요할 때만)
4. `plan/04_migration.md` § 4.3 — 전체 Phase 0~8 흐름
5. `git log --oneline -10` — 최근 commit

`spaces/.../memory/MEMORY.md` (auto-memory) 는 자동 로드됨 —
재읽기 불필요.

## 1. 현재 진행 상황 (이 줄만 수시로 갱신)

> **다음 진입점**: Phase 7.6 DONE — main_window DLC bootstrap (옵션 A).
> ResourceLibrary→Editor sidebar 자동 feed 동작, PanelRegistry 가
> trsim.ui.panels DLC 자동 등록. 다음 큰 작업 선택지 B/C/D (Variant
> build runner / Real TrainerService / Simulator panel mount) 는
> 사용자 결정 영역.

- **Phase 7.6 DONE** — DLC runtime bootstrap (plan/17 § 17.4 finale).
  `src/workbench/app/dlc_runtime.py`: `DLCPaths` frozen (packages_root
  + user_root|None + builtin_root|None) + `default_dlc_paths(home=)`
  factory (~/.trsim/{packages,resources}) + `DLCAppRuntime` frozen
  (paths + PackageManager + PluginLoader + ResourceLibrary) +
  `build_dlc_app_runtime(paths)` (scan → load_all → library assembly,
  side-effect 0 on missing root). `src/workbench/ui/dlc_bootstrap.py`:
  `DLCRuntime` frozen (app + PanelRegistry) + `build_dlc_runtime(*,
  paths/app_runtime/panel_registry)` 3-way input + `populate_resource_
  browser_from_library(sidebar, library)` (4 카테고리 app→UI enum
  mapping: SCENARIOS→SCENARIO / MAPS→MAP / RADARS→RADAR / TARGETS→
  TARGETS, USER+PACKAGE→NORMAL status, BUILTIN→BUILTIN status, clear-
  before-add refresh). `src/workbench/ui/main_window.py` 가
  `__init__(*, dlc_runtime=None)` opt-in keyword + 생성 후 editor
  sidebar 자동 populate. 21 tests (app 9 + ui bootstrap 8 + main_window
  DLC 4): empty/missing root / user 단독 / builtin 단독 / user shadow
  builtin / UI panel plugin 자동 등록 / category mapping 4종 / builtin
  status prefix / clear-before-add refresh. 누적 **1505 PASS** (+21
  신규). 5 contracts KEPT (app/dlc_runtime → app.dlc + app.resources,
  ui/dlc_bootstrap → app + ui.editor + ui.panel_registry, contract 1
  위반 0).
- **Phase 7.3 + 7.4 + 7.5 DONE** — Plugin Loader + ResourceLibrary
  + Panel Registry (plan/17 § 17.4).
  - 7.3 `app/dlc/plugin_loader.py`: entry_point string `module:attr`
    importlib.util.spec_from_file_location + ``trsim.resources.*``
    path slot 디렉토리 resolve, slot prefix invalid / module 없음 /
    attribute 없음 / dir 없음 → load_errors 누적, 13 tests.
  - 7.4 `app/resources/library.py`: ResourceLibrary 3-source
    (User > Package > Built-in priority + shadowed_by_source 보고),
    ResourceCategory enum 4종 (maps/radars/targets/scenarios),
    dotfile skip, 11 tests.
  - 7.5 `ui/panel_registry.py`: PanelRegistry register / clear /
    workspace 필터 + register_dlc_plugins (PluginLoader 결과의
    trsim.ui.panels 자동 등록, default simulator/right), 13 tests.
  - 누적 **1484 PASS** (+37 신규).
- **Task 4 (Variant 4-tier manifest) DONE** — plan/07 § 7.4.5a.
  `src/workbench/domain/nn/variant_manifest.py`: `VariantEntry`
  (DatasetVariant + dataset_path) + `VariantsManifest` (spec_id +
  entries, duplicate variant_id reject) + `standard_pairing_
  variants()` 4-tier preset (A ideal / B attitude / C sidelobe /
  D full realistic) + `write_variants_manifest` (manual TOML
  string, backslash/quote escape, POSIX path normalisation) +
  `load_variants_manifest` (tomllib + per-field validation).
  14 tests (preset 4 + manifest validation 4 + write/read round-
  trip 2 + load failure 4). 누적 **1447 PASS** (+14 신규).
- **Phase 7.2 DONE** — PackageManager scan (plan/17 § 17.4.2).
  `src/workbench/app/dlc/package_manager.py`: `LoadedPackage`
  (manifest + root) + `PackageLoadError` + `PackageManager(packages_
  root).scan()` — 각 하위 디렉토리의 manifest.toml load,
  duplicate package_id reject (first wins), missing manifest /
  invalid TOML 은 load_errors 에 누적, get / installed_ids /
  load_errors property, rescan 가 이전 state 교체. 13 tests
  (missing root / empty / file-not-dir / single / 3-pack sorted /
  installed_ids / get hit+miss / missing manifest / invalid id /
  duplicate id / 2 rescan). 누적 **1433 PASS** (+13 신규).
- **Phase 7.1 DONE** — DLC manifest.toml schema (plan/17 § 17.2.4).
  `src/workbench/domain/dlc/`: `PackageMeta` (id kebab-case +
  SemVer version + license 필수) + `CompatibilitySpec` (trsim_min
  SemVer 필수, max free-form "1.x" 허용) + `PythonDeps`
  (extra_requires tuple) + `PackageManifest` (4 block 묶음) +
  `load_manifest_from_toml(path)` Python 3.11+ stdlib `tomllib`
  read-only parser. 28 tests (PackageMeta validation 13 / Compat
  validation 4 / TOML round-trip 4 / 누락 section reject 2 /
  invalid id propagate 1 / FileNotFound 1 / PythonDeps + manifest
  default 3). 누적 **1420 PASS** (+28 신규).
- **Task 3 (Training Panel UI) DONE** — plan/07 § 7.5.3.
  `src/workbench/ui/nn_training/`: `TrainingPanel` Qt widget (job
  config form 6 필드 + progress 4 라벨 + log + Run/Stop signals) +
  `NNTrainingController` 가 train_requested → TrainingJob 생성
  (validation: 빈 job_id/dataset/weights + non-int epochs +
  non-float lr + 0 epochs reject) → TrainerService(epoch_callback).
  run() → epoch 별 panel 업데이트. stop 은 stub (TrainerService MVP
  cancellation 없음). 19 pytest-qt tests (9 panel default/setter/
  signal + 10 controller happy/validation/stop). 누적 **1392 PASS**
  (+19 신규).
- **Task 2 (Phase 6 후속) DONE** — Real Pipeline probe wire (plan/07
  § 7.4.3 / § 7.4.5b). `src/workbench/app/nn/pipeline_runner.py`:
  `PairingScenarioSpec` frozen schema (targets_initial_state /
  dt_s / carrier_freq / bandwidth / sweep_period + 6 validation) +
  `PipelineRunner(builder, scenario, probe_callback)` 매 frame:
  target range propagate (CV) → `fmcw_triangle_beats` (Phase 1) →
  up/down beats + GT diagonal pair_indices, 패딩 -1 + zero → probe
  callback → builder.append. cancel 검사 probe 후 + frame 시작 시.
  `default_pairing_scenario(target_count)` 3-target preset.
  6.4c controller 의 random demo loop 를 PipelineRunner 호출로 교체.
  18 PipelineRunner tests + 6.4c test 1개 GT diagonal 검증 추가.
  누적 **1373 PASS** (+18 신규).
- **Phase 6.8 DONE** — Step 2 Evaluation controller (plan/07 § 7.6).
  `src/workbench/ui/simulator/nn_mode/step2_controller.py`:
  `NNStep2Controller(panel, datasets, plugins)` 가 dataset / plugin
  registry 받아 combo 채움 + `run_eval_requested` → pairing_loss
  (Pairing 행 RMSE 채움, Bias=0.0) + dataset/plugin 미선택 시 err
  메시지 + `export_report_requested` stub. `register_dataset` /
  `register_plugin` 동적 추가. 11 pytest-qt tests (combo populate
  + register / 2 empty-name reject / identity loss 0.000 / wrong
  loss 1.000 / 2 missing-input error / error recovery / export
  stub). 누적 **1355 PASS** (+11 신규).
- **Phase 6.7 DONE** — TrainerService stub (plan/07 § 7.5).
  `src/workbench/app/nn/trainer.py`: `TrainingJob` frozen+slots
  dataclass (training_job.toml 1:1 — job_id/task/dataset_path/
  weights_path/train_fraction/val_fraction/architecture/layer_sizes/
  activation/framework/optimizer/lr/batch_size/epochs/early_stopping/
  metrics_path; 9 validation rules) + `TrainingResult` (completed
  epochs/final losses/best val/best epoch/early_stopped) +
  `TrainerService(epoch_callback)` fake exponential-decay loss
  schedule + placeholder .npz weights save (layer pair zeros).
  실제 gradient descent 는 후속 sub-step / workbench-train CLI;
  schema + service surface 만 MVP. 21 tests in `tests/unit/app/
  test_nn_trainer.py` (default 생성 / 8 validation / 5 run / 2
  weights round-trip / job_id echo / 2 monotonicity). 누적 **1344
  PASS** (+21 신규).
- **Phase 6.6 DONE** — NNEvaluator 4-error 진단 (plan/07 § 7.6).
  `src/workbench/app/nn/evaluator.py`: `NNEvalResult` frozen
  dataclass (bayes_error / training / dev / test 4-error + 3 gap
  + diagnosis_hint + dataset_paths) + `pairing_loss(plugin, path)`
  =1-accuracy GT-valid filter (pair_indices≥0 만 채점) + `evaluate(
  plugin, training/dev/test, bayes_error=None)` = 4-error 계산 +
  gap 진단 hint. _GAP_FLAG_THRESHOLD=0.10 over threshold gap 마다
  bullet ("avoidable bias high" / "variance high" / "data
  mismatch"); balanced 시 단일 "balanced" 반환. 9 tests in
  `tests/unit/app/test_nn_evaluator.py` (identity dataset loss=0
  / wrong-label loss=1 / -1 mask exclude / 4-error all balanced /
  data mismatch detect / variance detect / bayes avoidable_bias /
  bayes range reject / dataset_paths round-trip). 누적 **1323
  PASS** (+9 신규).
- **Phase 6.5 DONE** — numpy-only Pairing NN reference (plan/07 §
  7.4.5b). `src/workbench/app/nn/pairing_nn.py`: `NumpyPairingNN`
  NNPluginMixin 첫 구체 plugin — Hungarian (scipy linear_sum_
  assignment) on `|up_beat[i] - down_beat[j]|` 비용. model_arch
  "numpy_nearest_neighbor_pairing" / framework_origin "numpy_only"
  / load_weights records path (no-op) / declare_internal_probes →
  `{"distance_matrix": np.ndarray}` / predict (up, down) →
  int32 pair_indices, -1 for unmatched. last_distance_matrix
  property 가 Probe Panel 노출. 13 tests in `tests/unit/app/
  test_nn_pairing.py` (mixin runtime check / 기본 속성 / load
  weights / probe declaration / 6 predict 정확성 (single / identity
  / 글로벌 최적 / 비대칭 / empty 양쪽 / probe record) / 2 input
  validation). 누적 **1314 PASS** (+13 신규).
- **Phase 6.4c DONE** — Step 1 Editor controller (plan/07 § 7.4.3).
  `src/workbench/ui/simulator/nn_mode/step1_controller.py`:
  NNStep1Controller(panel, seed) 가 `build_requested` →
  DatasetBuilder 생성 + target frames 만큼 random Pairing sample
  append + finalize, `cancel_requested` → builder.cancel(). 입력
  validation (frames non-int / negative / output path empty) +
  status/log 업데이트 + progress callback wiring. **scenario +
  Pipeline 통합은 6.5+ 에서 random sample loop 를 실제 step()
  probe 로 교체.** 8 pytest-qt tests in `tests/unit/ui/simulator/
  test_nn_step1_controller.py` (round-trip 6 sample 파일 / status
  + log / 3 input validation / cancel-no-build / 0-sample / 두 번
  consecutive build overwrite). 누적 **1301 PASS** (+8 신규).
- **Phase 6.4b DONE** — Pipeline probe-hook (plan/07 § 7.4.3).
  `src/workbench/domain/pipeline.py`: `ProbeCallback = Callable[[str,
  Mapping[str, Any]], None]` type + `step(..., probes=None)` 추가.
  4 stage hooks ("predict" / "associate" / "update" / "spawn") 매
  frame 매 stage 후 등록 callback 호출. payload dict 는 stage 별:
  predict→`predicted_tracks/dt_s`, associate→`predicted_tracks/
  detections/result`, update→`updated_tracks/associations`,
  spawn→`spawned_tracks/spawn_detection_indices`. probes=None 후방
  호환. 알 수 없는 stage 이름은 silently ignored (DLC forward
  compat). 9 tests in `tests/unit/domain/test_pipeline_probes.py`
  (backward compat + 4 stage payload + 4-stage 순서 + spawn 매
  frame 호출 + exception 전파 + unknown stage 무시). 누적 **1293
  PASS** (+9 신규).
- **Phase 6.4a DONE** — DatasetBuilder streaming class (plan/07 §
  7.4.3). `src/workbench/app/nn/dataset_builder.py`: spec/variant/
  dataset_id/output_path/target_samples/progress_callback 생성자 +
  `append(inputs_record, labels_record)` 매 sample 검증 + progress
  callback 호출 + `cancel()` / `finalize(scenarios, extra)` ->
  DatasetMeta + write_dataset 호출. App layer memory 에 list 누적,
  finalize 시 np.stack 으로 (N, *field.shape) 변환. 11 tests
  (round-trip / 0-sample edge / progress callback / cancel partial /
  append after finalize / finalize twice / 3 record-shape-dtype
  validation / 2 constructor validation). 누적 **1284 PASS**
  (+11 신규).
- **Phase 6.3 DONE** — DataExporter HDF5 IO (plan/07 § 7.4.4).
  `src/workbench/app/nn/data_exporter.py`: `write_dataset(path,
  meta, inputs, labels)` + `read_dataset(path) -> (meta, inputs,
  labels)`. HDF5 root attrs `meta_json` / `schema_json` /
  `variant_json` (JSON serialisation) + `inputs/<field>` /
  `labels/<field>` datasets per FieldSpec. 검증 (missing/extra
  field, wrong shape, wrong dtype) 가 file open 전에 실행 →
  partial file 생성 0. 10 tests: round-trip arrays/meta/spec/variant
  + 0-sample edge + 4 validation. 누적 **1273 PASS** (+10 신규).
- **Phase 6.1 + 6.2 DONE** — NN 통합 schema + plugin protocol layer.
  - 6.1 `src/workbench/domain/nn/sample_spec.py` (plan/07 § 7.4.4 /
    § 7.4.5a): FieldSpec (name/shape/dtype/desc, 15 allowed dtype
    strings, validation) + SampleSpec (spec_id/probe_stage/inputs/
    labels + duplicate-name check across inputs+labels) + DatasetVariant
    (A/B/C/D 4-tier + sea_state[0,9] validation) + DatasetMeta
    (dataset_id/spec/variant/total_samples/scenarios/extra). 24 tests
    in `tests/unit/domain/test_nn_sample_spec.py`.
  - 6.2 `src/workbench/sdk/protocols.py`: NNPluginMixin runtime_checkable
    Protocol (model_architecture / weights_path / FrameworkOrigin
    Literal / load_weights / declare_internal_probes). 5 tests in
    `tests/unit/sdk/test_nn_plugin_mixin.py` (mixin orthogonality
    + minimal impl runtime_checkable). 누적 **1263 PASS** (+29 신규).
- **Phase 5.15 + 5.16 DONE** (plan/11 § 11.7 / § 11.11.7 구현 +
  verification). `src/workbench/domain/coherence_validator.py`:
  ValidatorSeverity (INFO/WARN/ERROR) + ValidatorMessage frozen
  dataclass + `validate_map` (terrain ⊂ bounds + sea cell elevation
  ≤ sea_surface + all-land/all-sea INFO) + `validate_targets`
  (waypoint ∈ bounds + airborne altitude > terrain + surface near
  sea_surface) + `validate_buildings` (base ∈ bounds) + `has_errors`
  Run-gate. `src/workbench/domain/simulation_domain.py`:
  `sample_terrain_safe` bilinear interp + sea-cell snap to
  sea_surface.z + bounds-outside None. 15 + 9 tests. 누적 **1234
  PASS** (+24 신규).
- **Phase 5.19~5.22 DONE** — Phase 5 마감 batch.
  - 5.19 + 5.20 Multipath + horizon golden 회귀 (`tests/physics/
    test_multipath_horizon_golden.py` + `golden/multipath_horizon.json`):
    two-ray delta / phi / F²/F⁴ (free/sea/PEC) bit-for-bit rtol=1e-12
    + lobing landmarks (last null / first peak = 2x) + 4/3-earth Re_eff
    + 10m geometric horizon + two-point radio horizon 4/3 + sum-of-
    single-horizons invariant. 14 tests.
  - 5.21 ExtendedTarget σ_glint Monte Carlo 회귀
    (`tests/physics/test_extended_target_glint_rms.py`): Skolnik
    rule-of-thumb formula closed-form + 500-sample attitude/freq
    sweep per-axis std < L/(2√N) bound + |glint| < L convex hull
    + L/R symmetric body E-axis mean ~0 + deterministic seed
    invariant + different-seed divergence. 6 tests.
  - 5.22 Tracker maneuver scenario 회귀 (`tests/unit/domain/
    test_tracker_maneuver_scenario.py`): settled CV innovation → 0
    + velocity-step maneuver detection signature (post-step innov
    > 100x pre) + EKF/UKF RMSE 비율 0.95~1.05 (CV F-matrix 지배)
    + 높은 process noise → post-maneuver error 감소 + deterministic
    재현. 5 tests. 누적 **1210 PASS** (+25 신규).
- **Phase 5.17 + 5.18 DONE** — Tracker scenario regression.
  - 5.17 EKF + UKF: CV truth 위에서 F(dt) bit-for-bit 회귀 + 50-frame
    perfect-measurement 비발산 (pos<7.5m, vel<1.5m/s) + 정보 누적
    (cov trace 매 update 감소 + 첫 3 step monotonically 감소) + UKF
    predict ≡ EKF predict on linear CV (atol=1e-9) + UKF update
    pulls toward perfect measurement + innovation 노름 ½ 이하 감소
    + EKF/UKF predict negative dt reject. 9 tests.
  - 5.18 GNN data association: close pair → assigned, far pair →
    gated out, two-track/two-detection no-double-assignment +
    물리적 가까운 쪽 winner, two-track/one-detection 가까운 track
    winner, az ±pi wrap 경계 association, Mahalanobis = 0 for
    perfect measurement, noise std + gating threshold rejection,
    DEFAULT_GATING_THRESHOLD_CHI2 ≈ 14.16 (chi-square 3 DOF 99.7%).
    12 tests. 누적 1185 PASS (+21 신규).
- **Phase 5.15 + 5.16 SKIP** — coherence_validator + sample_terrain_safe
  는 plan/11 § 11.7 / § 11.11.7 정의만 있고 `src/workbench/` 코드
  미구현. Phase 6+ implementation 이후 verification 추가.
- **Phase 5.14 DONE** — ExtendedTarget multi-scatterer + glint 회귀
  (plan/14 § 14.10). golden 2-scatterer along-LOS 정확값 (amplitude
  1e-6 + (R0/R1)² ratio + centroid 1000.4995 + |sum| 1.2248e-6 +
  total_signal real/imag bit-for-bit). Skolnik glint 한계 invariant:
  apparent 5-scatterer aircraft 5종 attitude/freq 에서 scatterer ENU
  bounding box 안 + triangle inequality (|sum|≤Σamp) + total_rcs_dbsm
  attitude-invariant 4종 + deterministic 회귀 + body-x-aligned roll
  invariant + symmetric paired freq sweep glint mean ~0. 누적 1164
  PASS (+19 신규).
- **Phase 5.13 DONE** — FrameProfiler + StageTimingProbe 검증
  (plan/18 § 18.17). 기본 warmup=10 + negative warmup reject + empty
  stage / negative elapsed reject + stages 알파벳 정렬 + missing
  stage KeyError + below-warmup → NaN percentile + uniform 2ms 100
  sample → avg/p50/p95/p99 all 2.0 ms + report_all + reset.
  StageTimingProbe 1ms sleep → 1 sample 기록 + 예외 발생 시에도
  sample 기록 (worst case capture). 누적 1145 PASS (+12 신규).
- **Phase 5.12 DONE** — FrameBoundaryDetector 검증. 기본 frame_id=0
  + on_track_output 증가 + reset 0 복귀 + 명시 초기 frame_id 42
  부터 시작 + 매 호출 True 반환 invariant (MVP). 누적 1133 PASS
  (+6 신규).
- **Phase 5.11 DONE** — PerformanceClock 검증 (plan/18 § 18.16).
  생성자 reject + factory 두 종 (from_target_latency_ms /
  from_frame_rate_hz) + budget exhausted → sleep 0 + short frame
  pad ~ budget (5ms~50ms 대역) + factory round-trip (40ms ↔ 25Hz).
  누적 1127 PASS (+9 신규).
- **Phase 5.10 DONE** — CFAR detector 검증 (plan/04 § 4.3 Phase 5 #17,
  OS-CFAR vs CA-CFAR). alpha_ca_for_pfa Skolnik closed-form 3 case +
  monotonicity + pfa/n_total rejection. ca_cfar_1d spike detection +
  pure-noise 2048 cells with alpha(1e-3,32) → fa<20 + edge cells
  False + 4 input validation. os_cfar_1d clutter-edge spike + 2D
  shape rejection. 누적 1118 PASS (+16 신규).
- **Phase 5.9 DONE** — Single-scatterer RCS 분석 검증. sphere
  geometric pi·r² (r=1 → π, r²-scaling) + Rayleigh (r=1cm @ λ=3cm) +
  flat plate 4πA²/λ² + A² scaling + cylinder broadside + L² scaling +
  trihedral corner + a⁴ scaling + dBsm round-trip (1↔0, 10↔10, full
  round). 누적 1102 PASS (+14 신규).
- **Phase 5.8 DONE** — Ballistic analytic vs RK4 회귀 (plan/14 §
  14.5.3). vacuum free-fall 1s/2s position+velocity rtol=1e-12 + 수직
  fall horizontal 성분 invariant + sim_t 증가 + upward throw 왕복
  invariant + apex velocity zero / 높이 = v0²/(2g) + drag=0 일 때
  atm 무관 + drag>0 일 때 vacuum 보다 천천히 + BallisticDynamics
  validation + 45° 사선 throw range = v0²sin(2θ)/g. 누적 1088 PASS
  (+12 신규).
- **Phase 5.7 DONE** — Planar-array element_power 검증. isotropic
  unity / cos boresight / 30·45·60 deg 정확값 / 90 deg+ back-hemisphere
  zero / off-axis hypot(theta,phi) 회전 invariant / unknown kind
  rejection / non-increasing monotonicity. 누적 1076 PASS (+22 신규).
- **Phase 5.6 DONE** — Monopulse error 검증 (plan/08 § 8.5a.4).
  pure-real channel → slope·ratio 회수, imaginary delta → zero error,
  sigma 위상 회전 invariant, slope 2배 → error 2배, slope≤0 / |sigma|=0
  rejection, sum_amplitude = |sigma|. 누적 1054 PASS (+9 신규).
- **Phase 5.5 DONE** — Dynamics forces 검증 (gravity / drag, golden).
  gravity_force 선형 mass scaling + drag_force zero-velocity / 100mps
  east 정확값 + 임의 3 velocity 에서 drag·velocity 내적 <= 0 (kinetic
  energy 감소 invariant). 누적 1045 PASS (+6 신규).
- **Phase 5.4 DONE** — ISA atmosphere + rain attenuation 검증 (golden).
  Temperature lapse (sea/1km/11km), pressure (sea/1km/5km), density
  (sea/1km), rain_attenuation_dbpkm (10GHz 4mm/h) + 회귀 invariant
  (linear lapse, tropopause clamp, zero-rain edge) + AtmosphereState
  validation 4 종. 누적 1039 PASS (+13 신규).
- **Phase 5.3 DONE** — Parabolic antenna 검증 (golden 기반). beamwidth
  (D=0.6m / 1.2m @ 9.5 GHz) + 2x 비례 회귀 + peak gain dBi (eff=0.6) +
  beam pattern (boresight=1.0, half-bw=0.5) + 입력 검증 5종. 누적
  1026 PASS (+11 신규).
- **Phase 5.2 DONE** — FMCW propagation 검증 (golden 기반). beat_freq /
  doppler / range_resolution / wavelength 4 함수 + UP/DOWN beats round-
  trip pairing + zero-range / sign-convention edge cases. golden JSON
  closed-form reference (rtol=1e-12). 누적 1015 PASS (+8 신규).
- **Phase 5.1 DONE** — Golden Dataset 인프라 (plan/04 § 4.3 Phase 5).
  `tests/physics/golden_dataset.py`: GoldenDatasetMeta + GoldenSample
  + GoldenDataset frozen dataclass + JSON load/save (sorted keys).
  `tests/physics/golden/` 디렉토리 + sample reference. Phase 5.2~ 가
  19 카테고리 검증 시 이 모듈에 reference 데이터 적재. 누적 1007 PASS
  (+9 신규).
- **Phase 4 ALL DONE** (12 sub-phase 누적) — UI 골격 완성. Editor 5
  Activity (Composer/Map/Radar/Targets/Atmosphere) + Resource Browser
  사이드바 + Simulator 8 panel (FFT/RD/Run/Properties/PluginMgr/StageIO
  + Scene3D + ScopePOV) + Profiler tab (Timing/Scale/Report). 모든
  플롯 canvas 와 PyVista 임베드 는 Phase 4.x.x 후속에서. 누적 998
  PASS, ruff/mypy strict/import-linter 5 contracts KEPT.
- **Phase 4.12 DONE** — ProfilerPanel composite (plan/18 § 18.16/17).
  TimingBreakdownPanel (6 stage QProgressBar) + ScaleIndicator (toolbar
  scale 0.57x readout, 색상 cue 0.9/0.5 threshold) + ProfileReport
  (5 column QTableWidget: Stage/avg/p50/p95/p99). SimulatorWorkspace
  bottom tabs 에 Profiler 추가 (Run / Stage I/O / Profiler 3 tabs).
  Run Profile (100 frames) / Set Reference Timing 버튼 signals. 누적
  998 PASS (+15 신규).
- **Phase 4.11 DONE** — NN Mode panels (plan/07 + plan/05 § 5.1
  principle 6). Step 1 (Dataset Builder): Scenario / probe / frames /
  output path inputs + status banner + log list + Build/Cancel.
  Step 2 (Eval): Dataset / NN plugin combos + 4-error diagnostic table
  (Pairing / Tracker / Predictor / Classifier × RMSE/Bias). Mode
  selector UI 통합은 Phase 4.12. 누적 983 PASS (+9 신규).
- **Phase 4.10 DONE** — Scene3DPanel + ScopePOVPanel (plan/05 § 5.3.2).
  Scene3D = 3rd-person canvas placeholder + Camera preset toolbar
  (T/L/F/R) + 11 SceneLayer toggle (8 default-on). ScopePOV = boresight
  cross-hair canvas placeholder + AZ actual/cmd/lag readout.
  SimulatorWorkspace layout 4-col (PluginManager / 3D+Spectra vsplit /
  Scope / Properties) + bottom Run/StageIO tabs. PyVista QtInteractor
  + cross-hair renderer 는 4.10.x. 누적 974 PASS (+7 신규).
- **Phase 4.9 DONE** — Simulator 6 panel widgets + SimulatorWorkspace
  splitter layout (plan/05 § 5.3.4 / 5.3.6 / 5.3.6c / 5.3.5 / 5.3.3).
  FFTPanel + RangeDopplerPanel + RunPanel (history + primary metrics
  6 readout) + PropertiesPanel (context-sensitive form) +
  PluginManagerPanel (5 stage QListWidget) + StageIOPanel (6 IN/OUT
  box grid + record toggle). SimulatorWorkspace = 3-col QSplitter
  (PluginManager / FFT+RD vsplit / Properties) + bottom QTabWidget
  (Run / Stage I/O). 누적 967 PASS (+14 신규).
- **Phase 4.8 DONE** — TargetsEditor (plan/13 § 13.6) + AtmospherePanel
  (plan/15 § 15.4.3). Targets: 메타 form (name / motion_kind dropdown
  7종 / RCS / scatterer count) + Trajectory Preview placeholder + CSV
  Import/Export + Validation. Atmosphere: 5 field form (sky 4종 +
  visibility/rain_rate/temperature/pressure) → AtmosphereState frozen
  dataclass round-trip. 누적 953 PASS (+12 신규).
- **Phase 4.7 DONE** — RadarEditor 통합 폼 (plan/05 § 5.3.9 + plan/13
  § 13.5). AntennaType StrEnum (Parabolic / PlanarArray) → QStackedWidget
  로 동적 폼 swap. RXChannelMode (SINGLE_SUM / MONOPULSE_4CH) radio.
  Computed values strip (Az BW / El BW / Peak gain). BeamPattern
  Preview placeholder. Action: Save / Save As New. 누적 941 PASS
  (+9 신규).
- **Phase 4.6 DONE** — MapEditor 골격 (plan/13 § 13.4).
  Tools palette 좌측 (Pan/LandSeaBrush/SpotEdit/FlattenArea/AddBuilding 5
  ToolButton, exclusive group) + canvas placeholder + Layers panel
  (5 checkbox, 기본 3 on) + Edit History list + action row (Save /
  Import DEM... / Validate). MapTool StrEnum, tool_changed /
  layer_visibility_changed signal. canvas 는 pyqtgraph 도착 (Phase
  4.6.x) 까지 stub. 누적 932 PASS (+10 신규).
- **Phase 4.5 DONE** — ScenarioComposer 4 block 골격 (plan/13 § 13.3).
  References (Map/Radar/Targets dropdown + Open in Editor 버튼) +
  Installation (East/North/Az QLineEdit) + Composition (Sea State /
  Atmosphere QComboBox) + Validation (status banner + message list).
  Action row: Save / Save As / Validate / Export Bundle (4 signals).
  data source 는 Phase 5+ 에서 ResourceLibrary 로 주입. 누적 922 PASS
  (+8 신규).
- **Phase 4.4 DONE** — Resource Browser sidebar (plan/13 § 13.2.3).
  좌측 vertical activity bar 옆에 QSplitter 로 ResourceBrowserSidebar +
  central QStackedWidget. 트리 4 카테고리 (Scenarios/Maps/Radars/Targets)
  + ASCII status prefix ([active]/[stale]/[builtin]) + 검색 필터 +
  더블클릭 시 자동으로 매칭 Activity 로 전환. ResourceLibrary 데이터 source 는
  Phase 5+ 에서 주입. 누적 914 PASS (+21 신규).
- **Phase 4.3 DONE** — Editor ActivitySelector + 5 placeholder activities
  + Ctrl+1~5 단축키 + WorkbenchCommand 5 (`editor.activity.*`).
  ActivitySelector(QObject signal) 패턴 = WorkspaceSelector 와 동일.
  EditorWorkspace = 좌측 vertical activity bar + 중앙 QStackedWidget.
  placeholder 5종 (Composer/Map/Radar/Targets/Browser) — Phase 4.4+
  실제 구현이 swap. main_window 가 dispatch 시 자동으로 Editor
  workspace 로 전환 후 activity 선택. 17 tests 추가, 누적 893 PASS.
- **Phase 4.2 DONE** (4 sub-step 누적):
  - 4.2a (`e99c73d`) ui/commands/ 인프라 — WorkbenchCommand (frozen+
    slots) + Registry (substring fuzzy, title>id ranking, enabled_when)
    + CommandPalette QDialog (Ctrl+Shift+P, 화살표 from search box,
    Enter dispatch).
  - 4.2b (`9fa0ffd`) Sim / Target-Run 두 레이어 toolbar — addToolBarBreak
    로 행 분리. SIM_SPEEDS=(1,2,4,8) radio. State 라벨 (IDLE/RUNNING/
    PAUSED/ENDED). builtin.py 추출로 main_window thin assembler 유지.
  - 4.2c (`24e6d8b`) MainMenuBar(QMenuBar) — File/Edit/View/Run/Plugins/
    Tools/Help 7 menu. Run 안 Speed submenu. menu strong-ref 정책으로
    libshiboken "C++ deleted" 회피.
  - 4.2d DockManager (register/toggle/save_state/restore_state) —
    Phase 4.3+ 패널들이 여기 mount.
- 누적 test **876 로컬 PASS** (4.1 808 + 4.2a 19 + 4.2b 27 + 4.2c 12 +
  4.2d 10). .venv Python 3.13.3, pytest-qt 4.5.0. ruff/mypy
  strict/import-linter all clean. 5 contracts KEPT.
- 다음: **Phase 4.3** Editor ActivitySelector + 5 placeholder activities
  (Composer / Map / Radar / Targets / Browser). 전체 sub-phase 12개 계획
  (4.1~4.12).

## 2. 사용자 커뮤니케이션

- 한국어 **반말**, 간결.
- "추천대로" / "그렇게 가자" 한 마디 = full GO. 의문 다시 묻지 말 것.
- 누적 결정 ~100 개는 **이미 끝남**. 블로커 0. 재논의 회피.
- 완곡 표현 ("괜찮으시면", "제 생각엔") 최소화.

## 3. 코드 작업 규약

### 3.1 모듈 작성 패턴

- `frozen=True, slots=True` 기본. 도메인 dataclass 전부.
- `from __future__ import annotations` 항상.
- mypy strict 통과 — `**` 결과 Any 회피, `math.pow()`/`math.sqrt()` 사용.
- numpy 타입: `numpy.typing.NDArray[np.float64]`, `NDArray[np.bool_]`.
- 레이어 import 방향 (`02_architecture` § 2.6): UI → App → SDK →
  Domain → Physics → Primitives. `import-linter` 강제.

### 3.2 테스트

- 모든 모듈에 pytest 짝꿍 (`tests/unit/<layer>/test_<name>.py`).
- `pytest.approx` 는 **expected 우측** (`actual == approx(expected)`)
  — Yoda 회피 (SIM300 은 tests/ 에 per-file-ignore 적용).
- `pytest.raises(match=r"...")` 는 raw string + `\.` escape (RUF043).

### 3.3 Octave 짝꿍 (cross-validation)

- 위치: `docs/matlab_validation/`
- **base 함수만** 사용 — Mapping/Signal/Aerospace Toolbox 호출 금지
  (사용자 PC 는 GNU Octave).
- function-with-subfunctions 패턴 (Octave 의 script 안 local function
  미지원).
- Python 정확값을 expected 로 — 손계산 정밀도 낮으면 1e-3 → 1e-9 좁힘.

### 3.4 Lint 트랩 회피 (Phase 1 누적)

- RUF002 ASCII-confusable: `α`/`τ`/`−`/`×` → `alpha`/`tau`/`-`/`x`.
  docstring 도 검사됨.
- RUF043: regex meta-char 는 raw string + `\.` escape.
- I001: `ruff check --fix` 자동.
- ruff `format` 도 항상 통과 (commit 전 sandbox 에서 1 차 검증).

## 4. Cowork ↔ Windows mount sync 트랩

bindfs 가 가끔 파일 끝 1~5 char 잘라먹음 (Phase 1 부터 반복 발생).
대응:

- 파일 쓸 때 Python `open + flush + os.fsync()` 강제 sync.
- 매 commit 스크립트 첫 줄에 `tail -3 + grep <마지막_식별자>`
  자동 truncation 감지.

`git_sh/commit_*.sh` 의 sync 확인 블록이 표준 패턴.

## 5. Git 작업 (Claude Code 가 직접)

- Cowork 시절 사용자가 Git Bash 로 실행했지만 **Claude Code 단계
  (2026-05-09~) 부터는 내가 직접 commit + push** (gh auth 완료 후).
- 일회성 commit 스크립트 `git_sh/<name>.sh` 는 여전히 만들어 둠
  (gitignore) — sync 가드 + commit message 내용 정리용. 실행은 직접
  bash 또는 git 명령으로.
- DCO sign-off 필수 (`git commit -s`). 모든 commit 에 `-s` 포함.
- Co-Authored-By footer 포함 (system prompt 표준).
- branch 전략 단순: `main` 직 push. 외부 PR 받기 시작하면 재고.
- push 후 CI 결과 추측 금지 — `_ci_log.md` 에 한 줄 추가 흐름 (§ 7.1).

## 6. 세션 끝나면

사용자가 "오늘 여기까지" 또는 phase 완료 신호 주면:

1. `docs/sessions/phase_<N>_<topic>.md` 작성 또는 갱신 (1-3 페이지).
   컨벤션은 `docs/sessions/README.md` 참조.
2. `SESSION_SUMMARY.md` 의 milestone 줄 갱신 (Phase 단위 끝 시).
3. 새로운 결정·교정·트랩이 있으면 auto-memory 에 저장
   (`feedback_*.md` / `project_*.md`).

## 7. 흔한 함정 (Cowork 구현 단계 누적)

1. **CI 결과 추측** — 사용자가 push 한 뒤 CI 결과 받기 전에 "통과했을
   것" 추측 금지. 항상 "사용자 push 완료 → CI 결과 알려줘" 흐름.
2. **이미 한 결정 다시 묻기** — `MEMORY.md` 에 "결정 다시 묻지 말기"
   feedback 있음. 누적 ~100 결정은 끝난 사항.
3. **expected 손계산** — Phase 1.1 Seoul ECEF 2km 어긋남 / 1.3 beat
   freq 0.006 Hz 어긋남 사례. **Python 으로 계산한 정확값을 expected
   로** 박고 tolerance 좁히는 게 정답.
4. **Toolbox 호출** — Octave 는 base 만. `aer2enu`, `wgs84Ellipsoid`,
   `chirp` 류 전부 금지 — 직접 NIMA TR8350.2 / Mahafza 공식 작성.
5. **계획서 정체성 재정의** — `AGENT_GUIDE.md` § 1 의 불변 원칙
   (Primary Target / FMCW Triangle 단독 / Closed-loop 등) 충돌 시
   사용자 합의 필수.
6. **bindfs 잘림 무시** — `tail -3` 으로 파일 끝 검사 안 하면
   `Pyt` 같은 import 쓰레기로 commit 됨.

## 8. 이 파일 갱신

- 새 트랩 발견 → § 7 추가.
- Phase 진행 → § 1 한 줄 갱신.
- 작업 규약 합의 변화 → § 2~6 갱신.

설계 정체성·plan 인덱스는 여기 안 둠. `AGENT_GUIDE.md` 가 권위.

## 9. 사용자 명령 매핑 (단축 트리거)

사용자가 짧은 한국어 명령을 주면 해당 워크플로 .md 따라 실행.
워크플로 진입점은 `docs/agent_workflows/README.md`.

| 트리거 | 워크플로 | 동작 |
|---|---|---|
| "phase 상태", "진행 상황", "dashboard 갱신" | `docs/agent_workflows/phase_status.md` | 진행 보고 + dashboard artifact 갱신 |
| "sync 체크", "잘림 확인", 모듈 Write 직후 | `docs/agent_workflows/sync_check.md` | py_compile + ruff + tail 검사 |
| "ci 결과", "ci 봐줘", push 직후 | `docs/agent_workflows/ci_status.md` | scheduled task `trsim-ci-status` 또는 sandbox curl |

**중요 도구 위치**:
- Phase dashboard artifact id = `trsim-phase-dashboard` (cowork 사이드바)
- Scheduled task = `trsim-ci-status` (사용자 OneDrive\Claude\Scheduled\)
- pre-commit hook = `scripts/githooks/` (사용자 PC 에서 setup_hooks.sh 1회)

새 트리거 추가 시 워크플로 .md + 위 표에 한 줄.

---
최근 갱신: 2026-05-08 — Phase 2.3c 시점 + Cowork 구현 컨벤션 + § 9 명령 매핑 추가.
