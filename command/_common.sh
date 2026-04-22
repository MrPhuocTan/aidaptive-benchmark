#!/bin/bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$LOG_DIR/app.pid"
APP_LOG_FILE="$LOG_DIR/app.log"
PORT_FILE="$LOG_DIR/app.port"

DEFAULT_APP_PORT="8443"
SERVICE_PORTS=(8443 3000 5432 8086 11434 9100)

mkdir -p "$LOG_DIR"

purple='\033[0;35m'
white='\033[1;37m'
yellow='\033[1;33m'
green='\033[0;32m'
red='\033[0;31m'
nc='\033[0m'

print_info() {
  echo -e "${white}$1${nc}"
}

print_warn() {
  echo -e "${yellow}$1${nc}"
}

print_ok() {
  echo -e "${green}$1${nc}"
}

print_err() {
  echo -e "${red}$1${nc}"
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

require_core_commands() {
  local missing=()
  for cmd in awk curl; do
    if ! has_command "$cmd"; then
      missing+=("$cmd")
    fi
  done

  if ! has_command lsof; then
    missing+=("lsof")
  fi

  if (( ${#missing[@]} > 0 )); then
    print_err "Missing required commands: ${missing[*]}"
    exit 1
  fi
}

resolve_compose_cmd() {
  if has_command docker && docker compose version >/dev/null 2>&1; then
    echo "docker compose"
    return 0
  fi

  if has_command docker-compose; then
    echo "docker-compose"
    return 0
  fi

  return 1
}

docker_daemon_ready() {
  if ! has_command docker; then
    return 1
  fi

  docker info >/dev/null 2>&1
}

docker_desktop_running() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    return 1
  fi

  pgrep -x "Docker" >/dev/null 2>&1 || pgrep -f "/Applications/Docker.app" >/dev/null 2>&1
}

open_docker_desktop() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    return 1
  fi

  if ! has_command open; then
    return 1
  fi

  print_warn "Docker daemon is not running. Launching Docker Desktop..."
  open -a Docker >/dev/null 2>&1 || return 1
  return 0
}

wait_for_docker_daemon() {
  local timeout_seconds="${1:-90}"
  local elapsed=0

  while (( elapsed < timeout_seconds )); do
    if docker_daemon_ready; then
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done

  return 1
}

resolve_python() {
  if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    echo "$PROJECT_ROOT/.venv/bin/python"
  elif has_command python3; then
    command -v python3
  else
    print_err "Python runtime not found. Create .venv or install python3 first."
    exit 1
  fi
}

detect_app_port() {
  local configured
  configured="$(awk -F': *' '
    $1 ~ /^app$/ { in_app=1; next }
    in_app && $1 ~ /^  port$/ { gsub(/"/, "", $2); print $2; exit }
    /^[^ ]/ && $1 !~ /^app$/ { in_app=0 }
  ' "$PROJECT_ROOT/benchmark.yaml" 2>/dev/null || true)"

  if [[ -n "${configured:-}" ]]; then
    echo "$configured"
  else
    echo "$DEFAULT_APP_PORT"
  fi
}

is_port_busy() {
  local port="$1"
  lsof -ti tcp:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

next_available_port() {
  local start_port="${1:-8443}"
  local max_port="${2:-8500}"
  local port="$start_port"

  while (( port <= max_port )); do
    if ! is_port_busy "$port"; then
      echo "$port"
      return 0
    fi
    port=$((port + 1))
  done

  return 1
}

kill_port_if_busy() {
  local port="$1"
  local pids

  pids="$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    return 0
  fi

  print_warn "Port $port is busy. Stopping process(es): $pids"
  kill $pids 2>/dev/null || true
  sleep 1

  pids="$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    print_warn "Force killing remaining process(es) on port $port: $pids"
    kill -9 $pids 2>/dev/null || true
    sleep 1
  fi
}

kill_pid_file_if_running() {
  if [[ ! -f "$PID_FILE" ]]; then
    return 0
  fi

  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    print_warn "Stopping tracked app pid: $pid"
    kill "$pid" 2>/dev/null || true
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
      print_warn "Force killing tracked app pid: $pid"
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi

  rm -f "$PID_FILE" "$PORT_FILE"
}

wait_for_tcp_port() {
  local port="$1"
  local timeout_seconds="${2:-30}"
  local elapsed=0

  while (( elapsed < timeout_seconds )); do
    if has_command nc && nc -z localhost "$port" >/dev/null 2>&1; then
      return 0
    fi
    if is_port_busy "$port"; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  return 1
}

wait_for_http_health() {
  local url="$1"
  local timeout_seconds="${2:-30}"
  local elapsed=0

  while (( elapsed < timeout_seconds )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  return 1
}

ensure_support_services() {
  local compose_cmd
  if ! compose_cmd="$(resolve_compose_cmd)"; then
    print_warn "Docker Compose not found. Skipping PostgreSQL startup."
    return 0
  fi

  if ! docker_daemon_ready; then
    if docker_desktop_running; then
      print_warn "Docker Desktop is already open. Waiting for daemon to become ready..."
    else
      if ! open_docker_desktop; then
        print_warn "Unable to launch Docker Desktop automatically."
        print_warn "Start Docker Desktop first if you want local database services."
        return 0
      fi
    fi

    print_info "Waiting for Docker daemon to become ready..."
    if ! wait_for_docker_daemon 120; then
      print_warn "Docker daemon is still not ready. Continuing with app startup only."
      return 0
    fi

    print_ok "Docker daemon is ready"
  fi

  print_info "Starting support services with $compose_cmd"
  if ! (
    cd "$PROJECT_ROOT"
    $compose_cmd up -d postgres
  ); then
    print_warn "Failed to start Docker services. Continuing with app startup only."
    return 0
  fi

  if wait_for_tcp_port 5432 40; then
    print_ok "PostgreSQL is ready on port 5432"
  else
    print_warn "PostgreSQL did not become ready in time"
  fi

}

open_log_terminal_tab() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    if has_command x-terminal-emulator; then
      x-terminal-emulator -e "bash -lc 'printf \"\\n--- aiDaptive log tail ---\\n\"; tail -n 200 -f \"$APP_LOG_FILE\"'" >/dev/null 2>&1 &
    elif has_command gnome-terminal; then
      gnome-terminal -- bash -lc "printf '\n--- aiDaptive log tail ---\n'; tail -n 200 -f \"$APP_LOG_FILE\"; exec bash" >/dev/null 2>&1 &
    elif has_command xterm; then
      xterm -e "printf '\n--- aiDaptive log tail ---\n'; tail -n 200 -f \"$APP_LOG_FILE\"" >/dev/null 2>&1 &
    fi
    return 0
  fi

  if ! has_command osascript; then
    return 0
  fi

  local escaped_root escaped_log
  escaped_root="${PROJECT_ROOT//\"/\\\"}"
  escaped_log="${APP_LOG_FILE//\"/\\\"}"

  osascript >/dev/null 2>&1 <<EOF || true
tell application "Terminal"
  activate
  do script "cd \"$escaped_root\"; printf '\\n--- aiDaptive log tail ---\\n'; tail -n 200 -f \"$escaped_log\""
end tell
EOF
}

open_app_in_browser() {
  local port="$1"
  local url="http://localhost:$port"

  if [[ "$(uname -s)" == "Darwin" ]] && has_command open; then
    open "$url" >/dev/null 2>&1 || true
    return 0
  fi

  if has_command xdg-open; then
    xdg-open "$url" >/dev/null 2>&1 || true
  fi
}

start_app_background() {
  local python_bin app_port requested_port
  python_bin="$(resolve_python)"
  requested_port="$(detect_app_port)"
  app_port="$requested_port"

  if is_port_busy "$app_port"; then
    print_warn "Requested app port $app_port is still busy after cleanup."
    if app_port="$(next_available_port "$((requested_port + 1))")"; then
      print_warn "Switching app startup to fallback port $app_port"
    else
      print_err "No free fallback port found near $requested_port"
      exit 1
    fi
  fi

  print_info "Starting app on port $app_port"
  : >"$APP_LOG_FILE"
  echo "$app_port" >"$PORT_FILE"
  (
    cd "$PROJECT_ROOT"
    AIDAPTIVE_APP_PORT="$app_port" nohup "$python_bin" -m src >"$APP_LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
  )

  sleep 3

  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE")"
    if kill -0 "$pid" 2>/dev/null; then
      if wait_for_http_health "http://localhost:$app_port/api/health" 30; then
        print_ok "App started. PID: $pid"
        print_info "Log file: $APP_LOG_FILE"
        print_info "URL: http://localhost:$app_port"
        open_log_terminal_tab
        open_app_in_browser "$app_port"
        return 0
      fi
    fi
  fi

  print_err "App failed to start. Check log: $APP_LOG_FILE"
  exit 1
}
