#!/usr/bin/env bash
# TRsim — Git hook 활성화 (사용자 PC 에서 한 번만 실행).
#
# 사용법 (저장소 루트에서):
#   $ bash scripts/githooks/setup_hooks.sh

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

git config core.hooksPath scripts/githooks
chmod +x scripts/githooks/pre-commit 2>/dev/null || true

echo "[setup_hooks] core.hooksPath = scripts/githooks"
echo "[setup_hooks] pre-commit 활성화."
echo ""
echo "확인:"
git config --get core.hooksPath
echo ""
echo "bypass 가 필요하면: git commit --no-verify"
