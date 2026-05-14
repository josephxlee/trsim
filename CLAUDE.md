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

> **Phase 4 L3 — Simulator RD panel pyqtgraph live heatmap DONE**.
> L2 (FFT) 직후 Simulator 8 panel 중 세 번째 panel 이 실 데이터 받음.
> 신규 app/simulator/mock_range_doppler.py — `MockRangeDopplerGenerator`
> (deterministic sim_t_s → 2-D Gaussian heatmap, range/doppler 두
> 독립 sinusoid → Lissajous-like trajectory, Gaussian noise quantised
> by sim_t_s ^ rng_seed) + `MockRangeDopplerFrame` frozen dataclass.
> 갱신 ui/simulator/panels/range_doppler_panel.py — placeholder QFrame
> 제거 후 `pg.PlotWidget` + `pg.ImageItem` row-major + viridis LUT +
> ``setRect`` axis calibration ([m] vs [m/s]) + 2 InfiniteLine
> cross-hair (vertical doppler + horizontal range, DashLine) +
> `set_heatmap(heatmap_db, range_axis_m, doppler_axis_mps, *,
> levels_db)` + `set_peak / clear_peak`. Phase 4.9 header API
> (set_frame) 보존. 신규 ui/simulator/rd_controller.py =
> `SimulatorRDController(QObject)` — L2 의 FFTController 패턴 그대로
> 재활용 (tick_completed → generator.heatmap_for → panel push +
> enabled toggle + paint_for headless 진입점). SimulatorWorkspace 가
> FFTController 직후 RDController 자동 인스턴스화 + `rd_controller()`
> accessor. 누적 **2607 PASS** (+48 신규 in this cycle: 26
> mock_range_doppler + 12 range_doppler_panel + 10
> rd_controller/workspace), 5 contracts KEPT. ruff / mypy --strict /
> import-linter all clean.

> **Phase 4 L2 — Simulator FFT panel pyqtgraph live spectrum DONE —
> 1 sub-step (직전 cycle)**. app/simulator/mock_spectrum.py 신규
> (`MockSpectrumGenerator` deterministic sim_t_s → up/down sweep) +
> fft_panel.py 가 pg.PlotWidget + 2 PlotDataItem + 2 InfiniteLine
> peak marker + set_spectrum/set_peak_freqs API + fft_controller.py
> 신규 (`SimulatorFFTController` tick_completed wiring) + workspace
> 자동 wiring. 누적 2518 → 2559 PASS (+41).

> **Phase 4 L1 — Simulator Run panel 실 sim_time / frame_id binding
> DONE — 1 sub-step (직전 cycle)**. ui/simulator/panels/run_panel.py
> 에 새 "Simulation Time" GroupBox 추가 (sim_t / frame / state / speed
> 4 readout). 신규 ui/simulator/run_controller.py =
> `SimulatorRunController(QObject)` — 16ms QTimer + 자체
> `SimulationClock` + play/pause/stop/set_speed + tick(wall_dt_s) test
> 진입점 + tick_completed signal. frame_id 는 advance 시 sim_dt > 0 일
> 때만 +1 (paused/stopped 무영향). SimulatorWorkspace 가 controller
> 인스턴스 owned + sim_play / sim_pause / sim_stop / sim_set_speed
> forward 메서드. MainWindow 의 `_build_command_hooks` 가 sim.start /
> pause / stop / speed 명령 hook 을 그쪽으로 routing. 누적 2490 →
> 2518 PASS (+28).

> **Phase 9 MainWindow DLC Physics-Model Auto-Register (J1) DONE —
> 1 sub-step (직전 cycle)**. ui/main_window.py 가 DLCRuntime 받으면
> PhysicsLabWorkspace 생성 전 `_register_dlc_physics_models` 호출 →
> PhysicsLabWorkspace 의 default_physics_models() 가 built-in 3 +
> 등록 plug-in 다 picks up. 누적 2486 → 2490 PASS (+4).

> **Phase 9 PluginLoader Physics-Model Discovery (I1~I2) DONE —
> 2 sub-step 묶음 (직전 cycle)**. app/dlc/plugin_loader.py 의
> `_PYTHON_IMPORT_EXACT_SLOTS` 신설 + 9 singleton slot 지원 (I1) +
> app/physics_lab/discovery.py 신규 (`DiscoveryError` /
> `DiscoveryResult` + pure transform + side-effect helper) (I2). 누적
> 2468 → 2486 PASS (+18).

> **Phase 9 Library Models 동적 채우기 (H1~H2) DONE — 2 sub-step
> 묶음 (직전 cycle)**. ui/physics_lab/bouncing_ball_demo.py 의
> `LibraryWidget` 가 `set_physics_models` / `physics_model_for` /
> `physics_model_selected` 신규 (H1) + app/physics_lab/model_registry.
> py 신규 (`builtin_physics_models` / `register_physics_model` /
> `default_physics_models` / `physics_models_from`) + PhysicsLabWorkspace
> `physics_models` kwarg + `set_/refresh_/physics_models()` (H2).
> 누적 2434 → 2468 PASS (+34).

> **Phase 4 UI domain_settings + installation_panel (G1~G4) DONE —
> 4 sub-step 묶음 (직전 cycle)**. domain/simulation_domain.py 가
> `SimulationDomain` frozen+slots dataclass + `OutsideEnvironment`
> StrEnum 추가 (plan/11 § 11.11.3 finally 데이터모델, G1) +
> ui/editor/map_editor/domain_settings.py 가 `DomainSettingsPanel
> (QWidget)` (I/O free, 6 spin + 4 radio + Coverage Preview
> placeholder + Status, validation 은 SimulationDomain.__post_init__
> 위임, G2) + MapEditor 우측 panel 이 `QTabWidget(Layers + Domain)`
> 로 (G3) + ScenarioComposer Installation block 본격 layout +
> Domain Override block + `CoverageStats` frozen dataclass (G4).
> 누적 2360 → 2434 PASS (+74).
>
> **이 cycle 인계**: `docs/sessions/phase_4_l3_rd_panel_2026_05_14.md`.
> 직전 cycle 인계: `docs/sessions/phase_4_l2_fft_panel_2026_05_14.md`,
> `docs/sessions/phase_4_l1_run_panel_2026_05_13.md`.
> 사용자 우선순위 (변동 없음):
> **physics_lab > simulator > editor** — Simulator 8 panel 중 Run + FFT
> + RD ✓; 다음 cycle 후보: L4 Scene 3D PyVista lazy create (큼) /
> L5+L6 (Properties / ScopePOV / PluginMgr stage / StageIO record, 중).

- **Phase 4 cycle (L3) 1 sub-step (이 cycle)** — Simulator 8 panel 중
  세 번째 panel (RD) 가 처음으로 실 데이터 받음. L2 의 FFTController
  패턴 그대로 재활용 (mock generator + tick_completed wiring). 누적
  +48 tests.

  | sub | commit | new | 내용 |
  |---|---|---|---|
  | L3 | `24d1894` | +48 | `app/simulator/mock_range_doppler.py` 신규 (`MockRangeDopplerGenerator` deterministic 2-D Gaussian + Lissajous trajectory + `MockRangeDopplerFrame`) + `panels/range_doppler_panel.py` pyqtgraph PlotWidget + ImageItem (row-major + viridis LUT + setRect axis calibration) + 2 InfiniteLine cross-hair + `set_heatmap / set_peak / clear_peak` + `ui/simulator/rd_controller.py` 신규 (`SimulatorRDController` tick_completed wire + paint_for) + SimulatorWorkspace 자동 wiring + `rd_controller()` accessor |

  학습 (1개):
  - **pyqtgraph ImageItem.boundingRect() 가 local pixel rect 반환** —
    `setRect(x, y, w, h)` 는 QTransform 으로 pixel → data 좌표 매핑.
    boundingRect() 만 보면 (0,0,n_cols,n_rows). 데이터 좌표 검증은
    `item.mapRectToParent(item.boundingRect())` 또는
    `mapRectToView()` 로 변환 후 확인 필요.

