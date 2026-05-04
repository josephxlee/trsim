# UI Mockup Spec — Plugin Manager (v0.40)

**최종 갱신**: 2026-05-02
**대상 plan**: 17 open_platform (DLC + .trsim-pkg + 11 Plugin Protocol), 19 § 19.7 (PhysicsModelProtocol + Validation Bench), 02 § 2.6b SDK Layer
**대상 Phase**: Phase 7 (DLC 시스템, MVP+α Wave 2)

---

## 0. 의도

**Plugin Manager** = TRsim 의 DLC 에코시스템 핵심 UI. v0.35 의 .trsim-pkg + v0.40 의 PhysicsModelProtocol 통합 관리.

**VS Code Extensions Marketplace 패턴** — 카테고리 별 plugin 카드, install / uninstall, dependency, 검증 상태.

핵심 사용자 흐름:
```
[1] Plugin Manager 열기 (메뉴 또는 Workspace 어디서나)
[2] Browse 탭 → 카테고리 (Tracking / Physics / etc.) 선택
[3] Plugin 카드 클릭 → Detail 화면 (README / dep / validation)
[4] [+ Install] → 다운로드 + 의존성 해결 + 자동 검증
[5] Installed 탭 → 활성/비활성 토글, version 관리, uninstall
[6] PhysicsModel plugin: Validated 표시, Unvalidated 사용 시 시뮬 실행 시점 경고
```

---

## 1. Screen PM-1 — Installed Plugins

**현재 설치된 plugin 목록 (flat).**
**파일**: `ui/plugin_manager/installed_panel.py`

### 1.1 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Plugin Manager · TRsim                                              [×] │
├─────────────────────────────────────────────────────────────────────────┤
│ Tabs: [📦 Installed (8)] [🔍 Browse] [📂 Local Install]                  │
├─────────────────────────────────────────────────────────────────────────┤
│ Search: [_______________]   Filter: [All ▾] [Active] [⚠ Unvalidated]    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ ✓ ☑  trsim-core-detectors           v1.2.0  (built-in)           │    │
│ │      OS-CFAR, CA-CFAR, GO/SO-CFAR detectors                      │    │
│ │      DetectorProtocol  ·  by Anthropic                            │    │
│ │      [Settings]  [Update]                                         │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ ✓ ☑  trsim-trackers-classic         v0.8.3                       │    │
│ │      EKF, UKF, IMM tracker implementations                        │    │
│ │      TrackerProtocol  ·  by tracking-research-lab                 │    │
│ │      [Settings]  [Update available 0.8.4 →]                       │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ ✓ ☑  torch-lstm-tracker             v0.4.0                       │    │
│ │      LSTM-based tracker (NN, PyTorch)                             │    │
│ │      TrackerProtocol  ·  by deepradar/research                    │    │
│ │      🧠 NN plugin · trained on 5000 trajectories                   │    │
│ │      [Settings]  [Trace inputs]                                   │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ ✓ ☑  4ray-multipath-physics ⭐      v0.2.1                       │    │
│ │      4-ray multipath model (maritime)                             │    │
│ │      PhysicsModelProtocol  ·  category: propagation               │    │
│ │      ✓ Validated · 17/17 tests pass · ref: Smith 2023             │    │
│ │      [Settings]  [Open in Physics Lab]                            │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ ⚠ ☑  magnus-effect-physics ⭐       v0.1.0                       │    │
│ │      Magnus effect for spinning targets                            │    │
│ │      PhysicsModelProtocol  ·  category: dynamics                  │    │
│ │      ⚠ UNVALIDATED — usage will warn in Simulator                 │    │
│ │      [Settings]  [Validate in Physics Lab]                        │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ ✓ ☑  tcp-json-dut-adapter           v0.5.0                       │    │
│ │      Generic TCP/JSON HIL adapter                                 │    │
│ │      DUTAdapterProtocol  ·  by Anthropic                          │    │
│ │      [Settings]                                                   │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ ✓ ☐  korean-coastline-resources     v1.0.5                       │    │
│ │      Korean peninsula DEM + coastline data                        │    │
│ │      ResourceProtocol  ·  by ko-radar-comm                        │    │
│ │      [Settings]                                                   │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ ✓ ☑  custom-plot-panel              v0.2.0                       │    │
│ │      Custom UI panel — Doppler waterfall                          │    │
│ │      UIPanelProtocol  ·  by user-local                            │    │
│ │      [Settings]                                                   │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│ Storage: 47 MB used of allocated  ·  ~/.trsim/packages/                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 행 구성

