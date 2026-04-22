#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

require_core_commands
print_info "Killing default service ports for aiDaptive Benchmark Suite"
kill_pid_file_if_running

for port in "${SERVICE_PORTS[@]}"; do
  kill_port_if_busy "$port"
done

print_ok "Done. Default service ports checked: ${SERVICE_PORTS[*]}"
