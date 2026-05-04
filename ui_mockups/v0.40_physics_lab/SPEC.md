# UI Mockup Spec — Physics Lab (v0.40)

**최종 갱신**: 2026-05-02 (v0.40 신설 후 첫 UI mockup)
**대상 plan**: 19 physics_lab (권위 문서, 1086줄), 02 § 2.6c Physics Layer, 03 § 3.2.1o
**대상 Phase**: Phase 9.1 (MVP+α Wave 4)

---

## 0. 의도

Physics Lab 의 **3-pane 인터랙티브 환경**을 시각화. 너의 통찰 ("물리 공식을 개별/그룹/전체 적용 확인. 예: 중력 테스트 = 코드 한쪽 + 2D/3D 창에 공+지면+낙하·튕김. 파라미터 모두 조정 가능. 시간 개념 필수.") 직접 표현.

핵심 사용자 흐름:
```
[1] Workspace = Physics Lab 선택 (3번째 Workspace)
[2] Library 에서 Test 선택 또는 New Test
[3] Test Object 선택 (Ball, Cube, Plate 등) + Models 활성 (Gravity, Drag, Lift)
[4] 3-pane: Code Pane (Read-only/Edit) | Visualization (3D + 시간 진화) | Parameters (자동 슬라이더)
[5] 시간 컨트롤 (Play/Pause/Stop/Slider/Frame-by-frame) — 4 시간 모드 중 선택
[6] 파라미터 슬라이더 변경 → 즉시 시뮬 재실행 → 시각화 갱신
[7] (옵션) Validation Bench → 분석 공식 vs 구현 비교
[8] (옵션) Parameter Studio → 외부 측정 데이터로 파라미터 학습
```

이 흐름이 한 화면에서 인터랙티브하게 동작.

---

## 1. Screen PL-1 — 메인 3-pane 레이아웃 ⭐ 핵심

**가장 자주 보는 화면.** Physics Lab 의 본체.
**파일**: `ui/physics_lab/physics_lab_workspace.py`
**참조**: 19 § 19.5

