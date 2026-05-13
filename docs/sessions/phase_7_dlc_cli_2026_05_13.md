# Phase 7 DLC CLI 완성 (C1~C6) — 6 sub-step 인계 (2026-05-13)

Phase 7 (DLC, Wave 2) 의 CLI / SDK / UI / sample / tutorial 단번에
완성. 외부 DLC 작성자가 `trsim sdk build` -> `trsim sdk test` ->
`trsim install` 워크플로를 end-to-end 로 사용 가능. Runtime 은 이미
끝나있던 상태 (Phase 7.1~7.6), 이번 cycle 은 그 위에 CLI front-door
+ UI front-door + reference sample + 작성자 가이드를 얹은 것.

## 0. 현재 상태 (한 줄)

- HEAD = `1c8122c` (`C5/C6 — PackageManagerPanel + sample DLC + tutorial`)
- 누적 **2182 PASS** local (2131 → 2182, +51 across 6 sub-steps)
- ruff / mypy --strict / import-linter 5 contracts KEPT 매 commit
- 이 cycle 4 feature commits + 1 handoff main 직접 push

## 1. 사용자 설계 우선순위 (변동 없음)

> **physics_lab > simulator > editor**
>
> Phase 9 ✓ + Phase 5 후속 ✓ + Phase 6 NN 보강 ✓ + Phase 5 추가 ✓ +
> **Phase 7 DLC CLI ✓ (이 cycle)**. 다음 진입점 후보 (MVP_STATUS §
> 우선순위):
> 1. **Phase 3 MVP 누락 4 모듈** — bundle_service / evaluator
>    (Command Lineage) / physics_gate / io/dem_import. 중간 크기.
> 2. **Phase 8 HIL 전체** — 가장 큰 작업, 새 protocol + 새 layer.
> 3. Phase 4 UI 실 데이터 binding (가장 크고 가시 큰 작업).
> 4. Phase 7 잔여 (sdk/resource_schemas.py + sdk/package_validator.py
>    분리 + Editor "Install Package..." menu wiring).

## 2. 이 cycle 누적 push (4 commits + 1 handoff)

| sub | commit | new | 범위 |
|---|---|---|---|
| C1 | `934c1d3` | +15 | io/package_io (.trsim-pkg pack/unpack + zip-slip + manifest probe) |
| C2 + C3 + C4 | `e080822` | +17 | sdk.build_package + sdk.test_package + `trsim sdk build/test` + `trsim install` |
| C5 + C6 | `1c8122c` | +19 | PackageManagerPanel + sample DLC + creating_dlc.md tutorial + e2e |
| (handoff) | (this) | — | 이 문서 |

## 3. 각 sub-step 요점

### C1 — io/package_io (15 tests)
- `pack_package(src, out)` — directory → `.trsim-pkg` zip with
  manifest pre-validation (no broken artifact on disk).
- `unpack_package(pkg, target)` — zip → directory with zip-slip
  defence (CVE-2018-1002201) + existing-target refusal.
- `read_manifest_from_package(pkg)` — peek manifest without
  extracting (install preview, CI checks).
- Constants `MANIFEST_FILENAME = "manifest.toml"`,
  `PACKAGE_SUFFIX = ".trsim-pkg"`.

### C2 — sdk.build_package + `trsim sdk build`
- Thin SDK wrapper around `pack_package` so authors can build
  packages from Python.
- CLI exits 2 on missing source / wrong suffix / invalid manifest.

### C3 — sdk.test_package + `trsim sdk test`
- `PackageTestResult` carrying package_id/name/version + trsim_min
  + non-fatal issues list (empty description / author warnings).
- CLI prints fields + soft issues; exit 0 unless the manifest
  itself is broken.

### C4 — `trsim install`
- Default install root `~/.trsim/packages/<package_id>/`.
- `--packages-root` override + `--force` for `pip install --force-
  reinstall` semantics.
- Refuses existing target without `--force` (exit 2).

### C5 — ui/editor/package_manager_panel (10 tests)
- `InstalledPackageRow` dataclass + `PackageManagerPanel(QWidget)`.
- Three signals: `install_requested()`, `uninstall_requested(str)`,
  `refresh_requested()`. The panel itself is I/O-free; wiring layer
  (MainWindow) catches signals → file pickers → io.package_io.
- Uninstall button auto-disables when nothing is selected.

### C6 — Sample DLC + tutorial (9 tests)
- `examples/dlc/simple_pairing_demo/` — canonical layout (manifest
  + maps resource + DemoPanel + README).
- `docs/dev_guide/creating_dlc.md` — 8-section guide (rationale,
  layout, schema, slot reference, build/test/install commands,
  exit codes, Python API, pitfalls).
- End-to-end test ensures the in-tree sample round-trips through
  `sdk build` → `sdk test` → `install` every commit.

## 4. 정합성 검사 결과 (Phase 7 cycle 끝)

`docs/MVP_STATUS.md` Phase 7 매트릭스:

