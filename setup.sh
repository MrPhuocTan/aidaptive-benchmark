#!/bin/bash

set -e

PURPLE='\033[0;35m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
NC='\033[0m'
BOLD='\033[1m'

echo ""
echo -e "${PURPLE}================================================================${NC}"
echo -e "${WHITE}${BOLD}  aiDaptive Benchmark Suite - Setup${NC}"
echo -e "${PURPLE}================================================================${NC}"
echo ""

echo -e "${WHITE}[1/7] Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "  Python3 not found. Installing via Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "  Homebrew not found. Install from https://brew.sh"
        exit 1
    fi
    brew install python@3.11
fi
echo -e "${GRAY}  $(python3 --version)${NC}"

echo -e "${WHITE}[2/7] Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo "  Docker not found. Install Docker Desktop:"
    echo "  https://www.docker.com/products/docker-desktop/"
    exit 1
fi
echo -e "${GRAY}  $(docker --version)${NC}"

echo -e "${WHITE}[3/7] Checking k6...${NC}"
if ! command -v k6 &> /dev/null; then
    echo "  Installing k6..."
    brew install k6
fi
echo -e "${GRAY}  $(k6 version 2>&1 | head -1)${NC}"

echo -e "${WHITE}[4/7] Checking oha...${NC}"
if ! command -v oha &> /dev/null; then
    echo "  Installing oha..."
    brew install oha
fi
echo -e "${GRAY}  oha installed${NC}"

echo -e "${WHITE}[5/7] Creating Python virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${GRAY}  Created .venv${NC}"
else
    echo -e "${GRAY}  .venv already exists${NC}"
fi
source .venv/bin/activate

echo -e "${WHITE}[6/7] Installing Python dependencies...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GRAY}  Dependencies installed${NC}"

echo -e "${WHITE}[7/7] Starting Docker services...${NC}"
docker-compose up -d
echo -e "${GRAY}  PostgreSQL: localhost:5432${NC}"
echo -e "${GRAY}  InfluxDB:   localhost:8086${NC}"
echo -e "${GRAY}  Grafana:    localhost:3000${NC}"

echo ""
echo -e "${PURPLE}================================================================${NC}"
echo -e "${WHITE}${BOLD}  Setup complete.${NC}"
echo ""
echo -e "${WHITE}  Activate environment:${NC}"
echo -e "${GRAY}    source .venv/bin/activate${NC}"
echo ""
echo -e "${WHITE}  Start application:${NC}"
echo -e "${GRAY}    python -m src${NC}"
echo ""
echo -e "${WHITE}  Open browser:${NC}"
echo -e "${GRAY}    http://localhost:8080${NC}"
echo -e "${PURPLE}================================================================${NC}"
echo ""