# UI Mockup Spec — Welcome / Project Picker (v0.40)

**최종 갱신**: 2026-05-04
**대상 plan**: 01 § 1.1 정체성, 05 ui_ux, 13 editor_workspace, 19 § 19.5 (Physics Lab Workspace)
**대상 Phase**: Phase 4 (UI 기본)

---

## 0. 의도

**TRsim 처음 열 때 첫 화면**. 첫 인상 + 정체성 자연 노출 + 빠른 시작.

핵심 사용자 흐름:
```
[1] 앱 실행
[2] Welcome 화면 자동 (또는 메뉴: File > Welcome)
[3] 4 액션 중 선택:
    (a) New Scenario      → 템플릿 선택 (Maritime / Fixed Ground / Empty / Custom / Tutorial)
    (b) Open Scenario     → 파일 picker
    (c) Tutorial          → 5 Tutorial 시나리오
    (d) Plugin Manager    → DLC 둘러보기
[4] Recent projects 클릭으로 빠른 재진입
[5] What's New 박스 보고 새 기능 인지
```

---

## 1. Screen W-1 — Welcome / Project Picker

**파일**: `ui/welcome/welcome_window.py`
**참조**: 05 ui_ux

### 1.1 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────┐
│ TRsim                                                            ─ □ ×  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│        ╭──────────────╮                                                 │
│        │   ▲▽▲▽       │   TRsim Workbench                               │
│        │  ╲ │ ╱        │   v0.40                                         │
│        │   └──         │   추적 레이더 알고리즘·자원·시각화·물리 모델     │
│        │   📡          │   워크벤치 플랫폼                                │
│        ╰──────────────╯                                                 │
│                                                                          │
├──────────────────────────────────────┬──────────────────────────────────┤
│                                       │                                   │
│  Recent Projects                      │   Quick Start                    │
│  ─────────────                        │   ───────────                    │
│                                       │                                   │
│  📁 Maritime · Missile Defense   ★    │   ┌─────────────────┐           │
│     ~/trsim/maritime_md.toml          │   │  📐  New        │           │
│     2 hours ago · 12 runs · DSP+NN    │   │      Scenario   │           │
│                                       │   └─────────────────┘           │
│  📁 Fixed Ground · Aircraft           │                                   │
│     ~/trsim/fg_aircraft.toml          │   ┌─────────────────┐           │
│     yesterday · 8 runs · DSP          │   │  📂  Open       │           │
│                                       │   │      Scenario   │           │
│  📁 RCS Calibration · Trihedral 🟣    │   └─────────────────┘           │
│     ~/trsim/rcs_cal.toml              │                                   │
│     3 days ago · 24 runs · Physics    │   ┌─────────────────┐           │
│                                       │   │  🎓  Tutorial   │           │
│  📁 HIL · C6678 Loopback Test 🟠      │   │      Scenarios  │           │
│     ~/trsim/hil_c6678.toml            │   └─────────────────┘           │
│     1 week ago · 5 runs · HIL         │                                   │
│                                       │   ┌─────────────────┐           │
│  📁 Two-ray Multipath Sandbox         │   │  🧩  Plugin     │           │
│     ~/trsim/multipath_sandbox.toml    │   │      Manager    │           │
│     2 weeks ago · 3 runs · DSP        │   └─────────────────┘           │
│                                       │                                   │
│  [→ Show all 18 recent projects]      │                                   │
│                                       │                                   │
├──────────────────────────────────────┴──────────────────────────────────┤
│                                                                          │
│  ✨ What's New in v0.40                                                  │
│  ─────────────────────                                                   │
│  ⭐ Physics Lab — 인터랙티브 물리 실험실 (5번째 차별점)                  │
│     3-pane (Code / Visualization / Parameters) + 9 Test Objects + 4 시간 모드 │
│     [→ Try Physics Lab]                                                 │
│                                                                          │
│  ⚙ Force Composition — 사용자 물리 plugin 가능 (Validation Bench 안전망) │
│  📊 Reference Timing — frame 단위 시간 보정 (v0.39, HIL 기반)            │
│                                                                          │
│  [→ Read full release notes]                                            │
├─────────────────────────────────────────────────────────────────────────┤
│ [☐ Show on startup]                              v0.40.2 · Apache 2.0   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 영역 구성

#### A. Top Hero — Logo + 정체성 한 줄
- TRsim logo (작은 SVG — 빔 sweep + 표적)
- "TRsim Workbench"
- 버전 (v0.40)
- 한 줄 정체성: "추적 레이더 알고리즘·자원·시각화·물리 모델 워크벤치 플랫폼"

#### B. Left — Recent Projects
- 5개 표시 (~/.trsim/recent.json 기반)
- 행 정보 (Q-W-4=b):
  - 📁 이름
  - 경로 (회색)
  - 마지막 수정 시간
  - Run count
  - 사용 plugin/mode (DSP / NN / Physics / HIL — 색 hint)
