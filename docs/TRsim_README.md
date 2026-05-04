# TRsim — Tracking Radar Simulator

**프로젝트 기획·설계 문서 아카이브**
작성: 2026-04-23 (최초) / 2026-05-02 (v0.40 갱신)
버전: **v0.40**

---

## 이 아카이브는 무엇인가

추적 레이더 알고리즘·자원·시각화를 DLC 패키지로 자유롭게 확장하는 **오픈소스 워크벤치
플랫폼 TRsim (Tracking Radar Simulator)** 의 기획·설계 문서, 아키텍처, 오픈소스 인프라
초안, 정합성 검토 결과 등을 묶은 패키지입니다.

한 줄 정의:

> **TRsim은 추적 레이더 알고리즘·자원·시각화·물리 모델을 자유롭게 다루는 오픈소스
> 워크벤치 플랫폼이다. Apache 2.0 코어 + .trsim-pkg DLC + HIL 통합 + Reference Timing +
> Physics Lab — 5번째 차별점. 추적 IDE + 인터랙티브 물리 시각화 = 시장에 부재한 조합.**

상태: 설계 단계 종료 · 결정 72개 · 블로커 0 · MVP Phase 0 진입 가능

---

## 구성

```
TRsim_v0.37/
│
├── README.md                       ← 패키지 진입점 (v0.37 변경 요약)
├── COWORK_HANDOFF.md                ← cowork 첫 진입 가이드 ⭐
├── TRsim_README.md                  ← 이 파일
│
├── AGENT_GUIDE.md                   ← Claude·기여자 작업 가이드
├── ROADMAP.md                       ← 작업 로드맵 + 6단계 큰 흐름
├── OPEN_QUESTIONS.md                ← 미결정 사항 (43 closed, Open 다수)
├── SESSION_SUMMARY.md               ← 누적 세션 요약
├── REVIEW_REPORT_v0.35.md           ← 정합성 검토 종합 보고서
│
├── plan/                            ← 기획·설계 문서 (18 plan + 부록 2)
│   ├── 00_README.md                 ← 계획서 진입점, 읽는 순서, 변경 이력
│   ├── 01_vision_scope.md           ← 정체성·MVP·사용자 Journey
│   ├── 02_architecture.md           ← 아키텍처 블록도·디렉토리·의존 규칙
│   ├── 03_data_model.md             ← 데이터 모델·Contract (가장 큼, 2,193줄)
│   ├── 04_migration.md              ← Phase 0~7 신규 구현 순서
│   ├── 05_ui_ux.md                  ← 🟡 참조 보존 (권위는 13)
│   ├── 06_topics.md                 ← 🟡 참조 보존 (권위는 17, 02 § 2.6b)
│   ├── 07_nn_integration.md         ← NN 모드·Stage Slot·4-error 진단
│   ├── 08_radar_waveforms.md        ← FMCW Triangle + 안테나 + multipath/CFAR
│   ├── 09_radar_platforms.md        ← Maritime / Fixed Ground 플랫폼
│   ├── 10_workspaces.md             ← 두 Workspace + 자원 라이브러리
│   ├── 11_coordinate_systems.md     ← WGS84·ENU·SimulationDomain
│   ├── 12_placement_and_motion.md   ← MotionKind 7 · anchor · waypoint
│   ├── 13_editor_workspace.md       ← Editor 5 Activity 상세
│   ├── 14_dynamics_model.md         ← 사실적 동역학 + ExtendedTarget
│   ├── 15_atmosphere_model.md       ← ISA + rain · refraction
│   ├── 16_baseline_audit.md         ← v0.34 베이스라인 점검 결과
│   ├── 17_open_platform.md          ← v0.35 오픈소스 + DLC 시스템
│   ├── 18_hil_integration.md        ← 🆕 v0.38 HIL 통합 + v0.39 Reference Timing + Frame Profiler
│   ├── 19_physics_lab.md             ← 🆕 v0.40 Physics Lab (3-pane 인터랙티브 + 9 Test Objects)
│   ├── appendix_A_code_audit.md     ← 🚫 DEPRECATED (sim_3d 평가 무효)
│   └── appendix_B_glossary.md       ← 용어집 (870줄)
│
├── repo_root_drafts/                ← MVP Phase 0 시 레포 루트로 복사
│   ├── LICENSE                      ← Apache 2.0
│   ├── NOTICE                       ← 서드파티 라이선스 목록
│   ├── README.md                    ← 프로젝트 README
│   ├── CONTRIBUTING.md              ← 기여 가이드 + DCO
│   ├── CODE_OF_CONDUCT.md           ← Contributor Covenant 2.1
│   ├── GOVERNANCE.md                ← BDFL → Core Team 진화
│   ├── SECURITY.md                  ← 취약점 신고
│   ├── pyproject.toml               ← 빌드·의존성·tool 설정 (ruff/mypy/pytest)
│   ├── .importlinter                ← 의존 규칙 강제 (6개 contract)
│   └── .github/
│       ├── PULL_REQUEST_TEMPLATE.md ← PR 템플릿 + DCO 체크
│       ├── ISSUE_TEMPLATE/
│       │   ├── bug_report.md
│       │   ├── feature_request.md
│       │   └── question.md
│       └── workflows/
│           └── ci.yml               ← lint + test + dco-check + lint-imports
│
└── competitive_analysis/            ← 경쟁 환경 분석
    ├── TRsim_competitive_v0.1.md    ← 경쟁 제품 비교 (Stone Soup·MATLAB 등)
    └── baseline_audit_v0.1.md       ← v0.34 베이스라인 점검 근거
```

