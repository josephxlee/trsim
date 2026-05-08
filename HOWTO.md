# HOWTO — Cowork 에서 Claude Code (VS Code) 로 옮기기

이 문서는 TRsim 작업 환경을 **Cowork desktop** 에서 **Claude Code (CLI / VS Code 통합)** 으로 이전하는 절차. 핵심 자산 (코드 / plan / 메모리 / 워크플로) 은 그대로 살리되, Cowork 특화 한계 (bindfs sync, sandbox network 차단, Octave 자동화 어려움 등) 를 제거.

---

## 0. 사전 준비

이미 가지고 있는 것 (사용자 PC):
- Python 3.12 / 3.13
- Git Bash + git config (user.name=joseph, email=huvluv14@gmail.com, credential helper)
- GNU Octave 11.1.0 (CLI / GUI)
- Visual Studio Code
- Node.js (Claude Code 설치에 필요)
- 저장소 `C:\Workspaces\Claude\Tracking Radar Simulator\trsim` (이미 GitHub push 끝남)

새로 필요한 것:
- **Claude Code** (npm 패키지)

---

## 1. Claude Code 설치

PowerShell 또는 Git Bash 에서:

```bash
npm install -g @anthropic-ai/claude-code
claude --version    # 설치 확인
```

설치 후 첫 실행 시 인증 — 브라우저에서 Anthropic 계정 로그인. 토큰은 사용자 홈에 저장 (한 번만).

---

## 2. VS Code 통합

### 2.1 권장 — VS Code 안에서 Claude Code 사용

1. VS Code 로 저장소 열기:
   ```bash
   code "C:\Workspaces\Claude\Tracking Radar Simulator\trsim"
   ```
