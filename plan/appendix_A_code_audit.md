# 부록 A. (DEPRECATED) 기존 sim_3d 코드 자산 평가

**최종 갱신**: 2026-04-28 (v0.36 — DEPRECATED 처리)

> 🚫 **DEPRECATED — 본 평가는 무효**
>
> 기존 `sim_3d` 프로토타입은 **정상 동작이 검증되지 않은** 코드입니다. 본 부록의
> 모듈별 재사용/재작성 판정 (🟢/🟡/🔴) 은 **참조하지 마세요**.
>
> **올바른 방침**:
> - 모든 물리 함수·도메인 코드는 v0.16~v0.35 계획서 기반 **신규 작성**
> - 검증은 분석 공식 (수계산) + Stone Soup·MATLAB 비교
> - 옛 코드를 회귀 비교 기준으로 쓰지 않음
>
> 본 부록은 **역사적 메모**로만 보존. 04 migration 의 이식 매트릭스에서도 본 평가를 참조하지 않습니다.

---

## ⚠️ 본 부록 이하 내용은 무효 (보존만)

모듈별로 재사용/재작성/폐기 판정. 04 마이그레이션 매트릭스의 **근거**를 상세히 기록.

---

## 평가 기준

각 모듈에 대해:

- 🟢 **재사용** — 그대로 이식, 구조 유지
- 🟡 **구조 조정** — 로직은 유지, 껍데기/인터페이스만 교체
- 🔴 **재작성** — 기능만 참조하고 처음부터 다시
- ⚪ **폐기** — 새 레포에 필요 없음

각 모듈의 **문제점**과 **재사용 시 주의사항**도 함께.

---

## A.1 `physics/` — 🟢 전체 재사용 (조건부)

### A.1.1 `physics/fmcw.py` (571줄)

**판정**: 🟢 재사용

**내용 요약**:
- FMCWConfig, RXArrayConfig dataclass
- IF 주파수 ↔ bin ↔ range 변환
- 4채널 위상 → AZ/EL 계산
- `simulate_rx_signal()` — RX 시뮬레이션
- `pair_up_down_peaks()` — Up/Down 페어링

**강점**:
- 순수 함수 다수, UI 의존 없음
- `@dataclass(frozen=True)` 적용됨
- 수치 상수에 단위 접미사 명시

**주의사항**:
- `fs_decim_hz = 200_000.0` — 디시메이션 후 샘플링 레이트. AWG 미래 연결 시 재검토 필요.
- 일부 함수에 `numpy` 반환과 스칼라 반환이 섞여 있음 — 시그니처 일관성 점검 필요.

**검증 필요**:
- 단위 테스트 전무 → MVP 이식 시 추가
- 문헌 비교 (Richards "Fundamentals of Radar Signal Processing" Ch.2-3)

### A.1.2 `physics/ray_tracing.py` (573줄)

**판정**: 🟢 재사용

**내용 요약**:
- `trace_tx_to_target()` — TX 레이트레이싱 + LOS + Gaussian 빔 게인
- `TerrainGridIndex` — 격자 인덱스, 빠른 교차 검사
- `check_los_terrain`, `check_horizon_limit` — 가시성
- `terrain_height_bilinear` — 보간

**강점**:
- 공간 인덱스 구조가 잘 설계됨
- 지구 곡률 보정 포함

**주의사항**:
- `TerrainGridIndex` 빌드 비용이 큼 — 캐시 정책 필요 (프레임마다 다시 만들지 않도록)
- 멀티스레드 안전성 미검증

**검증 필요**:
- 지형 기반 차폐의 회귀 테스트
- 수평선 거리 공식 (4/3 Earth radius 근사)

### A.1.3 `physics/reflections.py` (739줄)

**판정**: 🟡 재사용 + 검증 필요

**내용 요약**:
- 해면 클러터 (Douglas Sea State 기반)
- 멀티패스 기하
- 해면 반사계수 ρ
- 건물 RCS

**강점**:
- 벡터화된 구현

