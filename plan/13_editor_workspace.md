# 13. Editor Workspace 상세 설계

**최종 갱신**: 2026-04-28 (v0.35)

**관련 문서**: [10 workspaces](10_workspaces.md), [05 ui_ux](05_ui_ux.md), [09 radar_platforms](09_radar_platforms.md), [11 coordinate_systems](11_coordinate_systems.md), [12 placement_and_motion](12_placement_and_motion.md)

## 13.1 왜 이 문서가 있나

[10 § 10.3.2](10_workspaces.md#1032-editor-workspace-v019-신설)에서 Editor Workspace를
"자원 편집·조립의 공간"으로 정의했지만 **상세는 미정**으로 남겨뒀다 (어제 미결).

이 문서에서:
- Editor Workspace의 **전체 레이아웃** 결정 (Activity + 탭 + 사이드바)
- 5개 Activity 각각의 **진입·전환·저장 흐름**
- **MVP 범위와 MVP+α 경계** 명시
- 기존 결정들 (v0.18 Installation, v0.21 좌표계, v0.22 자체 규격 지형, v0.25 Antenna Editor)을 **하나의 일관된 UI 흐름**으로 통합

## 13.2 핵심 결정 — Activity + 탭 + 상시 사이드바

### 13.2.1 레이아웃 모델

VS Code 스타일을 채택:

```
┌──────────────────────────────────────────────────────────────────────┐
│  [📐 Editor ← active] [▶ Simulator]    Workspace Selector           │
├──────────────────────────────────────────────────────────────────────┤
│  Editor Toolbar  (File | New | Save | Validate | Open in Simulator) │
├──┬───────────────────────┬───────────────────────────────────────────┤
│🎬│  Resource Browser     │  ┌─ B_Conflict ─┬─ EastCoast_50km ┬─ + ┐ │
│🗺 │  (상시 사이드바)       │  │   active      │                    │ │
│📡│                       │  ├──────────────┴────────────────────┤ │
│🎯│  Scenarios (3)         │  │                                    │ │
│📂│   ✓ B_Conflict          │  │   (현재 활성 탭의 편집 영역)         │ │
│  │   ⏤ A_Base              │  │   — Activity 따라 다름              │ │
│  │   ⏤ Custom              │  │                                    │ │
│  │                       │  │   🎬 Scenario Composer                │ │
│  │  Maps (2)             │  │   🗺  Map Editor                      │ │
│  │   ⏤ EastCoast_50km     │  │   📡 Radar Editor                     │ │
│  │   ⏤ Harbor_10km         │  │   🎯 Targets Editor                   │ │
│  │                       │  │   📂 Resource Browser (전체 화면)      │ │
│  │  Radars (3)           │  │                                    │ │
│  │   ⏤ fmcw_corvette       │  │                                    │ │
│  │   ⏤ planar_16x16        │  │                                    │ │
│  │                       │  │                                    │ │
│  │  Targets (2)          │  │                                    │ │
│  │   ⏤ CrossingShips        │  │                                    │ │
│  │                       │  │                                    │ │
│  │  [+ New ...]          │  │                                    │ │
│  └───────────────────────┴──┴────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│  Status Bar  (저장됨/수정됨, hash 일치 상태, Coherence 검증 결과)      │
└──────────────────────────────────────────────────────────────────────┘
```

### 13.2.2 좌측 Activity Selector

5개 아이콘. 위에서부터:

| 아이콘 | Activity | 역할 | MVP |
|---|---|---|---|
| 🎬 | **Scenario Composer** | Map + Radar + Targets 조합, Installation, Run 메타 | ✅ (핵심) |
| 🗺 | **Map Editor** | DEM import, terrain.npz 편집, 건물 배치 | ✅ (경량) |
| 📡 | **Radar Editor** | Antenna + RX 채널 + Waveform 편집 | ✅ (v0.25) |
| 🎯 | **Targets Editor** | 메타 편집, trajectory 시각화 | ✅ (편집은 MVP 후) |
| 📂 | **Resource Browser** | 전체 자원 목록 (사이드바 확장 보기) | ✅ |

Activity 클릭 시:
- 해당 Activity의 **마지막 활성 자원**이 메인 영역에 열림
- 처음이면 빈 상태 + "Open ..." 안내

**Scenario Composer를 첫 번째**에 두는 이유: Editor의 **주 목적이 조합**이기 때문. 다른
Editor들은 거기서 호출되는 도구 성격.

### 13.2.3 Resource Browser (좌측 상시 사이드바)

**항상 표시**. Activity 전환과 독립적. 폭 조절 가능 (200~400px), 접기 가능.

```
┌─ Resource Browser ──────────┐
│ [⌕ filter ____]              │  ← 검색
│                             │
│ ▼ Scenarios (3)             │
│   ✓ B_Conflict 🟢            │  🟢 = 현재 활성, 모든 ref hash 일치
│   ⏤ A_Base ⚠                │  ⚠ = 참조 자원 hash 불일치 (자원 수정됨)
│   ⏤ Custom                  │
│ ▼ Maps (2)                  │
│   ⏤ EastCoast_50km            │
│   ⏤ Harbor_10km              │
│ ▼ Radars (3)                │
│   ⏤ fmcw_corvette            │
│   ⏤ planar_16x16             │
│   ⏤ fmcw_tower               │
│ ▼ Targets (2)               │
│   ⏤ CrossingShips             │
│   ⏤ SingleApproach            │
│                             │
│ [+ New Resource ▾]           │  → Map / Radar / Targets / Scenario
└─────────────────────────────┘
```

**기능**:
- 더블클릭 → 해당 자원이 **연관 Activity의 새 탭**으로 열림 (Map → Map Editor 등)
- 우클릭 컨텍스트 메뉴: Open / Open in Tab / Duplicate / Rename / Delete / Show in Files / Export Bundle
- 드래그 → Scenario Composer 영역으로 끌어 놓으면 자동 ref 추가
- 자원별 상태 표시:
  - `🟢` 활성 (현재 Scenario에 참조됨)
  - `⚠` 자원 hash 변경됨 (Scenario의 ref와 불일치)
  - `🔒` Built-in (수정 불가)
  - `⏤` 일반

### 13.2.4 중앙 탭 영역

**여러 자원을 동시에 열어두고 비교**할 수 있도록. 탭은 Activity 종류와 무관하게 섞일 수
있음 (예: Map 탭 옆에 Radar 탭).

- 탭 클릭 → 활성화 + 해당 Activity로 **자동 전환** (Activity Selector도 동기화)
- 탭 아이콘으로 종류 구분 (🎬/🗺/📡/🎯)
- 미저장 변경 표시 ● (탭 이름 옆)
- 우클릭 컨텍스트: Close / Close Others / Close All / Pin / Split (MVP+α)

**Pin** (MVP+α): 자주 보는 자원을 항상 첫 자리에 고정.

### 13.2.5 상단 Editor Toolbar

```
[File ▾] [+ New ▾] [💾 Save] [💾 Save As] [✓ Validate] [📦 Export Bundle] [▶ Open in Simulator]
```

- **File**: Open Recent / Open from Path / Import Bundle
- **+ New**: Map / Radar / Targets / Scenario (Resource Browser의 + 와 동일)
- **Save**: 활성 탭 자원 저장 (Ctrl+S)
- **Save As**: 새 이름으로 fork (10 § 10.10 정책)
- **Validate**: Coherence Validator 수동 실행 (11 § 11.7)
- **Export Bundle**: 활성 Scenario를 .scnbundle로 (10 § 10.11)
- **Open in Simulator**: Simulator Workspace로 전환 + 활성 Scenario 자동 로드

---

## 13.3 Activity 1: Scenario Composer 🎬 (핵심)

Editor Workspace의 **메인 활동**. 자원들을 골라서 시뮬 가능한 Scenario로 조립.

### 13.3.1 화면 구성

```
┌─ Scenario: B_Conflict_hilltop ────────────────────────────────────┐
│                                                                   │
│  Name: [B_Conflict_hilltop_______]   Version: 1.2  Hash: ...      │
│  Description: [_________________________________________________] │
│                                                                   │
│  ┌─ References ──────────────────────────────────────────────┐    │
│  │  🗺 Map     [EastCoast_50km        ▾]  hash: def... 🟢    │    │
│  │             [Open in Map Editor]                            │    │
│  │                                                             │    │
│  │  📡 Radar   [fmcw_tower             ▾]  hash: ghi... 🟢    │    │
│  │             [Open in Radar Editor]                          │    │
│  │                                                             │    │
│  │  🎯 Targets [CrossingShips           ▾]  hash: jkl... ⚠    │    │
│  │             ⚠ 자원이 수정됨. [Update ref] / [Reload current]│   │
│  │             [Open in Targets Editor]                        │    │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─ Installation ────────────────────────────────────────────┐    │
│  │  (v0.18 Installation 내용 — 09 § 9.6, 05 § 5.3.8 통합)     │    │
│  │                                                             │    │
│  │  Position:                                                  │    │
│  │    East:  [1250.0  ] m    North: [3400.0  ] m              │    │
│  │    Alt:   [87.3    ] m    (DEM 자동 + 안테나 높이)          │    │
│  │  Initial AZ: [180.0]°   EL: [0.0]°                         │    │
│  │                                                             │    │
│  │  ┌─ DEM Map (top-down) ────────────────────────────────┐   │    │
│  │  │   (육상=초록 / 해상=파랑 / land_mask 시각화)          │   │    │
│  │  │     ⬢ 설치 위치     /\                              │   │    │
│  │  │       ↗ AZ 180°   가시 cone                          │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  │                                                             │    │
│  │  Coverage Stats:                                            │    │
│  │   Max range: 28.4 km   Obstructed: 3/72 sectors (4%)       │    │
│  │   Blind bearings: 045° / 120° / 280°                       │    │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─ Composition (Run 메타) ──────────────────────────────────┐    │
│  │  Primary Target ID: [1   ▾]  (CrossingShips의 표적 중)      │    │
│  │  Seed:              [42  ]                                  │    │
│  │  Duration:          [60.0] s                                │    │
│  │  Frame rate:        [20  ] Hz                               │    │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─ Validation ──────────────────────────────────────────────┐    │
│  │  ✓ All refs resolved                                        │    │
│  │  ⚠ Targets ref hash mismatch (1 issue)                      │    │
│  │  ✓ Installation valid                                       │    │
│  │  [Run Validator] for detailed Coherence check               │    │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│       [Save]  [Save As]  [Export Bundle]  [▶ Open in Simulator]   │
└───────────────────────────────────────────────────────────────────┘
```

### 13.3.2 References 블록

- 각 자원 슬롯은 **드롭다운**으로 라이브러리에서 선택 또는 새로 만들기
- "Open in ... Editor" 버튼으로 해당 자원 편집 (다른 Activity 탭 열림)
- **hash 상태 인디케이터**:
  - 🟢 ref hash와 자원 현재 hash 일치
  - ⚠ 불일치 (자원이 수정됨) — `[Update ref]` 또는 `[Reload current]` 버튼
  - 🔴 자원 missing (참조 깨짐)
- Drag & Drop: Resource Browser에서 자원 끌어와 슬롯에 드롭

### 13.3.3 Installation 블록

v0.18 Installation 화면 ([05 § 5.3.8](05_ui_ux.md#538-installation-화면-v018-신설))이
**Scenario Composer 안에 통합**됨 (별도 모달 아님).

- DEM Map은 **선택된 Map의 land_mask** 시각화 (육상=초록, 해상=파랑)
- 클릭으로 설치 위치 지정 (DEM에서 자동 고도 샘플)
- v0.21 anchor 시스템에 따라 base_altitude 결정
- 차폐 Coverage 통계 (09 § 9.7)

**Run 중에는 read-only**: Target RUNNING/PAUSED 상태에서 Editor 들어와도 Installation 수정 불가
([05 § 5.3.8e](05_ui_ux.md#538e-run-중에는-installation-진입-불가)).

### 13.3.4 Composition 블록

Scenario 고유 메타 (자원에 종속되지 않는 것):
- Primary Target ID — 선택된 Targets 자원의 표적 중
- Seed — RNG 시드
- Duration — Run 길이
- Frame rate — trajectory 샘플링 주기

### 13.3.5 Validation 블록

**실시간 자동 검증**:
- ref 해결 여부 (자원이 라이브러리에 존재)
- ref hash 일치
- Installation 정합성 (위치가 Map 안, 해상에 건물 없음 등)

`[Run Validator]` 클릭 시 **Coherence Validator 종합 실행** (11 § 11.7) — 5종 검사 결과 표시.

### 13.3.6 저장 동작 (10 § 10.10 정책 준수)

`[Save]`:
- 사용자 소유 Scenario면 즉시 덮어쓰기
- Built-in이면 경고 다이얼로그 → "Save As New" 권장

`[Save As]`:
- 새 이름 입력 → my_scenarios/<new_name>/ 복제

`[Export Bundle]`:
- 현재 Scenario + 참조 자원 전부를 .scnbundle (10 § 10.11)

`[▶ Open in Simulator]`:
- 자동 저장 (또는 미저장 변경 확인) → Simulator로 전환 → 자동 로드 → Installation 자동 적용

### 13.3.7 MVP 범위

✅ **포함**:
- 자원 ref 선택·교체
- Installation 통합
- Composition 메타 편집
- 실시간 Validation
- Save/SaveAs/Bundle/Open in Simulator

❌ **제외 (MVP+α)**:
- Multi-radar Scenario (한 시뮬에 여러 레이더)
- Scenario 비교 모드 (두 Scenario diff)
- 템플릿 (자주 쓰는 조합 저장)

---

## 13.4 Activity 2: Map Editor 🗺 (경량)

DEM import + terrain.npz 편집 + 건물 배치. v0.22에서 결정된 **MVP 경량** 범위 ([12 § 12.11](12_placement_and_motion.md#1211-지형-편집-도구-editor-workspace-v022)).

### 13.4.1 화면 구성

```
┌─ Map Editor — EastCoast_50km ────────────────────────────────────┐
│                                                                  │
│  Name: [EastCoast_50km____]  Version: 1.2  Hash: def...           │
│                                                                  │
│  ┌─ Map Properties ────────────────────────────────────────┐    │
│  │  Origin: 37.5665°N, 126.9780°E   Vertical: egm96         │    │
│  │  Bounds: ±25 km E/N    Resolution: 10 m                  │    │
│  │  Sea Surface z: [0.0] m                                  │    │
│  │  [Edit Origin... 🔒]  ← 생성 후 변경 불가                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ Tools ─────────────────┐  ┌─ Map Canvas ───────────┐         │
│  │ [Pan] [Land/Sea Brush] │  │  (top-down 2D view)     │         │
│  │ [Spot Edit z]           │  │                         │         │
│  │ [Flatten Area] 🆕        │  │   (terrain + buildings) │         │
│  │ [Add Building]          │  │                         │         │
│  │ [Coastline ⏸]           │  │   land_mask 표시:        │         │
│  │                         │  │     초록 = 육상           │         │
│  │ Brush:                  │  │     파랑 = 해상           │         │
│  │   Mode: ●Land ○Sea     │  │                         │         │
│  │   Size: [5] px          │  │   Layers:                │         │
│  │                         │  │   ☑ Terrain heightmap   │         │
│  │ Spot Edit:              │  │   ☑ Land/Sea mask        │         │
│  │   z target: [12.5] m    │  │   ☑ Buildings            │         │
│  │   Apply at click       │  │   ☐ Coastline polygon   │         │
│  │                         │  │   ☐ Source DEM (참조)    │         │
│  │ Flatten Area: 🆕         │  │                         │         │
│  │   Mode: Rectangle       │  │   [- +][R]              │         │
│  │   Target z: [15.0] m    │  │                         │         │
│  │   ☐ Land only           │  │                         │         │
│  │   ☐ Preserve buildings  │  │                         │         │
│  │   [Apply to selection] │  │                         │         │
│  │                         │  │                         │         │
│  │ Buildings: 5            │  │                         │         │
│  │   Tower_5 (87.0m)       │  │                         │         │
│  │   ...                   │  │                         │         │
│  └─────────────────────────┘  └─────────────────────────┘         │
│                                                                  │
│  ┌─ Edit History ──────────────────────────────────────────┐    │
│  │  12 edits  [Undo] [Redo]   [↶ Reset to source DEM]       │    │
│  │  · 10:30 land_mask_paint (polygon_A)                     │    │
│  │  · 10:32 spot_edit (Tower_5, 87.4 → 87.0)                │    │
│  │  · 10:35 flatten_area (1200,3300)→(1500,3500), z=15.0    │    │
│  │  · ...                                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│         [Cancel]  [Save]  [Import DEM ...]  [Validate]           │
└──────────────────────────────────────────────────────────────────┘
```

### 13.4.2 도구

**MVP 범위** (12 § 12.11):

| 도구 | 동작 | 상태 |
|---|---|---|
| Pan/Zoom | Google Maps 식 (휠 줌, 드래그 팬) | ✅ |
| Land/Sea Brush | 픽셀별 land_mask 페인트 (육상 ↔ 해상) | ✅ |
| Spot Edit z | 클릭 위치의 elevation 값 수정 | ✅ |
| **Flatten Area** | **사각형 영역 z 단일값 통일** (정박지·활주로·부지) | ✅ **v0.33** |
| Add Building | 건물 추가 (anchor mode 선택) | ✅ |
| Coastline Polygon | 해안선 폴리곤 직접 편집 | ⏸ MVP+α |
| Smooth/Sharpen | 지형 부드럽게/날카롭게 | ⏸ MVP+α |
| Crop | Map 영역 변경 | ⏸ MVP+α |
| Flatten 확장 | 폴리곤 / Brush 반경 / min/avg/max 모드 | ⏸ MVP+α |

### 13.4.3 Layer 토글

- Terrain heightmap (등고선 또는 색 그라데이션)
- Land/Sea mask (override layer)
- Buildings (위에서 본 footprint)
- Coastline polygon (자동 또는 사용자 정의)
- Source DEM (참조용, terrain.npz와 비교)

### 13.4.4 Edit History

- 모든 편집은 `[op, area, params, time]`으로 기록 (12 § 12.11.3)
- Undo/Redo 50개 (MVP)
- "Reset to source DEM" — 모든 편집 무효화 후 원본에서 재변환

### 13.4.5 DEM Import

`[Import DEM ...]` 클릭:
- v0.22 Import Wizard (11 § 11.5) 시작
- 7 step (포맷 감지 → vertical ref 다이얼로그 → 영역 → land/sea 구분 → 변환 → 보간 → 저장)
- 기존 terrain.npz가 있으면 "기존 편집을 보존하시겠어요?" 다이얼로그

### 13.4.6 Building 추가·편집

Map Canvas에서 클릭 또는 우측 Buildings 목록에서:

```
┌─ Building: Tower_5 ──────────────────┐
│  Name:   [Tower_5________]            │
│  Position: E [1250.0] N [3400.0]      │
│  Mesh:    [tower_50m.stl ▾]            │
│  Mesh origin: [base_center ▾]          │
│                                       │
│  Anchor Mode:                         │
│   (•) base_to_terrain  (DEM 자동)      │
│   ( ) explicit_alt    [____] m        │
│   ( ) floor_at_msl                    │
│   ( ) terrain_offset  [____] m        │
│                                       │
│  Computed base z: 87.4 m (DEM sample)  │
│                                       │
│         [Cancel]  [Apply]              │
└───────────────────────────────────────┘
```

해상 영역(land_mask=False)에 건물 배치 시도 시 거부 (12 § 12.8.6).

### 13.4.7 MVP 범위

✅ **포함**: Pan/Zoom, Land/Sea Brush, Spot Edit, **Flatten Area** (v0.33), Add Building, DEM Import, Edit History
❌ **제외 (MVP+α)**: Smooth/Sharpen, Coastline 폴리곤 직접 편집, Crop, Multi-DEM 합성

---

## 13.5 Activity 3: Radar Editor 📡 (v0.25 명세)

이미 [05 § 5.3.9](05_ui_ux.md#539-radar-editor-editor-workspace-v025-신설)에서 상세
정의됨. 여기서는 **Editor Workspace 통합 측면**만 추가:

### 13.5.1 진입

- Resource Browser에서 Radar 더블클릭 → Radar Editor 탭 새로 열림
- Scenario Composer의 Radar 슬롯에서 "Open in Radar Editor" → 같은 동작

### 13.5.2 통합 폼 (드롭다운 중심)

[05 § 5.3.9b](05_ui_ux.md#539b-통합-에디터--안테나-타입-드롭다운-중심-q3-결정) 참조:
- AntennaType 드롭다운 → 동적 폼
- RX 채널 모드 라디오 → monopulse 그룹 활성/비활성
- Beam Pattern Preview 실시간

### 13.5.3 Save 동작

[10 § 10.10](10_workspaces.md#10100-재현성--content-hash--run-manifest-v020) 정책:
- 사용자 소유 → 즉시 덮어쓰기
- Built-in → "Save As New" 권장
- 저장 시 content_hash 자동 재계산 → Scenario에서 참조하는 곳에 ⚠ 표시

---

## 13.6 Activity 4: Targets Editor 🎯 (메타 편집만)

v0.21 Q에서 결정: **MVP에서 trajectory 편집 GUI는 제외**, CSV import + 메타 편집·시각화만
([12 § 12.7.3](12_placement_and_motion.md#1273-mvp에서-표적-궤적-편집은-미포함)).

### 13.6.1 화면 구성

```
┌─ Targets Editor — CrossingShips ─────────────────────────────────┐
│                                                                  │
│  Name: [CrossingShips______]  Version: 1.0  Hash: jkl...          │
│  Trajectory file: trajectories.csv  [Reload] [Open in editor]    │
│                                                                  │
│  ┌─ Targets ────────────────────────┐  ┌─ Trajectory Preview ┐   │
│  │ ● Target #1                       │  │  (Map 위 trajectory)  │   │
│  │   motion_kind: [SURFACE_VESSEL ▾]│  │    Map: [B_Conflict ▾]│   │
│  │   wave_response: [large_ship ▾]   │  │      (선택해서 prev)  │   │
│  │   RCS model: [simple_aspect ▾]    │  │                      │   │
│  │   Peak RCS: [-5.0] dBsm           │  │   ━━━●━━●━━●━━━●━━   │   │
│  │   Start: t=0  E=12000 N=5000     │  │      Target 1         │   │
│  │   End:   t=60 E=18000 N=7000     │  │   ╲╲╲╲╲╲             │   │
│  │   Waypoints: 60                   │  │      Target 2 (-8dBsm) │   │
│  │                                   │  │                      │   │
│  │ ⏤ Target #2                        │  │   [- +][R]            │   │
│  │   motion_kind: [SURFACE_VESSEL ▾]│  └──────────────────────┘   │
│  │   ...                             │                              │
│  │                                   │   ⚠ Read-only:               │
│  │ [+ Add Target] (CSV 통해)          │      Trajectory CSV 직접     │
│  │                                   │      편집 → Reload          │
│  └───────────────────────────────────┘                              │
│                                                                  │
│       [Cancel]  [Save]  [Open trajectories.csv in OS]            │
└──────────────────────────────────────────────────────────────────┘
```

### 13.6.2 편집 가능한 것 (MVP)

- Target별 메타: motion_kind, wave_response, RCS model/params
- 표적 추가/삭제는 **CSV 직접 편집 후 Reload**로

### 13.6.3 편집 불가 (MVP)

- Trajectory waypoint 추가/이동/삭제 — CSV에서 직접
- 표적 ID 변경 — CSV에서 직접

### 13.6.4 Trajectory Preview

읽기 전용 시각화:
- Map 선택 (Scenario에 묶여 있지 않으니 자유 선택)
- 표적별 trajectory 색 구분
- 시간 슬라이더로 시점 표시

### 13.6.5 검증

- Map 경계 밖 waypoint → 경고
- 해상 motion_kind인데 trajectory z가 비합리적 → 경고
- (Coherence Validator는 Scenario 단위에서 종합 실행, 11 § 11.7)

### 13.6.6 MVP+α

- Waypoint 그래픽 편집 (드래그 추가)
- 시간·위치 표 형식 편집 (Excel 식)
- 패턴 generator (직선, 원호, 교차 등 자동 생성)

---

## 13.7 Activity 5: Resource Browser 📂 (전체 화면 보기)

> ⚠️ **v0.35 정합**: Resource Browser는 v0.35 DLC ResourceLibrary 확장 (10 § 10.9, 17 § 17.4.3) 와 통합:
>
> - 자원 출처 3개 표시: **User** (`~/.trsim/resources/`) / **Package: <id>** (DLC) / **Built-in**
> - DLC 자원도 동일 UI에서 검색·선택 가능
> - **Plugin Manager 통합** (옵션): Resource Browser에 `📦 Packages` 섹션 추가 — 설치된 `.trsim-pkg` 목록, manifest 정보, install/uninstall 버튼
>
> MVP+α (Phase 7) 시점에 정식 통합. MVP는 Resource Browser 자체만 — DLC 시스템 없음.

좌측 사이드바의 확장 형태. 자원이 많아지면 검색·필터·정렬·일괄 작업에 유용.

### 13.7.1 화면 구성

```
┌─ Resource Browser ────────────────────────────────────────────────┐
│                                                                   │
│  [⌕ Search ___________]  Filter: [All ▾]  Sort: [Modified ▾]      │
│                                                                   │
│  Type    Name              Modified         Hash       Size  Use  │
│  ─────   ───────────────   ─────────────   ────────   ────  ───  │
│  🎬     B_Conflict_hill   2026-04-25 14:20  ✓ ok       8 KB   3↑  │
│  🎬     A_Base             2026-04-23 11:00  ⚠ stale    7 KB   1↑  │
│  🗺     EastCoast_50km     2026-04-25 09:00  ✓ ok       4.2 MB 2↓  │
│  🗺     Harbor_10km        2026-04-22 17:00  ✓ ok       1.1 MB 1↓  │
│  📡    fmcw_corvette       2026-04-24 10:00  ✓ ok       3 KB   1↓  │
│  📡    planar_16x16        2026-04-25 13:00  ✓ ok       4 KB   2↓  │
│  📡    fmcw_tower          2026-04-21 08:00  ✓ ok       3 KB   2↓  │
│  🎯    CrossingShips         2026-04-25 12:00  ⚠ edited   24 KB  3↑  │
│  🎯    SingleApproach        2026-04-20 09:00  ✓ ok       18 KB  0    │
│                                                                   │
│  Bulk: [Export All ...] [Validate All] [Show in Files]            │
└───────────────────────────────────────────────────────────────────┘
```

`Use` 컬럼:
- ↑ (참조됨, 다른 자원에서 사용 중)
- ↓ (참조 중, 다른 자원을 사용함)
- 숫자 = 카운트

### 13.7.2 Bulk 작업 (MVP)

- Export Selected → Bundle
- Validate All → Coherence 일괄 검사
- Show in Files → OS 파일 탐색기 열기

### 13.7.3 MVP+α

- 자원 dependency graph 시각화 (자원 간 ref 관계)
- 정합 깨진 자원 일괄 수정
- 사용 안 되는 자원 정리 (orphan resources)

---

## 13.8 Workspace 공통 동작

### 13.8.1 자동 저장

- 명시적 Save만 (auto-save 없음, MVP 기준)
- 미저장 변경은 탭 이름에 ● 표시
- Workspace 닫을 때 또는 Simulator로 전환 시 미저장 변경 다이얼로그

### 13.8.2 미저장 변경 다이얼로그

```
┌─ Unsaved Changes ──────────────────────────────┐
│ 다음 자원에 저장되지 않은 변경이 있습니다:      │
│                                                │
│ ● B_Conflict_hilltop (Scenario)                │
│ ● CrossingShips (Targets)                      │
│                                                │
│ [Save All]  [Discard All]  [Cancel]            │
│                                                │
│ ☐ 다시 묻지 않기                                │
└────────────────────────────────────────────────┘
```

### 13.8.3 Coherence Validator 통합

11 § 11.7의 5종 Validator는 다음 시점에 자동 실행:
- 자원 변경 시 (Map Editor·Radar Editor·Targets Editor에서)
- Scenario Composer 열 때
- Save 직전
- "Open in Simulator" 클릭 시 (전환 차단 가능 — Error 있으면)

결과는 Status Bar + Validation 블록에 표시.

### 13.8.4 단축키 (Editor Workspace 한정)

| 단축키 | 동작 |
|---|---|
| Ctrl+S | 활성 탭 저장 |
| Ctrl+Shift+S | Save As |
| Ctrl+W | 탭 닫기 |
| Ctrl+Shift+T | 닫은 탭 다시 열기 |
| Ctrl+Tab | 탭 전환 |
| Ctrl+1~5 | Activity 전환 (1=Composer, 2=Map, 3=Radar, 4=Targets, 5=Browser) |
| Ctrl+Shift+V | Validate |
| Ctrl+E | Export Bundle |
| F5 | Open in Simulator |

(공통 단축키는 [05 § 5.5.3](05_ui_ux.md#553-단축키-정책))

---

## 13.9 Workspace 전환 통합

### 13.9.1 Editor → Simulator

`[▶ Open in Simulator]` 또는 F5:
1. 미저장 변경 확인
2. 활성 Scenario를 Simulator의 Scenario Explorer가 자동 로드
3. Installation 자동 적용 (이미 Composer에서 결정)
4. Simulator Workspace로 전환 (DockLayout 교체)
5. Target Run 가능 상태

### 13.9.2 Simulator → Editor

Simulator에서 메뉴 또는 단축키 (Ctrl+Shift+E):
1. Sim RUNNING이면 자동 PAUSE 확인 다이얼로그
2. Editor로 전환
3. **마지막 편집 위치 복원** — 어느 Activity, 어느 탭, 어느 자원을 보고 있었는지 (10 § 10.5)

### 13.9.3 "Back to Editor" 컨텍스트

Run 완료 후 Simulator의 알림에서:
```
Run completed (Run #5).
[View Results] [Run Again] [Back to Editor]
```

`[Back to Editor]` → Editor Workspace로 복귀 + 방금 실행한 Scenario를 Composer에서 활성화.

---

## 13.10 MVP 구현 우선순위

### Phase A (MVP 핵심)
- [ ] Activity Selector + 5 Activity 골격
- [ ] Resource Browser 사이드바 + 자원 트리
- [ ] Scenario Composer (References + Composition + Save 흐름)
- [ ] Radar Editor (v0.25 명세 그대로)
- [ ] Workspace 전환 (Editor ↔ Simulator)

### Phase B (MVP 필수)
- [ ] Map Editor 경량 (Land/Sea Brush + Spot Edit + Add Building)
- [ ] DEM Import Wizard 통합
- [ ] Installation을 Scenario Composer 안에 통합
- [ ] Targets Editor (메타 편집 + 시각화)
- [ ] Coherence Validator 통합

### Phase C (MVP+α)
- [ ] Bundle Export/Import 풀 흐름
- [ ] Trajectory 편집 GUI
- [ ] Map Editor 고급 도구 (Smooth, Coastline, Crop)
- [ ] Resource Browser 고급 (dependency graph 등)
- [ ] Multi-Scenario diff/compare

---

## 13.11 Open Questions

이 문서의 미결 사항은 **OPEN_QUESTIONS.md**에 Q-EW1~5로 정식 등록됨 (v0.27):

- Q-EW1: 탭 split (한 화면 두 자원)
- Q-EW2: Resource Browser 검색·필터 범위
- Q-EW3: Editor 미니 preview (배치 검증용)
- Q-EW4: Auto-save 정책
- Q-EW5: Resource Dependency 시각화 시점

## 섹션 상태

- 13.1 개요 — ✅
- 13.2 레이아웃 (Activity + 탭 + 사이드바) — ✅
- 13.3 Scenario Composer — ✅ (Editor의 메인)
- 13.4 Map Editor — ✅ (MVP 경량)
- 13.5 Radar Editor — ✅ (05 § 5.3.9 참조)
- 13.6 Targets Editor — ✅ (메타만, trajectory 편집은 MVP+α)
- 13.7 Resource Browser — ✅
- 13.8 공통 동작 — ✅ (저장·검증·단축키)
- 13.9 Workspace 전환 — ✅
- 13.10 구현 우선순위 — ✅
- 13.11 Open Questions — 🟡

---

👉 이전: [12_placement_and_motion.md](12_placement_and_motion.md)
