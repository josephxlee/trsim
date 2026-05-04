# 17. Open Platform — 오픈소스·DLC 에코시스템·거버넌스 (v0.35)

**최종 갱신**: 2026-05-02 (v0.40 — PhysicsModelProtocol 추가, Plugin Protocol 10 → 11)

**관련 문서**: [01 vision_scope](01_vision_scope.md), [02 architecture](02_architecture.md), [04 migration](04_migration.md), [07 nn_integration](07_nn_integration.md), [16 baseline_audit](16_baseline_audit.md)

## 17.1 왜 이 문서가 있나

v0.34까지의 TRsim은 **"개인이 만든 검증 도구"** 정체성이었지만, v0.35에서 결정적 정체성 전환:

> **"개인 도구"가 아니라 "확장 가능한 오픈소스 플랫폼"**

이 전환의 의미:
- 다른 개발자가 **알고리즘·자원·시각화 패널을 패키지(.trsim-pkg)로 추가** 가능
- Blender·VS Code 같은 **DLC 에코시스템** 모델
- **Apache 2.0 오픈소스**로 공개
- **GitHub public repo** + 적극 커뮤니티 권장

이 결정은 **설계 우선순위·아키텍처·문서·거버넌스 모두**에 영향. 이 문서가 그 정합을 맡는다.

## 17.2 핵심 결정 (v0.35)

### 17.2.1 라이선스 — Apache 2.0 (Q1-rev)

**선택 이유**:
- **DLC 자유도**: DLC 작성자가 자기 패키지를 어떤 라이선스로든 (closed/MIT/GPL) 배포 가능 → Marketplace 크기 ↑
- **특허 grant 명시**: 누군가 우리 코드 보고 특허 등록해 사용자 공격하는 risk 차단 (Stone Soup의 MIT엔 약함)
- **TF/PyTorch 호환**: NN 통합 (Apache 2.0)에 자연스러움
- **기업 채택 친화**: Anthropic·Google·Apache·Kubernetes 모두 Apache

**MIT 대비 차별점**:
- MIT는 특허 grant 약함 → 사용자가 우리 코드 보고 특허 등록 후 다른 사용자 공격 가능
- Apache는 명시적 특허 라이선스로 차단

**Blender(GPL) 대비 차별점**:
- Blender는 C++ 기반, Python 환경에서 GPL은 dynamic linking 모호
- 우리는 Python 기반이라 Apache가 자연스러움
- **Q5의 "Blender 역할"은 라이선스가 아닌 모델(플랫폼+커뮤니티)**, 그건 Apache로도 달성 가능

**대안 검토 결과**:
- ❌ MIT — 특허 grant 약함
- ❌ GPL/LGPL — DLC 상용화 막힘, Marketplace 작아짐
- ❌ BSD-3 — Apache와 비슷하지만 특허 조항이 약함
- ✅ **Apache 2.0** — 모든 야망과 정합

### 17.2.2 공개 모델 — 적극 공공 (Q2)

- GitHub public repo (예: `github.com/<user>/trsim`)
- Issue 열림 — 버그·기능 요청·질문 모두 환영
- PR 받음 — 초기엔 엄선, 점차 확대
- Discussion 활성 — 설계·아이디어 논의
- 릴리스 노트·changelog 표준화

**커뮤니티 권장 도구**:
- README의 "Contributing" 섹션
- `CONTRIBUTING.md` — 기여 가이드
- `CODE_OF_CONDUCT.md` — Contributor Covenant 채택
- `GOVERNANCE.md` — 의사결정 구조 명시
- `SECURITY.md` — 취약점 신고 방법

### 17.2.3 확장 깊이 — 핵심 계층 (Q3)

**개방 (DLC로 확장 가능)**:
- ✅ **알고리즘 계층** — Pipeline Stage Slot의 모든 슬롯 (Detector / AngleEstimator / Pairing / Tracker / Predictor / Classifier) + NN Plugin
- ✅ **자원 계층** — Map / Radar / Target Preset
- ✅ **시각화 패널** — pyqtgraph 패널, PyVista 셰이더, NN Mode 추가 패널

