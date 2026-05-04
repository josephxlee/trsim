# TRsim 독창성 평가 — 경쟁 분석 v0.1

**작성**: 2026-04-28 (v0.1 분석 보고서, 보존)
**목적**: TRsim의 진짜 차별점·자유로운 영역 식별

> ⚠️ **후속**: 본 분석은 **v0.34 베이스라인 보강 + v0.35 오픈소스+DLC 정체성 전환의 근거**가 됨.
> 본 문서의 권장 사항 중 라이선스 결정 (Apache 2.0)·DLC 시스템·17 open_platform 모두 v0.35에 closed.
> 본 문서는 **분석 시점의 근거 자료**로 보존.

---

## 1. 경쟁 도구 라이선스·접근성 한 표

| 도구 | 출처 | 라이선스 | 가격 | 추적 레이더 특화? | NN 통합? | GUI/IDE? | 오픈소스? |
|---|---|---|---|---|---|---|---|
| **MATLAB Radar Toolbox + Phased Array + Sensor Fusion and Tracking** | MathWorks (US) | 상용 (per-seat) | 1seat ~$10K/년 + 각 toolbox | △ 다중 추적 강점 | △ 별도 Deep Learning Toolbox | ✅ Radar Designer App | ❌ |
| **Cadence AWR / VSS** | Cadence (US) | 상용 (대기업) | 매우 비쌈 (수만 USD~) | △ RF·DSP 위주 | ❌ | ✅ | ❌ |
| **Keysight Radar Signal Processing Models** | Keysight (US) | 상용 | 비쌈 | △ digital twin | ❌ | ✅ ADS | ❌ |
| **Riverside Research RADSim, RadGen, ResourceSIM, PHAROS** | Riverside (미 방산) | 정부·내부 | 비공개 (방산만) | ✅ 완전 특화 | ❌ | ✅ | ❌ |
| **Stone Soup** | Dstl (UK) + 5-eyes | **MIT** | 무료 | ✅ **추적·상태 추정 전용** | △ 외부 Gym 연결 가능 | ❌ Library only | ✅ |
| **RadarSimPy** | RadarSimX (개인/소규모) | **GPL + 상용 dual** | Free tier 제한 / Commercial 별매 | ❌ 신호처리 위주 | ❌ | ❌ Library only | △ (제약 있음) |
| **gr-radar** | GNU Radio 커뮤니티 | **GPL** | 무료 | ❌ SDR용 | ❌ | △ GRC graph | ✅ |
| **OpenRadar** (TI mmWave) | TI 커뮤니티 | **Apache 2.0** | 무료 | ❌ 자동차 mmWave | ❌ | ❌ | ✅ |
| **CARRADA, RADIal 등 데이터셋 + 학술 NN 코드** | 학계 | 다양 (대부분 MIT/CC) | 무료 | △ 자동차 위주 | ✅ | ❌ | ✅ |
| **Pyroomacoustics·기타 시뮬** | 학계 | MIT | 무료 | ❌ | △ | ❌ | ✅ |

**TRsim 위치 (목표)**: **MIT 또는 Apache 2.0 + 완전 무료 + 추적 레이더 IDE + NN 통합 GUI**

이 조합은 **현재 시장에 없음**.

---

## 2. 핵심 경쟁자 심층 비교 — TRsim vs 4개 메이저

### 2.1 비교 매트릭스 (기능별 0~3 점수)

