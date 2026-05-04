# OPEN_QUESTIONS.md — 미결 질문 통합 (v0.40 기준)

**마지막 갱신**: 2026-04-28

---

## 0. 우선순위 범례

- 🔴 **블로커** — 답 없으면 진행 불가
- 🟠 **곧 필요** — 1~2 세션 내 결정
- 🟡 **중기** — MVP 전에는 결정
- 🟢 **장기** — MVP 이후 또는 사용 피드백 후

---

## 1. 블로커 (🔴)

**없음.** v0.27 시점 모든 큰 설계 결정 완료.

---

## 2. 곧 필요 (🟠)

### Q-EW1. 탭 split (한 화면 두 자원 동시 보기)
- **출처**: 13 § 13.11
- **결정 시점**: Editor Workspace 풀 구현 시
- **현재 가정**: MVP+α (드래그로 split, IntelliJ 식)

### Q-EW2. Resource Browser 검색·필터 범위
- **출처**: 13 § 13.11
- **결정 시점**: Resource Browser 구현 시
- **현재 가정**: MVP는 이름·hash 메타까지, trajectory 내용 검색은 MVP+α

### Q-EW3. Editor 미니 preview (배치 검증용)
- **출처**: 13 § 13.11
- **결정 시점**: Editor 풀 사용 시점
- **현재 가정**: Sim 미실행 상태로 "정적 view"만 (Coherence Validator로 충분)

### Q-EW4. Auto-save 정책
- **출처**: 13 § 13.11, 13 § 13.8.1
- **결정 시점**: 사용자 피드백 후
- **현재 가정**: MVP는 disable, MVP+α에서 옵션

### Q-EW5. Resource Dependency 시각화 시점
- **출처**: 13 § 13.11, 13 § 13.7.3
- **결정 시점**: 자원 많아질 때 (사용 후)
- **현재 가정**: MVP+α

---

## 3. 중기 (🟡)

### Q-A1. Antenna 정밀 빔 패턴 (실측·EM 시뮬 데이터 import)
- **출처**: 08 § 8.5a.7
- **결정 시점**: MVP 후 (정밀 시뮬 요구 시점)
- **현재 가정**: sinc² / uniform array factor 단순 모델

### Q-A2. Monopulse calibration 데이터 형식
- **출처**: 08 § 8.5a.4 boresight_calibration
- **결정 시점**: 실 모노펄스 시나리오 구현 시
- **현재 가정**: dict (구조 미확정)

### Q-D1. 풀 6DOF 도입 시점 (자세 동역학)
- **출처**: 14 § 14.10, 14 § 14.11
- **결정 시점**: MVP+α 첫 Wave
- **현재 가정**: MVP는 Level 1 (3DOF + velocity 기반 자세), Level 2가 6DOF

### Q-D2. ISA atmosphere 정밀도
- **출처**: 14 § 14.4.2, 14 § 14.10
- **결정 시점**: 고고도 표적 시나리오
- **현재 가정**: MVP는 단순 ISA 근사 (tropospher), MVP+α는 풀 ISA

### Q-D3. POWERED_FLIGHT thrust vs trajectory 우선순위
- **출처**: 14 § 14.5.2, 14 § 14.11
- **결정 시점**: 미사일 시나리오 첫 구현 시
- **현재 가정**: `use_trajectory_as_reference` flag로 사용자 선택

### Q-D4. 동역학 적분 라이브러리
- **출처**: 14 § 14.6.1, 14 § 14.11
- **결정 시점**: T3 Phase 0 시작 시
- **현재 가정**: 자체 RK4 (의존성 최소)

### Q-D5. BALLISTIC spin rate (자체 회전, RCS 영향)
- **출처**: 14 § 14.5.3, 14 § 14.11
- **결정 시점**: BALLISTIC 표적 RCS 정밀화 시점
- **현재 가정**: MVP는 spin 무시 또는 단순 일정 회전

### Q-D6. 동역학 Sub-step 자동 조정 (빠른 표적 처리)
- **출처**: 14 § 14.12
- **결정 시점**: BALLISTIC 표적 정밀도 검증 시
- **현재 가정**: 고정 sub-step 0.005s

