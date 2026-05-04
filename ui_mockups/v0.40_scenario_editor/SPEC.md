# UI Mockup Spec — Scenario Editor 상세 (v0.40)

**최종 갱신**: 2026-05-04
**대상 plan**: 13 editor_workspace, 12 § 12.11 (Flatten Area), 11 (Coherence Validator), 03 § 3.2 dataclass
**대상 Phase**: Phase 4 (MVP) + Phase 4 보강

이전 mockup 점검: `/home/claude/ui_mockups/editor_workspace/SPEC.md` — 5 Activity 개요 + 공통 레이아웃 정리됨.
**이번 mockup**: 각 Activity 의 깊이 1 화면씩, 총 5 화면.

---

## 0. 의도

Editor Workspace 의 5 Activity 깊이 시각화. 이전 SPEC 의 개요 → 본 SPEC 의 깊이 (Activity 별 1 화면).

핵심 사용자 흐름 (5 Activity 통합):
```
[1] Workspace = Editor (이전 SPEC)
[2] 좌측 Activity Selector 5개 중 선택
[3] 각 Activity 깊이:

    SE-1 Scenario Composer  → 시나리오 자원 통합 + Coherence Validator
    SE-2 Map Editor         → DEM + Flatten Area + Left-Right 단면 view
    SE-3 Radar Editor       → RadarConfig 통합 폼 + 안테나 패턴 plot
    SE-4 Targets Editor     → Trajectory 작성 (waypoint + 속도 + 고도)
    SE-5 Resource Browser   → 모든 자원 전체 화면 (검색·필터·preview)

[4] Quick test → Simulator 로 즉시 검증
```

**시나리오**: Maritime · Missile Defense (Simulator mockup 과 동일, 흐름 추적).

---

## 1. Screen SE-1 — Scenario Composer ⭐

**가장 자주 보는 Activity.** 시나리오 자원 통합 + Coherence Validator.
**파일**: `ui/editor/scenario_composer.py`
**참조**: 13 § 13.3.1, 11 (Coherence Validator)