| 기능 영역 | TRsim 목표 | MATLAB Radar Toolbox | Stone Soup | RadarSimPy | Riverside RADSim |
|---|---|---|---|---|---|
| **추적 레이더 단일 표적 안정성** | ⭐⭐⭐ 1급 메트릭 | ⭐ add-on | ⭐⭐ 핵심이지만 다중 위주 | ⭐ 주변 | ⭐⭐ |
| **DSP 블록 ↔ NN 교체 IDE** | ⭐⭐⭐ 핵심 가치 | ⭐⭐ Simulink로 가능 | ⭐ Python 코드만 | ❌ | ⭐ Graphical, NN 없음 |
| **4-error 진단 (Bayes/Train/Dev/Test)** | ⭐⭐⭐ 신설 | ❌ 없음 | ❌ 없음 | ❌ | ❌ |
| **FMCW Triangle 웨이브폼 정밀 시뮬** | ⭐⭐ MVP | ⭐⭐⭐ | ❌ 추적만 | ⭐⭐⭐ | ⭐⭐ |
| **모노펄스 4채널** | ⭐⭐ MVP | ⭐⭐⭐ | ❌ | ⭐⭐ | ⭐⭐ |
| **사실적 표적 동역학 (6 motion_kind)** | ⭐⭐ MVP | ⭐⭐⭐ Aerospace | ⭐ point mass | ⭐ | ⭐⭐ |
| **DEM 지형 + 자체 규격 (land_mask)** | ⭐⭐⭐ 신설 | ⭐⭐ Mapping Toolbox | ❌ | ❌ | ⭐ |
| **좌표계 정합 (vertical_reference 명시)** | ⭐⭐⭐ 신설 | ⭐⭐ | ⭐ | ⭐ | ⭐ |
| **Simulation Domain (Map+Outside)** | ⭐⭐⭐ 신설 | ❌ 명시 안 됨 | ❌ | ❌ | ❌ |
| **대기 모델 3측면 (시각·동역학·전파)** | ⭐⭐ MVP | ⭐⭐ Radar Toolbox 부분 | ❌ | ❌ | ⭐ |
| **자원 라이브러리 + content_hash 재현성** | ⭐⭐⭐ 신설 | ⭐ | ⭐ | ❌ | ⭐ |
| **두 Workspace IDE (Editor/Simulator)** | ⭐⭐⭐ 신설 | ⭐⭐ Simulink | ❌ | ❌ | ⭐⭐ |
| **CommandBus / Single Command Path** | ⭐⭐ 안전성 | ❌ 명시 안 됨 | ❌ | ❌ | ❌ |
| **Pipeline Stage Slot + plugin 동적 로드** | ⭐⭐⭐ 핵심 | ⭐⭐ Simulink 블록 | ⭐⭐⭐ Component | ❌ | ⭐⭐ Graphical |
| **다중 표적 추적기 (JPDA/MHT/MM)** | ⭐ 단순만 (단일 표적 우선) | ⭐⭐⭐ | ⭐⭐⭐ 핵심 | ❌ | ⭐⭐ |
| **빔포밍·DBF·MIMO** | ⭐ MVP+α | ⭐⭐⭐ | ❌ | ⭐⭐ | ⭐⭐ |
| **3D Scene (DEM + 함정 + 파도)** | ⭐⭐ PyVista | ⭐⭐ MATLAB 3D | ❌ | ⭐ matplotlib | ⭐⭐ |
| **SAR / ISAR** | ❌ | ⭐⭐⭐ | ❌ | ⭐⭐ | ⭐ |
| **HDL/FPGA 코드 생성** | ❌ | ⭐⭐⭐ | ❌ | ❌ | ❌ |
| **하드웨어 통합 (HIL)** | ❌ MVP+α | ⭐⭐⭐ | ❌ | ❌ | ⭐⭐ |

### 2.2 점수 의미

- **MATLAB**: 거의 모든 영역에서 ⭐⭐⭐. 단 **TRsim의 핵심 신설 영역(4-error/SimDomain/CommandBus/자원 hash)에는 없음**
- **Stone Soup**: 추적·NN 통합 강점, 하지만 **신호처리·웨이브폼·UI 모두 없음**
- **RadarSimPy**: 신호처리만, **추적·NN·UI 다 없음**, 라이선스 제약
- **Riverside**: 방산 내부, 외부 접근 불가

### 2.3 결론

**TRsim과 정면 경쟁할 도구는 없다.** 다음 두 가지 조합:
- "추적 레이더 + IDE" → **Riverside만 비슷, 외부 비공개**
- "추적 + NN 비교 + 4-error 진단" → **어디에도 없음**

**TRsim의 niche**: **무료/오픈소스 추적 레이더 알고리즘 검증 IDE**.

---

## 3. 라이선스·특허 자유 영역 분석

### 3.1 라이선스 관점에서 자유로운 영역

#### ✅ 완전 자유 (특허·라이선스 거의 위험 없음)

