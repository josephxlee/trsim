# Phase 4 — DEM Import Wizard cycle (2026-05-13)

이 cycle 은 `session_2026_05_13_multi_cycle_handoff.md` § 7 추천 1
순위 (Phase 4 UI dem_import_wizard) 를 그대로 따라갔다. D4 backend
(io/dem_import) 가 cycle-바로-전에 끝났으므로 자연 next.

## 0. 한 줄 요약

- HEAD = `b8e9f24` (E3 + MVP_STATUS).
- 누적 **2327 PASS** local (2280 → 2327, **+47** in this cycle).
- 5 contracts KEPT 매 commit. ruff / mypy --strict / import-linter
  all clean.
- 3 sub-step (E1 / E2 / E3) push, 각 단독 commit.

## 1. 진입 근거

`docs/MVP_STATUS.md § "미구현 우선순위 리스트"` 의 6 번 항목
**Phase 4 UI dem_import_wizard / domain_settings / installation_panel**
(중 크기). dem_import_wizard 만 이 cycle 에서 종결, domain_settings
+ installation_panel 은 후속 cycle 후보.

## 2. 3 sub-step 요약

| sub | commit | 추가 | 누계 PASS | 핵심 |
|---|---|---|---|---|
| E1 | `f2f7644` | `app/dem_wizard.py` + 22 tests | 2280 → 2302 | 도메인 모델 (3 StrEnum + 2 frozen dataclass + 3 pure 함수) |
| E2 | `77f93bd` | `ui/editor/map_editor/dem_import_wizard.py` + 19 tests | 2302 → 2321 | 7-page QWizard, accept() → execute() |
| E3 | `b8e9f24` | `ui/editor/activity_pages.py` + 6 tests + MVP_STATUS | 2321 → 2327 | MapEditorPage 가 시그널 받아 wizard 띄움 |

## 3. 구현 디자인

### 3.1 레이어 분리

```
plan/11 § 11.5 (7 steps)
      │
      ▼
[E1] app/dem_wizard.py
   - VerticalReference / LandSeaMethod / InterpolationMode StrEnum
   - CropBounds, WizardConfig frozen+slots dataclass
   - derive_land_mask / crop_grid / execute (pure)
      │  uses
      ▼
   io/dem_import.py  (Phase 3 D4)
   - read_esri_ascii_grid / write_terrain_npz
      ▲
      │
[E2] ui/editor/map_editor/dem_import_wizard.py
   - QWizard with 7 QWizardPage (Page 0..6)
   - build_config() → WizardConfig
   - accept() → execute() → emit import_completed/failed
      ▲
      │
[E3] ui/editor/activity_pages.py (MapEditorPage)
   - import_dem_requested → DEMImportWizard().show()
   - emit-driven history push (newest first)
```

### 3.2 7 page 매핑 (plan/11 § 11.5.2)

| Step | 페이지 클래스 | UI |
|---|---|---|
| 1. Source select | `SourcePage` | QLineEdit + Browse... QPushButton (QFileDialog) |
| 2. Vertical ref | `VerticalReferencePage` | 4 QRadioButton (EGM96 default) |
| 3. Region | `RegionPage` | Full vs Custom radio + 4 QDoubleSpinBox |
| 4. Land/Sea | `LandSeaPage` | 4 QRadioButton + threshold QDoubleSpinBox; COASTLINE_FILE disabled |
| 5. CRS conversion | `CoordinateConversionPage` | "MVP no-op" note label |
| 6. Interpolation | `InterpolationPage` | QComboBox 3 modes |
| 7. Save | `SavePage` | QLineEdit + Browse... (QFileDialog.getSaveFileName) |

### 3.3 도메인 검증 (E1)

- `CropBounds.__post_init__` rejects east_min≥east_max,
  north_min≥north_max.
- `WizardConfig.__post_init__` rejects:
  - `land_sea_method=COASTLINE_FILE` without `coastline_path`.
  - `land_sea_threshold_m < 0`.
- `derive_land_mask` raises `NotImplementedError` for COASTLINE_FILE
  (coastline parser deferred).
- `crop_grid` raises ValueError when bounds don't overlap grid extent;
  otherwise clamps to grid corners + snaps to whole cells.

### 3.4 MVP no-op fields

- `vertical_reference` 와 `interpolation` 은 wizard 가 수집만 함.
  지금 backend (ESRI ASCII → terrain.npz) 는 두 필드 무시. 향후
  GeoTIFF importer 가 도착하면 같은 public surface 그대로 활용.

