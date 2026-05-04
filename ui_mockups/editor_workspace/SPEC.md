# UI Mockup Spec — Editor Workspace (5 Activity)

**최종 갱신**: 2026-04-29
**대상 plan**: 13 editor_workspace (권위 문서, v0.35), 02 § 2.2 Workspaces, 12 § 12.11 Flatten Area
**대상 Phase**: Phase 4 UI

---

## 0. 의도

13_editor_workspace.md 의 자세한 spec 본문을 시각화로 보강.
HTML artifact 와 함께 본 docs.

핵심 사용자 흐름:
```
[1] 앱 실행 → Workspace = Editor (또는 Simulator)
[2] 좌측 Activity Selector (5개) 중 하나 선택
[3] 좌측 상시 Resource Browser sidebar — 자원 탐색
[4] 중앙 탭 영역 — 선택 Activity 내용 + 다중 탭
[5] 상단 Toolbar — Activity 별 동작 (Save / New / Validate 등)
```

5 Activity:
1. **Scenario Composer** 🎬 — 시뮬 시나리오 만들기 (메인, 가장 자주)
2. **Map Editor** 🗺 — 지형·건물 편집 (Flatten Area 포함)
3. **Radar Editor** 📡 — RadarConfig 통합 폼 (v0.25)
4. **Targets Editor** 🎯 — Target 메타 편집 (trajectory 외)
5. **Resource Browser** 📂 — 모든 자원 전체 화면 (Activity 5)

---

## 1. 공통 레이아웃

### 1.1 전체 구조

```
┌──────────────────────────────────────────────────────────────────────┐
│ Title bar: TRsim Workbench                                           │
├──────────────────────────────────────────────────────────────────────┤
│ ◤ Workspace Selector ◢   Editor | Simulator                          │
├──┬─────────────────────────┬─────────────────────────────────────────┤
│  │                         │ Editor Toolbar                          │
│A │  Resource Browser       ├─────────────────────────────────────────┤
│c │  (상시 사이드바)        │ Tab1 │ Tab2 │ Tab3 + ▾                   │
│t │                         ├─────────────────────────────────────────┤
│  │  - 카테고리 트리        │                                          │
│i │  - 검색                 │   중앙 탭 영역 (선택 Activity)           │
│v │  - resource list        │                                          │
│  │  - Recent / Favorites   │                                          │
│i │                         │                                          │
│t │                         │                                          │
│y │                         │                                          │
│  │                         │                                          │
└──┴─────────────────────────┴─────────────────────────────────────────┘
```

### 1.2 좌측 Activity Selector (13 § 13.2.2)

세로 아이콘 stripe. 5 + 1 (Settings):

| 아이콘 | Activity | 단축키 |
|---|---|---|
| 🎬 | Scenario Composer | Ctrl+1 |
| 🗺 | Map Editor | Ctrl+2 |
| 📡 | Radar Editor | Ctrl+3 |
| 🎯 | Targets Editor | Ctrl+4 |
| 📂 | Resource Browser | Ctrl+5 |
| ⚙ | Settings | Ctrl+, |

선택된 activity 는 highlight + 좌측 stripe 에 accent bar.

### 1.3 좌측 Resource Browser sidebar (13 § 13.2.3)

**상시 표시**. Activity 5 (Resource Browser 전체 화면) 와 다름 — 항상 옆에 있어 작업 중 자원 참조.

```
┌──────────────────────────┐
│ 🔍 Search...             │
├──────────────────────────┤
│ ▼ Maps (3)               │
│   📍 PortBusan_v2.toml   │
│   📍 OpenSea_basic       │
│   📍 SeoulCity_demo      │
├──────────────────────────┤
│ ▼ Radars (5)             │
│   📡 KS-1_default        │
│   📡 KS-2_high_res       │
│   ...                    │
├──────────────────────────┤
│ ▼ Targets (12)           │
│   🎯 boeing_737          │
│   🎯 cruise_missile      │
│   ...                    │
├──────────────────────────┤
│ ▼ Scenarios (8)          │
│   🎬 A_Base.toml ⭐      │
│   🎬 B_HighSeas          │
│   ...                    │
├──────────────────────────┤
│ Recent · Favorites       │
└──────────────────────────┘
```

