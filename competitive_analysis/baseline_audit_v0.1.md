# TRsim 베이스라인 점검 — RF·물리·동역학·추적·검증

**작성**: 2026-04-28 (v0.1 분석 보고서, 보존)
**목적**: 경쟁자(MATLAB·Stone Soup·RadarSimPy·GPARM 등)가 가진 베이스라인을 우리와 정밀 비교, 부족한 점 식별

> ⚠️ **후속**: 본 분석에서 권장된 Q-BL1~5 (Two-ray multipath / Multi-scatterer + Glint /
> UKF / GNN / Refraction) 는 **모두 v0.34에서 closed** 됨. 정식 통합 위치는
> `plan/16_baseline_audit.md` (v0.34 신규). 본 문서는 **분석 시점의 근거 자료**로 보존.

---

## 0. 평가 방법

각 영역에서 경쟁자가 가진 기능을 4 분류로 표시:

- **🟢 MVP**: 우리가 v0.33까지 명시적으로 가진 것
- **🟡 MVP+α**: 우리가 차후 계획으로만 명시
- **🔴 부재**: 우리 계획서에 없음 — **점검 대상**
- **⚪ 의도적 제외**: 우리 niche 밖 (예: SAR, 자동차 mmWave 칩 인터페이스)

각 항목에 **권장 조치**: MVP 추가 / MVP+α 명시 / 의도적 제외 명시 / 추후 결정.

---

## 1. RF / 신호처리

### 1.1 안테나 / 어레이

| 기능 | MATLAB Phased Array | Stone Soup | RadarSimPy | GPARM | TRsim 현재 | 권장 |
|---|---|---|---|---|---|---|
| Parabolic dish (sinc²) | ✅ | ❌ | △ | ✅ | 🟢 v0.25 | OK |
| Planar array (array factor) | ✅ | ❌ | ✅ | ✅ | 🟢 v0.25 | OK |
| **AESA / PESA (전자 조향)** | ✅ | ❌ | ✅ | ✅ | 🔴 | **MVP+α 명시** (운영 자체는 추적 빔 1개라 MVP 영향 작음) |
| **Subarray 구조** | ✅ | ❌ | △ | ✅ | 🔴 | MVP+α 명시 |
| **Mutual coupling 모델** | ✅ embedded pattern | ❌ | ❌ | ✅ | 🔴 | MVP+α 명시 (정밀 빔 패턴이 필요할 때) |
| **Polarization (수직/수평/원형)** | ✅ scattering matrix | ❌ | △ | ✅ | 🔴 | **MVP+α 명시** — 추후 성능 검증에 필요 |
| **Element pattern (microstrip/horn/dipole)** | ✅ Antenna Toolbox 통합 | ❌ | △ | ✅ | 🟡 v0.25 sinc²만 | Custom pattern import (numpy 배열) MVP 추가 검토 |
| **Tapering (Taylor/Chebyshev/Hamming)** | ✅ | ❌ | ✅ | ✅ | 🔴 | MVP에 uniform + Hamming 정도 추가 |
| **Sparse / thinned array** | ✅ | ❌ | △ | △ | 🔴 | 의도적 제외 (단일 빔 추적엔 큰 영향 X) |

### 1.2 웨이브폼 / TX

| 기능 | MATLAB | Stone Soup | RadarSimPy | TRsim 현재 | 권장 |
|---|---|---|---|---|---|
| FMCW (Triangle/Sawtooth) | ✅ 다양 | ❌ | ✅ | 🟢 v0.16 Triangle | OK |
| **Pulse waveform (정형 펄스)** | ✅ | ❌ | ✅ | 🔴 | **MVP+α 명시** — 추적 레이더 일부는 펄스 |
| **Chirp 압축 (Pulse Compression)** | ✅ stretch processing, matched filter | ❌ | ✅ | 🔴 | **MVP 추가 검토** — FMCW에서도 일부 변형 사용 |
| **PRF staggering** | ✅ | ❌ | △ | 🔴 | 의도적 제외 (추적 레이더 보통 단일 PRF) |
| **PRF agility / Frequency agility** | ✅ | ❌ | ❌ | 🔴 | MVP+α 명시 (재머 회피용) |
| **MFSK** | ✅ | ❌ | ❌ | 🔴 | 의도적 제외 |