- **Phase 4 cycle (L2) 1 sub-step (직전 cycle)** — Simulator 8 panel 중
  두 번째 panel (FFT) 가 처음으로 실 데이터 받음. 누적 +41 tests.

  | sub | commit | new | 내용 |
  |---|---|---|---|
  | L2 | `0d6b8db` | +41 | `app/simulator/mock_spectrum.py` 신규 (`MockSpectrumGenerator` deterministic + `MockSpectrumFrame`) + `panels/fft_panel.py` pyqtgraph PlotWidget + 2 PlotDataItem + 2 InfiniteLine peak marker + `set_spectrum / set_peak_freqs / clear_peak_freqs` + `ui/simulator/fft_controller.py` 신규 (`SimulatorFFTController` tick_completed wire + enabled toggle + paint_for) + SimulatorWorkspace 자동 wiring + `fft_controller()` accessor |

  학습 (2개, 직전 cycle):
  - **PySide6 ``QPen.setStyle`` raw int 거부** — `pyqtgraph.mkPen(...,
    style=2)` 가 PySide6 6.11 strict-typed signature 에 의해 `TypeError`.
    `Qt.PenStyle.DashLine` 등 enum 필수.
  - **ruff RUF046** — Python 3 `round()` 는 이미 int 반환.
    `int(round(x))` 는 redundant cast.

- **Phase 4 cycle (L1) 1 sub-step (직전 cycle)** — Simulator Run panel
  이 처음으로 실 데이터 (SimulationClock state) 받음. 사용자
  "Simulation 가장 시급" 우선순위 첫 진입. 누적 +28 tests.

  | sub | commit | new | 내용 |
  |---|---|---|---|
  | L1 | `25db1ae` | +28 | run_panel "Simulation Time" GroupBox (4 readout) + `SimulatorRunController` (16ms QTimer + SimulationClock + play/pause/stop/set_speed/tick) + workspace forward + MainWindow sim.start/pause/stop/speed hooks |

- **Phase 9 cycle (J1) 1 sub-step (직전 cycle)** — DLC 의 physics-model
  plug-in 이 사용자 GUI 에서 처음으로 visible. plan/19 § 19.7.5+
  전체 ✓. 누적 +4 tests.

  | sub | commit | new | 내용 |
  |---|---|---|---|
  | J1 | `0b03e3e` | +4 | MainWindow `_register_dlc_physics_models(dlc_runtime)` helper + PhysicsLabWorkspace 생성 전 register 호출 + `physics_discovery_result()` accessor |

- **Phase 9 cycle (I1~I2) 2 sub-step (직전 cycle)** — DLC 가 manifest 의
  `trsim.physics_model` 슬롯으로 사용자 정의 PhysicsModel 을 ship
  가능. plan/19 § 19.7.5+ "Plugin discovery via PluginLoader" ✓.
  누적 +18 tests.

  | sub | commit | new | 내용 |
  |---|---|---|---|
  | I1 | `0e9a01f` | +4 | PluginLoader `_PYTHON_IMPORT_EXACT_SLOTS` frozenset + `trsim.physics_model` / `trsim.tracker` 등 9 singleton 슬롯 + error msg 갱신 |
  | I2 | `eed2640` | +14 | `app/physics_lab/discovery.py` — `DiscoveryError` / `DiscoveryResult` frozen dataclass + `physics_models_from_loaded_plugins` pure transform + `register_discovered_physics_models` side-effect helper |

- **Phase 9 cycle (H1~H2) 2 sub-step (직전 cycle)** — Physics Lab
  Library Models 카테고리가 처음으로 PhysicsModelProtocol 인스턴스
  를 받게 됨. plan/19 § 19.7.5+ "Library Models 동적 채우기" ✓.
  PhysicsLabWorkspace 가 default 3 built-in (Gravity / BouncingBall /
  FreeSpaceLoss) 자동 mount. 누적 +34 tests.

  | sub | commit | new | 내용 |
  |---|---|---|---|
  | H1 | `0773c9d` | +12 | LibraryWidget `set_physics_models` / `physics_model_for` / `physics_model_selected` signal — empty fallback to legacy 2 placeholder |
  | H2 | `03b22e9` | +22 | `app/physics_lab/model_registry.py` (`builtin_*` / `register_*` / `default_*` / `physics_models_from`) + PhysicsLabWorkspace `physics_models` kwarg + `set_/refresh_/physics_models()` |

- **Phase 4 cycle (G1~G4) 4 sub-step (직전 cycle)** — Map Editor 우측
  panel 이 처음으로 Layers 외 두 번째 탭 갖게 됨. Composer 의
  Installation block 이 plan/13 § 13.3.3 의 본격 layout 으로 확장.
  누적 +74 tests.

  | sub | commit | new | 내용 |
  |---|---|---|---|
  | G1 | `1403278` | +24 | `SimulationDomain` + `OutsideEnvironment` dataclass (plan/11 § 11.11.3) — `from_map_bounds` classmethod + `contains_bounds` |
  | G2 | `e0256ef` | +18 | `DomainSettingsPanel(QWidget)` — I/O free + 6 spin + 4 radio + Coverage Preview placeholder + Status |
  | G3 | `9b70fc1` | +11 | Map Editor 우측 panel → `QTabWidget(Layers + Domain)`; signal forward + `set_map_bounds`/`show_domain_tab` |
  | G4 | `8460f5f` | +21 | Composer Installation 본격 layout + Domain Override block + `CoverageStats` dataclass |

  학습 (3개):
  - **PySide6 ``QComboBox.itemData`` 가 Python Enum 객체 identity 잃음** —
    QVariant wrap 통과 시 `combo.currentData() == MyEnum.X` 가 False.
    StrEnum 이면 `.value` (str) 저장 + round-trip 시 `MyEnum(value)`.
  - **Worktree rebase + main 직 push fast-forward** — origin/main 이
    다른 session 으로 앞서있을 때 `git rebase origin/main` + `git
    push origin <branch>:main` 으로 ff push (force 차단 안 걸림).
  - **stale `# type: ignore` 검출** — mypy --strict 가 stale ignore
    검출. inner panel forward 시 findChild None 가능성 위 `type:
    ignore[return-value]` 명시 필요.

- **Phase 7 remainder (F1~F3) DONE — 3 sub-step 묶음 (직전 cycle)**.
  app/dlc/installer.py 가 install_package + uninstall_package +
  InstallResult / UninstallResult + 3 typed errors 추출 (CLI + UI
  공유, F1) + ui/editor/package_manager_dialog.py 가
  PackageManagerDialog (QDialog wrapping 기존 PackageManagerPanel) +
  PackageManagerController (panel signal ↔ installer 서비스 wire +
  install_completed/install_failed 등 4 outgoing signals, F2) +
  MainWindow 가 plugins.manage / plugins.install_package 두 메뉴
  entry 를 PackageManagerController 에 routing + Plugins 메뉴에
  "Install Package..." 추가 (F3). 누적 **2360 PASS** (+34 신규
  in this cycle), 5 contracts KEPT 매 commit.