**우려사항**:
- **문헌 출처가 불명확한 수식 존재** — 어떤 논문/교과서 기반인지 추적 필요
- `compute_building_total_rcs_dbsm`의 합산 방식이 "가시면 RCS 단순 합"인데 이게 물리적으로 맞는지 재검토 필요
- Sea State → 클러터 전력 변환의 경험식 출처 확인

**액션**:
- 이식 시 각 함수에 **참고문헌 주석 명시** 의무
- Golden Dataset 구축 우선순위 높음

### A.1.4 `physics/geometry.py` (111줄)

**판정**: 🟢 재사용

단순 기하 유틸. 박스/L자 건물 면 계산. 단위 테스트만 추가하면 됨.

### A.1.5 `physics/render/` (서브디렉토리)

**판정**: 🟡 이동 (계층 재분류)

- `gerstner_waves.py` — 해면 파도 메시 생성
- `terrain_mesh.py` — LOD/청크 지형 메시

이 둘은 **렌더링 보조**라 `physics/`가 아니라 `ui/panels/mesh_helpers/` 쪽으로 이동.

---

## A.2 `model/` — 🟡 대부분 구조 조정

### A.2.1 `model/sim_engine.py` (696줄)

**판정**: 🔴 분리 재작성

**내용 요약**:
- `SimFrameResult` — 프레임 결과 DTO
- `SimEngine` — 프레임 계산 엔진
- `buildings_to_scene_objects()` — 변환
- CA-CFAR 검출

**문제점**:
- **결과 DTO(`SimFrameResult`)에 UI 표시용 필드 섞임** (fft_power_db 등)
- **CA-CFAR 검출**이 엔진 내부에 하드코딩 — Detector 플러그인과 중복
- `compute_frame_scene()` 메서드 하나가 200줄 가까이 — 7단계 파이프라인을 한 함수에

**새 위치**:
- 물리 계산 로직 → `domain/environment.py`의 Environment 구현체
- CA-CFAR → `plugins_builtin/default_detector.py`
- SimFrameResult 역할 → TraceFrame (Probe 시스템)으로 대체

### A.2.2 `model/radar/` (서브모듈, 2,800줄)

**판정**: 🟡 대부분 재사용 (Contract 기반으로)

파이프라인 설계가 **이미 훌륭하다**. 그대로 살려서 새 Contract에 맞춤.

| 파일 | 판정 | 새 위치 |
|---|---|---|
| `pipeline.py` | 🟡 | `domain/pipeline.py` — Protocol 기반으로 |
| `transmitter.py` | 🟡 | `plugins_builtin/default_transmitter.py` |
| `receiver.py` | 🟡 | `plugins_builtin/default_receiver.py` |
| `detector.py` | 🟡 | `plugins_builtin/default_detector.py` |
| `pairing.py` | 🟡 | `plugins_builtin/default_pairing.py` |
| `tracker.py` | 🟡 | `plugins_builtin/default_tracker.py` |
| `positioner.py` | 🟡 | `plugins_builtin/default_positioner.py` + `domain/positioner_dynamics.py` |
| `config.py` | 🟡 | `domain/radar_state.py` + `domain/latency.py` |
| `antenna.py` | 🟢 | `domain/antenna_spec.py` |
| `fmcw.py` | ⚠ 중복 | `physics/fmcw.py`와 합병 |

**중복 이슈**: `physics/fmcw.py`와 `model/radar/fmcw.py`가 비슷한 이름으로 공존.
확인 결과 역할이 다르긴 함(`physics`는 구현, `model/radar`는 인터페이스/설정) — 명확히 분리 또는 통합 필요.

### A.2.3 `model/terrain.py`, `model/building.py`, `model/geo.py`

**판정**: 🟢 재사용

작고 응집도 높음. 그대로 `domain/`으로 이동.

### A.2.4 `model/positioner.py`, `model/antenna.py`, `model/camera.py`

**판정**: 🟢 재사용

스펙 데이터 클래스들. 그대로 `domain/*_spec.py`로.

### A.2.5 `model/scene_layers.py` (88줄)

