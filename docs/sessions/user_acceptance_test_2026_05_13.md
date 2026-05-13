# 사용자 수동 GUI UAT — 2026-05-13

직전 2 cycle (2026-05-13) 에 추가된 UI 영역을 GUI 에서 손으로 검증.
모든 항목 √ 가 떨어지면 다음 cycle 진행 가능. ✗ 가 있으면 보고만 — 자동
모드는 ✗ 발견 시 멈춤.

각 항목: **어디서 → 무엇을 클릭/입력 → 무엇을 기대**.

## 0. 환경 준비 (PowerShell)

```powershell
cd "C:\Workspaces\Claude\Tracking Radar Simulator\trsim"
git pull --ff-only

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$(Get-Location)\src"
$PY = ".\.venv\Scripts\python.exe"

# 빠른 sanity
& $PY -m pytest -q
# 2434 PASS expected (Phase 4 G1-G4 후)

# UI 가동
& $PY -m workbench
# 또는: & $PY -m workbench.cli ui --workspace editor
```

---

## A. Phase 4 dem_import_wizard (직전 cycle, 이미 main 에 있음)

### A.1 Map Editor 에서 Import DEM Wizard 열기

- [ ] Editor workspace 활성 → 좌측 Activity bar 의 🗺 (Map) 아이콘 클릭.
- [ ] 하단 action row 의 **`Import DEM...`** 버튼 클릭.
- [ ] 4-page wizard 다이얼로그 등장 — `Source` / `Land/Sea` / `Output` /
      `Summary` 4 step.

### A.2 wizard 각 step

- [ ] Page 1 (Source): GeoTIFF / ESRI ASCII grid 라디오 + Browse 버튼.
  GeoTIFF 는 stub (rasterio 의존 — MVP+α). ESRI ASCII (.asc) 만 동작.
- [ ] Page 2 (Land/Sea): Land/Sea 분류 모드 3종 라디오
  (`elevation_threshold` / `all_land` / `all_sea`). threshold 모드 선택
  시 threshold 입력 spin 등장.
- [ ] Page 3 (Output): 출력 .npz 경로 (default `terrain.npz`) 입력.
- [ ] Page 4 (Summary): 위 3 step 의 요약 readout.
- [ ] **`Finish`** 클릭 시 진행 상황 status. ✗ 면 사용자에게 명확한
  error 메시지.

### 알려진 한계 / stub
- GeoTIFF 입력 = stub (rasterio 의존, MVP+α). ESRI ASCII 만 round-trip.
- Wizard 가 종료되어도 Map Editor canvas 에 즉시 미리보기 ✗ (canvas
  자체가 placeholder).

---

## B. Phase 7 Plugins menu (직전 cycle, 이미 main 에 있음)

### B.1 Plugins menu 가 메뉴바에 보임

- [ ] 메뉴바: `File / Edit / View / Run / Plugins / Tools / Help` 의 6번째
  메뉴.
- [ ] `Plugins` 클릭 시 sub-menu: `Manage Plugins...` + `Install Package...`.

### B.2 Manage Plugins 다이얼로그

- [ ] `Plugins > Manage Plugins...` → `PackageManagerDialog` 등장 (별도
  창, modal).
- [ ] List view: 설치된 .trsim-pkg 목록. 없으면 `(no packages installed)`.
- [ ] Refresh 버튼 → 목록 재로드.
- [ ] 선택 후 `Uninstall` 버튼 → confirm dialog → 삭제.

### B.3 Install Package 직접 호출

- [ ] `Plugins > Install Package...` → file picker (.trsim-pkg
  필터). 파일 선택 → 진행 상황 + 결과 메시지.
- [ ] 같은 ID 가 이미 설치되어 있으면 overwrite 확인 dialog.

### 알려진 한계 / stub
- 실제 `.trsim-pkg` 가 없으면 list 비어있음 — sample DLC build CLI
  (`trsim sdk build`) 로 만들거나 `examples/dlc/simple_pairing_demo/`
  를 빌드 후 install.

---

## C. Phase 4 G1-G4 Domain Settings + Installation (이 cycle)

