# TRsim 설계 문서 (Design Docs)

이 폴더는 **이미 구현된 모듈** 을 다이어그램·표·시퀀스로 풀어쓴
설계 문서를 모아둔다. `docs/plan/` 은 "앞으로 무엇을 만들 것인가"
(plan-of-record), 여기는 "지금 코드는 어떻게 되어 있는가" (as-built).

## 왜 따로 두는가

- `docs/plan/` 17 권은 설계 단계 (Phase -1) 의 권위 문서. 한 번 합의
  되면 잘 안 바뀜.
- `src/workbench/.../*.py` docstring 은 모듈 단위 설명. 화면 한 장의
  레이아웃 / 위젯 계층 / 컨트롤러 ↔ 패널 데이터 흐름 같은
  **시각적 정보** 는 docstring 으로 못 담음.
- 새 세션 / 외부 기여자가 코드 들어가기 전에 한 번 훑어보면
  10분 안에 그림이 잡히도록 — 그게 이 폴더의 목적.

## 구조

```
docs/design/
├── README.md                    ← 진입점 (이 파일)
├── simulator/                   ← Simulator workspace 패널들
│   ├── README.md                ← Simulator 진입점 + 패널 인덱스
│   └── scene_3d_panel.md        ← Scene3DPanel 상세 다이어그램
├── editor/                      ← (placeholder) Editor activities
└── physics_lab/                 ← (placeholder) Physics Lab widgets
```

워크스페이스 별로 1 폴더, 패널·위젯 별로 1 .md. 더 큰 단위
(예: NN mode 흐름 전체) 가 필요해지면 별도 디렉토리.

## 문서 컨벤션

각 패널 문서는 다음 8 절을 가진다:

1. **위치와 역할** — 어느 워크스페이스의 어느 자리, plan 참조
2. **UI 레이아웃** — ASCII art 박스 다이어그램
3. **위젯 계층** — mermaid `graph TD`
4. **공개 API · 시그널** — 표
5. **데이터 흐름** — mermaid `sequenceDiagram` 또는 `flowchart`
6. **enum / 상수** — 표
7. **lazy / headless 패턴** — (해당 시) CI / 헤드리스 우회 설명
8. **알려진 함정** — 트랩 · `MVP_VERIFICATION_TREE.md § 4` 참조

다이어그램은 mermaid 가 default (GitHub render + plain text 양립).
ASCII art 는 비율 강조용으로만 (mermaid 가 못 그리는 경우).

## 인덱스

| 카테고리 | 문서 | 상태 |
|---|---|---|
| Simulator | [Scene3DPanel](simulator/scene_3d_panel.md) | ✓ 작성 |
| Simulator | FFTPanel | ☐ TODO |
| Simulator | RangeDopplerPanel | ☐ TODO |
| Simulator | RunPanel | ☐ TODO |
| Simulator | PropertiesPanel | ☐ TODO |
| Simulator | ScopePOVPanel | ☐ TODO |
| Simulator | PluginManagerPanel | ☐ TODO |
| Simulator | StageIOPanel | ☐ TODO |
| Simulator | ProfilerPanel | ☐ TODO |
| Editor | (활동 5종 다이어그램) | ☐ TODO |
| Physics Lab | BouncingBallDemo | ☐ TODO |

새 패널 문서 작성 시 위 표 한 줄 갱신.

## 작성 신호

- 패널 코드가 **새로 짜였을 때** — 같은 cycle 에 문서 1 장.
- 기존 패널을 **다이어그램 없이 이해 못 하겠을 때** — 그 시점에
  retroactive 1 장 (Scene3DPanel 이 이 trigger 로 작성된 첫 케이스).
- 새 세션이 들어와서 헷갈리는 부분이 반복 발견되면 그 부분 1 장.

문서가 코드를 **압도하지 않게**. 한 패널 = 1 페이지 정도, 표 + 다이어그램
중심, prose 는 짧게.