**비개방 (Domain Layer 핵심)**:
- ❌ MotionKind 추가 (동역학 계약이 무너짐)
- ❌ RadarModel 추가 (시뮬 안정성 위험)
- ❌ Coordinate System 변경 (Map Origin 불변)
- ❌ Coherence Validator 코어 (자체 일관성)

**MVP+α 검토**:
- MotionKind plugin (예: 헬리콥터 — autorotation 모델, 잠수함 — 수중 dynamics)
- RadarModel plugin (예: Pulse, CW)
- Validator plugin (커스텀 검사)

### 17.2.4 DLC 형태 — `.trsim-pkg` (Q4)

**구조** — VS Code Extension 모델:

```
my_advanced_tracker.trsim-pkg/        ← .zip 형식 (혹은 디렉토리)
├── manifest.toml                      ← 메타·의존·진입점 (필수)
├── README.md                          ← 사용자에게 보일 설명 (필수)
├── LICENSE                            ← DLC 라이선스 (작성자 자유)
├── plugins/                           ← 알고리즘 (선택)
│   ├── advanced_tracker.py
│   └── advanced_pairing.py
├── resources/                         ← 자원 (선택)
│   ├── radars/
│   │   └── kuband_naval.toml
│   ├── targets/
│   │   └── stealth_aircraft/
│   └── maps/
├── ui/                                ← 시각화 패널 (선택)
│   └── advanced_diagnostics_panel.py
├── tests/                             ← DLC 테스트 (권장)
│   └── test_advanced_tracker.py
└── examples/                          ← 사용 예시 (권장)
    └── advanced_tracking_demo.scnbundle
```

**manifest.toml 스키마**:

```toml
[package]
id = "advanced-tracker"               # 전역 고유 ID (kebab-case)
name = "Advanced Tracker for Stealth Targets"
version = "1.2.0"                      # SemVer
author = "Researcher Kim <kim@univ.ac.kr>"
description = "Stealth target 추적 향상 알고리즘 (CNN + Kalman 결합)"
license = "MIT"                        # DLC 작성자가 자유롭게
homepage = "https://github.com/researcher/trsim-advanced-tracker"

[compatibility]
trsim_min_version = "0.35.0"           # 호환 가능한 TRsim 최소 버전
trsim_max_version = "1.x"              # 호환 최대 (선택)

[dependencies]
# 다른 .trsim-pkg에 의존 (선택)
"glint-modeling-extras" = ">=1.0.0"

[entry_points]
# Pipeline Stage Slot에 register
"trsim.plugins.tracker" = "advanced_tracker:AdvancedTracker"
"trsim.resources.radars" = "resources/radars/"
"trsim.resources.targets" = "resources/targets/"
"trsim.ui.panels" = "ui/advanced_diagnostics_panel:Panel"

[python]
# Python 의존성 (numpy 등은 TRsim 본체와 공유)
extra_requires = ["torch>=2.0", "scikit-learn>=1.3"]
```

**설치 방식 (사용자 입장)**:
- **(MVP)** 파일 시스템에 압축 풀기 → `~/.trsim/packages/<package_id>/`
- **(MVP)** TRsim의 Editor → "Install Package..." 메뉴 → .trsim-pkg 파일 선택
- **(MVP+α)** `pip install trsim-pkg-<id>` (PyPI 통합)
- **(MVP+α)** Marketplace에서 1-click install

**세 가지 방식이 결국 같은 결과**: `~/.trsim/packages/<id>/`에 압축 해제 + manifest 등록.

### 17.2.5 마켓플레이스 — Awesome-list (Q7)

**MVP**: 별도 마켓플레이스 없이 `awesome-trsim-packages` repo:

```markdown
# Awesome TRsim Packages

## Trackers
- [advanced-tracker](https://github.com/researcher/trsim-advanced-tracker) — Stealth target 추적
- [imm-tracker](https://github.com/lab/trsim-imm) — IMM (Multiple Model)
- [particle-filter](https://github.com/cse/trsim-particle) — Particle Filter

## Detectors
- [adaptive-cfar](https://github.com/...) — Adaptive CFAR variants

## Targets
- [naval-fleet-pack](https://github.com/...) — 함정 5종 multi-scatterer 정밀

## Visualizations
- [3d-glint-viz](https://github.com/...) — Glint 시각화 패널
```

**MVP+α**: 별도 마켓플레이스 (GitHub Pages 또는 자체 웹). 트래픽·DLC 수가 일정 임계 넘으면.

### 17.2.6 SDK — Core에 포함 (Q8)

**구조**:
```python
# TRsim Core에 포함
import trsim.sdk as sdk

# Plugin 만들기
class MyTracker(sdk.TrackerProtocol):
    def predict(self, state, dt): ...
    def update(self, state, meas): ...

# DLC 빌드
sdk.build_package(
    package_dir="./my_tracker",
    output="my_tracker.trsim-pkg",
)

# 로컬 테스트
sdk.test_package("my_tracker.trsim-pkg")
```

**SDK 책임**:
- Plugin Protocol 정의 (Tracker / Detector / Pairing 등)
- Resource 스키마 검증 (Map / Radar / Target TOML 검사)
- Package builder (디렉토리 → .trsim-pkg)
- Package validator (manifest 검증, 의존성 체크)
- Local test runner

**위치**: `src/workbench/sdk/` (Core 패키지의 일부, `pip install trsim` 시 자동 설치)

### 17.2.7 거버넌스 — Core team (Q6)

**MVP 시점**:
- **BDFL temporary**: 너 혼자 결정. 단 PR·Issue는 모두 받음
- 이건 임시 — 신뢰할 수 있는 기여자 2~3명 모이면 Core team으로 전환

**MVP+α 단계**:
- **Core team (3~5명)**: 합의로 결정. Major 변경(Domain·라이선스·breaking change)은 합의 필수, Minor는 단독 가능
- 명시적 명단을 `GOVERNANCE.md`에 두기
- 신규 멤버 추가는 기존 멤버 만장일치

**장기**:
- Foundation 또는 단체 (Apache·NumFOCUS 같은) — 수년 후, 채택 규모 따라

### 17.2.8 안전·악장 관리 — MVP+α (Q9)

**MVP는 미정**:
- 자율 관리 (Issue로 의심 신고)
- 기본 sandbox 정도만 (이미 v0.14 plugin_scanner AST 검사)

**MVP+α 검토**:
- 명시적 Marketplace 입점 정책 (보안 검사, 서명, 명시한 불허 리스트)
- DLC 코드 sandboxing 강화 (subprocess 격리, OS 권한 제한)
- 신뢰 점수 시스템

이건 **마켓 규모 커진 후 결정** — 작은 마켓에 과한 governance는 사용자만 불편.

## 17.3 정체성 진화 — 한 줄 가치 제안

### v0.34 가치 제안 (현재)
> "추적 레이더의 DSP 블록을 NN으로 교체했을 때 단일 표적 추적 안정성이 어떻게 변하는지 IDE에서 비교·진단하는 워크벤치"

### v0.35 가치 제안 (제안)
> **"추적 레이더 알고리즘·자원·시각화를 DLC 패키지로 자유롭게 확장하는 오픈소스 워크벤치 플랫폼. 무료·Apache 2.0 코어에 커뮤니티가 만든 .trsim-pkg를 더해, 어떤 추적 시나리오라도 시뮬·검증·NN 학습이 가능하다."**

차이:
- "워크벤치" → "워크벤치 **플랫폼**"
- "도구" → "코어 + DLC 에코시스템"
- "비교·진단" → "시뮬·검증·NN 학습 + 확장"
- 라이선스 명시 (Apache 2.0)

### 단계별 정체성

| 단계 | 정체성 | 메시지 |
|---|---|---|
| MVP | 추적 레이더 IDE | "Stone Soup의 IDE 버전" |
| MVP+α (Wave 1) | + DLC 시작 | "VS Code Marketplace 같은 모델" |
| 성장기 | 플랫폼 | "Blender의 추적 레이더 버전" |
| 성숙기 | 학술·산업 표준 | "추적 레이더 분야의 GitHub" |

