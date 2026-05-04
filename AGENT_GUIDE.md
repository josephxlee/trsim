# AGENT_GUIDE.md — TRsim 프로젝트에서 Claude가 일하는 방법

**이 문서의 독자**: 이 프로젝트에서 작업하게 되는 **Claude (AI Assistant)** 자신.

사용자(프로젝트 소유자)가 새 세션에서 "TRsim 작업 이어가자" 라고 했을 때, Claude는 먼저 이 문서를 읽고 여기 적힌 방식대로 행동한다.

---

## 0. 가장 먼저 할 일

사용자가 작업을 요청하면 **질문에 바로 답하기 전에** 다음 파일들을 읽어 맥락을 확보한다:

1. `COWORK_HANDOFF.md` — cowork 진입 시 첫 문서 (12 섹션 종합 가이드)
2. `SESSION_SUMMARY.md` — 직전 세션에서 어디까지 했고 다음에 뭘 할 예정이었는지
3. `ROADMAP.md` — 전체 남은 작업과 우선순위 + 6단계 큰 흐름
4. `REVIEW_REPORT_v0.35.md` — 정합성 검토 결과 (어느 게 권위, 어느 게 참조 보존)
5. `OPEN_QUESTIONS.md` — 답 기다리는 질문들 (블로커 0)
6. `plan/00_README.md` — 17 plan 진입점 + 변경 이력

요청된 작업에 따라 추가로 읽을 것:
- 계획서 내용 수정이면 → 해당 `plan/NN_*.md`
- 용어 확인이면 → `plan/appendix_B_glossary.md`
- 과거 결정의 이유가 필요하면 → `DECISIONS.md` (있으면)
- Phase 0 시작이면 → `plan/04_migration.md` § 4.3 + `repo_root_drafts/`

읽지 않고 추측으로 대답하지 않는다.

---

## 1. 프로젝트 정체성 (절대 잊지 말 것)

TRsim은 **추적 레이더(Tracking Radar) 시뮬레이터 + IDE 스타일 워크벤치 + DLC 확장 + HIL 통합 + Physics Lab 가능 오픈소스 플랫폼**이다.

### 한 줄 정의 (v0.40)

> 추적 레이더 알고리즘·자원·시각화·**물리 모델**을 **DLC 패키지로 자유롭게 확장하는 오픈소스 워크벤치 플랫폼**.
> Apache 2.0 코어 + .trsim-pkg DLC + HIL 통합 (펌웨어 검증) + **Physics Lab 으로 물리 모델 3D 시각화·검증·진화 가능**.

### 한 단락 정의 (기능 중심)

> 다중 표적 환경에서 사용자가 선택한 단일 표적을 안정적으로 추적하는 것이 목표인
> 추적 레이더에 대해, DSP·웨이브폼 개선안의 추적 성능을 시뮬레이션으로 검증한다.
> NN 개발을 위한 별도 모드도 제공하며, **DLC 패키지 시스템으로 알고리즘·자원·시각화·물리 모델을 자유롭게 확장 가능**.
> v0.38 부터 HIL 통합 (GT/SIL/HIL 3-way) + v0.40 부터 Physics Lab (3-pane 인터랙티브 + 9 Test Objects + 4 시간 모드).

### 정체성 진화 (단계별)

| 단계 | 정체성 |
|---|---|
| MVP | 추적 레이더 IDE ("Stone Soup의 IDE 버전") |
| MVP+α (Wave 1) | + NN 통합 |
| MVP+α (Wave 2) | + DLC 시작 (VS Code Extension 모델) |
| MVP+α (Wave 3) | + HIL 통합 (v0.38) |
| **MVP+α (Wave 4)** | **+ Physics Lab (v0.40)** ⭐ |
| 성장기 | 플랫폼 ("Blender의 추적 레이더 버전") |
| 성숙기 | 학술·산업 표준 |

### 핵심 차별점 (5 + 1, v0.40)

1. 추적 알고리즘 검증 IDE
2. DSP ↔ NN 동일 인터페이스 비교
3. 4-error 진단
4. HIL 통합 (v0.38)
5. **Physics Lab — 인터랙티브 물리 실험실** ⭐ v0.40
6. ➕ DLC 에코시스템

상세: `plan/01_vision_scope.md`, `plan/17_open_platform.md`, `plan/19_physics_lab.md`

### 이 정체성에서 파생되는 불변 원칙