- **Phase 7 remainder menu wiring 3 sub-step (직전 cycle)** — Plugins
  메뉴에서 처음으로 실제 동작. 누적 +34 tests.

  | sub | commit | new | 내용 |
  |---|---|---|---|
  | F1 | `892d209` | +11 | app/dlc/installer.py: install_package + uninstall_package + InstallResult / UninstallResult + 3 typed errors (Error suffix for N818 ruff). CLI 가 thin wrapper 로 refactor. |
  | F2 | `b94351e` | +17 | ui/editor/package_manager_dialog.py: PackageManagerDialog (QDialog hosting PackageManagerPanel) + PackageManagerController (single-window + 4 outgoing signals + installer/uninstaller/dialog_factory/file_picker 모두 inject 가능). |
  | F3 | (this commit) | +6 | MainWindow: plugins.install_package 명령 + Plugins 메뉴 entry 추가 + Manage Plugins... 가 dialog open / Install Package... 가 direct file picker. dlc_runtime 의 packages_root override 가능. |

  학습:
  - **ruff N818**: `Exception name should be named with an Error suffix`.
    `PackageAlreadyInstalled` → `PackageAlreadyInstalledError` 등.
    Custom exception subclass 작성 시 항상 -Error suffix.
  - **`replace_all=True` 무한 luxe**: `Edit replace_all` 가 `Foo` →
    `FooError` 도중 이미 `FooError` 였던 라인을 `FooErrorError` 로
    만들 수 있음. 대량 rename 시 이미 부분 변경된 토큰 검사.
  - **MainWindow 메서드 hook 의 late binding**: `register_builtin_
    commands` 가 hooks 등록할 때 `self._dlc_manager_controller`
    는 아직 None — 하지만 hook 이 `self._open_dlc_manager` 메서드
    참조라면 OK. 메서드 안의 attribute access 는 dispatch 시점에
    resolve. controller 는 __init__ 후반에 만들어지면 충분.

- **Phase 4 dem_import_wizard 4 sub-step (직전 cycle)** — Editor
  "Import DEM..." 버튼이 처음으로 실제 동작. 4 sub-step (E1
  LandSeaMode → E2 run_dem_import → E3 wizard QDialog → E4 controller
  + MainWindow mount). +46 tests. 자세한 내용은
  `docs/sessions/phase_4_dem_import_wizard_2026_05_13.md`.

- **Phase 5 후속 DONE (이 세션)** — 12 sub-step, test-only, 누적
  +79 tests (1986 → 2065). 패턴: 기존 검증 카테고리 각각에 closed-
  form scaling invariant / boundary case / multi-band golden /
  monotonicity / cross-axis decoupling 정량 추가. src 변경 0.

  | sub | commit | new | 보강 카테고리 |
  |---|---|---|---|
  | 5.21b | `1588b1f` | +9 | ExtendedTarget glint — N=2/5/10 × L=4/12/40 scaling, plan/14 § 14.10.6 closed-form lock |
  | 5.22b | `36f3e9c` | +6 | Tracker — Bar-Shalom CT (1.6 g) sustained maneuver, plateau invariant |
  | 5.19c/5.20c | `abfe398` | +12 | Multipath/horizon — S-band (constructive) / Ku-band lobing / k=1/1.5 horizon |
  | 5.18b | `e21ed86` | +5 | GNN — 4×4 dense / 3+1 clutter / boundary gating (calibrated offset) / chi² quadratic |
  | 5.13b | `dab6492` | +6 | FrameProfiler — warmup boundary off-by-one / bimodal+ramp distribution / reset idempotent |
  | 5.4b | `452f079` | +7 | ISA — stratosphere T/rho clamp / ideal gas law / rain monotonicity |
  | 5.10b | `b76a695` | +5 | CFAR — alpha asymptotic `-ln(Pfa)` / N-monotonic / CA-mask vs OS-recover (interferer) |
  | 5.9b | `2390ee2` | +6 | RCS — Rayleigh r⁶/λ⁻⁴ / cylinder linear-in-r / trihedral 3x flat-plate / dBsm 6-decade round-trip |
  | 5.2b | `f0139e4` | +7 | FMCW — linear in (B, R, 1/T_s) / doppler antisymmetric / receding-target round-trip |
  | 5.3b | `90635cb` | +5 | Parabolic — BW inverse-f / G +6 dB on 2x D / radial symmetry / monotone descent |
  | 5.6b | `17cca72` | +5 | Monopulse — axis decoupling / sign symmetry / Re(δ/σ) sigma scaling |
  | 5.5b | `13210b3` | +6 | Drag — v²/A/Cd scaling / altitude decrease / antiparallel-to-v / gravity ENU lock |

  공통 패턴 학습:
  - itertools.pairwise 우선 (RUF007). `zip(..., strict=False)` 도 RUF007.
  - mypy --strict 의 `[unused-ignore]` 가 stale `# type: ignore`
    잡아냄. 검증 파일 손댈 때 함께 cleanup.
  - boundary 검증은 measured 기반 (`_calibrated_offset_for_chi2`)
    로 fragility 회피. `H P H^T + R` 처럼 implementation 내부에
    숨겨진 scaling 이 있으면 closed-form lock 대신 measure-and-
    lock pattern 권고.
  - amplitude-weighted centroid (5.21b uniform-line target) 은
    RCS 균등이면 geometric centroid 가 고정 → L² scaling artifact.
    glint scaling 검증은 asymmetric RCS 또는 monotonicity 만.
  - bimodal distribution percentile (5.13b): numpy linear-interp
    p99 가 outlier 1개에선 안 잡힘 — 5 outlier 비율 필요.



- **Phase 9.3a/b/c/d/e DONE** — Physics Lab 고급 기능 (plan/19 § 19.8 +
  § 19.9.5 + § 19.7.4). 5 commits push.
  - **9.3a** (`95d7927`): `ui/physics_lab/code_editor.py` 신규.
    `PythonCodeEditor(QTextEdit)` + QCompleter case-insensitive +
    Python keywords + builtins + Bouncing Ball API (simulator, dt_s,
    state, position_m 등). `default_completion_words()` pure 함수.
    keyPressEvent override 로 popup 통합 + Ctrl+Space 수동 trigger.
    CodePreview 가 QTextEdit → PythonCodeEditor 교체 (highlighter +
    Edit toggle 그대로 작동). 15 신규 tests (word list invariants +
    completer 와이어링 + CodePreview integration + multi-function /
    import / module-level constant exec regression).
  - **9.3b** (`fce9384`): `sdk/protocols.py` 의 PhysicsModelProtocol
    stub → full concrete (name / category / parameters / time_mode
    / visualization / compute). 3 type alias (PhysicsModelCategory /
    PhysicsModelTimeMode / PhysicsModelVisualization). SDK 가 처음
    domain.physics_lab.PhysicsParam import (Contract 4 allowed).
    `app/physics_lab/models.py` 신규 3 built-in 구현: GravityOnly
    Model (analytic free-fall, dynamic), BouncingBallModel (PL-D
    step packaged, BOUNCING_BALL_PARAM_SPECS), FreeSpaceLossModel
    (static Friis). 14 신규 tests (runtime_checkable conformance +
    metadata + compute physics + Bouncing Ball regression vs
    BouncingBallSimulator).
  - **9.3c/d** (`9095174`): `app/physics_lab/learning_models.py` 신규.
    NumpyNNPhysicsModel (Phase 6 numpy_mlp wrap, train(x, y) +
    compute({"x"}, ...) -> {"y_pred"}, static, parameters=()).
    PolynomialFitModel (numpy.polyfit degree 1..5, coefficients
    high-to-low, single 'degree' user-facing PhysicsParam). 16 신규
    tests (NN linear-map convergence + reject pre-train compute +
    Polynomial recover y=x^2 to 1e-9 + higher-degree-better-fit
    invariant + underdetermined / shape reject).
  - **9.3e** (`6d9e328`): `sdk/protocols.py` 에 TestObjectProtocol
    추가 (name / visual / analytic_rcs_m2). `__test__ = False`
    post-class setattr (runtime_checkable membership 영향 회피).
    `ui/physics_lab/test_object_view.py` 의 build_test_object_mesh
    가 `_VISUAL_KIND_BUILDERS: dict[str, MeshBuilder]` 레지스트리로
    리팩터링 + `register_visual_kind_builder(visual, builder)` 공개
    API. 9 built-in 그대로 사전 등록. `ui/physics_lab/custom_test_
    objects.py` 신규 Pyramid 샘플 plugin (square base + apex 4-면체)
    + `register_custom_test_objects()` 헬퍼. 12 신규 tests
    (registry 사전 등록 / overwrite / unknown kind reject / Pyramid
    runtime_checkable / 차원 검증 / 메쉬 빌드 등록 전후).

  세션 누적 9.3 push: 95d7927 + fce9384 + 9095174 + 6d9e328. 누적
  1986 PASS (+57 across 9.3a-e), 5 contracts KEPT.