**드래그 가능**: Resource Browser 에서 Scenario Composer 로 자원 끌어 놓기 (References 블록에 추가).

### 1.4 중앙 탭 영역 (13 § 13.2.4)

- **다중 탭**: 한 Activity 안에서 여러 자원 동시 편집 (예: Map A.toml + Map B.toml)
- **Tab 라벨**: 자원 이름 + 변경 표시 (` *` if dirty)
- **닫기**: 각 탭 ×, 변경된 탭 닫을 때 confirm

### 1.5 Editor Toolbar (13 § 13.2.5)

Activity 별 다름:

| Activity | Toolbar 항목 |
|---|---|
| Scenario | New / Save / Save As / Validate / Run (Simulator 이동) |
| Map | New / Save / Save As / Import DEM / Export |
| Radar | New / Save / Save As / Test Beam |
| Targets | Save / Trajectory Preview |
| Resource Browser | Bulk Delete / Export / Import |

---

## 2. Screen E-1 — Scenario Composer 🎬 (메인)

**가장 자주 사용**. 시뮬 시나리오를 만드는 핵심 화면.
**파일**: `ui/editor/activities/scenario_composer.py`
**참조**: 13 § 13.3

### 2.1 레이아웃

```
┌────────────────────────────────────────────────────────────────────┐
│ Editor Toolbar:  [+ New] [💾 Save] [Save As] [✓ Validate] [▶ Run]  │
├────────────────────────────────────────────────────────────────────┤
│ Tabs: [ A_Base.toml * ] [ B_HighSeas ] [ + ]                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ Scenario Name:   [ A_Base                              ]            │
│ Description:     [ 단일 표적 단순 추적 검증           ]            │
│                                                                     │
│ ┌─── References (자원 참조) ─────────────────────────────────────┐ │
│ │ Map:      📍 PortBusan_v2.toml                          [×]    │ │
│ │ Radar:    📡 KS-1_default.toml                          [×]    │ │
│ │ Targets:  🎯 boeing_737.toml                            [×]    │ │
│ │           🎯 cruise_missile.toml                        [×]    │ │
│ │           [ + Add Target... ]                                  │ │
│ └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─── Installation (자원의 시뮬 내 위치) ─────────────────────────┐ │
│ │ Radar (1)                                                       │ │
│ │  ◦ KS-1_default                                                 │ │
│ │    Position: lat 35.123, lon 129.456, alt 50m                  │ │
│ │    Heading: 045°  (NE)                                          │ │
│ │    Anchor: Building "BusanTowerA" / lat-lon free                │ │
│ │                                                                 │ │
│ │ Targets (2)                                                     │ │
│ │  ◦ boeing_737  → spawn @ ENU (5000, 0, 1500), heading 270°     │ │
│ │  ◦ cruise_missile → trajectory file: traj_M01.csv               │ │
│ └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─── Composition (시나리오 동작) ────────────────────────────────┐ │
│ │ Sim Duration:    [ 60 ] s        Random Seed: [ 42 ]            │ │
│ │ Primary Target:  ⦿ Auto (가장 가까운)                           │ │
│ │                  ○ Manual: [ select... ]                        │ │
│ │ Time:            ⦿ sim_time   ○ real_time   ○ reference (v0.39) │ │
│ │ HIL:             ☐ Enable HIL DUT (HIL-1 setup 필요)            │ │
│ └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─── Validation ─────────────────────────────────────────────────┐ │
│ │ ✓ Map references resolved                                       │ │
│ │ ✓ Radar references resolved                                     │ │
│ │ ✓ Target references resolved                                    │ │
│ │ ✓ Coherence Validator: 6/6 passed                               │ │
│ │   - vertical_ref: WGS84 ellipsoid ✓                             │ │
│ │   - 해안선: ✓                                                   │ │
│ │   - 건물 anchor: ✓                                              │ │
│ │   - 해상: ✓                                                     │ │
│ │   - vertical_명시: ✓                                            │ │
│ │   - Simulation Domain: ✓ (radar 빔 max range < domain 경계)    │ │
│ │ ⚠ Warning: cruise_missile 의 trajectory 가 Domain 경계 근접     │ │
│ └────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

### 2.2 4 블록 (13 § 13.3.1)

**References** (§ 13.3.2):
- Map / Radar / Targets 자원 참조
- Resource Browser 에서 drag-drop 또는 + 버튼 추가
- × 로 제거

**Installation** (§ 13.3.3):
- 각 자원의 시뮬 내 배치
- Radar: position + heading + anchor
- Target: spawn 위치 + 또는 trajectory 파일

**Composition** (§ 13.3.4):
- Sim duration, random seed
- Primary Target 선택 (auto / manual)
- Time mode (v0.39: reference 추가)
- HIL toggle (v0.38)

**Validation** (§ 13.3.5):
- 자동 검증 결과 (실시간 갱신)
- ✓ / ⚠ / ✗ 표시
- Coherence Validator 6 항목

### 2.3 인터랙션

- **드래그 drop** Resource Browser → References
- **+ Add Target** → Resource Browser 에서 다중 선택 dialog
- **자동 저장** (3초 idle, 13 § 13.8.1) — tab 라벨 ` *` 사라짐
- **Validate** 버튼 → 6 검증 즉시 재실행, Validation 블록 갱신
- **Run** → Workspace 가 Simulator 로 전환, 이 시나리오 자동 load

---

## 3. Screen E-2 — Map Editor 🗺

**Maps 자원 편집**. 지형·건물·해안선·anchor 정의.
**파일**: `ui/editor/activities/map_editor.py`
**참조**: 13 § 13.4, 12 § 12.11 Flatten Area

### 3.1 레이아웃

```
┌────────────────────────────────────────────────────────────────────┐
│ Toolbar: [+ New] [💾 Save] [Import DEM] [Export] [Validate]        │
├────────────────────────────────────────────────────────────────────┤
│ Tabs: [ PortBusan_v2.toml ]                                        │
├──────────┬─────────────────────────────────────────────────────────┤
│ Tools    │                                                          │
│          │            3D Map Preview (PyVista)                      │
│ Pan      │                                                          │
│ Zoom     │       ╱╲___╱╲                                            │
│ Rotate   │      ╱       ╲___                                        │
│ ─────    │     ╱  ▣ Bldg     ╲                                      │
│ + Land   │    ╱_______________╲___                                  │
│ ⊕ Bldg   │   ━━━━━━━━━━━━━━━━━━━━━ ← coastline                     │
│ ▣ Coast  │   〰〰〰〰〰〰〰〰〰〰〰〰 ← sea                             │
│ ⌂ Anchor │                                                          │
│ ◯ Flatten│                                                          │
│ ─────    │   Drag to rotate · Shift+Drag pan · Wheel zoom           │
│ Layers   │                                                          │
│ ☑ Terrain│                                                          │
│ ☑ Bldg   │                                                          │
│ ☑ Coast  │                                                          │
│ ☑ Sea    │                                                          │
│ ☐ Grid   │                                                          │
├──────────┴─────────────────────────────────────────────────────────┤
│ Map Info:  PortBusan_v2 · 35.10~35.20 N · 129.40~129.50 E          │
│ DEM: SRTM 30m · 50 buildings · 3 anchors · sea_state 3            │
└────────────────────────────────────────────────────────────────────┘
```

### 3.2 도구 (§ 13.4.2)

- Pan / Zoom / Rotate (기본)
- + Land (육지 추가, 해안선 그리기)
- ⊕ Building (건물 추가)
- ▣ Coast (해안선 편집)
- ⌂ Anchor (anchor 추가, building 또는 free)
- **◯ Flatten Area (v0.33)** — 평탄화 영역 그리기
  - 폴리곤 그려서 그 영역의 DEM 평탄화
  - 함정 정박지·활주로·건물 부지

### 3.3 Layer 토글 (§ 13.4.3)
- ☑ Terrain (지형)
- ☑ Buildings
- ☑ Coast (해안선)
- ☑ Sea (해상)
- ☐ Grid (좌표 그리드)

### 3.4 Edit History (§ 13.4.4)
- Undo / Redo (Ctrl+Z / Ctrl+Y)
- 변경 사항 stack

### 3.5 DEM Import (§ 13.4.5)
- Wizard 7-step (v0.22)
- SRTM / DTED / GeoTIFF 지원

### 3.6 Building 추가 (§ 13.4.6)
- 클릭으로 polygon 그리기
- height 입력
- material 선택 (concrete / steel / wood)

---

## 4. Screen E-3 — Radar Editor 📡 (v0.25)

**RadarConfig 단일 폼**. 통합 입력 화면.
**파일**: `ui/editor/activities/radar_editor.py`
**참조**: 13 § 13.5

### 4.1 레이아웃

```
┌────────────────────────────────────────────────────────────────────┐
│ Toolbar: [+ New] [💾 Save] [Save As] [Test Beam]                   │
├────────────────────────────────────────────────────────────────────┤
│ Tabs: [ KS-1_default.toml ]                                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ Radar Name:    [ KS-1_default                  ]                    │
│ Description:   [ K-Series 1세대, FMCW Triangle ]                    │
│                                                                     │
│ ┌─── Waveform ────────────────────────────────────────────────────┐ │
│ │ Type:    ⦿ FMCW Triangle (MVP)                                  │ │
│ │          ○ FMCW Sawtooth (Phase 8.3+)                           │ │
│ │          ○ CW (MVP+α)                                           │ │
│ │ Center freq:  [ 9.4 ] GHz                                       │ │
│ │ Bandwidth:    [ 100 ] MHz                                       │ │
│ │ Sweep time:   [ 1.0 ] ms                                        │ │
│ │ Sample rate:  [ 50 ] MHz                                        │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─── Antenna ─────────────────────────────────────────────────────┐ │
│ │ Geometry:  ⦿ Parabolic (single dish)                            │ │
│ │            ○ Planar Array (4×4 monopulse)                       │ │
│ │ Diameter:    [ 0.6 ] m                                          │ │
│ │ Beamwidth:   [ 3.5 ] deg (auto-calculated)                      │ │
│ │ Polarization: [ Linear-V ]  ▾                                   │ │
│ │ Steering:    ⦿ Fixed     ○ Mechanical scan    ○ Electronic      │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─── DSP Pipeline ────────────────────────────────────────────────┐ │
│ │ Detector:           [ OS-CFAR (default) ]  ▾   [ Configure... ] │ │
│ │ Pairing:            [ default_pairing ]    ▾                    │ │
│ │ Angle Estimator:    [ monopulse_v1 ]       ▾                    │ │
│ │ Tracker:            [ EKF (default) ]      ▾   [ Configure... ] │ │
│ │ Predictor:          [ default ]            ▾                    │ │
│ │ Data Associator:    [ GNN (default) ]      ▾                    │ │
│ │ Classifier:         [ none ]               ▾                    │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─── Test Beam Preview (옵션) ────────────────────────────────────┐ │
│ │  Beam pattern at 0° / 1km                                       │ │
│ │  ─────────────                                                  │ │
│ │     ╱╲                                                          │ │
│ │    ╱  ╲   3.5° -3dB beamwidth                                   │ │
│ │   ╱    ╲___                                                     │ │
│ │  ╱  side lobes                                                  │ │
│ │  └──────────────                                                │ │
│ │ -10 -5 0 5 10 deg                                               │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