- **주 목적은 추적 성능 검증** — 탐지율이나 전반적 DSP 품질이 아님
- **Primary Target이 1급 개념** — 모든 메트릭·UI·제어가 선택 표적 중심
- **Closed-Loop Tracking** — EKF/UKF 출력이 Positioner로 피드백됨. Positioner Lag이 성능의 일부
- **멀티 추적 + 단일 포커스** — 모든 표적 Track 유지하되 선택 표적에만 집중 (v0.34 GNN 추가)
- **NN은 선택적** — 기본은 NN 없이도 동작. NN 모드는 별도 진입
- **FMCW Triangle 단독** — 다른 파형(Hybrid, CW+FMCW 등)은 미래 RadarModel
- **Multi-scatterer 표적** (v0.34) — 점 표적이면 glint 없어 우리 차별점("단일 표적 추적 안정성") 의 핵심 변수가 사라짐
- **오픈소스 + DLC 에코** (v0.35) — Apache 2.0, 적극 공공 GitHub, .trsim-pkg 확장
- **SDK Layer는 안정 API** (v0.35) — Domain 변경이 DLC를 깨뜨리지 않게

이 원칙들은 이미 여러 버전에 걸쳐 교정된 결과다. 새 제안이 이 원칙과 충돌하면 **수용하기 전에 사용자에게 확인**한다.

---

## 2. 작업 규약

### 2.1 파일 수정

- 기존 파일 수정 시 **관련 파일 전체 맥락 파악 후** 수정 (교차 참조 많음)
- 03 data model 수정 시 → 05 UI, 07 NN 영향 여부 점검
- 07 NN 수정 시 → 03 Metrics, 05 UI 영향 여부 점검
- 01 정체성 수정 시 → 전체 문서 영향 큼. 반드시 사용자 합의 후
- 06 Deferred Physics 수정 시 → 01 MVP 범위와 일관성 점검

### 2.2 버전 올리기

계획서 전체 버전(v0.X)은 **의미 있는 변경 블록이 끝났을 때** 올린다:

- 작은 오타 수정은 버전 올리지 않음
- 새 섹션 추가, 핵심 Contract 변경, 정체성 재정의 등은 버전 올림
- 버전 올리면 **반드시 `plan/00_README.md`의 변경 이력 표에 1줄 추가**
- 변경 이력 1줄은 "뭐가 바뀌었는지 + 파급 범위"를 포함 (예시는 기존 이력 참고)

### 2.3 산출물 위치

Cowork 환경 기준:

```
TRsim/                              ← 프로젝트 루트 (사용자 로컬)
├── README.md
├── AGENT_GUIDE.md                  ← 이 문서
├── SESSION_SUMMARY.md              ← 세션 끝날 때 갱신
├── DECISIONS.md                    ← 주요 결정 ADR (점진적 누적)
├── OPEN_QUESTIONS.md               ← 미결 질문 (점진적 누적)
├── ROADMAP.md                      ← 다음 작업 우선순위
├── plan/*.md                       ← 계획서 (수정 주 대상)
└── ui_mockup/*.html                ← UI 목업
```

- 계획서 수정은 `plan/` 안에서만
- 새 산출물(예: 함선 3D RCS 설계 문서)은 번호 붙여 `plan/`에 추가 (예: `09_target_rcs_rendering.md`)
- 임시 파일·스케치는 루트나 `plan/` 밖의 별도 디렉토리

### 2.4 세션 끝마다

사용자가 "오늘은 여기까지" 또는 세션 종료 신호를 주면:

1. `SESSION_SUMMARY.md`를 **이번 세션 내용으로** 갱신 (이전 내용 덮어쓰기)
   - 이번 세션에 뭘 완료했는지
   - 지금 어디까지 왔는지
   - 다음에 뭘 할 예정이었는지
2. 새로 생긴 결정이 있으면 `DECISIONS.md`에 추가 (있으면)
3. 새 미결 질문 생겼으면 `OPEN_QUESTIONS.md` 갱신 (있으면)
4. `ROADMAP.md` 진행 상태 반영

---

## 3. 사용자와의 대화 방식

### 3.1 언어

- 기본 **한국어**. 사용자가 영어로 쓰면 영어로.
- 레이더·DSP·ML 전문 용어는 영어 그대로 쓰는 게 자연스러움 (pairing, EKF, CFAR, variance, bias 등)

### 3.2 말투

- 반말 톤 OK. 사용자와 동료 같은 관계
- 존댓말로 부드럽게 포장하지 말고 **짧고 정확하게**
- "제 생각엔..." "괜찮으시다면..." 같은 완곡 표현 최소화
- 확신 있으면 단정. 추측이면 추측임을 명시

### 3.3 피드백 루프 패턴

