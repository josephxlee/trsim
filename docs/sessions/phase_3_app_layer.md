# Phase 3 — App layer (DONE)

## Status
- 날짜: 2026-05-09
- CI: push 후 확인 (마지막 commit `7be1c2a`).
- Phase 0+1+2+3 누적 test: 820 (+161 from Phase 3).

## Commits (this session)

| Commit | Sub-phase | New tests |
|---|---|---|
| `10bab83` | 3.1 EventBus + CommandBus + command_registry | 28 |
| `51abcd8` | 3.2 SimulationClock + InputBuffer + RunManager + ProbeRecorder | 31 |
| `ce73329` | 3.3 ResourceLibrary + ResourceCache + ScenarioService | 23 |
| `2e433cb` | 3.4 io/run_storage + io/trace_storage | 13 |
| `927c131` | 3.5 plugin_loader + plugin_scanner | 14 |
| `994e9ec` | 3.6 timing/{performance_clock,frame_boundary,probe,profiler} | 22 |
| `7be1c2a` | 3.7 cli/main — trsim run / profile | 7 |

Plus `Phase 2` ALL DONE doc commit `ec81de5` was the prior session boundary.

## Modules (Phase 3 surface)

`src/workbench/app/`:
- `event_bus.py`, `command_bus.py`, `command_registry.py`
- `simulation_clock.py`, `input_buffer.py`, `run_manager.py`, `probe_recorder.py`
- `resource_library.py`, `resource_cache.py`, `scenario_service.py`
- `plugin_loader.py`, `plugin_scanner.py`
- `timing/performance_clock.py`, `timing/stage_timing_probe.py`,
  `timing/frame_boundary_detector.py`, `timing/frame_profiler.py`

`src/workbench/io/`:
- `run_storage.py` (RunManifest JSON), `trace_storage.py` (npz)

`src/workbench/cli/main.py` + `src/workbench/__main__.py` (re-export).

## Conventions / 결정

- **Single Command Path** — `CommandBus.dispatch` is the only entry to
  state-changing operations. TRACKER-sourced `Command` instances enforce
  `source_track_id + source_frame_id` at construction.
- **JSON over TOML** for `RunManifest` — `tomli_w` is in the optional
  sdk extra; manifest is machine-only data.
- **npz for traces** — stdlib + numpy; HDF5 reserved for MVP+alpha.
- **AST scan precedes plugin load** — `plugin_scanner.scan_plugin_file`
  must pass (`is_isolated == True` for the configured forbidden list)
  before `plugin_loader.load_plugin_module` runs.
- **Warmup discard** for FrameProfiler — first 10 samples per stage
  excluded from p50/p95/p99 (plan/18 § 18.17 Q-RT7).
- **CLI minimal frame body** — Phase 3.7 `trsim run` writes manifest +
  empty traces; per-frame Pipeline.step integration deferred to Phase 4.
- **mypy stub override**: `pyproject.toml` `[tool.mypy.overrides]`
  added `scipy.*` (Phase 2.8).

## MVP+α 제외 (Phase 3 단위)

- **EventBus**: async dispatch / threading.
- **InputBuffer**: priority / dedupe.
- **RunManager**: M-of-N confirmation policy.
- **ResourceLibrary**: federation across multiple workspaces, watchdog
  hot reload.
- **ScenarioService**: full TOML <-> Scenario conversion.
- **plugin_scanner**: dynamic import / exec sandbox.
- **PerformanceClock**: ReferenceTimingState handshake with HIL DUT.
- **CLI**: per-frame Pipeline.step integration, .scnbundle export.

## 트랩 / 교정 (Phase 3 누적)

- **lint SIM102** — nested `if` 문 한 줄 권장: `EventBus.unsubscribe`,
  `Command.__post_init__` 둘 다 적용.
- **ruff RUF009** — `field default` 가 함수 호출이면 fail. `Scenario.timing`
  / `PipelineConfig.{ekf,ukf}_config` 모두 `default_factory` 로 수정.
- **N806** — uppercase 변수명 (`vE/vN/vU`, `dE/dN/dU`) — snake_case
  로 일관 적용.
- **tempfile lifetime** — `scan_plugin_file(p)` 가 `with TemporaryDirectory`
  바깥에서 호출되면 파일 삭제 후 fail. 두 번째 호출도 with 블록 안으로.
- **import-linter scipy stubs** — `pyproject.toml [tool.mypy.overrides]
  module` 에 `scipy.*` 추가.
- **frozen+slots TypeError** — `s.extra_attr = ...` 가 expected `AttributeError`
  대신 `TypeError` 던짐. `__dict__` 부재 직접 검사로 수정 (Phase 2.4a 트랩
  재발).

## 다음

**Phase 4** — UI (PySide6 + pyqtgraph + pyvista). Two Workspaces (Editor,
Simulator) + Editor Activity 5종. `plan/04_migration.md` § 4.3 Phase 4.

Phase 3 도메인 layer 가 완성됐으므로 Phase 4 는 UI 가 App 의 EventBus /
CommandBus 에 binding 되는 형태. CI는 Qt headless 환경 (xvfb / libegl1)
세팅이 필요할 수 있음.
