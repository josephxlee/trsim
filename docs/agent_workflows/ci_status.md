# ci_status — CI 결과 조회 trigger

호출 trigger: "ci 결과", "ci 상태", "ci 봐줘", push 직후

## 옵션 1 — scheduled task 호출 (권장)

`trsim-ci-status` 가 이미 등록됨 (`mcp__scheduled-tasks__create_scheduled_task`
로 ad-hoc 생성). 호출 방식:

- 사용자가 사이드바 "Scheduled" → "Run now" 클릭
- 또는 cowork 가 task 의 trigger API 사용 (현재 schedule 도구가 trigger
  엔드포인트 직접 노출 안 함 — 현재는 manual)

task 가 실행되면 자동으로:
1. GitHub Actions API 로 최근 3 run 조회
2. `docs/sessions/_ci_log.md` 한 줄 append
3. 6 환경 matrix 결과 + commit msg 보고

## 옵션 2 — Cowork sandbox 에서 직접 (즉시)

scheduled task 안 거치고 곧바로:

```bash
curl -s "https://api.github.com/repos/josephxlee/trsim/actions/runs?per_page=3" \
  -H "Accept: application/vnd.github+json"
```

- 가장 최근 run 의 `status` / `conclusion` 추출
- `completed` 이면 jobs 조회 → 6 환경 matrix
- `in_progress` 이면 "N분 경과, 다시 시도" 보고

## 보고 형식

```
Phase 2.3c CI 6/6 PASS
sha: abc1234 — "Phase 2.3c: domain/building.py — ..."
run: https://github.com/josephxlee/trsim/actions/runs/<id>
```

또는:

```
Phase 2.3c CI in_progress (5분 경과)
ETA ~3-5분 더. 다시 ci 봐줘.
```

또는:

```
Phase 2.3c CI 5/6 — Windows / Py 3.12 FAIL
첫 에러: tests/unit/domain/test_building.py:42 AssertionError
docs/sessions/_ci_log.md 에 기록함.
```

## 누적 로그

`docs/sessions/_ci_log.md` 형식:

```
| 시각 (KST) | sha | branch | conclusion | 6env | commit msg |
|---|---|---|---|---|---|
| 2026-05-08 14:32 | abc1234 | main | success | 6/6 | Phase 2.3c: ... |
```

새 세션 진입 시 마지막 줄 한 번만 보면 push-CI 흐름 따라잡음.