- ★ 즐겨찾기 표시
- 영역 색 hint:
  - 🟣 Physics 시나리오
  - 🟠 HIL 시나리오
  - (DSP only 는 색 없음 — 일반)
- "Show all" 링크 → SIM-4 Run Manager 의 시나리오 history

#### C. Right — Quick Start (Q-W-1=d)
4 큰 액션 카드:
1. **📐 New Scenario** → 모달: 템플릿 선택
2. **📂 Open Scenario** → 파일 picker
3. **🎓 Tutorial Scenarios** → 5 tutorial 목록
4. **🧩 Plugin Manager** → Plugin Manager (PM-1) 직접

#### D. Bottom — What's New (Q-W-3=d)
- 큰 박스, 보라 stripe 강조
- v0.40 핵심: **Physics Lab** ⭐
- 부 항목 2~3 개
- "Read full release notes" → 외부 또는 in-app 보기
- 사용자 dismiss 가능 (다음 startup 시 v0.41 까지 안 보임)

#### E. Footer
- "Show on startup" 토글
- 버전 / license

### 1.3 New Scenario 모달 (Q-W-2=c)

큰 액션 1번 클릭 시 모달:

```
┌────────────────────────────────────────────────────────────────┐
│ New Scenario                                              [×]  │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Choose a template:                                              │
│                                                                 │
│ ▼ Templates                                                     │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│ │ 🌊 Maritime  │ 🏔 Fixed Gnd │ ⬜ Empty     │ 📁 Custom    │  │
│ │              │              │              │              │  │
│ │ 함정 RX +    │ 지상 RX +    │ 빈 시나리오  │ 외부 .toml    │  │
│ │ 해상 표적 +  │ 항공 표적    │ 처음부터     │ import       │  │
│ │ Sea State    │              │              │              │  │
│ └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                 │
│ ▼ Tutorial Scenarios (5)                                        │
│ ┌──────────────┬──────────────┬──────────────┐                  │
│ │ 🎓 Lesson 1  │ 🎓 Lesson 2  │ 🎓 Lesson 3  │                  │
│ │ First trace  │ Multi-target │ DSP↔NN cmp   │                  │
│ │ ★            │ ★★            │ ★★★          │                  │
│ └──────────────┴──────────────┴──────────────┘                  │
│ ┌──────────────┬──────────────┐                                 │
│ │ 🎓 Lesson 4  │ 🎓 Lesson 5  │                                 │
│ │ HIL setup    │ Physics Lab  │                                 │
│ │ ★★★          │ ★★            │                                 │
│ └──────────────┴──────────────┘                                 │
│                                                                 │
│ Selected: 🌊 Maritime                                           │
│                                                                 │
│ Project name: [maritime_2026_05_04_______]                      │
│ Location:     [~/trsim/______________________] [Browse]         │
│                                                                 │
│                          [Cancel]  [Create Scenario]            │
└────────────────────────────────────────────────────────────────┘
```

5 Tutorial:
1. **First trace** — 단일 표적 detect → track
2. **Multi-target** — GNN + multi-scatterer
3. **DSP↔NN compare** — 차별점 2 직접 시도
4. **HIL setup** — DUTAdapter 연결 (v0.38)
5. **Physics Lab** — 9 Test Objects 첫 시도 (v0.40)

### 1.4 색·시각 (Q-W-5=b)

기본: 중성 회색-청 (Plugin Manager 와 비슷, Welcome 자체는 "도구" 의 입구).
**영역별 hint** 만 절제:
- Recent project 의 mode badge (DSP gray / NN 보라 / Physics 보라 / HIL 주황)
- New Scenario 템플릿 카드 (Maritime 회청 / Fixed Ground 갈색 / Empty 회색 / Custom teal)
- What's New 박스 (Physics Lab 보라 stripe)

### 1.5 데이터 출처

- `app/welcome/recent_manager.py` — Recent projects (~/.trsim/recent.json)
- `app/welcome/templates.py` — 4 templates + 5 tutorials
- `app/welcome/release_notes.py` — What's New (in-app markdown)

---

## 2. 영향 받는 plan 영역

| 영역 | 변경 |
|---|---|
| 05 ui_ux | Welcome window 추가 |
| 04 Phase 4 | UI 체크리스트 |

---

## 3. 미결정 (UI 측)

- **W-U1**: 시작 시 자동 표시 vs 수동 (File > Welcome) default
- **W-U2**: Recent 의 max 개수 (5 / 10 / unlimited)
- **W-U3**: What's New 박스의 dismiss 정책 (한 번 / 매 startup)
- **W-U4**: Tutorial 시나리오의 in-app vs 외부 link

---

## 4. Phase 위치

- **Phase 4 MVP**: Welcome 기본 + Recent + 4 액션
- **Phase 4 보강**: What's New 박스 + Tutorial scenarios

---

👉 HTML artifact 동행