- **Phase 9.2a/b/c/d DONE** — Physics Lab 외부 자료 + 학습 워크플로
  (plan/19 § 19.9). 4 commits push.
  - **9.2a/b** (`a199e3a`): `domain/physics_lab/measured_data.py` +
    `papers.py` 신규. `MeasuredDataset` (csv/hdf5 + columns +
    description + source + license + units) + `PaperReference` (pdf
    only). `inspect_csv` / `inspect_hdf5` / `inspect_pdf` 가 sidecar
    `<file>.toml` 자동 로드. `load_measured_csv` (skip-header float64
    2D) / `load_measured_hdf5(dataset, column)` 데이터 로더. `list_*`
    sorted directory scan. LibraryWidget 가 QTreeWidget 5 카테고리로
    확장 (Measured Data + Papers 추가) + `set_measured_datasets` /
    `set_papers` / `measured_for` / `paper_for` + `measured_dataset_
    selected` / `paper_selected` 시그널. PhysicsLabWorkspace `measured_
    root` / `papers_root` kwargs + `refresh_measured_datasets` /
    `refresh_papers`. 37 신규 tests.
  - **9.2c** (`43153f9`): `domain/physics_lab/validation.py` 신규.
    `ValidationMetrics` (n_samples / rmse / max_abs_error /
    pearson_correlation) + `compute_validation_metrics(measured_x,
    measured_y, sim_x, sim_y)` — sim_x sort + measured 범위 제한 + interp
    + RMSE/max/corr. Zero-variance 입력 corr=0 (NaN 회피). `BouncingBall
    Controller.run_validation_from_dataset(dataset, *, x_column,
    y_column, dt_s=0.005)` 가 dataset 의 column pair 로드 → 현재 params
    로 fresh simulator 돌려 measured x-range cover → 메트릭 계산 →
    `validation_measured` (red) + `validation_sim` (blue) overlay curve
    설치 → `validation_metrics_ready(metrics)` 시그널. live history
    무영향. 워크스페이스가 measured_dataset_selected 자동 fire →
    상태바에 `RMSE=... max|err|=... corr=... (n=...)`. 21 신규 tests.
  - **9.2d** (`5de15a0`): `app/physics_lab/parameter_fitter.py` 신규.
    `FitConfig` (fit_restitution=True default + 3 off) + `FitResult`
    (4 fitted scalars + RMSE + iters + msg) + `fit_bouncing_ball
    (*, measured_x/y, initial_*, config, dt_s, max_iter)` 가
    `scipy.optimize.minimize` Nelder-Mead 로 RMSE 최소화. Bounds
    clamp inside loss. 1 ~ 4 free params 지원. `BouncingBallController.
    fit_to_measurement(dataset, config, apply_to_live_state=True)` +
    `fit_result_ready(result)` 시그널. LibraryWidget 가 "Fit to
    selected measurement" 버튼 추가 (measured 선택 시만 enable) +
    `fit_requested(MeasuredDataset)` 시그널. Workspace 가 fit 결과
    자동 슬라이더 갱신 + 상태바 `fit: rest=... drag=... RMSE=...`.
    Synthetic 측정 (r=0.5) → biased start (r=0.85) → fit 이 ~5% 안
    수렴 검증. 21 신규 tests.

  세션 누적 9.2 push: a199e3a (9.2a/b) + 43153f9 (9.2c) + 5de15a0
  (9.2d). 누적 1929 PASS (+79 across 9.2a-d), 5 contracts KEPT.

- **Phase 9.1d/e/f/g DONE** — Physics Lab 잔여 4 sub-step (2nd + 3rd
  bundles per `docs/sessions/phase_mvp_a_handoff_2026_05_12.md` § 3).
  - **9.1d** (`ac1b675`): `ui/physics_lab/test_object_view.py` 신규 —
    `build_test_object_mesh(obj) -> pv.PolyData` (9 visual kind → pv.
    Sphere/Cube/Plane/Cylinder/Cone/Trihedral(merged plates)/Wall/
    Plane(20m ref)/Point(small sphere)). `TestObject3DPanel(QWidget)`
    가 pyvistaqt.QtInteractor 임베드. PhysicsLabWorkspace 가 viz 영역
    QStackedWidget (idx 0 = BouncingBallPlot, idx 1 = 3D panel). 3D
    panel 은 **lazy create** (첫 Test Object 클릭 시) — 워크스페이스
    생성 시 OpenGL 컨텍스트 안 만들어 headless CI 회피. `enable_3d_
    viewer=False` kwarg 로 강제 비활성 가능 (테스트 + CLI). domain 에
    `TestObject` Union 타입 alias 추가. `LibraryWidget.test_object_for
    (label)` 가 row label → TestObject dataclass 매핑. 14 신규 tests
    (10 mesh builder + 1 construction-only + 3 workspace integration).
    `tests/unit/ui/physics_lab/conftest.py` 가 `pyvista.OFF_SCREEN =
    True` 셋업.
  - **9.1e** (`10811a9`): `domain/physics_lab/time_modes.py` 신규 —
    `TimeMode` StrEnum (static/run/compare/sweep) + `TIME_MODES_IN_
    DISPLAY_ORDER` tuple. `BouncingBallPlot` 가 multi-curve 지원
    (`PRIMARY_CURVE = "primary"` + `add_overlay_curve / append_to /
    set_history_of / remove_overlay_curve / overlay_names`). `_Time
    Controls` Row 1 에 `Mode:` QComboBox 추가. `BouncingBallController.
    set_mode(mode)` 가 Static 시 transport disable + Compare 시
    `analytic_peak` overlay 추가 (한 bounce 당 closed-form peak 마커)
    + Sweep 시 4 sibling simulator (restitution=0.3/0.5/0.7/0.9) 동시
    실행 + 4 overlay curve. Play tick 이 sweep simulators 도 step.
    21 신규 tests (enum 2 + combo 2 + controller mode 3 + transport
    disable 2 + Compare overlay 2 + Sweep 4 + plot multi-curve 6).
  - **9.1f** (`46e1d64`): `domain/physics_lab/saved_experiments.py`
    신규 — `SavedExperiment` frozen dataclass + `write_/read_/list_
    saved_experiments` TOML I/O (manual write 통한 ``[experiment]`` +
    ``[parameters]`` 2 section, BOM strip + 5 validation). LibraryWidget
    가 QListWidget → **QTreeWidget** 변경 (3 top-level: Tests / Models
    / Saved Experiments). Tests = BOUNCING_BALL_ROW + 9 Test Objects;
    Models = `Gravity (always on)` + `Air Drag (toggle)` placeholders;
    Saved = `set_saved_experiments(experiments)` 로 동적 populate.
    `save_requested` / `experiment_selected(SavedExperiment)` 신규
    signal 2 종. PhysicsLabWorkspace `experiment_root: Path | None`
    kwarg 추가 + `save_current_experiment(name)` / `load_experiment
    (exp)` / `refresh_saved_experiments()` 메서드. `BouncingBallController.
    reset_with(*, gravity, restitution, height, velocity, drag)` 신규
    (load 시 simulator 교체). 5 신규 tests in test_workspace 갱신
    (list_widget → tree_widget). 31 신규 tests (16 saved_experiments
    도메인 + 15 LibraryWidget + workspace save/load).
  - **9.1g** (`46e1d64`): `BouncingBallSimulator` 에 `drag_coefficient_k:
    float = 0.0` 5번째 파라미터 추가. step() 가 `a_drag = -k * v *
    |v|` 적용 (quadratic drag, 0 이면 PL-D 동일 invariant). `set_drag_
    coefficient(value)` mid-run 변경 + 음수 reject. `@physics_param`
    decorator 5번째 추가 → BOUNCING_BALL_PARAM_SPECS 5 entries.
    AutoParametersWidget 자동 5번째 slider 생성. `_on_parameter_changed`
    dispatcher 가 drag 값 변경 시 simulator.set_drag_coefficient 호출.
    SavedExperiment + load_experiment 도 drag round-trip. Legacy
    file (drag 키 없음) 은 0.0 fallback. 11 신규 tests (zero-drag
    regression + dampened-peak invariant + validation + UI integration
    + SavedExperiment 통합 + legacy fallback). 기존 3 테스트 갱신 (4
    → 5 params).

  세션 누적 push: 9.1d (ac1b675) + 9.1e (10811a9) + 9.1f/g (46e1d64).
  9.1f 와 9.1g 는 같은 commit (작은 변경 묶음). 누적 1850 PASS
  (+77 across 9.1d-g), 5 contracts KEPT.