### 4.2 단일 폼 원칙 (v0.25)

13 § 13.5 의 핵심: **모든 RadarConfig 항목을 한 폼에**. 탭 분리 없음.
사용자가 위→아래 스크롤 만으로 전체 설정 보고 수정.

### 4.3 DSP Pipeline 영역

각 stage 의 plugin 선택 (드롭다운). [Configure...] 버튼은 plugin 별 옵션 dialog.

---

## 5. Screen E-4 — Targets Editor 🎯

**Target 메타 편집만**. trajectory 자체는 Composer 또는 외부 파일.
**파일**: `ui/editor/activities/targets_editor.py`
**참조**: 13 § 13.6

### 5.1 레이아웃

```
┌────────────────────────────────────────────────────────────────────┐
│ Toolbar: [💾 Save] [Trajectory Preview]                            │
├────────────────────────────────────────────────────────────────────┤
│ Tabs: [ boeing_737.toml ]                                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ Target Name:    [ boeing_737                              ]         │
│ Description:    [ Boeing 737-800 commercial airliner     ]         │
│                                                                     │
│ ┌─── Type & MotionKind ──────────────────────────────────────────┐ │
│ │ MotionKind:    [ AIRCRAFT ]  ▾  (v0.27, 7 categories)           │ │
│ │ Description:   "Airfoil-based powered flight, autopilot"         │ │
│ └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─── Geometry ───────────────────────────────────────────────────┐ │
│ │ Length:    [ 39.5 ] m       Wingspan: [ 35.8 ] m                │ │
│ │ Mass:      [ 64000 ] kg                                         │ │
│ └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─── Dynamics Limits (Aircraft) ─────────────────────────────────┐ │
│ │ Max climb rate:    [ 2400 ] ft/min     Max bank: [ 30 ] deg     │ │
│ │ Max load factor:   [ 2.5 ] g           V_stall:  [ 70 ] m/s     │ │
│ │ V_max:             [ 250 ] m/s         V_cruise: [ 220 ] m/s    │ │
│ └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─── RCS Model ──────────────────────────────────────────────────┐ │
│ │ Type:  ⦿ Single point (constant)                                │ │
│ │        ○ Aspect-dependent (table)                               │ │
│ │        ○ ExtendedTarget (v0.34, multi-scatterer + glint) ⭐     │ │
│ │ Mean RCS:  [ 50 ] m²                                            │ │
│ └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ┌─── Trajectory Reference ───────────────────────────────────────┐ │
│ │ ⦿ Auto-generate (Composer 의 spawn + heading 기반)              │ │
│ │ ○ External file:  [ ____________________ ]  [ Browse... ]       │ │
│ │ ○ Waypoint list:  (only for AIRCRAFT/SHIP)                      │ │
│ └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ Note: trajectory 자체는 Composer 의 Installation 에서 정의.        │
│       이 화면은 표적의 "정체성" (메타·동역학·RCS) 만.              │
└────────────────────────────────────────────────────────────────────┘
```