### Q-D7. 6DOF 도입 시 Aircraft Coordinated Flight 가정 강화 vs 풀 lateral 동역학
- **출처**: 14 § 14.12
- **결정 시점**: Level 2 6DOF 도입 시점 (MVP+α)
- **현재 가정**: Level 1은 coordinated flight, Level 2 미정

### Q-M1. Map Origin 변경 시 자동 변환
- **출처**: 11 § 11.3.3 + 11.9
- **결정 시점**: 자원 fork 도구 구현 시
- **현재 가정**: 변경 불가, 새 Map Save As

### Q-M2. DEM 해상도 표준 (10m / 30m / 100m)
- **출처**: 11 § 11.9
- **결정 시점**: Map Editor 구현 시
- **현재 가정**: 사용자 선택, 기본 30m

### Q-W1. Wave 응답 모델 자유도 (sinusoidal vs 측정 기반)
- **출처**: 12 § 12.12
- **결정 시점**: 정밀 해상 시나리오 시점
- **현재 가정**: sinusoidal MVP

### Q-N1. NN 학습 실행 위치
- **출처**: 07 § 7.9 N1
- **결정 시점**: Wave 1 진입 시 (Pairing NN 첫 구현)
- **현재 가정**: Workbench는 Dataset·평가만, 학습은 외부 CLI

### Q-N2. GPU 지원 정책
- **출처**: 07 § 7.9 N2
- **결정 시점**: Wave 1
- **현재 가정**: CPU 전용

### Q-N7. NNPluginMixin을 SDK Public API에 포함할지
- **출처**: 07 § 7.3
- **결정 시점**: SDK 안정화 시점 (Phase 7)
- **현재 가정**: MVP는 옵션 B — SDK는 일반 Protocol만, NNPluginMixin은 App Layer 헬퍼

### Q-S1. 시나리오·표적 Trajectory 편집 UI 형태
- **출처**: 12 § 12.7.3, 13 § 13.6.6
- **결정 시점**: MVP 후 사용 피드백
- **현재 가정**: MVP는 CSV import만, UI는 후속

### Q-T1. Resource History 정책 (옛 자원 버전 보관)
- **출처**: 10 § 10.10.6
- **결정 시점**: MVP+α
- **현재 가정**: 최근 10개 버전 자동 보관 (디스크 한도)

### Q-AT1. Stratosphere ISA 도입 시점 (11+ km)
- **출처**: 15 § 15.3.1, 15 § 15.10
- **결정 시점**: 고고도 표적 시나리오 (탄도 미사일 등) 첫 구현 시
- **현재 가정**: MVP는 트로포스피어만 (11 km 이상 clamp)

### Q-AT2. Ducting 모델 정밀도
- **출처**: 15 § 15.5.3, 15 § 15.10
- **결정 시점**: 정밀 해상 시나리오 (해수면 ducting) 시점
- **현재 가정**: MVP는 ducting_enabled=False (직선 전파)

### Q-AT3. Atmosphere 시간 가변
- **출처**: 15 § 15.10
- **결정 시점**: 동적 날씨 시나리오 시점
- **현재 가정**: MVP는 Scenario 단위 정적

### Q-AT4. Wind을 motion_kind별로 다르게?
- **출처**: 15 § 15.10
- **결정 시점**: 정밀 동역학 시점 (지상 vehicle 도입 시)
- **현재 가정**: MVP는 wind 무시 또는 균일 적용

### Q-BL6. Extended target에 Frequency-dependent RCS 추가 시점
- **출처**: 16 § 16.6
- **결정 시점**: 다중 주파수 시뮬 도입 시
- **현재 가정**: MVP는 frequency-independent

### Q-BL7. UKF의 sigma point 파라미터 (alpha/beta/kappa) UI 노출
- **출처**: 16 § 16.6
- **결정 시점**: 사용자가 정밀 튜닝 요구 시
- **현재 가정**: MVP는 표준값 (alpha=1e-3, beta=2.0, kappa=0)

### Q-BL8. GNN의 gating threshold 자동 vs 수동
- **출처**: 16 § 16.6
- **결정 시점**: 다중 표적 시나리오 다양화 시
- **현재 가정**: MVP는 3.0σ 고정

