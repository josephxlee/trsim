#!/usr/bin/env bash
# TRsim — Octave .m cross-validation 실행기.
#
# 사용법:
#   $ bash scripts/run_octave_validation.sh test_geometry
#   $ bash scripts/run_octave_validation.sh all   # 모든 .m 순차 실행
#
# 사용자 PC 의 GNU Octave (octave-cli) 가 PATH 에 있어야 함.
# Windows 표준 설치 시 PATH:
#   C:\Octave\Octave-11.1.0\mingw64\bin
# Git Bash 에서 작동하도록 PATH 자동 보정.

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# octave-cli 위치 자동 탐색 (Windows 표준 설치)
if ! command -v octave-cli >/dev/null 2>&1; then
    for cand in \
        "/c/Octave/Octave-11.1.0/mingw64/bin/octave-cli.exe" \
        "/c/Octave/Octave-10.1.0/mingw64/bin/octave-cli.exe" \
        "/c/Octave/Octave-9.2.0/mingw64/bin/octave-cli.exe" \
        "$(ls -d /c/Octave/Octave-*/mingw64/bin/octave-cli.exe 2>/dev/null | head -1)"; do
        if [ -x "$cand" ]; then
            export PATH="$(dirname "$cand"):$PATH"
            echo "[octave-run] PATH +=$(dirname "$cand")"
            break
        fi
    done
fi

if ! command -v octave-cli >/dev/null 2>&1; then
    echo "ERROR: octave-cli 못 찾음. PATH 또는 설치 확인."
    echo "  - Windows: https://octave.org/download → mingw64 installer"
    echo "  - macOS: brew install octave"
    echo "  - Linux: apt install octave"
    exit 1
fi

NAME="${1:-}"
if [ -z "$NAME" ]; then
    echo "사용법: bash scripts/run_octave_validation.sh <test_name>"
    echo ""
    echo "사용 가능:"
    ls -1 docs/matlab_validation/test_*.m 2>/dev/null | sed 's|docs/matlab_validation/||; s|\.m$||; s|^|  - |'
    echo "  - all   (모든 test_*.m 순차 실행)"
    exit 1
fi

if [ "$NAME" = "all" ]; then
    for m in docs/matlab_validation/test_*.m; do
        n="$(basename "$m" .m)"
        echo "===== $n ====="
        octave-cli --no-gui --silent --eval "addpath('docs/matlab_validation'); $n; quit" \
            || echo "[!] $n FAIL"
        echo ""
    done
else
    SCRIPT="docs/matlab_validation/${NAME}.m"
    if [ ! -f "$SCRIPT" ]; then
        echo "ERROR: $SCRIPT 없음."
        exit 1
    fi
    echo "===== $NAME ====="
    octave-cli --no-gui --silent --eval "addpath('docs/matlab_validation'); $NAME; quit"
fi