### 1.1 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Title: TRsim Workbench                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│ Workspace: 📐 Editor [active] | ▶ Simulator | 🔬 Physics Lab             │
├──┬──────────────────┬──────────────────────────────────────────────────┤
│  │                  │ Editor Toolbar:                                   │
│🎬│  Resource        │ [+ New] [💾 Save] [✓ Validate] [▶ Quick Test]    │
│🗺│  Browser sidebar ├──────────────────────────────────────────────────┤
│📡│                  │ Tab: [ Maritime · Missile * ] [+]                 │
│🎯│  🔍 Search       ├──────────────────────────────────────────────────┤
│📂│  ▼ Maps (3)      │                                                   │
│  │   📍 Donghae    │  ╭─ Scenario: Maritime Missile Defense ─╮         │
│⚙ │   📍 OpenSea     │  │ name = "maritime_missile_defense_v3"  │         │
│  │   📍 Busan       │  │ duration = 15.0  # seconds            │         │
│  │  ▼ Radars (5)    │  ╰────────────────────────────────────────╯         │
│  │   📡 KS-1 ⭐     │                                                   │
│  │   📡 KS-2        │  ┌─ Map ─────────────────────────────────┐        │
│  │  ▼ Targets (12)  │  │ → Donghae_30km.toml                    │        │
│  │   🎯 missile_1   │  │   [drag from sidebar / dropdown]       │        │
│  │   🎯 ship_1      │  │   ✓ DEM 30km × 30km, 사면 verified     │        │
│  │   🎯 ship_2      │  └────────────────────────────────────────┘        │
│  │  ▼ Scenarios (8) │                                                    │
│  │   🎬 base ⭐     │  ┌─ Radar (RX) ──────────────────────────┐        │
│  │   🎬 high_seas   │  │ → KS-1_default.toml                    │        │
│  │                  │  │   ✓ X-band FMCW 9.4GHz, 100MHz BW      │        │
│  │  Recent          │  │   Position: ship-mounted, ENU origin   │        │
│  │  Favorites       │  └────────────────────────────────────────┘        │
│  │                  │                                                    │
│  │                  │  ┌─ Targets (4) ─────────────────────────┐        │
│  │                  │  │ → 🎯 T1 missile_supersonic.toml ⚠      │        │
│  │                  │  │      Primary, 500 m/s, descending      │        │
│  │                  │  │ → 🎯 T2 ship_decoy_1.toml              │        │
│  │                  │  │      ballistic, 8 m/s                  │        │
│  │                  │  │ → 🎯 T3 ship_decoy_2.toml              │        │
│  │                  │  │ → 🎯 T4 ship_decoy_3.toml              │        │
│  │                  │  │   [+ Add Target]                       │        │
│  │                  │  └────────────────────────────────────────┘        │
│  │                  │                                                    │
│  │                  │  ┌─ Environment ─────────────────────────┐        │
│  │                  │  │ Sea state: 4 (slider)                  │        │
│  │                  │  │ Atm: ITU-R clear (no rain)             │        │
│  │                  │  │ Multipath: ☑ Two-ray  ☐ Custom plugin  │        │
│  │                  │  └────────────────────────────────────────┘        │
│  │                  │                                                    │
│  │                  │  ┌─ Coherence Validator ─────────────────┐        │
│  │                  │  │ ⚠ 1 warning · 0 errors                  │        │
│  │                  │  │                                         │        │
│  │                  │  │ ⚠ T1 missile speed (500m/s) near upper  │        │
│  │                  │  │   limit for "supersonic" template       │        │
│  │                  │  │   [→ View in Targets Editor]            │        │
│  │                  │  │ ✓ DEM ⇄ Radar ENU coordinates aligned    │        │
│  │                  │  │ ✓ Beam can reach all targets            │        │
│  │                  │  │ ✓ Run duration adequate                  │        │
│  │                  │  └────────────────────────────────────────┘        │
│  │                  │                                                    │
└──┴──────────────────┴──────────────────────────────────────────────────┘
```

### 1.2 핵심 영역

#### A. 자원 슬롯 (Map / Radar / Targets / Environment)
- 각 슬롯에 자원 reference (toml 파일)
- 드래그·드롭 또는 dropdown 선택
- 슬롯 옆 ✓ / ⚠ / ✗ 검증 상태
- 슬롯 클릭 → 해당 Activity 로 이동 (Map → SE-2)

#### B. Coherence Validator (Q-SE-6=b, plan 11 통합)

**자동 백그라운드 검증**:
- DEM ⇄ Radar 좌표계 (ENU origin 일치?)
- Beam 도달 범위 vs 표적 위치
- Run duration 적절성
- Target template 의 한계 (속도/고도)
- Plugin compatibility

**warnings vs errors 분리**:
- ⚠ warnings: 시뮬 실행 가능, 사용자 인지 필요
- ✗ errors: 시뮬 실행 불가, 수정 필수

각 warning 클릭 → 해당 Activity 로 이동 (drill).

#### C. Toolbar
- [+ New] / [💾 Save] / [✓ Validate] (수동 trigger) / **[▶ Quick Test]** (Simulator 로 즉시 실행)

### 1.3 Quick Test 흐름 (Editor → Simulator)

```
Editor Toolbar [▶ Quick Test]
       │
       │ 1. 현재 시나리오 자동 save (.toml)
       │ 2. Workspace 자동 전환 → Simulator
       │ 3. SIM-1 으로 자원 자동 로드
       │ 4. Run ▶ 자동 실행
       │
       ▼
   Simulator 의 SIM-1 (이미 실행 중)
