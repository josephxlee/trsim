# Phase 4 dem_import_wizard cycle — 4 sub-step (2026-05-13)

직전 5-cycle 종합 (`session_2026_05_13_multi_cycle_handoff.md`) 후
사용자 자동-진행 모드에서 진입한 첫 cycle. plan/13 § 13.4.5 + plan/11
§ 11.5 의 "Import DEM..." 7-step 위자드를 Editor 에 처음 mount.

## 0. 한 줄 요약

- HEAD = `19e21d8` (Phase 4 dem_import_wizard E4 + docs).
- 누적 **2326 PASS** local (2280 → 2326, **+46 신규** in this cycle).
- 5 contracts KEPT 매 commit. ruff / mypy --strict / import-linter
  all clean.
- 4 sub-step push (E1 = `08ad550`, chore = `63347ec`, E2 = `2bd330f`,
  E3 = `13adca6`, E4 = `19e21d8`).

## 1. 4 sub-step

| sub | commit | new | 내용 |
|---|---|---|---|
| E1 | `08ad550` | +8 | `LandSeaMode` StrEnum (`AUTO_THRESHOLD`/`NODATA`/`ALL_LAND`) + `compute_land_mask(grid, mode, threshold_m=0.5) -> NDArray[bool_]` pure function. plan/11 § 11.5.5 의 4 modes 중 GeoJSON 코ast line 만 deferred. |
| E2 | `2bd330f` | +7 | `DEMImportRequest` (frozen+slots: source_asc_path / output_npz_path / land_sea_mode / threshold_m=0.5) + `DEMImportSummary` (request + output_path + grid_shape + cell counts) + `run_dem_import(req) -> DEMImportSummary` orchestrator. `read_esri_ascii_grid → compute_land_mask → write_terrain_npz` 합성. |
| E3 | `13adca6` | +20 | `DEMImportWizard(QDialog)` 4-page (Source / Land-Sea / Output / Summary, plan/11 § 11.5.2 의 7-step 을 MVP 로 응축). Steps 2/3/5/6 (vertical-ref dialog / area crop / coordinate transform / regrid) deferred — 백엔드가 source CRS 를 ENU metres 로 직접 받음. `set_source_path` / `set_output_path` / `set_land_sea_mode` / `set_threshold_m` 가 test driver (QFileDialog 회피). `import_requested(DEMImportRequest)` + `report_import_result(summary)` / `report_import_error(msg)` public API. |
| Chore | `63347ec` | 0 | `.claude/settings.local.json` 을 `.gitignore` 에 추가 — worktree-local Claude Code 설정이 E1 commit 에 sneak in 한 후속 cleanup. |
| E4 | `19e21d8` | +10 | `DEMImportController(QObject)` 가 MapEditor.import_dem_requested → wizard.show → import_requested → run_dem_import → report_result / report_error wire. `wizard_factory` + `runner` 인젝션 가능 (test 가 file-touching 회피). `finished` 시 active wizard ref drop. MainWindow `__init__` 에 자동 mount. `dem_import_controller()` 테스트 헬퍼. |

## 2. 도메인 결정

### LandSeaMode 3 modes (plan/11 § 11.5.5 distilled)

- `AUTO_THRESHOLD` — `elevation > threshold_m & finite`. NaN comparison
  return False, NODATA cells stay sea automatically.
- `NODATA` — `finite(elevation)`. SRTM-style DEM 에서 ocean 이 NODATA
  로 sentinel 된 케이스.
- `ALL_LAND` — `np.ones(shape, bool)`. NaN 이 elevation 에 그대로
  남으므로 sampling 시 NaN return — caller responsibility.

Coastline-file mode (외부 GeoJSON/Shapefile) 는 deferred — parser
의존성 큰 작업.

### Wizard 4-page (MVP distillation of 7-step)

