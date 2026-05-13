# `docs/agent_workflows/` — Cowork agent 자주 호출하는 워크플로

slash skill 대신 markdown 워크플로 가이드. 사용자가 짧은 명령 ("phase 상태",
"sync 체크" 등) 만 하면 Cowork 가 해당 .md 파일 따라 단계 실행.

`CLAUDE.md` § 9 의 "사용자 명령 매핑" 표가 진입점.

## 현재 워크플로

- **[phase_status.md](phase_status.md)** — 현재 진행 상황 조회 + dashboard
  artifact 갱신. 매 세션 첫 진입 / sub-phase 끝마다 1회.
- **[sync_check.md](sync_check.md)** — 방금 Write 한 .py 의 bindfs 잘림 +
  lint 빠른 검사. 모듈 작성 직후 자동.
- **[ci_status.md](ci_status.md)** — `trsim-ci-status` scheduled task
  trigger. push 후 사용자가 결과 받을 때.
- **[mvp_status_update.md](mvp_status_update.md)** — `docs/MVP_STATUS.md`
  매트릭스 자동 갱신. 매 sub-step push 직후 + 사용자가 "다음 작업?",
  "남은 작업?", "MVP 상태?" 질문 시.

## 새 워크플로 추가

1. `docs/agent_workflows/<name>.md` 작성 (단계 + 보고 형식 명시)
2. `CLAUDE.md` § 9 표에 한 줄 추가: 명령 → .md 경로 → 짧은 설명
3. 첫 호출 후 효과 확인. 마찰 줄어들면 keep, 아니면 제거.

## 추가 후보

- `commit_phase.md` — git_sh/commit_phase<id>.sh 자동 생성
- `octave_run.md` — .m 짝꿍 실행 + 비교 (computer control)
- `decision_add.md` — DECISIONS.md 결정 append (ID 자동)
- `session_handoff.md` — phase 끝 docs/sessions/phase_<N>_<topic>.md 작성
  + CLAUDE.md § 1 갱신 + memory 업데이트