2. 통합 터미널 열기 (`` Ctrl+` ``).
3. 터미널에서 `claude` 입력 → 대화형 세션 시작.

VS Code 의 파일 탐색기 + Git 패널 + 터미널 + Claude Code 가 한 창에 공존. 파일 수정은 Claude 가 직접 하고, diff 는 VS Code 의 Git 패널에서 시각적으로 확인.

### 2.2 (옵션) Claude Code IDE extension

Anthropic 가 공식 VS Code extension 을 제공하면 marketplace 에서 "Claude Code" 검색 후 설치 — 사이드바에 Claude 패널이 추가되어 채팅 + diff preview 가 통합. 없으면 위 2.1 방식만.

---

## 3. 첫 세션 진입

저장소 루트에서 `claude` 실행하면 자동으로 다음 파일이 로드됨:

- `CLAUDE.md` (이 저장소 루트에 이미 있음) — Cowork 구현 단계 작업 규약
- 사용자가 `--resume` 같은 플래그로 이전 세션 이어가기 가능

첫 명령으로:
```
"phase 상태"
```

`docs/agent_workflows/phase_status.md` 따라 현재 진행 상황 보고. 또는:
```
"본 작업 진행하자"
```
→ 다음 sub-phase 자동 진입.

---

## 4. Cowork 자산이 어디로 가나

| Cowork 자산 | Claude Code 에서 |
|---|---|
| `CLAUDE.md` (repo 루트) | **그대로** — 자동 로드 |
| `AGENT_GUIDE.md` / `DECISIONS.md` / `SESSION_SUMMARY.md` / `ROADMAP.md` | **그대로** |
| `docs/sessions/` | **그대로** |
| `docs/agent_workflows/` (phase_status / sync_check / ci_status) | **그대로** — 트리거 매핑 동일 |
| `scripts/githooks/` (pre-commit + setup_hooks.sh) | **그대로** — `bash scripts/githooks/setup_hooks.sh` 한 번 |
| `git_sh/commit_*.sh` | **그대로**, 단 Claude Code 가 직접 git 호출하므로 사용 빈도 낮음 |
| `docs/matlab_validation/test_*.m` | **그대로** |
| `scripts/run_octave_validation.sh` | **그대로**, 이제 Claude 가 직접 호출 가능 |
| Cowork 의 `phase dashboard artifact` | **잃음** (CLI 환경) — 대신 markdown / TUI table |
| Cowork 의 `trsim-ci-status` scheduled task | **잃음** — 대신 Claude 가 직접 `gh run list` 또는 `curl api.github.com` 즉시 |
| Cowork auto-memory (`spaces/.../memory/`) | **잃음** — 대신 `CLAUDE.md` 가 항상 로드됨. 추가로 `~/.claude/CLAUDE.md` (사용자 전역) 활용 가능 |

---

## 5. Workflow 차이 — 무엇이 자동으로 되나

### 5.1 Cowork 에서 막혔던 것 → Claude Code 에서

- **bindfs sync truncation 트랩** — 사라짐 (mount 없음, 직접 fs).
- **git push 인증** — 사용자 git config + credential helper 그대로 → 자동 push.
- **api.github.com 차단** — 차단 없음. Claude 가 `curl api.github.com/...` 또는 `gh run list` 즉시.
- **Octave 자동 실행** — `bash scripts/run_octave_validation.sh test_atmosphere` 한 줄. stdout 즉시 회수, mask 없음.
- **terminal mask / GUI mask** — 해당 없음.

### 5.2 Claude Code 표준 워크플로

매 sub-phase 끝:
```
1. Claude 가 모듈 + pytest + (필요 시) .m 짝꿍 작성
2. ruff check + ruff format (Claude 가 직접 실행)
3. pytest -q (로컬 즉시 — CI 기다릴 필요 X)
4. Octave 짝꿍 검증 (Claude 가 직접 실행)
5. git add + commit -s + push (Claude 가 직접)
6. CI 결과 polling (Claude 가 직접 gh run watch)
7. docs/sessions/phase_<N>_<topic>.md 작성
```

대부분 사용자 개입 없이 진행. 사용자는 큰 결정만.

---

## 6. 첫 세션 마이그레이션 체크리스트

순서대로:

```bash
# (1) 저장소 루트로
cd "/c/Workspaces/Claude/Tracking Radar Simulator/trsim"

# (2) Claude Code 설치 (한 번만)
npm install -g @anthropic-ai/claude-code

# (3) pre-commit hook 활성화 (한 번만)
bash scripts/githooks/setup_hooks.sh

# (4) GitHub CLI (선택, 권장 — Claude 가 PR / CI 직접 다룸)
winget install --id GitHub.cli   # 또는 https://cli.github.com
gh auth login

# (5) Python 환경 확인
python --version
pip install -r requirements-dev.txt   # 또는 uv sync (있으면)

# (6) 빠른 sanity check
ruff check .
ruff format --check .
pytest -q

# (7) VS Code 열기 + Claude Code 시작
code .
# VS Code 통합 터미널에서:
claude
```

첫 메시지로 `"phase 상태"` 또는 `"본 작업 이어가자"` — 자동으로 SESSION_SUMMARY.md / docs/sessions/ 최신 .md 읽고 다음 sub-phase 진행.

---

## 7. 트러블슈팅

### 7.1 `claude` 가 CLAUDE.md 를 못 읽는 듯

저장소 루트에서 실행했는지 확인. `claude` 는 cwd 의 `CLAUDE.md` 를 자동 로드. 또는 명시:
```
"먼저 CLAUDE.md 읽고 시작해"
```

### 7.2 push 가 prompt 로 password 묻는다

Windows credential manager 가 GitHub 토큰 만료. Git Bash 에서:
```bash
git config --global credential.helper manager-core
```
첫 push 시 GitHub 로그인 창. 그 후 자동.

### 7.3 Octave 가 PATH 에 없다

`scripts/run_octave_validation.sh` 가 `C:\Octave\Octave-11.1.0\mingw64\bin\octave-cli.exe` 자동 탐색. 다른 위치 설치면 스크립트의 `for cand in ...` 블록에 경로 추가.

### 7.4 ruff 또는 pytest 가 없다

```bash
pip install ruff pytest pytest-cov
```
또는 프로젝트 dev extras 설치:
```bash
pip install -e ".[dev]"
```

### 7.5 `gh` 없이 CI 결과 보기

```bash
curl -s "https://api.github.com/repos/josephxlee/trsim/actions/runs?per_page=3" \
  | python -m json.tool
```
Claude 한테 "ci 결과" 한 마디 → 알아서 호출 + 6 환경 matrix 정리.

---

## 8. Cowork 로 다시 돌아오고 싶으면

저장소는 같으니 그냥 Cowork 열고 같은 폴더 선택. `CLAUDE.md` 가 자동 로드되어 컨벤션 그대로. Cowork 의 phase dashboard artifact 만 다시 갱신 (한 번 호출하면 됨).

두 환경 병행 가능 — 다만 같은 시점에 양쪽이 git 건드리면 conflict 위험. 한 번에 한 환경.

---

## 9. 권장 사용 패턴

- **TRsim 같은 코드 중심 작업** → Claude Code (속도 + 직접 git/CI/Octave)
- **외부 산출물 (보고서 / 슬라이드 / 시각화 dashboard)** → Cowork (artifact + 컴퓨터 컨트롤)
- **둘 다 필요한 워크플로** → Claude Code 메인 + Cowork 는 발표/시연용 dashboard 갱신만

---

작성: 2026-05-08 — Phase 2.6 시점 마이그레이션 가이드.