### Q-BL9. Two-ray multipath의 reflection coefficient 정밀도
- **출처**: 16 § 16.6
- **결정 시점**: 정밀 시나리오 (특정 sea state) 시점
- **현재 가정**: MVP는 단순화 (-0.95 고정), 정밀은 Fresnel + roughness

### Q-BL10. Refraction의 ducting 트리거 시점
- **출처**: 16 § 16.6
- **결정 시점**: 해상 ducting 시나리오 본격 도입 시
- **현재 가정**: MVP는 4/3 earth 직선

### Q-OP1. DLC marketplace 별도 사이트 분리 시점
- **출처**: 17 § 17.12
- **결정 시점**: awesome-list가 트래픽·발견성 한계 도달 시
- **현재 가정**: MVP는 Core repo 안 awesome-trsim-packages.md

### Q-OP2. DLC 보안·sandbox 정책
- **출처**: 17 § 17.12
- **결정 시점**: 악장 사례 발생 또는 MVP+α 안정 후
- **현재 가정**: MVP는 sandbox 없음, "신뢰 출처에서만 install" 권장

### Q-OP3. SDK 안정성 정책 (semver, deprecation, 호환성 보장 기간)
- **출처**: 17 § 17.12
- **결정 시점**: SDK 정식 (Phase 7) 시점
- **현재 가정**: MVP+α에서 결정

### Q-OP4. 외부 기여자 commit 권한 부여 기준
- **출처**: 17 § 17.12
- **결정 시점**: Core team Phase 2 진입 시
- **현재 가정**: GOVERNANCE.md § Phase 2 기준 (PR 10+, 6개월+ 활동)

### Q-OP5. 방산 DLC 배포 가이드 (수출 통제·면책)
- **출처**: 17 § 17.12, 17 § 17.10
- **결정 시점**: 방산 관련 DLC 등장 시
- **현재 가정**: README "Export Control Notice" 정도, 사용자 책임 명시

### Q-HIL1. 첫 sample 어댑터는 TCP/JSON 외 추가 필요?
- **출처**: 18 § 18.7
- **결정 시점**: Phase 8.1 후
- **현재 가정**: TCP/JSON 만, 사용자 어댑터 작성 가이드 충실

### Q-HIL2. C6678 PCIe 어댑터 sample 우선순위
- **출처**: 18 § 18.10
- **결정 시점**: Phase 8.3 또는 사용자 요청 시
- **현재 가정**: C6678 어댑터는 사용자 펌웨어 환경에 맞게 별도 작성

### Q-HIL3. AWG vendor 우선순위 (Spectrum / Keysight / Rohde&Schwarz)
- **출처**: 18 § 18.6 TX-B
- **결정 시점**: Phase 8.3
- **현재 가정**: 미결정 — Phase 8.3 시점에 보유 장비 따라

### Q-HIL4. DUT-Bias 임계값 자동 알람
- **출처**: 18 § 18.9
- **결정 시점**: Phase 8.1 후 운영 경험 후
- **현재 가정**: MVP는 시각화만, 임계값 알람 후속

### Q-HIL5. 다중 DUT 동시 비교 (DUT A vs DUT B vs SIL)
- **출처**: 18 § 18.12 MVP+α 외
- **결정 시점**: 산업 사용자 요청 시
- **현재 가정**: 단일 DUT 만, 다중은 미래

### Q-HIL6. 펌웨어 자동 deploy / DUT discovery
- **출처**: 18 § 18.12 MVP+α 외
- **결정 시점**: 산업 deployment 시점
- **현재 가정**: 수동 셋업 (사용자가 펌웨어 load 후 IP 알려줌)

### Q-HIL7. real_time sync mode 의 sample loss 정책
- **출처**: 18 § 18.8 모드 2
- **결정 시점**: Phase 8.3
- **현재 가정**: warning + skip, sample loss 통계 기록

### Q-RT1. Frame 정의 — 자동 추론 vs 사용자 명시
- **출처**: 18 § 18.16.2
- **결정 시점**: Phase 3 SIL Reference Timing 구현 시
- **현재 가정**: 둘 다 지원 — Scenario `frame_unit` 명시 우선, 없으면 자동 추론 (테스트 코드 최종 결론(AZ/EL 출력) 시점)