| Wizard page | plan/11 § 11.5.2 step |
|---|---|
| Source | Step 1 (포맷 감지) |
| Land-Sea | Step 4 (land/sea 구분) |
| Output | Step 7 (Workbench Native 저장) |
| Summary | 모두 통합 |
| (deferred) | Steps 2 (vertical-ref dialog) / 3 (area crop) / 5 (CRS/datum 변환) / 6 (regrid 보간) |

### Controller injection 패턴

```python
DEMImportController(
    map_editor=editor,
    parent=host,
    wizard_factory=DEMImportWizard,    # 기본
    runner=run_dem_import,              # 기본
)
```

Tests 가 `runner=fake_runner` 또는 `wizard_factory=fake_wiz` 로 I/O
회피 가능. 두 override 모두 happy-path 테스트에서 검증.

## 3. 학습 (2 trap)

### Trap 1: headless Qt visibility

`isVisible()` 은 widget 이 실제 표시될 때만 True (parent 도 visible
이어야 함). Headless test 가 `.show()` 안 부르면 `setVisible(True)`
후에도 `isVisible()` == False.

→ 패턴: setVisible 상태만 확인하려면 `isHidden()` (부정). 단,
`isHidden()` 도 widget 이 explicit hide 일 때 True 라서 setVisible
역사를 정확히 보지는 않음. test_dem_import_wizard.py 의 summary
swap 테스트에서 `isHidden() is True` / `isHidden() is False` 패턴.

### Trap 2: constructor ordering for radios + dependent widgets

`QRadioButton.toggled` 가 `setChecked(True)` 시 immediately fire.
핸들러가 같은 widget 의 다른 멤버 (spin / btn) 를 읽으면 `AttributeError:
'X' object has no attribute '_threshold_spin'`.

→ 패턴: 모든 widget build 후 마지막에 wire + default check. wizard
의 `__init__` finale 에서 mode radios connect + default-NODATA check
일괄 처리. 이전 trap (5.6 Monopulse decoupling) 과 유사한 "create-then-
wire" 패턴.

### Trap 3 (bonus): `.claude/settings.local.json` sneaking into commits

Worktree-local Claude Code 자동 권한 승인 파일이 `git add -A` 에 잡혀
E1 commit 에 포함됨. 추가 `chore: ignore` follow-up commit 으로
`.gitignore` 갱신 + `git rm --cached`.

→ 패턴: 새 worktree 시작 시 한 번씩 `.gitignore` 확인. 전통적인
`.idea/` / `.vscode/` 와 같은 위치.

## 4. 다음 cycle 후보 (`docs/MVP_STATUS.md § "미구현 우선순위 리스트"` 따라)

| 우선 | 작업 | 크기 | 비고 |
|---|---|---|---|
| 1 | Phase 7 remainder Editor "Install Package..." menu wiring | **작음** | MainMenuBar action → file picker → PackageInstaller (이미 있음) → toast / refresh. 1-2 sub-step. |
| 2 | Phase 4 UI domain_settings + installation_panel | 중 | Scenario Composer Installation panel + Map Editor Domain Settings panel — placeholder 만 있음. |
| 3 | Phase 4 UI 실 데이터 binding | 대 | Editor 5 activity + Simulator 8 panel placeholder → 실 데이터. 여러 cycle. |
| 4 | Phase 8 HIL 전체 | 매우 대 | 8.1 MVP → Lock-step → 8.2 L2/L4 → 8.3 L1+AWG. 새 protocol + 새 layer. |

자동 진행 모드 다음 cycle 은 추천 1 (Phase 7 menu wiring) 부터.

## 5. 다음 세션 진입 명령 (PowerShell)

```powershell
cd "C:\Workspaces\Claude\Tracking Radar Simulator\trsim"
git pull --ff-only

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

& $PY -m pytest -q
# 2326 PASS expected

& ".\.venv\Scripts\lint-imports.exe"
# 5 contracts KEPT
```

그 다음 `docs/MVP_STATUS.md § "미구현 우선순위 리스트"` 첫 행 자동 진입.