### 5.2 편집 가능 (MVP)

- 메타: 이름, description
- MotionKind (7 종)
- Geometry (length, mass, wingspan)
- Dynamics limits (motion_kind 별 다름)
- RCS Model (single / aspect / ExtendedTarget)

### 5.3 편집 불가 (MVP)

- Trajectory 직접 (Composer 가 담당)
- Sensor model (현재 시뮬 X)

### 5.4 Trajectory Preview

별도 dialog. 현재 설정으로 임의 spawn → trajectory 생성 → 3D plot 표시.

---

## 6. Screen E-5 — Resource Browser 📂 (전체 화면)

**전체 자원 한 눈에**. 1.3 의 sidebar 와 다름 — 전체 화면 grid view.
**파일**: `ui/editor/activities/resource_browser.py`
**참조**: 13 § 13.7

### 6.1 레이아웃

```
┌────────────────────────────────────────────────────────────────────┐
│ Toolbar: [Bulk Delete] [Export] [Import] [Refresh]                 │
├────────────────────────────────────────────────────────────────────┤
│ 🔍 [ Search resources...           ]   Filter: [ All ] ▾           │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ▼ Maps (3)                                          [Sort by ▾]    │
│ ┌──────────────┬──────────────┬──────────────┐                     │
│ │ 📍           │ 📍           │ 📍           │                     │
│ │ PortBusan_v2 │ OpenSea_basic│ SeoulCity    │                     │
│ │              │              │              │                     │
│ │ 35.10~35.20N │ 0~10N        │ 37.50~37.60N │                     │
│ │ 129.40-50E   │ 100-110E     │ 126.95-127.5 │                     │
│ │ 50 buildings │ 0 buildings  │ 200 buildings│                     │
│ │ 2 days ago   │ 5 days ago   │ 1 week ago   │                     │
│ └──────────────┴──────────────┴──────────────┘                     │
│                                                                     │
│ ▼ Radars (5)                                                       │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐      │
│ │ 📡 KS-1      │ 📡 KS-2      │ 📡 X-band    │ 📡 ...       │      │
│ │ ...          │ ...          │ ...          │              │      │
│ └──────────────┴──────────────┴──────────────┴──────────────┘      │
│                                                                     │
│ ▼ Targets (12)                                                     │
│ ▼ Scenarios (8)                                                    │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### 6.2 카드 표시
- 자원 type 아이콘
- 이름
- 핵심 메타 (지역·건물 수·표적 type 등)
- 마지막 수정 시간

### 6.3 Bulk 작업 (§ 13.7.2)
- 다중 선택 (Ctrl/Shift+클릭)
- Bulk Delete / Export

### 6.4 MVP+α
- 가져오기·내보내기 (.trsim-pkg DLC, v0.35)
- 카드 thumbnail (3D 미리보기)

---

## 7. 화면 간 흐름

```
[App 실행]
   │
   ▼
