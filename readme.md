<div align="center">
  <h1>🚀 aiDaptive Benchmark Suite v2.0</h1>
  <p><b>A professional, dynamic, and multi-server LLM inference benchmarking platform.</b></p>
  
  [![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](#)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.103.0-009688.svg?logo=fastapi&logoColor=white)](#)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg?logo=postgresql&logoColor=white)](#)
  [![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](#)
  [![License](https://img.shields.io/badge/License-Proprietary-red.svg)](#)
</div>

---

## 📖 Overview

**aiDaptive Benchmark Suite** is an advanced AI performance measurement tool that allows you to configure and compare LLM inference performance across multiple servers dynamically.

### 🎯 Core Objectives
- Flexible management of unlimited servers via a dynamic Data Table UI.
- Concurrent benchmarking across 1 to N servers.
- **Hardware vs. Optimized Comparison:** Prove empirical performance gains by comparing raw hardware (Baseline) against optimized configurations (aiDaptive+ Enabled).

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| 🖥️ **Server Monitoring** | Auto-scans hardware and monitors real-time system status. |
| 🛠️ **Multi-tool Benchmark**| Native support for 7 benchmarking tools (Ollama, Oha, K6, Locust, LLMPerf, vLLM, LiteLLM). |
| ⚖️ **Automated Comparison** | Automatically calculates `Δ%` (Delta) to determine the absolute performance winner. |
| 📊 **Built-in Visualization**| Interactive Chart.js integration right in the UI—no Grafana needed. |
| 📑 **History & Reports** | Persistent run history with PDF/CSV export capabilities. |
| 📝 **Prompt Scenarios** | Diverse test scenarios including chat, coding, and long-context outputs. |

---

## 📈 Core Metrics

| Metric | Full Name | Unit | Description |
| :---: | :--- | :---: | :--- |
| **TTFT** | Time To First Token | `ms` | Latency until the first token is generated. |
| **TPOT** | Time Per Output Token | `ms` | Average time spent generating each subsequent token. |
| **TPS** | Tokens Per Second | `tokens/s` | Token generation speed (throughput). |
| **ITL** | Inter-Token Latency | `ms` | Latency between consecutive tokens. |
| **RPS** | Requests Per Second | `req/s` | Number of requests handled per second. |
| **P50/P95/P99** | Latency Percentiles | `ms` | Percentile distribution of latency. |
| **Error Rate** | Failure Rate | `%` | Percentage of failed inference requests. |

---

## 🏗️ System Architecture

```mermaid
graph TD
    User([🌐 User Browser]) -->|HTTP / UI| App[🖥️ Controller Node]
    
    subgraph Controller Node
        direction TB
        UI[Web UI & REST API] --> Orch[Orchestrator]
        Orch --> Adapters[Benchmark Adapters]
        Orch --> Collectors[Metrics Collectors]
        Adapters --> DS[(Data Sink)]
        Collectors --> DS
        DS --> DB[(PostgreSQL)]
    end
    
    Adapters -->|Inference: Port 11434| S1
    Adapters -->|Inference: Port 11434| SN
    
    Collectors -->|Metrics: Port 9100| S1
    Collectors -->|Metrics: Port 9100| SN

    subgraph Target Servers
        direction LR
        S1[🖥️ AI Server 1<br/>Baseline]
        SN[🖥️ AI Server N<br/>aiDaptive+ Enabled]
    end
```

---

## 🗄️ Database Design

```mermaid
erDiagram
    SERVER_PROFILES {
        int id PK
        string server_id UK
        string name
        string ip_address
        string status
        json models_available
    }
    
    BENCHMARK_RUNS {
        int id PK
        string run_id UK
        string status
        datetime started_at
        string suite
        int total_tests
    }
    
    BENCHMARK_RESULTS {
        int id PK
        string run_id FK
        string server
        float tps
        float ttft_ms
        float error_rate
    }
    
    SERVER_COMPARISONS {
        int id PK
        string run_id FK
        string overall_winner
        float delta_tps_pct
    }
    
    BENCHMARK_RUNS ||--o{ BENCHMARK_RESULTS : "has"
    BENCHMARK_RUNS ||--o{ SERVER_COMPARISONS : "analyzes"
```

---

## 🔄 Benchmark Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant WebUI
    participant Orchestrator
    participant Servers
    participant DB as PostgreSQL

    User->>WebUI: Click "Start Benchmark"
    WebUI->>Orchestrator: POST /api/benchmark/start
    Orchestrator->>DB: INSERT run (status: running)
    
    Note over Orchestrator,Servers: Phase 1 & 2: Preflight & Warmup
    Orchestrator->>Servers: Verify connectivity & Warmup Models
    Servers-->>Orchestrator: OK
    
    Note over Orchestrator,Servers: Phase 3: Benchmarking
    loop For each test scenario
        Orchestrator->>Servers: Execute Inference Requests
        Servers-->>Orchestrator: Metrics (TTFT, TPS, P99)
        Orchestrator->>DB: Save Results
    end
    
    Note over Orchestrator,DB: Phase 4: Finalize
    Orchestrator->>DB: Compare Servers & Calculate Δ%
    Orchestrator->>DB: UPDATE run (status: completed)
    Orchestrator-->>WebUI: Emit Complete Event
    WebUI-->>User: Show Results Dashboard
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **Docker & Docker Compose**
- **PostgreSQL 15+**

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/MrPhuocTan/aidaptive-benchmark.git
cd aidaptive-benchmark

# Start the database
docker-compose up -d

# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the server
python -m src
```
*Access the Web UI at `http://localhost:8000`*

---

## 🤝 Support & Contact
For inquiries and support, please contact the engineering team.

*aiDaptive Benchmark Suite v2.0 - © 2024 aiDaptive Inc. All rights reserved.*
