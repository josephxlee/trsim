# ROADMAP — TRsim (v0.40 기준)

**마지막 갱신**: 2026-04-28

## 현재 위치

```
v0.13 ─→ ... ─→ v0.37 ─→ v0.38 (HIL) ─→ v0.39 (Reference Timing) ─→ v0.40 (Physics Lab) [지금 여기]
                                                                                          │
                                                                                          │  🎯 설계 + 정합 + 인프라 모두 완료
                                                                                          │     (블로커 0, 결정 72개, 차별점 5+1)
                                                                                          │
                                                                                          ├─→ T3 Phase 0 구현 착수 ⭐ (repo + 빈 QMainWindow)
                                                                                          ├─→ T1 UI 목업 마무리 (Phase 0과 병렬)
                                                                                          ├─→ T6 DECISIONS.md ADR (점진적)
                                                                                          └─→ MVP+α: Phase 6 NN, Phase 7 DLC, Phase 8 HIL, Phase 9 Physics Lab ⭐
```

설계·정합·베이스라인·플랫폼 정체성·Phase 0 인프라 모두 단단함. **MATLAB·Stone Soup 비교 demo 신뢰 기반 + 오픈소스 + DLC 에코 + 신규 구현 원칙**. v0.37에서 sim_3d 분리 (정상 동작 미검증, 회귀 비교 대상 아님).

---

## 완료된 작업 (누적)