### 3.5 시그널 contract (E2 / E3)

- `DEMImportWizard.import_completed(Path)` — Finish 클릭 +
  execute() 성공 시.
- `DEMImportWizard.import_failed(str)` — build_config() ValueError /
  FileNotFoundError / NotImplementedError / OSError 어떤 것이든
  단일 message 시그널로 통일.
- `MapEditorPage.last_imported_path()` — 마지막 성공한 import 의
  destination path 누적.
- `MapEditorPage.active_wizard()` — wizard 가 열려 있을 때 non-None.
  finished(int) 후 자동 None 복귀 (Finish 든 Cancel 든).

## 4. 운영 학습

### 4.1 StrEnum + QComboBox userData 함정

`QComboBox.addItem(label, mode)` 에 `InterpolationMode.BILINEAR`
같은 StrEnum 을 userData 로 넣으면 Qt 의 QVariant coercion 이
**str 로 stringify** 한다. round-trip 시 `currentData()` 가
`"bilinear"` 문자열을 돌려주지 enum member 가 아니다.

대처: parallel `self._modes: tuple[InterpolationMode, ...]` 를 두고
`currentIndex()` 로 lookup. userData 미사용.

### 4.2 `typing.override` vs mypy --strict

Python 3.13 가 `typing.override` 를 noqa 회피용으로 제공하지만
**mypy --strict 가 "Untyped decorator" 로 reject** 함 (typeshed
완전 cover 못 함). 대안: `# noqa: N802 - Qt method` 명시. Qt
override (`isComplete`, `accept`) 함수에 일관 적용.

### 4.3 QWizard accept() 실패 시 super 호출 금지

`accept()` override 안에서 `import_failed` 시그널 emit 후 **early
return** 하면 wizard 가 닫히지 않음 (super().accept() 미호출).
사용자가 입력 고치고 다시 Finish 누를 수 있음. 성공 path 만
`super().accept()` 호출.

E3 의 `test_wizard_failure_appends_failure_entry` 는 이 invariant
검증 (wizard 가 살아있어야 history 만 추가되고 active_wizard()
는 `wiz` 그대로).

### 4.4 ESRI flip 방향과 테스트 helper

`io.dem_import.read_esri_ascii_grid` 는 row 0 = south (north-up)
로 flip 한다. 하지만 도메인 테스트의 `_grid([[..],[..]])` helper 는
flip 없이 raw 배열. 두 convention 을 혼동하면 crop test 가 잘못된
cell 을 검증 (E1 첫 run 의 2 failure).

대처: helper 안에 docstring "stores array as-is (no ESRI flip)" 명시.
ESRI 입력의 row 순서 검증은 io.dem_import 전용 test 에만.

## 5. 다음 cycle 후보

`docs/MVP_STATUS.md § "미구현 우선순위 리스트"` 기준, 우선순위 1~3
(Phase 6/5/7) 이전 cycle 들에서 완료, 4 (Phase 8 HIL) 가 가장 큰
미시작, 5 (Phase 3 누락) 도 완료. 따라서:

1. **Phase 4 UI domain_settings panel** — plan/11 § 11.11 의
   Simulation Domain + Outside Environment 패널. dem_wizard 와 같은
   사이즈 (3 sub-step). Map Editor activity 안에 자연스럽게 들어감.
2. **Phase 4 UI installation_panel** — plan/13 § 13.3.x 의 Scenario
   Composer Installation 패널 (DEM + 차폐 preview + coverage stats).
   composer.py 가 이미 widget skeleton 인 상태.
3. **Phase 4 UI 실 데이터 binding** — 큰 작업, 여러 cycle 분할 필요.
   ResourceLibrary ↔ Editor activities ↔ Simulator panels.
4. **Phase 8 HIL 전체** — 가장 큰 미시작, plan/18 전체.
5. **Phase 7 remainder** — Editor 메뉴 "Install Package..." wiring.
   매우 작음 (1 sub-step).

다음 cycle 자동 진행 시 추천: **Phase 4 domain_settings** (이 cycle
의 패턴 거의 동일, 사용자 가시 + 작은 작업).

## 6. UAT 체크리스트

`docs/sessions/user_acceptance_test_2026_05_13.md` — 이 cycle 에서
추가된 UI 동작 모음. 사용자가 직접 brew 한 .asc 파일로 wizard
일주 가능한지 확인하는 step-by-step.