- **Phase 9.1a/b/c DONE** — Physics Lab Code Pane / Time controls /
  Parameters pane 본격화 (handoff `docs/sessions/phase_mvp_a_handoff_
  2026_05_12.md` § 3 의 1st bundle).
  - **9.1a** (`f07781f`): `ui/physics_lab/python_highlighter.py` +
    `tokenize_python_line(text, prev_state)` pure-Python categoriser
    + `PythonSyntaxHighlighter(QSyntaxHighlighter)` 10 카테고리
    (keyword/builtin/constant/self/string/comment/number/decorator/
    defname/classname). Triple-quoted string state 가 QSyntaxHighlighter
    block 간 전파. CodePreview 의 editor.document() 에 자동 부착.
    31 신규 tests (pure tokeniser 21 + palette 3 + Qt integration 3 +
    CodePreview integration 1 + Misc 3).
  - **9.1b** (`2bbce62`): BouncingBallController 에 frame history
    (list[BouncingBallState]) + cursor (_history_index) 추가.
    `step_forward_once / step_backward_once / seek_to_frame` 3
    method. Play 중 cursor mid-history 면 future truncate +
    새 timeline 생성. `_TimeControls` 가 2-row layout: Row 1
    Play/Pause/Stop + status, Row 2 Prev | Frame slider | Next |
    `"frame N / max"` readout. 14 신규 tests (history seed/forward/
    backward/seek-clamp/truncate-on-play/stop-clears/slider tracking/
    button-click routing/plot truncate/readout text).
  - **9.1c** (`7f94e31`): `domain/physics_lab/parameter_metadata.py`
    신규 — `PhysicsParam(frozen, slots)` dataclass + `@physics_param`
    decorator (`insert(0, param)` 로 source line order 유지) +
    `get_physics_params(func)` + `BOUNCING_BALL_PARAM_SPECS` (4 param
    선언: gravity_m_s2 linear [1,30] default 9.81 / restitution linear
    [0,1] default 0.70 / initial_height_m **log** [0.1,50] default 5 /
    initial_velocity_m_s linear [-20,20] default 0). Validation 4종.
    `ui/physics_lab/auto_parameters.py` 신규 — `AutoParametersWidget
    (params, parent)` 가 spec 1 개당 QSlider + QLabel row 생성.
    `parameter_changed(name, value)` signal + `current_value/set_value/
    slider_for/parameter_names/parameter_spec` API. linear/log tick
    mapping (`SLIDER_TICK_RESOLUTION = 100`). `ParametersWidget` 가
    `AutoParametersWidget(BOUNCING_BALL_PARAM_SPECS)` wrapper 로 변경,
    공개 API (`restitution_changed`, `current_restitution`,
    `set_restitution`, `slider()`) 보존 + 신규 (`auto_parameters()`,
    `parameter_changed(str, float)`) 노출. 36 신규 tests (decorator 13 +
    AutoParametersWidget 20 + ParametersWidget 신규 API 3).


- **PL-E (Code 즉석 수정) + 옵션 A (toolbar visibility) DONE** — 사용자
  요청 두 가지 동시 처리.
  - **옵션 A**: `MainWindow._refresh_sim_toolbars_visibility(workspace)`
    가 `selector.workspace_changed` 에 connect. Simulator 가 아닐 때
    `SimulationToolbar` + `TargetRunToolbar` setVisible(False). Editor /
    Physics Lab 에서 화면 정돈. 1 신규 test.
  - **PL-E**: `BouncingBallSimulator.set_step_override(StepFn | None)` +
    `update_state(BouncingBallState)` + `has_step_override` property +
    `_step_override` 사용 분기 in `step()`. reset 시 override 보존
    (사용자 iteration UX). `CodePreview` 가 read-only QTextEdit →
    Edit/Save && Reload/Revert 3 버튼 + status label 추가. Edit
    토글: 첫 클릭 시 자동으로 `_DEFAULT_USER_STEP` scaffold (built-in
    의 mutable 버전) 로 교체. `save_requested` / `revert_requested`
    Signal. `BouncingBallController.apply_user_step_code(source)`:
    `ast.parse` → `exec` → `step` 심볼 추출 → `simulator.set_step_
    override`. Play 중이면 자동 pause + reload + restart. 오류 (syntax
    / exec / no step) → `_post_code_status(msg, ok=False)` → CodePreview
    빨간 status. `revert_user_step_code()` 동일 흐름. 12 신규 tests
    (simulator 4 + UI 8: read-only default / Edit toggle scaffold /
    save+revert signal emit / apply 성공 / syntax error / no-step
    error / revert restores built-in / reset preserves override).
  - MVP_GUIDE rev8: § 6.4 코드 즉석 수정 사용 시나리오 + 공기 저항
    예시 코드.
  - 누적 **1690 PASS** (+13 신규). 5 contracts KEPT.