```

이 흐름이 Editor / Simulator 분리하면서도 빠른 iteration 가능.

---

## 2. Screen SE-2 — Map Editor (Q-SE-3)

**DEM + Flatten Area + Left-Right 단면 view.**
**파일**: `ui/editor/map_editor.py`
**참조**: 12 § 12.11 (Flatten Area)

### 2.1 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Editor Toolbar: [+ New Map] [💾 Save] [📥 Import DEM] [📤 Export] [✓]   │
├─────────────────────────────────────────────────────────────────────────┤
│ Tab: [ Donghae_30km.toml * ] [+]                                         │
├──┬─────────────────────────────────────────────────────────────────────┤
│🎬│                                                                       │
│🗺│ ┌─ Map metadata ─────────────────────────────────────────────────┐  │
│📡│ │ Name: Donghae_30km   Origin: 37.5°N 129.5°E   Size: 30km×30km │  │
│🎯│ │ DEM resolution: 10m × 10m (3001×3001)         Min/Max: 0/240m │  │
│📂│ └────────────────────────────────────────────────────────────────┘  │
│  ├─────────────────────────────────────────┬───────────────────────────┤
│⚙ │                                          │                            │
│  │   ╔══════════════════════════════════╗   │  Tools                     │
│  │   ║                                  ║   │  ────                      │
│  │   ║                                  ║   │  ⦿ Select                  │
│  │   ║   2D Top-down DEM view           ║   │  ○ Pan                     │
│  │   ║   (heatmap, height = color)      ║   │  ○ Flatten Area            │
│  │   ║                                  ║   │  ○ Add coastline           │
│  │   ║   ────────────────                ║   │  ○ Add building            │
│  │   ║   ░░░░░░ ▒▒▒▒▒▒                  ║   │                            │
│  │   ║   ░░░░░░░▒▒▒▒▒▒▓▓                ║   │  Flatten Area              │
│  │   ║   ░░░░░░░▒▒▒▒▓▓▓▓                ║   │  ──── (Q-SE-3=b)            │
│  │   ║   ░░░░░░░░▒▒▓▓▓▓▓                ║   │                            │
│  │   ║   ░░░░██▒▒▓▓▓▓▓▓▓                ║   │  Mode: ⦿ Rectangle  ○ Free │
│  │   ║   ░░░░████████▓▓                 ║   │                            │
│  │   ║   ─── coastline ───              ║   │  Selection:                │
│  │   ║       sea  ░░░░░                 ║   │   x1: 12340 m              │
│  │   ║                                  ║   │   x2: 14820 m              │
│  │   ║   📍 Radar (RX) ship             ║   │   y1: 8950  m              │
│  │   ║                                  ║   │   y2: 11200 m              │
│  │   ╚══════════════════════════════════╝   │                            │
│  │   [zoom: 1x] [reset cam]                 │  Target height: [▆▆▆░] 5m  │
│  │                                          │  Mode: ⦿ Set ○ Add ○ Sub   │
│  ├──────────────────────────────────────────┤                            │
│  │ ── Left-Right cross-section ──── ⭐ Phase 4 보강                       │
│  │                                          │  [Apply Flatten]           │
│  │  height [m]   ↕  cross-section along selection center                 │
│  │   240 ┤  ╱────╲                          │  Last: applied to          │
│  │   180 ┤ ╱      ╲                         │   24,000 cells             │
│  │   120 ┤╱        ╲___    ╱─────╲          │                            │
│  │    60 ┤            ╲___╱       ╲___      │  Coherence:                │
│  │     0 ┤                            ──    │  ✓ slope OK                │
│  │       └──────────────────────────────    │  ✓ no negative DEM         │
│  │       0    8km   16km   24km   30km       │                            │
│  └──────────────────────────────────────────┴───────────────────────────┘
```

### 2.2 핵심 영역

#### A. 2D Top-down DEM view (MVP, Q-SE-3=b)
- DEM heightmap as heatmap (low → green, high → brown)
- 해안선 표시 (DEM ≤ 0 = 바다)
- 건물 / 표지물 markers
- Pan / Zoom / Reset camera
- 좌표 cursor (실시간)

#### B. Tools sidebar
- Select / Pan / Flatten Area / Add coastline / Add building
- 도구별 sidebar 변경

#### C. Flatten Area panel (활성 도구일 때, MVP)
- Mode: Rectangle / Free polygon
- Selection 좌표 표시
- **Target height 슬라이더** + Mode (Set / Add / Sub)
- Apply / Undo

#### D. Left-Right Cross-section view ⭐ Phase 4 보강
- 선택 영역 중심을 따라 cross-section
- 자동 갱신 (선택 영역 이동 시)
- height 시각 — 선택 영역 보기 + 주변 지형
- Flatten 결과 즉시 반영

#### E. Coherence panel (자동 백그라운드)
- DEM 사면 (gradient) 합리성
- 음수 height 검출
- 표적 trajectory 와 충돌 검사 (Targets 와 연동)

### 2.3 단계화

**MVP (Phase 4)**:
- 2D top-down + Flatten Rectangle + Target height 슬라이더
- 기본 Coherence (사면, 음수)

**Phase 4 보강**:
- Left-Right Cross-section view ⭐
- Free polygon Flatten
- Add building / coastline tools

---

## 3. Screen SE-3 — Radar Editor (Q-SE-4)

**RadarConfig 통합 폼 + 안테나 패턴 plot (빔포밍 only).**
**파일**: `ui/editor/radar_editor.py`
**참조**: 13 § 13.3.3, 03 § 3.2.1c

### 3.1 결정 정리 (Q-SE-4=b)

- **Beam Test = 안테나 패턴 plot only** (sinc² / array factor)
- 자유 공간 가정 (환경 X)
- Multipath / atm loss / refraction 등은 Simulator 또는 Physics Lab 영역
- Editor 안에 [▶ Quick Test in Simulator] 버튼 — 환경 영향 보고 싶으면 즉시 Simulator 진입

