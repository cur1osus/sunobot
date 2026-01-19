#!/usr/bin/env bash
set -euo pipefail

MSG="${1:-update}"

# 1. pre-commit через uv (только изменённые файлы)
uv run pre-commit run

# 2. stage → commit → push
git add -A

# если нет изменений — выходим без ошибки
if git diff --cached --quiet; then
  echo "Nothing to commit"
  exit 0
fi

git commit -m "$MSG"
git push
