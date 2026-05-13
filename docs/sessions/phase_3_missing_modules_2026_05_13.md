# Phase 3 MVP 누락 4 모듈 (D1~D4) — 4 sub-step 인계 (2026-05-13)

`docs/MVP_STATUS.md § "미구현 우선순위 리스트"` 우선순위 #5 (Phase 3
MVP 누락 4 모듈) 의 4 sub-step 모두 완료. Phase 3 (Application
layer) 의 ✗ 모듈 4개가 ✓ 로 마감.

## 0. 현재 상태 (한 줄)

- HEAD = `267348f` (D3 직후, D4 commit 다음 push)
- 누적 **2280 PASS** local (+82 across 4 sub-steps from 2198)
- ruff / mypy --strict / import-linter 5 contracts KEPT 매 commit

## 1. 사용자 설계 우선순위 (변동 없음)

> **physics_lab > simulator > editor**
>
> Phase 9 ✓ + Phase 5 후속 ✓ + Phase 6 NN 보강 ✓ + Phase 5 추가 ✓ +
> Phase 7 DLC CLI ✓ + Phase 7 remainder ✓ + **Phase 3 누락 4 모듈 ✓
> (이 cycle)**. 다음 cycle 후보:
> 1. **Phase 8 HIL 전체** — 가장 큰 작업. 8.1 MVP → Lock-step → 8.2
>    L2/L4 → 8.3 L1+AWG 4 sub-step.
> 2. **Phase 4 UI 실 데이터 binding** — Editor 5 activity / Simulator
>    8 panel 의 placeholder → 실 데이터.
> 3. **Phase 7 잔여** (Editor "Install Package..." menu wiring).
> 4. **Phase 4 UI dem_import_wizard / domain_settings / installation_panel**
>    — D4 backend 완료 후 wizard front-end 자연스러운 다음 단계.

## 2. 이 cycle 누적 push (4 commits)

| sub | commit | new | 범위 |
|---|---|---|---|
| D1 | `8636c5b` | +16 | bundle_service (.scnbundle / .runbundle export·import + tar-slip + manifest probe) |
| D2 | `75aacef` | +37 | physics_gate (5 sanity checks + PhysicsGateReport) |
| D3 | `267348f` | +15 | command_evaluator (Lineage Level 3-2: monotonic_sim_time / tracker_provenance / initial_scan_single) |
| D4 | (next) | +14 | io/dem_import (ESRI ASCII grid → terrain.npz + NODATA + north-up + land_mask) |
| (handoff) | (this) | — | 이 문서 |

## 3. 각 sub-step 요점

### D1 — bundle_service (16 tests)
- `pack_scenario_bundle` / `pack_run_bundle` — tar.gz writer with
  auto-generated manifest.toml at root (kind / created_iso UTC /
  workbench_version / creator). Source-provided manifest skipped.
- `unpack_bundle` — tar-slip defence (absolute paths + parent-
  relative entries rejected) + `extractall(filter="data")` for
  Python 3.14 forward-compat.
- `read_bundle_manifest` — peek manifest without full extract.

### D2 — physics_gate (37 tests, parametrised)
- 5 check functions: `velocity < c` / `mass > 0` / `altitude ∈ [-500,
  100_000] m` / `frequency ∈ [100 MHz, 100 GHz]` / `finite position`.
- `PhysicsCheckResult` + `PhysicsGateReport.has_failures` /
  `.failures` for Run-start UI gating.
- Module-level constants documented (CODATA c, altitude bounds, radar
  band edges).

### D3 — command_evaluator (15 tests)
- `LineageIssue` (rule_name + command_index + message) +
  `LineageReport.is_valid` for replay-loaded lineage validation.
- 3 rules:
  - `monotonic_sim_time`: `sim_t_s` non-decreasing, bootstrap prefix
    (`sim_t_s == -1.0`) skipped.
  - `tracker_source_provenance`: TRACKER source -> both
    `source_track_id` and `source_frame_id` required (re-checks
    replay-loaded commands that bypass `__post_init__`).
  - `initial_scan_single_dispatch`: INITIAL_SCAN source -> exactly
    one occurrence (zero allowed; 2+ flagged at every extra index).

