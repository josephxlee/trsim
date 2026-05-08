# DECISIONS.md — TRsim 누적 결정 로그 (ADR-light)

claude.ai 17 세션 (v0.1~v0.41) + Cowork Phase 0~2 에서 합의된 핵심
결정. **이미 끝난 사항** — 새 세션에서 재논의 금지. 충돌하는 제안은
이 문서를 먼저 깨야 함.

형식: 카테고리별 단답 + 짧은 근거. 권위 문서 인용은 `plan/NN_*.md`
또는 `AGENT_GUIDE.md` 로.

---

## A. 정체성·범위

**A1. 주 목적 = 추적 성능 검증.** 탐지율 / 일반 DSP 품질이 아님.
plan/01.

**A2. Primary Target 이 1급 개념.** 모든 메트릭 / UI / 제어가 선택
표적 중심. DSP Plugin 에는 노출하지 않음 (메트릭·제어 레벨에서만).

**A3. Closed-loop tracking 이 본질.** EKF/UKF 출력 → Positioner 피드백.
Positioner Lag 가 성능의 일부. open-loop 모드는 별도.

**A4. FMCW Triangle 단독.** Hybrid (CW+FMCW), Pulse Doppler 등은 미래
RadarModel. Pairing 정의가 다르므로 코드/Contract 에서 섞지 말 것.
plan/08.

**A5. Multi-scatterer 표적 (v0.34).** 점 표적이면 glint 가 사라져 차별점이
사라짐. ExtendedTarget 이 기본.

**A6. NN 은 선택적, 별도 모드.** 기본은 NN 없이 동작. v0.13 분리 합의.

**A7. Apache 2.0 + DLC 에코 (v0.35).** `.trsim-pkg` 확장. SDK Layer 가
DLC 안정 API.

---

## B. 아키텍처

**B1. 6 Layer.** UI → App → SDK → Domain → Physics → Primitives.
import-linter 강제. plan/02 § 2.6.

**B2. SDK 는 안정 API.** Domain 변경이 DLC 를 깨뜨리지 않게. v0.35.

**B3. Three Workspaces.** Editor (teal) / Simulator (회청+빨강) /
Physics Lab (보라). plan/10, plan/13, plan/19.

**B4. 11 Plugin Protocol.** Tracker / Detector / Waveform / Antenna /
RCS / Atmosphere / Dynamics / Pairing / Detection / Display / Physics.
plan/17, plan/19.

**B5. Single Command Path.** `CommandSource` enum (USER / SCRIPT /
TRACKER / ...). TRACKER 일 때 `source_track_id` + `source_frame_id`
필수 — validation 강제. Phase 2.1.

**B6. SimulationState ⊥ RunState.** 완전히 별개 enum 타입. 시뮬레이션
계의 상태와 한 회 Run 의 상태는 분리. Phase 2.1.

**B7. Tracker 는 교체 가능 Slot.** EKF 는 기본 구현. Contract 를 EKF
특성에 결합 금지.

**B8. Target Gate 는 Tracker 옵션.** 독립 스테이지로 설계 금지.

---

## C. 물리 상수·관례

**C1. SI exact 광속.** `C_LIGHT_M_S = 299_792_458.0`. fmcw / multipath
공유. 모듈별 `Final[float]`.

**C2. WGS84 mean Earth.** `R_EARTH_MEAN_M = 6_371_008.7714`. geometry /
ray_tracing 공유. NIMA TR8350.2.

**C3. ITU-R P.834 4/3.** `K_FACTOR_DEFAULT = 4/3`. standard atmosphere
refraction.

**C4. ITU-R P.527 sea bounce.** `RHO_FLAT_SEA_SMOOTH = -0.95`. X-band
flat-sea smooth case. Two-ray sign convention: **negative ρ** (π reflection phase).

**C5. AZ convention.** Clockwise from North (radar standard). 수학
`phi` (counterclockwise from East) 와 다름. 변환 시 명시.

**C6. FMCW Triangle sign.** 접근 = +v, `f_up = alpha * tau - f_D`.
Phase 1.3 docstring + .m 파일 동일.

**C7. X-band 표준 검증 frequency.** 9.4 GHz, λ ≈ 0.03189 m. test fixture
기본값.