### Q-RT2. Lock-step Handshake protocol (frame ID 매칭)
- **출처**: 18 § 18.16.4
- **결정 시점**: Phase 8.1 HIL 구현 시
- **현재 가정**: frame_id (uint64) + ack_required + timeout 표준. DUT 측 구현 가이드 별도

### Q-RT3. 빠른 PC 의 sleep 정밀도 (OS jitter)
- **출처**: 18 § 18.16.1
- **결정 시점**: Phase 3 측정 후
- **현재 가정**: time.sleep() 충분 (ms 단위). 더 정밀 필요 시 spin-wait 옵션

### Q-RT4. Stage 단위 측정 overhead
- **출처**: 18 § 18.16.3, 18 § 18.17
- **결정 시점**: Phase 3 PerformanceClock 구현 시
- **현재 가정**: 측정 모드 toggle — 평소 off, profiling 시 on. perf_counter_ns ~200ns/call

### Q-RT5. DUT-Bias 와 Reference Timing 결합
- **출처**: 18 § 18.9 + 18 § 18.16
- **결정 시점**: Phase 8.1 후 운영 경험
- **현재 가정**: 별개 metric — DUT-Bias 는 "결과 정확도", Reference Timing 은 "처리 시간". 같이 표시

### Q-RT6. Profile 미명시 stage 의 default 동작
- **출처**: 18 § 18.16.3
- **결정 시점**: Phase 3 구현 시
- **현재 가정**: scale_factor=1.0 (보정 안 함, wall_clock 그대로)

### Q-RT7. Frame Profiler warmup 프레임 수
- **출처**: 18 § 18.17
- **결정 시점**: Phase 3 후 측정 안정성 확인
- **현재 가정**: 첫 10 프레임 warmup discard, 실제 측정은 11번째부터 (JIT/cache 효과 제외)

### Q-RT8. Frame Profiler 결과의 재현성 (PC 부하 변동)
- **출처**: 18 § 18.17
- **결정 시점**: Phase 3 후 운영 경험
- **현재 가정**: 동일 PC·동일 부하에서 percentile 일관성 명시. 결과에 measurement context (CPU·load) 기록

### Q-PL1. Physics Lab 의 3D 시각화 라이브러리 일관성
- **출처**: 19 § 19.4
- **결정 시점**: Phase 9.1
- **현재 가정**: PyVista (3D) + pyqtgraph (2D), 기존 일관

### Q-PL2. 측정 데이터 형식 표준 schema
- **출처**: 19 § 19.8.2
- **결정 시점**: Phase 9.1 후 사용자 피드백
- **현재 가정**: CSV / HDF5 / .npz 모두 지원, 표준 schema 권장 (정식 정의 미루기)

### Q-PL3. 분석 공식 reference 의 출처 우선순위
- **출처**: 19 § 19.5.2, 19.9
- **결정 시점**: Phase 2 통합 시
- **현재 가정**: 표준 책 (Skolnik / Mahafza) 우선, 논문은 보조

### Q-PL4. 사용자 물리 plugin 검증 임계값
- **출처**: 19 § 19.7.3
- **결정 시점**: Phase 9.1 운영 후
- **현재 가정**: 분석 공식과 RMSE < 5% 권장 (모델별 다름)

### Q-PL5. 17종 검증 시나리오의 Physics Lab plot 형태
- **출처**: 19 § 19.9.2
- **결정 시점**: Phase 9.1
- **현재 가정**: Analytic + Implementation overlay + RMSE/Max diff 표시

### Q-PL6. NN 대체 학습 (형태 2) 의 Phase 6 결합 시점
- **출처**: 19 § 19.8.1
- **결정 시점**: Phase 6 NN 통합 완료 후
- **현재 가정**: Phase 9.3

### Q-PL7. Symbolic regression 도구 선택
- **출처**: 19 § 19.8.1 Phase 9.2
- **결정 시점**: Phase 9.2 시작 시
- **현재 가정**: PySR 우선 (Apache 2.0 호환), 대안 검토

### Q-PL8. 학습 영역 vs 외삽 영역 표시 방법
- **출처**: 19 § 19.8.1 Phase 9.3
- **결정 시점**: Phase 9.3
- **현재 가정**: 3D 시각화에 색·투명도로 표시

