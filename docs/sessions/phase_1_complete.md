# Phase 1 — Primitives Layer (완료)

## Status
- 완료: 2026-05-06
- CI: 6 환경 모두 PASS (Ubuntu/Windows/macOS × Py 3.11/3.12)
- Test: 158 (Phase 0 의 5 위에 누적)

## Sub-phase 요약

| sub | 모듈 | test | Octave reference |
|---|---|---|---|
| 1.1 | `physics/geometry.py` | 28 | WGS84↔ECEF↔ENU↔AER, Seoul ECEF sub-mm |
| 1.2 | `domain/geo.py` | 17 | GeoOrigin / VerticalReference (data only) |
| 1.3 | `physics/propagation/fmcw.py` | 21 | f_beat 667128.19 Hz, f_D 627.10 Hz |
| 1.4 | `physics/propagation/ray_tracing.py` | 22 | horizon 41218.15 m (4/3), bulge 1.4715 m |
| 1.5 | `physics/reflection/rcs_single.py` | 20 | plate 12354.47 m², trihedral 2316.46 m² |
| 1.6 | `physics/propagation/multipath.py` | 15 | F²/F⁴ lobing, d_null 62710 m |

## 핵심 상수·결정

- `C_LIGHT_M_S = 299_792_458.0` (SI exact, fmcw.py / multipath.py 공유)
- `R_EARTH_MEAN_M = 6_371_008.7714` (WGS84 mean, geometry.py / ray_tracing.py 공유)
- `K_FACTOR_DEFAULT = 4/3` (ITU-R P.834 standard atmosphere)
- `RHO_FLAT_SEA_SMOOTH = -0.95` (ITU-R P.527 X-band sea bounce)
- `PI` 모듈별 local Final[float]
- FMCW Triangle sign convention: 접근 = +v, `f_up = α·τ - f_D`
- Two-ray sign convention: negative ρ for soft-bounce (π reflection phase)
- 9.4 GHz X-band 표준 검증 frequency (λ ≈ 0.03189 m)
- AZ convention: clockwise from North (radar standard, 수학 phi 와 다름)

## 학습된 패턴 (Phase 1 누적)

### Lint trap
- RUF002 docstring ASCII-confusable: `α/τ` → `alpha/tau`, `−` → `-`,
  `×` → `x`, `MVP+α` → `MVP+alpha`
- SIM300 pytest.approx Yoda → `pyproject.toml` per-file-ignores 에 추가
- RUF043 pytest.raises match 메타문자 → raw string `r"..."` + `\.` escape
- I001 import 순서 → `ruff check --fix` 자동 정리

### mypy strict
- `**` 결과 Any → `math.pow()`, `math.sqrt()` 사용
- numpy ndarray 타입: `numpy.typing.NDArray[np.float64]`, `NDArray[np.bool_]`

### Cross-validation workflow
1. Cowork 가 module + pytest + .m 짝꿍 작성
2. Sandbox 에서 `ruff check + format` + Python parse 사전 검증
3. 사용자 Git Bash 로 commit + push
4. CI 결과 + Octave 비교
5. 손계산 정밀도 부족 시 → Python 정확값으로 expected 갱신, tolerance 좁힘 (1e-3 → 1e-9)

### Cowork ↔ Windows mount sync issue
- bindfs 가 가끔 파일 끝 truncate (마지막 1~5 char 잘림)
- Python `open + flush + os.fsync()` 강제 sync 로 복구
- 매 commit 스크립트에 `tail -3 + grep` 자동 truncation 감지

## Octave 짝꿍 파일 위치

`docs/matlab_validation/` —
- `test_geometry.m` (Phase 1.1)
- `test_fmcw.m` (Phase 1.3)
- `test_horizon.m` (Phase 1.4)
- `test_rcs.m` (Phase 1.5)
- `test_multipath.m` (Phase 1.6)

`README.md` 가 폴더 안에 — Octave/MATLAB 양쪽 호환 + 사용법.

## 다음 (Phase 2 진입)

Phase 2 = Domain Contract + dataclass. 12 sub-phase 분할.
첫 sub: `2.1` Core types (PositionerCommand + Run/Sim lifecycle).