이 영역은 본 프로젝트가 자유롭게 만들어 **MIT/Apache 2.0**으로 배포 가능:

1. **4-error 진단 시스템** (Bayes/Training/Dev/Test)
   - Andrew Ng의 ML 진단 패턴은 **공개 교육 자료**, 특허 없음
   - 추적 레이더 검증에 적용한 건 본 프로젝트 신설
   - 특허 위험: 거의 0

2. **Simulation Domain + OutsideEnvironment 분리**
   - Map 안 정밀 / Map 밖 단순 가정
   - 일반적 SW 패턴, 특허 없음
   - 본 프로젝트가 처음 명시적으로 분리

3. **자체 규격 지형 (terrain.npz + land_mask)**
   - DEM 한계 회피, land/sea 구분 4 방식
   - 일반 numpy 배열 포맷
   - 특허 위험 0

4. **Vertical Reference 명시 시스템 (egm96/wgs84/msl_local)**
   - 측지학 표준 (GRS, EGM96, WGS84)은 모두 **공개 표준**
   - 본 프로젝트의 명시적 분리는 SW 디자인 패턴

5. **CommandBus / Single Command Path**
   - 일반 SW 디자인 패턴 (CQRS와 비슷)
   - 특허 없음

6. **Workspace 분리 (Editor/Simulator)**
   - VS Code·IntelliJ 같은 IDE 패턴 일반
   - 특허 없음

7. **Pipeline Stage Slot + 플러그인 시스템**
   - GStreamer / AudioUnit / VST 같은 패턴 일반
   - 특허 없음 (특정 기업 구현체와만 차이)

8. **자원 참조 + content_hash 재현성**
   - Git·Nix·Bazel 같은 hash 기반 재현성 일반
   - 특허 없음

9. **PlacedEntity·MotionKind 추상**
   - 일반 OOP 디자인
   - 특허 없음

#### ⚠️ 주의가 필요한 영역

10. **모노펄스 각도 추정**
    - 알고리즘 자체는 1940년대 발명, **특허 만료**
    - 단 **특정 회사 구현체(BAE Systems·Lockheed·Hanwha 등)는 특허 가능성**
    - 안전한 길: 교과서적 표준 알고리즘만 구현 (Skolnik의 Radar Handbook 식)

11. **EKF / UKF / IMM**
    - 알고리즘은 모두 **공개·특허 만료** (1960~80년대)
    - Stone Soup가 이미 MIT 라이선스로 구현 — 따라가도 안전

12. **JPDA / MHT**
    - 1970~80년대 발명, 특허 만료
    - Stone Soup도 구현

13. **CFAR (CA/OS/등)**
    - 표준 알고리즘, 특허 만료
    - 모든 도구가 구현

14. **FMCW Triangle 웨이브폼**
    - 자동차 레이더 표준, 공개
    - 특허는 특정 변형(예: Bosch·Continental 특정 PRF 패턴)에만

15. **Phased array beamforming**
    - 기본은 공개, **MIMO·DBF 특정 알고리즘**은 특허 가능 (Texas Instruments·NXP 등)
    - 안전한 길: uniform weighting array factor만 구현 (이미 v0.25에서 그렇게 결정)

#### 🔴 피해야 할 영역

16. **특정 RCS 모델** — 일부는 군사 특허
    - 안전: Swerling 0~5 표준만 사용

17. **특정 빔 패턴 합성 알고리즘** (Taylor·Chebyshev 일부 변형)
    - 표준은 공개, 특정 특허 변형은 회피
    - 안전: 표준 함수만 사용

18. **자동차 mmWave 특정 칩셋 인터페이스** (TI AWR1843·NXP TEF82xx)
    - 펌웨어 특허 있음
    - 본 프로젝트는 추상 레이어만, 구체 칩 미터치 → 안전

### 3.2 특허·라이선스 안전 가이드 (TRsim용)