각 plugin 행:
- **상태 아이콘**: ✓ healthy / ⚠ unvalidated / ✗ broken / 🔒 disabled
- **Active 토글**: ☑/☐
- **Plugin name** + version
- **Description** (한 줄)
- **Protocol type** + author/source
- **NN/Physics 표시**: 🧠 NN plugin / ⭐ PhysicsModel plugin
- **검증 상태** (PhysicsModel 만): ✓ Validated · 17/17 tests / ⚠ UNVALIDATED
- **Actions**: [Settings] [Update] [Open in {Workspace}] [Validate]

### 1.3 카테고리별 색

행의 좌측 stripe (3px) 색:
- DetectorProtocol / PairingProtocol / AngleEstimator → 노랑 (Detection 영역)
- TrackerProtocol / Predictor / Classifier / DataAssociator → 회청 (Simulator 색)
- ResourceProtocol → teal (Editor 색)
- UIPanelProtocol → 회색 (UI)
- DUTAdapterProtocol → 주황 (HIL 색)
- **PhysicsModelProtocol → 보라** (Physics Lab 색) ⭐
- NN plugin → 보라 (학술, Physics Lab 과 통일)

### 1.4 Search / Filter

- Search: name / description / author
- Filter dropdown:
  - All
  - Active only
  - **Unvalidated (PhysicsModel)** — v0.40 안전망 강조
  - Updates available
  - By category

---

## 2. Screen PM-2 — Browse ⭐ 핵심

**11 카테고리 그룹 + plugin 카드.** VS Code Marketplace 스타일.

### 2.1 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Plugin Manager · Browse                                             [×] │
├─────────────────────────────────────────────────────────────────────────┤
│ Tabs: [📦 Installed] [🔍 Browse] [📂 Local Install]                      │
├─────────────────────────────────────────────────────────────────────────┤
│ Sources: ⦿ awesome-trsim  ○ GitHub URL  ○ Local file                     │
│ Search: [____________________]  Sort: [Popular ▾]                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ ▼ Detection (3)                                                          │
│ ┌────────────────┬────────────────┬────────────────┐                     │
│ │ 🟡 OS-CFAR-NN  │ 🟡 sea-clutter │ 🟡 adapt-thresh│                     │
│ │ NN-based OS    │ Sea state-     │ Adaptive       │                     │
│ │ CFAR detector  │ aware CFAR     │ threshold tune │                     │
│ │ Detector · NN  │ Detector       │ Detector       │                     │
│ │ ⭐ 124 · v0.3  │ ⭐ 89 · v1.1   │ ⭐ 45 · v0.8   │                     │
│ │ [Install]      │ [Install]      │ [Installed ✓]  │                     │
│ └────────────────┴────────────────┴────────────────┘                     │
│                                                                          │
│ ▼ Tracking (5)                                                           │
│ ┌────────────────┬────────────────┬────────────────┐                     │
│ │ 🔵 EKF/UKF     │ 🔵 IMM tracker │ 🔵 PMHT tracker│                     │
│ │ Classical KF   │ Interacting    │ Probabilistic  │                     │
│ │ family         │ multi-model    │ MHT            │                     │
│ │ Tracker        │ Tracker        │ Tracker        │                     │
│ │ ⭐ 312 · v0.8  │ ⭐ 156 · v0.5  │ ⭐ 78 · v0.2   │                     │
│ │ [Installed ✓]  │ [Install]      │ [Install]      │                     │
│ └────────────────┴────────────────┴────────────────┘                     │
│ ┌────────────────┬────────────────┐                                      │
│ │ 🧠 LSTM-track  │ 🧠 transformer │                                      │
│ │ LSTM-based     │ Transformer    │                                      │
│ │ tracker (NN)   │ tracker (NN)   │                                      │
│ │ Tracker · NN   │ Tracker · NN   │                                      │
│ │ ⭐ 234 · v0.4  │ ⭐ 67 · v0.1β  │                                      │
│ │ [Installed ✓]  │ [Install]      │                                      │
│ └────────────────┴────────────────┘                                      │
│                                                                          │
│ ▼ Physics ⭐ (v0.40, 4)                                                  │
│ ┌────────────────┬────────────────┬────────────────┐                     │
│ │ 🟣 4ray-multi  │ 🟣 magnus-eff  │ 🟣 GTD-rcs     │                     │
│ │ 4-ray multi-   │ Magnus effect  │ GTD-based RCS  │                     │
│ │ path (marin)   │ for spinning   │ for complex    │                     │
│ │ Physics·prop   │ Physics·dyn    │ Physics·refl   │                     │
│ │ ✓ Validated    │ ⚠ Unvalid      │ ✓ Validated    │                     │
│ │ ⭐ 92 · v0.2   │ ⭐ 34 · v0.1   │ ⭐ 56 · v0.3   │                     │
│ │ [Installed ✓]  │ [Installed ✓]  │ [Install]      │                     │
│ └────────────────┴────────────────┴────────────────┘                     │
│ ┌────────────────┐                                                       │
│ │ 🟣 ducting-prop│                                                       │
│ │ Atm ducting    │                                                       │
│ │ propagation    │                                                       │
│ │ Physics·atm    │                                                       │
│ │ ✓ Validated    │                                                       │
│ │ ⭐ 28 · v0.1   │                                                       │
│ │ [Install]      │                                                       │
│ └────────────────┘                                                       │
│                                                                          │
│ ▼ Resource (2)                                                           │
│ ┌────────────────┬────────────────┐                                      │
│ │ 🟢 korean-coast│ 🟢 us-coastal  │                                      │
│ │ Korean DEM +   │ US coastal     │                                      │
│ │ coastline      │ DEM + maps     │                                      │
│ │ Resource       │ Resource       │                                      │
│ │ ⭐ 67 · v1.0.5 │ ⭐ 89 · v0.8   │                                      │
│ │ [Installed ✓]  │ [Install]      │                                      │
│ └────────────────┴────────────────┘                                      │
│                                                                          │
│ ▼ UI Panel (1)                                                           │
│ ▼ HIL Adapter (2)                                                        │
│                                                                          │
│ Source: [awesome-trsim] github.com/anthropic/awesome-trsim               │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 카테고리 그룹 (Q-PM-3=b)