- **PL-D Bouncing Ball demo DONE** — Physics Lab 첫 인터랙티브 데모.
  사용자 우선순위 명시 (physics_lab > simulator > editor) 반영.
  plan/19 § 19.12.1 시나리오 실현.
  - `src/workbench/app/physics_lab/clock.py`: `PhysicsClock(dt_s)`
    + `ClockTick(dt_s, time_s, frame_id)` + `start/pause/stop/tick/
    run_for(n_frames, callback)`.
  - `src/workbench/app/physics_lab/bouncing_ball.py`:
    `BouncingBallSimulator(gravity_m_s2=9.81, restitution=0.7,
    initial_height_m=5.0, initial_velocity_m_s=0.0)` 1-D 수직 dynamics
    + semi-implicit Euler step + 충돌 시 restitution 적용 + bounce
    counter. `analytic_peak_height_m(h0, r, bounce)` closed-form
    reference (h_n = r^(2n) × h0). `set_restitution(v)` 슬라이더
    live update.
  - `src/workbench/ui/physics_lab/bouncing_ball_demo.py`: 4 신규
    widget + 1 controller.
    * `LibraryWidget` — `Bouncing Ball Demo` row + `default_library()`
      9 Test Objects 표시 (총 10 row).
    * `CodePreview` — `inspect.getsource(BouncingBallSimulator.step)`
      을 read-only QTextEdit 에 표시 (Consolas font).
    * `BouncingBallPlot` — pyqtgraph PlotWidget y(t) 곡선 + grid +
      축 label (m, s) + `append(t, y)` / `set_history` / `clear_history`.
    * `ParametersWidget` — Restitution QSlider 0..100 ticks
      (1% 단위) + readout + `restitution_changed(float)` signal.
    * `BouncingBallController(plot, parameters, play/pause/stop btn,
      status_label, clock_dt_s)` — QTimer 가 16ms 마다 tick → clock
      tick → simulator step → plot append + status refresh. Play /
      Pause / Stop 라우팅 + slider → simulator.set_restitution 연결.
      `step_once(dt_s)` headless helper (test 가 QTimer 없이 호출).
  - `PhysicsLabWorkspace.__init__` 가 PL-B placeholder 4 종 교체 →
    실 widgets + controller. Accessor 갱신.
  - 38 신규 tests: clock 8 (default / pause / tick / run_for /
    validation) + bouncing_ball 16 (constructor 검증 4 / physics 5 /
    reset / step 검증 / analytic_peak_height 3 / closed-form
    invariant: lossless ball + free-fall time) + bouncing_ball_demo
    14 (Library 10-row / CodePreview / Plot append+clear /
    Parameters slider+signal / Controller integration: seed +
    step_once + play/pause / stop reset / slider → simulator).
  - 누적 **1677 PASS** (+38 신규). 5 contracts KEPT.
- **PL-A + PL-B + PL-C (3rd workspace + Test Objects 9) DONE**
  - `WorkspaceSelector.Workspace.PHYSICS_LAB` 추가 + `WORKSPACE_ORDER`
    tuple + toggle 3-way + Ctrl+Shift+L 단축키 (MainMenuBar 단독).
  - `ui/physics_lab/workspace.py` — `PhysicsLabWorkspace` QSplitter
    Library/Code+Viz/Parameters + bottom Time controls.
  - `domain/physics_lab/test_objects.py` — 9 frozen dataclass
    (Sphere/Cube/Plate/Cylinder/Cone/Trihedral/Wall/Plane/Point)
    + analytic_rcs_m2(wavelength_m) (Phase 5.9 RCS 공식 재사용 +
    Cone Knott tip-on 신규).
  - `default_library()` factory (X-band 적정 크기 1 객체/kind).
  - `cli/main.py` `trsim ui --workspace physics_lab` 추가.
  - 25 신규 tests. 누적 **1639 PASS**.
- **Floating dock 옵션 D (Detachable bottom tabs) DONE** — 플랜
  외 MVP+α 영역에서 가장 작은 변경으로 가장 큰 UX 개선. plan/05
  § 5.2 / plan/13 § 13.2 의 fixed QSplitter layout 은 유지하면서
  Simulator workspace 의 하단 tabs (Run/StageIO/Profiler/NN
  Step1/Step2/Training + DLC) 를 detach 가능하게 만듦.
  - `src/workbench/ui/widgets/detachable_tab.py` 신규: `FloatingPanel`
    (QMainWindow subclass, 닫힐 때 takeCentralWidget + content.setParent
    (None) 으로 원본 widget 보존 + `closed` signal emit) +
    `DetachableTabWidget` (QTabWidget subclass, tabBar 우클릭
    context menu "Detach tab" → 새 FloatingPanel 만들어 show, panel
    closed signal → 원래 index 로 insertTab 복귀). `tab_detached`
    / `tab_reattached` signal 2 종. `floating_panels()` property.
  - `src/workbench/ui/widgets/__init__.py` 신규 (re-export).
  - `SimulatorWorkspace.bottom_tabs` 가 `QTabWidget` → `DetachableTabWidget`
    교체. 기존 사용처 (`addTab`, `tabText`, `widget`) 인터페이스 동일,
    유일한 차이는 우클릭 context menu 등장.
  - 7 신규 tests: tab properties 보존 / detach removes from tabs +
    emits signal / out-of-range index no-op / FloatingPanel 메타데이터
    / 닫기 시 re-insert + signal / count shrink 시 clamp / 다중
    동시 floating.
  - MVP_GUIDE rev6 갱신: § 3.5b 신규 "tab 떼어내기" 안내 (tabBar
    우클릭 + 창 닫기 re-attach), § 6 checklist 갱신.
  - 누적 **1612 PASS** (+7 신규). 5 contracts KEPT.
- **A2 후속 (Step1→Step2 auto-refresh) DONE** — 사용자 보고: Step 1
  빌드 후 Step 2 dataset combo 가 비어있음. SimulatorWorkspace 가
  cwd/datasets 를 `__init__` 시점에 한 번만 scan → Step 1 빌드 *후*
  새 .h5 가 생겨도 보이지 않음. 두 가지 경로로 해결.
  - **자동 refresh**: `Step1DatasetPanel.build_completed = Signal()` 추가.
    `NNStep1Controller._run_single` + `_run_chain` 가 success 시 emit
    (chain 의 경우 manifest 가 None 이 아닐 때만). `NNStep2Controller.
    _last_datasets_root` + `refresh_datasets()` 메서드 (root 재 scan,
    dataset 갱신 + combo refresh). `SimulatorWorkspace` 가 `step1_panel.
    build_completed.connect(step2_controller.refresh_datasets)` wire.
  - **수동 refresh**: `Step2EvalPanel.refresh_requested = Signal()` +
    "Refresh datasets" 버튼 (Run Evaluation 옆). controller 가
    connect 후 refresh_datasets 호출. 외부에서 `.h5` 떨궜을 때 대비.
  - 5 신규 tests: refresh picks up new file / refresh count / no-root
    no-op / panel refresh_requested signal / workspace end-to-end
    (Step 1 빌드 → Step 2 combo 자동 등장).
  - MVP_GUIDE rev5 갱신: § 5.4 의 "dataset 콤보 비어있을 때" 안내가
    rev5 자동 refresh 흐름 반영. § 7 실패 대처표 2 행 갱신
    (빌드 전 비어있음 vs 빌드 후도 비어있음). 누적 **1601 PASS**
    (+5 신규). 5 contracts KEPT.
- **A1 + A2 (MVP NN UX 완성) DONE** — 사용자 NN 전체 흐름이 Python
  fallback 없이 GUI 만으로 가능.
  - **A1 TrainingPanel backend toggle**: `_BACKENDS` literal
    `("numpy_mlp", "fake")` + `Backend` QComboBox row + `current_
    backend()` / `set_backend(id)` API. Default = `numpy_mlp` (real
    gradient descent). `NNTrainingController._on_train` 가 `panel.
    current_backend()` → `TrainerService(backend=...)` 전달. 로그에
    `Training started: <job_id> (backend=<backend>)` 출력. 예외 catch
    에 `FileNotFoundError` 추가 (numpy_mlp 가 missing dataset 일 때).
    6 신규 tests (panel combo count / default numpy_mlp / set_backend
    round-trip / unknown reject / fake log / numpy_mlp end-to-end with
    synthetic HDF5 / numpy_mlp missing dataset error).
  - **A2 Step 2 default register**: `NNStep2Controller.register_default_
    setup(*, datasets_root, builtin_plugins=True)` — `datasets_root /
    "*.h5"` glob scan 후 stem 으로 등록 + `NumpyPairingNN` 자동 등록
    (`"numpy_pairing_nn"` 키). 이미 등록된 plugin 은 skip
    (double-register 방지). `SimulatorWorkspace.__init__` 가
    `nn_datasets_root=<cwd>/datasets` (default) 으로 호출 — `trsim ui`
    가동 시 cwd 의 datasets/ 자동 scan + plugin 자동 등록. test 격리는
    `nn_datasets_root=None` 으로 가능 (sentinel `_NN_DATASETS_DEFAULT`).
    7 신규 tests (controller default plugin / dataset scan / missing
    root skip / builtin_plugins=False / no double-register / workspace
    auto-register / workspace explicit datasets_root).
  - `docs/MVP_GUIDE.md` rev4 갱신: § 5.3 Python fallback 제거 → GUI
    Backend 콤보 안내. § 5.4 Python fallback 제거 → 자동 등록 plugin
    +cwd scan 안내. § 7 실패 대처표 2 행 갱신 (numpy_mlp missing
    dataset / Step 2 dataset combo 비어있음). 누적 **1596 PASS** (+13
    신규: A1=6, A2=7). 5 contracts KEPT.