- ✅ v0.16: 통합 리뷰 (T0/T2/T7)
- ✅ v0.17: 휠 줌 + Unreal+Maya 3D 조작
- ✅ v0.18: Radar Platforms + Installation
- ✅ v0.19: 두 Workspace
- ✅ v0.20: 자원 참조 + Bundle
- ✅ v0.21: 좌표계 정합 + 정적/동적 분리
- ✅ v0.22: 자체 규격 지형 + 편집 도구
- ✅ v0.23: 03 data_model 정합
- ✅ v0.24: 09 ↔ MotionKind 정합
- ✅ v0.25: Antenna Model + Radar Editor
- ✅ v0.26: Editor Workspace 전체 레이아웃
- ✅ **v0.27: 사실적 표적 동역학** (`14_dynamics_model.md`)
- ✅ **v0.28: 시각화 스택 + 대기 모델** (`15_atmosphere_model.md`, Q-P2/Q-A1 closed)
- ✅ **v0.29: Simulation Domain** (11 § 11.11, Q-MS1/2/3 closed)
- ✅ **v0.30: T11 NN 모드 보강** (v0.25~v0.29 정합, 확장 Variant 6종)
- ✅ **v0.31: T10 04 migration Phase 갱신** (v0.18~v0.30 모듈 + Phase 6 NN)
- ✅ **v0.32: T9 02 architecture 갱신** (블록도·디렉토리·의존 규칙 + § 2.9 모듈 도입 이력)
- ✅ **v0.33: Map Editor Flatten Area** (정박지·활주로·부지 평탄화)
- ✅ **v0.34: 베이스라인 보강 + 16 baseline_audit 신규** (Q-BL1~5 closed, 5종 MVP 추가)
- ✅ **v0.35: 오픈소스 + DLC 플랫폼 정체성 전환** (Q1-rev/Q2~Q9 closed, 17 open_platform 신규, Apache 2.0)
- ✅ **v0.36: 정합성 검토 5세션** (2026-04-28) — 약 52~55개 정정 + § 3.2.1l Plugin Manifest 신설(108줄) + 용어집 21개 신규 용어 보강. 17/20 문서 v0.35 헤더, 정합 노트 19개로 옛 표현 함정 차단. **MVP Phase 0 진입 가능**. 상세: `/REVIEW_REPORT_v0.35.md`
- ✅ **v0.37: Phase 0 인프라 보강 + sim_3d 분리** (2026-04-28) — `pyproject.toml`(257줄)·`.importlinter`(106줄) 신설, 02 § 2.3 디렉토리 갱신, 04 migration 큰 재작성 (이식 → 신규 구현), appendix_A DEPRECATED, 정체성·검증 기준에서 sim_3d 제거. **6단계 큰 흐름 정립**.
- ✅ **v0.38: HIL 통합 추가 (4번째 차별점)** (2026-04-29) — `plan/18_hil_integration.md`(635줄) 신설, DUTAdapter Protocol (10번째 SDK), L1~L5 RX 표준 + 양방향 TX, GT/SIL/HIL 3-way 검증 모델, Phase 8 신설 (8.1/8.2/8.3), `domain/hil/`·`app/hil/`·`ui/simulator/hil_panel/` 디렉토리, `tcp_json_dut_adapter.py` 기본 sample, Q-HIL1~7 등록. **차별점 3+1 → 4+1**.
- ✅ **v0.39: Reference Timing Mode + Frame Profiler 추가** (2026-04-29) — 18 § 18.16 (Reference Timing Mode) + § 18.17 (Frame Profiler) 신설, PerformanceClock (02 § 2.2c, SimulationClock 의 보정 layer), 03 § 3.2.1n dataclass (StageTimingProfile / FrameTimingReport / StageTimingStat 등), `domain/timing/` + `app/timing/` + `ui/simulator/profiler_panel/` 디렉토리, DUTAdapter 의 sync 메서드 (Lock-step Handshake), Phase 2/3/4/5 분산 + Phase 8.1 보강, Q-RT1~8 등록. **차별점 4+1 유지** (Reference Timing 은 당연한 기능).
- ✅ **v0.40: Physics Lab 추가 (5번째 차별점) ⭐** (2026-05-02) — `plan/19_physics_lab.md`(1086줄) 신설. **3-pane 인터랙티브** (Code | Visualization | Parameters), **9 표준 Test Objects** (Sphere/Cube/Plate/Cylinder/Cone/Point/Plane/Wall/Trihedral), **4 시간 모드** (Static/Single Run/Compare/Sweep), **PhysicsModelProtocol** (11번째 SDK Plugin Protocol). **Physics Layer 분리** — `domain/dynamics`·`domain/atmosphere`·`domain/radar` 의 물리 → `physics/` 통합. `app/physics_lab/` + `ui/physics_lab/` Workspace 신설 (3번째 Workspace). **06 § 6.7 사용자 물리 plugin 영구 제외 결정 변경** (Validation Bench 가 안전망). **17종 검증 시나리오 → Physics Lab 통합** (16 § 16.9). **외부 자료 학습 점진**: 형태 1 (파라미터 학습) + 형태 5 (검증) MVP, 형태 2 (NN 대체) Phase 9.3 Phase 6 결합, 형태 4 (Symbolic regression) Phase 9.2, **형태 3 (논문 PDF → 자동 코드 생성) 명시 제외** — 논문은 참조 자료만. **Phase 9 신설** (MVP+α Wave 4) — 9.1 (MVP), 9.2 (학습 보강), 9.3 (NN 대체). **차별점 4+1 → 5+1**. Q-PL1~10 등록.

---

## 작업 항목 (남은 것, 우선순위순)

> **참고**: T9 (02 architecture), T10 (04 migration), T11 (07 NN), Q-P2 (VTK)는
> 모두 v0.28~v0.32에서 완료됨. 위 § 완료된 작업 표 참조.

### 🎨 T1. UI 목업 v0.3 마무리 (보류 중)

**왜**: 모든 새 모델 시각화 (Editor Workspace, Antenna, **동역학 거동**, **glint·DLC 패널**).

**선행**: 없음 (Q-P2 closed v0.28)

**내용**:
- Screen 1 마무리, Screen 4~7, Screen 8 본문
- 신규: Editor Workspace 레이아웃 (Resource Browser + Radar Editor + Map Editor)
- 신규: 동역학 가시화 (max_climb_rate 도달, BALLISTIC 포물선 등)
- 신규 (v0.34): Multi-scatterer + glint 시각화
- 신규 (v0.35): Plugin Manager UI (DLC install·uninstall)