### C.1 Map Editor 우측 panel = QTabWidget (Layers + Domain)

- [ ] Editor → 🗺 Map activity.
- [ ] 우측 panel 상단에 **두 개의 탭** 표시: `Layers` 와 `Domain`.
- [ ] 기본 활성 탭 = `Layers` (기존 5개 체크박스: Terrain heightmap /
  Land-Sea mask / Buildings / Coastline polygon / Source DEM).
- [ ] `Domain` 탭 클릭 → 우측 panel 이 Domain Settings 로 전환.

### C.2 Domain Settings 패널 — bounds 편집

- [ ] `Domain` 탭 안 위쪽: **Map bounds (precise)** 행 (read-only) —
  현재 "(no map loaded)" 표시.
- [ ] **Simulation Domain** 6 spin: East min/max, North min/max, Ceiling,
  Floor. 기본값 East/North=(-25000, 25000), Ceiling=30000, Floor=-100.
- [ ] East max 를 -30000 으로 내려보기 → 패널 하단 `Status:` 라벨이
  `Invalid: bounds_east[1] must exceed ...` 으로 변경. 다시 +40000 입력
  → `Status: OK`.

### C.3 Outside Map Environment 라디오

- [ ] `Domain` 탭 중간: **Outside Map Environment** 4 radio: Open Sea
  (기본 선택) / Open Land / Blocked / Infinite Plane.
- [ ] 라디오 클릭 → 다른 라디오 해제 (exclusive).
- [ ] (signal 만 — 시각화 변화는 후속 cycle).

### C.4 Coverage Preview placeholder

- [ ] `Domain` 탭 아래쪽: `Coverage Preview` group 안의 hint label.
  "Map + Simulation Domain footprint + radar beam arc.\nWires to actual
  data in a later cycle." 표시.

### C.5 Scenario Composer Installation block 본격 layout

- [ ] Editor → 🎬 Composer activity.
- [ ] `Installation` group 안:
  - East / North line edit (기본 "0.0").
  - **Altitude** label — 기본 "(DEM sample pending)" (회색).
  - Initial Azimuth (기본 "180.0") / Initial Elevation (기본 "0.0")
    line edit.
  - **DEM Map (top-down) — installation pose preview** placeholder
    (회색 hint).
  - Coverage Stats sub-group: Max range / Obstructed sectors / Blind
    bearings (기본 "--").

### C.6 Composer Domain Override block

- [ ] `Installation` group 바로 아래 새 group `Domain Override
  (optional)`.
- [ ] "Override SimulationDomain (otherwise inherit from Map)" 체크박스
  (기본 off).
- [ ] "Override Outside Environment:" 체크박스 + 콤보 (기본 콤보 =
  `Inherit from Map`, disabled).
- [ ] 두 번째 체크박스 toggle → 콤보 enable / disable.
- [ ] 콤보 5 option: `Inherit from Map` / Open Sea / Open Land / Blocked /
  Infinite Plane.

### 알려진 한계 / stub
- Domain Settings 의 East/North/Ceiling/Floor 변경이 아직 Map / Scenario
  데이터에 저장 ✗ — Signal 만 발생. 후속 cycle 에서 Scenario `[domain]`
  section 으로 binding.
- Map bounds 라벨이 "(no map loaded)" 인 상태 유지 — Map 로드 시점에
  `MapEditor.set_map_bounds(map_.bounds)` 호출 wiring 이 필요 (현재는
  programmatic API 만 있음).
- Composer Coverage Stats 가 `--` 상태 유지 — 후속 cycle 에서 Radar +
  Validator 결과를 `set_coverage_stats(stats)` 로 채움.
- Composer Altitude label 도 동일 — `set_terrain_altitude(z)` API 만
  있고 wiring 미완.

---

## E. Phase 9 H1-H2 Library Models 동적 채우기 (Phase 9 cycle)

### E.1 Physics Lab Library 의 Models 카테고리 = 3 row

- [ ] Ctrl+Shift+L → Physics Lab workspace 활성.
- [ ] 좌측 Library tree 의 `Models` 카테고리 펼침.
- [ ] 3 row 표시:
  - `Gravity Only (analytic)  (dynamics)`
  - `Bouncing Ball  (dynamics)`
  - `Free-Space Path Loss  (rf_propagation)`