## 17.4 아키텍처 영향

### 17.4.1 Plugin SDK 계층 신설

기존 (v0.34):
```
ui → app → domain → physics
                          ↑
              plugins (Stage Slot, NN)
```

v0.35:
```
ui → app → domain → physics
                          ↑
            sdk (Plugin Protocol, Builder, Validator)
                          ↑
        DLC packages (.trsim-pkg)
```

**SDK Layer**:
- 위치: `src/workbench/sdk/`
- 의존: domain, physics만 (UI·App 모름)
- 책임: Plugin/Resource/Panel의 Contract 정의·검증·Build

#### Plugin Protocol 분류 (11개, v0.40)

| # | Protocol | 역할 | 도입 |
|---|---|---|---|
| 1 | DetectorProtocol | CFAR detection | v0.13 |
| 2 | PairingProtocol | Up/down 매칭 | v0.13 |
| 3 | AngleEstimatorProtocol | sum-channel + monopulse | v0.25 |
| 4 | TrackerProtocol | EKF/UKF/etc. | v0.13 |
| 5 | PredictorProtocol | Track prediction | v0.13 |
| 6 | ClassifierProtocol | Track classification (스텁) | v0.13 |
| 7 | DataAssociatorProtocol | GNN/JPDA/etc. | v0.34 |
| 8 | ResourceProtocol | Map/Radar/Target loader | v0.20 |
| 9 | UIPanelProtocol | DLC UI 패널 | v0.35 |
| 10 | DUTAdapterProtocol | HIL DUT 통신 + Lock-step sync (v0.39) | v0.38 |
| **11** | **PhysicsModelProtocol** | **사용자 물리 모델 plugin (v0.40)** | **v0.40** ⭐ |

**비공개 (Domain 안정성)**:
- MotionKindProtocol (14 § 14.5)
- RadarModelProtocol (08 § 8.x)

> **v0.39 갱신**: DUTAdapter 에 `sync_frame_start(frame_id)` / `sync_frame_end(frame_id, timeout_ms)` 메서드 추가 (Lock-step Handshake — Reference Timing Mode HIL 측). 18 § 18.16.4 참조.

> **v0.40 갱신** ⭐: **PhysicsModelProtocol** 추가 (11번째). 사용자 물리 plugin (06 § 6.7a 결정 변경). 5 카테고리 (`propagation` / `reflection` / `dynamics` / `atmosphere` / `antenna`) 지원. **Physics Lab Validation Bench 검증 통과한 것만 시뮬에서 사용** — 17~20+ 종 회귀 + 분석 공식 비교 + 사용자 시각 검증. 19 § 19.7 참조.

상세는 03 § 3.3 (Domain Contract) + 18 § 18.7 (DUTAdapter) + 18 § 18.16.4 (Lock-step) + 19 § 19.7 (PhysicsModelProtocol).

### 17.4.2 Plugin Loader 확장

기존 v0.13의 `PluginLoader`는 단일 .py 파일 로드. v0.35는:

```python
# src/workbench/app/package_manager.py (신규)
class PackageManager:
    """DLC .trsim-pkg 통합 관리.

    설치된 packages: ~/.trsim/packages/<id>/
    """

    def install(self, package_path: Path) -> InstallResult: ...
    def uninstall(self, package_id: str) -> None: ...
    def list_installed(self) -> list[PackageInfo]: ...
    def load_all(self) -> None:
        """앱 시작 시 모든 설치된 패키지 로드.

        - manifest.toml 검증
        - entry_points 등록 (Stage Slot, Resources, UI)
        - Compatibility 검사 (TRsim 버전)
        """
```

### 17.4.3 Resource Library 확장

v0.20의 `ResourceLibrary`가 다음 위치들을 모두 인덱스:
1. **Built-in**: `data/resources/{maps,radars,targets}/` (TRsim 내장)
2. **User**: `~/.trsim/resources/{maps,radars,targets}/` (사용자 작성)
3. **Packages**: `~/.trsim/packages/<id>/resources/{maps,radars,targets}/` (DLC 자원)