### 1.3 RX / DSP

| 기능 | MATLAB | Stone Soup | RadarSimPy | TRsim 현재 | 권장 |
|---|---|---|---|---|---|
| Range/Doppler FFT | ✅ | ❌ | ✅ | 🟢 | OK |
| Matched filtering | ✅ | ❌ | ✅ | 🟡 (FMCW만) | MVP에서 명시 |
| **CFAR (CA/OS/GO/SO)** | ✅ 다양 | ❌ | ✅ | 🟡 (CA만 MVP) | **MVP에 OS-CFAR도 추가 검토** — 클러터 환경에서 표준 |
| **Pulse canceller (MTI)** | ✅ | ❌ | ❌ | 🔴 | MVP+α 명시 (이동 표적 식별) |
| **STAP (SMI/DPCA/ADPCA)** | ✅ Phased Array Toolbox | ❌ | ❌ | 🔴 | 의도적 제외 (공중·우주 레이더 위주, 우리 niche 밖) |
| **DOA estimation (Beamscan/MVDR/MUSIC/ESPRIT/Root-MUSIC)** | ✅ 다 있음 | ❌ | ✅ | 🔴 | **MVP+α 명시** — DOA는 추적 niche 안. MUSIC 정도 검토 |
| **Monopulse** (Σ/Δ 4채널) | ✅ | ❌ | △ | 🟢 v0.25 | OK |
| **DBF (Digital Beamforming)** | ✅ MVDR adaptive | ❌ | ✅ | 🔴 | **MVP+α 명시** — MUSIC과 같이 |
| **Adaptive beamforming (Jammer suppression)** | ✅ | ❌ | △ | 🔴 | 의도적 제외 (대형 레이더 영역) |
| **Hybrid / Digital beamforming (massive MIMO)** | ✅ | ❌ | ✅ | 🔴 | 의도적 제외 (5G/통신 분야) |

### 1.4 RF / 회로

| 기능 | MATLAB | RadarSimPy | TRsim 현재 | 권장 |
|---|---|---|---|---|
| TX/RX 증폭기 모델 (NF, gain) | ✅ | ✅ | 🟡 (단순) | MVP에 NF·gain 명시적으로 |
| **Phase noise** | ✅ | ✅ | 🔴 | **MVP+α 명시** — 추적 정밀도에 영향 |
| ADC 양자화 (effective bits) | ✅ | ✅ | 🔴 | MVP+α 명시 |
| RF compression / saturation | ✅ | △ | 🔴 | 의도적 제외 (고급 RF 영역) |
| **Quadrature imbalance (I/Q mismatch)** | ✅ | △ | 🔴 | MVP+α 명시 |

---

## 2. 환경 / 전파 / 클러터

### 2.1 전파 (Propagation)

| 기능 | MATLAB | Stone Soup | RadarSimPy | GPARM | TRsim 현재 | 권장 |
|---|---|---|---|---|---|---|
| Free-space path loss (R⁻⁴) | ✅ | △ | ✅ | ✅ | 🟢 | OK |
| **Atmospheric attenuation (gases — O₂·H₂O)** | ✅ ITU-R P.676 | ❌ | △ | ✅ | 🔴 | **MVP+α 명시** — X-band 영향 작지만 mmWave 영향 큼 |
| Rain attenuation | ✅ ITU-R P.838 | ❌ | △ | ✅ | 🟢 v0.28 | OK |
| **Fog/cloud attenuation** | ✅ ITU-R P.840 | ❌ | ❌ | △ | 🔴 | MVP+α 명시 |
| **Two-ray multipath** | ✅ | ❌ | ✅ | ✅ | 🔴 | **MVP 추가 검토** — 해상 시나리오의 핵심 (sea bounce) |
| **Multipath fading (Rayleigh/Rician/Nakagami)** | ✅ | ❌ | △ | ✅ | 🔴 | **MVP+α 명시** — 추적 정확도에 큰 영향 |
| **Atmospheric refraction (4/3 earth radius)** | ✅ | ❌ | △ | ✅ | 🔴 | **MVP 추가 검토** — 장거리 정확도 |
| **Ducting (anomalous propagation)** | ✅ | ❌ | ❌ | ✅ | 🟡 v0.28 MVP+α | OK 명시됨 |
| **Diffraction (knife-edge)** | △ | ❌ | ❌ | ✅ | 🔴 | MVP+α 명시 (산악 차폐) |
| **RIS (Reconfigurable Intelligent Surface)** | ✅ | ❌ | ❌ | ❌ | ⚪ | 의도적 제외 (5G/SATCOM 신기술) |
| **Forward scatter from sea** | ✅ | ❌ | △ | ✅ | 🔴 | **MVP 추가 검토** — 해상 핵심 |