**C8. ASCII-only docstring.** RUF002 회피 — `α/τ/−/×` 대신 `alpha / tau
/ - / x`. lint trap 누적.

---

## D. dataclass·코드 패턴

**D1. frozen=True, slots=True.** 모든 도메인 dataclass. 불변 + 메모리
효율.

**D2. from __future__ import annotations.** 항상. forward-ref 자유.

**D3. mypy strict.** `**` 결과 Any → `math.pow()`/`math.sqrt()`. numpy
는 `NDArray[np.float64]` / `NDArray[np.bool_]`.

**D4. entity_id / map_id non-empty validation.** `__post_init__` 에서
빈 문자열 거부.

**D5. WorkbenchTerrain numpy 불변.** `setflags(write=False)` 강제 — 복사
실수 방지.

**D6. Map.content_hash 빈 default.** Phase 4 bundle 시점에 채움.

---

## E. 도메인 모델

**E1. MotionKind 7 종.** FIXED_GROUND / GROUND_VEHICLE / SURFACE_VESSEL
/ FLOATING_STATIC / AIRCRAFT / POWERED_FLIGHT / BALLISTIC. plan/12.

**E2. AnchorMode 4.** BASE_TO_TERRAIN (default, 물 위 거부) /
EXPLICIT_ALT / FLOOR_AT_MSL / TERRAIN_OFFSET. v0.21 anchor 시스템.
plan/12 § 12.8.

**E3. MeshOrigin 3.** BASE_CENTER (default) / BASE_LOWER_CORNER /
BASE_LOWER_CENTER. plan/12 § 12.8.2.

**E4. WaveResponsePreset 4.** heave amplitude 순서: BUOY (0.95) >
SMALL_BOAT (0.7) > LARGE_SHIP (0.3) > NONE (0.0). Phase 2.3b.

**E5. WMO sea_state 0..9 strict.** Phase 2.2 SeaSurface.

**E6. BuildingEntity placement.motion_kind 반드시 FIXED_GROUND.**
__post_init__ 강제. Phase 2.3c.

**E7. 9 Test Objects (Physics Lab).** plan/19. Phase 6+ 구현.

---

## F. 검증·테스트

**F1. Octave base 함수만.** Mapping / Signal / Aerospace Toolbox 호출
금지. NIMA TR8350.2 / Mahafza / Skolnik 직접 작성. 사용자 PC 는 GNU
Octave.

**F2. Python exact 값 = expected.** 손계산 정밀도 부족 (Seoul ECEF
2 km / beat freq 0.006 Hz 사례). tolerance 1e-3 → 1e-9 좁힘이 정답.

**F3. pytest.approx 우측 expected.** SIM300 Yoda → `tests/**/*.py`
per-file-ignore.

**F4. CI 6 환경.** Ubuntu / Windows / macOS × Python 3.11 / 3.12.
모두 PASS 가 push 통과 기준.

**F5. Octave 짝꿍 위치.** `docs/matlab_validation/`. function-with-
subfunctions 패턴 (Octave script 내 local function 미지원).

---

## G. 워크플로

**G1. Cowork 는 commit 안 함.** 사용자 Git Bash 가 실행. 일회성 commit
스크립트는 `git_sh/<name>.sh` (gitignored).

**G2. DCO sign-off 필수.** `git commit -s` — 모든 commit 스크립트에
포함. CONTRIBUTING.md 명시.

**G3. branch 전략 = main 직 push.** 외부 PR 받기 시작하면 재고.

**G4. pre-commit hook = bindfs sync 검증 + ruff.** `scripts/githooks/`
저장소 내장. mypy 는 시간 들어 CI 만.

**G5. 세션 핸드오프.** Phase 끝마다 `docs/sessions/phase_<N>_<topic>.md`.
sub-step 단위 1-3 페이지. CLAUDE.md / docs/sessions/README.md 참조.

---

## 갱신 규칙

- 새 결정 합의 시 해당 카테고리 끝에 추가 (번호 증가).
- 기존 결정 뒤집을 때는 **삭제 금지** — `~~취소선~~` + 사유 + 대체 결정
  ID 명시. 미래 재논의 차단의 핵심.
- 카테고리 자체 추가는 사용자 합의 후 (구조 변경).

최근 갱신: 2026-05-08 — 시드 (Phase 0~2.3c 누적 36 결정).