**예상 소요**: 2~3 세션 (분량 큼)

---

### 💻 T3. Phase 0 구현 착수

**왜**: 설계가 충분히 안정. 코드 시작 시점.

**선행**: 없음 (T9/T10/T11 완료, 베이스라인·플랫폼 정체성 확정)

**내용**:
- 레포 뼈대 (`pyproject.toml`, 디렉토리 구조)
- 기본 타입 정의 (domain/types.py — `RigidBodyState` 등)
- pytest 설정
- 첫 코드 (CLI Hello World)

**예상 소요**: 1 세션

---

### 🧩 T6. DECISIONS.md 작성 (점진적)

**왜**: ADR 스타일로 "왜 이렇게 결정했나" 기록.

**선행**: 없음 (점진적)

**내용**:
- ADR-013: 두 Workspace 구조 (v0.19)
- ADR-014: 자원 참조 구조 + Bundle (v0.20)
- ADR-015: Vertical Reference 명시 + 자체 규격 지형 (v0.21~v0.22)
- ADR-016: PlacedEntity + MotionKind (v0.21)
- ADR-017: Antenna Model 일반화 + Monopulse (v0.25)
- ADR-018: Editor Workspace Activity + 탭 + 사이드바 (v0.26)
- **ADR-019: 사실적 표적 동역학 (trajectory=reference, 실제=동역학)** (v0.27)
- ADR-020: 크로스 플랫폼 (v0.27 Q-P1)

**예상 소요**: 1 세션 (또는 점진적)

---

## 큰 흐름 (설계 종료 후 — 2026-04-28 합의)

```
0. Phase 0 인프라 셋업
   - GitHub public repo + Apache 2.0 + CI + pyproject.toml + 디렉토리 구조
   - repo_root_drafts/ → 레포 루트 적용
   - python -m workbench 빈 QMainWindow

1. UI 목업 확인 (0과 병렬 가능)
   - T1 — Editor Workspace 5 Activity + Simulator Workspace 패널 시각화
   - 동역학·glint·DLC Plugin Manager 신규 시각화

2. MVP 제작 (Phase 1~5)
   - Phase 1: Primitives 이식
   - Phase 2: Domain Contract + 베이스라인 5종 (multipath/glint/UKF/GNN/refraction)
   - Phase 3: App Layer
   - Phase 4: UI 기본 레이아웃 (1번 결과 적용)
   - Phase 5: 검증 프레임워크 뼈대

2.5 베이스라인 검증 (물리 정확성)
   - 16 § 16.3 5종 검증 시나리오 통과
   - MATLAB Phased Array Toolbox·Stone Soup 비교 demo
   - 신뢰 기반 확보 (v0.34 동기 — "이 프로그램이 생명력을 얻으려면")

3. 재점검 (정합성)
   - 코드 ↔ 계획서 정합 점검
   - 아키텍처 의존 규칙 검사 (import-linter)

4. 주요 기능 확인 (사용성)
   - Editor Workspace 기능: 자원 작성·조립·저장 흐름 (Journey 시나리오)
     → Map 만들기 / Radar 만들기 / Targets CSV import / Scenario 조립 / Validation
   - Simulator Workspace 기능: Run·Pause·Seek·Tracker 동작·3D Scene·Scope POV·메트릭
     → Journey A~F (01 § 1.3) 실증

5. 외부 공개 + 커뮤니티
   - GitHub public announce
   - awesome-trsim-packages repo 생성
   - 첫 외부 PR·Issue 응대

6. MVP+α
   - Phase 6 NN 통합 (Wave 1)
   - Phase 7 DLC 시스템 (.trsim-pkg) (Wave 2)
   - Phase 8 HIL 통합 (DUTAdapter + GT/SIL/HIL 3-way) (Wave 3, v0.38)
   - Q-OP1~5, Q-N7, Q-HIL1~7 결정
```

**핵심 구분**:
- **2.5 vs 4**: 둘 다 "검증"이지만 차원 다름
  - 2.5 = 물리가 정확한가? (수치 비교)
  - 4 = 사용자가 쓸 수 있는가? (UX·Journey)