### 2.2 클러터 (Clutter)

| 기능 | MATLAB | Stone Soup | RadarSimPy | GPARM | TRsim 현재 | 권장 |
|---|---|---|---|---|---|---|
| **Sea clutter — Rayleigh** | ✅ | ❌ | △ | ✅ | 🔴 | **MVP 추가** — 가장 단순한 모델 |
| **Sea clutter — K-distribution** | ✅ | ❌ | △ | ✅ | 🔴 | **MVP+α** — 고분해능 표준 |
| **Sea clutter — Weibull** | ✅ | ❌ | △ | ✅ | 🔴 | MVP+α |
| **Land clutter — gamma value** | ✅ | ❌ | △ | ✅ | 🔴 | **MVP+α 명시** — STAP 예제처럼 표준 |
| **Land clutter — Weibull / log-normal** | ✅ | ❌ | △ | ✅ | 🔴 | MVP+α |
| **JONSWAP/Hwang ocean spectrum (sea profile)** | △ | ❌ | ❌ | △ | 🔴 | 의도적 제외 — 너무 정밀, 우리는 statistical clutter로 충분 |
| **Compound Gaussian (texture + speckle)** | ✅ | ❌ | △ | ✅ | 🔴 | MVP+α |
| **Volume clutter (rain backscatter)** | ✅ | ❌ | △ | ✅ | 🔴 | MVP+α 명시 |
| **Discrete clutter (point reflectors)** | ✅ | ❌ | ✅ | ✅ | 🟡 v0.21 buildings | OK |

### 2.3 간섭 / 재밍

| 기능 | MATLAB | TRsim 현재 | 권장 |
|---|---|---|---|
| **Barrage jammer** (광대역) | ✅ `barrageJammer` | 🔴 | **MVP+α 명시** — 추적 안정성 검증에 가치 |
| **Spot jammer** (좁은 대역) | ✅ | 🔴 | MVP+α |
| **Deception jammer** (가짜 표적) | ✅ | 🔴 | MVP+α 명시 |
| **Multiple radar interference** (FMCW car-to-car) | ✅ | 🔴 | 의도적 제외 (자동차 영역) |
| **Jammer nullification (adaptive)** | ✅ | 🔴 | 의도적 제외 (대형 phased array) |

---

## 3. 표적 / 동역학

### 3.1 RCS / 표적 모델

| 기능 | MATLAB | Stone Soup | RadarSimPy | GPARM | TRsim 현재 | 권장 |
|---|---|---|---|---|---|---|
| Constant RCS (Swerling 0/V) | ✅ | △ | ✅ | ✅ | 🟢 v0.16 | OK |
| **Swerling 1~4 fluctuation** | ✅ `phased.BackscatterRadarTarget` | △ (단순) | ✅ | ✅ | 🔴 | **MVP 추가 필수** — 통계적 추적 검증의 표준 |
| **Aspect-dependent RCS** (azimuth/elevation별 RCS 패턴) | ✅ | ❌ | ✅ | ✅ | 🔴 | **MVP 추가 검토** — 함정·항공기 사실성에 직결 |
| **Frequency-dependent RCS** | ✅ | ❌ | ✅ | △ | 🔴 | MVP+α 명시 |
| **Polarimetric RCS (scattering matrix)** | ✅ | ❌ | △ | ✅ | 🔴 | MVP+α 명시 |
| **Multi-scatterer model (extended target)** | ✅ | ❌ | ✅ | ✅ | 🔴 | **MVP+α 명시** — 항공기·대형 함정에 표준. 단순 점 표적과 큰 차이 |
| **Micro-Doppler (회전 부품 — 프로펠러/제트엔진/헬리콥터 로터)** | ✅ | ❌ | ✅ | △ | 🔴 | **MVP+α 명시** — 표적 분류·추적 정확도에 큰 영향 |
| **Glint (각도 noise from extended targets)** | ✅ | △ | △ | ✅ | 🔴 | **MVP 추가 검토** — 단일 표적 추적 안정성에 직접 영향 |
| **Range glint** (range jitter) | ✅ | △ | △ | ✅ | 🔴 | MVP+α 명시 |