같은 ID의 자원이 여러 곳에 있으면 우선순위:
**User > Packages > Built-in**.

### 17.4.4 UI Panel Registry 신설

기존엔 UI 패널이 코드에 hard-coded. v0.35는 `PanelRegistry` 통해 DLC 패널도 등록 가능:

```python
# src/workbench/ui/panel_registry.py (신규)
class PanelRegistry:
    """UI 패널 등록·관리.

    Built-in 패널 + DLC 패널을 통합 관리.
    Workspace별로 어떤 패널을 표시할지 결정.
    """

    def register(self, panel_class: type, *, workspace: str, dock_area: str): ...
    def get_panels_for_workspace(self, workspace: str) -> list[type]: ...
```

DLC manifest의 `[entry_points]"trsim.ui.panels"`가 이 registry에 등록.

## 17.5 의존성 규칙 갱신 (02 § 2.5 보강)

v0.35 추가 규칙:

| 금지 | 예시 | 왜 |
|---|---|---|
| `domain/` → `sdk/` | Domain이 SDK 함수 import | SDK는 Domain 위 계층 |
| DLC `package` → `app/`, `ui/` 직접 import | Plugin이 RunManager 직접 호출 | Plugin은 SDK Protocol만 사용 |
| `sdk/` → `app/`, `ui/` | SDK가 App·UI 알고 있음 | SDK는 Domain·Physics만 의존 |

이로써 **DLC가 호환성 깨도 Core는 안정**.

## 17.6 라이선스 호환성 매트릭스

DLC가 다양한 라이선스로 배포될 수 있으니 사용자가 합쳐 쓸 때 호환성 명확히:

| Core (Apache 2.0) + DLC | 호환? | 결과 |
|---|---|---|
| Apache 2.0 DLC | ✅ | 자유 |
| MIT DLC | ✅ | 자유 |
| BSD-3 DLC | ✅ | 자유 |
| GPL v3 DLC | ⚠️ | DLC 사용 시 그 결과물도 GPL |
| LGPL DLC | ✅ | LGPL 의무는 DLC 자체에만 |
| Commercial / Closed-source DLC | ✅ | DLC 작성자 책임 |
| Public Domain / CC0 | ✅ | 자유 |

**중요**: DLC 작성자가 자기 라이선스를 명시하는 것이 의무. `manifest.toml`의 `license` 필드 필수.

## 17.7 거버넌스 문서 (요약)

`GOVERNANCE.md` (루트):

```markdown
# TRsim Governance

## Decision Making

### MVP Phase (current)
- BDFL: <name> (initial maintainer)
- All issues, PRs welcome
- Major decisions documented in plan/DECISIONS.md (ADR)

### Core Team Phase (future)
- 3~5 maintainers, consensus on:
  - License changes
  - Architecture changes (Domain Layer)
  - Breaking changes
- Single maintainer can merge:
  - Bug fixes
  - Documentation
  - Non-breaking features
```

## 17.8 기여자 라이선스 (DCO)

PR 받을 때:
- 각 commit에 `Signed-off-by: Name <email>` 필수
- DCO (Developer Certificate of Origin) 채택 — Linux 표준
- CLA는 채택 안 함 (지금은 단순함 우선)

`.github/PULL_REQUEST_TEMPLATE.md`에 명시.

## 17.9 NN 모델·데이터셋 (별도 라이선스)

DLC가 학습된 NN 가중치 포함 시:
- **NN 모델 자체 라이선스 별도** (manifest의 `[model]` 섹션)
- **학습 데이터 라이선스 별도** (CC-BY, CC-BY-SA 등)
- 작성자 책임으로 명시

이는 Apache 2.0 Core와 별도 — Core는 코드만 담당.

## 17.10 한국 법적 환경 (참고)

