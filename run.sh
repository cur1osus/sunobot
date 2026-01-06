#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env.dev}"

set -a
source "$ENV_FILE"
set +a

exec uv run -m bot