**판정**: 🟡 이동 + 재배치

씬 로딩 기능 — `io/scenario_loader.py`로 통합.

### A.2.6 `model/render/` (서브모듈)

**판정**: 🟡 이동 (UI 계층으로)

- `radar_mesh.py` — 레이더 3D 모델 파트 정의
- `solar_lighting.py` — 태양 위치/조명
- `solar_mesh.py` — 조명 메시

**새 위치**: `ui/panels/mesh_helpers/`

---

## A.3 `view/` — 🔴 전체 재작성

### A.3.1 `view/main_window.py` (1,583줄, 48 메서드)

**판정**: 🔴 폐기 후 재작성

**문제점**:
- God Class의 교과서 예시
- 48개 메서드가 한 클래스 안에 섞여 있음
- 재생 / LOD / 인셋 / 레이아웃 / 빔 / 포지셔너 / 키보드가 한 곳에

**재설계 방침**:
- 새 `ui/main_window.py`는 **조립자**로만 (< 300줄 목표)
- 48개 메서드는 대부분 패널/커맨드/서비스로 분산
- LOD 관리는 3D View 패널 내부로 캡슐화
- 뷰 모드 전환은 **DockWidget 도킹 상태**로 대체

### A.3.2 `view/radar_viewer_3d.py` (1,358줄)

**판정**: 🔴 재작성 (기능 참조)

기존 GLViewWidget 기반. 새 `ui/panels/scene_view_3d.py`로.
- 현재 기능 전부 이식
- **단일 뷰 패널**로 단순화 (복수 뷰는 여러 패널로)
- 오버레이 레이어 개념 도입

### A.3.3 `view/data_panel.py` (682줄)

**판정**: 🔴 분할 재작성

**분할**:
- FFT 부분 → `ui/panels/fft_panel.py`
- 각도/트랙 시계열 → `ui/panels/tracking_panel.py`
- 수치 정보 → `ui/panels/properties_panel.py` 또는 StatusBar
- 태양 조명 컨트롤 → `ui/panels/environment_panel.py` (선택)

### A.3.4 `view/beam_visualization.py` (547줄)

**판정**: 🟡 재사용 (3D View의 내부 모듈로)

TX 빔 시각화. `scene_view_3d.py`의 헬퍼로 포함.

---

## A.4 `controller/`, `presenter/` — ⚪ 폐기

### A.4.1 `controller/input_handler.py` (156줄)

**판정**: ⚪ 폐기

**이유**:
- 키보드 이벤트 해석이 중앙 집중 안 됨 — 일부는 여기, 일부는 `MainWindow._setup_shortcuts`
- `self._win.xxx` 직접 참조 (진짜 Controller 아님)

**대체**:
- Command Registry가 같은 역할 수행
- 키는 단축키로 Command에 바인딩

### A.4.2 `presenter/sim_presenter.py` (297줄)

**판정**: ⚪ 폐기 (기능은 흡수)

**이유**:
- "Presenter"라기보단 "MainWindow의 확장 메서드 묶음"
- 강한 순환 의존 (`self._win` 도처)

**대체**:
- `app/evaluator.py` + `app/playback_clock.py` + EventBus 조합으로 역할 분담
- UI↔Domain 중재는 **EventBus가 담당**

---

## A.5 `physics/`는 이미 다뤘고, 기타

### A.5.1 `utils/`

| 파일 | 판정 | 새 위치 |
|---|---|---|
| `common.py` | 🟢 | `workbench/common.py` |
| `mesh_loader.py` | 🟢 | `io/mesh_loader.py` |

### A.5.2 `scripts/`

**판정**: 🟢 대부분 재사용 (개발 보조용)

- `scripts/terrain/` — DEM 다운로드/병합 스크립트
- `scripts/buildings/` — OSM 건물 변환
- `scripts/scene/` — 씬 매니페스트 검증

→ 새 레포의 `scripts/` 디렉토리에 그대로. 이식 우선순위 **낮음** (MVP 이후).

### A.5.3 `scenarios/`

**판정**: 🟢 데이터 보존