### 1.1 레이아웃

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Title bar: TRsim Workbench · Physics Lab                                   │
├────────────────────────────────────────────────────────────────────────────┤
│ Workspace tabs: 📐 Editor | ▶ Simulator | 🔬 Physics Lab [active]          │
├────────────────────────────────────────────────────────────────────────────┤
│ Toolbar: [+ New Test] [💾 Save] [📁 Library] [✓ Validate] [📊 Sweep]        │
├────────────────────────────────────────────────────────────────────────────┤
│ Tab: [ Gravity Test * ] [ Two-ray Multipath ] [ + ]                        │
├──────┬─────────────────────────────────┬──────────────────────────────────┤
│      │                                 │                                   │
│ Mode │   Code Pane (Read-only)         │   Visualization Pane (3D)         │
│ Sel  │   ┌─────────────────────────┐   │                                   │
│ ☑Grav│   │ # physics/dynamics/     │   │      ╲│╱                         │
│ ☐Drag│   │ # newton.py              │   │      ─●─  ← 공 (Sphere)          │
│ ☐Lift│   │                          │   │      ╱│╲                         │
│ ☐Buoy│   │ def gravity(m, g):      │   │       │                           │
│ ☐Mag │   │     """F = m·g"""       │   │       │  ↓ velocity              │
│      │   │     return -m * g        │   │       │                           │
│ Test │   │                          │   │       ▼                           │
│ Obj  │   │ def update(s, dt):       │   │   ━━━━━━━━━━━ 지면 (Plane)        │
│ ──── │   │     a = F / m           │   │                                   │
│ ⦿Ball│   │     s.v += a * dt       │   │   trajectory                     │
│ ○Cube│   │     s.p += s.v * dt     │   │   ╱─────╲                         │
│ ○Plate│   │     if s.p.y < 0:      │   │  ╱       ╲                        │
│ ○Cyld│   │         s.v.y *= -e    │   │ ●         ●                       │
│ ...  │   │     return s             │   │                                   │
│      │   └─────────────────────────┘   │                                   │
│      │   [Read-only] [Edit Mode ⚠]     │                                   │
│      │                                  │                                   │
│ Time │                                  │                                   │
│ Mode │                                  │   Camera: [Pan] [Zoom] [Rotate]  │
│ ──── │                                  │                                   │
│ ⦿Run │                                  │                                   │
│ ○Cmpr│                                  │                                   │
│ ○Sweep│                                 │                                   │
│ ○Static│                                │                                   │
│      │                                  │                                   │
├──────┴─────────────────────────────────┬─────────────────────────────────┤
│ Time controls                          │  Side plot (선택 metric)         │
│ [▶ Play] [⏸] [⏹] [◀ Frame] [Frame ▶]   │  Height vs time                  │
│ Time slider: [▆▆▆▆▆▆░░░░░░] 2.34/10s  │  ╱─╲   ╱╲                         │
│ Speed: 0.5x | 1x | 2x                  │ ╱   ╲ ╱  ╲                        │
├────────────────────────────────────────┴─────────────────────────────────┤
│ Parameters (자동 슬라이더, decorator/type hint 기반)                       │
│ ────────────────────────────────────────────────────────────────────────  │
│ Mass [kg]:         [▆▆▆▆▆▆▆▆░░░░░░] 1.0       [0.1 ⇄ 10] linear          │
│ Radius [m]:        [▆▆░░░░░░░░░░░░] 0.1       [0.01 ⇄ 1] linear          │
│ Restitution:       [▆▆▆▆▆▆▆▆▆▆▆▆░░] 0.8       [0 ⇄ 1] linear             │
│ Initial height [m]:[▆▆▆▆▆▆▆▆░░░░░░] 5.0       [0 ⇄ 50] linear            │
│ Gravity [m/s²]:    [▆▆▆▆▆▆▆▆▆▆▆▆░░] 9.81      [0 ⇄ 20] linear            │
│ dt [s]:            [▆▆░░░░░░░░░░░░] 0.001     [0.0001 ⇄ 0.1] log         │
│                                                                            │
│ [💾 Save Experiment] [📋 Export Data] [↻ Reset]                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Pane 별 책임

#### 좌측: Model Selector + Test Object Selector + Time Mode (PL-3)

**Models** (Force toggle):
- ☑ / ☐ 체크박스로 force 활성/비활성
- 활성 force 합산 (ForceComposition)
- 5 force 표준 (Gravity, Drag, Lift, Buoyancy, Magnus)
- Plugin 으로 추가 가능 (Phase 9.2)

**Test Objects** (PL-9, 9 표준):
- ⦿ ○ 라디오로 단일 선택
- Sphere / Cube / Plate / Cylinder / Cone / Point / Plane / Wall / Trihedral
- 선택 시 Test Object metadata + 시각적 미리보기 갱신

**Time Mode** (PL-4, 4 모드):
- ⦿ Single Run (기본, 시간 진화)
- ○ Static (정지 상태, 한 시점)
- ○ Compare (두 모델 비교)
- ○ Sweep (파라미터 batch)

#### 중-좌: Code Pane (PL-7 Hybrid)

- **Read-only default** — 활성 모델의 코드 표시
- **Edit Mode toggle** — 사용자가 명시 활성화 시 편집 가능 (위험 인지)
- **Pygments syntax highlight** — Python
- **Imports/utility 자동 숨김** — 핵심 로직만 표시
- **시간 진행 시 current line highlight** — 디버거 통합 (Q-PL10)

#### 중-우: Visualization Pane

- **3D PyVista** (모델 따라 2D pyqtgraph 도)
- **Test Object 시각화** — Sphere = 구체, Cube = 정육면체, etc.
- **Force vectors** — 화살표 (Gravity 아래 / Drag 반대 방향 / etc.)
- **Trajectory line** — 시간 진화 경로
- **Side plot** — 사용자 선택 metric (Height/Velocity/Energy vs Time)
- **Camera controls** — Pan/Zoom/Rotate (3D)