- Apache/MIT/GPL 모두 한국 법정에서 인정
- **방산 기술의 해외 배포**는 산업통상자원부 신고 의무 (DLC 작성자 책임)
- GitHub public repo는 자동 글로벌 — 작성자가 ECCN/HS code 검토 필요할 수 있음

## 17.11 MVP 범위 — 정체성 + 인프라

✅ **MVP**:
- LICENSE (Apache 2.0)
- README.md (오픈소스 + DLC 비전)
- CONTRIBUTING.md
- CODE_OF_CONDUCT.md (Contributor Covenant)
- GOVERNANCE.md
- SECURITY.md
- `.trsim-pkg` manifest 스키마
- PackageManager + 기본 install 흐름
- SDK Plugin Protocol 정의
- 1~2개 sample DLC (참조 구현)

❌ **MVP+α**:
- 별도 Marketplace 웹사이트
- DLC 보안 검사·서명
- PyPI 통합 (`pip install trsim-pkg-<id>`)
- DLC 의존성 해석 (다른 DLC에 의존)
- DLC 자동 업데이트
- DLC 평가·리뷰 시스템

## 17.12 Open Questions

- Q-OP1. 첫 sample DLC를 어떤 알고리즘으로? (Stone Soup adapter? IMM tracker?)
- Q-OP2. DCO만 vs CLA도 (기여자 부담 vs 명확성)
- Q-OP3. Marketplace awesome-list의 quality control (얼마나 엄격할지)
- Q-OP4. DLC 의존성 해석 시점 (MVP+α 어디?)
- Q-OP5. NN 모델 가중치 배포 표준 (HuggingFace 통합?)

## 17.13 영향 받는 문서

| 문서 | 변경 |
|---|---|
| 01 vision_scope.md | 한 줄 가치 제안 재작성, MVP 표에 "오픈 플랫폼" 추가 |
| 02 architecture.md | § 2.6b Plugin SDK Layer 신설, § 2.5 의존 규칙 보강 (SDK 격리), § 2.2 블록도 + § 2.9 모듈 도입 갱신 |
| **03 data_model.md** | **§ 3.2.1l Plugin Manifest 스키마 신설** (PackageManifest, InstalledPackage, EntryPoint, Compatibility) |
| 04 migration.md | Phase 0 오픈소스 인프라, Phase 7 DLC 시스템 신설 |
| 07 nn_integration.md | NN Plugin이 DLC 시스템과 통합됨 명시 |
| 10 workspaces.md | "Install Package..." 메뉴 추가 |
| 13 editor_workspace.md | Resource Browser에 packages 섹션 |
| 루트 LICENSE / NOTICE | 신규 |
| 루트 CONTRIBUTING.md | 신규 |
| 루트 CODE_OF_CONDUCT.md | 신규 |
| 루트 GOVERNANCE.md | 신규 |
| 루트 SECURITY.md | 신규 |

## 17.14 한 문장 요약

**TRsim은 "검증 도구"에서 "확장 가능한 오픈소스 플랫폼"으로 정체성 전환. Apache 2.0 + GitHub public + .trsim-pkg DLC + Core SDK로 알고리즘·자원·시각화를 자유롭게 확장 가능하게 하여, Stone Soup이 라이브러리, MATLAB이 종합 도구인 시장에서 "추적 레이더의 VS Code"를 노린다.**

## 섹션 상태

- 17.1 개요 — ✅
- 17.2 핵심 결정 (Q1-rev, Q2~Q9) — ✅
- 17.3 정체성 진화 — ✅
- 17.4 아키텍처 영향 — ✅
- 17.5 의존성 규칙 — ✅
- 17.6 라이선스 호환성 — ✅
- 17.7 거버넌스 — ✅
- 17.8 DCO — ✅
- 17.9 NN 모델 라이선스 — ✅
- 17.10 한국 법적 환경 — 🟡
- 17.11 MVP 범위 — ✅
- 17.12 Open Questions — 🟡
- 17.13 영향 문서 — ✅
- 17.14 요약 — ✅

---

👉 다음: [00_README.md](00_README.md) (계획서 진입점)
👉 이전: [16_baseline_audit.md](16_baseline_audit.md)