---

## 어디서부터 읽나

### cowork·새 Claude 진입 시 (5~15분)

1. **`COWORK_HANDOFF.md`** — cowork 첫 진입 종합 가이드 (12 섹션)
2. **`AGENT_GUIDE.md`** — Claude 작업 규약·정체성
3. **`REVIEW_REPORT_v0.35.md`** — 정합성 검토 결과 (어떤 게 권위, 어떤 게 참조 보존)
4. **`ROADMAP.md`** § 큰 흐름 — 6단계 (Phase 0 → 7)

### 정식으로 읽기 (점진적)

1. **`plan/00_README.md`** — 18개 plan 진입점 + 읽는 순서
2. **`plan/01_vision_scope.md`** — 정체성·MVP·Journey
3. **`plan/02_architecture.md`** — 아키텍처 블록도
4. **`plan/17_open_platform.md`** — v0.35 오픈소스 + DLC (정체성 핵심)
5. **`plan/18_hil_integration.md`** — v0.38 HIL 통합 (4번째 차별점) + v0.39 Reference Timing
6. **`plan/19_physics_lab.md`** — v0.40 Physics Lab (5번째 차별점) ⭐
6. 나머지는 `00_README.md` 의 우선순위대로

### 특정 주제

| 주제 | 보는 곳 |
|---|---|
| 데이터 모델 (Plugin Manifest, HIL DUT Messages 포함) | `plan/03_data_model.md` |
| Phase 0 시작 | `plan/04_migration.md` § 4.3 |
| 동역학 (사실적 표적 운동) | `plan/14_dynamics_model.md` |
| 베이스라인 점검 (v0.34) | `plan/16_baseline_audit.md` |
| DLC 시스템 (v0.35) | `plan/17_open_platform.md` |
| **HIL 통합 (v0.38)** | **`plan/18_hil_integration.md`** |
| **Reference Timing + Frame Profiler (v0.39)** | **`plan/18_hil_integration.md`** § 18.16~18.17 |
| **Physics Lab (v0.40)** | **`plan/19_physics_lab.md`** ⭐ |
| 용어 모름 | `plan/appendix_B_glossary.md` |
| 미결정 사항 | `OPEN_QUESTIONS.md` |

---

## 현재 상태 (v0.40, 2026-05-02)

### ✅ 완료

- 설계 문서 안정화 (v0.16~v0.38, 18 plan + 부록 2 = 12,500+ 줄)
- v0.34 베이스라인 보강 5종 + OS-CFAR (multipath / multi-scatterer / glint / EKF·UKF / GNN / refraction)
- v0.35 오픈소스 + DLC 정체성 전환 (Apache 2.0, .trsim-pkg, SDK Layer, 9 Plugin Protocol)
- 정합성 검토 5세션 완료 (약 52~55개 정정, 정합 노트 19개, 21 신규 용어)
- 루트 인프라 13종 (LICENSE/CI/Issue 템플릿/pyproject.toml/.importlinter)
- sim_3d 분리 (정상 동작 미검증, 회귀 비교 대상 아님)
- **v0.38 HIL 통합 신설** — DUTAdapter Protocol (10번째), GT/SIL/HIL 3-way, plan/18 신규 (635줄)
- **v0.39 Reference Timing + Frame Profiler** — 18 § 18.16/18.17 신설, PerformanceClock (02 § 2.2c), domain/timing + app/timing + profiler_panel 디렉토리, Q-RT1~8
- **v0.40 Physics Lab** ⭐ — 3-pane 인터랙티브 (Code | Visualization | Parameters), 9 Test Objects (Sphere/Cube/Plate/Cylinder/Cone/Point/Plane/Wall/Trihedral), 4 시간 모드 (Static/Run/Compare/Sweep), 사용자 물리 plugin (PhysicsModelProtocol 11번째), 06 § 6.7 영구 제외 결정 변경, 17종 → Physics Lab 통합, plan 19 신설 (1086줄), 차별점 4+1 → 5+1, MVP+α Wave 4 신설, Q-PL1~10

### ⏳ 다음

- **Phase 0 인프라 셋업** ⭐ — repo + Apache 2.0 + CI + 빈 QMainWindow
- **T1 UI 목업 마무리** (Phase 0과 병렬 가능)
- Phase 1~5 신규 구현 + 베이스라인 검증 + 외부 공개
- MVP+α: Phase 6 NN, Phase 7 DLC, **Phase 8 HIL**

자세한 흐름: `ROADMAP.md` § 큰 흐름 (6단계 + Phase 8).

미결정 항목: `OPEN_QUESTIONS.md` (Q-A2 / Q-D1~5 / Q-N7 / Q-OP1~5 / Q-HIL1~7 / Q-RT1~8 / Q-PL1~10 등)

---

## 큰 흐름 한 눈에

```
0. Phase 0 인프라 셋업      ← 즉시 가능
1. UI 목업 확인 (0과 병렬)
2. MVP 제작 (Phase 1~5)
2.5 베이스라인 검증 (물리)
3. 재점검 (정합성)
4. 주요 기능 확인 (Editor + Simulator UX)
5. 외부 공개 + 커뮤니티
6. MVP+α (Phase 6 NN, Phase 7 DLC, Phase 8 HIL)
```

---

## 구현 방침

> **v0.16~v0.35 계획서 기반 신규 작성**.
> 옛 프로토타입 (`sim_3d`) 은 정상 동작 미검증으로 회귀 비교나 직접 이식 대상 아님.
> 검증은 분석 공식 (수계산) + Stone Soup·MATLAB 비교.
