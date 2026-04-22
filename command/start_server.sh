#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

require_core_commands
APP_PORT="$(detect_app_port)"

print_info "Preparing to start aiDaptive Benchmark Suite"
kill_pid_file_if_running
kill_port_if_busy "$APP_PORT"
ensure_support_services
start_app_background