### 3.2 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Editor Toolbar: [+ New] [💾 Save] [📥 Import] [▶ Quick Test in Simulator]│
├─────────────────────────────────────────────────────────────────────────┤
│ Tab: [ KS-1_default.toml * ] [+]                                         │
├──┬─────────────────────────────────────────────────────────────────────┤
│🎬│                                                                       │
│🗺│ ┌─ Sections ─────────────────────────┬─────────────────────────────┐ │
│📡│ │                                     │                              │ │
│🎯│ │ ▼ Identity                          │  Antenna Pattern Plot        │ │
│📂│ │   Name:    KS-1_default              │  ──── (자동 갱신, sinc²)     │ │
│  │ │   Type:    FMCW                      │                              │ │
│⚙ │ │   Vendor:  Korean DDG-119           │  Power [dB]                 │ │
│  │ │                                     │     0 ┤  ╱╲                  │ │
│  │ │ ▼ RF                                │   -10 ┤ ╱  ╲                 │ │
│  │ │   Carrier:    9.4 GHz   [slider]    │   -20 ┤╱    ╲                │ │
│  │ │   Bandwidth:  100 MHz   [slider]    │   -30 ┤      ╲╱╲ ╱╲ ╱╲      │ │
│  │ │   Power:      10 kW                 │       └──────────────────    │ │
│  │ │   PRF:        5 kHz                 │       -90  -45   0   45  90 │ │
│  │ │                                     │       angle [deg]            │ │
│  │ │ ▼ Antenna                           │                              │ │
│  │ │   Type:    Parabolic                │  HPBW (3dB):  ~3.4°          │ │
│  │ │   Diameter: 1.2 m                   │  First null:  ±5.2°          │ │
│  │ │   Gain:     38.5 dBi                │  SLL:         -13.2 dB       │ │
│  │ │   HPBW:     3.4°  (auto)            │  Dir:         38.5 dBi       │ │
│  │ │                                     │                              │ │
│  │ │ ▼ Scan                              │  ┌─────────────────────┐    │ │
│  │ │   Mode:    Mechanical sweep          │  │  Polar plot          │    │ │
│  │ │   Range:   ±60° azimuth              │  │   ╱──╲              │    │ │
│  │ │   Rate:    30°/s                     │  │  ╱    ╲             │    │ │
│  │ │                                     │  │  │      │            │    │ │
│  │ │ ▼ Position (in Maritime scenario)   │  │  ╲    ╱             │    │ │
│  │ │   Mount:    Ship-borne               │  │   ╲──╱              │    │ │
│  │ │   Height:   28 m above sea           │  └─────────────────────┘    │ │
│  │ │   Stab:     ☑ Roll  ☑ Pitch          │                              │ │
│  │ │                                     │  Side plot:                  │ │
│  │ │ ▼ Pipeline default                  │  Range vs Doppler (clean)    │ │
│  │ │   Detector:  OS-CFAR                 │  ────────                    │ │
│  │ │   Tracker:   UKF (Default)          │   (placeholder)              │ │
│  │ │                                     │                              │ │
│  │ └─────────────────────────────────────┴─────────────────────────────┘ │
│  │                                                                       │
│  │ Coherence:                                                            │
│  │  ✓ Carrier within X-band                                              │
│  │  ✓ HPBW computed from antenna size correctly                          │
│  │  ⚠ Power 10kW high — confirm regulatory compliance                    │
│  │                                                                       │
└──┴───────────────────────────────────────────────────────────────────────┘
```

### 3.3 핵심 영역

#### A. RadarConfig 통합 폼 (좌)
**6 섹션** (collapsible):
- Identity — 이름·종류·vendor
- RF — carrier / bandwidth / power / PRF
- Antenna — type / size / gain / HPBW (auto)
- Scan — mode / range / rate
- Position — mount / height / stabilization (Maritime 시 ship-borne)
- Pipeline default — 권장 Detector / Tracker

#### B. Antenna Pattern Plot (우, 자동 갱신, Bret Victor 스타일)
- **Cartesian** (angle vs power) — sinc² 패턴
- **Polar** (방향 패턴)
- 파라미터 변경 시 즉시 갱신 (Antenna size 슬라이더 등)
- 핵심 metric: HPBW / First null / SLL / Directivity

#### C. Coherence
- 자동 검증 (X-band 범위 / HPBW 계산 / 규제 등)

### 3.4 환경 영향 분리

Editor 안에는 **자유 공간 안테나 패턴**만. 환경 영향 보고 싶으면:
- **[▶ Quick Test in Simulator]** 버튼 — Maritime 시나리오 자동 실행
- Multipath / atm loss / refraction 영향이 Simulator SIM-5 Probe Viewer 에서 stage 별 검사

이 분리가 Editor 의 정체성 ("자원 작성") + Simulator ("실행 관찰") + Physics Lab ("물리 모델 검증") 명확히.

---

## 4. Screen SE-4 — Targets Editor (Q-SE-5)

**Trajectory 작성 + 표적 종류별 차별 (해상/육상 vs 공중).**
**파일**: `ui/editor/targets_editor.py`
**참조**: 13 § 13.3.4

### 4.1 결정 (Q-SE-5=b + 단계화)

**MVP (Phase 4)**:
- 2D 지도 click 으로 waypoint 추가
- 구간별 속도 (m/s)

**Phase 4 보강**:
- 공중 표적: 고도 (m) 추가
- 표적 종류별 한계 속도 조언 (DB 기반)

### 4.2 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Editor Toolbar: [+ New] [💾 Save] [Test in Simulator]                    │
├─────────────────────────────────────────────────────────────────────────┤
│ Tab: [ T1 missile_supersonic.toml * ] [+]                                │
├──┬─────────────────────────────────────────────────────────────────────┤
│🎬│ ┌──────────────────┬──────────────────────────────────────────────┐ │
│🗺│ │ Target meta      │  2D Map view (Maritime, click to add waypoint) │ │
│📡│ │ ────             │                                                │ │
│🎯│ │ Name:            │   ●━━━━━●━━━━━●━━━━━●━━━━━●                  │ │
│📂│ │ T1 missile_sup   │   wp1   wp2   wp3   wp4   wp5                 │ │
│  │ │                  │  500   500   500   500   480 m/s              │ │
│⚙ │ │ Type: 🛫 Aerial  │                                                │ │
│  │ │ ⦿ Aerial         │   ┌─ DDG-119 (RX)                              │ │
│  │ │ ○ Surface        │   │                                             │ │
│  │ │ ○ Subsurface     │   │                                             │ │
│  │ │                  │                                                │ │
│  │ │ Template:        │   ░░░░░░░░░░░ sea ░░░░░░░░░░░░                │ │
│  │ │ ▾ supersonic     │                                                │ │
│  │ │   missile        │  [zoom 1x] [reset]                              │ │
│  │ │                  │                                                │ │
│  │ │ Limits:          │                                                │ │
│  │ │ Max speed:       │                                                │ │
│  │ │ 700 m/s          │                                                │ │
│  │ │                  │                                                │ │
│  │ │ Max altitude:    │                                                │ │
│  │ │ 15000 m          │                                                │ │
│  │ │                  │                                                │ │
│  │ ├──────────────────┼──────────────────────────────────────────────┤ │
│  │ │ Trajectory       │ Trajectory waypoint table                      │ │
│  │ │ Mode: Aerial     │ ┌──────┬──────┬──────┬──────┬──────────────┐ │ │
│  │ │                  │ │ # │ x [m] │ y [m] │ z [m] │ speed → next │ │ │
│  │ │ MVP:             │ ├──────┼──────┼──────┼──────┼──────────────┤ │ │
│  │ │  click to add    │ │ wp1 │ 12000 │  3000 │ 5000 │   500 m/s    │ │ │
│  │ │  speed slider    │ │ wp2 │ 10000 │  2400 │ 4500 │   500 m/s    │ │ │
│  │ │                  │ │ wp3 │  7000 │  1800 │ 3000 │   500 m/s    │ │ │
│  │ │ Phase 4+:        │ │ wp4 │  4000 │  1200 │ 1500 │   500 m/s    │ │ │
│  │ │  altitude (z)    │ │ wp5 │  1000 │   500 │  100 │   480 m/s    │ │ │
│  │ │  ⭐ aerial only  │ └──────┴──────┴──────┴──────┴──────────────┘ │ │
│  │ │                  │  [+ Insert] [⊥ Delete] [↑↓ Reorder]            │ │
│  │ │ Speed advice:    │                                                │ │
│  │ │ ⚠ Phase 4 보강   │ Profile preview:                                │ │
│  │ │  Max ≤ 700 m/s  │                                                │ │
│  │ │                  │  Speed [m/s]  ──────────────                    │ │
│  │ │ Coherence:       │   500 ┤━━━━━━━━━━━━╲                            │ │
│  │ │ ✓ all under max  │   400 ┤              ╲                           │ │
│  │ │ ✓ smooth         │   300 ┤                                          │ │
│  │ │   transition     │       └──────────                                │ │
│  │ │ ⚠ wp5 z=100m    │                                                │ │
│  │ │   very low       │  Altitude [m]  ⭐ Phase 4 보강                  │ │
│  │ │   (sea-skimmer)  │   5000 ┤▆▆▆▆╲                                   │ │
│  │ │                  │   3000 ┤      ╲                                  │ │
│  │ │                  │   1500 ┤        ╲                                │ │
│  │ │                  │     0 └─────────────                              │ │
│  │ │                  │                                                │ │
│  │ └──────────────────┴──────────────────────────────────────────────┘ │
└──┴───────────────────────────────────────────────────────────────────────┘
```