- **TOML BOM tolerance + MVP_GUIDE PowerShell 5.1 fix DONE** — 사용자
  MVP_GUIDE § 4.1 의 `Out-File -Encoding utf8` 가 PowerShell 5.1 에서
  UTF-8 **BOM** 으로 저장 → tomllib 가 `Invalid statement (at line 1,
  column 1)` 거부 → DLC tab silent fail. `domain/dlc/manifest.py` 의
  `load_manifest_from_toml` + `domain/nn/variant_manifest.py` 의
  `load_variants_manifest` 가 read_bytes → BOM strip (`b"\\xef\\xbb\\xbf"`
  prefix 검사) → `tomllib.loads(decode("utf-8"))` 으로 변경.
  UnicodeDecodeError 는 ValueError("not valid UTF-8") 로 wrap.
  3 신규 tests (DLC manifest BOM 통과 / DLC manifest cp949-like
  invalid UTF-8 reject / variants manifest BOM 통과). `docs/MVP_GUIDE.
  md` § 0.0 갱신 (uv venv `No module named pip` 대처 3-way),
  § 4.1 PowerShell 명령 `[System.IO.File]::WriteAllText` +
  `UTF8Encoding($false)` 로 변경 (BOM 없는 UTF-8), § 4.3 user
  resource 명령 동일 변경, § 7 실패 대처표 2 행 추가. 누적 **1583
  PASS** (+3 신규). 5 contracts KEPT.
- **DLC silent-fail fix DONE** — 사용자 MVP_GUIDE § 4.1+4.2 따라 sample
  DLC 만들었지만 tab 안 등장. 두 가지 root cause:
  - **PluginLoader slash-path 미처리**: plan/17 § 17.2.4 표준이
    `"ui/diagnostic_panel:Panel"` 같은 slash 형식이지만
    `_import_from_package_root` 가 `module_name.split(".")` 만 했음.
    이제 `module_name.replace("\\\\", "/").replace("/", ".").split(".")`
    으로 normalize. Windows 백슬래시도 처리. `unique_name` 도 dot
    형식으로 통일해 sys.modules 충돌 회피. 2 신규 tests (slash 경로
    success + backslash 경로 success).
  - **load_errors silent suppression**: PackageManager + PluginLoader
    + SimulatorWorkspace 의 `load_errors` / `dlc_mount_errors` 가
    누적되지만 `trsim ui` 가 stderr 출력 안 함. 사용자는 왜 DLC 안
    뜨는지 알 길 없음. `cli/main.py` 의 `build_ui_window` 가
    `_report_dlc_load_errors` + `_report_simulator_mount_errors` 호출 —
    package error (`[trsim ui] package error <path>: <msg>`), plugin
    error (`[trsim ui] plugin error <pkg>/<slot> -> <target>:
    <msg>`), panel mount error (`[trsim ui] panel mount error <pkg>:
    <msg>`) 모두 stderr 로 echo. 2 신규 tests (잘못된 TOML → package
    error / 존재하지 않는 entry_point module → plugin error). 누적
    **1580 PASS** (+4 신규). 5 contracts KEPT.
- **MVP UI gap fix DONE** — 사용자 MVP_GUIDE 검증에서 발견된 2 개
  진짜 누락점 해소.
  - **단축키 충돌 해소**: toolbar QAction `setShortcut` + standalone
    `QShortcut` 제거. `MainMenuBar` 가 Ctrl+Shift+E/S/P 단독 소유
    (plan/05 § 5.1 "All actions are Command"). Qt ambiguous-shortcut
    suppression 회피. 2 tests 갱신: toolbar QAction.shortcut() ==
    QKeySequence() 빈 검증 + `MainMenuBar` 의 `MenuAction_workspace.
    switch_to_editor/simulator` + `MenuAction_palette.open` 가 정확한
    shortcut 보유 검증.
  - **NN mode UI 진입경로 추가** (Phase 4.11 잊혀진 통합 회수):
    `SimulatorWorkspace.__init__` 가 `Step1DatasetPanel +
    NNStep1Controller`, `Step2EvalPanel + NNStep2Controller`,
    `TrainingPanel + NNTrainingController` 인스턴스 생성 후 bottom_
    tabs 에 "NN Step 1" / "NN Step 2" / "NN Training" 3 tab 추가
    (Run / Stage I/O / Profiler 옆). DLC panel 들은 tab index 6+
    으로 자동 밀림. nn_step1/2_panel/controller + nn_training_panel/
    controller 6 accessor 노출. 영향 tests: workspace bottom tab
    titles 검증 갱신, DLC mount 의 tabText(3) → tabText(6) 일괄
    갱신, profiler_panel test 가 첫 3 tab 만 확인하도록 완화. 5 신
    tests (panel instantiate / controller wiring / 3 tab 위치 검증 /
    build_requested → end-to-end HDF5 작성 / training panel
    objectName preserve). 누적 **1576 PASS** (+6 신규: shortcut
    menu-bar assert 1 + nn-mode 5). 5 contracts KEPT.

- **MVP wrap-up DONE** — CLI ui DLC 자동 로드. `src/workbench/cli/
  main.py`: `ui` subparser 에 `--no-dlc` flag + `--workspace` 유지 +
  `build_ui_window(args) -> MainWindow` factory 분리 (event loop 진입
  없이 testable) + `_cmd_ui` 가 `build_dlc_runtime()` (default ~/.
  trsim/) 로 DLCRuntime 자동 mount → MainWindow(dlc_runtime=...).
  `docs/MVP_USAGE.md` 신규 (8 섹션: 환경 / UI 가동 / NN dataset /
  학습 / 평가 / DLC 만들기 / 비-UI CLI / 검증). README.md status
  부분 갱신. 5 새 tests (parser default / simulator workspace /
  --no-dlc flag / no-dlc 시 dlc_runtime None / paths injected via
  monkeypatch). 누적 **1570 PASS** (+5 신규). 5 contracts KEPT.

