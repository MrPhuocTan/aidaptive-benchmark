#!/bin/bash

# ==============================================
# aiDaptive Benchmark - AI Server Setup Script
# Chạy script này trên mỗi AI Server (Ubuntu/Debian)
# ==============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() { echo -e "${BLUE}[*]${NC} \$1"; }
print_success() { echo -e "${GREEN}[✓]${NC} \$1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} \$1"; }
print_error() { echo -e "${RED}[✗]${NC} \$1"; }

echo ""
echo "=============================================="
echo "   aiDaptive Benchmark - AI Server Setup"
echo "=============================================="
echo ""

# ----------------------------------------------
# 1. System Update
# ----------------------------------------------
print_status "Updating system packages..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq
print_success "System updated"

# ----------------------------------------------
# 2. Install basic dependencies
# ----------------------------------------------
print_status "Installing dependencies..."
sudo apt-get install -y -qq \
    curl \
    wget \
    git \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    jq \
    htop \
    nvtop
print_success "Dependencies installed"

# ----------------------------------------------
# 3. Install Ollama
# ----------------------------------------------
print_status "Installing Ollama..."
if command -v ollama &> /dev/null; then
    print_warning "Ollama already installed: $(ollama --version)"
else
    curl -fsSL https://ollama.com/install.sh | sh
    print_success "Ollama installed"
fi

# Start Ollama service
print_status "Starting Ollama service..."
sudo systemctl enable ollama 2>/dev/null || true
sudo systemctl start ollama 2>/dev/null || true

# Wait for Ollama to be ready
sleep 3
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    print_success "Ollama is running on port 11434"
else
    print_warning "Ollama may need manual start: ollama serve"
fi

# ----------------------------------------------
# 4. Pull Llama3 model
# ----------------------------------------------
print_status "Pulling Llama3:8b model (this may take a while)..."
ollama pull llama3:8b || print_warning "Failed to pull model, try manually: ollama pull llama3:8b"
print_success "Model ready"

# ----------------------------------------------
# 5. Install oha (HTTP load tester - Rust)
# ----------------------------------------------
print_status "Installing oha..."
if command -v oha &> /dev/null; then
    print_warning "oha already installed: $(oha --version)"
else
    # Try cargo first, then prebuilt binary
    if command -v cargo &> /dev/null; then
        cargo install oha
    else
        # Download prebuilt binary
        OHA_VERSION="1.4.6"
        wget -q "https://github.com/hatoo/oha/releases/download/v${OHA_VERSION}/oha-linux-amd64" -O /tmp/oha
        chmod +x /tmp/oha
        sudo mv /tmp/oha /usr/local/bin/oha
    fi
    print_success "oha installed"
fi

# ----------------------------------------------
# 6. Install k6 (Load testing - Go)
# ----------------------------------------------
print_status "Installing k6..."
if command -v k6 &> /dev/null; then
    print_warning "k6 already installed: $(k6 version)"
else
    sudo gpg -k
    sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
    echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
    sudo apt-get update -qq
    sudo apt-get install -y -qq k6
    print_success "k6 installed"
fi

# ----------------------------------------------
# 7. Setup Benchmark Agent
# ----------------------------------------------
print_status "Setting up Benchmark Agent..."

AGENT_DIR="/opt/aidaptive-agent"
sudo mkdir -p $AGENT_DIR

# Create agent script
sudo tee $AGENT_DIR/agent.py > /dev/null << 'AGENT_EOF'
#!/usr/bin/env python3
"""aiDaptive Benchmark Agent - Thu thập metrics từ AI Server"""

import subprocess
import json
import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="aiDaptive Benchmark Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_cmd(cmd, timeout=5):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/metrics/gpu")
async def gpu_metrics():
    """Get GPU metrics via nvidia-smi"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,utilization.memory,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode != 0:
            return {"error": "nvidia-smi failed", "gpus": []}
        
        gpus = []
        for line in result.stdout.strip().split("\n"):
            if line:
                p = [x.strip() for x in line.split(",")]
                if len(p) >= 9:
                    gpus.append({
                        "index": int(p[0]),
                        "name": p[1],
                        "memory_total_mb": float(p[2]),
                        "memory_used_mb": float(p[3]),
                        "memory_free_mb": float(p[4]),
                        "gpu_util_pct": float(p[5]) if p[5] not in ["[N/A]", "N/A"] else 0,
                        "memory_util_pct": float(p[6]) if p[6] not in ["[N/A]", "N/A"] else 0,
                        "temperature_c": float(p[7]) if p[7] not in ["[N/A]", "N/A"] else 0,
                        "power_w": float(p[8]) if p[8] not in ["[N/A]", "N/A"] else 0,
                    })
        return {"gpus": gpus, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        return {"error": str(e), "gpus": []}

@app.get("/metrics/system")
async def system_metrics():
    """Get CPU/RAM metrics"""
    try:
        # CPU Usage
        cpu_output = run_cmd("top -bn1 | grep 'Cpu(s)' | awk '{print \$2}'")
        cpu_pct = float(cpu_output) if cpu_output else 0
        
        # Memory
        mem_output = run_cmd("free -m | awk 'NR==2{printf \"%s %s %s\", \$2, \$3, \$4}'")
        mem_parts = mem_output.split() if mem_output else ["0", "0", "0"]
        
        # Load average
        load_output = run_cmd("cat /proc/loadavg | awk '{print \$1, \$2, \$3}'")
        load_parts = load_output.split() if load_output else ["0", "0", "0"]
        
        # Disk
        disk_output = run_cmd("df -h / | awk 'NR==2{print \$2, \$3, \$5}'")
        disk_parts = disk_output.split() if disk_output else ["0", "0", "0%"]
        
        return {
            "cpu_usage_pct": cpu_pct,
            "memory_total_mb": int(mem_parts[0]),
            "memory_used_mb": int(mem_parts[1]),
            "memory_free_mb": int(mem_parts[2]),
            "load_avg_1m": float(load_parts[0]),
            "load_avg_5m": float(load_parts[1]),
            "load_avg_15m": float(load_parts[2]),
            "disk_total": disk_parts[0],
            "disk_used": disk_parts[1],
            "disk_used_pct": disk_parts[2],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/ollama/status")
async def ollama_status():
    """Check Ollama status and loaded models"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            # Check if Ollama is running
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return {"online": True, "models": models}
            return {"online": False, "models": []}
    except:
        return {"online": False, "models": []}