### 4.3 핵심 영역

#### A. Target meta (좌-상)
- Name
- **Type radio**: Aerial / Surface / Subsurface
  - Aerial → 고도 (z) 활성 (Phase 4+)
  - Surface → z = 0, 해상 또는 육상 (DEM 기반)
  - Subsurface → z 음수
- Template dropdown (supersonic missile / cargo ship / submarine 등)
- **Limits 자동** (template 기반):
  - Max speed (예: supersonic missile 700 m/s)
  - Max altitude (예: 15000 m)

#### B. 2D Map view (우-상, MVP Q-SE-5=b)
- Maritime 시나리오 위 click → waypoint 추가
- 기존 waypoint 드래그 가능
- Trajectory line 표시
- 인접 waypoint 사이 속도 표시

#### C. Trajectory 표 (우-중)
- 표 형식 — # / x / y / z / speed → next
- z (altitude) 활성/비활성 (Type Aerial 일 때만 — Phase 4+)
- Insert / Delete / Reorder
- 직접 편집 가능

#### D. Profile preview (우-하)
- **Speed 시계열** (MVP)
- **Altitude 시계열** ⭐ Phase 4 보강 (Aerial 일 때)
- 자동 갱신

#### E. Speed advice (좌-하, Phase 4+)
- 표적 종류별 max speed/altitude 자동 조언
- ⚠ 한계 초과 경고
- 예: "F-15 max ~750 m/s, current 800 m/s ⚠"

