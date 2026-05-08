# `docs/sessions/` — Session-to-session handoff log

Cowork (Claude Agent) 세션이 길어지면 컨텍스트 윈도우가 벅차짐. 새 세션이
중간부터 자연스럽게 이어받을 수 있도록 **각 Phase sub-step 끝마다** 짧은
markdown 요약을 남긴다.

## 컨벤션

- 파일 이름: `phase_<N>_<M>_<short_topic>.md`
  - 예) `phase_2_3c_building.md`, `phase_1_4_ray_tracing.md`
- 분량: 1-3 페이지. 길게 쓰지 말 것.
- 위치: `trsim/docs/sessions/` (committed, gitignored 아님).

## 매 파일이 담는 것

```markdown
# Phase X.Y — <module>

## Status
- 날짜, CI 상태, test count

## Added (this sub-phase)
- 파일 목록 + 핵심 API
- 핵심 결정 (sign convention, 상수, validation rule 등)

## Cumulative test count
- 누적 통계

## Octave / cross-validation
- 적용 시 reference 값 또는 N/A

## Next sub-phase
- 다음 단계 + 의존
```

## 새 세션 시작 시 읽는 순서

1. `SESSION_SUMMARY.md` (root) — 큰 그림 + Phase 진척
2. `docs/sessions/<latest>.md` — 직전 sub-phase 무엇을 했나
3. `plan/04_migration.md` § 4.3 — 전체 Phase 흐름
4. `git log --oneline -10` — 최근 commit 히스토리
5. 필요하면 `docs/sessions/` 의 이전 phase 요약들

## 관련

- **Auto-memory** (`spaces/.../memory/project_trsim_state.md`) — Cowork
  agent 가 자동 로드하는 빠른 상태 파일. 사람이 직접 읽기보다는 agent 용.
- **SESSION_SUMMARY.md** (root) — 큰 milestone (Phase 단위) 누적 로그.
- **`docs/sessions/`** (이 폴더) — sub-step 단위 디테일.