```
▼ Detection — DetectorProtocol / PairingProtocol / AngleEstimator
▼ Tracking — TrackerProtocol / Predictor / Classifier / DataAssociator
▼ Physics ⭐ v0.40 — PhysicsModelProtocol (5 sub-cat: propagation/reflection/dynamics/atmosphere/antenna)
▼ Resource — ResourceProtocol (Map/Radar/Target loader)
▼ UI Panel — UIPanelProtocol
▼ HIL Adapter — DUTAdapterProtocol
```

### 2.3 Plugin 카드 구성

각 카드 (200×140px 정도):
- **카테고리 색 stripe** (좌측 또는 상단 3px)
- **아이콘** (카테고리 별 이모지 — 🟡 Detect / 🔵 Track / 🟣 Physics / 🧠 NN / 🟢 Resource / 🟠 HIL)
- **Plugin name**
- **Short description**
- **Protocol type · sub-category**
- **검증 상태** (PhysicsModel 만): ✓ Validated / ⚠ Unvalidated
- **Stats**: ⭐ stars · version
- **Action**: [Install] / [Installed ✓] / [Update v0.x →]

### 2.4 Sources (Q-PM-2=d)

- ⦿ **awesome-trsim** — 중앙 정리 list (github.com/anthropic/awesome-trsim 같은 곳)
- ○ **GitHub URL** — 직접 입력 (예: `github.com/user/my-tracker`)
- ○ **Local file** — `.trsim-pkg` 파일 선택

### 2.5 Sort / Filter

- Sort: Popular / Recently updated / Most installed / Alphabetical
- Filter (왼쪽 collapsible side):
  - Category checkboxes
  - License (Apache / MIT / GPL / etc.)
  - **NN plugin only**
  - **Validated only** (PhysicsModel 일 때 강조)
  - Author

---

## 3. Screen PM-3 — Plugin Detail (Drill)

**단일 plugin 의 상세 정보.** Browse 의 카드 클릭 → 이 화면.