#### F. Coherence (좌-하)
- waypoints 의 가속도 합리성 (smooth)
- DEM 위 / 아래 충돌 검사 (Surface)
- 한계 초과 (Phase 4+)

### 4.4 단계화 정리

| 항목 | MVP (Phase 4) | Phase 4 보강 |
|---|---|---|
| 2D click waypoint | ✓ | |
| 구간별 속도 | ✓ | |
| 표적 종류 (radio) | ✓ (Aerial/Surface/Subsurface) | |
| Aerial 고도 (z) | ─ | ⭐ |
| Speed advice (max) | ─ | ⭐ |
| Altitude advice | ─ | ⭐ |
| Profile preview (altitude) | ─ | ⭐ |

---

## 5. Screen SE-5 — Resource Browser (전체 화면)

**Activity 5 — 모든 자원 전체 화면 + 검색 + filter + preview.**
**파일**: `ui/editor/resource_browser.py`
**참조**: 13 § 13.3.5

### 5.1 차이 — Sidebar vs Activity 5

| | Sidebar (상시) | Activity 5 (전체 화면) |
|---|---|---|
| 위치 | 좌측 항상 | 중앙 탭 |
| 크기 | 작음 | 큼 |
| 정보 | 이름·아이콘 | 이름·날짜·태그·preview·thumbnail |
| 작업 | 드래그·드롭 | 메타 편집·rename·delete·duplicate |

