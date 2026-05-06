# Cross-validation `.m` scripts

이 폴더의 `.m` 파일은 TRsim Python primitives 와 **수치적으로 같은 결과** 를 내는지 독립
검증하는 reference 스크립트들이다.

## 실행 환경

**둘 다 동작**:
- **MATLAB** (R2014b+, Toolbox 없음 — base 만)
- **GNU Octave** (5.0+)

스크립트는 의도적으로 base 함수 (`sin`, `cos`, `atan2`, `hypot`, `sqrt`, `mod`,
`deg2rad`, `rad2deg`) 만 사용. **Mapping Toolbox / Aerospace Toolbox / 기타 add-on
필요 없음**. WGS84 / ECEF / ENU / AER / Haversine 변환은 NIMA TR8350.2 표준 공식을
inline 함수로 직접 구현.

## 사용법

```bash
# Octave (Linux/Mac/Windows)
octave test_geometry.m

# MATLAB
matlab -batch "run('test_geometry.m')"
# 또는 IDE 에서 열고 Run
```

각 스크립트는 console 에 reference 값 출력. TRsim pytest 와 비교:

```python
# tests/physics/test_geometry.py 의 expectation 과 .m 출력값 일치 여부 확인
```

차이가 tolerance 보다 크면 issue 를 열어 reference 값 또는 Python 구현 점검.

## 파일

| `.m` | 검증 대상 | TRsim test |
|---|---|---|
| `test_geometry.m` | `physics/geometry.py` (Phase 1.1) | `tests/physics/test_geometry.py` |
| (추가 예정) `test_fmcw.m` | `physics/propagation/fmcw.py` (Phase 1.3) | `tests/physics/test_fmcw_signal.py` |
| (추가 예정) `test_horizon.m` | `physics/propagation/ray_tracing.py` (Phase 1.4) | `tests/physics/test_horizon.py` |
| (추가 예정) `test_rcs.m` | `physics/reflection/rcs_single.py` (Phase 1.5) | `tests/physics/test_radar_equation.py` |
| (추가 예정) `test_multipath.m` | `physics/propagation/multipath.py` (Phase 1.6) | `tests/physics/test_two_ray_multipath.py` |

## 폴더 이름 (`matlab_validation`) 에 대해

이름은 역사적 — `.m` 확장자가 MATLAB 에서 유래. 실제로 모든 스크립트는 Octave 에서도
동작하게 작성됨. 폴더 이름 굳이 변경 안 한 이유는 외부에서 검색·인지하기 쉬움.

향후 PROJ (pyproj) / Stone Soup / 기타 라이브러리 비교 스크립트가 추가되면 별도 폴더:
- `docs/pyproj_validation/`
- `docs/stonesoup_validation/`