```
✅ 사용 안전: 1940~1990년대 표준 레이더 알고리즘 (대부분 만료)
✅ 사용 안전: Stone Soup·MATLAB 공개 문서에 이름이 나오는 알고리즘
✅ 사용 안전: 측지학 표준 (EGM96·WGS84·ITU-R P.838)
✅ 사용 안전: 일반 SW 디자인 패턴 (CQRS·Plugin·Workspace)
⚠️ 주의: 2000년대 이후 발명, 특히 자동차 mmWave 칩 펌웨어
⚠️ 주의: 특정 기업 이름 붙은 알고리즘 변형 (Bosch BroadR-Reach 같은)
🔴 회피: NDA 자료·내부 사양서에서 본 알고리즘
🔴 회피: 특정 군사 plat 특허 (외부 자료로만 검증)
```

### 3.3 라이선스 권장: **Apache 2.0**

**왜 MIT가 아니라 Apache 2.0?**
- MIT보다 **특허 라이선스 명시적 grant** 포함 (사용자 보호)
- 기업 채택 친화 (구글·아파치·Anthropic 모두 채택)
- TensorFlow·PyTorch도 Apache 2.0 (NN 호환성 ↑)

**대안 — MIT** (Stone Soup와 같은 라이선스로 호환성 강조)

**비추천 — GPL**
- RadarSimPy 길로 가면 채택 한계
- 기업·방산이 못 씀 (GPL-incompatible)

---

## 4. TRsim의 진짜 독창성 (가장 중요한 부분)

### 4.1 5가지 독창성 — 우선순위 순

#### 🥇 1순위: **추적 알고리즘 검증 IDE**
**핵심**: "Stone Soup가 라이브러리이고 MATLAB이 종합 도구인데, **추적 알고리즘만 빠르게 비교·교체하는 가벼운 IDE는 시장에 없음**"

- VS Code · Jupyter처럼 **친화적 UI에서 알고리즘 hot-swap**
- 결과를 즉시 4-error로 분석
- 자원 라이브러리에서 시나리오 골라 즉시 비교

#### 🥈 2순위: **DSP ↔ NN 동일 인터페이스 교체·비교**
**핵심**: "어떤 연구원이 'EKF를 LSTM으로 바꿔보면?' 하는 질문에 **5분 안에 답을 얻는 도구**"

- 학술 NN 연구는 활발하지만 표준 비교 환경이 없어 논문마다 setup 다름
- TRsim은 **Pipeline Stage Slot으로 동일 환경에서 비교** 보장
- Variant 6종 (A_ideal/B_realistic/C_rain/...)으로 도메인 시프트 측정

#### 🥉 3순위: **4-error 진단 표준화**
**핵심**: "Andrew Ng의 ML 워크플로를 추적 레이더에 도입"

- Bayes Error → Avoidable Bias → Variance → Data Mismatch
- 추적 레이더 분야에 이런 진단 프레임워크 없음
- 학술 연구가 사용 시작하면 **사실상 표준** 자리

#### 4순위: **단일 표적 안정성을 1급 메트릭으로**
**핵심**: 추적 레이더 운영 현실 반영

- 다중 추적이 학술 주류지만 **현장 운영은 종종 단일 표적 lock**
- Lock-on 안정성 (RMSE in stable phase, recovery after lock loss 등) 1급

#### 5순위: **사용자 통찰의 흐름이 반영된 디테일**
- 좌표계 정합 (vertical_reference 명시)
- 자체 규격 지형 (land_mask)
- Simulation Domain (빔이 Map 넘어가는 문제)
- 평탄화 도구 (실무 시나리오)

이런 디테일들이 **현장 사용자가 필요한 것**이지, 마케팅 문서에 안 적힌 것들. 진짜 가치는 여기 있음.

### 4.2 종합 — TRsim의 한 줄 가치 제안 (제안)

> **"무료·오픈소스로, 추적 레이더의 DSP 블록을 NN으로 교체했을 때 단일 표적 추적 안정성이 어떻게 변하는지 IDE에서 5분 안에 비교·진단하는 워크벤치"**

- 무료·오픈소스 → MATLAB·RadarSimPy 차별화
- 추적 레이더 + 단일 표적 안정성 → 다중 추적 도구와 차별화
- DSP↔NN IDE 비교 → 학술 연구 표준화 자리
- 4-error 진단 → 분석 깊이 차별화

---

## 5. 진짜 위험·기회 평가

### 5.1 위험