### 5.2 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Editor Toolbar: [+ New] [📥 Import] [🗑 Delete] [📤 Export]               │
├─────────────────────────────────────────────────────────────────────────┤
│ Tab: [ Resource Browser ] [+]                                            │
├──┬─────────────────────────────────────────────────────────────────────┤
│🎬│ ┌─ Filters ─────────────────────────────────────────────────────────┐ │
│🗺│ │ Type: [All ▾] [Maps] [Radars] [Targets] [Scenarios]               │ │
│📡│ │ Tags: [maritime] [supersonic] [+]   Author: [All ▾]                │ │
│🎯│ │ Search: [_________________________]                                │ │
│📂│ └────────────────────────────────────────────────────────────────────┘ │
│  │                                                                       │
│⚙ │ ▼ Maps (3)                                                            │
│  │ ┌──────────────┬──────────────┬──────────────┐                        │
│  │ │ 🗺 Donghae   │ 🗺 OpenSea    │ 🗺 Busan      │                        │
│  │ │   30km×30km  │   100km×100km│   15km×15km   │                        │
│  │ │   ⭐         │              │               │                        │
│  │ │              │              │               │                        │
│  │ │ DEM thumbnail│ DEM thumbnail│ DEM thumbnail │                        │
│  │ │ ░░▒▒▓▓       │ ░░░░░░       │ ▒▓▓▓░        │                        │
│  │ │              │              │               │                        │
│  │ │ Modified     │ Modified     │ Modified      │                        │
│  │ │ 2 hours ago  │ 3 days ago   │ 1 week ago    │                        │
│  │ │              │              │               │                        │
│  │ │ Tags:        │ Tags:        │ Tags:         │                        │
│  │ │ maritime,    │ open ocean   │ port,         │                        │
│  │ │ coastal      │              │ urban         │                        │
│  │ └──────────────┴──────────────┴──────────────┘                        │
│  │                                                                       │
│  │ ▼ Radars (5)                                                          │
│  │ ┌──────────────┬──────────────┬──────────────┐                        │
│  │ │ 📡 KS-1 ⭐   │ 📡 KS-2      │ 📡 KS-3 (NN) │                        │
│  │ │ X-band FMCW  │ X-band FMCW  │ X-band FMCW   │                        │
│  │ │ 9.4 GHz      │ 9.4 GHz      │ 9.4 GHz       │                        │
│  │ │ 100 MHz BW   │ 200 MHz BW   │ Tracker NN    │                        │
│  │ │              │              │               │                        │
│  │ │ Beam pattern │ Beam pattern │ Beam pattern  │                        │
│  │ │ thumbnail    │ thumbnail    │ thumbnail     │                        │
│  │ │              │              │               │                        │
│  │ │ HPBW 3.4°    │ HPBW 1.8°    │ HPBW 3.4°    │                        │
│  │ └──────────────┴──────────────┴──────────────┘                        │
│  │ ┌──────────────┬──────────────┐                                       │
│  │ │ 📡 ...       │ 📡 ...        │                                       │
│  │ └──────────────┴──────────────┘                                       │
│  │                                                                       │
│  │ ▼ Targets (12)  ▶ Scenarios (8)                                       │
│  │                                                                       │
│  │                                                                       │
│  │ Selected: 1 item                                                      │
│  │ ──────────────                                                         │
│  │ KS-1_default.toml                                                     │
│  │ Modified 2 hours ago, 28KB, used in 5 scenarios                       │
│  │ [Open] [Duplicate] [Rename] [Delete]                                  │
│  │                                                                       │
└──┴───────────────────────────────────────────────────────────────────────┘
```

### 5.3 핵심 영역

#### A. Filters (top)
- Type filter — All / Maps / Radars / Targets / Scenarios
- Tags filter — multi-select (maritime / supersonic / coastal 등)
- Author filter — 작성자 (협업 시)
- Search — 이름·태그·메타 fuzzy search

#### B. 자원 카드 그리드 (Plugin Manager 패턴 응용)
- **카테고리 별 그룹** (Maps / Radars / Targets / Scenarios)
- 카드 정보:
  - 이름 + ⭐ (즐겨찾기)
  - 핵심 메타 (DEM 크기, RF carrier, target type 등)
  - **Thumbnail / preview** (DEM heatmap / Beam pattern / Trajectory plot)
  - Modified time + Tags

#### C. 선택 자원 정보 (bottom)
- 선택 자원 메타 + 사용 위치 (몇 시나리오에서)
- 액션: Open / Duplicate / Rename / Delete / Export

### 5.4 그룹 collapse/expand

각 카테고리 ▼ ▶ 토글 — 작업 집중 시 다른 카테고리 접기.

---

## 6. 화면 간 흐름

```
[Workspace = Editor]
       │
       ▼