### D4 — io/dem_import (14 tests)
- `read_esri_ascii_grid(path)` — parse `.asc` with 5 required headers
  + optional NODATA_value. Row 0 = south (north-up flip from ESRI's
  top-down order). NODATA cells → NaN.
- `write_terrain_npz(path, grid, *, land_mask=None)` — workbench-
  native `terrain.npz` (elevation + land_mask + origin + cellsize).
  Default land mask = `np.isfinite(elevation)` (NaN = sea).
- `import_dem_to_terrain_npz(asc, npz)` — end-to-end helper.
- Validation: missing file / missing required header / ncols mismatch
  / nrows mismatch / non-numeric body / mask shape mismatch.

## 4. 정합성 검사 결과 (Phase 3 cycle 끝)

`docs/MVP_STATUS.md` Phase 3 매트릭스: 4 ✗ → ✓ 모두 갱신.

Phase 3 전체 상태:
- ✓ Application layer 의 모든 MVP-defined 모듈 (D1~D4 포함).
- △ Profile 모드 toggle (off / explicit / live, Q4) — 후속.

5 contracts KEPT 매 commit. ruff / mypy --strict / import-linter 모두
clean.

## 5. 운영 학습 (이 cycle)

1. **tar-slip ≠ zip-slip but same defence** (D1) — Python `tarfile`
   에서도 entry path 가 target_dir 밖으로 escape 가능. zip-slip 과
   동일 패턴 (absolute path + parent-relative resolve check). Python
   3.14 의 `extractall(filter="data")` 도 추가 layer 로 적용.
2. **UTC tag literal `Z` vs `%z`** (D1) — `strftime("%z")` 가
   `+0000` 으로 나옴. `.iso8601` 표준은 `Z` 가 가장 깔끔. 수동
   `"%Y-%m-%dT%H:%M:%SZ"` format 사용.
3. **`datetime.UTC` vs `datetime.timezone.utc`** (D1) — Python 3.11+
   의 `datetime.UTC` alias 가 ruff UP017 권고. import 도 짧다.
4. **`object.__new__` 로 dataclass post_init 우회** (D3 test) —
   replay-loaded malformed Command 시뮬레이션. `frozen=True` 라
   `__setattr__` 도 막혀있어서 `object.__setattr__` 로 우회.
5. **ESRI ASCII grid row order = north-down** (D4) — Row 0 이 max
   y (top). north-up indexable elevation 만들려면 `arr[::-1, :]` flip.
   surprise factor 있는 부분 — docstring 에 명시.

## 6. 다음 세션 진입 명령

```powershell
cd "C:\Workspaces\Claude\Tracking Radar Simulator\trsim"
git pull --ff-only

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

& $PY -m pytest -q
# 2280 PASS expected

& ".\.venv\Scripts\lint-imports.exe"
# 5 contracts KEPT
```

다음 cycle 결정:
- **Phase 8 HIL** (가장 큰 미시작 phase, 새 protocol + 새 layer).
- **Phase 4 UI dem_import_wizard** (D4 backend 완료 후 자연스러운
  next, plan/22 § 22.5 의 7-step wizard).
- **Phase 4 UI 실 데이터 binding** (Editor 5 activity + Simulator
  8 panel 의 placeholder → 실 데이터).
- **Phase 7 remainder** (Editor "Install Package..." menu wiring).

## 7. 문서 위치 정리

| 문서 | 용도 |
|---|---|
| `docs/sessions/phase_5_followup_2026_05_13.md` | Phase 5 후속 12 sub-step |
| `docs/sessions/phase_6_augmentation_2026_05_13.md` | Phase 6 NN 보강 4 sub-step |
| `docs/sessions/phase_5_additional_followup_2026_05_13.md` | Phase 5 추가 후속 4 sub-step |
| `docs/sessions/phase_7_dlc_cli_2026_05_13.md` | Phase 7 DLC CLI 6 sub-step |
| `docs/sessions/phase_3_missing_modules_2026_05_13.md` | **이 인계** (Phase 3 누락 4 모듈) |
| `docs/MVP_STATUS.md` | Phase 0~9 매트릭스 |
| `CLAUDE.md` § 1 | 누적 진행 log |