- **0·1·2 병렬**: T1 UI 목업은 차단 게이트 아님. Phase 0~2는 UI 무관

---

## 작업 의존 그래프

```
✅ v0.16~v0.35 (설계·정합·베이스라인·플랫폼 정체성 모두 완료)

T3 (Phase 0 구현) ⭐ 다음 ── 모든 선행 완료
T1 (UI 목업) ── 독립
T6 (DECISIONS) ── 독립, 점진적
C8/C9 (03/13 DLC 보강) ── SDK 구현 시점에
```

---

## 추천 순서

**다음 세션 (1~2개 진행)**:
1. **T3** (Phase 0 구현 착수) ⭐ — 레포 뼈대 + 오픈소스 인프라 (Apache 2.0/CI/Issue 템플릿 다 준비됨)
2. **T6** (DECISIONS.md ADR) — 점진적 누적, 가벼운 시작

**그 후**:
- **T1** (UI 목업 마무리) — 동역학·glint·DLC 패널 시각화
- **MVP+α**: Phase 7 DLC 시스템 (`.trsim-pkg`)

**언제든**:
- T6 — 점진적 누적

---

## 잠정 원칙

- **한 세션 = 한 주제** 권장 (또는 청크 단위 분할 — v0.34/v0.35에서 검증됨)
- **설계 변경 크면 통합 리뷰** 재실시 — v0.16의 T2 패턴, v0.34 베이스라인 점검 패턴
- **ROADMAP도 살아있는 문서** — 세션 끝마다 진행 상태 반영
- **새 통찰 들어오면** — 진단 → 추상 일반화 → 모듈 추가 (8단계 통찰 흐름 패턴)

---

## 완료 체크리스트

**MVP 설계 단계** — 모두 완료 (v0.16~v0.35):
- [x] T0/T2/T7 (v0.16) — 통합 리뷰 + OPEN_QUESTIONS 신설
- [x] v0.17~v0.27 — Workspaces·자원·좌표·동역학·안테나·Editor
- [x] T8 Editor Workspace 레이아웃 (v0.26)
- [x] v0.28 시각화 + 대기 (Q-P2/Q-A1 closed)
- [x] v0.29 Simulation Domain (Q-MS1/2/3 closed)
- [x] T11 07 NN 보강 (v0.30)
- [x] T10 04 migration Phase 갱신 (v0.31)
- [x] T9 02 architecture 갱신 (v0.32)
- [x] v0.33 Map Editor Flatten Area
- [x] v0.34 베이스라인 보강 (Q-BL1~5 closed, 16 신규)
- [x] v0.35 오픈소스 + DLC 정체성 (Q1-rev/Q2~Q9 closed, 17 신규)
- [x] v0.36 정합성 검토 5세션 (~52~55개 정정)
- [x] v0.37 Phase 0 인프라 + sim_3d 분리
- [x] v0.38 HIL 통합 (HIL-1~7 closed, 18 신규)
- [x] v0.39 Reference Timing + Frame Profiler (D1~D4 closed, 18 § 18.16/18.17 신설)
- [x] v0.40 Physics Lab (PL-1~15 closed, plan 19 신설, 차별점 5+1, 11 Plugin Protocol) ⭐
- [ ] T1 UI 목업 v0.3 마무리 (선택, 코드와 병렬 가능)

**MVP 구현 단계** — 시작 가능:
- [ ] T3 Phase 0 구현 착수 ⭐
- [ ] Phase 1 Primitives 신규 작성
- [ ] Phase 2 Domain Contract + 베이스라인 5종
- [ ] Phase 3~5 (App, UI, 검증)
- [ ] Phase 6 NN (MVP+α — Wave 1)
- [ ] Phase 7 DLC 시스템 (MVP+α — Wave 2)
- [ ] Phase 8 HIL 통합 (MVP+α — Wave 3, v0.38)

**언제든 좋음**:
- [ ] T6 DECISIONS ADR
