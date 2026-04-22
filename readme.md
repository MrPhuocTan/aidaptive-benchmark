<div align="center">
  <h1>aiDaptive Benchmark Suite</h1>
  <p><b>A professional, dynamic, and multi-server LLM inference benchmarking platform.</b></p>
  
  [![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](#)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.103.0-009688.svg?logo=fastapi&logoColor=white)](#)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg?logo=postgresql&logoColor=white)](#)
  [![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](#)
  [![License](https://img.shields.io/badge/License-Proprietary-red.svg)](#)
</div>

---

## Overview

The **aiDaptive Benchmark Suite** is an advanced AI performance measurement tool designed to configure and compare LLM inference performance across multiple servers dynamically.

### Core Objectives
- Flexible management of unlimited servers via a dynamic Data Table UI.
- Concurrent benchmarking execution across multiple target environments.
- **Hardware vs. Optimized Comparison:** Empirical performance validation comparing raw hardware configurations (Baseline) against optimized configurations (aiDaptive+ Enabled).

---

## Key Features

| Feature | Description |
| :--- | :--- |
| **Server Monitoring** | Automated hardware scanning and real-time system status tracking. |
| **Multi-tool Benchmark**| Native support for 7 benchmarking tools (Ollama, Oha, K6, Locust, LLMPerf, vLLM, LiteLLM). |
| **Automated Comparison** | Automatic calculation of performance differentials (`Δ%`) to determine the optimal configuration. |
| **Built-in Visualization**| Interactive Chart.js integration embedded directly within the user interface. |
| **History & Reports** | Persistent test execution history with comprehensive PDF/CSV export capabilities. |
| **Prompt Scenarios** | Diverse testing scenarios including conversational, coding, and long-context outputs. |

---

## Core Metrics

| Metric | Full Name | Unit | Description |
| :---: | :--- | :---: | :--- |
| **TTFT** | Time To First Token | `ms` | Latency measured until the generation of the first token. |
| **TPOT** | Time Per Output Token | `ms` | Average time required to generate each subsequent token. |
| **TPS** | Tokens Per Second | `tokens/s` | Token generation throughput speed. |
| **ITL** | Inter-Token Latency | `ms` | Latency delay between consecutive tokens. |
| **RPS** | Requests Per Second | `req/s` | Processing volume of requests handled per second. |
| **P50/P95/P99** | Latency Percentiles | `ms` | Percentile distribution thresholds of inference latency. |
| **Error Rate** | Failure Rate | `%` | Percentage metric of failed inference requests. |

---

## System Architecture

```mermaid
graph TD
    User([User Browser]) -->|HTTP / UI| App[Controller Node]
    
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
        S1[AI Server 1<br/>Baseline]
        SN[AI Server N<br/>aiDaptive+ Enabled]
    end
```

---

## Database Design

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

## Benchmark Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant WebUI
    participant Orchestrator
    participant Servers
    participant DB as PostgreSQL

    User->>WebUI: Initiate Benchmark
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
    Orchestrator->>DB: Compare Servers & Calculate Deltas
    Orchestrator->>DB: UPDATE run (status: completed)
    Orchestrator-->>WebUI: Emit Complete Event
    WebUI-->>User: Display Results Dashboard
```

---

## Getting Started

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

# Start the application server
python -m src
```
*The Web UI will be accessible at `http://localhost:8443`*

---

## Support & Contact
For platform inquiries, infrastructure support, or architectural discussions, contact the engineering team.

*aiDaptive Benchmark Suite v2.0 - © 2024 aiDaptive Inc. All rights reserved.*