- 7개 시나리오 CSV 그대로
- 각 디렉토리에 `scenario.toml` 추가 (마이그레이션 스크립트 필요)

### A.5.4 `obj/`, `data/`

**판정**: 🟢 데이터 보존, 이동만

- `obj/statics/` → `data/static/`
- `obj/dynamics/` → `data/ships/`
- `data/terrain/` → `data/terrain/`

### A.5.5 진입점 파일들

| 파일 | 판정 |
|---|---|
| `run_sim.py` (340줄) | ⚪ 폐기 — `__main__.py`로 대체, subprocess 재실행 방식 제거 |
| `sim_3d_boresight_qt.py` (100줄) | ⚪ 폐기 — CLI argparse 대신 Workbench UI |

### A.5.6 테스트 코드

| 파일 | 판정 |
|---|---|
| `test/ctrl_model_tb.py` (24K) | ⚠ 검토 필요 — 어떤 테스트베드인지 내용 확인 후 결정 |
| `test/ctrl_tb.py` (9K) | ⚠ 검토 필요 |

기존 테스트 코드의 가치는 구현 시점에 케이스별로 확인.

---

## A.6 문서화 자산

### A.6.1 `docs/` (267K)

기존 `docs/` 디렉토리에 귀중한 설계 자료 존재:

- `docs/radar/` — 레이더 사양 문서
- `docs/terrain/` — DEM 처리 방법론
- `docs/building/` — 건물 데이터 구조
- `docs/schema/` — 데이터 스키마
- `docs/spec/` — 각종 스펙
- `docs/workflow/` — 워크플로우
- `docs/sim_3d_code_analysis.md` — 이번 분석에서 발견한 기존 분석 보고서

**판정**: 🟢 선별 이식

새 레포의 `docs/`에 **참고 문서로 보존**. 새 계획서와 상충하는 부분은 **deprecated 폴더**로.

---

## A.7 재사용 요약 통계

| 판정 | 모듈 수 | 라인 수 | 비고 |
|---|---|---|---|
| 🟢 재사용 | ~15 | ~4,000 | 주로 physics/, model/ 데이터 타입 |
| 🟡 구조 조정 | ~12 | ~3,500 | 주로 model/radar/ |
| 🔴 재작성 | 4 | ~4,200 | view/ 전체 |
| ⚪ 폐기 | 3 | ~800 | controller/, presenter/, run_sim |
| **합계** | ~34 | **~12,500** | 핵심 Python 코드 |

**자산 재활용률 추정**: ~60% (🟢 + 🟡의 일부)

---

## A.8 즉시 이식 가능 vs 검증 필요 분류

### 즉시 이식 가능 (Phase 1)

문헌 검증 필요 없음. 구조 변경만.

- `model/geo.py` → `domain/geo.py`
- `model/terrain.py` → `domain/terrain.py`
- `model/building.py` → `domain/building.py`
- `model/positioner.py` → `domain/positioner_spec.py`
- `model/antenna.py` → `domain/antenna_spec.py`
- `utils/common.py` → `workbench/common.py`
- `utils/mesh_loader.py` → `io/mesh_loader.py`
- `physics/geometry.py` → `physics/geometry.py`

### 검증 필요 (문헌 비교 + Golden Dataset)

MVP에서 Golden Dataset 우선 구축 대상.

- `physics/reflections.py` — 클러터/멀티패스 모델
- `model/sim_engine.py`의 CA-CFAR
- `model/radar/tracker.py` — EKF 파라미터
- `model/radar/detector.py` — 검출 임계값 정책

### 신중히 재설계 (🔴)

UI 계층 전부. 새 설계로 처음부터.

---

## 섹션 상태

- A.1 physics — ✅
- A.2 model — ✅
- A.3 view — ✅
- A.4 controller/presenter — ✅
- A.5 기타 — ✅
- A.6 docs — ✅
- A.7 통계 — ✅
- A.8 이식 순서 — ✅

---

👉 마지막: [appendix_B_glossary.md](appendix_B_glossary.md)
