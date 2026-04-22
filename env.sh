#!/bin/bash
# ============================================================================
#  aiDaptive Benchmark Suite - Environment Setup Script
#  Chuẩn bị môi trường cho máy chủ Controller (chạy app benchmark)
#  và máy chủ Target (máy chủ AI đang được đánh giá).
#
#  Cách dùng:
#    chmod +x env.sh
#    ./env.sh controller    # Cài đặt trên máy chạy app benchmark
#    ./env.sh target        # Cài đặt trên máy chủ AI đích
#    ./env.sh all           # Cài cả hai (nếu chạy trên cùng 1 máy)
# ============================================================================

set -euo pipefail

# ---- Colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

info()  { echo -e "${WHITE}[INFO]  $1${NC}"; }
ok()    { echo -e "${GREEN}[OK]    $1${NC}"; }
warn()  { echo -e "${YELLOW}[WARN]  $1${NC}"; }
err()   { echo -e "${RED}[ERROR] $1${NC}"; }
step()  { echo -e "\n${CYAN}==== $1 ====${NC}"; }

has_cmd() { command -v "$1" >/dev/null 2>&1; }

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        echo "$ID"
    elif [[ "$(uname -s)" == "Darwin" ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

detect_arch() {
    local arch
    arch="$(uname -m)"
    case "$arch" in
        x86_64)  echo "amd64" ;;
        aarch64) echo "arm64" ;;
        arm64)   echo "arm64" ;;
        *)       echo "$arch" ;;
    esac
}

OS="$(detect_os)"
ARCH="$(detect_arch)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ============================================================================
# SECTION 1: Controller Machine Setup
# Cài đặt các công cụ benchmark trên máy chạy app aiDaptive
# ============================================================================
setup_controller() {
    step "Setting up CONTROLLER environment"
    info "OS: $OS | Arch: $ARCH"

    # ---- 1. Python ----
    step "1/7 - Python 3.10+"
    if has_cmd python3; then
        local pyver
        pyver="$(python3 --version 2>&1)"
        ok "Python found: $pyver"
    else
        err "Python3 not found. Please install Python 3.10+ first."
        exit 1
    fi

    # ---- 2. Python venv & Dependencies ----
    step "2/7 - Python Dependencies (requirements.txt)"
    if [[ -f "$SCRIPT_DIR/requirements.txt" ]]; then
        if [[ -d "$SCRIPT_DIR/.venv" ]]; then
            info "Virtual environment found at .venv"
            source "$SCRIPT_DIR/.venv/bin/activate" 2>/dev/null || true
        else
            info "Creating virtual environment..."
            python3 -m venv "$SCRIPT_DIR/.venv"
            source "$SCRIPT_DIR/.venv/bin/activate"
            ok "Virtual environment created"
        fi
        info "Installing Python dependencies..."
        pip install --upgrade pip -q
        pip install -r "$SCRIPT_DIR/requirements.txt" -q
        ok "Python dependencies installed (litellm, locust, etc.)"
    else
        warn "requirements.txt not found, skipping Python deps"
    fi

    # ---- 3. k6 ----
    step "3/7 - k6 (Grafana Load Testing)"
    if has_cmd k6; then
        ok "k6 already installed: $(k6 version 2>&1 | head -1)"
    else
        info "Installing k6..."
        case "$OS" in
            macos)
                if has_cmd brew; then
                    brew install k6
                else
                    err "Homebrew not found. Install k6 manually: https://k6.io/docs/getting-started/installation/"
                    warn "Skipping k6 installation"
                fi
                ;;
            ubuntu|debian)
                sudo gpg -k >/dev/null 2>&1 || true
                sudo gpg --no-default-keyring \
                    --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
                    --keyserver hkp://keyserver.ubuntu.com:80 \
                    --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D68 2>/dev/null
                echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
                    | sudo tee /etc/apt/sources.list.d/k6.list >/dev/null
                sudo apt-get update -qq
                sudo apt-get install -y k6
                ;;
            centos|rhel|fedora)
                sudo dnf install -y https://dl.k6.io/rpm/repo.rpm 2>/dev/null || true
                sudo dnf install -y k6
                ;;
            *)
                warn "Unsupported OS for k6 auto-install. Install manually: https://k6.io"
                ;;
        esac
        has_cmd k6 && ok "k6 installed successfully" || warn "k6 installation failed"
    fi

    # ---- 4. oha ----
    step "4/7 - oha (HTTP Load Generator)"
    if has_cmd oha; then
        ok "oha already installed: $(oha --version 2>&1 | head -1)"
    else
        info "Installing oha..."
        case "$OS" in
            macos)
                if has_cmd brew; then
                    brew install oha
                else
                    warn "Homebrew not found. Install oha manually: https://github.com/hatoo/oha"
                fi
                ;;
            ubuntu|debian|centos|rhel|fedora)
                local oha_arch="amd64"
                [[ "$ARCH" == "arm64" ]] && oha_arch="aarch64"
                local oha_url="https://github.com/hatoo/oha/releases/latest/download/oha-linux-${oha_arch}"
                info "Downloading oha from $oha_url ..."
                if curl -fsSL "$oha_url" -o /tmp/oha; then
                    sudo mv /tmp/oha /usr/local/bin/oha
                    sudo chmod +x /usr/local/bin/oha
                    ok "oha installed to /usr/local/bin/oha"
                else
                    warn "oha download failed. Install manually: https://github.com/hatoo/oha"
                fi
                ;;
            *)
                warn "Unsupported OS for oha auto-install."
                ;;
        esac
        has_cmd oha && ok "oha installed successfully" || warn "oha installation failed"
    fi

    # ---- 5. Docker & Docker Compose ----
    step "5/7 - Docker & Docker Compose (PostgreSQL, InfluxDB, Grafana)"
    if has_cmd docker; then
        ok "Docker found: $(docker --version 2>&1)"
        if docker compose version >/dev/null 2>&1; then
            ok "Docker Compose found: $(docker compose version 2>&1)"
        elif has_cmd docker-compose; then
            ok "docker-compose (legacy) found"
        else
            warn "Docker Compose not found. Required for database services."
        fi
    else
        warn "Docker not installed. Required for PostgreSQL, InfluxDB, and Grafana."
        info "Install Docker: https://docs.docker.com/get-docker/"
    fi

    # ---- 6. LLMPerf (Optional) ----
    step "6/7 - LLMPerf (Optional - Anyscale LLM Benchmark)"
    if python3 -c "import llmperf" 2>/dev/null; then
        ok "llmperf already installed"
    else
        warn "llmperf is NOT installed."
        info "llmperf requires Ray and is heavy. Install if needed:"
        info "  pip install llmperf"
        info "Or skip - the system will automatically skip this tool."
    fi

    # ---- 7. Verification ----
    step "7/7 - Verification Summary"
    echo ""
    echo "  Controller Tool Status:"
    echo "  ────────────────────────────────────────"
    printf "  %-20s %s\n" "Python3"       "$(has_cmd python3  && echo '✓ OK' || echo '✗ MISSING')"
    printf "  %-20s %s\n" "k6"            "$(has_cmd k6       && echo '✓ OK' || echo '✗ MISSING')"
    printf "  %-20s %s\n" "oha"           "$(has_cmd oha      && echo '✓ OK' || echo '✗ MISSING')"
    printf "  %-20s %s\n" "locust"        "$(has_cmd locust   && echo '✓ OK' || echo '✗ MISSING')"
    printf "  %-20s %s\n" "litellm"       "$(python3 -c 'import litellm' 2>/dev/null && echo '✓ OK' || echo '✗ MISSING')"
    printf "  %-20s %s\n" "llmperf"       "$(python3 -c 'import llmperf' 2>/dev/null && echo '✓ OK (optional)' || echo '~ SKIPPED (optional)')"
    printf "  %-20s %s\n" "Docker"        "$(has_cmd docker   && echo '✓ OK' || echo '✗ MISSING')"
    echo "  ────────────────────────────────────────"
    echo ""
}