[Activity Selector — 5 + Settings]
       │
       ├── 🎬 SE-1 Scenario Composer ⭐ (default)
       │       │
       │       ├── 자원 슬롯 클릭 → 다른 Activity 로 drill
       │       │   - Map 슬롯 → SE-2
       │       │   - Radar 슬롯 → SE-3
       │       │   - Target 슬롯 → SE-4
       │       │
       │       └── [▶ Quick Test] → Workspace 전환 → Simulator SIM-1
       │
       ├── 🗺 SE-2 Map Editor
       │       └── Flatten / DEM 편집 → SE-1 의 Map 슬롯 자동 갱신
       │
       ├── 📡 SE-3 Radar Editor
       │       │
       │       └── [▶ Quick Test in Simulator] → Workspace 전환
       │
       ├── 🎯 SE-4 Targets Editor
       │       └── Trajectory 편집 → SE-1 자동 갱신
       │
       └── 📂 SE-5 Resource Browser
               └── Open → 해당 Activity 로
```

---

## 7. CLI 대응

```bash
# Scenario 작성 (programmatic)
trsim editor scenario new maritime_md.toml \
    --map donghae_30km --radar ks-1_default \
    --targets t1_missile,t2_ship,t3_ship,t4_ship

# Validate
trsim editor validate maritime_md.toml --coherence

# Quick test
trsim sim run maritime_md.toml  # 직접 시뮬

# Map editing
trsim editor map flatten donghae_30km.toml \
    --area "12340,8950,14820,11200" --height 5

# Antenna pattern compute
trsim editor radar pattern ks-1_default --plot polar.png
```

---

## 8. 영향 받는 plan 영역

| 영역 | 변경 |
|---|---|
| 13 editor_workspace | Activity 깊이 시각화 보강 |
| 12 § 12.11 Flatten Area | Left-Right 단면 view 추가 (Phase 4 보강) |
| 11 Coherence Validator | Editor UI 통합 |
| 03 § 3.2.1 dataclass | Target 의 Aerial/Surface/Subsurface 구분 |
| 04 Phase 4 / 보강 | 분량 분리 |

---

## 9. MVP 단계화 ⭐ (너 추가)

| 항목 | Phase 4 MVP | Phase 4 보강 (MVP+) |
|---|---|---|
| **SE-2 Map Editor** | | |
| 2D top-down DEM | ✓ | |
| Flatten Rectangle | ✓ | |
| Target height 슬라이더 | ✓ | |
| 기본 Coherence (사면, 음수) | ✓ | |
| **Left-Right Cross-section view** | | ⭐ |
| Free polygon Flatten | | ✓ |
| Add building / coastline | | ✓ |
| **SE-3 Radar Editor** | | |
| RadarConfig 6 섹션 | ✓ | |
| 안테나 패턴 plot (sinc²) | ✓ | |
| Polar plot | ✓ | |
| HPBW / SLL / Directivity 자동 | ✓ | |
| Quick Test in Simulator | ✓ | |
| **SE-4 Targets Editor** | | |
| 2D click waypoint | ✓ | |
| 구간별 속도 | ✓ | |
| 표적 종류 radio | ✓ | |
| Trajectory 표 + Profile (speed) | ✓ | |
| **공중 표적 고도 (z)** | | ⭐ |
| **표적 종류별 한계 속도 조언** | | ⭐ |
| **Altitude profile preview** | | ⭐ |
| **SE-1 Scenario Composer** | | |
| 자원 슬롯 + 검증 | ✓ | |
| Coherence Validator (DEM/Beam/Duration) | ✓ | |
| Quick Test | ✓ | |
| **SE-5 Resource Browser** | | |
| 카드 그리드 + filter | ✓ | |
| Thumbnail / preview | ✓ | |
| Tags + Author filter | ✓ | |

---

## 10. 미결정 (UI 측)

- **SE-U1**: 자원 충돌 시 (같은 이름 두 .toml) 처리 — version naming?
- **SE-U2**: 시나리오 다중 사용 자원 변경 시 자동 갱신 vs 명시 update
- **SE-U3**: Coherence 의 "errors" 와 "warnings" 의 구체적 임계값
- **SE-U4**: Map Editor 의 DEM 해상도 변경 (downsampling) 정책
- **SE-U5**: Targets Editor 에서 trajectory smoothing 제공 여부
- **SE-U6**: 표적 종류별 한계 속도 DB 출처 (위키·기관 등)
- **SE-U7**: Resource Browser 의 thumbnail 자동 생성 시점 (저장 시 / 백그라운드)

---

## 11. Phase 위치

- **Phase 4 MVP**: SE-1 + SE-2 (기본) + SE-3 + SE-4 (기본) + SE-5
- **Phase 4 보강 (MVP+)**: SE-2 Left-Right + SE-4 고도/속도 조언

---

👉 HTML artifact 동행 (5 화면 인터랙티브)
