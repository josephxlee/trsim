# Phase 9 M1-M3 + Phase 4 L1-L5 + sidequests (2026-05-13 자동 모드)

사용자 결정 "내일 아침 6:00 까지 자동 진행" 에 따라 진행한 1 세션
10 commit 묶음. 우선순위 #1 (Validation Bench 일반화) **종결**,
우선순위 #2 (Simulator panel 잔여 5 binding) 의 frame-level wiring
완료, 사이드 quest 3 종 (#7 reproducibility / #9 SDK manifest move /
#6 Profile mode toggle) 처리.

HIL 제외 결정 (사용자: "MVP 공간만, 실 작업 ✗") 가 이 세션 첫 commit
(`43c2759`) 로 우선순위 리스트에 반영됨.

---

## 1. Phase 9 M1+M2+M3 — Validation Bench 일반화 종결

`BouncingBallController.run_validation_from_dataset` 가 PL-9.2c 부터
BouncingBall 만 지원했었음. 이번 cycle 로 임의 PhysicsModelProtocol
plug-in 도 GUI 에서 measured dataset 으로 validate 가능.

### M1 — generalised layer (`b733608`)

- `src/workbench/app/physics_lab/validation_runner.py` 신규.
- `simulate_dynamic_for_validation(model, params, *, initial_state,
  dt_s, t_end_s, x_field="time_s", y_field)` — dynamic 모델 step
  loop, 매 step 마다 ``(state[x_field], state[y_field])`` 수집.
- `sweep_static_for_validation(model, params, *, x_values, x_field,
  y_field)` — static 모델 ``params[x_field]`` override + compute({})
  결과의 ``y_field`` 추출.
- `run_validation_for_model(model, *, params, measured_x, measured_y,
  y_field, x_field=None, initial_state=None, dt_s=None)` —
  ``model.time_mode`` 로 자동 dispatch + 5 validation rule.
- `ValidationRun` frozen dataclass (metrics + sim_x + sim_y) — UI
  callers 가 1 call 로 metrics + overlay 둘 다 받음.
- 17 신규 tests (GravityOnly closed-form / BouncingBall bounce /
  FSPL 20log10 / dispatch / 7 error / ValidationRun).

### M2 — BouncingBall delegation (`afc52a2`)

- `BouncingBallController.run_validation_from_dataset` 가 M1 layer 위임
  으로 단순화. obsolete `_simulate_for_validation` (~25 줄) 제거.
- BouncingBallSimulator.step 과 BouncingBallModel.compute 가 비트
  동일 알고리즘이므로 PL-9.2c GUI 동작은 동일.
- 1 parity regression test (controller path == 직접 layer 호출 결과
  1e-12 일치).

### M3 — 임의 PhysicsModelProtocol UI dispatch (`3fdd9ff`)

- `src/workbench/domain/physics_lab/validation_defaults.py` 신규
  (`default_validation_fields` — 3 built-in 모델 매핑).
- `PhysicsLabWorkspace`:
  - `LibraryWidget.physics_model_selected` 신호 연결.
  - `_current_physics_model` track.
  - `_on_measured_dataset_selected` 분기 — BouncingBall = legacy
    path, else `_run_generic_validation`.
  - `_run_generic_validation` = defaults 룩업 + PhysicsParam.default
    로 params dict 생성 + `run_validation_for_model` + 새 public
    `BouncingBallController.install_validation_overlay` + status bar.
- 9 신규 tests (4 defaults + 5 workspace dispatch).
- plan/19 § 19.7.5+ "Validation Bench 일반화" 우선순위 #1 **closed**.

**누적 영향**: 2518 → 2545 PASS (예상, +27).

---

## 2. Phase 4 L2-L5 — Simulator panel 실 데이터 binding 잔여

L1 (Run panel sim_t/frame_id) 직후의 cycle. 사용자 "Simulation 가장
시급" 명시 → physics_lab 종결 후 곧장 simulator panel wiring.

### L2 — PluginManager baseline (`e504df1`)

- `src/workbench/ui/simulator/builtin_pipeline_plugins.py` 신규.
- `BUILTIN_SIMULATOR_PLUGINS` 매핑 (5 stage curated baseline):
  Detector / Pairing / Tracker 채우고 Predictor / Classifier 는 비움
  (Phase 6 후속 plug-in 대기).
- SimulatorWorkspace `_populate_builtin_pipeline_plugins` init 후
  자동 호출.
- 5 신규 tests.

### L3 — FFT/RD/StageIO frame fan-out (`bda4d51`)

- `SimulatorRunController.tick_completed(sim_t_s, frame_id)` 시그널
  을 SimulatorWorkspace `_on_run_tick_completed` 가 받아 FFT panel
  / RD panel / StageIO panel 의 ``set_frame(frame_id)`` 호출.
- 4 panel (Run + FFT + RD + StageIO) frame_id lock-step 보장.
- 5 신규 tests (default "frame: -" / 단일 tick / pause invariant /
  stop replay / 5-tick lock-step).

### L4 — Properties live snapshot + selection pin (`d715c68`)

- 같은 tick handler 가 Properties panel 도 paint (sim_t_s / frame_id
  / state / speed 4-row form).
- 신규 public API `show_selected_in_properties(label, properties)` /
  `clear_property_selection()` — 향후 Scene3D selection 이 hook 할 때
  tick handler 가 안 덮어쓰게 하는 `_properties_owned_by_selection`
  플래그.
- 5 신규 tests.

### L5 — StageIO 6-box placeholder text (`66960b9`)

- 같은 tick handler 가 StageIO 6 box (Transmitter / Environment /
  Receiver / Detector / Pairing / Tracker) IN/OUT 자리에 deterministic
  placeholder text 채움 (frame_id + sim_t_s 인코딩).
- Detector / Pairing / Tracker 는 "pipeline pending" 명시 — 실
  pipeline 후 swap.
- 4 신규 tests.

**누적 영향**: +23 신규 tests across L2-L5.

**남은 panel 작업**: FFT 의 실 spectrum / RD 의 실 heatmap data
binding 은 실 pipeline 후 후속. 현재 위치 = MVP_STATUS Phase 4 row
가 "Run ✓ L1; PluginManager ✓ L2; FFT/RD/StageIO frame_label ✓ L3;
Properties ✓ L4; StageIO 6 box ✓ L5" 까지 진행.

---

## 3. Sidequest 3 종

### #7 Phase 5 #18/#19 reproducibility (`d833889`)

plan/04 § 4.3 Phase 5 list 의 reproducibility 검증 missing 항목.
PerformanceClock + FrameProfiler 둘 다 pure-deterministic 이라
golden-replay 패턴으로 증명.

- `tests/unit/app/timing/test_reference_timing_reproducibility.py`
  신규 (9 tests).
- PerformanceClock: factory 동일 args → 동일 state / round-trip
  ms↔Hz / cross-validation.
- FrameProfiler: 동일 sequence → 동일 report / 순서 independent /
  reset replay invariant / 손계산 percentile golden (3.0 mean / 4.8
  p95 / 4.96 p99 on 1..5 ms 샘플).
- test-only; production code 변경 0.

### #9 SDK manifest.py 이동 (`cf0f57e`)

plan/02 § 2.6b — SDK 가 DLC author 의 단일 surface. manifest 가
Phase 7.1 부터 `workbench.domain.dlc.manifest` 에 살았는데 SDK
일관성 위해 이동.

- `src/workbench/sdk/manifest.py` 신규 + `sdk/__init__.py` 5 symbol
  re-export.
- `src/workbench/domain/dlc/` 패키지 전체 삭제.
- 6 callers 갱신 (app/dlc/installer.py, app/dlc/package_manager.py,
  io/package_io.py, sdk/package_validator.py, app/nn/trainer.py 의
  docstring, app/dlc/__init__.py 의 docstring).
- `tests/unit/domain/test_dlc_manifest.py` → `tests/unit/sdk/test_
  manifest.py` 이동 (git mv) + import 갱신.
- integration test 갱신.
- Contract 1 (UI → App → SDK → Domain → Physics) 유지 — chain
  단축됨 (app/dlc/* → sdk/manifest 가 app → sdk 이라 OK).

### #6 Phase 3 Profile mode toggle (`5ce10d2`)

plan/04 § 4.3 Phase 3 의 마지막 △ 항목. plan/18 § 18.17.5 specifies
3-way switch.

- `src/workbench/domain/timing/profile_mode.py` 신규 — ProfileMode
  StrEnum (OFF / EXPLICIT / LIVE) + DEFAULT_PROFILE_MODE = OFF +
  PROFILE_MODES_IN_DISPLAY_ORDER tuple + `parse_profile_mode` helper
  (case-insensitive, strip whitespace).
- CLI:
  - `trsim run --profile-mode {off,explicit,live}` default off.
  - `trsim profile --profile-mode {explicit,live}` default explicit
    (off 거부 — 목적과 충돌).
  - run command 가 manifest metadata 에 profile_mode 기록.
- 16 신규 tests (9 enum + 7 CLI).
- Pipeline / probe runtime gating 은 Pipeline.step 본격 wire 후 후속.

---

## 4. 누적

| 영역 | commit | 신규 tests (예상) |
|---|---|---|
| HIL 우선순위 제외 | `43c2759` | 0 |
| Phase 9 M1 | `b733608` | +17 |
| Phase 9 M2 | `afc52a2` | +1 |
| Phase 9 M3 | `3fdd9ff` | +9 |
| Phase 4 L2 | `e504df1` | +5 |
| Phase 4 L3 | `bda4d51` | +5 |
| Phase 4 L4 | `d715c68` | +5 |
| Phase 4 L5 | `66960b9` | +4 |
| Sidequest #7 | `d833889` | +9 |
| Sidequest #9 | `cf0f57e` | 0 (refactor, 동일 test 재배치) |
| Sidequest #6 | `5ce10d2` | +16 |
| 세션 핸드오프 doc | `da70f65` | 0 |
| Editor Composer wiring | `3b0f30a` | +3 |
| **합계** | 12 commit | **+74 tests** |

직전 검증 라인 = 2518 PASS (L1 기준). 사용자 PC 검증 후 = **2592
PASS** 예상.

ruff / py_compile / format 전부 통과. mypy --strict / pytest /
import-linter 검증은 사용자 PC 에서 (sandbox 에 numpy / pytest /
PySide6 없음).

---

## 5. 다음 cycle 후보 (우선순위 갱신)

이 세션이 #1 / #6 / #7 / #9 + #2 의 frame-level wiring 종결. 남은
잔여:

| 우선 | 작업 | 크기 | 비고 |
|---|---|---|---|
| 1 | **Simulator FFT/RD 실 spectrum/heatmap data binding** | 중-대 | 실 pipeline 필요. PairingScenarioSpec + PipelineRunner 와 SimulatorRunController 결합. |
| 2 | **Editor 5 activity 실 데이터 binding** | 대 (multi cycle) | Composer + Map + Radar + Targets + Atmosphere → ResourceLibrary round-trip. AtmospherePanel 은 이미 self-contained. |
| 3 | **Phase 6 Step 2 per-category dispatch** (Tracker / Predictor / Classifier loss) | 중 | A1-c stub. NN plug-in 출시 후. |
| 4 | **Phase 6 multi-step rollout RMSE** | 중 | A1-d stub. Sequence dataset spec + Predictor NN. |
| 5 | **Phase 4 UI 잡** (방향키 / Mode 전환 UI / 단축키 정책) | 소 | △. workspace 안 키 routing 정리. |
| 6 | **Polish** (Floating dock 옵션 B / Theme manager / Stone Soup adapter) | 소 | 미루기 OK. |

다음 세션 시작 시 `docs/MVP_STATUS.md § "미구현 우선순위 리스트"` 가
권위. 본 핸드오프는 backfill.

---

## 6. 사용자 PC 검증 명령 (PowerShell)

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

# pytest (예상 2589 PASS)
& $PY -m pytest -q

# mypy --strict — 전체
& $PY -m mypy --strict src/workbench

# import-linter (5 contracts)
& $PY -m lint_imports
```

manifest 이동이 가장 risky — `lint_imports` 가 Contract 1 / Contract
4 통과 확인 필수.

---

## 7. 한 줄 인계

> 우선순위 #1 (physics_lab Validation Bench 일반화) closed + #2 frame-
> level wiring 완료. 다음 사람: FFT/RD 실 spectrum data binding 또는
> Editor activity binding 중 선택.
