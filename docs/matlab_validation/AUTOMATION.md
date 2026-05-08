# Octave Validation 자동화

## 목적

Phase 1.x / 2.x 물리 모듈마다 Python pytest 와 Octave `.m` 짝꿍을 짠다.
Octave 결과를 Python expected 와 비교 — Toolbox 없이 base 함수로
NIMA TR8350.2 / Mahafza / Skolnik 공식 직접 작성.

## 두 가지 실행 경로

### A. 사용자 직접 (Git Bash, 기본)

```bash
cd "/c/Workspaces/Claude/Tracking Radar Simulator/trsim"
bash scripts/run_octave_validation.sh test_geometry
bash scripts/run_octave_validation.sh all
```

스크립트가 `octave-cli` PATH 자동 보정 (Windows 표준 설치 위치 탐색).
없으면 안내. 메모리의 "메인 PC 에서 동기 실행" 정책 그대로.

### B. Cowork 자동 (선택 — 다음 Phase 에서 합의 후)

새 `.m` 짝꿍 작성하는 phase 에 진입하면 Cowork 가:

1. `request_access` 로 `Octave-11.1.0 (CLI)` 권한 요청.
2. `open_application` + `type` 으로 .m 실행.
3. console 출력 회수 → Python 정확값과 비교 → tolerance 좁힘 보고.

자동 실행 전 사용자 합의 필요 — G1 (Cowork 는 commit 안 함) 의
정신은 "사용자 PC 에서 자동으로 무거운 작업 안 한다" 이니, 매 phase
첫 회는 manual run 으로 결과 합의 후 자동화 활성.

## 짝꿍 작성 컨벤션

- function-with-subfunctions 패턴 (Octave script 안 local function 미지원).
- Toolbox 호출 금지 — `aer2enu` / `wgs84Ellipsoid` / `chirp` 등 X.
- 마지막에 `printf('PASS\n')` 또는 `error('FAIL: ...')` 명시.
- Python expected 값을 .m 안에 const 로 박음 (Python 으로 한 번 계산 후 박아서 1e-9 tolerance 검증).

## 현재 짝꿍 목록

`docs/matlab_validation/` —

- `test_geometry.m` (Phase 1.1: WGS84/ECEF/ENU/AER)
- `test_fmcw.m` (Phase 1.3: f_beat 667128.19 Hz, f_D 627.10 Hz)
- `test_horizon.m` (Phase 1.4: horizon 41218.15 m, bulge 1.4715 m)
- `test_rcs.m` (Phase 1.5: plate 12354.47 m², trihedral 2316.46 m²)
- `test_multipath.m` (Phase 1.6: F²/F⁴ lobing, d_null 62710 m)

Phase 2.x 는 dataclass-only 라 .m 짝꿍 없음 (validation 은 pytest).
Phase 2.5 (Atmosphere) 부터 다시 짝꿍 추가 예정.