#### 하-우: Side Plot

Visualization 옆 또는 아래 작은 plot:
- Height vs Time (default)
- Velocity vs Time
- Energy vs Time (kinetic + potential + total)
- Custom metric

#### 하: Time Controls

- Play / Pause / Stop
- Frame-by-frame (◀ ▶)
- Time slider
- Speed (0.5x / 1x / 2x)
- Keyboard shortcuts (Space=play, ←→=frame)

#### 하-단: Parameters Pane

- 모든 파라미터 자동 슬라이더 (decorator/type hint 기반)
- Linear / Log scale (모델 metadata)
- Min/Max 사용자 변경 (입력 박스)
- Live update (변경 → 시뮬 재실행 → 시각화 갱신)
- Unit 표시 (kg, m, s, dB, deg 등)

### 1.3 인터랙션

- **Models toggle** → 활성 force 합산 갱신 + 코드 pane 갱신 + 시뮬 재실행
- **Test Object 선택** → 3D 시각화 갱신 + 적용 가능한 force 자동 갱신
- **Time Mode 전환** → UI 다른 화면 (Compare → split, Sweep → heatmap)
- **Code edit** (toggle 활성 시) → 라이브 갱신
- **파라미터 슬라이더** → live update
- **Play/Pause** → 시뮬 진행 + Visualization 애니메이션
- **Frame slider** → 임의 시점 점프

### 1.4 색·시각