- [ ] 직전 PL-9.1f 의 placeholder 2 row (`Gravity (always on)` /
  `Air Drag (toggle)`) 가 더 이상 안 보임.

### E.2 Models row 클릭 → signal 발생

- [ ] `Bouncing Ball  (dynamics)` row 클릭. UI 시각 변화 없음
  (signal-only, 후속 cycle 에서 Parameters / Viz binding).
- [ ] `Gravity Only (analytic)  (dynamics)` row 클릭. 동일.

### E.3 직전 PL feature 들 회귀

- [ ] Tests > `Bouncing Ball Demo` 클릭 → 기존 y(t) plot + Restitution
  slider + Play 동작.
- [ ] Tests > `Sphere  (sphere)` 클릭 → 3D viewer (PyVista) 등장.

### 알려진 한계 / stub
- Models row 클릭 시 Parameters / Viz 가 자동 swap ✗ — 후속 cycle
  에서 BouncingBallController 가 PhysicsModelProtocol 일반화 받아
  처리.
- 사용자 정의 plug-in (custom PhysicsModelProtocol 구현) 등록 GUI
  ✗ — `register_physics_model()` Python API 만. PluginLoader 통합
  은 후속.

---

## D. 회귀 (기존 기능이 안 깨졌는지)

### D.1 Workspace 전환 단축키

- [ ] Ctrl+Shift+E → Editor 활성.
- [ ] Ctrl+Shift+S → Simulator 활성.
- [ ] Ctrl+Shift+L → Physics Lab 활성.

### D.2 Editor Activity 단축키

- [ ] Editor 안에서 Ctrl+1~5 로 5 Activity (Composer / Map / Radar /
  Targets / Browser) 전환.

### D.3 Simulator bottom tab 떼어내기

- [ ] Simulator workspace → 하단 tab bar 우클릭 → "Detach tab" → 별도
  창 등장. 창 닫기 → 원래 자리 복귀.

### D.4 Physics Lab Bouncing Ball demo

- [ ] Physics Lab → Library 트리에서 `Bouncing Ball Demo` 클릭.
- [ ] Play 버튼 → 시뮬레이션 시작, plot 에 y(t) 곡선 등장.
- [ ] Restitution slider 변경 → bounce 감쇠 변화.

---

## E. 보고 양식

위 항목 검증 후 다음 형식으로 알려줘 (간단히):

- **GREEN** — 다 √. 자동 모드 다음 cycle 진행.
- **YELLOW** — `<section>.<num>` 에서 사소한 미세 이슈 (예: 라벨 색,
  spacing). 다음 cycle 진행하되 follow-up todo 추가.
- **RED** — `<section>.<num>` 에서 기능 안 됨 / crash / wrong behavior.
  자동 모드 중지, 진단부터.

---

## 진행 상황

### 2026-05-13 cycle 6 = G1-G4 (Phase 4 domain_settings)

| 영역 | 상태 |
|---|---|
| G1 SimulationDomain + OutsideEnvironment dataclass | ✓ |
| G2 DomainSettingsPanel widget | ✓ |
| G3 Map Editor mounts Domain tab | ✓ |
| G4 Composer Installation + Domain Override block | ✓ |

### 2026-05-13 cycle 7 = H1-H2 (Phase 9 Library Models)

| 영역 | 상태 |
|---|---|
| H1 LibraryWidget set_physics_models API | ✓ |
| H2 model_registry + workspace integration | ✓ |
| 누적 test | 2468 PASS |
| import-linter | 5 contracts KEPT |

다음 cycle 후보 — `docs/MVP_STATUS.md § "미구현 우선순위 리스트"`:
- 1. Phase 4 UI 실 데이터 binding (Editor 5 activity / Simulator 8
     panel placeholder → 실 데이터). 큰 작업, 여러 cycle 분할.
- 2. Phase 8 HIL 전체. 매우 큰 작업.
- 3. Phase 9 § 19.7.5+ remainder (Validation Bench 일반화 /
     PluginLoader discovery).
