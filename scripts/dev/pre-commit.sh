#!/usr/bin/env bash
# Git pre-commit hook: everything `make check` runs except the test suite,
# in about fifteen seconds. The tests take ten minutes and run in CI.
# Installed by `make hooks`; skip once with `git commit --no-verify`.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
exec make --no-print-directory quick