Physics Lab accent: **보라/녹색** (Editor teal / Simulator gray / HIL orange / RT blue 와 구분).
- 후보 1: 보라 (#a371f7) — 학술·실험 느낌
- 후보 2: 녹색 (#3fb950) — 자연·물리 느낌
- 후보 3: 밝은 노랑 (#d29922) — 에너지 느낌

내 추천: **보라 (#a371f7)** — 학술 느낌, 다른 영역과 구분.

### 1.5 데이터 출처

- `app/physics_lab/experiment_runner.py` — 시뮬 진행
- `app/physics_lab/param_introspector.py` — 파라미터 자동 노출
- `physics/test_objects.py` — 9 표준 객체
- `physics/dynamics/` 등 — 물리 모델

---

## 2. Screen PL-2 — Library

**Test 모음 + 자료 라이브러리.** Models / Test Objects / External Data / Reference Papers / Saved Experiments.
**파일**: `ui/physics_lab/library_panel.py`
**참조**: 19 § 19.9 (Reference Library)

### 2.1 레이아웃

```
┌────────────────────────────────────────────────────────────────────┐
│ Library                                                       [×]  │
├────────────────────────────────────────────────────────────────────┤
│ Tabs: [Models] [Test Objects] [External Data] [Papers] [Saved]     │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ [Models tab active]                                                 │
│ Search: [_________________]    Filter: [All Categories ▾]           │
│                                                                     │
│ ▼ Built-in (12)                                                    │
│ ┌──────────────┬──────────────┬──────────────┐                     │
│ │ 🌍           │ 💨           │ ✈           │                     │
│ │ Gravity      │ Air Drag     │ Aerodynamic  │                     │
│ │              │              │ Lift         │                     │
│ │ dynamics     │ dynamics     │ dynamics     │                     │
│ │ F = -m·g    │ F = ½ρv²Cd·A │ F = ½ρv²CL·A │                     │
│ │ analytic ✓   │ analytic ✓   │ analytic ✓   │                     │
│ └──────────────┴──────────────┴──────────────┘                     │
│ ┌──────────────┬──────────────┬──────────────┐                     │
│ │ 📡           │ 🌫           │ ⚡           │                     │
│ │ Free Space   │ Atm Loss     │ Multipath    │                     │
│ │ Loss (Friis) │ (rain/fog)   │ (Two-ray)    │                     │
│ │ propagation  │ atmosphere   │ propagation  │                     │
│ │ analytic ✓   │ ITU-R ✓      │ analytic ✓   │                     │
│ └──────────────┴──────────────┴──────────────┘                     │
│                                                                     │
│ ▼ User Plugins (2) — Phase 9.2 검증 통과                            │
│ ┌──────────────┬──────────────┐                                    │
│ │ 🆕 Magnus    │ 🆕 4-ray     │                                    │
│ │ Effect       │ Multipath    │                                    │
│ │ dynamics     │ propagation  │                                    │
│ │ ✓ Validated  │ ✓ Validated  │                                    │
│ └──────────────┴──────────────┘                                    │
│                                                                     │
│ [+ Install Plugin]  [→ Open Plugin Manager]                         │
└────────────────────────────────────────────────────────────────────┘
```

### 2.2 5 탭

#### Models tab
- Built-in 12개 (Gravity, Drag, Lift, Buoyancy, Magnus, Free Space Loss, Atm Loss, Multipath, RCS, Doppler, Antenna Pattern, Refraction)
- User plugins (Phase 9.2 검증 통과)
- Install / Plugin Manager 링크

#### Test Objects tab
- 9 표준 객체 카드
- 각 카드: 시각 미리보기 + 메타 (mass / size / RCS analytic 등)
- "+ Custom Test Object" — Phase 9.2 (사용자 정의)

#### External Data tab
- 업로드된 측정 데이터 목록 (CSV / HDF5 / .npz)
- 메타: 출처 / 측정 조건 / 라이선스
- "+ Upload Data"
- 검증·학습에서 참조

#### Reference Papers tab (PL-10, 참조 자료만)
- 업로드된 논문 PDF 목록
- 메타: 저자 / 인용 / 모델 설명 (수동 입력)
- 각 물리 모델의 "출처 논문" metadata 연결
- **자동 코드 생성 X** (명시적 제외)

#### Saved Experiments tab
- 사용자가 저장한 PhysicsExperiment 목록
- 메타: 이름 / 사용 모델 / 사용 Test Object / 결과 요약

### 2.3 데이터 출처

- `app/physics_lab/library_manager.py` (Phase 9.1)
- `physics/_testbench/golden_dataset/`

---

## 3. Screen PL-3 — Validation Bench

**분석 공식 vs 구현 비교 + 17~20+ 종 회귀 + 외부 데이터 overlay.**
**파일**: `ui/physics_lab/validation_panel.py`
**참조**: 19 § 19.10, 16 § 16.9

### 3.1 레이아웃

```
┌────────────────────────────────────────────────────────────────────┐
│ Validation Bench                                              [×]  │
├────────────────────────────────────────────────────────────────────┤
│ [Run All] [Run Selected]   Status: 18 PASS · 2 FAIL · 1 SKIP       │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ Test                              Status   Analytic   Impl   Diff  │
│ ───────────────────────────────────────────────────────────────── │
│ ✓ two_ray_multipath_lobing       PASS    ─          ─      0.42  │
│ ✓ multi_scatterer_glint           PASS    ─          ─      ✓     │
│ ✓ ekf_vs_ukf_tracking             PASS    ─          ─      ✓     │
│ ✓ gnn_data_association            PASS    ─          ─      ✓     │
│ ✓ refraction_4_3_earth            PASS    ─          ─      0.18  │
│ ✓ os_cfar_vs_ca_cfar              PASS    ─          ─      ✓     │
│ ✓ antenna_sinc2_pattern           PASS    -13.2 dB   ─      0.05  │
│ ✓ free_space_loss_friis           PASS    ─          ─      ✓     │
│ ✓ doppler_shift_accuracy          PASS    ─          ─      ✓     │
│ ✓ range_bin_resolution            PASS    ─          ─      ✓     │
│ ✓ stage_timing_accuracy (RT)      PASS    ─          ─      ✓     │
│ ✓ frame_profiler_percentile (RT)  PASS    ─          ─      ✓     │
│ ✓ gt_vs_sil_accuracy (HIL)        PASS    ─          ─      ✓     │
│ ✓ sil_vs_hil_bias (HIL)           PASS    ─          ─      ✓     │
│ ✓ l4_paired_matching (HIL)        PASS    ─          ─      ✓     │
│ ✓ sphere_freefall (analytic vs RK4) ⭐ PASS  9.81 m/s² ─      0.001 │
│ ✓ trihedral_rcs_boresight ⭐      PASS    4πa⁴/(3λ²) ─      0.08  │
│ ✓ force_composition_grav_drag ⭐  PASS    ─          ─      ✓     │
│ ⚠ test_object_dynamics_bouncing ⭐ FAIL  energy_decay 0.83  threshold > 0.95 │
│ ⏸ extended_target_rcs_montecarlo  SKIP    ─          ─      Q-PL3  │
│ ───────────────────────────────────────────────────────────────── │
│ Total: 20 scenarios   Time: 4.2s                                   │
│                                                                     │
│ Selected: test_object_dynamics_bouncing                            │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ Plot: Analytic vs Implementation                              │  │
│ │  Energy [J]                                                    │  │
│ │   100 ┤━━━━━━━━━━━━━━━━ analytic (no decay)                   │  │
│ │    80 ┤              ╲                                         │  │
│ │    60 ┤                ╲╲                                      │  │
│ │    40 ┤                  ╲╲╲ implementation (decay too fast) │  │
│ │    20 ┤                       ╲╲                              │  │
│ │       └──────────────────────────                             │  │
│ │        0    2    4    6    8   t [s]                          │  │
│ │                                                                │  │
│ │ ⚠ Energy decay 0.83 (expected > 0.95)                          │  │
│ │ Hint: restitution 값 검토 또는 dt 너무 큼?                       │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│ [💾 Export Report] [🔍 Drill into Test] [↻ Update Golden]          │
└────────────────────────────────────────────────────────────────────┘
```

### 3.2 위젯 목록

| 위젯 | 타입 | 역할 |
|---|---|---|
| Run All / Run Selected | QPushButton × 2 | 회귀 실행 |
| Status summary | QLabel | PASS/FAIL/SKIP count |
| Test 표 | QTableView | 시나리오 목록 + 상태 |
| Drill plot | pyqtgraph PlotWidget | 선택 시나리오의 analytic vs implementation |
| Hint panel | QTextEdit | FAIL 시 진단·제안 |
| Export Report | QPushButton | JSON / Markdown |
| Update Golden | QPushButton | 의도된 수정 시 |

### 3.3 인터랙션

- **Test 행 클릭** → drill plot 갱신 + hint 표시
- **Run All** → 모든 시나리오 실행 (수 초)
- **Run Selected** → 선택 시나리오만
- **FAIL 시 hint** — 자동 진단 (dt 조정 / 파라미터 검토 등)
- **Update Golden** — 의도된 수정 시 새 결과를 golden 으로 채택 (확인 dialog)

### 3.4 데이터 출처

- `app/physics_lab/validation_bench.py` 의 `ValidationReport`
- `physics/_testbench/golden_dataset/`
- 03 § 3.2.1o `ValidationResult` dataclass

---

## 4. Screen PL-4 — Parameter Studio

**파라미터 sweep + 학습 (형태 1) + 학습 영역 시각화.**
**파일**: `ui/physics_lab/parameter_studio.py`
**참조**: 19 § 19.9.3, Phase 9.1 (형태 1) + 9.2 (Symbolic regression) + 9.3 (NN 대체)

### 4.1 레이아웃

```
┌────────────────────────────────────────────────────────────────────┐
│ Parameter Studio                                              [×]  │
├────────────────────────────────────────────────────────────────────┤
│ Mode: ⦿ Sweep  ○ Fit (form 1)  ○ Symbolic Reg (9.2)  ○ NN (9.3)    │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ [Sweep mode active]                                                 │
│ Model: [ Drag (quadratic) ]   Test Object: [ Sphere ]               │
│                                                                     │
│ Sweep Variable 1:                                                   │
│   [ Mass ▾ ]  Range: [ 0.5 ⇄ 5.0 ]  Steps: [ 20 ] [linear ▾]        │
│                                                                     │
│ Sweep Variable 2 (optional):                                        │
│   [ Cd ▾ ]    Range: [ 0.1 ⇄ 2.0 ]  Steps: [ 15 ] [linear ▾]        │
│                                                                     │
│ Output Metric:                                                      │
│   [ Terminal velocity ▾ ]  [m/s]                                    │
│                                                                     │
│ [▶ Run Sweep]   Progress: [▆▆▆▆▆▆▆▆▆▆░░░░░░░] 65%                  │
│                                                                     │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │  Heatmap (Mass × Cd → Terminal velocity)                      │  │
│ │                                                                │  │
│ │  Cd  ┤                                                         │  │
│ │  2.0 ┤▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ low velocity                            │  │
│ │  1.5 ┤▓▓▓▓▒▒▒▒▒▒▒▒▒▒▓▓                                         │  │
│ │  1.0 ┤▓▒▒░░░░░░░░░░▒▒▓                                         │  │
│ │  0.5 ┤▒░░░       ░░░▒▒                                         │  │
│ │  0.1 ┤░░░         ░░░░ high velocity                           │  │
│ │      └──────────────────                                       │  │
│ │       0.5  1.5  2.5  3.5  4.5  Mass [kg]                       │  │
│ │                                                                │  │
│ │  Color: [▓▓▓▒▒▒░░░] 0 ─ 50 m/s                                 │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│ Cursor: Mass=2.5 kg, Cd=0.8 → V_terminal = 23.4 m/s                 │
│                                                                     │
│ [💾 Save Sweep] [📋 Export CSV] [📊 To Plot]                         │
└────────────────────────────────────────────────────────────────────┘
```

### 4.2 4 모드

#### Mode 1: Sweep (Phase 9.1)
- 파라미터 1~2 sweep
- 출력 1D line / 2D heatmap
- CSV / NumPy export

#### Mode 2: Fit (형태 1, Phase 9.1)
- 외부 측정 데이터 업로드 (CSV/HDF5)
- 기존 모델 파라미터 fit (scipy.optimize.curve_fit)
- 시각화: 측정 vs fit 결과 overlay
- fit_quality (R² / RMSE) 표시
- 사용자 검토 → 채택

#### Mode 3: Symbolic Regression (형태 4, Phase 9.2)
- 외부 측정 데이터 → PySR 으로 수식 발견
- 발견 수식 sympy 표현 + Python 코드 생성
- 사용자 검토 후 새 모델로 채택

#### Mode 4: NN Replacement (형태 2, Phase 9.3)
- 외부 측정 데이터 → NN 학습 (Phase 6 NN 결합)
- **학습 영역 vs 외삽 영역** 색·투명도로 표시 (Q-PL8)
- 외삽 시 위험 경고
- NN 모델 → .trsim-pkg packaging

### 4.3 학습 영역 시각화 (Mode 4 핵심, Q-PL8)

```
3D plot (parameter × parameter × output):

  parameter B
       │
       │   ┌─── 학습 영역 (불투명) ───┐
       │   │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     │
       │   │  ▓▓▓ NN reliable ▓▓▓   │
       │   │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     │
       │   └────────────────────────┘
       │
       │      ░░░ 외삽 영역 (반투명, ⚠) ░░░
       │      "NN extrapolation — verify carefully"
       │
       └──────────────────────────────────
              parameter A

색:
  학습 영역 = 녹색 (NN 신뢰)
  외삽 영역 = 빨강·반투명 (⚠ 위험)
```

### 4.4 데이터 출처

- `app/physics_lab/experiment_runner.py` — sweep 진행
- `app/physics_lab/parameter_fitter.py` — 형태 1
- `app/physics_lab/symbolic_regression.py` — 형태 4 (Phase 9.2)
- `app/physics_lab/nn_replacement.py` — 형태 2 (Phase 9.3)

---

## 5. 화면 간 흐름

```
[Workspace = Physics Lab]
       │
       ▼
[PL-1 메인 3-pane] (default)
       │
       │ Library 버튼
       ▼
[PL-2 Library]
   - Models / Test Objects / External Data / Papers / Saved
       │
       │ 선택 → PL-1 로 적용
       ▼
[PL-1 갱신]
       │
       │ Validate 버튼 또는 Toolbar
       ▼
[PL-3 Validation Bench]
   - 17~20+ 종 회귀
   - FAIL 시 drill
       │
       │ Sweep / Fit 버튼 또는 Toolbar
       ▼
[PL-4 Parameter Studio]
   - Sweep / Fit / Symbolic / NN
   - 결과 → Resource Library 저장
```

---

## 6. CLI 대응

```bash
# 단일 test 실행
trsim physics-lab run gravity_test.toml

# 회귀 모두
trsim physics-lab validate --all

# 특정 시나리오
trsim physics-lab validate --scenario sphere_freefall

# Sweep
trsim physics-lab sweep --model drag --vars mass,cd --metric terminal_velocity

# Fit (형태 1)
trsim physics-lab fit --data measured_rcs.csv --model extended_target

# Update golden (의도된 수정)
trsim physics-lab validate --update-golden two_ray_multipath
```

---

## 7. 영향 받는 plan 영역

| 영역 | 변경 |
|---|---|
| 19 physics_lab | 본 mockup 으로 시각화 보강 |
| 02 § 2.6c Physics Layer | UI 측에서 physics 함수 호출 |
| 03 § 3.2.1o | dataclass → UI 데이터 모델 |
| 04 Phase 9 | UI 구현 체크리스트 |
| 17 § 17.4.1 PhysicsModelProtocol | Library 의 plugin 검증 |

---

## 8. 미결정 사항 (UI 측)

- **PL-U1**: Physics Lab accent 색 — 보라 (#a371f7) 추천. 변경 의향?
- **PL-U2**: Code Pane 의 "Edit Mode" toggle 위치 (toolbar / pane header / 메뉴)
- **PL-U3**: 시간 슬라이더의 정밀도 (frame 단위 / continuous)
- **PL-U4**: 파라미터 슬라이더 max 개수 (UI 분량 — 화면 채워질 때)
- **PL-U5**: Library 의 Built-in vs User Plugin 분리 시각 (헤더 / 색)
- **PL-U6**: Validation Bench 의 fail hint 자동 진단 정도 (단순 메시지 / 상세 분석)
- **PL-U7**: Parameter Studio 의 Sweep 결과 plot 형식 (heatmap default? 3D scatter 가능?)
- **PL-U8**: NN 학습 영역 표시 — 색·투명도 외 다른 시각 (boundary line?)

---

## 9. Phase 위치

- **Phase 9.1 (MVP+α)**: PL-1 메인 + PL-2 Library + PL-3 Validation Bench + PL-4 Sweep + Fit (형태 1)
- **Phase 9.2**: PL-2 의 plugin 검증 + PL-4 Symbolic Regression
- **Phase 9.3**: PL-4 NN Replacement + 학습 영역 시각화

---

## 10. 다음 (UI mockup 작업)

남은 영역 (Physics Lab 후):
- Simulator Workspace 메인 (Editor 의 짝)
- Plugin Manager UI (v0.35 DLC install + v0.40 Physics plugin)
- 4-error 진단 화면 (NN 모드 step 2)
- 옛 영역 (Screen 1~8)

---

👉 HTML artifact 동행 (인터랙티브 mockup)
