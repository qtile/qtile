#!/usr/bin/env bash
# macos_check.sh — Proxy test runner for macOS backend fix agents (runs on Linux).
# Exit code 0 = all checks passed. Non-zero = at least one check failed.
#
# NOTE: This script is not yet integrated into CI (.github/workflows/ci.yml).
# To add CI coverage, create a new job that runs: bash scripts/macos_check.sh
#
# Runs:
#   1. mypy on the macos backend Python package
#   2. pytest on non-macOS tests and any Linux-runnable macos unit tests
#   3. ruff (or flake8 fallback) on the macos backend
#
# Must be run from the repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PASS=0
FAIL=0
FAILURES=()

run_check() {
    local name="$1"
    shift
    echo ""
    echo "=== $name ==="
    if "$@"; then
        echo "PASS: $name"
        (( PASS += 1 )) || true
    else
        echo "FAIL: $name (exit $?)"
        (( FAIL += 1 )) || true
        FAILURES+=("$name")
    fi
}

# --- 1. mypy: macos backend ---
run_check "mypy: macos backend" \
    "${REPO_ROOT}/../venv/bin/python" -m mypy \
        --ignore-missing-imports \
        --no-error-summary \
        libqtile/backend/macos/

# --- 2. mypy: base backend interfaces ---
run_check "mypy: base backend" \
    "${REPO_ROOT}/../venv/bin/python" -m mypy \
        --ignore-missing-imports \
        --no-error-summary \
        libqtile/backend/base/

# --- 3. pytest: non-platform unit tests ---
run_check "pytest: non-platform unit tests" \
    "${REPO_ROOT}/../venv/bin/python" -m pytest \
        test/ \
        -n auto \
        --ignore=test/backend/wayland \
        --ignore=test/backend/x11 \
        --ignore=test/backend/macos \
        --ignore=test/migrate \
        --ignore=test/shell_scripts \
        -x \
        -q \
        --tb=short \
        -m "not (wayland or x11 or darwin)"

# --- 4. pytest: macos unit tests that are Linux-runnable ---
if ls test/backend/macos/test_unit_*.py > /dev/null 2>&1; then
    run_check "pytest: macos unit tests (Linux-runnable)" \
        "${REPO_ROOT}/../venv/bin/python" -m pytest \
            test/backend/macos/ \
            -k test_unit_ \
            -x \
            -q \
            --tb=short
else
    echo ""
    echo "=== pytest: macos unit tests ==="
    echo "SKIP: no test/backend/macos/test_unit_*.py files found yet"
fi

# --- 5. ruff / flake8 ---
if command -v ruff > /dev/null 2>&1; then
    run_check "ruff: macos backend" \
        ruff check libqtile/backend/macos/
elif command -v flake8 > /dev/null 2>&1; then
    run_check "flake8: macos backend" \
        flake8 libqtile/backend/macos/ --max-line-length=100
else
    echo ""
    echo "=== lint ==="
    echo "SKIP: neither ruff nor flake8 found in PATH"
fi

# --- Summary ---
echo ""
echo "========================================"
echo "Results: $PASS passed, $FAIL failed"
if (( FAIL > 0 )); then
    echo "Failed checks:"
    for f in "${FAILURES[@]}"; do
        echo "  - $f"
    done
    echo "========================================"
    exit 1
fi
echo "All checks passed."
echo "========================================"
exit 0