@app.get("/info")
async def server_info():
    """Get server information"""
    hostname = run_cmd("hostname") or "unknown"
    kernel = run_cmd("uname -r") or "unknown"
    uptime = run_cmd("uptime -p") or "unknown"
    
    # GPU info
    gpu_name = run_cmd("nvidia-smi --query-gpu=name --format=csv,noheader") or "No GPU"
    gpu_driver = run_cmd("nvidia-smi --query-gpu=driver_version --format=csv,noheader") or "N/A"
    
    return {
        "hostname": hostname,
        "kernel": kernel,
        "uptime": uptime,
        "gpu_name": gpu_name.split("\n")[0] if gpu_name else "No GPU",
        "gpu_driver": gpu_driver.split("\n")[0] if gpu_driver else "N/A",
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9100)
AGENT_EOF

# Create requirements
sudo tee $AGENT_DIR/requirements.txt > /dev/null << 'REQ_EOF'
fastapi==0.109.0
uvicorn==0.27.0
httpx==0.26.0
REQ_EOF

# Create virtual environment and install
print_status "Installing Python dependencies for agent..."
cd $AGENT_DIR
sudo python3 -m venv venv
sudo $AGENT_DIR/venv/bin/pip install -q -r requirements.txt
print_success "Agent dependencies installed"

# ----------------------------------------------
# 8. Create systemd service for Agent
# ----------------------------------------------
print_status "Creating systemd service for agent..."

sudo tee /etc/systemd/system/aidaptive-agent.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=aiDaptive Benchmark Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aidaptive-agent
ExecStart=/opt/aidaptive-agent/venv/bin/python /opt/aidaptive-agent/agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE_EOF

sudo systemctl daemon-reload
sudo systemctl enable aidaptive-agent
sudo systemctl start aidaptive-agent
print_success "Agent service created and started"

# ----------------------------------------------
# 9. Configure firewall
# ----------------------------------------------
print_status "Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 11434/tcp comment 'Ollama API' 2>/dev/null || true
    sudo ufw allow 9100/tcp comment 'Benchmark Agent' 2>/dev/null || true
    print_success "Firewall rules added (ports 11434, 9100)"
else
    print_warning "ufw not found, manually open ports 11434 and 9100"
fi

# ----------------------------------------------
# 10. Verify installation
# ----------------------------------------------
echo ""
echo "=============================================="
echo "   Verifying Installation"
echo "=============================================="

# Check Ollama
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    print_success "Ollama: Running ✓"
    MODELS=$(curl -s http://localhost:11434/api/tags | jq -r '.models[].name' 2>/dev/null | tr '\n' ', ')
    echo "         Models: ${MODELS:-none}"
else
    print_error "Ollama: Not running"
fi

# Check Agent
if curl -s http://localhost:9100/health > /dev/null 2>&1; then
    print_success "Agent: Running on port 9100 ✓"
else
    print_error "Agent: Not running"
fi

# Check oha
if command -v oha &> /dev/null; then
    print_success "oha: $(oha --version 2>/dev/null || echo 'installed') ✓"
else
    print_warning "oha: Not installed"
fi

# Check k6
if command -v k6 &> /dev/null; then
    print_success "k6: $(k6 version 2>&1 | head -1) ✓"
else
    print_warning "k6: Not installed"
fi

# Get server IP
SERVER_IP=$(hostname -I | awk '{print \$1}')

echo ""
echo "=============================================="
echo "   Setup Complete!"
echo "=============================================="
echo ""
echo "Server IP: ${SERVER_IP}"
echo ""
echo "Endpoints:"
echo "  - Ollama API:  http://${SERVER_IP}:11434"
echo "  - Agent API:   http://${SERVER_IP}:9100"
echo ""
echo "Test commands:"
echo "  curl http://${SERVER_IP}:9100/health"
echo "  curl http://${SERVER_IP}:9100/metrics/gpu"
echo "  curl http://${SERVER_IP}:9100/ollama/status"
echo ""
echo "Add to benchmark.yaml on Mac:"
echo "  ollama_url: \"http://${SERVER_IP}:11434\""
echo "  agent_url: \"http://${SERVER_IP}:9100\""
echo ""