### 3.2 동역학

| 기능 | MATLAB | Stone Soup | RadarSimPy | TRsim 현재 | 권장 |
|---|---|---|---|---|---|
| Constant velocity / acceleration | ✅ | ✅ | △ | 🟢 v0.27 | OK |
| **6DOF rigid body (full)** | ✅ Aerospace Toolbox | ❌ | △ | 🟡 (3DOF + derived attitude) MVP, 6DOF MVP+α | OK 명시 |
| Aircraft autopilot (climb rate, bank) | ✅ Aerospace | ❌ | ❌ | 🟢 v0.27 PD control | OK |
| Ballistic (자유낙하) | ✅ | △ | ❌ | 🟢 v0.27 | OK |
| **Coordinated turn model (CTM)** | ✅ | ✅ | ❌ | 🟡 PD로 일부 구현 | MVP에 명시 (Stone Soup 호환용) |
| **Singer model** (random acceleration) | ✅ | ✅ | ❌ | 🔴 | MVP+α 명시 — 추적 시뮬 표준 |
| **Constant turn rate / variable speed** | ✅ | ✅ | ❌ | 🟡 | MVP에 명시 |
| **Ship dynamics (sea state response — pitch/roll/heave)** | △ | ❌ | ❌ | 🟢 v0.21 WaveResponseModel | OK — 실제 우리만 정밀 |
| Wind drift | ✅ | ❌ | ❌ | 🟡 MVP+α | OK 명시 |

---

## 4. 추적 / 데이터 연관

### 4.1 단일 표적 (TRsim 핵심)

| 기능 | MATLAB | Stone Soup | RadarSimPy | TRsim 현재 | 권장 |
|---|---|---|---|---|---|
| Kalman Filter (KF) | ✅ | ✅ | ❌ | 🟡 | MVP에 명시 |
| **Extended KF (EKF)** | ✅ | ✅ | ❌ | 🟢 v0.10 | OK |
| **Unscented KF (UKF)** | ✅ | ✅ | ❌ | 🔴 | **MVP 추가 검토** — Stone Soup 표준, NN 비교 베이스라인에도 유용 |
| **α-β-γ filter** | ✅ | ❌ | ❌ | 🔴 | 의도적 제외 (구식) |
| **Particle filter** | ✅ | ✅ NUTS proposal | ❌ | 🔴 | MVP+α 명시 |

### 4.2 다중 표적 (TRsim 우선순위 낮음)

| 기능 | MATLAB Sensor Fusion and Tracking | Stone Soup | TRsim 현재 | 권장 |
|---|---|---|---|---|
| **GNN (Global Nearest Neighbor)** | ✅ | ✅ | 🔴 | MVP에 단순 NN만 추가 — 다중 표적 환경 시뮬은 필수 |
| **JPDA** | ✅ | ✅ | 🔴 | MVP+α 명시 |
| **MHT (Multiple Hypothesis Tracking)** | ✅ | ✅ MFA | 🔴 | MVP+α 명시 |
| **PHD / GM-PHD** (random finite set) | ✅ | ✅ | 🔴 | 의도적 제외 (다중 표적 우선순위 낮음) |
| **LMB / GLMB** | △ | △ | 🔴 | 의도적 제외 |
| **IMM (Interacting Multiple Models)** | ✅ | ✅ | 🔴 | **MVP+α 명시** — 기동 표적 표준 |
| Track initiator/deleter logic | ✅ | ✅ | 🟡 단순 | MVP에 명시 |