### Q-PL9. 논문 PDF 라이브러리의 검색·tag
- **출처**: 19 § 19.8.1 (참조 자료만)
- **결정 시점**: Phase 9.2 운영 후
- **현재 가정**: 단순 file metadata + 사용자 tag (자동 분석 X)

### Q-PL10. Code Pane 의 syntax highlighting / debugger 통합 정도
- **출처**: 19 § 19.4.2
- **결정 시점**: Phase 9.1
- **현재 가정**: Pygments syntax highlight, debugger 미통합 (line highlight 만 시간 진행 따라)

---

## 4. 장기 (🟢)

### Q-D11~D18. 배포·라이선스·기타·미래 (이전 누적)
- 배포 방식 (Source / PyInstaller / Docker)
- 최종 라이선스
- 크래시 리포팅
- 테마 추가
- 커스터마이저블 툴바
- pint 도입 (물리 단위)
- TF 버전 고정
- 분산 학습 지원
- ONNX export
- Bundle 서명·검증
- Cloud Resource Registry
- GROUND_VEHICLE 도로 자원 (RoadNetwork)
- Tide model
- EGM2008 정밀 geoid
- MIMO TX / DBF
- Antenna Aperture taper

---

## 5. 답이 결정된 이전 TBD

이전 세션 결정 (생략):
- 두 운용 모드 (DSP/NN), 물리 4종+Deferred 6, Run 생애주기, Single Command Path, 두 레이어 시간 제어, ...

오늘 (v0.16~v0.27)에 결정된 것:
- ✅ 휠 줌 + Unreal+Maya 3D 조작 (v0.17)
- ✅ Radar Platform Maritime + Fixed Ground (v0.18)
- ✅ Installation 필수 게이트 (v0.18)
- ✅ 두 Workspace 분리 (v0.19)
- ✅ 자원 참조 구조 + Bundle (v0.20)
- ✅ WGS84 + ENU + Vertical Reference (v0.21)
- ✅ MotionKind 5 카테고리 + Wave 응답 분리 (v0.21)
- ✅ Building anchor 4 mode (v0.21)
- ✅ MVP에서 표적 궤적 편집 GUI 제외 (v0.21)
- ✅ 자체 규격 지형 (terrain.npz + land_mask) (v0.22)
- ✅ Land/Sea 구분 4방식 사용자 선택 (v0.22)
- ✅ 지형 편집 도구 MVP 경량 (v0.22)
- ✅ Antenna Model 파라볼릭 + 평면 어레이 (v0.25)
- ✅ Monopulse 4채널 (v0.25)
- ✅ Radar Editor 통합 폼 (v0.25)
- ✅ Editor Workspace Activity + 탭 + 사이드바 (v0.26)
- ✅ Scenario Composer (Editor 메인) (v0.26)
- ✅ Map Editor 경량 + DEM Wizard 통합 (v0.26)
- ✅ **사실적 동역학 모델 — Level 1 MVP** (v0.27)
- ✅ **MotionKind 5 → 7** (AIRBORNE 폐기, AIRCRAFT/POWERED_FLIGHT/BALLISTIC 신설) (v0.27)
- ✅ **trajectory = reference, 실제 = 동역학 적분** (v0.27)
- ✅ **타입별 자유도** (AIRCRAFT/POWERED_FLIGHT 6DOF target, BALLISTIC 3DOF) (v0.27)
- ✅ **표적 Preset 라이브러리** (fighter_jet/airliner/missile_cruise/ballistic/drone/artillery) (v0.27)
- ✅ **크로스 플랫폼 (Win/Linux/Mac)** (v0.27 결정 — Q-P1 closed)
- ✅ **시각화 라이브러리: pyqtgraph + PyVista 하이브리드** (v0.28 — Q-P2 closed)
- ✅ **대기 모델 — 시각·동역학·전파 세 측면 모두** (v0.28 — Q-A1 closed, plan/15_atmosphere_model.md 신규)
- ✅ **Simulation Domain — Map + Outside Environment** (v0.29 — Q-MS1/2/3 closed, 11 § 11.11)
- ✅ **Map Editor Flatten Area** (v0.33 — 정박지·활주로·부지 평탄화, 12 § 12.11.1)
- ✅ **Two-ray multipath (sea bounce)** (v0.34 — Q-BL1 closed, 08 § 8.5b.1)
- ✅ **Multi-scatterer 표적 + Glint 자동 발생** (v0.34 — Q-BL2 closed, 14 § 14.10) ⭐ 차별점 강화
- ✅ **EKF + UKF 선택 가능** (v0.34 — Q-BL3 closed, Stone Soup 호환)
- ✅ **GNN 다중 표적 데이터 연관** (v0.34 — Q-BL4 closed, Hungarian)
- ✅ **Atmospheric refraction (4/3 earth)** (v0.34 — Q-BL5 closed, 15 § 15.5.4)
- ✅ **OS-CFAR 추가** (v0.34 — 클러터 환경 표준, 08 § 8.5c)
- ✅ **라이선스 — Apache 2.0** (v0.35 — Q1-rev closed, 17 § 17.2.1)
- ✅ **공개 모델 — 적극 공공** (v0.35 — Q2 closed, GitHub public + Issue·PR + DCO)
- ✅ **확장 깊이 — 핵심 계층만** (v0.35 — Q3 closed, 알고리즘 + 자원 + 시각화 패널)
- ✅ **DLC 형태 — `.trsim-pkg` 패키지** (v0.35 — Q4 closed, VS Code Extension 모델)
- ✅ **궁극적 목표 — DLC 에코시스템** (v0.35 — Q5 closed, Blender 역할)
- ✅ **거버넌스 — Core team 3~5명** (v0.35 — Q6 closed, 초기 BDFL 임시)
- ✅ **Marketplace — awesome-list 가벼운 시작** (v0.35 — Q7 closed)
- ✅ **SDK — Core에 포함 (`trsim.sdk`)** (v0.35 — Q8 closed)
- ✅ **DLC 보안 — MVP 미정, MVP+α에서 결정** (v0.35 — Q9 closed)