[Editor Workspace] (default)
   │
   ▼ Activity Selector (Ctrl+1~5)
   │
   ├→ E-1 Scenario Composer (메인) ─────► Run → Simulator Workspace
   ├→ E-2 Map Editor
   ├→ E-3 Radar Editor
   ├→ E-4 Targets Editor
   └→ E-5 Resource Browser

[모든 Activity 에서]
   ◄─── Resource Browser sidebar (좌측, 항상 표시)
   ◄─── Drag-drop 가능 (자원 → Composer References)
```

---

## 8. 영향 받는 plan 영역

| 영역 | 변경 |
|---|---|
| 13 editor_workspace | 본 mockup 으로 시각화 보강 |
| 12 § 12.11 Flatten Area | E-2 Map Editor 의 도구 (◯) |
| 14 § 14.5 MotionKind | E-4 Targets Editor 의 type |
| 16 § 16.2 ExtendedTarget | E-4 RCS Model 옵션 (v0.34) |
| 17 § 17.4.4 UI Panel Registry | DLC UI 패널 (v0.35) — Activity 추가 가능? (MVP+α) |

---

## 9. 미결정 사항 (UI 측)

- **E-U1**: Activity 6번째 — DLC plugin 이 추가할 수 있는가? (17 UIPanelProtocol 과 연계)
- **E-U2**: 다중 탭 max 개수 (성능)?
- **E-U3**: 자동 저장 vs 명시적 저장 (Q-T1 Resource History 와 연계)
- **E-U4**: Resource Browser sidebar 의 카테고리 customizable?
- **E-U5**: Target Trajectory Preview 의 3D plot 라이브러리 (PyVista 사용 일관)?

---

## 10. 다음 (UI mockup 작업)

남은 영역:
- Simulator Workspace 메인 화면 (Run/Pause/시각화)
- Plugin Manager UI (v0.35 DLC install)
- 4-error 진단 화면 (NN 모드 step 2)
- 옛 영역 (Screen 1~8 from v0.13~v0.27)

---

👉 HTML artifact 동행 (인터랙티브 mockup)