- **Task D (Simulator panel mount) DONE** — plan/17 § 17.4.4 +
  plan/05 § 5.2. `src/workbench/ui/simulator/workspace.py`:
  `SimulatorWorkspace(*, panel_registry: PanelRegistry | None = None)`
  생성 시 panel_registry 가 있으면 자동으로 `get_panels_for_workspace
  ("simulator")` 호출 → `mount_dlc_panels(registrations)` 가 각
  registration.panel_class(self) 인스턴스 생성 → bottom_tabs.addTab
  with "[DLC] <pkg>: <Class>" 라벨 (source_package_id 비어있으면
  "[DLC] <Class>"). 생성자 예외 / non-QWidget 반환 모두
  `DLCMountError` 로 누적 (frozen dataclass: registration + message)
  + 다른 panel 진행 — 하나 깨져도 workspace 자체는 살아있음.
  `dlc_panels` / `dlc_mount_errors` property 노출. `src/workbench/
  ui/main_window.py` 가 `dlc_runtime.panel_registry` 를
  `SimulatorWorkspace(panel_registry=...)` 로 주입. 11 tests in
  `tests/unit/ui/simulator/test_workspace_dlc_mount.py` (no-registry
  default / 1 panel happy path / 2-panel 순서 / editor-tagged skip /
  empty pkg label / raise constructor isolate / non-QWidget reject /
  mixed good+bad / explicit mount API / QLabel subclass accept) +
  `test_main_window_dlc.py` 에 main_window 통합 1 추가 (DLC plugin
  end-to-end SimulatorWorkspace 까지 라우팅). 누적 **1565 PASS**
  (+11 신규). 5 contracts KEPT.
- **Task C (Real TrainerService numpy MLP backend) DONE** — plan/07
  § 7.5.3. `src/workbench/app/nn/numpy_mlp.py`: pure numpy MLP helper —
  `NumpyMLPParams` (mutable list weights/biases + Activation Literal),
  `Activation = Literal["relu","tanh"]`, `init_params(layer_dims, *,
  activation, rng_seed)` He init (ReLU) / Xavier (tanh), `forward(params,
  x) → Y_pred` (last layer linear), `mse_loss(pred, target)` mean over
  batch + features, `train_one_epoch(params, x_train, y_train, *,
  learning_rate, batch_size, rng) → post-update loss` mini-batch SGD
  in-place update, `flatten_inputs / flatten_labels(spec, mapping, n)`
  complex → (re, im) concat 후 (N, D) float32 행렬. `src/workbench/app/
  nn/trainer.py` 의 `TrainerService(*, epoch_callback=None, backend:
  TrainingBackend="fake", rng_seed=0)` 추가, `TrainingBackend = Literal[
  "fake","numpy_mlp"]`. backend="numpy_mlp" 분기: read_dataset →
  flatten → split (train/val by job fractions, seed reproducible) →
  init_params(layer_dims=(D_in, *job.hidden, D_out)) → epoch loop
  (train_one_epoch + val mse + best_val/early_stopping) → weights
  `.npz` 에 layer_i_W + layer_i_b 저장 (fake 의 layer_i 와 다른 키).
  fake backend (Phase 6.7) 그대로 유지 (default). 22 새 tests (helper
  14 + trainer backend 8): layer shape / He init scale / dim 검증 /
  seed 재현 / forward zero-weights / mse loss / 합성 linear data 위
  1 epoch + 50 epochs loss 감소 / mismatched axes / non-positive lr /
  complex flatten / int → float32 / wrong leading axis; default backend
  fake 검증 / numpy_mlp 가 missing dataset reject / weights save layer_
  i_W key / val_loss 감소 / epoch callback signature / early stop 발산
  trigger (warnings filtered) / 0-sample reject / seed 재현. 누적
  **1554 PASS** (+22 신규). 5 contracts KEPT.
- **Task B (Variant build runner) DONE** — plan/07 § 7.4.5a.
  `src/workbench/app/nn/variant_runner.py`: `VariantBuildPlan` frozen
  (variant + dataset_filename + scenario + frames, 2 validation) +
  `VariantBuildResult` frozen (plan + dataset_path + frames_executed +
  cancelled) + `standard_pairing_build_plans(target_count, frames_per_
  variant, scenario=None)` 4-tier preset (A/B/C/D 동일 scenario 공유) +
  `VariantBuildRunner(*, spec, plans, output_root, manifest_filename=None,
  dataset_id_prefix="", progress_callback=None)` chain build (per-variant
  DatasetBuilder + PipelineRunner.run_pairing_dataset + builder.finalize
  → VariantEntry 누적 → VariantsManifest 생성 + write_variants_
  manifest, 0 entries 면 manifest=None 반환). cancel() 가 current
  builder 까지 propagate. 18 tests (plan validation 3 / preset 4 /
  runner constructor 2 / happy path 5 / cancellation 3 / manifest_path
  surface 1). `src/workbench/ui/simulator/nn_mode/step1_dataset.py`:
  `Step1BuildMode` StrEnum (SINGLE / CHAIN_4VARIANT) + 새 "Build mode"
  combo row + `current_build_mode()` / `set_build_mode()` 접근자.
  `step1_controller.py` 가 mode 별 `_run_single` (기존) vs `_run_chain`
  (output_path → output_root, standard_pairing_build_plans, manifest
  + 4 dataset 로그). Cancel 도 variant_runner 우선 처리. 9 신규 tests
  (panel default mode / chain 4×h5 + manifest / per-variant id /
  log summary / status done / 2 validation / SINGLE 모드 복귀
  round-trip). 누적 **1532 PASS** (+27 신규). 5 contracts KEPT.
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

### 3.6 MVP 매트릭스 자동 갱신 (모든 sub-step push 직후)

`docs/MVP_STATUS.md` 가 plan/04 § 4.3 의 Phase 0~9 list vs 실제 구현
상태 매트릭스. **매 sub-step push 직후 해당 행을 갱신**하고 follow-up
commit (`docs: update MVP_STATUS — <항목> ✓ after <sub-step>`) 로
같은 push 에 묶어 origin/main 으로 보냄. 자세한 절차는
[`docs/agent_workflows/mvp_status_update.md`](docs/agent_workflows/mvp_status_update.md).

상태 마크: ✓ (완전) / △ (skeleton·placeholder 만, 실 데이터 binding
또는 CLI 미완) / ✗ (미구현). § "변경 이력 footer" 에 한 줄 append.

새 작업 결정 시 `docs/MVP_STATUS.md § "미구현 우선순위 리스트"` 가
첫 참조. 매트릭스의 ✓/△/✗ 가 실제 코드와 어긋나면 신뢰가 깨지니
의심 시 `grep` + `Glob` 으로 cross-check 후 정정.

## 3.5 셸 문법 — 사용자 환경은 **PowerShell**

handoff / 인계 / 사용자에게 명령 제시할 때는 PowerShell 우선:

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"
& $PY -m pytest -q
```

Bash (`VAR=value cmd`) 한 줄 prefix 패턴은 PowerShell 에서 cmdlet
인식 실패 (`PYTHONUTF8=1 ... CommandNotFoundException`). 반드시
`$env:VAR = "value"` 별도 줄 + `& $exe args` call operator 로 분리.

내가 Bash 도구로 실행할 때는 `PYTHONUTF8=1 ... "$PY" ...` Bash
문법이 동작하지만, **사용자에게 보여주는 명령**은 PowerShell 변형이
기본. 두 셸 모두 필요하면 둘 다 표시 (PowerShell 우선).

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
| "다음 작업?", "남은 작업?", "MVP 상태?", sub-step push 직후 | `docs/agent_workflows/mvp_status_update.md` | `docs/MVP_STATUS.md` 매트릭스 갱신 + 우선순위 리스트 참조 |

**중요 도구 위치**:
- Phase dashboard artifact id = `trsim-phase-dashboard` (cowork 사이드바)
- Scheduled task = `trsim-ci-status` (사용자 OneDrive\Claude\Scheduled\)
- pre-commit hook = `scripts/githooks/` (사용자 PC 에서 setup_hooks.sh 1회)

새 트리거 추가 시 워크플로 .md + 위 표에 한 줄.

---
최근 갱신: 2026-05-14 — Phase 4 L3 (Simulator RD panel pyqtgraph live heatmap) DONE, 2607 PASS. Simulator 8 panel 중 세 번째 실 데이터 binding.