### 3.1 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Plugin Manager · 4ray-multipath-physics                             [×] │
├─────────────────────────────────────────────────────────────────────────┤
│ ← Back to Browse                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ 🟣 4ray-multipath-physics                                v0.2.1          │
│ 4-ray multipath model for maritime radar                                 │
│ PhysicsModelProtocol · category: propagation · ⭐ 92 · 1247 installs     │
│                                                                          │
│ ┌─────────────────────────┐   [✓ Installed]  [Open in Physics Lab]     │
│ │ ✓ Validated             │   [Uninstall]    [Settings]                  │
│ │ 17/17 tests passed      │                                              │
│ │ Reference: Smith 2023   │                                              │
│ └─────────────────────────┘                                              │
│                                                                          │
├──────────────────────────────────────────────┬──────────────────────────┤
│                                               │                           │
│ Tabs: [README] [Validation] [Dep] [Source]   │  Sidebar                  │
│                                               │                           │
│ # 4-ray Multipath Physics Plugin              │  Author                   │
│                                               │  smith-radar-lab         │
│ This plugin extends TRsim's propagation       │  github.com/smith-radar  │
│ models with a 4-ray multipath simulation,    │                           │
│ accounting for direct, sea-reflected,         │  Published                │
│ and two atmospheric reflected rays.           │  2026-04-15              │
│                                               │                           │
│ ## Use cases                                  │  Last updated             │
│ - Maritime radar with low-altitude targets    │  2026-04-28              │
│ - High-fidelity sea-state-aware simulation    │                           │
│                                               │  License                  │
│ ## Comparison                                 │  Apache 2.0              │
│ vs trsim built-in two-ray:                    │                           │
│ - Adds 2 atmospheric ray paths                │  Repository               │
│ - +15% fidelity in maritime scenes            │  github.com/smith-radar/  │
│ - +25% computation cost                       │  4ray-multipath          │
│                                               │                           │
│ ## Reference                                  │  Stats                    │
│ Smith, J. (2023). "4-ray multipath model for  │  ⭐ 92 stars              │
│ maritime radar." IEEE Trans. Aerospace.       │  📥 1247 installs         │
│                                               │  🐛 3 open issues         │
│ ## Compatibility                              │                           │
│ - TRsim: ≥ v0.40                              │  Categories               │
│ - Physics Layer: yes                          │  · propagation            │
│ - Validation Bench: 17 standard tests         │  · maritime               │
│                                               │                           │
│                                               │  Tags                     │
│                                               │  multipath, maritime,     │
│                                               │  physics, plugin          │
│                                               │                           │
└──────────────────────────────────────────────┴──────────────────────────┘
```

### 3.2 4 탭

#### Tab: README
- Plugin 작성자가 제공한 markdown
- Description / use cases / comparison / reference / compatibility

#### Tab: Validation (PhysicsModel 만)
```
Validation Status: ✓ PASSED

17 standard tests:
┌────────────────────────────────────┬────────┬────────┐
│ Test                               │ Result │ RMSE   │
├────────────────────────────────────┼────────┼────────┤
│ two_ray_lobing_sanity              │ ✓ PASS │ 0.42dB │
│ analytic_4ray_smith2023            │ ✓ PASS │ 0.18dB │
│ multipath_at_horizon               │ ✓ PASS │ 0.23dB │
│ ... (14 more)                      │        │        │
└────────────────────────────────────┴────────┴────────┘

[Re-run validation] [View detailed reports] [Open in Physics Lab]
```

#### Tab: Dependencies
```
Required:
- trsim-core ≥ 0.40.0    ✓ installed (v0.40.2)
- numpy ≥ 1.24            ✓ installed
- scipy ≥ 1.10            ✓ installed

Optional (enhanced features):
- pyvista ≥ 0.40         ✓ installed (better 3D viz)

Conflicts:
- trsim-multipath-old ✗  (replaced by this plugin)
```

#### Tab: Source
- File tree (read-only browse)
- LICENSE
- pyproject.toml
- src/ 의 주요 파일

### 3.3 Sidebar 정보

- Author + repo
- Published / updated date
- License
- Stats (stars / installs / issues)
- Categories + tags

### 3.4 Action 버튼 (상단 우)

상황 별:
- 미설치: **[+ Install]** primary
- 설치됨: [✓ Installed] disabled + [Uninstall] + [Settings]
- 업데이트 가능: **[Update v0.2.2 →]** primary
- PhysicsModel: + [Open in Physics Lab] / [Validate]
- 활성/비활성: ☑/☐ toggle

### 3.5 PhysicsModel 의 검증 상태 명시 (Q-PM-4=a+c)

```
[✓ Validated]  ← 녹색 박스
17/17 tests passed
Reference: Smith 2023