---

## 6. 현재 상태 요약

- 블로커: **0개**
- 곧 필요: **5개** (Q-EW1~5)
- 중기: **57개** (안테나·동역학·좌표·NN·편집 UI·자원·atmosphere·베이스라인 정밀화 + 오픈 플랫폼 + Q-N7 + Q-D6/D7 + Q-AT4 + Q-HIL1~7 + Q-RT1~8 + **Q-PL1~10 v0.40**)
- 장기: **8개** (Q-D11~D18 — 배포·라이선스·기타·미래)
- 결정됨 (v0.16~v0.40): **72개** (HIL-1~7 + RT D1~D4 + Q1~Q6 + Profiler Q1~Q5 + **PL-1~15** 포함)
- **Open 합계: 70개 / Closed: 72개**

**v0.40 시점에서 큰 설계 결정 + 베이스라인 보강 + 정체성 전환 + HIL 통합 + Reference Timing + Physics Lab 모두 완료.** 남은 미결은 구현 세부, 사용 피드백,
또는 명확한 트리거 시점이 있는 것들. **동역학·대기·시각화·시뮬·RF/물리 베이스라인 + 오픈소스/DLC 에코 + 거버넌스 + HIL 통합 + Reference Timing + Physics Lab 까지**
모두 확보. MATLAB·Stone Soup 비교 demo 신뢰 + Apache 2.0 + .trsim-pkg 플랫폼 + DUT 펌웨어 검증 + Vivado 패턴 timing 보정 + 인터랙티브 물리 실험실 기반 마련.

**v0.36~v0.37**: 정합성 검토 + Phase 0 인프라 + sim_3d 분리. 새 결정 없음 (구조 정합·옛 표현 정정만).
**v0.38**: HIL 통합 신설. HIL-1~7 모두 closed, Q-HIL1~7 신규 등록.
**v0.39**: Reference Timing Mode + Frame Profiler 추가. D1~D4 + Q1~Q6 + Profiler Q1~Q5 모두 closed, Q-RT1~8 신규 등록. 차별점 4+1 유지 (당연한 기능).
**v0.40**: Physics Lab 추가. PL-1~15 모두 closed, Q-PL1~10 신규 등록. **차별점 4+1 → 5+1**. plan 19 신설. Plugin Protocol 10 → 11 (PhysicsModelProtocol). Physics Layer 분리. 06 § 6.7 결정 변경. 17종 → Physics Lab 통합.
