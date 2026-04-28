# 🚀 aiDaptive Benchmark Suite

**aiDaptive Benchmark Suite** is a premium, state-of-the-art performance testing and monitoring system designed for AI Infrastructure. It allows you to benchmark multiple LLM servers (Ollama, vLLM, etc.) simultaneously while collecting real-time hardware telemetry.

![Aesthetic Dashboard Preview](https://img.shields.io/badge/UI-Modern_&_Dynamic-blueviolet?style=for-the-badge)
![N-Server Support](https://img.shields.io/badge/Support-1,_2,_3+_Servers-orange?style=for-the-badge)
![Hardware Telemetry](https://img.shields.io/badge/Hardware-GPU_/_CPU_/_I/O-green?style=for-the-badge)

---

## ✨ Key Features

- **🌐 N-Server Benchmarking**: Compare performance across 1, 2, or 3+ servers in a single run.
- **📊 Comprehensive Telemetry**: Real-time tracking of:
  - **LLM Metrics**: TTFT (Time to First Token), TPS (Tokens Per Second), ITL, Latency, Goodput.
  - **Hardware Metrics**: GPU Utilization, VRAM, Power Consumption, Temperature, CPU Usage, RAM, Disk I/O (MB/s), and Network throughput (MB/s).
- **📑 Professional Reporting**:
  - **HTML Reports**: Standalone, interactive reports with Chart.js visualizations.
  - **Excel Export**: Detailed breakdown of every test case, prompt, and result for deep analysis.
- **🌍 Multilingual UI**: Full support for English, Vietnamese, and Simplified Chinese.
- **🛠️ Multi-Tool Support**: Integrated adapters for `Locust`, `oha`, `k6`, `LLMPerf`, and more.
- **💎 Premium Aesthetics**: Modern dark mode/glassmorphism design with smooth animations and responsive charts.

---

## 🏗️ Architecture

The system consists of a central **Controller** (FastAPI) and lightweight **Agents** deployed on AI servers.

- **Controller (Port 8443)**: Orchestrates benchmarks, manages data (PostgreSQL), and serves the Web UI.
- **Agent (Port 9100)**: Deployed on each AI server to collect GPU and System metrics via `nvidia-smi` and `/proc`.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **PostgreSQL** (configured in `src/config.py` or `.env`)
- **Ollama** installed on AI Servers.

### 2. Controller Setup
```bash
# Clone the repository
git clone https://github.com/MrPhuocTan/aidaptive-benchmark.git
cd aidaptive-benchmark

# Install dependencies
pip install -r requirements.txt

# Run the system
./run.sh
```

### 3. Agent Setup (Run on AI Servers)
```bash
# One-line installation
curl -sSL https://raw.githubusercontent.com/MrPhuocTan/aidaptive-benchmark/main/install_ai_server.sh | bash
```

---

## 📅 Deployment

Detailed deployment instructions for production environments can be found in the [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

- **Production URL**: `http://<your-server-ip>:8443`
- **Agent Port**: `9100`

---

## 🛠️ Developer Guide

For developers looking to extend the suite or add new benchmark adapters, please refer to the [Skill.md](Skill.md) guide. It covers:
- Directory structure and conventions.
- Data mapping between Agents and Database.
- Adding new tool adapters.
- i18n implementation.

---

## 📜 License

Created by **MrPhuocTan** — *Ted.t*. Built for advanced AI performance engineering.