또는

[⚠ UNVALIDATED]  ← 노란색 박스
Tests not run yet
[→ Run validation in Physics Lab]

또는

[✗ FAILED]  ← 빨간색 박스
3/17 tests failed
[View report]   사용 시 시뮬에서 경고
```

---

## 4. 화면 간 흐름

```
[메뉴: Plugin Manager 열기]
       │
       ▼
[PM-1 Installed] (default — 현재 설치된 것 먼저 보임)
       │
       ├── Browse 탭 ─→ [PM-2 Browse]
       │                   │
       │                   └── 카드 클릭 ─→ [PM-3 Detail]
       │                                       │
       │                                       └── [+ Install]
       │                                            └── 진행 → Installed 갱신
       │
       └── 행 클릭 ─→ [PM-3 Detail] (installed 상태로)
```

---

## 5. CLI 대응

```bash
# Installed plugin 목록
trsim plugin list

# Browse / search
trsim plugin search "tracker"

# Install
trsim plugin install 4ray-multipath-physics
trsim plugin install github.com/smith-radar/4ray-multipath
trsim plugin install ./local-plugin.trsim-pkg

# Validate (PhysicsModel)
trsim plugin validate 4ray-multipath-physics

# Update
trsim plugin update --all
trsim plugin update 4ray-multipath-physics

# Uninstall
trsim plugin uninstall magnus-effect-physics
```

---

## 6. 색·시각 (Q-PM-5=c)

**카테고리 별 영역 색** — 일관 시각 정체성:

| 카테고리 | 색 | 영역 |
|---|---|---|
| Detection | **🟡 #d29922 노랑** | DSP — CFAR / Pair / Angle |
| Tracking | **🔵 #58a6ff 회청** | Simulator (Track / Pred / Classify / DataAssoc) |
| Physics ⭐ | **🟣 #a371f7 보라** | Physics Lab |
| Resource | **🟢 #39d0d8 teal** | Editor |
| UI Panel | **⚪ #768390 회색** | UI |
| HIL | **🟠 #ff9f43 주황** | HIL Workspace |
| NN (any category) | **🧠 #a371f7 보라** | 학술 (Physics 와 통일) |

배경: 일반 dark engineering tool 톤. Plugin 카드 자체는 중성 (border 색만 카테고리).

---

## 7. 데이터 출처

- `app/plugin_manager/registry.py` — 설치 plugin 목록
- `app/plugin_manager/installer.py` — 다운로드 + 의존성
- `app/plugin_manager/validator.py` — PhysicsModel 검증 (Physics Lab Validation Bench 호출)
- `~/.trsim/packages/<id>/` — 설치 위치
- `~/.trsim/cache/awesome-trsim.json` — Browse 카탈로그

---

## 8. 영향 받는 plan 영역

| 영역 | 변경 |
|---|---|
| 17 § 17.4 open_platform | UI 측 보강 |
| 04 Phase 7 DLC | UI 체크리스트 |
| 19 § 19.7 PhysicsModelProtocol | 검증 흐름 시각 |

---

## 9. 미결정 사항 (UI 측)

- **PM-U1**: awesome-trsim 카탈로그의 운영 방식 (Anthropic 공식 vs 커뮤니티)
- **PM-U2**: GitHub URL install 의 보안 (untrusted source 경고 필요?)
- **PM-U3**: PhysicsModel plugin Unvalidated 시 시뮬 진행 — 경고만 vs 진행 차단
- **PM-U4**: Plugin update 자동 체크 주기 (실행 시 / 매일 / 수동)
- **PM-U5**: NN plugin 의 학습 데이터 표시 정책 (privacy / 라이선스 표시)

---

## 10. Phase 위치

- **Phase 7 (DLC, MVP+α Wave 2)**:
  - PM-1 Installed
  - PM-2 Browse (awesome-trsim source)
  - PM-3 Detail
- **Phase 9.2 (Physics Lab 보강)**:
  - PhysicsModel plugin 검증 흐름 PM-3 통합
  - Validation 탭

---

👉 HTML artifact 동행 (3 화면 인터랙티브)