이 프로젝트는 **Claude 제안 → 사용자 도메인 지식으로 교정** 패턴이 반복됐다. 과거에 이런 교정이 있었다:

- v0.5: "Hybrid 레이더 특징" 이라고 추론 → 실은 별개 레이더였음 → v0.6 철회
- v0.7: Target Gate를 독립 개념으로 다룸 → Tracker 의존 옵션으로 재정의
- v0.11: 물리 모델 충분하다고 판단 → 전수 검토 요청받음 → MVP 4종 추가
- v0.13: NN이 주 목적과 혼선 지적받음 → 두 모드 분리

**교훈**: Claude의 일반 지식이 이 레이더 도메인 특유의 사정과 안 맞을 수 있다. **확신 있는 주장도 도메인 지식으로 뒤집힐 수 있음**을 받아들이고, 사용자가 교정하면 즉시 수용하고 파급 범위까지 반영한다.

### 3.4 질문 방식

복잡한 선택지를 물을 때는 **선택지를 명시한 단답형 질문** 선호. 사용자가 모바일에서도 빠르게 답할 수 있게.

이번 세션에서 쓴 `ask_user_input_v0` 도구처럼 구조화된 질문이 효과적이었음. Cowork에서 동일 도구 지원 여부는 환경마다 다름 — 없으면 번호 붙인 선택지로 대체.

### 3.5 큰 결정 전 확인

다음 경우엔 반드시 사용자 확인 받고 진행:

- 계획서 전체 버전(v0.X) 올리는 변경
- 정체성·MVP 범위 변경
- Contract·스키마 구조 변경
- 새 `.md` 파일 생성 (10번대 이후)
- 파일 삭제·이름 변경

---

## 4. 이 프로젝트의 맥락 빠르게 잡기

새 세션에서 Claude가 혼자 파악하기 어려울 수 있는 **암묵적 전제**들:

### 4.1 외부 자산의 의미

- `rcs_monopulse_` = C6678 DSP 펌웨어. **Contract 매핑의 기준**. 이 쪽 함수 시그니처가 Workbench Python Contract와 일치해야 함
- `target_pairing.c`는 **빈 파일** — Workbench가 Pairing 알고리즘 개발의 주 도구가 되는 이유
- 옛 프로토타입 (`sim_3d`) 은 정상 동작 미검증 코드. **회귀 비교나 직접 이식 대상 아님**. 신규 작성 원칙

### 4.2 "왜 계획서가 18개씩이나" 되는지

처음엔 1~2개로 시작했으나, 도메인이 크고 교차 관심사가 많아 분할된 것. 분할 기준은:
- 00 = 진입점·이력
- 01 = 전략 (왜 만드나)
- 02 = 큰 그림 (어떻게 쪼개나)
- 03 = 데이터 계약 (뭘 주고받나)
- 04 = 신규 구현 순서 (Phase 0~8)
- 05 = UI (🟡 참조 보존, 권위는 13)
- 06 = 횡단 주제 (🟡 참조 보존, 권위는 17·02 § 2.6b)
- 07 = NN (특수 영역)
- 08 = 레이더 파형 (특수 영역)
- 09 = Radar Platform (Maritime/Fixed Ground)
- 10 = Workspaces (자원 라이브러리)
- 11 = 좌표계 (WGS84·ENU·SimulationDomain)
- 12 = Placement & Motion (MotionKind 7)
- 13 = Editor Workspace (5 Activity 상세)
- 14 = Dynamics (사실적 동역학 + ExtendedTarget)
- 15 = Atmosphere (ISA + rain + refraction)
- 16 = Baseline Audit (v0.34 베이스라인 5종)
- 17 = Open Platform (v0.35 오픈소스 + DLC, 정체성 핵심)
- **18 = HIL Integration (v0.38 HIL 통합, GT/SIL/HIL 3-way) + v0.39 Reference Timing Mode + Frame Profiler**
- **19 = Physics Lab (v0.40 — 3-pane 인터랙티브 + 9 Test Objects + 4 시간 모드 + 사용자 물리 plugin) ⭐**
- appendix A = 🚫 DEPRECATED (sim_3d 평가 무효)
- appendix B = 용어집 (870줄, v0.27~v0.35 신규 21 용어 + v0.38 HIL 용어)

새 주제 추가 시 기존 문서를 확장할지 신규 생성할지 판단.

### 4.3 사용자 환경 추정

- 업무 도메인: 추적 레이더 신호처리 전반 개발
  - 펌웨어 (C6678 등 DSP 임베디드)
  - FPGA 로직 (Verilog/VHDL, IP 통합·timing closure)
  - Python 알고리즘 (TRsim 자체)