### 4.3 추적 메트릭

| 기능 | MATLAB | Stone Soup | TRsim 현재 | 권장 |
|---|---|---|---|---|
| **OSPA (Optimal SubPattern Assignment)** | △ | ✅ | 🔴 | MVP+α 명시 |
| **SIAP (Single Integrated Air Picture)** | △ | ✅ | 🔴 | MVP+α 명시 |
| **GOSPA** | ❌ | ✅ | 🔴 | MVP+α |
| Position RMSE / NEES | ✅ | ✅ | 🟡 RMSE | MVP에 명시 |
| **Single-target stability metric (lock-on hold time, recovery)** | ❌ | ❌ | 🟢 (우리 차별점) | OK — TRsim 신설 |

---

## 5. 검증 / 시나리오

| 기능 | MATLAB Radar Designer | Stone Soup | TRsim 현재 | 권장 |
|---|---|---|---|---|
| **Link budget analysis** | ✅ | ❌ | 🟡 (단순) | MVP에 명시 — 시나리오 만들 때 표준 |
| **Detection range / Pd-Pfa curves (ROC)** | ✅ | △ | 🔴 | MVP+α 명시 |
| **Range-angle-height (Blake) charts** | ✅ | ❌ | 🔴 | 의도적 제외 |
| **Coverage analysis (3D terrain)** | ✅ | ❌ | 🟡 v0.18 Installation Preview | MVP+α 명시 (확장) |
| **Search-and-track timeline** | ✅ Riverside ResourceSIM | ❌ | 🔴 | 의도적 제외 (멀티펑션 영역) |
| Synthetic dataset 자동 생성 | ✅ | ✅ | 🟢 v0.30 | OK |
| Golden truth comparison | ✅ | ✅ | 🟡 명시됨 | OK |

---

## 6. 시각화

| 기능 | MATLAB | Stone Soup | RadarSimPy | TRsim 현재 | 권장 |
|---|---|---|---|---|---|
| Range-Doppler 2D | ✅ | ❌ | ✅ | 🟢 v0.13 | OK |
| 3D Scene (terrain + targets) | ✅ Aerospace | ❌ | △ | 🟢 v0.28 PyVista | OK — 우리 강점 |
| Beam pattern (polar) | ✅ | ❌ | ✅ | 🟢 v0.25 | OK |
| Multi-track timeline | ✅ | ✅ matplotlib | ❌ | 🟡 | MVP에 명시 |
| Live console / log | △ | △ | ❌ | 🟢 | OK |

---

## 7. 종합 — 부족한 점 우선순위

### 🔴 베이스라인 부족 — MVP에 추가 필수 (5개)

이게 없으면 MATLAB 결과 비교 demo에서 망신:

1. **Swerling 1~4 RCS fluctuation** — 통계적 추적 검증의 표준. 추가 비용 작음 (1~2일)
2. **OS-CFAR** — 클러터 환경에서 CA-CFAR 단독은 부적절. CA가 MVP면 OS도 MVP에 (1일)
3. **Two-ray multipath** — 해상 시나리오의 핵심. sea bounce 없으면 추적 안정성 검증 의미 없음 (3~5일)
4. **GNN (단순 다중 표적 데이터 연관)** — 다중 표적 환경 시뮬레이션의 최소 요건. 단일 표적만 잡는 시뮬도 다중 표적이 떠다녀야 의미 (2~3일)
5. **Atmospheric refraction (4/3 earth radius)** — 장거리 추적의 기본. 단순 모델 (1일)

### 🔴 베이스라인 부족 — MVP+α 명시 권장 (10개)

명시만 해도 "우리도 알고 있고 계획에 있다"는 것으로 신뢰도 회복:

6. **K-distribution sea clutter** — 고분해능 해상 표준
7. **Land clutter (gamma value)** — STAP 예제 표준
8. **Aspect-dependent RCS pattern** — 함정·항공기 사실성
9. **Multi-scatterer extended target** — 대형 표적 모델
10. **Micro-Doppler** — 회전 부품 (프로펠러·로터). 표적 분류 핵심
11. **Glint (angle noise)** — 단일 표적 추적 안정성 직접 영향
12. **UKF + IMM** — Stone Soup 표준 호환
13. **DOA estimation (MUSIC)** — DOA가 추적 niche 안
14. **Phase noise + ADC quantization** — RF 비이상성
15. **Barrage/spot jammer** — 추적 안정성 검증 시나리오

### ⚪ 의도적 제외 명시 권장 (5개)

"우리 범위가 아니다"를 명확히:

16. STAP — 공중·우주 레이더 영역
17. Massive MIMO / Hybrid beamforming — 5G/통신
18. SAR / ISAR — 영상 영역
19. PHD / GM-PHD / LMB — 다중 표적 RFS 영역
20. RIS — 신기술 통신 영역

---

## 8. Glint — 우리가 놓치고 있는 결정적 요소

특히 **glint**는 추적 레이더 단일 표적 안정성과 직접 관련. 짧게 강조:

> 항공기·함정 같은 extended target은 표적 위 여러 reflector의 위상 합성으로 받음 신호 형성. 표적이 회전·이동하면 reflector 간 phase가 변하고 **수신 빔의 도래각이 표적 중심에서 흔들림** (glint, mm~m 수준). 추적 레이더의 monopulse error가 이 흔들림을 실제 표적 이동으로 오인 → 추적 안정성 저하.
> 
> 현재 v0.27 동역학·v0.25 monopulse 다 만들었지만 **표적이 점**이라 glint 없음. 추적 안정성 검증의 핵심 시나리오인데 빠짐.

→ **MVP+α에 multi-scatterer + glint 명시**. 또는 multi-scatterer 1개라도 MVP에 추가 검토.

---

## 9. 권장 다음 작업

### A. 계획서 갱신 (작은 작업)

1. **08 radar_waveforms.md** 에 § 8.x "베이스라인 점검 결과" 신설
   - MVP 추가 5개 (Swerling/OS-CFAR/Two-ray/GNN/Refraction)
   - MVP+α 명시 10개
   - 의도적 제외 5개

2. **15 atmosphere_model.md** § 15.5 보강
   - Atmospheric refraction (4/3 earth) 추가
   - Multipath fading 명시

3. **01 vision_scope.md** 에 "Out of Scope" 섹션 강화
   - STAP, MIMO, SAR, RFS multi-target 등 명시

4. **새 § plan/16_baseline_audit.md** (이 분석을 정식 통합)
   - 새 Claude·새 개발자가 "왜 이건 빠졌나?" 질문에 답

### B. 14 dynamics_model.md 보강

5. § 14.x "표적 모델 정밀도" 신설
   - 단일 점 표적 / multi-scatterer / aspect-dependent RCS / glint 단계
   - MVP는 점, MVP+α는 multi-scatterer

### C. 차후 결정 필요 (Open Questions)

- Q-BL1. Two-ray multipath MVP 여부 (해상 시나리오 핵심 vs 구현 복잡도)
- Q-BL2. Multi-scatterer 표적 MVP 여부 (glint 사실성 vs MVP 범위)
- Q-BL3. UKF MVP 여부 (Stone Soup 호환 vs EKF로 충분)
- Q-BL4. GNN 포함 — 다중 표적 환경의 최소 요건이지만 우리 추적은 단일이라 결정 필요
- Q-BL5. Refraction 4/3 earth MVP 여부 (장거리만 영향)

---

## 10. 한 문장 요약

**TRsim의 차별점 (단일 추적 + DSP↔NN IDE + 4-error)은 견고하지만, 베이스라인 5개(Swerling/OS-CFAR/Two-ray/GNN/Refraction)가 빠지면 MATLAB·Stone Soup과의 비교 demo에서 신뢰도를 잃을 위험이 큼. MVP에 5개 추가, MVP+α에 10개 명시, 의도적 제외 5개 명시하면 베이스라인 인식 + 차별점 집중 둘 다 확보 가능.**
