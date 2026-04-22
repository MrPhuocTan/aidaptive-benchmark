#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

print_info "Clearing Python and frontend-related cache directories"

find "$PROJECT_ROOT" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$PROJECT_ROOT" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

rm -rf \
  "$PROJECT_ROOT/.pytest_cache" \
  "$PROJECT_ROOT/.mypy_cache" \
  "$PROJECT_ROOT/.ruff_cache" \
  "$PROJECT_ROOT/htmlcov" \
  "$PROJECT_ROOT/.coverage" \
  "$PROJECT_ROOT/.vite" \
  "$PROJECT_ROOT/dist" \
  "$PROJECT_ROOT/build" \
  "$PROJECT_ROOT/node_modules/.cache" \
  "$PROJECT_ROOT/static/.cache"

rm -f "$APP_LOG_FILE" "$PID_FILE" "$PORT_FILE"

print_ok "Cache cleanup completed."