- 로케일: 한국
- 기존 도구: C6678 임베디드, MATLAB, Python, FPGA 툴체인 (Vivado/Quartus 등)

> **참고**: FPGA 는 사용자의 **능력 영역**일 뿐, **TRsim의 검증 대상은 아님**.
> 즉 FPGA HIL DUT 로는 다루지 않음. 단 사용자가 FPGA 개발자라는 점은 시뮬레이션
> 대상의 timing/resource/throughput 한계를 평가할 때 자연스러운 기준이 됨
> (예: "이 알고리즘이 FPGA 로 실현 가능한가" 같은 사용자 직관).

---

## 5. 흔한 함정

이 프로젝트 작업하다 Claude가 실수하기 쉬운 지점들:

1. **"NN도 그냥 Plugin"이라고 간소화** — 표면적으로는 맞지만 NN 모드는 별도 UI·워크플로. v0.13 분리가 이걸 명시화함
2. **레이더 파형을 쉽게 일반화** — FMCW Triangle과 CW+FMCW Hybrid는 **완전 다른 레이더**. Pairing 정의도 다름. 섞지 말 것
3. **"추적 = EKF"로 등치** — Tracker는 교체 가능한 Slot이고 EKF는 기본 구현. Contract를 EKF 특성에 결합시키지 말 것
4. **Target Gate를 독립 개념으로** — 이건 Tracker가 필요로 할 때만 활성화되는 옵션. 독립 스테이지로 설계하지 말 것
5. **물리 모델을 무한 확장** — MVP 4종만 확실히. 나머지는 Deferred 6 Suite. 새 물리 제안 나오면 먼저 어느 Suite에 속하는지 확인
6. **Primary Target을 Plugin에 노출** — DSP Plugin은 Primary가 누군지 몰라야 함. Primary는 메트릭·제어 레벨에서만 쓰임

---

## 6. 도구 사용

Cowork 환경에서 기대되는 도구:

- **파일 읽기·편집** — 주 작업. 계획서 `.md` 파일이 주 편집 대상
- **파일 생성** — 새 계획서 문서 추가 시
- **구조화 질문** (가능하면) — 사용자 결정이 필요할 때

이번 세션(Claude.ai)에서 썼지만 Cowork에 없을 수 있는 도구:

- UI 목업 즉시 렌더링 (Artifacts) — Cowork에선 사용자가 브라우저로 열어봐야
- 파일 업로드 공유 (present_files) — Cowork는 로컬 파일 시스템이라 불필요

### Drive 업로드는 금지

Claude.ai에서 시도했던 Drive 자동 업로드는 **이용 정책상 불가**로 확인됨. 사용자가 직접 올린다.
Claude는 파일을 준비하고 압축만 제공, 업로드는 사용자 몫.

---

## 7. 미래 큰 작업들 (v0.37 시점)

ROADMAP.md § 큰 흐름 (6단계) 에 상세. 대략:

- **즉시 가능**: T3 Phase 0 인프라 셋업 (repo + Apache 2.0 + CI + 빈 QMainWindow)
- **단기**: Phase 1 Primitives 신규 작성, Phase 2 Domain Contract + 베이스라인 5종, T1 UI 목업 마무리 (Phase 0과 병렬)
- **중기**: Phase 2.5 베이스라인 검증 (Stone Soup·MATLAB 비교) → Phase 3 App Layer → Phase 4 UI → Phase 5 검증 프레임워크
- **외부 공개**: Phase 5 통과 후 GitHub public announce, awesome-trsim-packages
- **MVP+α**: Phase 6 NN 통합, Phase 7 DLC `.trsim-pkg` 시스템, **Phase 8 HIL 통합 (v0.38)**

각 작업의 선행 조건과 예상 결과물은 ROADMAP.md 참조.

---

## 8. 이 문서 갱신

`AGENT_GUIDE.md` 자체도 프로젝트 진화에 따라 갱신된다:

- 새로운 함정을 발견하면 § 5에 추가
- 프로젝트 정체성 재정의 있으면 § 1 갱신
- 대화 패턴의 새 합의 있으면 § 3 갱신

갱신 시 하단에 "최근 갱신: YYYY-MM-DD, 변경 내용" 한 줄 추가.

---

최근 갱신: 2026-05-02 — v0.40 시점 갱신 (Physics Lab 추가, plan 19 신설, 차별점 5+1, 11 Plugin Protocol, MVP+α Wave 4)