1. **MATLAB이 추격할 위험**
   - 가능성: 중간. 단 MATLAB은 추적 레이더 단일 표적 niche에 우선순위 낮음
   - 대응: 오픈소스 + 학술 채택 빠르게

2. **Stone Soup이 NN·UI 추가**
   - 가능성: 중간. 이미 RL/DRL 통합 시도 중
   - 대응: TRsim의 "IDE 통합 GUI" + "신호처리까지 통합"이 차별

3. **방산 기관이 비공개 도구 만들어 시장 비자유화**
   - 가능성: 낮음 (Riverside는 이미 비공개)
   - 대응: 오픈소스 자체가 방어막

### 5.2 기회

1. **학술 표준 도구 자리**
   - 추적 레이더 + NN 논문 작성자들이 공통 환경 필요
   - TRsim이 그 자리 찾으면 해마다 인용·확산
   - **Stone Soup 모델을 따르되 IDE 추가**

2. **방산 / 정부 연구소 채택**
   - MATLAB 라이선스 비용 부담, 오픈소스 대안 수요
   - TRsim이 무료 + 충분한 정밀도면 채택 가능

3. **교육 시장**
   - 대학 레이더 강의·실습
   - MATLAB 라이선스 못 쓰는 곳 많음
   - TRsim이 무료 + IDE면 강의 도구로 채택

4. **자동차/드론/방산 스타트업**
   - 초기 단계 라이선스 비용 부담
   - TRsim이 충분히 정밀하면 채택

---

## 6. 구체 권장 — TRsim 다음 작업 우선순위

설계서에 **명시적으로 강화·강조**할 것들:

### 🔥 즉시 강조해야 할 5가지

1. **01 vision_scope의 가치 제안 재작성**
   - 현재: "DSP·웨이브폼 개선안의 추적 성능을 시뮬로 검증하는 IDE 워크벤치"
   - 개선: 위 § 4.2 한 줄 가치 제안

2. **04 migration의 Phase 0 — "비교 매트릭스" 산출물 추가**
   - Phase 0 종료 시 **Stone Soup·MATLAB 비교 데모** 의무화
   - "우리가 뭘 다르게 하는지" 코드로 증명

3. **07 nn_integration의 Bayes Error 측정**
   - 현재 4-error에 Bayes는 옵션
   - 시뮬은 GT가 있으니 **Bayes 측정 가능 (실 데이터와 다른 강점)** 강조

4. **새 § 16 또는 새 문서: "Differentiation"**
   - 본 분석을 정식 계획서 문서로
   - 새 Claude·새 개발자가 "왜 이 프로젝트인가" 이해

5. **라이선스 결정 — Apache 2.0**
   - 현재 LICENSE 미정
   - Apache 2.0으로 정식 결정 (특허 grant + 기업 친화)

### 📋 중기 (구현 단계)

6. **Stone Soup adapter 추가**
   - Stone Soup의 Tracker를 plugin으로 사용 가능하게
   - 사용자 입장: "내가 알던 도구 그대로 + IDE"
   - 채택 장벽 낮춤

7. **MATLAB 결과 비교 demo**
   - 같은 시나리오를 MATLAB과 TRsim에서 돌려 numeric 일치 보임
   - 신뢰도 확보

8. **학술 데이터셋 어댑터**
   - CARRADA · RADIal 등 공개 데이터셋 import
   - 학계 진입 장벽 낮춤

---

## 7. 최종 평가 — 한 문단

**TRsim은 "MATLAB의 작은 복제"가 아니라 "Stone Soup의 IDE화 + DSP 통합 + NN 워크플로 표준화"의 새 도구가 될 수 있다.** 시장에 정확히 같은 niche의 경쟁자는 없으며, 라이선스·특허 면에서도 자유로운 영역이 충분히 넓다. 진짜 차별점인 **(1) 추적 레이더 IDE, (2) DSP↔NN 비교, (3) 4-error 진단**에 집중하면 학술·방산·교육 모든 영역에서 채택 가능. 단 **사실성 강화 (v0.27 동역학·v0.28 대기 등)는 차별점이 아니라 "필수 베이스라인"** 이라는 인식 전환이 필요. 이걸로 너무 많은 시간 쓰면 추격에 그치고, 진짜 차별점에 자원이 부족할 수 있음.