# ============================================================================
# SECTION 2: Target AI Server Setup
# Cài đặt Ollama và Agent trên máy chủ AI đang bị đánh giá
# ============================================================================
setup_target() {
    step "Setting up TARGET AI SERVER environment"
    info "OS: $OS | Arch: $ARCH"

    # ---- 1. System Dependencies ----
    step "1/5 - System Dependencies"
    case "$OS" in
        ubuntu|debian)
            info "Installing system packages..."
            sudo apt-get update -qq
            sudo apt-get install -y -qq curl wget lsof net-tools python3 python3-pip >/dev/null
            ok "System packages installed"
            ;;
        centos|rhel|fedora)
            info "Installing system packages..."
            sudo dnf install -y curl wget lsof net-tools python3 python3-pip >/dev/null
            ok "System packages installed"
            ;;
        macos)
            ok "macOS - system tools already available"
            ;;
        *)
            warn "Unknown OS. Please install: curl, wget, python3, lsof manually."
            ;;
    esac

    # ---- 2. NVIDIA Drivers & CUDA (GPU) ----
    step "2/5 - NVIDIA GPU Drivers"
    if has_cmd nvidia-smi; then
        ok "NVIDIA driver found:"
        nvidia-smi --query-gpu=gpu_name,driver_version,memory.total --format=csv,noheader 2>/dev/null || true
    else
        warn "nvidia-smi not found. GPU benchmarking requires NVIDIA drivers."
        info "Install guide: https://docs.nvidia.com/datacenter/tesla/tesla-installation-notes/"
    fi

    # ---- 3. Ollama ----
    step "3/5 - Ollama (LLM Inference Server)"
    if has_cmd ollama; then
        ok "Ollama found: $(ollama --version 2>&1)"
        info "Checking Ollama service status..."
        if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
            ok "Ollama service is running on port 11434"
            info "Loaded models:"
            curl -sf http://localhost:11434/api/tags 2>/dev/null \
                | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    print(f\"  - {m['name']} ({m.get('size', 'unknown')} bytes)\")
" 2>/dev/null || true
        else
            warn "Ollama is installed but service is NOT running."
            info "Start it with: ollama serve"
        fi
    else
        info "Installing Ollama..."
        if curl -fsSL https://ollama.com/install.sh | sh; then
            ok "Ollama installed successfully"
        else
            err "Failed to install Ollama. Try manually: https://ollama.com/download"
        fi
    fi

    # ---- 4. Pull Benchmark Model ----
    step "4/5 - Benchmark Model"
    local MODEL="llama3.2:latest"
    if has_cmd ollama; then
        if curl -sf http://localhost:11434/api/tags 2>/dev/null | python3 -c "
import sys, json
models = [m['name'] for m in json.load(sys.stdin).get('models', [])]
sys.exit(0 if any('llama3.2' in m for m in models) else 1)
" 2>/dev/null; then
            ok "Benchmark model (llama3.2) is already loaded"
        else
            info "Pulling benchmark model: $MODEL ..."
            info "(This may take several minutes depending on network speed)"
            ollama pull "$MODEL" && ok "Model pulled successfully" || warn "Model pull failed"
        fi
    else
        warn "Ollama not available, cannot pull model"
    fi

    # ---- 5. Monitoring Agent ----
    step "5/5 - Monitoring Agent (Port 9100)"
    info "The benchmark controller connects to port 9100 on this server"
    info "to collect hardware metrics (GPU, CPU, RAM, Temperature)."
    echo ""
    info "The agent script is part of the benchmark suite."
    info "To start the agent on this server, copy and run:"
    echo ""
    echo "  # From the controller machine, copy the agent:"
    echo "  scp -r src/collectors/agent_server.py user@THIS_SERVER:/opt/aidaptive-agent/"
    echo ""
    echo "  # On this server, start the agent:"
    echo "  python3 /opt/aidaptive-agent/agent_server.py --port 9100"
    echo ""

    # ---- 6. Firewall Check ----
    step "Firewall & Network Check"
    info "Ensure the following ports are open for inbound connections:"
    echo ""
    echo "  Port 11434  - Ollama API (HTTP)"
    echo "  Port  9100  - Monitoring Agent (HTTP)"
    echo ""

    if has_cmd ufw; then
        info "UFW firewall detected. Suggested commands:"
        echo "  sudo ufw allow 11434/tcp"
        echo "  sudo ufw allow 9100/tcp"
    elif has_cmd firewall-cmd; then
        info "firewalld detected. Suggested commands:"
        echo "  sudo firewall-cmd --permanent --add-port=11434/tcp"
        echo "  sudo firewall-cmd --permanent --add-port=9100/tcp"
        echo "  sudo firewall-cmd --reload"
    fi

    # ---- Summary ----
    step "Target Server Verification Summary"
    echo ""
    echo "  Target Server Status:"
    echo "  ────────────────────────────────────────"
    printf "  %-20s %s\n" "NVIDIA Driver"   "$(has_cmd nvidia-smi && echo '✓ OK' || echo '✗ MISSING')"
    printf "  %-20s %s\n" "Ollama"          "$(has_cmd ollama     && echo '✓ OK' || echo '✗ MISSING')"
    printf "  %-20s %s\n" "Ollama Service"  "$(curl -sf http://localhost:11434/ >/dev/null 2>&1 && echo '✓ RUNNING' || echo '✗ NOT RUNNING')"
    printf "  %-20s %s\n" "Port 11434"      "$(curl -sf http://localhost:11434/ >/dev/null 2>&1 && echo '✓ OPEN' || echo '✗ CLOSED')"
    printf "  %-20s %s\n" "Python3"         "$(has_cmd python3    && echo '✓ OK' || echo '✗ MISSING')"
    echo "  ────────────────────────────────────────"
    echo ""
}

# ============================================================================
# Main
# ============================================================================
usage() {
    echo ""
    echo "Usage: $0 <mode>"
    echo ""
    echo "Modes:"
    echo "  controller  - Setup the benchmark controller machine"
    echo "                (installs k6, oha, locust, litellm, Docker, etc.)"
    echo ""
    echo "  target      - Setup a target AI server being benchmarked"
    echo "                (installs Ollama, NVIDIA check, model pull, agent)"
    echo ""
    echo "  all         - Setup both (for single-machine testing)"
    echo ""
}

MODE="${1:-}"

case "$MODE" in
    controller)
        setup_controller
        ;;
    target)
        setup_target
        ;;
    all)
        setup_controller
        setup_target
        ;;
    *)
        usage
        exit 1
        ;;
esac

echo ""
ok "Environment setup complete!"
echo ""