| 항목 | 상태 | 갱신 |
|---|---|---|
| SDK protocols (11 Protocol) | ✓ | 이미 ✓ |
| SDK manifest.py | △ | domain/dlc/manifest.py 에 있음, sdk/ 이동은 후속 |
| SDK resource_schemas.py | ✗ | **여전히 ✗** (후속 작업) |
| SDK package_builder + `trsim sdk build` | ✓ | C2 |
| SDK package_validator.py | ✗ | **여전히 ✗** (test_harness 가 일부 역할) |
| SDK test_harness + `trsim sdk test` | ✓ | C3 |
| App layer (PackageManager + PluginLoader + PanelRegistry + dlc_runtime) | ✓ | 이미 ✓ |
| io/package_io.py | ✓ | C1 |
| `trsim install` CLI | ✓ | C4 |
| ui/editor/package_manager_panel.py | ✓ | C5 |
| Editor 메뉴 "Install Package..." + file picker | ✗ | wiring 미완 — panel 만 작성, MainWindow 연결 안 함 (후속) |
| Sample DLC | ✓ | C6 |
| DLC 만드는 튜토리얼 | ✓ | C6 |

Phase 7 cycle 의 핵심 (CLI 3 endpoint + SDK 2 함수 + UI panel +
sample + tutorial + 매트릭스 갱신 + change log footer) 모두 완료.
잔여 3 항목 (resource_schemas / package_validator / Editor menu
wiring) 은 별도 sub-cycle 또는 다음 phase 진입 시 함께 정리.

5 contracts KEPT 매 commit. ruff / mypy --strict / import-linter
모두 clean.

## 5. 운영 학습 (이 cycle)

1. **manifest 검증을 pack 시점에 끌고 오기** (C1) — pack 후 broken
   artifact 가 디스크에 남는 게 가장 디버깅 어려운 케이스. 검증을
   pack 진입 즉시 실행하면 fail fast.
2. **zip-slip defence pre-extraction** (C1) — entries 의 path 가
   target_dir 안에 있는지 *extractall 전*에 확인. 일부만 풀린 상태로
   target_dir 가 만들어지면 안전 X. test 가 "target dir was never
   created" 까지 검증.
3. **I/O-free Qt widget pattern** (C5) — Panel 이 filesystem 안
   건드림 → test 가 fake fs 없이 widget 만 instantiate + signal
   wiring 검증 가능. Wiring layer (MainWindow) 가 책임 짐.
4. **In-tree sample DLC end-to-end test** (C6) — `examples/dlc/
   simple_pairing_demo/` 자체가 매 commit 별 build/test/install
   round-trip 통과해야 함. 깨지면 `creating_dlc.md` tutorial 의 첫
   명령이 실패한다는 의미 → 새 author 가 즉시 차단당함. 최고 가시
   regression 신호.
5. **`PowerShell 5.1` BOM 방어 재발 방지** (C1 + earlier handoffs) —
   PackageManager + variant_manifest + TrainingJob loader + 새
   package_io 까지 BOM strip 패턴 통일. handoff 의 § 7 함정에 추가.

## 6. 다음 세션 진입 명령

```powershell
cd "C:\Workspaces\Claude\Tracking Radar Simulator\trsim"
git pull --ff-only

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

& $PY -m pytest -q
# 2182 PASS expected

& ".\.venv\Scripts\lint-imports.exe"
# 5 contracts KEPT
```

DLC 워크플로 직접 시도:

```powershell
& $PY -m workbench sdk build `
    --source examples/dlc/simple_pairing_demo `
    --output dist/simple_pairing_demo.trsim-pkg

& $PY -m workbench sdk test `
    --package dist/simple_pairing_demo.trsim-pkg

& $PY -m workbench install `
    --package dist/simple_pairing_demo.trsim-pkg `
    --packages-root C:\temp\trsim_packages
```

다음 cycle 결정 (MVP_STATUS § 우선순위):
- **Phase 3 MVP 누락 4 모듈** — bundle_service / evaluator (Command
  Lineage) / physics_gate / io/dem_import. 중간 크기 모듈 4개,
  test-only 가 아니라 실 구현 필요.
- **Phase 8 HIL 전체** — 가장 큰 작업, 새 protocol + 새 layer + UI
  panel + sample mock. 8.1 MVP / Lock-step / 8.2 L2-L4 / 8.3 L1+AWG
  sub-step 분할.

## 7. 문서 위치 정리

| 문서 | 용도 |
|---|---|
| `docs/sessions/phase_5_followup_2026_05_13.md` | Phase 5 후속 12 sub-step |
| `docs/sessions/phase_6_augmentation_2026_05_13.md` | Phase 6 NN 보강 4 sub-step |
| `docs/sessions/phase_5_additional_followup_2026_05_13.md` | Phase 5 추가 후속 4 sub-step |
| `docs/sessions/phase_7_dlc_cli_2026_05_13.md` | **이 인계** (Phase 7 DLC CLI 6 sub-step) |
| `docs/MVP_STATUS.md` | Phase 0~9 매트릭스 |
| `CLAUDE.md` § 1 | 누적 진행 log |
| `docs/dev_guide/creating_dlc.md` | DLC 작성자 가이드 (C6 신규) |
| `examples/dlc/simple_pairing_demo/` | DLC 참조 구현 (C6 신규) |
