# scripts/githooks/

TRsim 저장소-내장 Git hook. 사용자가 한 번 활성화하면 매 commit 마다 자동.

## 활성화 (한 번만)

```bash
cd "/c/Workspaces/Claude/Tracking Radar Simulator/trsim"
bash scripts/githooks/setup_hooks.sh
```

또는 직접:

```bash
git config core.hooksPath scripts/githooks
```

## pre-commit 가 검사하는 것

1. **bindfs truncation** — staged 된 모든 `.py` 파일을 `python -m py_compile`
   로 syntax 검사. 실패하면 commit 거부 + tail 출력. Cowork ↔ Windows mount
   sync 잘림이 자주 발생하는 패턴 대응.
2. **ruff check** — lint 위반 (RUF002 ASCII-confusable, SIM300 Yoda,
   RUF043 regex meta, I001 import 순서 등).
3. **ruff format --check** — 포매팅 미적용 검출.

## bypass

긴급 시 hook 우회:

```bash
git commit --no-verify -s -m "WIP"
```

남용 금지 — bypass 하면 CI 에서 잡힘.

## 확장

새로운 검사 추가 시 `pre-commit` 의 `--- N. ...` 섹션으로 append.
mypy strict 는 시간이 걸려서 hook 에 안 넣음 — CI 가 잡음.
