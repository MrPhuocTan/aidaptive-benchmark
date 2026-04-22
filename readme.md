# 📘 TÀI LIỆU KIẾN TRÚC HỆ THỐNG
# aiDaptive Benchmark Suite v2.0

---

## 📑 MỤC LỤC

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Database Design](#3-database-design)
4. [API Specification](#4-api-specification)
5. [UI/UX Design](#5-uiux-design)
6. [Benchmark Tools](#6-benchmark-tools)
7. [Cấu trúc Source Code](#7-cấu-trúc-source-code)
8. [Cài đặt và Deployment](#8-cài-đặt-và-deployment)
9. [Workflow và Use Cases](#9-workflow-và-use-cases)

---

# 1. TỔNG QUAN HỆ THỐNG

## 1.1 Mục đích

**aiDaptive Benchmark Suite** là phần mềm đo hiệu năng AI, so sánh hiệu suất LLM inference giữa 2 cấu hình:

| Server | Cấu hình | Mục tiêu |
|--------|----------|----------|
| **Server 1** | aiDaptive+ **DISABLED** | Baseline - Hardware thuần |
| **Server 2** | aiDaptive+ **ENABLED** | Chứng minh cải thiện hiệu năng |

## 1.2 Tính năng chính

| # | Tính năng | Mô tả |
|---|-----------|-------|
| F1 | **Server Monitoring** | Tự động scan hardware, theo dõi trạng thái realtime |
| F2 | **Multi-tool Benchmark** | 7 công cụ đo lường khác nhau |
| F3 | **Automated Comparison** | Tự động so sánh và xác định winner |
| F4 | **Built-in Visualization** | Charts nhúng trong UI, không cần Grafana |
| F5 | **History & Reports** | Lưu lịch sử, xuất PDF/CSV |
| F6 | **Prompt Scenarios** | Nhiều kịch bản test (chat, code, long output...) |

## 1.3 Metrics đo lường

| Metric | Tên đầy đủ | Đơn vị | Ý nghĩa |
|--------|-----------|--------|---------|
| **TTFT** | Time To First Token | ms | Thời gian đến token đầu tiên |
| **TPOT** | Time Per Output Token | ms | Thời gian trung bình mỗi token |
| **TPS** | Tokens Per Second | tokens/s | Tốc độ sinh token |
| **ITL** | Inter-Token Latency | ms | Độ trễ giữa các token |
| **RPS** | Requests Per Second | req/s | Số request xử lý mỗi giây |
| **P50/P95/P99** | Latency Percentiles | ms | Phân vị độ trễ |
| **Error Rate** | Tỷ lệ lỗi | % | Phần trăm request thất bại |

## 1.4 Technology Stack

| Layer | Technology | Mục đích |
|-------|------------|----------|
| Backend | Python 3.10 + FastAPI | Web server, API |
| Frontend | Jinja2 + TailwindCSS + Chart.js | UI, Charts |
| Database | PostgreSQL 15 | Data storage |
| LLM Engine | Ollama | Serve LLM models |
| Container | Docker | Deployment |

---

# 2. KIẾN TRÚC HỆ THỐNG

## 2.1 Sơ đồ tổng quan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONTROLLER NODE                                    │
│                     (Linux Ubuntu 22.04 + Python 3.10)                      │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                    aiDaptive Benchmark Suite                          │  │
│   │                                                                       │  │
│   │   ┌─────────────┐   ┌─────────────┐   ┌─────────────────────────┐   │  │
│   │   │   Web UI    │   │  REST API   │   │         CLI             │   │  │
│   │   │  (Jinja2 +  │   │  (FastAPI)  │   │     (argparse)          │   │  │
│   │   │  Chart.js)  │   │             │   │                         │   │  │
│   │   └──────┬──────┘   └──────┬──────┘   └───────────┬─────────────┘   │  │
│   │          │                 │                      │                  │  │
│   │          └─────────────────┼──────────────────────┘                  │  │
│   │                            ▼                                         │  │
│   │   ┌────────────────────────────────────────────────────────────┐    │  │
│   │   │                    ORCHESTRATOR                             │    │  │
│   │   │   - Điều phối benchmark flow                               │    │  │
│   │   │   - Quản lý progress                                       │    │  │
│   │   │   - Error handling                                         │    │  │
│   │   └──────────────────────────┬─────────────────────────────────┘    │  │
│   │                              │                                       │  │
│   │          ┌───────────────────┼───────────────────┐                  │  │
│   │          ▼                   ▼                   ▼                  │  │
│   │   ┌────────────┐     ┌─────────────┐     ┌─────────────┐           │  │
│   │   │  ADAPTERS  │     │ COLLECTORS  │     │  DATA SINK  │           │  │
│   │   │ (7 tools)  │     │ (Hardware)  │     │ (PostgreSQL)│           │  │
│   │   └────────────┘     └─────────────┘     └─────────────┘           │  │
│   │                                                                      │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                         PostgreSQL :5432                              │  │
│   │                    (Single Database - All Data)                       │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                    HTTP/REST (Ports: 11434, 9100)
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼                                                   ▼
┌─────────────────────────────┐            ┌─────────────────────────────┐
│       AI SERVER 1           │            │       AI SERVER 2           │
│   aiDaptive+ DISABLED       │            │   aiDaptive+ ENABLED        │
│                             │            │                             │
│  ┌───────────────────────┐  │            │  ┌───────────────────────┐  │
│  │    Ollama :11434      │  │            │  │    Ollama :11434      │  │
│  │   (LLM Inference)     │  │            │  │   (LLM Inference)     │  │
│  └───────────────────────┘  │            │  └───────────────────────┘  │
│                             │            │                             │
│  ┌───────────────────────┐  │            │  ┌───────────────────────┐  │
│  │    Agent :9100        │  │            │  │    Agent :9100        │  │
│  │  (Hardware Metrics)   │  │            │  │  (Hardware Metrics)   │  │
│  └───────────────────────┘  │            │  └───────────────────────┘  │
│                             │            │                             │
│  Hardware: Auto-detected    │            │  Hardware: Auto-detected    │
└─────────────────────────────┘            └─────────────────────────────┘
```

## 2.2 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATION                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         PRESENTATION LAYER                            │   │
│  │                                                                       │   │
│  │   app.py                                                             │   │
│  │   ├── Web Pages (Jinja2 templates)                                   │   │
│  │   │   ├── / (Dashboard)                                              │   │
│  │   │   ├── /servers                                                   │   │
│  │   │   ├── /benchmark                                                 │   │
│  │   │   ├── /history                                                   │   │
│  │   │   ├── /history/{run_id}                                          │   │
│  │   │   ├── /comparison                                                │   │
│  │   │   └── /settings                                                  │   │
│  │   │                                                                   │   │
│  │   └── REST API Endpoints                                             │   │
│  │       ├── /api/status                                                │   │
│  │       ├── /api/benchmark/*                                           │   │
│  │       ├── /api/runs/*                                                │   │
│  │       └── /api/charts/*                                              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                          BUSINESS LAYER                               │   │
│  │                                                                       │   │
│  │   orchestrator.py                                                    │   │
│  │   ├── Benchmark flow control                                         │   │
│  │   ├── Progress management                                            │   │
│  │   ├── Error handling                                                 │   │
│  │   └── Result aggregation                                             │   │
│  │                                                                       │   │
│  │   adapters/                          collectors/                     │   │
│  │   ├── ollama_adapter.py              ├── agent_client.py            │   │
│  │   ├── oha_adapter.py                 └── metric_collector.py        │   │
│  │   ├── k6_adapter.py                                                  │   │
│  │   ├── litellm_adapter.py                                            │   │
│  │   ├── locust_adapter.py                                             │   │
│  │   ├── llmperf_adapter.py                                            │   │
│  │   └── vllm_bench_adapter.py                                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                           DATA LAYER                                  │   │
│  │                                                                       │   │
│  │   database/                          data/                           │   │
│  │   ├── engine.py (connections)        ├── data_sink.py               │   │
│  │   ├── tables.py (schema)             └── postgres_writer.py         │   │
│  │   ├── repository.py (CRUD)                                          │   │
│  │   └── seed.py (init data)                                           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                          PostgreSQL                                   │   │
│  │   Tables: benchmark_runs, benchmark_results, hardware_snapshots,     │   │
│  │           server_comparisons, server_profiles                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2.3 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BENCHMARK DATA FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────┘

User clicks "Start Benchmark"
         │
         ▼
┌─────────────────┐
│  1. Web UI      │
│  POST /api/     │
│  benchmark/start│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Orchestrator│
│  - Create run_id│
│  - Save to DB   │
│  - Start phases │
└────────┬────────┘
         │
         ├──────────────────────────────────────┐
         │                                      │
         ▼                                      ▼
┌─────────────────┐                  ┌─────────────────┐
│ 3a. Metric      │                  │ 3b. Adapters    │
│ Collector       │                  │ (7 tools)       │
│ - Poll GPU/CPU  │                  │ - Send prompts  │
│ - Every 1 sec   │                  │ - Measure time  │
└────────┬────────┘                  └────────┬────────┘
         │                                    │
         │     ┌──────────────────────────────┤
         │     │                              │
         │     ▼                              ▼
         │  ┌─────────────────┐    ┌─────────────────┐
         │  │ AI Server 1     │    │ AI Server 2     │
         │  │ (Disabled)      │    │ (Enabled)       │
         │  │                 │    │                 │
         │  │ Ollama API      │    │ Ollama API      │
         │  │ Agent API       │    │ Agent API       │
         │  └────────┬────────┘    └────────┬────────┘
         │           │                      │
         │           └──────────┬───────────┘
         │                      │
         │                      ▼
         │           ┌─────────────────┐
         │           │ 4. Parse Results│
         │           │ - Extract TTFT  │
         │           │ - Calculate TPS │
         │           │ - Normalize     │
         │           └────────┬────────┘
         │                    │
         └────────────────────┤
                              │
                              ▼
                   ┌─────────────────┐
                   │ 5. Data Sink    │
                   │ - Write results │
                   │ - Write metrics │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ 6. PostgreSQL   │
                   │ benchmark_results│
                   │ hardware_snapshots│
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ 7. Aggregator   │
                   │ - Compare S1/S2 │
                   │ - Calculate Δ%  │
                   │ - Determine     │
                   │   winner        │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ 8. Display      │
                   │ - Charts        │
                   │ - Tables        │
                   │ - Export        │
                   └─────────────────┘
```

## 2.4 Sequence Diagram – Benchmark Execution

```
┌──────┐   ┌──────────┐   ┌────────────┐   ┌─────────┐   ┌──────────┐   ┌────────┐
│ User │   │  Web UI  │   │Orchestrator│   │ Adapter │   │AI Server │   │   DB   │
└──┬───┘   └────┬─────┘   └─────┬──────┘   └────┬────┘   └────┬─────┘   └───┬────┘
   │            │               │                │             │             │
   │ Click Start│               │                │             │             │
   │───────────>│               │                │             │             │
   │            │ POST /start   │                │             │             │
   │            │──────────────>│                │             │             │
   │            │               │ INSERT run     │             │             │
   │            │               │────────────────┼─────────────┼────────────>│
   │            │               │                │             │             │
   │            │               │ [Phase 1: Preflight]         │             │
   │            │               │ Check servers  │             │             │
   │            │               │────────────────┼────────────>│             │
   │            │               │<───────────────┼─────────────│ OK          │
   │            │               │                │             │             │
   │            │               │ [Phase 2: Warmup]            │             │
   │            │               │ Send warmup    │             │             │
   │            │               │───────────────>│ POST /generate           │
   │            │               │                │────────────>│             │
   │            │               │                │<────────────│             │
   │            │               │<───────────────│             │             │
   │            │               │                │             │             │
   │            │               │ [Phase 3: Benchmarking]      │             │
   │            │               │ Loop: for each test          │             │
   │            │               │───────────────>│ Run benchmark│            │
   │            │               │                │────────────>│             │
   │            │               │                │<────────────│ Results     │
   │            │               │                │ Parse       │             │
   │            │               │<───────────────│ results     │             │
   │            │               │ Save results   │             │             │
   │            │               │────────────────┼─────────────┼────────────>│
   │            │               │                │             │             │
   │ Poll progress              │                │             │             │
   │───────────>│ GET /progress │                │             │             │
   │            │──────────────>│                │             │             │
   │            │<──────────────│ {percent: 42}  │             │             │
   │<───────────│               │                │             │             │
   │            │               │                │             │             │
   │            │               │ [Phase 4: Finalize]          │             │
   │            │               │ Compare S1 vs S2             │             │
   │            │               │ Calculate deltas             │             │
   │            │               │ UPDATE run status            │             │
   │            │               │────────────────┼─────────────┼────────────>│
   │            │               │                │             │             │
   │            │<──────────────│ {status: completed}          │             │
   │<───────────│ Show results  │                │             │             │
   │            │               │                │             │             │
```

## 2.5 Network Topology

```
┌────────────────────────────────────────────────────────────────────┐
│                        NETWORK DIAGRAM                              │
└────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────┐
                    │   User Browser       │
                    │   (Any Device)       │
                    └──────────┬───────────┘
                               │
                          Port 8000
                               │
                    ┌──────────▼───────────┐
                    │   Controller Node    │
                    │   IP: 10.0.1.10      │
                    │                      │
                    │   FastAPI :8000      │
                    │   PostgreSQL :5432   │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                                 │
     Port 11434, 9100                  Port 11434, 9100
              │                                 │
   ┌──────────▼───────────┐        ┌───────────▼──────────┐
   │   AI Server 1        │        │   AI Server 2        │
   │   IP: 35.186.159.250 │        │   IP: 34.142.222.133 │
   │                      │        │                      │
   │   Ollama :11434      │        │   Ollama :11434      │
   │   Agent  :9100       │        │   Agent  :9100       │
   │                      │        │                      │
   │   aiDaptive+: OFF    │        │   aiDaptive+: ON     │
   └──────────────────────┘        └──────────────────────┘

   Firewall Rules:
   ┌─────────────────────────────────────────────────────┐
   │  Controller → Server1:11434  (Ollama API)   ALLOW   │
   │  Controller → Server1:9100   (Agent API)    ALLOW   │
   │  Controller → Server2:11434  (Ollama API)   ALLOW   │
   │  Controller → Server2:9100   (Agent API)    ALLOW   │
   │  User → Controller:8000      (Web UI)       ALLOW   │
   │  * → *                       (Others)       DENY    │
   └─────────────────────────────────────────────────────┘
```

---

# 3. DATABASE DESIGN

## 3.1 Entity Relationship Diagram

```
┌─────────────────────┐       ┌─────────────────────┐
│   server_profiles   │       │   benchmark_runs    │
├─────────────────────┤       ├─────────────────────┤
│ PK server_id        │       │ PK id               │
│    name             │       │ UK run_id           │
│    description      │       │    status           │
│    aidaptive_enabled│       │    started_at       │
│    created_at       │       │    finished_at      │
└─────────────────────┘       │    duration_seconds │
                              │    suite            │
                              │    environment      │
                              │    model            │
                              │    config_snapshot  │
                              │    notes            │
                              │    tags             │
                              │    total_tests      │
                              │    completed_tests  │
                              └──────────┬──────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
       ┌─────────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
       │  benchmark_results  │  │hardware_snapshots│  │ server_comparisons │
       ├─────────────────────┤  ├─────────────────┤  ├─────────────────────┤
       │ PK id               │  │ PK id           │  │ PK id               │
       │ FK run_id           │  │ FK run_id       │  │ FK run_id           │
       │    timestamp        │  │    server       │  │    tool             │
       │    server           │  │    timestamp    │  │    scenario         │
       │    tool             │  │    gpu_util_pct │  │    s1_tps           │
       │    scenario         │  │    gpu_temp_c   │  │    s2_tps           │
       │    model            │  │    vram_used_gb │  │    delta_tps_pct    │
       │    concurrency      │  │    cpu_pct      │  │    s1_ttft_ms       │
       │    ttft_ms          │  │    ram_used_gb  │  │    s2_ttft_ms       │
       │    tpot_ms          │  └─────────────────┘  │    delta_ttft_pct   │
       │    tps              │                       │    overall_winner   │
       │    itl_ms           │                       └─────────────────────┘
       │    rps              │
       │    latency_p50_ms   │
       │    latency_p95_ms   │
       │    latency_p99_ms   │
       │    error_rate       │
       │    total_tokens     │
       └─────────────────────┘
```

## 3.2 Table Definitions

### 3.2.1 `benchmark_runs`

```sql
CREATE TABLE benchmark_runs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) UNIQUE NOT NULL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    duration_seconds FLOAT,
    
    -- Config
    suite VARCHAR(50),                      -- single_request, concurrent_load, all
    environment VARCHAR(50),                -- lan, vpn, etc.
    model VARCHAR(100),                     -- llama3.2:1b, etc.
    config_snapshot JSONB,                  -- Full config at run time
    
    -- Metadata
    notes TEXT,
    tags TEXT[],
    
    -- Progress
    total_tests INTEGER DEFAULT 0,
    completed_tests INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_runs_status ON benchmark_runs(status);
CREATE INDEX idx_runs_created ON benchmark_runs(created_at DESC);
```

### 3.2.2 `benchmark_results`

```sql
CREATE TABLE benchmark_results (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) REFERENCES benchmark_runs(run_id) ON DELETE CASCADE,
    
    -- Context
    timestamp TIMESTAMP NOT NULL,
    server VARCHAR(50) NOT NULL,            -- server1, server2
    tool VARCHAR(50) NOT NULL,              -- ollama_native, oha, k6, etc.
    scenario VARCHAR(100),                  -- simple_chat, code_generation, etc.
    model VARCHAR(100),
    concurrency INTEGER,
    
    -- Latency metrics (ms)
    ttft_ms FLOAT,                          -- Time to first token
    tpot_ms FLOAT,                          -- Time per output token
    itl_ms FLOAT,                           -- Inter-token latency
    latency_p50_ms FLOAT,
    latency_p95_ms FLOAT,
    latency_p99_ms FLOAT,
    
    -- Throughput metrics
    tps FLOAT,                              -- Tokens per second
    rps FLOAT,                              -- Requests per second
    goodput FLOAT,                          -- Successful throughput
    
    -- Token counts
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    
    -- Request stats
    total_requests INTEGER,
    successful_requests INTEGER,
    failed_requests INTEGER,
    error_rate FLOAT,                       -- 0.0 to 1.0
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_results_run_id ON benchmark_results(run_id);
CREATE INDEX idx_results_server ON benchmark_results(server);
CREATE INDEX idx_results_tool ON benchmark_results(tool);
CREATE INDEX idx_results_timestamp ON benchmark_results(timestamp);
```

### 3.2.3 `hardware_snapshots`

```sql
CREATE TABLE hardware_snapshots (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50),
    server VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- GPU metrics
    gpu_util_pct FLOAT,
    gpu_memory_util_pct FLOAT,
    vram_used_gb FLOAT,
    vram_total_gb FLOAT,
    gpu_power_watts FLOAT,
    gpu_temperature_c FLOAT,
    
    -- System metrics
    cpu_pct FLOAT,
    ram_used_gb FLOAT,
    ram_total_gb FLOAT,
    load_avg_1m FLOAT,
    load_avg_5m FLOAT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_snapshots_run_id ON hardware_snapshots(run_id);
CREATE INDEX idx_snapshots_server ON hardware_snapshots(server);
CREATE INDEX idx_snapshots_timestamp ON hardware_snapshots(timestamp);
```

### 3.2.4 `server_comparisons`

```sql
CREATE TABLE server_comparisons (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) REFERENCES benchmark_runs(run_id) ON DELETE CASCADE,
    
    -- Context
    tool VARCHAR(50),
    scenario VARCHAR(100),
    
    -- Server 1 metrics (aiDaptive+ Disabled)
    s1_ttft_ms FLOAT,
    s1_tpot_ms FLOAT,
    s1_tps FLOAT,
    s1_rps FLOAT,
    s1_p99_ms FLOAT,
    s1_error_rate FLOAT,
    
    -- Server 2 metrics (aiDaptive+ Enabled)
    s2_ttft_ms FLOAT,
    s2_tpot_ms FLOAT,
    s2_tps FLOAT,
    s2_rps FLOAT,
    s2_p99_ms FLOAT,
    s2_error_rate FLOAT,
    
    -- Delta calculations (positive = S2 better)
    delta_ttft_pct FLOAT,                   -- Negative is better (lower latency)
    delta_tps_pct FLOAT,                    -- Positive is better (higher throughput)
    delta_p99_pct FLOAT,                    -- Negative is better
    
    -- Winner
    overall_winner VARCHAR(20),             -- server1, server2, tie
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_comparisons_run_id ON server_comparisons(run_id);
```

### 3.2.5 `server_profiles`

```sql
CREATE TABLE server_profiles (
    id SERIAL PRIMARY KEY,
    server_id VARCHAR(50) UNIQUE NOT NULL,  -- server1, server2
    
    -- Display
    name VARCHAR(100),
    description TEXT,
    
    -- Config
    ollama_url VARCHAR(255),
    agent_url VARCHAR(255),
    aidaptive_enabled BOOLEAN DEFAULT FALSE,
    
    -- Auto-detected hardware (updated by agent)
    gpu_name VARCHAR(100),
    gpu_vram_gb FLOAT,
    gpu_driver VARCHAR(50),
    cpu_name VARCHAR(100),
    cpu_cores INTEGER,
    ram_total_gb FLOAT,
    hostname VARCHAR(100),
    os_version VARCHAR(100),
    
    -- Status
    last_seen_at TIMESTAMP,
    is_online BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 3.3 Data Volume Estimation

| Table | Records / Run | Retention | Estimated Size |
|-------|--------------|-----------|----------------|
| `benchmark_runs` | 1 | Unlimited | ~1 KB/run |
| `benchmark_results` | ~168 (2 servers × 6 scenarios × 7 tools × 2 concurrencies) | Unlimited | ~50 KB/run |
| `hardware_snapshots` | ~1800 (2 servers × 1/sec × ~15 min) | 90 days | ~200 KB/run |
| `server_comparisons` | ~42 (6 scenarios × 7 tools) | Unlimited | ~10 KB/run |
| `server_profiles` | 2 (static) | Permanent | ~1 KB total |

**Tổng ước tính:** ~260 KB/run → 100 runs ≈ 26 MB → dung lượng rất nhỏ.

## 3.4 Migration & Seed Data

```sql
-- Seed data cho server_profiles
INSERT INTO server_profiles (server_id, name, description, ollama_url, agent_url, aidaptive_enabled)
VALUES 
  ('server1', 'aiDaptive+ Disabled', 'Baseline server without aiDaptive+ optimization',
   'http://35.186.159.250:11434', 'http://35.186.159.250:9100', false),
  ('server2', 'aiDaptive+ Enabled', 'Server with aiDaptive+ optimization enabled',
   'http://34.142.222.133:11434', 'http://34.142.222.133:9100', true)
ON CONFLICT (server_id) DO NOTHING;
```

---

# 4. API SPECIFICATION

## 4.1 REST API Overview

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| **System** |||
| GET | `/api/status` | Trạng thái hệ thống và servers |
| GET | `/api/health` | Health check |
| **Benchmark Control** |||
| POST | `/api/benchmark/start` | Bắt đầu benchmark |
| POST | `/api/benchmark/stop` | Dừng benchmark |
| GET | `/api/benchmark/progress` | Tiến độ hiện tại |
| **Runs Management** |||
| GET | `/api/runs` | Danh sách runs |
| GET | `/api/runs/{run_id}` | Chi tiết run |
| DELETE | `/api/runs/{run_id}` | Xóa run |
| GET | `/api/runs/{run_id}/export` | Export CSV |
| **Charts Data** |||
| GET | `/api/charts/comparison/{run_id}` | Data cho comparison charts |
| GET | `/api/charts/timeline/{run_id}` | Data cho timeline charts |
| GET | `/api/charts/summary/{run_id}` | Data cho summary cards |
| **Servers** |||
| GET | `/api/servers` | Danh sách servers và hardware info |
| GET | `/api/servers/{server_id}/metrics` | Realtime metrics |

## 4.2 API Details

### 4.2.1 `GET /api/status`

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-04-15T10:30:00Z",
  "servers": [
    {
      "server_id": "server1",
      "name": "aiDaptive+ Disabled",
      "aidaptive_enabled": false,
      "ollama_online": true,
      "agent_online": true,
      "models_loaded": ["llama3.2:1b"],
      "hardware": {
        "gpu_name": "NVIDIA GeForce RTX 4090",
        "gpu_vram_gb": 24.0,
        "cpu_name": "Intel Xeon E5-2680 v4",
        "ram_total_gb": 64.0
      }
    },
    {
      "server_id": "server2",
      "name": "aiDaptive+ Enabled",
      "aidaptive_enabled": true,
      "ollama_online": true,
      "agent_online": true,
      "models_loaded": ["llama3.2:1b"],
      "hardware": {
        "gpu_name": "NVIDIA GeForce RTX 3070",
        "gpu_vram_gb": 8.0,
        "cpu_name": "Intel Core i7-12700",
        "ram_total_gb": 32.0
      }
    }
  ],
  "database": {
    "postgres": true
  },
  "benchmark": {
    "is_running": false,
    "current_run_id": null
  }
}
```

### 4.2.2 `POST /api/benchmark/start`

**Request:**
```json
{
  "suite": "single_request",
  "server": "all",
  "environment": "lan",
  "notes": "Test run description",
  "tags": ["production", "v1.0"]
}
```

**Response (200):**
```json
{
  "run_id": "run_20240415_103000",
  "status": "started",
  "message": "Benchmark started successfully"
}
```

**Response (409 - Already Running):**
```json
{
  "error": "conflict",
  "message": "Benchmark already running",
  "current_run_id": "run_20240415_100000"
}
```

**Response (503 - Servers Offline):**
```json
{
  "error": "service_unavailable",
  "message": "One or more servers are offline",
  "details": {
    "server1": {"ollama": true, "agent": false},
    "server2": {"ollama": true, "agent": true}
  }
}
```

### 4.2.3 `POST /api/benchmark/stop`

**Response (200):**
```json
{
  "run_id": "run_20240415_103000",
  "status": "stopped",
  "message": "Benchmark stopped. Partial results saved.",
  "completed_tests": 35,
  "total_tests": 84
}
```

### 4.2.4 `GET /api/benchmark/progress`

**Response:**
```json
{
  "status": "running",
  "run_id": "run_20240415_103000",
  "current_phase": "Benchmarking",
  "current_test": "server1/simple_chat/llama3.2:1b/ollama_native",
  "total_tests": 84,
  "completed_tests": 35,
  "percent": 42,
  "started_at": "2024-04-15T10:30:00Z",
  "elapsed_seconds": 125,
  "estimated_remaining_seconds": 173,
  "errors": [],
  "live_metrics": {
    "last_tps": 52.3,
    "last_ttft_ms": 132.5,
    "current_server": "server1"
  }
}
```

### 4.2.5 `GET /api/runs`

**Query Parameters:**
- `limit` (int, default: 20)
- `offset` (int, default: 0)
- `status` (string, optional): pending, running, completed, failed
- `sort` (string, default: "created_at_desc")

**Response:**
```json
{
  "total": 45,
  "limit": 20,
  "offset": 0,
  "runs": [
    {
      "run_id": "run_20240415_103000",
      "status": "completed",
      "started_at": "2024-04-15T10:30:00Z",
      "finished_at": "2024-04-15T10:45:30Z",
      "duration_seconds": 930,
      "suite": "single_request",
      "model": "llama3.2:1b",
      "total_tests": 84,
      "completed_tests": 84,
      "notes": "Production benchmark",
      "tags": ["production"],
      "winner": "server2"
    }
  ]
}
```

### 4.2.6 `GET /api/runs/{run_id}`

**Response:**
```json
{
  "run": {
    "run_id": "run_20240415_103000",
    "status": "completed",
    "started_at": "2024-04-15T10:30:00Z",
    "finished_at": "2024-04-15T10:45:30Z",
    "duration_seconds": 930,
    "suite": "single_request",
    "environment": "lan",
    "model": "llama3.2:1b",
    "total_tests": 84,
    "completed_tests": 84,
    "config_snapshot": {
      "warmup_requests": 3,
      "repeat_count": 5,
      "concurrency_levels": [1, 5, 10],
      "timeout_seconds": 120
    }
  },
  "summary": {
    "server1": {
      "avg_tps": 45.2,
      "avg_ttft_ms": 150.5,
      "avg_tpot_ms": 22.1,
      "avg_p50_ms": 1200,
      "avg_p95_ms": 2100,
      "avg_p99_ms": 2500,
      "total_tokens": 15000,
      "total_requests": 84,
      "successful_requests": 83,
      "error_rate": 0.005
    },
    "server2": {
      "avg_tps": 58.7,
      "avg_ttft_ms": 125.2,
      "avg_tpot_ms": 17.0,
      "avg_p50_ms": 950,
      "avg_p95_ms": 1500,
      "avg_p99_ms": 1800,
      "total_tokens": 19500,
      "total_requests": 84,
      "successful_requests": 84,
      "error_rate": 0.003
    },
    "comparison": {
      "tps_delta_pct": 29.9,
      "ttft_delta_pct": -16.8,
      "tpot_delta_pct": -23.1,
      "p99_delta_pct": -28.0,
      "error_rate_delta_pct": -40.0,
      "winner": "server2"
    }
  },
  "results_count": 168,
  "comparisons_count": 12
}
```

### 4.2.7 `DELETE /api/runs/{run_id}`

**Response (200):**
```json
{
  "message": "Run run_20240415_103000 deleted successfully",
  "deleted_results": 168,
  "deleted_snapshots": 1800,
  "deleted_comparisons": 12
}
```

**Response (404):**
```json
{
  "error": "not_found",
  "message": "Run run_20240415_103000 not found"
}
```

### 4.2.8 `GET /api/runs/{run_id}/export`

**Query Parameters:**
- `format` (string, default: "csv"): csv, json, pdf

**Response (CSV):**
```
Content-Type: text/csv
Content-Disposition: attachment; filename="run_20240415_103000.csv"

server,tool,scenario,model,concurrency,ttft_ms,tpot_ms,tps,itl_ms,rps,p50_ms,p95_ms,p99_ms,error_rate
server1,ollama_native,simple_chat,llama3.2:1b,1,150.5,22.1,45.2,23.5,1.2,1200,2100,2500,0.005
server2,ollama_native,simple_chat,llama3.2:1b,1,125.2,17.0,58.7,18.2,1.5,950,1500,1800,0.003
...
```

### 4.2.9 `GET /api/charts/comparison/{run_id}`

**Response:**
```json
{
  "tools": ["ollama_native", "oha", "k6", "litellm", "vllm_bench", "locust", "llmperf"],
  "scenarios": ["simple_chat", "code_generation", "long_output", "reasoning", "translation", "summarization"],
  "tps": {
    "labels": ["ollama", "oha", "k6", "litellm", "vllm", "locust", "llmperf"],
    "server1": {
      "name": "aiDaptive+ Disabled",
      "color": "#EF4444",
      "data": [45.2, 42.1, 40.5, 38.9, 44.8, 41.2, 43.5]
    },
    "server2": {
      "name": "aiDaptive+ Enabled",
      "color": "#10B981",
      "data": [58.7, 55.3, 52.8, 50.2, 57.1, 53.8, 56.2]
    }
  },
  "ttft": {
    "labels": ["ollama", "oha", "k6", "litellm", "vllm", "locust", "llmperf"],
    "server1": {"data": [150.5, 155.2, 148.9, 160.3, 152.1, 157.8, 149.3]},
    "server2": {"data": [125.2, 128.5, 122.1, 130.8, 126.5, 131.2, 124.8]}
  },
  "latency": {
    "labels": ["TTFT", "P50", "P95", "P99"],
    "server1": [150.5, 1200, 2100, 2500],
    "server2": [125.2, 950, 1500, 1800]
  },
  "delta": {
    "labels": ["TPS", "TTFT", "TPOT", "P99", "Error Rate"],
    "values": [29.9, -16.8, -23.1, -28.0, -40.0],
    "colors": ["#10B981", "#10B981", "#10B981", "#10B981", "#10B981"]
  }
}
```

### 4.2.10 `GET /api/charts/timeline/{run_id}`

**Response:**
```json
{
  "timestamps": [
    "2024-04-15T10:30:00Z",
    "2024-04-15T10:30:01Z",
    "2024-04-15T10:30:02Z"
  ],
  "server1": {
    "gpu_util": [45, 67, 82, 78, 65],
    "gpu_temp": [55, 58, 62, 61, 59],
    "vram_used": [10.2, 10.5, 11.1, 10.8, 10.3],
    "cpu_util": [25, 30, 35, 32, 28],
    "ram_used": [12.5, 13.2, 14.1, 13.8, 13.0],
    "gpu_power": [120, 185, 280, 250, 170]
  },
  "server2": {
    "gpu_util": [50, 72, 88, 85, 70],
    "gpu_temp": [52, 56, 60, 58, 55],
    "vram_used": [5.1, 5.8, 6.5, 6.2, 5.5],
    "cpu_util": [28, 35, 42, 38, 30],
    "ram_used": [8.2, 9.1, 10.5, 10.0, 8.8],
    "gpu_power": [95, 140, 210, 195, 130]
  }
}
```

### 4.2.11 `GET /api/charts/summary/{run_id}`

**Response:**
```json
{
  "cards": [
    {
      "label": "TPS Improvement",
      "value": "+29.9%",
      "trend": "up",
      "color": "green",
      "description": "Server 2 generates 29.9% more tokens per second"
    },
    {
      "label": "TTFT Improvement",
      "value": "-16.8%",
      "trend": "down",
      "color": "green",
      "description": "Server 2 responds 16.8% faster to first token"
    },
    {
      "label": "P99 Improvement",
      "value": "-28.0%",
      "trend": "down",
      "color": "green",
      "description": "Server 2 has 28% lower tail latency"
    },
    {
      "label": "Winner",
      "value": "aiDaptive+ Enabled",
      "trend": "neutral",
      "color": "green",
      "description": "Server 2 wins across all major metrics"
    }
  ],
  "overall_winner": "server2",
  "confidence": "high",
  "win_count": {"server1": 0, "server2": 42, "tie": 0}
}
```

### 4.2.12 `GET /api/servers`

**Response:**
```json
{
  "servers": [
    {
      "server_id": "server1",
      "name": "aiDaptive+ Disabled",
      "aidaptive_enabled": false,
      "ollama_url": "http://35.186.159.250:11434",
      "agent_url": "http://35.186.159.250:9100",
      "ollama_online": true,
      "agent_online": true,
      "last_seen_at": "2024-04-15T10:30:00Z",
      "hardware": {
        "gpu_name": "NVIDIA GeForce RTX 4090",
        "gpu_vram_gb": 24.0,
        "gpu_driver": "535.129.03",
        "cpu_name": "Intel Xeon E5-2680 v4 @ 2.40GHz",
        "cpu_cores": 28,
        "ram_total_gb": 64.0,
        "hostname": "ai-server-01",
        "os_version": "Ubuntu 22.04.3 LTS"
      },
      "models": [
        {"name": "llama3.2:1b", "size_gb": 1.3, "format": "gguf", "quantization": "Q4_0"}
      ],
      "current_metrics": {
        "gpu_util_pct": 23.0,
        "gpu_temp_c": 45.0,
        "vram_used_gb": 10.8,
        "cpu_pct": 12.0,
        "ram_used_gb": 18.5
      }
    },
    {
      "server_id": "server2",
      "name": "aiDaptive+ Enabled",
      "aidaptive_enabled": true,
      "ollama_url": "http://34.142.222.133:11434",
      "agent_url": "http://34.142.222.133:9100",
      "ollama_online": true,
      "agent_online": true,
      "last_seen_at": "2024-04-15T10:30:00Z",
      "hardware": {
        "gpu_name": "NVIDIA GeForce RTX 3070",
        "gpu_vram_gb": 8.0,
        "gpu_driver": "535.129.03",
        "cpu_name": "Intel Core i7-12700 @ 2.10GHz",
        "cpu_cores": 20,
        "ram_total_gb": 32.0,
        "hostname": "ai-server-02",
        "os_version": "Ubuntu 22.04.3 LTS"
      },
      "models": [
        {"name": "llama3.2:1b", "size_gb": 1.3, "format": "gguf", "quantization": "Q4_0"}
      ],
      "current_metrics": {
        "gpu_util_pct": 18.0,
        "gpu_temp_c": 42.0,
        "vram_used_gb": 5.2,
        "cpu_pct": 8.0,
        "ram_used_gb": 12.3
      }
    }
  ]
}
```

### 4.2.13 `GET /api/servers/{server_id}/metrics`

**Response:**
```json
{
  "server_id": "server1",
  "timestamp": "2024-04-15T10:30:00Z",
  "gpu": {
    "utilization_pct": 23.0,
    "memory_util_pct": 45.0,
    "temperature_c": 45.0,
    "power_watts": 85.0,
    "power_limit_watts": 350.0,
    "vram_used_gb": 10.8,
    "vram_total_gb": 24.0
  },
  "cpu": {
    "utilization_pct": 12.0,
    "load_avg_1m": 1.25,
    "load_avg_5m": 1.10,
    "load_avg_15m": 0.95
  },
  "memory": {
    "used_gb": 18.5,
    "total_gb": 64.0,
    "available_gb": 45.5
  },
  "ollama": {
    "running": true,
    "models_loaded": ["llama3.2:1b"],
    "pending_requests": 0
  }
}
```

## 4.3 Error Response Format

Tất cả các error response đều tuân theo format thống nhất:

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {},
  "timestamp": "2024-04-15T10:30:00Z"
}
```

| HTTP Code | Error Code | Mô tả |
|-----------|-----------|-------|
| 400 | `bad_request` | Request body không hợp lệ |
| 404 | `not_found` | Resource không tìm thấy |
| 409 | `conflict` | Benchmark đang chạy |
| 500 | `internal_error` | Lỗi server |
| 503 | `service_unavailable` | AI server offline |

---

# 5. UI/UX DESIGN

## 5.1 Design Principles

| Principle | Mô tả |
|-----------|-------|
| **Server-Side Rendering** | Jinja2 templates, giảm JS phức tạp |
| **Responsive** | TailwindCSS, hỗ trợ desktop + tablet |
| **Dark/Light Theme** | Mặc định dark theme, toggle switch |
| **Realtime Updates** | Polling mỗi 2 giây khi benchmark chạy |
| **Accessibility** | Semantic HTML, ARIA labels, keyboard navigation |

## 5.2 Sitemap

```
┌─────────────────────────────────────────────────────────────────┐
│                        aiDaptive Benchmark                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐                                                │
│  │  Dashboard  │ ← Home page                                    │
│  │     /       │                                                │
│  └──────┬──────┘                                                │
│         │                                                        │
│  ┌──────┴──────┬──────────────┬──────────────┬────────────┐    │
│  │             │              │              │            │     │
│  ▼             ▼              ▼              ▼            ▼     │
│ ┌───────┐  ┌────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│ │Servers│  │Benchmark│  │ History  │  │Comparison│  │Settings│ │
│ │/servers│  │/benchmark│  │/history │  │/comparison│  │/settings│ │
│ └───────┘  └────────┘  └────┬─────┘  └──────────┘  └────────┘ │
│                             │                                   │
│                             ▼                                   │
│                      ┌────────────┐                            │
│                      │ Run Detail │                            │
│                      │/history/{id}│                            │
│                      └────────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 5.3 Color System

| Element | Dark Theme | Light Theme | Mục đích |
|---------|-----------|-------------|----------|
| Background | `#0F172A` (slate-900) | `#F8FAFC` (slate-50) | Page background |
| Surface | `#1E293B` (slate-800) | `#FFFFFF` (white) | Cards, panels |
| Border | `#334155` (slate-700) | `#E2E8F0` (slate-200) | Dividers |
| Text Primary | `#F1F5F9` (slate-100) | `#0F172A` (slate-900) | Main text |
| Text Secondary | `#94A3B8` (slate-400) | `#64748B` (slate-500) | Muted text |
| Server 1 | `#EF4444` (red-500) | `#EF4444` (red-500) | aiDaptive+ OFF |
| Server 2 | `#10B981` (emerald-500) | `#10B981` (emerald-500) | aiDaptive+ ON |
| Positive Δ | `#10B981` (emerald-500) | `#10B981` (emerald-500) | Improvement |
| Negative Δ | `#EF4444` (red-500) | `#EF4444` (red-500) | Degradation |
| Warning | `#F59E0B` (amber-500) | `#F59E0B` (amber-500) | Warning states |
| Info | `#3B82F6` (blue-500) | `#3B82F6` (blue-500) | Info states |


## 5.4 Page Specifications

### 5.4.1 Dashboard (`/`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ☰  aiDaptive Benchmark Suite                   🌙/☀️   [Status: Ready]    │
├────────┬────────────────────────────────────────────────────────────────────┤
│        │                                                                     │
│  NAV   │   DASHBOARD                                                        │
│        │   ─────────────────────────────────────────────────────────────    │
│ ┌────┐ │                                                                     │
│ │ 🏠 │ │   QUICK STATS                                                     │
│ │Dash│ │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│ └────┘ │   │  Total Runs     │  │  Last Run       │  │  Avg TPS Gain   │   │
│        │   │      45         │  │  2 hours ago    │  │    +29.9%       │   │
│ ┌────┐ │   │  ↑ 5 this week  │  │  ✓ Completed    │  │  aiDaptive+ wins│   │
│ │ 🖥️ │ │   └─────────────────┘  └─────────────────┘  └─────────────────┘   │
│ │Serv│ │                                                                     │
│ └────┘ │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│        │   │  Success Rate   │  │  Avg Duration   │  │  Win Rate S2    │   │
│ ┌────┐ │   │     93.3%       │  │    14:15        │  │     100%        │   │
│ │ ▶️ │ │   │  42/45 runs     │  │  min:10 max:22  │  │  42/42 wins     │   │
│ │Bench│ │   └─────────────────┘  └─────────────────┘  └─────────────────┘   │
│ └────┘ │                                                                     │
│        │   SERVER STATUS                                                    │
│ ┌────┐ │   ┌────────────────────────────────────────────────────────────┐   │
│ │ 📊 │ │   │                                                            │   │
│ │Hist│ │   │  Server 1 (aiDaptive+ Disabled)              🟢 Online    │   │
│ └────┘ │   │  GPU: RTX 4090 (24GB) | CPU: 28 cores | RAM: 64GB        │   │
│        │   │  GPU: 23% | VRAM: 45% | Temp: 45°C                       │   │
│ ┌────┐ │   │                                                            │   │
│ │ ⚖️ │ │   │  Server 2 (aiDaptive+ Enabled)               🟢 Online    │   │
│ │Comp│ │   │  GPU: RTX 3070 (8GB) | CPU: 20 cores | RAM: 32GB         │   │
│ └────┘ │   │  GPU: 18% | VRAM: 65% | Temp: 42°C                       │   │
│        │   │                                                            │   │
│ ┌────┐ │   └────────────────────────────────────────────────────────────┘   │
│ │ ⚙️ │ │                                                                     │
│ │Sett│ │   RECENT RUNS                                                      │
│ └────┘ │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │ Run ID              │ Status    │ Duration │ TPS Δ  │Winner│   │
│        │   │─────────────────────┼───────────┼──────────┼────────┼──────│   │
│        │   │ run_20240415_143022 │ ✓ Done    │ 15:30    │+29.9%  │ S2 ✓│   │
│        │   │ run_20240415_103000 │ ✓ Done    │ 12:45    │+27.5%  │ S2 ✓│   │
│        │   │ run_20240414_153022 │ ✓ Done    │ 14:20    │+31.2%  │ S2 ✓│   │
│        │   │ run_20240414_091500 │ ✗ Failed  │ 02:15    │  -     │  -  │   │
│        │   │ run_20240413_163045 │ ✓ Done    │ 16:00    │+26.8%  │ S2 ✓│   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   PERFORMANCE TREND (Last 10 Runs)                                 │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │  TPS Δ%                                                    │   │
│        │   │   35│          *                                           │   │
│        │   │     │     *         *    *                                 │   │
│        │   │   30│  *     *         *    *    *                         │   │
│        │   │     │              *              *                        │   │
│        │   │   25│                                                      │   │
│        │   │     └──┬──┬──┬──┬──┬──┬──┬──┬──┬──                       │   │
│        │   │        R1 R2 R3 R4 R5 R6 R7 R8 R9 R10                    │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   [▶ Start New Benchmark]              [View All History →]        │
│        │                                                                     │
└────────┴────────────────────────────────────────────────────────────────────┘
```

### 5.4.2 Servers (`/servers`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ☰  aiDaptive Benchmark Suite                   🌙/☀️                       │
├────────┬────────────────────────────────────────────────────────────────────┤
│        │                                                                     │
│  NAV   │   SERVERS                                     [↻ Refresh] [Auto ⏱]│
│        │   ─────────────────────────────────────────────────────────────    │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │  SERVER 1 - aiDaptive+ DISABLED                🟢 Online  │   │
│        │   ├────────────────────────────────────────────────────────────┤   │
│        │   │                                                            │   │
│        │   │  Connection                                                │   │
│        │   │  ├─ Ollama: http://35.186.159.250:11434       ✓ Connected │   │
│        │   │  │  Response: 12ms                                        │   │
│        │   │  └─ Agent:  http://35.186.159.250:9100        ✓ Connected │   │
│        │   │     Response: 8ms                                         │   │
│        │   │                                                            │   │
│        │   │  Hardware (Auto-detected)                                  │   │
│        │   │  ┌──────────────────────────────────────────────────────┐ │   │
│        │   │  │ Component │ Details                                   │ │   │
│        │   │  │───────────┼──────────────────────────────────────────│ │   │
│        │   │  │ GPU       │ NVIDIA GeForce RTX 4090                  │ │   │
│        │   │  │ VRAM      │ 24 GB GDDR6X                            │ │   │
│        │   │  │ Driver    │ 535.129.03                               │ │   │
│        │   │  │ CUDA      │ 12.2                                     │ │   │
│        │   │  │ CPU       │ Intel Xeon E5-2680 v4 @ 2.40GHz         │ │   │
│        │   │  │ Cores     │ 28 cores / 56 threads                    │ │   │
│        │   │  │ RAM       │ 64 GB DDR4                               │ │   │
│        │   │  │ OS        │ Ubuntu 22.04.3 LTS                       │ │   │
│        │   │  │ Hostname  │ ai-server-01                             │ │   │
│        │   │  └──────────────────────────────────────────────────────┘ │   │
│        │   │                                                            │   │
│        │   │  Models Loaded                                             │   │
│        │   │  ┌──────────────────────────────────────────────────────┐ │   │
│        │   │  │ Name          │ Size   │ Format │ Quantization       │ │   │
│        │   │  │───────────────┼────────┼────────┼────────────────────│ │   │
│        │   │  │ llama3.2:1b   │ 1.3 GB │ GGUF   │ Q4_0              │ │   │
│        │   │  └──────────────────────────────────────────────────────┘ │   │
│        │   │                                                            │   │
│        │   │  Live Resource Usage                                       │   │
│        │   │  ┌──────────────────────────────────────────────────────┐ │   │
│        │   │  │ GPU Util:  23% ████░░░░░░░░░░░░░░░░                 │ │   │
│        │   │  │ VRAM:      45% █████████░░░░░░░░░░░ (10.8/24.0 GB)  │ │   │
│        │   │  │ GPU Temp:  45°C ████████░░░░░░░░░░░░                │ │   │
│        │   │  │ GPU Power: 85W  ████░░░░░░░░░░░░░░░░ (85/350 W)    │ │   │
│        │   │  │ CPU:       12% ██░░░░░░░░░░░░░░░░░░                 │ │   │
│        │   │  │ RAM:       29% █████░░░░░░░░░░░░░░░ (18.5/64.0 GB) │ │   │
│        │   │  │ Load Avg:  1.25 / 1.10 / 0.95                       │ │   │
│        │   │  └──────────────────────────────────────────────────────┘ │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │  SERVER 2 - aiDaptive+ ENABLED                 🟢 Online  │   │
│        │   ├────────────────────────────────────────────────────────────┤   │
│        │   │                                                            │   │
│        │   │  Connection                                                │   │
│        │   │  ├─ Ollama: http://34.142.222.133:11434       ✓ Connected │   │
│        │   │  │  Response: 15ms                                        │   │
│        │   │  └─ Agent:  http://34.142.222.133:9100        ✓ Connected │   │
│        │   │     Response: 10ms                                        │   │
│        │   │                                                            │   │
│        │   │  Hardware (Auto-detected)                                  │   │
│        │   │  ┌──────────────────────────────────────────────────────┐ │   │
│        │   │  │ Component │ Details                                   │ │   │
│        │   │  │───────────┼──────────────────────────────────────────│ │   │
│        │   │  │ GPU       │ NVIDIA GeForce RTX 3070                  │ │   │
│        │   │  │ VRAM      │ 8 GB GDDR6                              │ │   │
│        │   │  │ Driver    │ 535.129.03                               │ │   │
│        │   │  │ CUDA      │ 12.2                                     │ │   │
│        │   │  │ CPU       │ Intel Core i7-12700 @ 2.10GHz           │ │   │
│        │   │  │ Cores     │ 20 cores / 28 threads                    │ │   │
│        │   │  │ RAM       │ 32 GB DDR4                               │ │   │
│        │   │  │ OS        │ Ubuntu 22.04.3 LTS                       │ │   │
│        │   │  │ Hostname  │ ai-server-02                             │ │   │
│        │   │  └──────────────────────────────────────────────────────┘ │   │
│        │   │                                                            │   │
│        │   │  Models Loaded                                             │   │
│        │   │  ┌──────────────────────────────────────────────────────┐ │   │
│        │   │  │ Name          │ Size   │ Format │ Quantization       │ │   │
│        │   │  │───────────────┼────────┼────────┼────────────────────│ │   │
│        │   │  │ llama3.2:1b   │ 1.3 GB │ GGUF   │ Q4_0              │ │   │
│        │   │  └──────────────────────────────────────────────────────┘ │   │
│        │   │                                                            │   │
│        │   │  Live Resource Usage                                       │   │
│        │   │  ┌──────────────────────────────────────────────────────┐ │   │
│        │   │  │ GPU Util:  18% ███░░░░░░░░░░░░░░░░░                 │ │   │
│        │   │  │ VRAM:      65% █████████████░░░░░░░ (5.2/8.0 GB)    │ │   │
│        │   │  │ GPU Temp:  42°C ████████░░░░░░░░░░░░                │ │   │
│        │   │  │ GPU Power: 65W  █████░░░░░░░░░░░░░░ (65/220 W)     │ │   │
│        │   │  │ CPU:        8% █░░░░░░░░░░░░░░░░░░░                 │ │   │
│        │   │  │ RAM:       38% ███████░░░░░░░░░░░░ (12.3/32.0 GB)  │ │   │
│        │   │  │ Load Avg:  0.85 / 0.72 / 0.68                       │ │   │
│        │   │  └──────────────────────────────────────────────────────┘ │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   HARDWARE COMPARISON                                              │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │ Component │ Server 1 (Disabled) │ Server 2 (Enabled) │ Ratio│  │
│        │   │───────────┼─────────────────────┼────────────────────┼──────│  │
│        │   │ GPU       │ RTX 4090            │ RTX 3070           │ 3.0x │  │
│        │   │ VRAM      │ 24 GB               │ 8 GB               │ 3.0x │  │
│        │   │ CPU Cores │ 28                  │ 20                 │ 1.4x │  │
│        │   │ RAM       │ 64 GB               │ 32 GB              │ 2.0x │  │
│        │   │ Note: S1 has stronger hardware, S2 has aiDaptive+ enabled   │  │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
└────────┴────────────────────────────────────────────────────────────────────┘
```

### 5.4.3 Benchmark (`/benchmark`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ☰  aiDaptive Benchmark Suite                   🌙/☀️                       │
├────────┬────────────────────────────────────────────────────────────────────┤
│        │                                                                     │
│  NAV   │   BENCHMARK CONTROL                                                │
│        │   ─────────────────────────────────────────────────────────────    │
│        │                                                                     │
│        │   PREFLIGHT CHECK                                                  │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │  ✓ Server 1 Ollama    ✓ Server 1 Agent                    │   │
│        │   │  ✓ Server 2 Ollama    ✓ Server 2 Agent                    │   │
│        │   │  ✓ PostgreSQL         ✓ Model: llama3.2:1b loaded         │   │
│        │   │  ✓ Disk Space OK      ✓ No benchmark running              │   │
│        │   │                                                            │   │
│        │   │  All checks passed! Ready to benchmark. ✓                  │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   CONFIGURATION                                                    │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │  Test Suite                                                │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ ● All Suites (Full benchmark)                      │   │   │
│        │   │  │ ○ Single Request (TTFT, TPS per request)           │   │   │
│        │   │  │ ○ Concurrent Load (RPS, P99 under load)            │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  Servers                                                   │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ ☑ Server 1 (aiDaptive+ Disabled) - 🟢 Online      │   │   │
│        │   │  │ ☑ Server 2 (aiDaptive+ Enabled)  - 🟢 Online      │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  Model                                                     │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ llama3.2:1b                                    ▼   │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  Advanced Options                                  [▼]    │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ Warmup Requests:     [3    ]                       │   │   │
│        │   │  │ Repeat Count:        [5    ]                       │   │   │
│        │   │  │ Concurrency Levels:  [1, 5, 10]                    │   │   │
│        │   │  │ Request Timeout (s): [120  ]                       │   │   │
│        │   │  │ Cooldown Between (s):[10   ]                       │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  Notes (optional)                                          │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ Production benchmark run for v2.0 release          │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  Tags (optional)                                           │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ [production] [v2.0] [+ Add tag]                    │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  Estimated Duration: ~15 minutes (84 tests)                │   │
│        │   │                                                            │   │
│        │   │           ┌──────────────────────────────┐                │   │
│        │   │           │    ▶ START BENCHMARK         │                │   │
│        │   │           └──────────────────────────────┘                │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
└────────┴────────────────────────────────────────────────────────────────────┘
```

**Trạng thái khi benchmark đang chạy:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ☰  aiDaptive Benchmark Suite                   🌙/☀️   [🔴 Running]       │
├────────┬────────────────────────────────────────────────────────────────────┤
│        │                                                                     │
│  NAV   │   BENCHMARK RUNNING                                                │
│        │   ─────────────────────────────────────────────────────────────    │
│        │                                                                     │
│        │   PROGRESS                                                         │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │  Run ID: run_20240415_143022                              │   │
│        │   │  Status: 🔴 Running                                       │   │
│        │   │                                                            │   │
│        │   │  Phase: ③ Benchmarking  (① Preflight ✓  ② Warmup ✓)      │   │
│        │   │  Current: server1 / code_generation / ollama_native       │   │
│        │   │                                                            │   │
│        │   │  Progress: 35 / 84 tests                                  │   │
│        │   │  ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░  42%     │   │
│        │   │                                                            │   │
│        │   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │   │
│        │   │  │ Elapsed      │  │ Remaining    │  │ ETA          │    │   │
│        │   │  │ 5:32         │  │ ~7:45        │  │ ~14:47:07    │    │   │
│        │   │  └──────────────┘  └──────────────┘  └──────────────┘    │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   LIVE METRICS                                                     │
│        │   ┌──────────────────────────┐  ┌──────────────────────────┐      │
│        │   │  Server 1 (Disabled)     │  │  Server 2 (Enabled)      │      │
│        │   │                          │  │                          │      │
│        │   │  Last TPS: 45.2          │  │  Last TPS: 58.7          │      │
│        │   │  Last TTFT: 150 ms       │  │  Last TTFT: 125 ms       │      │
│        │   │                          │  │                          │      │
│        │   │  GPU:  78% ████████████░ │  │  GPU:  85% █████████████ │      │
│        │   │  VRAM: 52% ██████████░░░ │  │  VRAM: 72% ██████████░░ │      │
│        │   │  CPU:  32% ██████░░░░░░░ │  │  CPU:  38% ███████░░░░░ │      │
│        │   │  Temp: 62°C              │  │  Temp: 60°C              │      │
│        │   └──────────────────────────┘  └──────────────────────────┘      │
│        │                                                                     │
│        │   TEST LOG (Live)                                                  │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │ 14:35:22 ✓ server1/simple_chat/ollama     TPS:45.2 TTFT:150│  │
│        │   │ 14:35:18 ✓ server2/simple_chat/ollama     TPS:58.7 TTFT:125│  │
│        │   │ 14:35:12 ✓ server1/simple_chat/oha        TPS:42.1 TTFT:155│  │
│        │   │ 14:35:07 ✓ server2/simple_chat/oha        TPS:55.3 TTFT:129│  │
│        │   │ 14:35:01 ✓ server1/code_gen/ollama        TPS:40.5 TTFT:149│  │
│        │   │ 14:34:55 ⟳ server1/code_gen/oha           Running...       │  │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ┌──────────────────────────────┐                                │
│        │   │    ⏹ STOP BENCHMARK          │                                │
│        │   └──────────────────────────────┘                                │
│        │                                                                     │
│        │   ⚠ Stopping will save partial results. You can view them          │
│        │     in History.                                                     │
│        │                                                                     │
└────────┴────────────────────────────────────────────────────────────────────┘
```

### 5.4.4 History (`/history`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ☰  aiDaptive Benchmark Suite                   🌙/☀️                       │
├────────┬────────────────────────────────────────────────────────────────────┤
│        │                                                                     │
│  NAV   │   BENCHMARK HISTORY                                                │
│        │   ─────────────────────────────────────────────────────────────    │
│        │                                                                     │
│        │   FILTERS                                                          │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │ Status: [All ▼]  Suite: [All ▼]  Tag: [All ▼]             │   │
│        │   │ Date:   [From ___] to [To ___]   [🔍 Search run ID...]    │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │ ☐ │ Run ID              │ Date         │Status │Duration│  │   │
│        │   │   │ Suite / Model       │ Tests        │TPS Δ  │Winner  │  │   │
│        │   │───┼─────────────────────┼──────────────┼───────┼────────│  │   │
│        │   │   │                     │              │       │        │  │   │
│        │   │ ☐ │ run_20240415_143022 │ Apr 15, 14:30│  ✓    │ 15:30  │  │   │
│        │   │   │ all / llama3.2:1b   │ 84/84        │+29.9% │ 🏆 S2  │  │   │
│        │   │   │ Tags: [production] [v2.0]                            │  │   │
│        │   │   │                     │              │       │        │  │   │
│        │   │ ☐ │ run_20240415_103000 │ Apr 15, 10:30│  ✓    │ 12:45  │  │   │
│        │   │   │ single_request/llama│ 42/42        │+27.5% │ 🏆 S2  │  │   │
│        │   │   │                     │              │       │        │  │   │
│        │   │ ☐ │ run_20240414_153022 │ Apr 14, 15:30│  ✓    │ 14:20  │  │   │
│        │   │   │ all / llama3.2:1b   │ 84/84        │+31.2% │ 🏆 S2  │  │   │
│        │   │   │                     │              │       │        │  │   │
│        │   │ ☐ │ run_20240414_091500 │ Apr 14, 09:15│  ✗    │ 02:15  │  │   │
│        │   │   │ all / llama3.2:1b   │ 15/84        │  -    │  -     │  │   │
│        │   │   │ Error: Server 1 connection timeout                   │  │   │
│        │   │   │                     │              │       │        │  │   │
│        │   │ ☐ │ run_20240413_163045 │ Apr 13, 16:30│  ✓    │ 16:00  │  │   │
│        │   │   │ concurrent_load/llama│ 42/42       │+26.8% │ 🏆 S2  │  │   │
│        │   │   │                     │              │       │        │  │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   Actions: [🗑 Delete Selected]  [📊 Compare Selected (max 2)]    │
│        │                                                                     │
│        │   Showing 1-20 of 45     [< Prev]  [1] [2] [3]  [Next >]          │
│        │                                                                     │
└────────┴────────────────────────────────────────────────────────────────────┘
```

### 5.4.5 Run Detail (`/history/{run_id}`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ☰  aiDaptive Benchmark Suite                   🌙/☀️                       │
├────────┬────────────────────────────────────────────────────────────────────┤
│        │                                                                     │
│  NAV   │   ← Back to History                                                │
│        │                                                                     │
│        │   RUN DETAIL: run_20240415_143022                                  │
│        │   ─────────────────────────────────────────────────────────────    │
│        │                                                                     │
│        │   SUMMARY CARDS                                                    │
│        │   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐     │
│        │   │ Status     │ │ Duration   │ │ Tests      │ │ Winner     │     │
│        │   │  ✓ Done    │ │  15:30     │ │  84/84     │ │ 🏆 S2      │     │
│        │   │  Completed │ │  930 sec   │ │  100%      │ │ aiDaptive+ │     │
│        │   └────────────┘ └────────────┘ └────────────┘ └────────────┘     │
│        │                                                                     │
│        │   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐     │
│        │   │ TPS Gain   │ │ TTFT Gain  │ │ P99 Gain   │ │ Error Δ    │     │
│        │   │  +29.9%    │ │  -16.8%    │ │  -28.0%    │ │  -40.0%    │     │
│        │   │  ↑ Higher  │ │  ↓ Lower   │ │  ↓ Lower   │ │  ↓ Lower   │     │
│        │   │  is better │ │  is better │ │  is better │ │  is better │     │
│        │   └────────────┘ └────────────┘ └────────────┘ └────────────┘     │
│        │                                                                     │
│        │   RUN INFO                                                         │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │ Suite: all                     Model: llama3.2:1b          │   │
│        │   │ Environment: lan               Tags: [production] [v2.0]   │   │
│        │   │ Started: Apr 15, 2024 14:30:22                             │   │
│        │   │ Finished: Apr 15, 2024 14:45:52                            │   │
│        │   │ Notes: Production benchmark run for v2.0 release           │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ─── COMPARISON SUMMARY TABLE ───                                 │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │  Metric         │ S1 (Disabled) │ S2 (Enabled)  │ Delta   │   │
│        │   │  ────────────────┼───────────────┼───────────────┼──────── │   │
│        │   │  Avg TPS        │ 45.2 tok/s    │ 58.7 tok/s    │+29.9% ✓│   │
│        │   │  Avg TTFT       │ 150.5 ms      │ 125.2 ms      │-16.8% ✓│   │
│        │   │  Avg TPOT       │ 22.1 ms       │ 17.0 ms       │-23.1% ✓│   │
│        │   │  Avg ITL        │ 23.5 ms       │ 18.2 ms       │-22.6% ✓│   │
│        │   │  Avg P50        │ 1200 ms       │ 950 ms        │-20.8% ✓│   │
│        │   │  Avg P95        │ 2100 ms       │ 1500 ms       │-28.6% ✓│   │
│        │   │  Avg P99        │ 2500 ms       │ 1800 ms       │-28.0% ✓│   │
│        │   │  Total Tokens   │ 15,000        │ 19,500        │+30.0% ✓│   │
│        │   │  Error Rate     │ 0.5%          │ 0.3%          │-40.0% ✓│   │
│        │   │  Total Requests │ 84            │ 84            │  -      │   │
│        │   │  Success Reqs   │ 83            │ 84            │  -      │   │
│        │   │                                                            │   │
│        │   │  OVERALL WINNER: 🏆 Server 2 (aiDaptive+ Enabled)         │   │
│        │   │  Wins all 9 metric categories                              │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ─── CHARTS ───                                     [Tab Layout] │
│        │                                                                     │
│        │   [TPS by Tool] [Latency Comparison] [GPU Timeline] [Delta %]     │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │  TPS BY TOOL                                    [Bar Chart]│   │
│        │   │                                                            │   │
│        │   │    65│                                                     │   │
│        │   │      │                    ██                               │   │
│        │   │    55│              ██    ██         ██                    │   │
│        │   │      │        ██    ██    ██    ██    ██    ██             │   │
│        │   │    45│  ██    ██    ██    ██    ██    ██    ██    ██       │   │
│        │   │      │  ██    ██    ██    ██    ██    ██    ██    ██       │   │
│        │   │    35│  ██    ██    ██    ██    ██    ██    ██    ██       │   │
│        │   │      │  ██    ██    ██    ██    ██    ██    ██    ██       │   │
│        │   │    25│  ██    ██    ██    ██    ██    ██    ██    ██       │   │
│        │   │      │  ██    ██    ██    ██    ██    ██    ██    ██       │   │
│        │   │     0└──────────────────────────────────────────────       │   │
│        │   │        ollama  oha   k6  litellm vllm locust llmperf      │   │
│        │   │                                                            │   │
│        │   │    ■ Server 1 (Disabled - Red)                             │   │
│        │   │    ■ Server 2 (Enabled - Green)                            │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ┌────────────────────────────┐ ┌─────────────────────────────┐  │
│        │   │  LATENCY COMPARISON        │ │  DELTA % BY METRIC          │  │
│        │   │  (Grouped Bar)             │ │  (Horizontal Bar)           │  │
│        │   │                            │ │                             │  │
│        │   │  2500│  ██                 │ │  TPS     ████████████ +30%  │  │
│        │   │      │  ██  ██             │ │  TTFT    ██████  -17%       │  │
│        │   │  2000│  ██  ██             │ │  TPOT    ████████  -23%     │  │
│        │   │      │  ██  ██  ██         │ │  P99     ██████████ -28%    │  │
│        │   │  1500│  ██  ██  ██  ██     │ │  Error   ████████████ -40%  │  │
│        │   │      │  ██  ██  ██  ██     │ │                             │  │
│        │   │  1000│  ██  ██  ██  ██     │ │  ■ Green = Improvement      │  │
│        │   │      │  ██  ██  ██  ██     │ │                             │  │
│        │   │   500│  ██  ██  ██  ██     │ │                             │  │
│        │   │      │  ██  ██  ██  ██     │ │                             │  │
│        │   │     0└──────────────────   │ │                             │  │
│        │   │       TTFT P50 P95 P99     │ │                             │  │
│        │   └────────────────────────────┘ └─────────────────────────────┘  │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │  GPU UTILIZATION TIMELINE                     [Line Chart] │   │
│        │   │                                                            │   │
│        │   │  100%│           /──\                                      │   │
│        │   │      │         /      \         S2 (Green)                 │   │
│        │   │   75%│       /          \                                  │   │
│        │   │      │     /    /────\    \___                             │   │
│        │   │   50%│   /    /        \       \___                        │   │
│        │   │      │  /   /            \          \     S1 (Red)         │   │
│        │   │   25%│/   /                \___       \___                 │   │
│        │   │      │  /                       \___       \_              │   │
│        │   │    0%└──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──              │   │
│        │   │         0  1  2  3  4  5  6  7  8  9 10 11 12 min         │   │
│        │   │                                                            │   │
│        │   │    ── Server 1 (Red)  ── Server 2 (Green)                  │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │  GPU TEMPERATURE TIMELINE                     [Line Chart] │   │
│        │   │                                                            │   │
│        │   │   70°│           /──\                                      │   │
│        │   │      │         /      \                                    │   │
│        │   │   60°│       /    /──\  \___                               │   │
│        │   │      │     /    /      \     \___                          │   │
│        │   │   50°│   /    /          \___     \___                     │   │
│        │   │      │  /   /                 \___     \_                  │   │
│        │   │   40°│/   /                        \___                    │   │
│        │   │      └──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──              │   │
│        │   │         0  1  2  3  4  5  6  7  8  9 10 11 12 min         │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ─── DETAILED RESULTS TABLE ───                                   │
│        │                                                                     │
│        │   Filter: [All Tools ▼]  [All Scenarios ▼]  [All Servers ▼]       │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │Server│Tool   │Scenario    │TPS  │TTFT │P50  │P95  │P99   │   │
│        │   │──────┼───────┼────────────┼─────┼─────┼─────┼─────┼──────│   │
│        │   │ S1   │ollama │simple_chat │45.2 │150  │1200 │2100 │2500  │   │
│        │   │ S2   │ollama │simple_chat │58.7 │125  │ 950 │1500 │1800  │   │
│        │   │      │       │            │     │     │     │     │      │   │
│        │   │ S1   │ollama │code_gen    │42.1 │155  │1250 │2200 │2600  │   │
│        │   │ S2   │ollama │code_gen    │55.3 │129  │ 980 │1550 │1850  │   │
│        │   │      │       │            │     │     │     │     │      │   │
│        │   │ S1   │oha    │simple_chat │40.5 │149  │1180 │2050 │2450  │   │
│        │   │ S2   │oha    │simple_chat │52.8 │122  │ 920 │1480 │1780  │   │
│        │   │      │       │            │     │     │     │     │      │   │
│        │   │ S1   │k6     │simple_chat │38.9 │160  │1300 │2300 │2700  │   │
│        │   │ S2   │k6     │simple_chat │50.2 │131  │1020 │1600 │1920  │   │
│        │   │      │       │            │     │     │     │     │      │   │
│        │   │ ...  │...    │...         │...  │...  │...  │...  │...   │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   PER-TOOL COMPARISON                                              │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │  Tool     │Scenario    │S1 TPS│S2 TPS│Δ TPS │S1 TTFT│S2  │   │
│        │   │           │            │      │      │      │  TTFT │Δ   │   │
│        │   │  ─────────┼────────────┼──────┼──────┼──────┼───────┼──  │   │
│        │   │  ollama   │simple_chat │ 45.2 │ 58.7 │+29.9%│150.5  │-17%│   │
│        │   │  ollama   │code_gen    │ 42.1 │ 55.3 │+31.4%│155.2  │-17%│   │
│        │   │  ollama   │long_output │ 43.8 │ 56.8 │+29.7%│148.9  │-18%│   │
│        │   │  oha      │simple_chat │ 40.5 │ 52.8 │+30.4%│149.2  │-18%│   │
│        │   │  oha      │code_gen    │ 38.2 │ 50.1 │+31.2%│153.8  │-16%│   │
│        │   │  k6       │simple_chat │ 38.9 │ 50.2 │+29.0%│160.3  │-18%│   │
│        │   │  litellm  │simple_chat │ 41.5 │ 53.5 │+28.9%│157.2  │-17%│   │
│        │   │  vllm     │simple_chat │ 44.8 │ 57.1 │+27.5%│152.1  │-17%│   │
│        │   │  locust   │simple_chat │ 41.2 │ 53.8 │+30.6%│157.8  │-17%│   │
│        │   │  llmperf  │simple_chat │ 43.5 │ 56.2 │+29.2%│149.3  │-16%│   │
│        │   │                                                            │   │
│        │   │  SUMMARY: Server 2 wins ALL 42 comparisons                 │   │
│        │   │  Average TPS Δ: +29.9%  |  Average TTFT Δ: -16.8%         │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   EXPORT                                                           │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │  [📄 Export PDF Report]  [📊 Export CSV Data]              │   │
│        │   │  [📋 Copy Summary]       [🔗 Share Link]                   │   │
│        │   │                                                            │   │
│        │   │  PDF Report includes:                                      │   │
│        │   │  - Summary cards & comparison table                        │   │
│        │   │  - All charts (TPS, Latency, GPU Timeline, Delta)          │   │
│        │   │  - Detailed results table                                  │   │
│        │   │  - Hardware specifications                                 │   │
│        │   │  - Run configuration                                       │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
└────────┴────────────────────────────────────────────────────────────────────┘
```


### 5.4.6 Comparison (`/comparison`) (tiếp)

```
│        │   PER-TOOL CROSS-RUN COMPARISON                                    │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │  Tool     │ Run A TPS Δ │ Run B TPS Δ │ Better Run        │   │
│        │   │  ──────────┼─────────────┼─────────────┼────────────────── │   │
│        │   │  ollama    │ +29.9%      │ +27.5%      │ Run A (+2.4pp)    │   │
│        │   │  oha       │ +30.4%      │ +28.1%      │ Run A (+2.3pp)    │   │
│        │   │  k6        │ +29.0%      │ +26.8%      │ Run A (+2.2pp)    │   │
│        │   │  litellm   │ +28.9%      │ +27.2%      │ Run A (+1.7pp)    │   │
│        │   │  vllm_bench│ +27.5%      │ +26.0%      │ Run A (+1.5pp)    │   │
│        │   │  locust    │ +30.6%      │ +28.5%      │ Run A (+2.1pp)    │   │
│        │   │  llmperf   │ +29.2%      │ +27.8%      │ Run A (+1.4pp)    │   │
│        │   │                                                            │   │
│        │   │  AVERAGE   │ +29.4%      │ +27.4%      │ Run A (+2.0pp)    │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   HARDWARE CONTEXT                                                 │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │  Conditions     │ Run A (Apr 15)    │ Run B (Apr 14)      │   │
│        │   │  ────────────────┼───────────────────┼──────────────────── │   │
│        │   │  S1 Avg GPU%    │ 72%               │ 70%                 │   │
│        │   │  S2 Avg GPU%    │ 80%               │ 78%                 │   │
│        │   │  S1 Avg Temp    │ 62°C              │ 60°C                │   │
│        │   │  S2 Avg Temp    │ 60°C              │ 58°C                │   │
│        │   │  S1 Peak VRAM   │ 11.2 GB / 24 GB   │ 11.0 GB / 24 GB    │   │
│        │   │  S2 Peak VRAM   │ 6.8 GB / 8 GB     │ 6.5 GB / 8 GB      │   │
│        │   │  Environment    │ LAN               │ LAN                 │   │
│        │   │                                                            │   │
│        │   │  Note: Similar hardware conditions across both runs.       │   │
│        │   │  Differences likely due to thermal/background variation.    │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   [📄 Export Comparison PDF]  [📊 Export Comparison CSV]           │
│        │                                                                     │
└────────┴────────────────────────────────────────────────────────────────────┘
```

### 5.4.7 Settings (`/settings`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ☰  aiDaptive Benchmark Suite                   🌙/☀️                       │
├────────┬────────────────────────────────────────────────────────────────────┤
│        │                                                                     │
│  NAV   │   SETTINGS                                                         │
│        │   ─────────────────────────────────────────────────────────────    │
│        │                                                                     │
│        │   ─── SERVER CONFIGURATION ───                                     │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │  Server 1 (aiDaptive+ Disabled)                           │   │
│        │   │                                                            │   │
│        │   │  Display Name:                                             │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ aiDaptive+ Disabled                                │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  Ollama URL:                                               │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ http://35.186.159.250:11434                        │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  Agent URL:                                                │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ http://35.186.159.250:9100                         │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  aiDaptive+ Enabled: [ ] (unchecked)                      │   │
│        │   │                                                            │   │
│        │   │  [Test Connection]  Status: ✓ Connected                   │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │  Server 2 (aiDaptive+ Enabled)                            │   │
│        │   │                                                            │   │
│        │   │  Display Name:                                             │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ aiDaptive+ Enabled                                 │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  Ollama URL:                                               │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ http://34.142.222.133:11434                        │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  Agent URL:                                                │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ http://34.142.222.133:9100                         │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  aiDaptive+ Enabled: [✓] (checked)                       │   │
│        │   │                                                            │   │
│        │   │  [Test Connection]  Status: ✓ Connected                   │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ─── BENCHMARK DEFAULTS ───                                       │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │  Default Model:                                            │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ llama3.2:1b                                    ▼   │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  Warmup Requests:        Repeat Count:                     │   │
│        │   │  ┌──────────────┐        ┌──────────────┐                 │   │
│        │   │  │ 3            │        │ 5            │                 │   │
│        │   │  └──────────────┘        └──────────────┘                 │   │
│        │   │                                                            │   │
│        │   │  Concurrency Levels:                                       │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ 1, 5, 10                                           │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  Request Timeout (seconds):   Cooldown Between Tests (s): │   │
│        │   │  ┌──────────────┐             ┌──────────────┐            │   │
│        │   │  │ 120          │             │ 10           │            │   │
│        │   │  └──────────────┘             └──────────────┘            │   │
│        │   │                                                            │   │
│        │   │  Max Tokens per Response:      Temperature:                │   │
│        │   │  ┌──────────────┐             ┌──────────────┐            │   │
│        │   │  │ 512          │             │ 0.7          │            │   │
│        │   │  └──────────────┘             └──────────────┘            │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ─── SCENARIOS ───                                                │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │  Active Scenarios:                                         │   │
│        │   │  ☑ simple_chat      - "Explain quantum computing"         │   │
│        │   │  ☑ code_generation  - "Write a Python function..."        │   │
│        │   │  ☑ long_output      - "Write a detailed essay..."         │   │
│        │   │  ☑ reasoning        - "Solve this math problem..."        │   │
│        │   │  ☑ translation      - "Translate the following..."        │   │
│        │   │  ☑ summarization    - "Summarize this article..."         │   │
│        │   │                                                            │   │
│        │   │  [+ Add Custom Scenario]                                   │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ─── ACTIVE TOOLS ───                                             │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │  ☑ Ollama Native API      (Built-in, always available)    │   │
│        │   │  ☑ oha                    (HTTP load testing)             │   │
│        │   │  ☑ k6                     (Load testing framework)        │   │
│        │   │  ☑ LiteLLM                (OpenAI-compatible proxy)       │   │
│        │   │  ☑ Locust                 (Python-based load testing)     │   │
│        │   │  ☑ LLMPerf               (LLM-specific benchmark)        │   │
│        │   │  ☑ vLLM Benchmark         (vLLM benchmark utility)       │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ─── DATABASE ───                                                 │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │  PostgreSQL Connection:                                    │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ postgresql://user:pass@localhost:5432/aidaptive     │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │  Status: ✓ Connected | Tables: 5 | Total Records: 8,240  │   │
│        │   │                                                            │   │
│        │   │  Data Retention:                                           │   │
│        │   │  ┌────────────────────────────────────────────────────┐   │   │
│        │   │  │ Hardware Snapshots: 90 days    ▼                    │   │   │
│        │   │  │ Benchmark Results: Unlimited   ▼                    │   │   │
│        │   │  └────────────────────────────────────────────────────┘   │   │
│        │   │                                                            │   │
│        │   │  [🗑 Purge Old Data]  [📦 Export All Data]                │   │
│        │   │  [🔄 Reset Database]  (requires confirmation)             │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ─── APPEARANCE ───                                               │
│        │                                                                     │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │                                                            │   │
│        │   │  Theme:  ● Dark   ○ Light   ○ System                      │   │
│        │   │                                                            │   │
│        │   │  Chart Style: ● Default  ○ High Contrast                  │   │
│        │   │                                                            │   │
│        │   │  Auto-refresh interval (seconds): [5    ]                  │   │
│        │   │                                                            │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        │   ┌──────────────────────────────┐  ┌──────────────────────────┐  │
│        │   │    💾 SAVE SETTINGS          │  │    ↻ RESET TO DEFAULTS  │  │
│        │   └──────────────────────────────┘  └──────────────────────────┘  │
│        │                                                                     │
│        │   ─── ABOUT ───                                                    │
│        │   ┌────────────────────────────────────────────────────────────┐   │
│        │   │  aiDaptive Benchmark Suite v2.0                           │   │
│        │   │  Build: 2024.04.15                                        │   │
│        │   │  Python: 3.10.12 | FastAPI: 0.104.1                       │   │
│        │   │  PostgreSQL: 15.4 | Chart.js: 4.4.0                       │   │
│        │   │  © 2024 aiDaptive Inc. All rights reserved.               │   │
│        │   └────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
└────────┴────────────────────────────────────────────────────────────────────┘
```

---

# 6. BENCHMARK TOOLS

## 6.1 Tool Overview

| # | Tool | Loại | Cài đặt | Mục đích chính |
|---|------|------|---------|----------------|
| T1 | **Ollama Native API** | Built-in | Python requests | Đo TTFT, TPS chính xác nhất |
| T2 | **oha** | HTTP load tester | Rust binary | Throughput & latency percentiles |
| T3 | **k6** | Load testing | Go binary | Concurrent load, scripted scenarios |
| T4 | **LiteLLM** | LLM proxy | Python package | OpenAI-compatible benchmark |
| T5 | **Locust** | Load testing | Python package | Distributed load testing |
| T6 | **LLMPerf** | LLM benchmark | Python package | LLM-specific metrics |
| T7 | **vLLM Benchmark** | LLM benchmark | Python script | Throughput-focused |

## 6.2 Tool Details

### 6.2.1 Ollama Native API (`ollama_adapter.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                    OLLAMA NATIVE ADAPTER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Endpoint:    POST {ollama_url}/api/generate                    │
│  Mode:        Streaming (SSE)                                   │
│  Metrics:     TTFT, TPOT, TPS, ITL, Total Tokens                │
│                                                                  │
│  Request Body:                                                   │
│  {                                                               │
│    "model": "llama3.2:1b",                                      │
│    "prompt": "<scenario_prompt>",                                │
│    "stream": true,                                               │
│    "options": {                                                  │
│      "num_predict": 512,                                        │
│      "temperature": 0.7                                         │
│    }                                                             │
│  }                                                               │
│                                                                  │
│  Measurement Logic:                                              │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  t0 = time.perf_counter()    ← Request sent           │      │
│  │  t1 = first_chunk_received   ← TTFT = t1 - t0         │      │
│  │  for each chunk:                                       │      │
│  │    token_times.append(time.perf_counter())             │      │
│  │  t_end = last_chunk_received                           │      │
│  │                                                        │      │
│  │  TTFT = (t1 - t0) * 1000          # ms                │      │
│  │  TPS  = total_tokens / (t_end - t1) # tokens/sec      │      │
│  │  TPOT = (t_end - t1) / total_tokens * 1000  # ms      │      │
│  │  ITL  = mean(diff(token_times)) * 1000       # ms      │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
│  Output Metrics:                                                 │
│  {                                                               │
│    "ttft_ms": 125.3,                                            │
│    "tpot_ms": 17.2,                                             │
│    "tps": 58.1,                                                 │
│    "itl_ms": 18.5,                                              │
│    "prompt_tokens": 25,                                         │
│    "completion_tokens": 487,                                    │
│    "total_tokens": 512                                          │
│  }                                                               │
│                                                                  │
│  Đặc điểm:                                                      │
│  + Đo chính xác nhất (direct API call)                          │
│  + Không overhead từ tool bên ngoài                              │
│  + Streaming cho phép đo ITL chính xác                           │
│  - Chỉ 1 request tại 1 thời điểm (single concurrency)           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2.2 oha (`oha_adapter.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                         OHA ADAPTER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Binary:      oha (Rust-based HTTP load generator)              │
│  Install:     cargo install oha                                 │
│  Mode:        HTTP POST with concurrency                        │
│  Metrics:     RPS, Latency percentiles, Error rate              │
│                                                                  │
│  Command:                                                        │
│  oha -n {total_requests}                                        │
│      -c {concurrency}                                           │
│      -m POST                                                    │
│      -H "Content-Type: application/json"                        │
│      -d '{request_body}'                                        │
│      -j                          # JSON output                  │
│      --latency-correction        # coordinated omission fix     │
│      {ollama_url}/api/generate                                  │
│                                                                  │
│  Concurrency Levels: [1, 5, 10, 20, 50]                        │
│                                                                  │
│  Parsed JSON Output:                                             │
│  {                                                               │
│    "summary": {                                                  │
│      "successRate": 0.997,                                      │
│      "total": 100,                                              │
│      "slowest": 3.245,                                          │
│      "fastest": 0.832,                                          │
│      "average": 1.523,                                          │
│      "requestsPerSec": 6.57,                                   │
│      "totalData": 524288                                        │
│    },                                                            │
│    "responseTimeHistogram": {...},                               │
│    "latencyPercentiles": {                                      │
│      "p50": 1.200, "p75": 1.650,                               │
│      "p90": 2.100, "p95": 2.500,                               │
│      "p99": 3.100                                               │
│    },                                                            │
│    "statusCodeDistribution": {                                  │
│      "200": 99, "500": 1                                        │
│    }                                                             │
│  }                                                               │
│                                                                  │
│  Mapped to standard metrics:                                     │
│  {                                                               │
│    "rps": summary.requestsPerSec,                               │
│    "latency_p50_ms": latencyPercentiles.p50 * 1000,             │
│    "latency_p95_ms": latencyPercentiles.p95 * 1000,             │
│    "latency_p99_ms": latencyPercentiles.p99 * 1000,             │
│    "error_rate": 1 - summary.successRate,                       │
│    "total_requests": summary.total,                             │
│    "successful_requests": statusCodes["200"],                   │
│    "tps": estimated from totalData & avg response time          │
│  }                                                               │
│                                                                  │
│  Đặc điểm:                                                      │
│  + Rất nhanh (Rust-based)                                       │
│  + Latency correction chính xác                                 │
│  + Hỗ trợ high concurrency                                      │
│  - Không đo được TTFT (streaming)                                │
│  - Cần install binary riêng                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2.3 k6 (`k6_adapter.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                          K6 ADAPTER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Binary:      k6 (Grafana k6 load testing)                      │
│  Install:     snap install k6 / brew install k6                 │
│  Mode:        Scripted JavaScript scenarios                     │
│  Metrics:     RPS, Response Time, VUs, Error rate               │
│                                                                  │
│  Generated Script (k6_script.js):                                │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  import http from 'k6/http';                          │      │
│  │  import { check, sleep } from 'k6';                   │      │
│  │  import { Trend, Counter } from 'k6/metrics';         │      │
│  │                                                        │      │
│  │  const ttft = new Trend('ttft');                       │      │
│  │  const tokensGenerated = new Counter('tokens');        │      │
│  │                                                        │      │
│  │  export const options = {                              │      │
│  │    scenarios: {                                        │      │
│  │      benchmark: {                                      │      │
│  │        executor: 'constant-vus',                       │      │
│  │        vus: __ENV.CONCURRENCY || 1,                    │      │
│  │        duration: '60s',                                │      │
│  │      }                                                 │      │
│  │    },                                                  │      │
│  │    thresholds: {                                       │      │
│  │      http_req_failed: ['rate<0.05'],                   │      │
│  │    }                                                   │      │
│  │  };                                                    │      │
│  │                                                        │      │
│  │  export default function () {                          │      │
│  │    const payload = JSON.stringify({                    │      │
│  │      model: __ENV.MODEL,                               │      │
│  │      prompt: __ENV.PROMPT,                             │      │
│  │      stream: false,                                    │      │
│  │      options: { num_predict: 512 }                     │      │
│  │    });                                                 │      │
│  │                                                        │      │
│  │    const res = http.post(                              │      │
│  │      `${__ENV.OLLAMA_URL}/api/generate`,               │      │
│  │      payload,                                          │      │
│  │      { headers: {'Content-Type':'application/json'},   │      │
│  │        timeout: '120s' }                               │      │
│  │    );                                                  │      │
│  │                                                        │      │
│  │    check(res, {                                        │      │
│  │      'status 200': (r) => r.status === 200,            │      │
│  │    });                                                 │      │
│  │                                                        │      │
│  │    if (res.status === 200) {                           │      │
│  │      const body = JSON.parse(res.body);                │      │
│  │      tokensGenerated.add(body.eval_count || 0);        │      │
│  │    }                                                   │      │
│  │    sleep(0.1);                                         │      │
│  │  }                                                     │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
│  Command:                                                        │
│  k6 run --out json=results.json                                 │
│         -e OLLAMA_URL={url}                                     │
│         -e MODEL={model}                                        │
│         -e PROMPT="{prompt}"                                    │
│         -e CONCURRENCY={n}                                      │
│         k6_script.js                                            │
│                                                                  │
│  Parsed Metrics:                                                 │
│  {                                                               │
│    "rps": http_reqs.rate,                                       │
│    "latency_p50_ms": http_req_duration.p(50),                   │
│    "latency_p95_ms": http_req_duration.p(95),                   │
│    "latency_p99_ms": http_req_duration.p(99),                   │
│    "error_rate": http_req_failed.rate,                          │
│    "total_requests": http_reqs.count,                           │
│    "tps": tokens.count / duration                               │
│  }                                                               │
│                                                                  │
│  Đặc điểm:                                                      │
│  + Script linh hoạt (JavaScript)                                │
│  + Scenarios phong phú (ramping, constant, etc.)                │
│  + Thresholds tự động                                            │
│  - Non-streaming nên không đo TTFT trực tiếp                    │
│  - Cần install binary riêng                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2.4 LiteLLM (`litellm_adapter.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                       LITELLM ADAPTER                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Package:     litellm (OpenAI-compatible LLM proxy)             │
│  Install:     pip install litellm                               │
│  Mode:        Python SDK - streaming & non-streaming            │
│  Metrics:     TTFT, TPS, TPOT, Latency                          │
│                                                                  │
│  Code Flow:                                                      │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  import litellm                                       │      │
│  │  import time                                          │      │
│  │                                                        │      │
│  │  litellm.api_base = f"{ollama_url}/v1"                │      │
│  │                                                        │      │
│  │  t0 = time.perf_counter()                             │      │
│  │  response = litellm.completion(                       │      │
│  │      model=f"ollama/{model}",                         │      │
│  │      messages=[{"role":"user","content":prompt}],     │      │
│  │      stream=True,                                     │      │
│  │      max_tokens=512,                                  │      │
│  │      temperature=0.7                                  │      │
│  │  )                                                    │      │
│  │                                                        │      │
│  │  tokens = []                                          │      │
│  │  for chunk in response:                               │      │
│  │      if chunk.choices[0].delta.content:               │      │
│  │          tokens.append({                              │      │
│  │              "text": chunk.choices[0].delta.content,   │      │
│  │              "time": time.perf_counter()               │      │
│  │          })                                           │      │
│  │                                                        │      │
│  │  ttft = (tokens[0]["time"] - t0) * 1000               │      │
│  │  tps = len(tokens) / (tokens[-1]["time"]-tokens[0]["time"]) │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
│  Output Metrics:                                                 │
│  {                                                               │
│    "ttft_ms": 130.8,                                            │
│    "tpot_ms": 18.7,                                             │
│    "tps": 53.5,                                                 │
│    "itl_ms": 19.2,                                              │
│    "prompt_tokens": 30,                                         │
│    "completion_tokens": 492,                                    │
│    "total_tokens": 522                                          │
│  }                                                               │
│                                                                  │
│  Đặc điểm:                                                      │
│  + OpenAI-compatible API                                        │
│  + Streaming support cho TTFT                                   │
│  + Dễ integrate (Python native)                                  │
│  + Hỗ trợ nhiều LLM providers                                   │
│  - Thêm overhead so với direct Ollama API                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2.5 Locust (`locust_adapter.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                       LOCUST ADAPTER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Package:     locust (Python load testing framework)            │
│  Install:     pip install locust                                │
│  Mode:        Programmatic (no web UI, headless)                │
│  Metrics:     RPS, Response Time, Error rate, Concurrent users  │
│                                                                  │
│  Generated Locustfile:                                           │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  from locust import HttpUser, task, between, events   │      │
│  │  import json, time                                    │      │
│  │                                                        │      │
│  │  class OllamaUser(HttpUser):                          │      │
│  │      wait_time = between(0.1, 0.5)                    │      │
│  │      host = "{ollama_url}"                            │      │
│  │                                                        │      │
│  │      @task                                            │      │
│  │      def generate(self):                              │      │
│  │          payload = {                                   │      │
│  │              "model": "{model}",                      │      │
│  │              "prompt": "{prompt}",                    │      │
│  │              "stream": False,                         │      │
│  │              "options": {"num_predict": 512}          │      │
│  │          }                                            │      │
│  │          with self.client.post(                       │      │
│  │              "/api/generate",                         │      │
│  │              json=payload,                            │      │
│  │              timeout=120,                             │      │
│  │              catch_response=True                      │      │
│  │          ) as resp:                                   │      │
│  │              if resp.status_code == 200:              │      │
│  │                  body = resp.json()                   │      │
│  │                  resp.success()                       │      │
│  │              else:                                    │      │
│  │                  resp.failure(f"Status {resp.status_code}") │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
│  Command (Headless):                                             │
│  locust -f locustfile.py                                        │
│         --headless                                              │
│         -u {concurrency}                                        │
│         -r {spawn_rate}                                         │
│         -t 60s                                                  │
│         --csv=results                                           │
│         --only-summary                                          │
│                                                                  │
│  Parsed from CSV output:                                         │
│  {                                                               │
│    "rps": requests_per_sec,                                     │
│    "latency_p50_ms": p50_response_time,                         │
│    "latency_p95_ms": p95_response_time,                         │
│    "latency_p99_ms": p99_response_time,                         │
│    "error_rate": failure_count / request_count,                 │
│    "total_requests": total_request_count                        │
│  }                                                               │
│                                                                  │
│  Đặc điểm:                                                      │
│  + Python native, dễ custom                                     │
│  + Hỗ trợ distributed testing                                   │
│  + CSV output dễ parse                                          │
│  - Non-streaming mode                                            │
│  - Overhead từ Python GIL                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2.6 LLMPerf (`llmperf_adapter.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                       LLMPERF ADAPTER                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Package:     llmperf (LLM-specific benchmark tool)             │
│  Install:     pip install llmperf                               │
│  Mode:        Python-based, LLM-aware metrics                   │
│  Metrics:     TTFT, TPOT, ITL, TPS, Goodput                     │
│                                                                  │
│  Code Flow:                                                      │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  from llmperf import benchmark                        │      │
│  │                                                        │      │
│  │  results = benchmark.run(                             │      │
│  │      api_base=f"{ollama_url}/v1",                     │      │
│  │      model=f"ollama/{model}",                         │      │
│  │      prompt=prompt,                                   │      │
│  │      max_tokens=512,                                  │      │
│  │      num_requests=total_requests,                     │      │
│  │      concurrency=concurrency,                         │      │
│  │      stream=True                                      │      │
│  │  )                                                    │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
│  Output Metrics:                                                 │
│  {                                                               │
│    "ttft_ms": 128.5,                                            │
│    "tpot_ms": 17.8,                                             │
│    "itl_ms": 18.9,                                              │
│    "tps": 56.2,                                                 │
│    "goodput": 55.8,                                             │
│    "total_tokens": 15360,                                       │
│    "error_rate": 0.003                                          │
│  }                                                               │
│                                                                  │
│  Đặc điểm:                                                      │
│  + Designed specifically for LLM benchmarking                   │
│  + Measures goodput (successful throughput only)                │
│  + Token-aware metrics                                          │
│  + Handles streaming natively                                   │
│  - Less flexible for custom scenarios                            │
│  - Newer tool, less battle-tested                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2.7 vLLM Benchmark (`vllm_bench_adapter.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                    VLLM BENCHMARK ADAPTER                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Script:      benchmark_serving.py (from vLLM repo)             │
│  Install:     pip install vllm (or clone benchmark script)      │
│  Mode:        Async HTTP client, high-throughput                 │
│  Metrics:     TPS, TTFT, TPOT, Request throughput                │
│                                                                  │
│  Command:                                                        │
│  python benchmark_serving.py                                    │
│      --backend ollama                                           │
│      --base-url {ollama_url}                                    │
│      --model {model}                                            │
│      --num-prompts {total_requests}                             │
│      --request-rate {concurrency}                               │
│      --max-tokens 512                                           │
│      --output-json results.json                                 │
│                                                                  │
│  Parsed JSON Output:                                             │
│  {                                                               │
│    "completed": 100,                                            │
│    "total_input_tokens": 2500,                                  │
│    "total_output_tokens": 51200,                                │
│    "request_throughput": 6.8,                                   │
│    "output_throughput": 347.5,                                  │
│    "mean_ttft_ms": 126.5,                                       │
│    "median_ttft_ms": 122.1,                                     │
│    "p99_ttft_ms": 185.3,                                        │
│    "mean_tpot_ms": 16.8,                                        │
│    "median_tpot_ms": 15.9,                                      │
│    "p99_tpot_ms": 28.5,                                         │
│    "mean_itl_ms": 17.2,                                         │
│    "median_itl_ms": 16.5,                                       │
│    "p99_itl_ms": 29.8                                           │
│  }                                                               │
│                                                                  │
│  Mapped to standard metrics:                                     │
│  {                                                               │
│    "ttft_ms": mean_ttft_ms,                                     │
│    "tpot_ms": mean_tpot_ms,                                     │
│    "itl_ms": mean_itl_ms,                                       │
│    "tps": output_throughput,                                    │
│    "rps": request_throughput,                                   │
│    "latency_p99_ms": p99_ttft_ms,                               │
│    "total_tokens": total_output_tokens                          │
│  }                                                               │
│                                                                  │
│  Đặc điểm:                                                      │
│  + Throughput-optimized (async)                                 │
│  + Comprehensive percentile metrics                              │
│  + Industry-standard LLM benchmark                              │
│  + Native TTFT, TPOT, ITL support                               │
│  - Heavier dependency                                            │
│  - Originally designed for vLLM engine                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 6.3 Tool Comparison Matrix

| Capability | Ollama | oha | k6 | LiteLLM | Locust | LLMPerf | vLLM |
|-----------|--------|-----|-----|---------|--------|---------|------|
| **TTFT** | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ |
| **TPOT** | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ |
| **TPS** | ✓ | △ | △ | ✓ | △ | ✓ | ✓ |
| **ITL** | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ |
| **RPS** | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| **Percentiles** | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| **Concurrency** | ✗ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ |
| **Streaming** | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ |
| **Goodput** | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| **Language** | Python | Rust | Go/JS | Python | Python | Python | Python |
| **External Binary** | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |

`✓` = Supported  `✗` = Not supported  `△` = Estimated/Derived

## 6.4 Prompt Scenarios

| # | Scenario ID | Category | Prompt | Expected Tokens |
|---|------------|----------|--------|-----------------|
| S1 | `simple_chat` | Conversation | "Explain quantum computing in simple terms" | ~200 |
| S2 | `code_generation` | Code | "Write a Python function to merge two sorted lists with error handling" | ~300 |
| S3 | `long_output` | Generation | "Write a detailed 1000-word essay about climate change impacts on oceans" | ~500 |
| S4 | `reasoning` | Logic | "A train leaves Station A at 60mph. Another train leaves Station B at 80mph. They are 280 miles apart. When do they meet? Show all steps." | ~250 |
| S5 | `translation` | Translation | "Translate the following paragraph to French: 'The rapid development of artificial intelligence has transformed...'" | ~150 |
| S6 | `summarization` | Summary | "Summarize the following article in 3 bullet points: [long input text ~500 words]" | ~100 |

## 6.5 Test Matrix

```
Total Tests = Servers × Scenarios × Tools × Concurrency Levels

For "all" suite:
= 2 servers × 6 scenarios × 7 tools × 1 concurrency (single)
= 84 tests (single request suite)

Plus concurrent:
= 2 servers × 6 scenarios × 5 tools (oha, k6, locust, llmperf, vllm)
    × 3 concurrency levels (5, 10, 20)
= 180 tests (concurrent load suite)

Total "all" suite: 84 + 180 = 264 tests

Each test runs {repeat_count} times (default: 5), results are averaged.
Total requests: 264 × 5 = 1,320 individual requests
Estimated duration: ~25-40 minutes
```

---

# 7. CẤU TRÚC SOURCE CODE

## 7.1 Directory Tree

```
aidaptive-benchmark/
├── 📄 README.md                          # Project documentation
├── 📄 requirements.txt                   # Python dependencies
├── 📄 Dockerfile                         # Docker build
├── 📄 docker-compose.yml                # Full stack compose
├── 📄 .env.example                       # Environment template
├── 📄 .gitignore
├── 📄 Makefile                           # Common commands
│
├── 📁 config/
│   ├── 📄 settings.py                   # App configuration (Pydantic)
│   ├── 📄 defaults.yaml                 # Default values
│   └── 📄 scenarios.yaml                # Prompt scenarios definition
│
├── 📁 app/
│   ├── 📄 __init__.py
│   ├── 📄 main.py                       # FastAPI app factory
│   ├── 📄 app.py                        # Routes & endpoints
│   │
│   ├── 📁 api/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 status.py                # GET /api/status, /api/health
│   │   ├── 📄 benchmark.py             # POST /api/benchmark/*
│   │   ├── 📄 runs.py                  # GET/DELETE /api/runs/*
│   │   ├── 📄 charts.py                # GET /api/charts/*
│   │   └── 📄 servers.py               # GET /api/servers/*
│   │
│   ├── 📁 pages/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 dashboard.py             # GET /
│   │   ├── 📄 servers_page.py          # GET /servers
│   │   ├── 📄 benchmark_page.py        # GET /benchmark
│   │   ├── 📄 history_page.py          # GET /history, /history/{run_id}
│   │   ├── 📄 comparison_page.py       # GET /comparison
│   │   └── 📄 settings_page.py         # GET /settings
│   │
│   └── 📁 templates/
│       ├── 📄 base.html                 # Base layout (nav, header, footer)
│       ├── 📄 dashboard.html
│       ├── 📄 servers.html
│       ├── 📄 benchmark.html
│       ├── 📄 history.html
│       ├── 📄 history_detail.html
│       ├── 📄 comparison.html
│       ├── 📄 settings.html
│       │
│       ├── 📁 components/
│       │   ├── 📄 nav.html              # Sidebar navigation
│       │   ├── 📄 header.html           # Top header bar
│       │   ├── 📄 stat_card.html        # Reusable stat card
│       │   ├── 📄 server_card.html      # Server info card
│       │   ├── 📄 progress_bar.html     # Benchmark progress
│       │   ├── 📄 run_table.html        # Runs table
│       │   ├── 📄 results_table.html    # Results table
│       │   └── 📄 comparison_table.html # Comparison table
│       │
│       └── 📁 charts/
│           ├── 📄 tps_bar_chart.html    # TPS by tool (Chart.js)
│           ├── 📄 latency_chart.html    # Latency comparison
│           ├── 📄 delta_chart.html      # Delta % horizontal bar
│           ├── 📄 gpu_timeline.html     # GPU usage over time
│           ├── 📄 temp_timeline.html    # Temperature timeline
│           └── 📄 trend_chart.html      # Performance trend line
│
├── 📁 core/
│   ├── 📄 __init__.py
│   ├── 📄 orchestrator.py               # Main benchmark orchestrator
│   ├── 📄 progress.py                   # Progress tracking state
│   ├── 📄 aggregator.py                 # Results aggregation & comparison
│   └── 📄 exporter.py                   # CSV/PDF export logic
│
├── 📁 adapters/
│   ├── 📄 __init__.py
│   ├── 📄 base_adapter.py              # Abstract base class
│   ├── 📄 ollama_adapter.py            # T1: Ollama Native API
│   ├── 📄 oha_adapter.py               # T2: oha HTTP load tester
│   ├── 📄 k6_adapter.py                # T3: k6 load testing
│   ├── 📄 litellm_adapter.py           # T4: LiteLLM
│   ├── 📄 locust_adapter.py            # T5: Locust
│   ├── 📄 llmperf_adapter.py           # T6: LLMPerf
│   └── 📄 vllm_bench_adapter.py        # T7: vLLM Benchmark
│
├── 📁 collectors/
│   ├── 📄 __init__.py
│   ├── 📄 agent_client.py              # HTTP client for agent :9100
│   └── 📄 metric_collector.py          # Background metric polling
│
├── 📁 database/
│   ├── 📄 __init__.py
│   ├── 📄 engine.py                    # SQLAlchemy engine & session
│   ├── 📄 tables.py                    # Table definitions (SQLAlchemy)
│   ├── 📄 repository.py               # CRUD operations
│   ├── 📄 seed.py                      # Initial data seeding
│   └── 📄 migrations/
│       ├── 📄 001_initial.sql
│       └── 📄 002_add_indexes.sql
│
├── 📁 data/
│   ├── 📄 __init__.py
│   ├── 📄 data_sink.py                # Write abstraction layer
│   └── 📄 postgres_writer.py          # PostgreSQL writer implementation
│
├── 📁 static/
│   ├── 📁 css/
│   │   ├── 📄 tailwind.min.css         # TailwindCSS (CDN fallback)
│   │   └── 📄 custom.css               # Custom styles
│   │
│   ├── 📁 js/
│   │   ├── 📄 chart.min.js             # Chart.js library
│   │   ├── 📄 app.js                   # Main app JavaScript
│   │   ├── 📄 benchmark.js             # Benchmark control & polling
│   │   ├── 📄 charts.js                # Chart rendering functions
│   │   └── 📄 servers.js               # Server monitoring auto-refresh
│   │
│   └── 📁 img/
│       ├── 📄 logo.svg                  # App logo
│       └── 📄 favicon.ico
│
├── 📁 scripts/
│   ├── 📄 k6_script.js                 # k6 benchmark script template
│   ├── 📄 locustfile.py                # Locust benchmark template
│   └── 📄 setup_tools.sh               # Install external tools (oha, k6)
│
├── 📁 agent/
│   ├── 📄 README.md                     # Agent installation guide
│   ├── 📄 agent.py                      # Lightweight metrics agent
│   ├── 📄 requirements.txt
│   ├── 📄 Dockerfile
│   └── 📄 agent.service                 # systemd service file
│
└── 📁 tests/
    ├── 📄 __init__.py
    ├── 📄 conftest.py                   # pytest fixtures
    ├── 📄 test_orchestrator.py
    ├── 📄 test_adapters.py
    ├── 📄 test_api.py
    ├── 📄 test_repository.py
    └── 📄 test_aggregator.py
```

## 7.2 Key File Descriptions

### 7.2.1 `config/settings.py`

```python
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "aiDaptive Benchmark Suite"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql://aidaptive:password@localhost:5432/aidaptive_bench"
    
    # Server 1 (aiDaptive+ Disabled)
    SERVER1_OLLAMA_URL: str = "http://35.186.159.250:11434"
    SERVER1_AGENT_URL: str = "http://35.186.159.250:9100"
    SERVER1_NAME: str = "aiDaptive+ Disabled"
    SERVER1_AIDAPTIVE_ENABLED: bool = False
    
    # Server 2 (aiDaptive+ Enabled)
    SERVER2_OLLAMA_URL: str = "http://34.142.222.133:11434"
    SERVER2_AGENT_URL: str = "http://34.142.222.133:9100"
    SERVER2_NAME: str = "aiDaptive+ Enabled"
    SERVER2_AIDAPTIVE_ENABLED: bool = True
    
    # Benchmark defaults
    DEFAULT_MODEL: str = "llama3.2:1b"
    WARMUP_REQUESTS: int = 3
    REPEAT_COUNT: int = 5
    CONCURRENCY_LEVELS: List[int] = [1, 5, 10, 20]
    REQUEST_TIMEOUT: int = 120
    COOLDOWN_SECONDS: int = 10
    MAX_TOKENS: int = 512
    TEMPERATURE: float = 0.7
    
    # Metric collection
    METRIC_POLL_INTERVAL: float = 1.0  # seconds
    
    # Data retention
    HARDWARE_SNAPSHOT_RETENTION_DAYS: int = 90
    
    # UI
    THEME: str = "dark"  # dark, light
    AUTO_REFRESH_INTERVAL: int = 5  # seconds
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

Tiếp tục từ **Section 7.2.2** và hoàn thành toàn bộ tài liệu:

---

### 7.2.2 `core/orchestrator.py` (Simplified) (tiếp)

```python
import asyncio
import time
from datetime import datetime
from typing import Optional, List, Dict

from config.settings import settings
from core.progress import ProgressTracker
from core.aggregator import ResultAggregator
from adapters import get_adapter
from collectors.metric_collector import MetricCollector
from database.repository import Repository
from data.data_sink import DataSink

class BenchmarkOrchestrator:
    """Main orchestrator for benchmark execution."""
    
    def __init__(self):
        self.repo = Repository()
        self.sink = DataSink()
        self.progress = ProgressTracker()
        self.aggregator = ResultAggregator()
        self.collector = MetricCollector()
        self._running = False
        self._stop_requested = False
        self._current_run_id: Optional[str] = None
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def current_run_id(self) -> Optional[str]:
        return self._current_run_id
    
    async def start(self, config: dict) -> str:
        """Start a new benchmark run."""
        if self._running:
            raise RuntimeError("Benchmark already running")
        
        # Generate run ID
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._current_run_id = run_id
        self._running = True
        self._stop_requested = False
        
        # Build test matrix
        test_matrix = self._build_test_matrix(config)
        
        # Create run record
        self.repo.create_run(
            run_id=run_id,
            suite=config.get("suite", "all"),
            environment=config.get("environment", "lan"),
            model=config.get("model", settings.DEFAULT_MODEL),
            config_snapshot=config,
            notes=config.get("notes", ""),
            tags=config.get("tags", []),
            total_tests=len(test_matrix)
        )
        
        # Initialize progress
        self.progress.reset(run_id=run_id, total_tests=len(test_matrix))
        
        # Start in background
        asyncio.create_task(self._execute(run_id, config, test_matrix))
        return run_id
    
    async def stop(self) -> dict:
        """Stop current benchmark run."""
        if not self._running:
            raise RuntimeError("No benchmark running")
        
        self._stop_requested = True
        completed = self.progress.completed_tests
        total = self.progress.total_tests
        
        return {
            "run_id": self._current_run_id,
            "completed_tests": completed,
            "total_tests": total
        }
    
    def get_progress(self) -> dict:
        """Get current progress."""
        return self.progress.to_dict()
    
    def _build_test_matrix(self, config: dict) -> List[Dict]:
        """Build list of all tests to run."""
        suite = config.get("suite", "all")
        model = config.get("model", settings.DEFAULT_MODEL)
        servers = self._get_target_servers(config.get("server", "all"))
        scenarios = self._load_scenarios()
        
        matrix = []
        
        if suite in ("single_request", "all"):
            # Single request tests (concurrency=1)
            single_tools = [
                "ollama_native", "oha", "k6", "litellm",
                "locust", "llmperf", "vllm_bench"
            ]
            for server in servers:
                for scenario in scenarios:
                    for tool in single_tools:
                        matrix.append({
                            "server": server,
                            "scenario": scenario["id"],
                            "prompt": scenario["prompt"],
                            "tool": tool,
                            "model": model,
                            "concurrency": 1
                        })
        
        if suite in ("concurrent_load", "all"):
            # Concurrent load tests (concurrency > 1)
            concurrent_tools = ["oha", "k6", "locust", "llmperf", "vllm_bench"]
            concurrency_levels = config.get(
                "concurrency_levels", 
                settings.CONCURRENCY_LEVELS[1:]  # Skip 1
            )
            for server in servers:
                for scenario in scenarios:
                    for tool in concurrent_tools:
                        for conc in concurrency_levels:
                            matrix.append({
                                "server": server,
                                "scenario": scenario["id"],
                                "prompt": scenario["prompt"],
                                "tool": tool,
                                "model": model,
                                "concurrency": conc
                            })
        
        return matrix
    
    def _get_target_servers(self, server_config: str) -> List[str]:
        """Get list of target servers."""
        if server_config == "all":
            return ["server1", "server2"]
        return [server_config]
    
    def _load_scenarios(self) -> List[Dict]:
        """Load prompt scenarios from config."""
        import yaml
        with open("config/scenarios.yaml", "r") as f:
            data = yaml.safe_load(f)
        return data["scenarios"]
    
    async def _execute(self, run_id: str, config: dict, test_matrix: List[Dict]):
        """Execute benchmark phases."""
        started_at = time.time()
        
        try:
            # Update status to running
            self.repo.update_run_status(run_id, "running", started_at=datetime.now())
            
            # ──────────────────────────────────────────────
            # Phase 1: Preflight Check
            # ──────────────────────────────────────────────
            self.progress.set_phase("Preflight")
            preflight_ok = await self._preflight_check()
            if not preflight_ok:
                raise RuntimeError("Preflight check failed")
            
            # ──────────────────────────────────────────────
            # Phase 2: Warmup
            # ──────────────────────────────────────────────
            self.progress.set_phase("Warmup")
            await self._warmup(config)
            
            # ──────────────────────────────────────────────
            # Phase 3: Start metric collection (background)
            # ──────────────────────────────────────────────
            metric_task = asyncio.create_task(
                self.collector.start_polling(run_id)
            )
            
            # ──────────────────────────────────────────────
            # Phase 4: Run Benchmarks
            # ──────────────────────────────────────────────
            self.progress.set_phase("Benchmarking")
            
            for i, test in enumerate(test_matrix):
                # Check stop request
                if self._stop_requested:
                    self.progress.set_phase("Stopped")
                    break
                
                # Update progress
                test_label = (
                    f"{test['server']}/{test['scenario']}/"
                    f"{test['tool']}/c={test['concurrency']}"
                )
                self.progress.set_current_test(test_label)
                
                try:
                    # Run single test
                    result = await self._run_single_test(test)
                    
                    # Save result
                    self.sink.write_result(
                        run_id=run_id,
                        server=test["server"],
                        tool=test["tool"],
                        scenario=test["scenario"],
                        model=test["model"],
                        concurrency=test["concurrency"],
                        metrics=result
                    )
                    
                    self.progress.increment_completed()
                    
                except Exception as e:
                    self.progress.add_error(f"{test_label}: {str(e)}")
                    # Continue to next test
                    self.progress.increment_completed()
                
                # Cooldown between tests
                if i < len(test_matrix) - 1:
                    await asyncio.sleep(settings.COOLDOWN_SECONDS)
            
            # ──────────────────────────────────────────────
            # Phase 5: Stop metric collection
            # ──────────────────────────────────────────────
            self.collector.stop_polling()
            await metric_task
            
            # ──────────────────────────────────────────────
            # Phase 6: Finalize - Aggregate & Compare
            # ──────────────────────────────────────────────
            self.progress.set_phase("Finalizing")
            
            # Generate comparisons
            comparisons = self.aggregator.compare_servers(run_id)
            for comp in comparisons:
                self.sink.write_comparison(run_id=run_id, comparison=comp)
            
            # Calculate duration
            duration = time.time() - started_at
            
            # Update run status
            final_status = "stopped" if self._stop_requested else "completed"
            self.repo.update_run_status(
                run_id,
                status=final_status,
                finished_at=datetime.now(),
                duration_seconds=duration,
                completed_tests=self.progress.completed_tests
            )
            
            self.progress.set_phase("Completed")
        
        except Exception as e:
            # Handle fatal error
            duration = time.time() - started_at
            self.repo.update_run_status(
                run_id,
                status="failed",
                finished_at=datetime.now(),
                duration_seconds=duration,
                completed_tests=self.progress.completed_tests
            )
            self.progress.set_phase("Failed")
            self.progress.add_error(f"Fatal: {str(e)}")
        
        finally:
            self._running = False
            self._current_run_id = None
            self.collector.stop_polling()
    
    async def _preflight_check(self) -> bool:
        """Check all servers and services are online."""
        import httpx
        
        checks = {
            "server1_ollama": settings.SERVER1_OLLAMA_URL,
            "server1_agent": settings.SERVER1_AGENT_URL,
            "server2_ollama": settings.SERVER2_OLLAMA_URL,
            "server2_agent": settings.SERVER2_AGENT_URL,
        }
        
        all_ok = True
        async with httpx.AsyncClient(timeout=10) as client:
            for name, url in checks.items():
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        self.progress.add_error(f"Preflight: {name} returned {resp.status_code}")
                        all_ok = False
                except Exception as e:
                    self.progress.add_error(f"Preflight: {name} unreachable - {e}")
                    all_ok = False
        
        # Check model loaded on both servers
        for server_name, url in [
            ("server1", settings.SERVER1_OLLAMA_URL),
            ("server2", settings.SERVER2_OLLAMA_URL)
        ]:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(f"{url}/api/tags")
                    models = resp.json().get("models", [])
                    model_names = [m["name"] for m in models]
                    if settings.DEFAULT_MODEL not in model_names:
                        self.progress.add_error(
                            f"Preflight: {server_name} missing model {settings.DEFAULT_MODEL}"
                        )
                        all_ok = False
            except Exception as e:
                self.progress.add_error(f"Preflight: {server_name} model check failed - {e}")
                all_ok = False
        
        return all_ok
    
    async def _warmup(self, config: dict):
        """Send warmup requests to both servers."""
        model = config.get("model", settings.DEFAULT_MODEL)
        warmup_count = settings.WARMUP_REQUESTS
        warmup_prompt = "Hello, how are you?"
        
        for server_name, url in [
            ("server1", settings.SERVER1_OLLAMA_URL),
            ("server2", settings.SERVER2_OLLAMA_URL)
        ]:
            for i in range(warmup_count):
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=60) as client:
                        await client.post(
                            f"{url}/api/generate",
                            json={
                                "model": model,
                                "prompt": warmup_prompt,
                                "stream": False,
                                "options": {"num_predict": 50}
                            }
                        )
                except Exception:
                    pass  # Warmup errors are non-fatal
    
    async def _run_single_test(self, test: dict) -> dict:
        """Run a single benchmark test with repeat averaging."""
        adapter = get_adapter(test["tool"])
        
        # Determine server URL
        if test["server"] == "server1":
            ollama_url = settings.SERVER1_OLLAMA_URL
        else:
            ollama_url = settings.SERVER2_OLLAMA_URL
        
        all_results = []
        
        for repeat in range(settings.REPEAT_COUNT):
            result = await adapter.run(
                ollama_url=ollama_url,
                model=test["model"],
                prompt=test["prompt"],
                concurrency=test["concurrency"],
                max_tokens=settings.MAX_TOKENS,
                temperature=settings.TEMPERATURE,
                timeout=settings.REQUEST_TIMEOUT
            )
            all_results.append(result)
        
        # Average the results
        averaged = self._average_results(all_results)
        return averaged
    
    def _average_results(self, results: List[Dict]) -> Dict:
        """Average multiple test results."""
        if not results:
            return {}
        
        # Collect numeric fields
        numeric_keys = [
            "ttft_ms", "tpot_ms", "tps", "itl_ms", "rps",
            "latency_p50_ms", "latency_p95_ms", "latency_p99_ms",
            "error_rate", "goodput"
        ]
        
        averaged = {}
        for key in numeric_keys:
            values = [r.get(key) for r in results if r.get(key) is not None]
            if values:
                averaged[key] = sum(values) / len(values)
        
        # Sum fields (tokens, requests)
        sum_keys = [
            "prompt_tokens", "completion_tokens", "total_tokens",
            "total_requests", "successful_requests", "failed_requests"
        ]
        for key in sum_keys:
            values = [r.get(key, 0) for r in results]
            averaged[key] = sum(values)
        
        averaged["timestamp"] = datetime.utcnow().isoformat()
        averaged["repeat_count"] = len(results)
        
        return averaged
```

### 7.2.3 `core/progress.py`

```python
import time
from typing import Optional, List
from dataclasses import dataclass, field

@dataclass
class ProgressTracker:
    """Thread-safe progress tracking for benchmark runs."""
    
    run_id: Optional[str] = None
    status: str = "idle"           # idle, running, completed, failed, stopped
    current_phase: str = ""        # Preflight, Warmup, Benchmarking, Finalizing
    current_test: str = ""
    total_tests: int = 0
    completed_tests: int = 0
    started_at: Optional[float] = None
    errors: List[str] = field(default_factory=list)
    
    def reset(self, run_id: str, total_tests: int):
        """Reset progress for new run."""
        self.run_id = run_id
        self.status = "running"
        self.current_phase = ""
        self.current_test = ""
        self.total_tests = total_tests
        self.completed_tests = 0
        self.started_at = time.time()
        self.errors = []
    
    def set_phase(self, phase: str):
        self.current_phase = phase
        if phase in ("Completed", "Failed", "Stopped"):
            self.status = phase.lower()
    
    def set_current_test(self, test: str):
        self.current_test = test
    
    def increment_completed(self):
        self.completed_tests += 1
    
    def add_error(self, error: str):
        self.errors.append(error)
    
    @property
    def percent(self) -> int:
        if self.total_tests == 0:
            return 0
        return int((self.completed_tests / self.total_tests) * 100)
    
    @property
    def elapsed_seconds(self) -> float:
        if self.started_at is None:
            return 0
        return time.time() - self.started_at
    
    @property
    def estimated_remaining_seconds(self) -> Optional[float]:
        if self.completed_tests == 0 or self.started_at is None:
            return None
        avg_per_test = self.elapsed_seconds / self.completed_tests
        remaining_tests = self.total_tests - self.completed_tests
        return avg_per_test * remaining_tests
    
    def to_dict(self) -> dict:
        """Serialize progress to dictionary."""
        return {
            "status": self.status,
            "run_id": self.run_id,
            "current_phase": self.current_phase,
            "current_test": self.current_test,
            "total_tests": self.total_tests,
            "completed_tests": self.completed_tests,
            "percent": self.percent,
            "started_at": (
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.started_at))
                if self.started_at else None
            ),
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "estimated_remaining_seconds": (
                round(self.estimated_remaining_seconds, 1)
                if self.estimated_remaining_seconds else None
            ),
            "errors": self.errors[-10:]  # Last 10 errors
        }
```

### 7.2.4 `core/aggregator.py`

```python
from typing import List, Dict, Optional
from database.repository import Repository

class ResultAggregator:
    """Aggregate benchmark results and generate comparisons."""
    
    def __init__(self):
        self.repo = Repository()
    
    def compare_servers(self, run_id: str) -> List[Dict]:
        """Compare Server 1 vs Server 2 across all tool/scenario combinations."""
        
        # Get all results for this run
        results = self.repo.get_results_by_run(run_id)
        
        # Group by (tool, scenario, concurrency)
        groups = {}
        for r in results:
            key = (r["tool"], r["scenario"], r["concurrency"])
            if key not in groups:
                groups[key] = {}
            groups[key][r["server"]] = r
        
        comparisons = []
        for (tool, scenario, concurrency), servers in groups.items():
            s1 = servers.get("server1")
            s2 = servers.get("server2")
            
            if not s1 or not s2:
                continue
            
            comp = self._compare_pair(tool, scenario, concurrency, s1, s2)
            comparisons.append(comp)
        
        return comparisons
    
    def _compare_pair(
        self, tool: str, scenario: str, concurrency: int,
        s1: Dict, s2: Dict
    ) -> Dict:
        """Compare a single pair of S1 vs S2 results."""
        
        comparison = {
            "tool": tool,
            "scenario": scenario,
            "concurrency": concurrency,
            
            # Server 1 metrics
            "s1_ttft_ms": s1.get("ttft_ms"),
            "s1_tpot_ms": s1.get("tpot_ms"),
            "s1_tps": s1.get("tps"),
            "s1_rps": s1.get("rps"),
            "s1_p99_ms": s1.get("latency_p99_ms"),
            "s1_error_rate": s1.get("error_rate"),
            
            # Server 2 metrics
            "s2_ttft_ms": s2.get("ttft_ms"),
            "s2_tpot_ms": s2.get("tpot_ms"),
            "s2_tps": s2.get("tps"),
            "s2_rps": s2.get("rps"),
            "s2_p99_ms": s2.get("latency_p99_ms"),
            "s2_error_rate": s2.get("error_rate"),
        }
        
        # Calculate deltas
        comparison["delta_ttft_pct"] = self._calc_delta(
            s1.get("ttft_ms"), s2.get("ttft_ms"), lower_is_better=True
        )
        comparison["delta_tps_pct"] = self._calc_delta(
            s1.get("tps"), s2.get("tps"), lower_is_better=False
        )
        comparison["delta_p99_pct"] = self._calc_delta(
            s1.get("latency_p99_ms"), s2.get("latency_p99_ms"), lower_is_better=True
        )
        
        # Determine winner
        comparison["overall_winner"] = self._determine_winner(comparison)
        
        return comparison
    
    def _calc_delta(
        self, s1_val: Optional[float], s2_val: Optional[float],
        lower_is_better: bool
    ) -> Optional[float]:
        """
        Calculate percentage delta.
        
        For throughput (higher is better):  delta = (s2 - s1) / s1 * 100
        For latency (lower is better):      delta = (s1 - s2) / s1 * 100
          → Positive delta always means S2 is better
        """
        if s1_val is None or s2_val is None or s1_val == 0:
            return None
        
        if lower_is_better:
            # Latency: negative change is improvement
            # We report as: positive = S2 improved (lower latency)
            return ((s1_val - s2_val) / s1_val) * 100
        else:
            # Throughput: positive change is improvement
            return ((s2_val - s1_val) / s1_val) * 100
    
    def _determine_winner(self, comp: Dict) -> str:
        """Determine overall winner based on weighted metrics."""
        
        scores = {"server1": 0, "server2": 0}
        
        # TPS (weight: 3) - higher is better for S2
        delta_tps = comp.get("delta_tps_pct")
        if delta_tps is not None:
            if delta_tps > 2:    # > 2% improvement threshold
                scores["server2"] += 3
            elif delta_tps < -2:
                scores["server1"] += 3
        
        # TTFT (weight: 2) - positive delta means S2 is faster
        delta_ttft = comp.get("delta_ttft_pct")
        if delta_ttft is not None:
            if delta_ttft > 2:
                scores["server2"] += 2
            elif delta_ttft < -2:
                scores["server1"] += 2
        
        # P99 (weight: 2) - positive delta means S2 is better
        delta_p99 = comp.get("delta_p99_pct")
        if delta_p99 is not None:
            if delta_p99 > 2:
                scores["server2"] += 2
            elif delta_p99 < -2:
                scores["server1"] += 2
        
        if scores["server2"] > scores["server1"]:
            return "server2"
        elif scores["server1"] > scores["server2"]:
            return "server1"
        else:
            return "tie"
    
    def get_run_summary(self, run_id: str) -> Dict:
        """Generate full summary for a run."""
        results = self.repo.get_results_by_run(run_id)
        comparisons = self.repo.get_comparisons_by_run(run_id)
        
        # Aggregate per server
        s1_results = [r for r in results if r["server"] == "server1"]
        s2_results = [r for r in results if r["server"] == "server2"]
        
        summary = {
            "server1": self._aggregate_server_metrics(s1_results),
            "server2": self._aggregate_server_metrics(s2_results),
            "comparison": self._aggregate_comparison(comparisons)
        }
        
        return summary
    
    def _aggregate_server_metrics(self, results: List[Dict]) -> Dict:
        """Calculate averages across all results for one server."""
        if not results:
            return {}
        
        def safe_avg(key):
            vals = [r[key] for r in results if r.get(key) is not None]
            return round(sum(vals) / len(vals), 2) if vals else None
        
        def safe_sum(key):
            return sum(r.get(key, 0) for r in results)
        
        return {
            "avg_tps": safe_avg("tps"),
            "avg_ttft_ms": safe_avg("ttft_ms"),
            "avg_tpot_ms": safe_avg("tpot_ms"),
            "avg_itl_ms": safe_avg("itl_ms"),
            "avg_p50_ms": safe_avg("latency_p50_ms"),
            "avg_p95_ms": safe_avg("latency_p95_ms"),
            "avg_p99_ms": safe_avg("latency_p99_ms"),
            "total_tokens": safe_sum("total_tokens"),
            "total_requests": safe_sum("total_requests"),
            "successful_requests": safe_sum("successful_requests"),
            "error_rate": safe_avg("error_rate"),
        }
    
    def _aggregate_comparison(self, comparisons: List[Dict]) -> Dict:
        """Calculate overall comparison summary."""
        if not comparisons:
            return {}
        
        def safe_avg(key):
            vals = [c[key] for c in comparisons if c.get(key) is not None]
            return round(sum(vals) / len(vals), 2) if vals else None
        
        # Count winners
        win_count = {"server1": 0, "server2": 0, "tie": 0}
        for c in comparisons:
            winner = c.get("overall_winner", "tie")
            win_count[winner] = win_count.get(winner, 0) + 1
        
        # Determine overall winner
        if win_count["server2"] > win_count["server1"]:
            overall = "server2"
        elif win_count["server1"] > win_count["server2"]:
            overall = "server1"
        else:
            overall = "tie"
        
        return {
            "tps_delta_pct": safe_avg("delta_tps_pct"),
            "ttft_delta_pct": safe_avg("delta_ttft_pct"),
            "p99_delta_pct": safe_avg("delta_p99_pct"),
            "winner": overall,
            "win_count": win_count,
            "total_comparisons": len(comparisons)
        }
```

### 7.2.5 `core/exporter.py`

```python
import csv
import io
from typing import Dict, List
from datetime import datetime
from database.repository import Repository
from core.aggregator import ResultAggregator

class Exporter:
    """Export benchmark results to CSV, JSON, and PDF."""
    
    def __init__(self):
        self.repo = Repository()
        self.aggregator = ResultAggregator()
    
    def export_csv(self, run_id: str) -> str:
        """Export run results as CSV string."""
        results = self.repo.get_results_by_run(run_id)
        
        if not results:
            return ""
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "server", "tool", "scenario", "model", "concurrency",
            "ttft_ms", "tpot_ms", "tps", "itl_ms", "rps",
            "latency_p50_ms", "latency_p95_ms", "latency_p99_ms",
            "error_rate", "total_tokens", "total_requests",
            "successful_requests", "failed_requests"
        ])
        
        # Data rows
        for r in results:
            writer.writerow([
                r.get("server"), r.get("tool"), r.get("scenario"),
                r.get("model"), r.get("concurrency"),
                r.get("ttft_ms"), r.get("tpot_ms"), r.get("tps"),
                r.get("itl_ms"), r.get("rps"),
                r.get("latency_p50_ms"), r.get("latency_p95_ms"),
                r.get("latency_p99_ms"), r.get("error_rate"),
                r.get("total_tokens"), r.get("total_requests"),
                r.get("successful_requests"), r.get("failed_requests")
            ])
        
        return output.getvalue()
    
    def export_json(self, run_id: str) -> Dict:
        """Export run results as JSON dict."""
        run = self.repo.get_run(run_id)
        results = self.repo.get_results_by_run(run_id)
        summary = self.aggregator.get_run_summary(run_id)
        comparisons = self.repo.get_comparisons_by_run(run_id)
        
        return {
            "export_timestamp": datetime.utcnow().isoformat(),
            "run": run,
            "summary": summary,
            "comparisons": comparisons,
            "results": results
        }
    
    def export_pdf_data(self, run_id: str) -> Dict:
        """
        Prepare data structure for PDF generation.
        PDF rendering done in template layer.
        """
        run = self.repo.get_run(run_id)
        results = self.repo.get_results_by_run(run_id)
        summary = self.aggregator.get_run_summary(run_id)
        comparisons = self.repo.get_comparisons_by_run(run_id)
        hardware = self.repo.get_hardware_summary(run_id)
        
        return {
            "title": f"Benchmark Report - {run_id}",
            "generated_at": datetime.utcnow().isoformat(),
            "run": run,
            "summary": summary,
            "comparisons": comparisons,
            "results": results,
            "hardware": hardware,
            "charts": {
                "tps_by_tool": self._prepare_tps_chart_data(results),
                "latency_comparison": self._prepare_latency_chart_data(results),
                "delta_summary": self._prepare_delta_chart_data(summary)
            }
        }
    
    def _prepare_tps_chart_data(self, results: List[Dict]) -> Dict:
        """Prepare TPS bar chart data."""
        tools = sorted(set(r["tool"] for r in results))
        s1_data = []
        s2_data = []
        
        for tool in tools:
            s1_vals = [
                r["tps"] for r in results
                if r["tool"] == tool and r["server"] == "server1"
                and r.get("tps") is not None
            ]
            s2_vals = [
                r["tps"] for r in results
                if r["tool"] == tool and r["server"] == "server2"
                and r.get("tps") is not None
            ]
            s1_data.append(round(sum(s1_vals) / len(s1_vals), 2) if s1_vals else 0)
            s2_data.append(round(sum(s2_vals) / len(s2_vals), 2) if s2_vals else 0)
        
        return {"labels": tools, "server1": s1_data, "server2": s2_data}
    
    def _prepare_latency_chart_data(self, results: List[Dict]) -> Dict:
        """Prepare latency comparison chart data."""
        labels = ["TTFT", "P50", "P95", "P99"]
        
        def avg_metric(server, key):
            vals = [
                r[key] for r in results
                if r["server"] == server and r.get(key) is not None
            ]
            return round(sum(vals) / len(vals), 2) if vals else 0
        
        return {
            "labels": labels,
            "server1": [
                avg_metric("server1", "ttft_ms"),
                avg_metric("server1", "latency_p50_ms"),
                avg_metric("server1", "latency_p95_ms"),
                avg_metric("server1", "latency_p99_ms"),
            ],
            "server2": [
                avg_metric("server2", "ttft_ms"),
                avg_metric("server2", "latency_p50_ms"),
                avg_metric("server2", "latency_p95_ms"),
                avg_metric("server2", "latency_p99_ms"),
            ]
        }
    
    def _prepare_delta_chart_data(self, summary: Dict) -> Dict:
        """Prepare delta percentage chart data."""
        comp = summary.get("comparison", {})
        return {
            "labels": ["TPS", "TTFT", "P99"],
            "values": [
                comp.get("tps_delta_pct", 0),
                comp.get("ttft_delta_pct", 0),
                comp.get("p99_delta_pct", 0),
            ]
        }
```

### 7.2.6 `adapters/base_adapter.py`

```python
from abc import ABC, abstractmethod
from typing import Dict

class BaseAdapter(ABC):
    """Abstract base class for all benchmark tool adapters."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of this adapter."""
        pass
    
    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether this adapter supports streaming (TTFT measurement)."""
        pass
    
    @property
    @abstractmethod
    def supports_concurrency(self) -> bool:
        """Whether this adapter supports concurrent requests."""
        pass
    
    @abstractmethod
    async def run(
        self,
        ollama_url: str,
        model: str,
        prompt: str,
        concurrency: int = 1,
        max_tokens: int = 512,
        temperature: float = 0.7,
        timeout: int = 120
    ) -> Dict:
        """
        Run benchmark and return standardized metrics.
        
        Returns:
            {
                "ttft_ms": float | None,
                "tpot_ms": float | None,
                "tps": float | None,
                "itl_ms": float | None,
                "rps": float | None,
                "latency_p50_ms": float | None,
                "latency_p95_ms": float | None,
                "latency_p99_ms": float | None,
                "error_rate": float | None,
                "goodput": float | None,
                "prompt_tokens": int | None,
                "completion_tokens": int | None,
                "total_tokens": int | None,
                "total_requests": int | None,
                "successful_requests": int | None,
                "failed_requests": int | None,
            }
        """
        pass
    
    def _empty_result(self) -> Dict:
        """Return empty result template."""
        return {
            "ttft_ms": None,
            "tpot_ms": None,
            "tps": None,
            "itl_ms": None,
            "rps": None,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
            "latency_p99_ms": None,
            "error_rate": None,
            "goodput": None,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "total_requests": None,
            "successful_requests": None,
            "failed_requests": None,
        }
```

### 7.2.7 `adapters/__init__.py`

```python
from adapters.base_adapter import BaseAdapter
from adapters.ollama_adapter import OllamaAdapter
from adapters.oha_adapter import OhaAdapter
from adapters.k6_adapter import K6Adapter
from adapters.litellm_adapter import LiteLLMAdapter
from adapters.locust_adapter import LocustAdapter
from adapters.llmperf_adapter import LLMPerfAdapter
from adapters.vllm_bench_adapter import VLLMBenchAdapter

_REGISTRY = {
    "ollama_native": OllamaAdapter,
    "oha": OhaAdapter,
    "k6": K6Adapter,
    "litellm": LiteLLMAdapter,
    "locust": LocustAdapter,
    "llmperf": LLMPerfAdapter,
    "vllm_bench": VLLMBenchAdapter,
}

def get_adapter(tool_name: str) -> BaseAdapter:
    """Get adapter instance by tool name."""
    adapter_class = _REGISTRY.get(tool_name)
    if adapter_class is None:
        raise ValueError(f"Unknown tool: {tool_name}. Available: {list(_REGISTRY.keys())}")
    return adapter_class()

def list_adapters() -> list:
    """List all available adapter names."""
    return list(_REGISTRY.keys())
```

### 7.2.8 `collectors/metric_collector.py`

```python
import asyncio
import time
from datetime import datetime
from typing import Optional
import httpx

from config.settings import settings
from data.data_sink import DataSink

class MetricCollector:
    """Background collector for hardware metrics from agents."""
    
    def __init__(self):
        self.sink = DataSink()
        self._polling = False
        self._poll_interval = settings.METRIC_POLL_INTERVAL
    
    async def start_polling(self, run_id: str):
        """Start background polling loop."""
        self._polling = True
        
        servers = [
            ("server1", settings.SERVER1_AGENT_URL),
            ("server2", settings.SERVER2_AGENT_URL),
        ]
        
        while self._polling:
            tasks = []
            for server_name, agent_url in servers:
                tasks.append(
                    self._collect_once(run_id, server_name, agent_url)
                )
            
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(self._poll_interval)
    
    def stop_polling(self):
        """Stop background polling."""
        self._polling = False
    
    async def _collect_once(
        self, run_id: str, server_name: str, agent_url: str
    ):
        """Collect metrics from one server's agent."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{agent_url}/metrics")
                
                if resp.status_code != 200:
                    return
                
                data = resp.json()
                
                snapshot = {
                    "run_id": run_id,
                    "server": server_name,
                    "timestamp": datetime.utcnow(),
                    
                    # GPU
                    "gpu_util_pct": data.get("gpu", {}).get("utilization_pct"),
                    "gpu_memory_util_pct": data.get("gpu", {}).get("memory_util_pct"),
                    "vram_used_gb": data.get("gpu", {}).get("vram_used_gb"),
                    "vram_total_gb": data.get("gpu", {}).get("vram_total_gb"),
                    "gpu_power_watts": data.get("gpu", {}).get("power_watts"),
                    "gpu_temperature_c": data.get("gpu", {}).get("temperature_c"),
                    
                    # System
                    "cpu_pct": data.get("cpu", {}).get("utilization_pct"),
                    "ram_used_gb": data.get("memory", {}).get("used_gb"),
                    "ram_total_gb": data.get("memory", {}).get("total_gb"),
                    "load_avg_1m": data.get("cpu", {}).get("load_avg_1m"),
                    "load_avg_5m": data.get("cpu", {}).get("load_avg_5m"),
                }
                
                self.sink.write_hardware_snapshot(snapshot)
        
        except Exception:
            pass  # Non-fatal: metric collection should not break benchmark
    
    async def get_realtime_metrics(self, server_name: str) -> Optional[dict]:
        """Get current metrics for a single server (for UI display)."""
        if server_name == "server1":
            agent_url = settings.SERVER1_AGENT_URL
        else:
            agent_url = settings.SERVER2_AGENT_URL
        
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{agent_url}/metrics")
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        
        return None
```

### 7.2.9 `database/repository.py`

```python
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import text
from database.engine import get_session

class Repository:
    """Data access layer for all database operations."""
    
    # ─── RUNS ───────────────────────────────────────────
    
    def create_run(self, **kwargs) -> str:
        """Create a new benchmark run."""
        with get_session() as session:
            session.execute(text("""
                INSERT INTO benchmark_runs 
                    (run_id, status, suite, environment, model, 
                     config_snapshot, notes, tags, total_tests)
                VALUES 
                    (:run_id, 'pending', :suite, :environment, :model,
                     :config_snapshot::jsonb, :notes, :tags, :total_tests)
            """), {
                "run_id": kwargs["run_id"],
                "suite": kwargs.get("suite", "all"),
                "environment": kwargs.get("environment", "lan"),
                "model": kwargs.get("model"),
                "config_snapshot": str(kwargs.get("config_snapshot", {})),
                "notes": kwargs.get("notes", ""),
                "tags": kwargs.get("tags", []),
                "total_tests": kwargs.get("total_tests", 0),
            })
            session.commit()
        return kwargs["run_id"]
    
    def update_run_status(self, run_id: str, status: str, **kwargs):
        """Update run status and metadata."""
        with get_session() as session:
            updates = ["status = :status"]
            params = {"run_id": run_id, "status": status}
            
            if "started_at" in kwargs:
                updates.append("started_at = :started_at")
                params["started_at"] = kwargs["started_at"]
            
            if "finished_at" in kwargs:
                updates.append("finished_at = :finished_at")
                params["finished_at"] = kwargs["finished_at"]
            
            if "duration_seconds" in kwargs:
                updates.append("duration_seconds = :duration_seconds")
                params["duration_seconds"] = kwargs["duration_seconds"]
            
            if "completed_tests" in kwargs:
                updates.append("completed_tests = :completed_tests")
                params["completed_tests"] = kwargs["completed_tests"]
            
            sql = f"UPDATE benchmark_runs SET {', '.join(updates)} WHERE run_id = :run_id"
            session.execute(text(sql), params)
            session.commit()
    
    def get_run(self, run_id: str) -> Optional[Dict]:
        """Get single run by ID."""
        with get_session() as session:
            result = session.execute(text(
                "SELECT * FROM benchmark_runs WHERE run_id = :run_id"
            ), {"run_id": run_id}).mappings().first()
            return dict(result) if result else None
    
    def get_runs(
        self, limit: int = 20, offset: int = 0,
        status: Optional[str] = None
    ) -> Dict:
        """Get paginated list of runs."""
        with get_session() as session:
            # Count
            count_sql = "SELECT COUNT(*) FROM benchmark_runs"
            params = {}
            if status:
                count_sql += " WHERE status = :status"
                params["status"] = status
            total = session.execute(text(count_sql), params).scalar()
            
            # Fetch
            fetch_sql = """
                SELECT * FROM benchmark_runs
                {where}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """.format(where="WHERE status = :status" if status else "")
            params.update({"limit": limit, "offset": offset})
            
            rows = session.execute(text(fetch_sql), params).mappings().all()
            
            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "runs": [dict(r) for r in rows]
            }
    
    def delete_run(self, run_id: str) -> Dict:
        """Delete a run and all related data (CASCADE)."""
        with get_session() as session:
            # Count related records
            results_count = session.execute(text(
                "SELECT COUNT(*) FROM benchmark_results WHERE run_id = :run_id"
            ), {"run_id": run_id}).scalar()
            
            snapshots_count = session.execute(text(
                "SELECT COUNT(*) FROM hardware_snapshots WHERE run_id = :run_id"
            ), {"run_id": run_id}).scalar()
            
            comparisons_count = session.execute(text(
                "SELECT COUNT(*) FROM server_comparisons WHERE run_id = :run_id"
            ), {"run_id": run_id}).scalar()
            
            # Delete (CASCADE handles related tables)
            session.execute(text(
                "DELETE FROM benchmark_runs WHERE run_id = :run_id"
            ), {"run_id": run_id})
            session.commit()
            
            return {
                "deleted_results": results_count,
                "deleted_snapshots": snapshots_count,
                "deleted_comparisons": comparisons_count,
            }
    
    # ─── RESULTS ────────────────────────────────────────
    
    def get_results_by_run(self, run_id: str) -> List[Dict]:
        """Get all results for a run."""
        with get_session() as session:
            rows = session.execute(text(
                "SELECT * FROM benchmark_results WHERE run_id = :run_id ORDER BY timestamp"
            ), {"run_id": run_id}).mappings().all()
            return [dict(r) for r in rows]
    
    # ─── COMPARISONS ────────────────────────────────────
    
    def get_comparisons_by_run(self, run_id: str) -> List[Dict]:
        """Get all comparisons for a run."""
        with get_session() as session:
            rows = session.execute(text(
                "SELECT * FROM server_comparisons WHERE run_id = :run_id"
            ), {"run_id": run_id}).mappings().all()
            return [dict(r) for r in rows]
    
    # ─── HARDWARE ───────────────────────────────────────
    
    def get_hardware_timeline(self, run_id: str) -> Dict:
        """Get hardware metrics timeline for a run."""
        with get_session() as session:
            rows = session.execute(text("""
                SELECT * FROM hardware_snapshots 
                WHERE run_id = :run_id 
                ORDER BY timestamp ASC
            """), {"run_id": run_id}).mappings().all()
            
            result = {"server1": [], "server2": []}
            for r in rows:
                server = r["server"]
                if server in result:
                    result[server].append(dict(r))
            
            return result
    
    def get_hardware_summary(self, run_id: str) -> Dict:
        """Get hardware summary (avg, peak) for a run."""
        with get_session() as session:
            summary = {}
            for server in ["server1", "server2"]:
                row = session.execute(text("""
                    SELECT 
                        AVG(gpu_util_pct) as avg_gpu_util,
                        MAX(gpu_util_pct) as peak_gpu_util,
                        AVG(gpu_temperature_c) as avg_gpu_temp,
                        MAX(gpu_temperature_c) as peak_gpu_temp,
                        AVG(vram_used_gb) as avg_vram,
                        MAX(vram_used_gb) as peak_vram,
                        AVG(cpu_pct) as avg_cpu,
                        MAX(cpu_pct) as peak_cpu,
                        AVG(ram_used_gb) as avg_ram,
                        MAX(ram_used_gb) as peak_ram,
                        AVG(gpu_power_watts) as avg_power,
                        MAX(gpu_power_watts) as peak_power
                    FROM hardware_snapshots
                    WHERE run_id = :run_id AND server = :server
                """), {"run_id": run_id, "server": server}).mappings().first()
                
                summary[server] = dict(row) if row else {}
            
            return summary
    
    # ─── SERVER PROFILES ────────────────────────────────
    
    def get_server_profiles(self) -> List[Dict]:
        """Get all server profiles."""
        with get_session() as session:
            rows = session.execute(text(
                "SELECT * FROM server_profiles ORDER BY server_id"
            )).mappings().all()
            return [dict(r) for r in rows]
    
    def update_server_hardware(self, server_id: str, hardware: Dict):
        """Update server hardware info from agent detection."""
        with get_session() as session:
            session.execute(text("""
                UPDATE server_profiles SET
                    gpu_name = :gpu_name,
                    gpu_vram_gb = :gpu_vram_gb,
                    gpu_driver = :gpu_driver,
                    cpu_name = :cpu_name,
                    cpu_cores = :cpu_cores,
                    ram_total_gb = :ram_total_gb,
                    hostname = :hostname,
                    os_version = :os_version,
                    last_seen_at = :now,
                    is_online = true,
                    updated_at = :now
                WHERE server_id = :server_id
            """), {
                "server_id": server_id,
                "gpu_name": hardware.get("gpu_name"),
                "gpu_vram_gb": hardware.get("gpu_vram_gb"),
                "gpu_driver": hardware.get("gpu_driver"),
                "cpu_name": hardware.get("cpu_name"),
                "cpu_cores": hardware.get("cpu_cores"),
                "ram_total_gb": hardware.get("ram_total_gb"),
                "hostname": hardware.get("hostname"),
                "os_version": hardware.get("os_version"),
                "now": datetime.utcnow(),
            })
            session.commit()
```

### 7.2.10 `database/engine.py`

```python
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

@contextmanager
def get_session() -> Session:
    """Context manager for database sessions."""
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

### 7.2.11 `data/data_sink.py`

```python
from typing import Dict
from datetime import datetime
from data.postgres_writer import PostgresWriter

class DataSink:
    """Abstraction layer for writing benchmark data."""
    
    def __init__(self):
        self.writer = PostgresWriter()
    
    def write_result(
        self, run_id: str, server: str, tool: str,
        scenario: str, model: str, concurrency: int,
        metrics: Dict
    ):
        """Write a single benchmark result."""
        record = {
            "run_id": run_id,
            "timestamp": metrics.get("timestamp", datetime.utcnow().isoformat()),
            "server": server,
            "tool": tool,
            "scenario": scenario,
            "model": model,
            "concurrency": concurrency,
            **{k: v for k, v in metrics.items() if k != "timestamp"}
        }
        self.writer.insert_result(record)
    
    def write_hardware_snapshot(self, snapshot: Dict):
        """Write a hardware metrics snapshot."""
        self.writer.insert_hardware_snapshot(snapshot)
    
    def write_comparison(self, run_id: str, comparison: Dict):
        """Write a server comparison record."""
        comparison["run_id"] = run_id
        self.writer.insert_comparison(comparison)
```

### 7.2.12 `agent/agent.py`

```python
"""
Lightweight metrics agent - runs on each AI server.
Exposes hardware metrics via HTTP on port 9100.
"""

import json
import subprocess
import psutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Optional

class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for metrics endpoints."""
    
    def do_GET(self):
        if self.path == "/metrics":
            self._handle_metrics()
        elif self.path == "/hardware":
            self._handle_hardware()
        elif self.path == "/":
            self._handle_health()
        else:
            self.send_error(404)
    
    def _handle_health(self):
        """Health check endpoint."""
        self._respond(200, {"status": "ok", "agent": "aidaptive-agent", "version": "1.0"})
    
    def _handle_metrics(self):
        """Current metrics endpoint."""
        metrics = {
            "gpu": self._get_gpu_metrics(),
            "cpu": self._get_cpu_metrics(),
            "memory": self._get_memory_metrics(),
        }
        self._respond(200, metrics)
    
    def _handle_hardware(self):
        """Static hardware info endpoint."""
        info = {
            "gpu_name": self._get_gpu_name(),
            "gpu_vram_gb": self._get_gpu_vram(),
            "gpu_driver": self._get_gpu_driver(),
            "cpu_name": self._get_cpu_name(),
            "cpu_cores": psutil.cpu_count(logical=True),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "hostname": self._get_hostname(),
            "os_version": self._get_os_version(),
        }
        self._respond(200, info)
    
    def _get_gpu_metrics(self) -> Dict:
        """Get current GPU metrics via nvidia-smi."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,utilization.memory,"
                    "memory.used,memory.total,power.draw,temperature.gpu",
                    "--format=csv,noheader,nounits"
                ],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode != 0:
                return {}
            
            values = result.stdout.strip().split(", ")
            if len(values) >= 6:
                return {
                    "utilization_pct": float(values[0]),
                    "memory_util_pct": float(values[1]),
                    "vram_used_gb": round(float(values[2]) / 1024, 2),
                    "vram_total_gb": round(float(values[3]) / 1024, 2),
                    "power_watts": float(values[4]),
                    "temperature_c": float(values[5]),
                }
        except Exception:
            pass
        return {}
    
    def _get_cpu_metrics(self) -> Dict:
        """Get current CPU metrics."""
        load1, load5, load15 = psutil.getloadavg()
        return {
            "utilization_pct": psutil.cpu_percent(interval=0.1),
            "load_avg_1m": round(load1, 2),
            "load_avg_5m": round(load5, 2),
            "load_avg_15m": round(load15, 2),
        }
    
    def _get_memory_metrics(self) -> Dict:
        """Get current memory metrics."""
        mem = psutil.virtual_memory()
        return {
            "used_gb": round(mem.used / (1024**3), 2),
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent": mem.percent,
        }
    
    def _get_gpu_name(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None
    
    def _get_gpu_vram(self) -> Optional[float]:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return round(float(result.stdout.strip()) / 1024, 1)
        except Exception:
            pass
        return None
    
    def _get_gpu_driver(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None
    
    def _get_cpu_name(self) -> Optional[str]:
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        except Exception:
            pass
        return None
    
    def _get_hostname(self) -> str:
        import socket
        return socket.gethostname()
    
    def _get_os_version(self) -> Optional[str]:
        try:
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME"):
                        return line.split("=")[1].strip().strip('"')
        except Exception:
            pass
        return None
    
    def _respond(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())
    
    def log_message(self, format, *args):
        pass  # Suppress default logging


if __name__ == "__main__":
    PORT = 9100
    server = HTTPServer(("0.0.0.0", PORT), MetricsHandler)
    print(f"Agent running on port {PORT}")
    server.serve_forever()
```

---

# 8. CÀI ĐẶT VÀ DEPLOYMENT

## 8.1 Yêu cầu hệ thống

### 8.1.1 Controller Node

| Component | Requirement |
|-----------|-------------|
| OS | Ubuntu 22.04 LTS |
| Python | 3.10+ |
| RAM | ≥ 4 GB |
| Disk | ≥ 10 GB free |
| Network | Kết nối tới cả 2 AI servers |
| Ports | 8000 (Web UI), 5432 (PostgreSQL) |

### 8.1.2 AI Servers (mỗi server)

| Component | Requirement |
|-----------|-------------|
| OS | Ubuntu 22.04 LTS |
| GPU | NVIDIA (có CUDA support) |
| NVIDIA Driver | ≥ 535.x |
| CUDA | ≥ 12.0 |
| Ollama | Latest |
| Agent | Python 3.10+ hoặc Docker |
| Ports | 11434 (Ollama), 9100 (Agent) |

## 8.2 Cài đặt thủ công (Manual Installation)

### 8.2.1 Controller Node (tiếp)

```bash
# ─── 1. Clone repository ───
git clone https://github.com/aidaptive/benchmark-suite.git
cd benchmark-suite

# ─── 2. Python environment ───
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# ─── 3. Install external tools ───
chmod +x scripts/setup_tools.sh
./scripts/setup_tools.sh
# Installs: oha, k6

# ─── 4. PostgreSQL ───
sudo apt update
sudo apt install -y postgresql-15
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Create database & user
sudo -u postgres psql <<EOF
CREATE USER aidaptive WITH PASSWORD 'your_secure_password';
CREATE DATABASE aidaptive_bench OWNER aidaptive;
GRANT ALL PRIVILEGES ON DATABASE aidaptive_bench TO aidaptive;
\q
EOF

# ─── 5. Initialize database schema ───
psql -U aidaptive -d aidaptive_bench -f database/migrations/001_initial.sql
psql -U aidaptive -d aidaptive_bench -f database/migrations/002_add_indexes.sql

# ─── 6. Seed initial data ───
python -m database.seed

# ─── 7. Configure environment ───
cp .env.example .env
nano .env

# ─── 8. Start application ───
python -m app.main

# Application available at: http://localhost:8000
```

### 8.2.2 AI Server 1 (aiDaptive+ Disabled)

```bash
# ─── 1. Install NVIDIA drivers ───
sudo apt update
sudo apt install -y nvidia-driver-535
sudo reboot

# Verify
nvidia-smi

# ─── 2. Install Ollama ───
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama (listen on all interfaces)
OLLAMA_HOST=0.0.0.0:11434 ollama serve &

# Pull model
ollama pull llama3.2:1b

# Verify
curl http://localhost:11434/api/tags

# ─── 3. Install & Start Agent ───
cd /opt
git clone https://github.com/aidaptive/benchmark-suite.git
cd benchmark-suite/agent

python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start agent
python agent.py &

# Verify
curl http://localhost:9100/metrics
curl http://localhost:9100/hardware

# ─── 4. Install as systemd service (Ollama) ───
# Ollama service is auto-installed by install script
# Edit to bind to 0.0.0.0:
sudo systemctl edit ollama.service
# Add:
# [Service]
# Environment="OLLAMA_HOST=0.0.0.0:11434"

sudo systemctl daemon-reload
sudo systemctl restart ollama

# ─── 5. Install Agent as systemd service ───
sudo cp agent.service /etc/systemd/system/aidaptive-agent.service
sudo systemctl daemon-reload
sudo systemctl enable aidaptive-agent
sudo systemctl start aidaptive-agent

# Verify services
sudo systemctl status ollama
sudo systemctl status aidaptive-agent
```

### 8.2.3 AI Server 2 (aiDaptive+ Enabled)

```bash
# Same as Server 1 steps above, plus:

# ─── Enable aiDaptive+ ───
# (Specific aiDaptive+ installation steps - provided by aiDaptive team)
# This step installs and configures the aiDaptive+ optimization layer
# on top of the existing hardware/software stack.

# Example (placeholder):
curl -fsSL https://install.aidaptive.com/plus | sudo bash
sudo aidaptive-plus enable
sudo systemctl restart ollama

# Verify aiDaptive+ status
sudo aidaptive-plus status
# Expected output:
#   aiDaptive+ Status: ENABLED
#   Optimization Level: Full
#   GPU Acceleration: Active
```

### 8.2.4 `scripts/setup_tools.sh`

```bash
#!/bin/bash
set -e

echo "=== aiDaptive Benchmark Suite - Tool Setup ==="
echo ""

# ─── Detect OS ───
OS=$(uname -s)
ARCH=$(uname -m)

echo "OS: $OS | Arch: $ARCH"
echo ""

# ─── 1. Install oha ───
echo ">>> Installing oha (HTTP load generator)..."

if command -v oha &> /dev/null; then
    echo "    oha already installed: $(oha --version)"
else
    if command -v cargo &> /dev/null; then
        cargo install oha
    else
        # Install via pre-built binary
        OHA_VERSION="1.4.1"
        if [ "$ARCH" = "x86_64" ]; then
            OHA_URL="https://github.com/hatoo/oha/releases/download/v${OHA_VERSION}/oha-linux-amd64"
        elif [ "$ARCH" = "aarch64" ]; then
            OHA_URL="https://github.com/hatoo/oha/releases/download/v${OHA_VERSION}/oha-linux-arm64"
        fi
        
        sudo curl -L "$OHA_URL" -o /usr/local/bin/oha
        sudo chmod +x /usr/local/bin/oha
    fi
    echo "    oha installed: $(oha --version)"
fi

echo ""

# ─── 2. Install k6 ───
echo ">>> Installing k6 (load testing)..."

if command -v k6 &> /dev/null; then
    echo "    k6 already installed: $(k6 version)"
else
    # Ubuntu/Debian
    if command -v apt &> /dev/null; then
        sudo gpg -k
        sudo gpg --no-default-keyring \
            --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
            --keyserver hkp://keyserver.ubuntu.com:80 \
            --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D68
        echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
            | sudo tee /etc/apt/sources.list.d/k6.list
        sudo apt update
        sudo apt install -y k6
    # macOS
    elif command -v brew &> /dev/null; then
        brew install k6
    # Snap fallback
    elif command -v snap &> /dev/null; then
        sudo snap install k6
    fi
    echo "    k6 installed: $(k6 version)"
fi

echo ""

# ─── 3. Install Python packages ───
echo ">>> Installing Python benchmark packages..."

pip install --quiet litellm locust llmperf 2>/dev/null || true

echo "    litellm: $(pip show litellm 2>/dev/null | grep Version || echo 'not installed')"
echo "    locust:  $(pip show locust 2>/dev/null | grep Version || echo 'not installed')"
echo "    llmperf: $(pip show llmperf 2>/dev/null | grep Version || echo 'not installed')"

echo ""

# ─── 4. Download vLLM benchmark script ───
echo ">>> Downloading vLLM benchmark_serving.py..."

VLLM_BENCH_PATH="scripts/benchmark_serving.py"
if [ ! -f "$VLLM_BENCH_PATH" ]; then
    curl -sL "https://raw.githubusercontent.com/vllm-project/vllm/main/benchmarks/benchmark_serving.py" \
        -o "$VLLM_BENCH_PATH"
    echo "    Downloaded to $VLLM_BENCH_PATH"
else
    echo "    Already exists at $VLLM_BENCH_PATH"
fi

echo ""
echo "=== Tool Setup Complete ==="
echo ""

# ─── 5. Verification ───
echo ">>> Verification:"
echo "    oha:              $(command -v oha && echo '✓' || echo '✗ NOT FOUND')"
echo "    k6:               $(command -v k6 && echo '✓' || echo '✗ NOT FOUND')"
echo "    litellm:          $(python -c 'import litellm' 2>/dev/null && echo '✓' || echo '✗ NOT FOUND')"
echo "    locust:           $(python -c 'import locust' 2>/dev/null && echo '✓' || echo '✗ NOT FOUND')"
echo "    llmperf:          $(python -c 'import llmperf' 2>/dev/null && echo '✓' || echo '✗ NOT FOUND')"
echo "    vllm_bench script:$([ -f scripts/benchmark_serving.py ] && echo '✓' || echo '✗ NOT FOUND')"
echo ""
```

### 8.2.5 `.env.example`

```bash
# ═══════════════════════════════════════════════════════
#  aiDaptive Benchmark Suite - Environment Configuration
# ═══════════════════════════════════════════════════════

# ─── Application ───
APP_NAME="aiDaptive Benchmark Suite"
APP_VERSION="2.0.0"
DEBUG=false
HOST=0.0.0.0
PORT=8000

# ─── Database ───
DATABASE_URL=postgresql://aidaptive:your_secure_password@localhost:5432/aidaptive_bench

# ─── Server 1 (aiDaptive+ Disabled) ───
SERVER1_OLLAMA_URL=http://35.186.159.250:11434
SERVER1_AGENT_URL=http://35.186.159.250:9100
SERVER1_NAME="aiDaptive+ Disabled"
SERVER1_AIDAPTIVE_ENABLED=false

# ─── Server 2 (aiDaptive+ Enabled) ───
SERVER2_OLLAMA_URL=http://34.142.222.133:11434
SERVER2_AGENT_URL=http://34.142.222.133:9100
SERVER2_NAME="aiDaptive+ Enabled"
SERVER2_AIDAPTIVE_ENABLED=true

# ─── Benchmark Defaults ───
DEFAULT_MODEL=llama3.2:1b
WARMUP_REQUESTS=3
REPEAT_COUNT=5
CONCURRENCY_LEVELS=1,5,10,20
REQUEST_TIMEOUT=120
COOLDOWN_SECONDS=10
MAX_TOKENS=512
TEMPERATURE=0.7

# ─── Metric Collection ───
METRIC_POLL_INTERVAL=1.0

# ─── Data Retention ───
HARDWARE_SNAPSHOT_RETENTION_DAYS=90

# ─── UI ───
THEME=dark
AUTO_REFRESH_INTERVAL=5
```

## 8.3 Docker Deployment

### 8.3.1 `Dockerfile` (Controller)

```dockerfile
# ═══════════════════════════════════════════
#  aiDaptive Benchmark Suite - Controller
# ═══════════════════════════════════════════

FROM python:3.10-slim

# Labels
LABEL maintainer="aiDaptive Team"
LABEL version="2.0.0"
LABEL description="aiDaptive Benchmark Suite Controller"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install oha
RUN curl -L "https://github.com/hatoo/oha/releases/download/v1.4.1/oha-linux-amd64" \
    -o /usr/local/bin/oha && \
    chmod +x /usr/local/bin/oha

# Install k6
RUN gpg -k && \
    gpg --no-default-keyring \
        --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
        --keyserver hkp://keyserver.ubuntu.com:80 \
        --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D68 && \
    echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
        > /etc/apt/sources.list.d/k6.list && \
    apt-get update && \
    apt-get install -y k6 && \
    rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Download vLLM benchmark script
RUN curl -sL "https://raw.githubusercontent.com/vllm-project/vllm/main/benchmarks/benchmark_serving.py" \
    -o scripts/benchmark_serving.py || true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start
CMD ["python", "-m", "app.main"]
```

### 8.3.2 `Dockerfile` (Agent)

```dockerfile
# ═══════════════════════════════════════════
#  aiDaptive Benchmark Suite - Agent
# ═══════════════════════════════════════════

FROM python:3.10-slim

LABEL maintainer="aiDaptive Team"
LABEL description="aiDaptive Hardware Metrics Agent"

WORKDIR /app

COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/agent.py .

EXPOSE 9100

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:9100/ || exit 1

CMD ["python", "agent.py"]
```

### 8.3.3 `docker-compose.yml`

```yaml
# ═══════════════════════════════════════════════════════
#  aiDaptive Benchmark Suite - Full Stack
# ═══════════════════════════════════════════════════════

version: "3.9"

services:
  # ─── PostgreSQL Database ───
  postgres:
    image: postgres:15-alpine
    container_name: aidaptive-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: aidaptive
      POSTGRES_PASSWORD: ${DB_PASSWORD:-aidaptive_secure_2024}
      POSTGRES_DB: aidaptive_bench
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/migrations/001_initial.sql:/docker-entrypoint-initdb.d/001_initial.sql
      - ./database/migrations/002_add_indexes.sql:/docker-entrypoint-initdb.d/002_add_indexes.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aidaptive -d aidaptive_bench"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - aidaptive-net

  # ─── Benchmark Controller ───
  controller:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: aidaptive-controller
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://aidaptive:${DB_PASSWORD:-aidaptive_secure_2024}@postgres:5432/aidaptive_bench
      SERVER1_OLLAMA_URL: ${SERVER1_OLLAMA_URL:-http://35.186.159.250:11434}
      SERVER1_AGENT_URL: ${SERVER1_AGENT_URL:-http://35.186.159.250:9100}
      SERVER1_NAME: "aiDaptive+ Disabled"
      SERVER1_AIDAPTIVE_ENABLED: "false"
      SERVER2_OLLAMA_URL: ${SERVER2_OLLAMA_URL:-http://34.142.222.133:11434}
      SERVER2_AGENT_URL: ${SERVER2_AGENT_URL:-http://34.142.222.133:9100}
      SERVER2_NAME: "aiDaptive+ Enabled"
      SERVER2_AIDAPTIVE_ENABLED: "true"
      DEFAULT_MODEL: ${DEFAULT_MODEL:-llama3.2:1b}
      HOST: "0.0.0.0"
      PORT: "8000"
      DEBUG: ${DEBUG:-false}
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config
      - ./scripts:/app/scripts
      - controller_data:/app/data
    networks:
      - aidaptive-net

volumes:
  postgres_data:
    driver: local
  controller_data:
    driver: local

networks:
  aidaptive-net:
    driver: bridge
```

### 8.3.4 `docker-compose.agent.yml` (Chạy trên AI Server)

```yaml
# ═══════════════════════════════════════════════════════
#  Agent - Run this on each AI Server
# ═══════════════════════════════════════════════════════

version: "3.9"

services:
  agent:
    build:
      context: .
      dockerfile: agent/Dockerfile
    container_name: aidaptive-agent
    restart: unless-stopped
    ports:
      - "9100:9100"
    # NVIDIA GPU access required for nvidia-smi
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    volumes:
      - /proc/cpuinfo:/proc/cpuinfo:ro
      - /etc/os-release:/etc/os-release:ro
```

## 8.4 Docker Commands

```bash
# ─── Controller Node ───

# Build & Start
docker compose up -d --build

# Check logs
docker compose logs -f controller
docker compose logs -f postgres

# Stop
docker compose down

# Stop and remove volumes (DELETES ALL DATA)
docker compose down -v

# Restart only controller
docker compose restart controller

# View running containers
docker compose ps

# ─── AI Server (Agent) ───

# Build & Start Agent
docker compose -f docker-compose.agent.yml up -d --build

# Check Agent logs
docker compose -f docker-compose.agent.yml logs -f agent

# Stop Agent
docker compose -f docker-compose.agent.yml down
```

## 8.5 Makefile

```makefile
# ═══════════════════════════════════════════
#  aiDaptive Benchmark Suite - Makefile
# ═══════════════════════════════════════════

.PHONY: help install dev run docker-up docker-down db-init db-reset test lint clean

# ─── Variables ───
PYTHON := python3.10
VENV := venv
PIP := $(VENV)/bin/pip
APP := $(VENV)/bin/python -m app.main

# ─── Help ───
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Development ───
install: ## Install Python dependencies + tools
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -r requirements.txt
	chmod +x scripts/setup_tools.sh
	./scripts/setup_tools.sh

dev: ## Start dev server (with auto-reload)
	DEBUG=true $(VENV)/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run: ## Start production server
	$(APP)

# ─── Docker ───
docker-up: ## Start with Docker Compose
	docker compose up -d --build

docker-down: ## Stop Docker Compose
	docker compose down

docker-logs: ## View Docker logs
	docker compose logs -f

docker-reset: ## Reset Docker (removes all data!)
	docker compose down -v
	docker compose up -d --build

# ─── Database ───
db-init: ## Initialize database schema
	psql -U aidaptive -d aidaptive_bench -f database/migrations/001_initial.sql
	psql -U aidaptive -d aidaptive_bench -f database/migrations/002_add_indexes.sql
	$(VENV)/bin/python -m database.seed

db-reset: ## Reset database (DROP + CREATE)
	@echo "WARNING: This will delete all data!"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	sudo -u postgres psql -c "DROP DATABASE IF EXISTS aidaptive_bench;"
	sudo -u postgres psql -c "CREATE DATABASE aidaptive_bench OWNER aidaptive;"
	$(MAKE) db-init

db-migrate: ## Run latest migrations
	for f in database/migrations/*.sql; do \
		echo "Running $$f..."; \
		psql -U aidaptive -d aidaptive_bench -f $$f; \
	done

db-backup: ## Backup database
	pg_dump -U aidaptive aidaptive_bench > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup created."

db-restore: ## Restore from backup (usage: make db-restore FILE=backup.sql)
	@[ -f "$(FILE)" ] || (echo "Usage: make db-restore FILE=backup.sql" && exit 1)
	psql -U aidaptive -d aidaptive_bench < $(FILE)
	@echo "Restored from $(FILE)"

# ─── Testing ───
test: ## Run tests
	$(VENV)/bin/pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage
	$(VENV)/bin/pytest tests/ -v --cov=app --cov=core --cov=adapters --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

# ─── Code Quality ───
lint: ## Run linter
	$(VENV)/bin/ruff check .

format: ## Format code
	$(VENV)/bin/ruff format .

# ─── Utilities ───
check-servers: ## Check if AI servers are reachable
	@echo "Server 1 Ollama:" && curl -s -o /dev/null -w "%{http_code}" $(SERVER1_OLLAMA_URL) && echo "" || echo "UNREACHABLE"
	@echo "Server 1 Agent:"  && curl -s -o /dev/null -w "%{http_code}" $(SERVER1_AGENT_URL)  && echo "" || echo "UNREACHABLE"
	@echo "Server 2 Ollama:" && curl -s -o /dev/null -w "%{http_code}" $(SERVER2_OLLAMA_URL) && echo "" || echo "UNREACHABLE"
	@echo "Server 2 Agent:"  && curl -s -o /dev/null -w "%{http_code}" $(SERVER2_AGENT_URL)  && echo "" || echo "UNREACHABLE"

clean: ## Clean build artifacts
	rm -rf __pycache__ .pytest_cache htmlcov .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
```

## 8.6 `requirements.txt`

```txt
# ═══════════════════════════════════════════
#  aiDaptive Benchmark Suite - Dependencies
# ═══════════════════════════════════════════

# ─── Web Framework ───
fastapi==0.104.1
uvicorn[standard]==0.24.0
jinja2==3.1.2
python-multipart==0.0.6

# ─── Database ───
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.13.0

# ─── HTTP Client ───
httpx==0.25.2
requests==2.31.0

# ─── Configuration ───
pydantic-settings==2.1.0
python-dotenv==1.0.0
pyyaml==6.0.1

# ─── Benchmark Tools (Python-based) ───
litellm==1.16.0
locust==2.20.0
# llmperf - install separately if needed

# ─── Export ───
# weasyprint==60.2  # Optional: for PDF export

# ─── Utilities ───
python-dateutil==2.8.2
tabulate==0.9.0

# ─── Development ───
pytest==7.4.3
pytest-asyncio==0.23.2
pytest-cov==4.1.0
ruff==0.1.8
```

## 8.7 Deployment Checklist

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT CHECKLIST                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PRE-DEPLOYMENT                                                  │
│  ─────────────                                                   │
│  ☐ AI Server 1 accessible (SSH + network)                       │
│  ☐ AI Server 2 accessible (SSH + network)                       │
│  ☐ Controller node provisioned                                  │
│  ☐ Network connectivity verified                                │
│  ☐ Firewall rules configured (11434, 9100, 8000, 5432)         │
│                                                                  │
│  AI SERVER 1 (aiDaptive+ Disabled)                              │
│  ──────────────────────────────────                              │
│  ☐ NVIDIA driver installed (≥535)                               │
│  ☐ nvidia-smi working                                           │
│  ☐ Ollama installed and running                                 │
│  ☐ Ollama listening on 0.0.0.0:11434                           │
│  ☐ Model pulled (llama3.2:1b)                                   │
│  ☐ Agent installed and running on :9100                         │
│  ☐ Agent /metrics endpoint returning data                       │
│  ☐ Agent /hardware endpoint returning data                      │
│  ☐ aiDaptive+ confirmed DISABLED                                │
│                                                                  │
│  AI SERVER 2 (aiDaptive+ Enabled)                               │
│  ──────────────────────────────────                              │
│  ☐ (Same as Server 1 steps above)                               │
│  ☐ aiDaptive+ installed and confirmed ENABLED                   │
│  ☐ aiDaptive+ status verified                                   │
│                                                                  │
│  CONTROLLER NODE                                                 │
│  ────────────────                                                │
│  ☐ Python 3.10+ installed                                       │
│  ☐ PostgreSQL 15 installed and running                          │
│  ☐ Database created and schema initialized                      │
│  ☐ Seed data loaded                                             │
│  ☐ .env configured with correct server IPs                      │
│  ☐ External tools installed (oha, k6)                           │
│  ☐ Python packages installed                                    │
│  ☐ Application starts without errors                            │
│  ☐ Web UI accessible at http://controller:8000                  │
│                                                                  │
│  VERIFICATION                                                    │
│  ────────────                                                    │
│  ☐ Dashboard shows both servers Online (🟢)                     │
│  ☐ Hardware auto-detected correctly on both servers             │
│  ☐ Models visible in Servers page                               │
│  ☐ Preflight check passes (all green)                           │
│  ☐ Test benchmark runs successfully (use "single_request")      │
│  ☐ Results visible in History page                              │
│  ☐ Charts rendering correctly                                   │
│  ☐ CSV export works                                             │
│                                                                  │
│  POST-DEPLOYMENT                                                 │
│  ────────────────                                                │
│  ☐ Run full "all" suite benchmark                               │
│  ☐ Verify comparison results make sense                         │
│  ☐ Export PDF report                                            │
│  ☐ Set up regular backup (pg_dump cron)                         │
│  ☐ Document server IPs and credentials                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 8.8 Troubleshooting Guide

### 8.8.1 Common Issues

| # | Issue | Symptom | Solution |
|---|-------|---------|----------|
| 1 | **Server Offline** | Dashboard shows 🔴 | Check Ollama/Agent service: `systemctl status ollama` |
| 2 | **Model Not Found** | Preflight check fails | Pull model: `ollama pull llama3.2:1b` |
| 3 | **DB Connection Failed** | App startup error | Check PostgreSQL: `systemctl status postgresql`, verify `.env` |
| 4 | **Ollama Timeout** | Benchmark test fails | Increase `REQUEST_TIMEOUT`, check GPU memory |
| 5 | **Agent No GPU Data** | GPU metrics all null | Check nvidia-smi: `nvidia-smi`, reinstall NVIDIA driver |
| 6 | **oha Not Found** | Benchmark skips oha tests | Run `scripts/setup_tools.sh` |
| 7 | **k6 Not Found** | Benchmark skips k6 tests | Run `scripts/setup_tools.sh` |
| 8 | **Port Already in Use** | App won't start | Kill existing process: `lsof -i :8000` then `kill -9 <PID>` |
| 9 | **VRAM Full** | OOM during benchmark | Use smaller model or reduce `MAX_TOKENS` |
| 10 | **Firewall Blocking** | Can't reach servers | Check: `curl http://<server-ip>:11434` |

### 8.8.2 Diagnostic Commands

```bash
# ─── Controller Node ───

# Check app status
curl http://localhost:8000/api/health

# Check full system status
curl http://localhost:8000/api/status | python -m json.tool

# Check database
psql -U aidaptive -d aidaptive_bench -c "SELECT COUNT(*) FROM benchmark_runs;"

# Check logs (Docker)
docker compose logs -f controller --tail=100

# Check logs (manual)
cat /var/log/aidaptive/app.log

# ─── AI Server ───

# Check Ollama
curl http://localhost:11434/api/tags
curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"llama3.2:1b","prompt":"hello","stream":false,"options":{"num_predict":10}}'

# Check Agent
curl http://localhost:9100/
curl http://localhost:9100/metrics
curl http://localhost:9100/hardware

# Check GPU
nvidia-smi
nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv

# Check connectivity from controller
curl -m 5 http://<server1-ip>:11434/api/tags
curl -m 5 http://<server1-ip>:9100/metrics
curl -m 5 http://<server2-ip>:11434/api/tags
curl -m 5 http://<server2-ip>:9100/metrics
```

### 8.8.3 Performance Tuning

```
┌─────────────────────────────────────────────────────────────────┐
│                    PERFORMANCE TUNING GUIDE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  OLLAMA OPTIMIZATION                                             │
│  ────────────────────                                            │
│  • Set OLLAMA_NUM_PARALLEL=1 for consistent benchmarks          │
│  • Set OLLAMA_MAX_LOADED_MODELS=1 to avoid VRAM contention      │
│  • Set OLLAMA_GPU_LAYERS=-1 for full GPU offloading              │
│  • Restart Ollama between test suites if VRAM fragmented         │
│                                                                  │
│  BENCHMARK ACCURACY                                              │
│  ──────────────────                                              │
│  • Increase REPEAT_COUNT to 10+ for production reports           │
│  • Increase WARMUP_REQUESTS to 5+ for GPU warming               │
│  • Increase COOLDOWN_SECONDS to 15-30 for thermal consistency    │
│  • Close all other processes on AI servers during benchmark      │
│  • Ensure A/C or cooling is consistent across servers            │
│  • Run at similar times of day (thermal ambient matters)         │
│                                                                  │
│  NETWORK                                                         │
│  ───────                                                         │
│  • Use LAN connection (not VPN) for lowest latency              │
│  • Ping servers first to check base latency                      │
│  • Disable power management on network interfaces               │
│                                                                  │
│  DATABASE                                                        │
│  ────────                                                        │
│  • Run VACUUM ANALYZE after large batch of runs                  │
│  • Monitor disk usage: hardware_snapshots grows fastest          │
│  • Set up retention policy for old snapshots                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

# 9. WORKFLOW VÀ USE CASES

## 9.1 Primary Workflow: Full Benchmark Run

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRIMARY WORKFLOW: FULL BENCHMARK RUN                       │
└─────────────────────────────────────────────────────────────────────────────┘

 ┌─────────────┐
 │  1. PREPARE │
 └──────┬──────┘
        │
        ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  • Open Web UI at http://controller:8000                    │
 │  • Check Dashboard → Both servers 🟢 Online                │
 │  • Navigate to Servers → Verify hardware detected           │
 │  • Verify model loaded: llama3.2:1b on both servers         │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────┐
 │ 2. CONFIGURE│
 └──────┬──────┘
        │
        ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  • Navigate to Benchmark page                               │
 │  • Preflight check: All green ✓                             │
 │  • Select suite: "All Suites"                               │
 │  • Select servers: Both checked                             │
 │  • Add notes: "Production benchmark run v2.0"               │
 │  • Add tags: [production] [v2.0]                            │
 │  • Review estimated duration: ~25 minutes                   │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────┐
 │  3. EXECUTE │
 └──────┬──────┘
        │
        ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  • Click "▶ START BENCHMARK"                                │
 │  • Phase 1: Preflight (5 sec)                               │
 │  │  - Check all connections                                 │
 │  │  - Verify model availability                             │
 │  │                                                          │
 │  • Phase 2: Warmup (30 sec)                                 │
 │  │  - 3 warmup requests per server                          │
 │  │  - GPU and model loaded into memory                      │
 │  │                                                          │
 │  • Phase 3: Benchmarking (~20 min)                          │
 │  │  - 264 tests across all combinations                     │
 │  │  - Each test repeated 5 times                            │
 │  │  - Progress bar updates in real-time                     │
 │  │  - Live metrics visible (TPS, GPU%, Temp)                │
 │  │                                                          │
 │  • Phase 4: Finalize (10 sec)                               │
 │  │  - Compare S1 vs S2 results                              │
 │  │  - Calculate delta percentages                           │
 │  │  - Determine winners per tool/scenario                   │
 │  │  - Save comparisons to database                          │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────┐
 │ 4. ANALYZE  │
 └──────┬──────┘
        │
        ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  • Auto-redirect to Run Detail page                         │
 │  • Review Summary Cards:                                    │
 │  │  - TPS Gain: +29.9%                                     │
 │  │  - TTFT Gain: -16.8%                                    │
 │  │  - P99 Gain: -28.0%                                     │
 │  │  - Winner: 🏆 Server 2 (aiDaptive+ Enabled)             │
 │  │                                                          │
 │  • Review Charts:                                           │
 │  │  - TPS by Tool (Bar chart)                               │
 │  │  - Latency Comparison (Grouped bar)                      │
 │  │  - GPU Timeline (Line chart)                             │
 │  │  - Delta % (Horizontal bar)                              │
 │  │                                                          │
 │  • Review Detailed Results Table                            │
 │  │  - Per tool/scenario breakdown                           │
 │  │  - All metrics visible                                   │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────┐
 │  5. EXPORT  │
 └──────┬──────┘
        │
        ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  • Click "📄 Export PDF Report"                             │
 │  │  - Full report with charts and tables                    │
 │  │  - Hardware specs included                               │
 │  │  - Suitable for stakeholder presentation                 │
 │  │                                                          │
 │  • Click "📊 Export CSV Data"                               │
 │  │  - Raw data for further analysis                         │
 │  │  - Import into Excel/Google Sheets                       │
 │  │                                                          │
 │  • Click "📋 Copy Summary" for quick sharing                │
 └─────────────────────────────────────────────────────────────┘
```

## 9.2 Use Case Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USE CASE DIAGRAM                                   │
└─────────────────────────────────────────────────────────────────────────────┘

                         ┌──────────────┐
                         │   Engineer   │
                         └──────┬───────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ UC1: View     │    │ UC2: Run         │    │ UC3: View        │
│ Server Status │    │ Benchmark        │    │ History          │
│               │    │                  │    │                  │
│ • Check online│    │ • Configure      │    │ • List runs      │
│ • View HW     │    │ • Start          │    │ • Filter/Search  │
│ • Live metrics│    │ • Monitor        │    │ • View detail    │
└───────────────┘    │ • Stop           │    │ • View charts    │
                     └──────────────────┘    └──────────────────┘
        │                       │                       │
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ UC4: Compare  │    │ UC5: Export      │    │ UC6: Configure   │
│ Runs          │    │ Results          │    │ Settings         │
│               │    │                  │    │                  │
│ • Select 2    │    │ • CSV download   │    │ • Server URLs    │
│ • Side-by-side│    │ • PDF report     │    │ • Benchmark opts │
│ • Trend       │    │ • JSON export    │    │ • Scenarios      │
│   analysis    │    │ • Copy summary   │    │ • Tools toggle   │
└───────────────┘    └──────────────────┘    │ • Theme          │
                                             └──────────────────┘

                         ┌──────────────┐
                         │  Sales/Exec  │
                         └──────┬───────┘
                                │
                ┌───────────────┼───────────────┐
                │                               │
                ▼                               ▼
     ┌──────────────────┐           ┌──────────────────┐
     │ UC7: View        │           │ UC8: Download     │
     │ Dashboard        │           │ Report            │
     │                  │           │                   │
     │ • Quick stats    │           │ • PDF for clients │
     │ • Win rate       │           │ • Share link      │
     │ • Recent runs    │           │                   │
     │ • Trend chart    │           │                   │
     └──────────────────┘           └──────────────────┘
```

## 9.3 Use Case Details

### UC1: View Server Status

```
┌─────────────────────────────────────────────────────────────────┐
│  USE CASE: UC1 - View Server Status                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Actor:       Engineer                                          │
│  Page:        /servers                                          │
│  Precondition: App is running                                   │
│                                                                  │
│  Main Flow:                                                      │
│  1. User navigates to Servers page                              │
│  2. System queries both AI servers (Ollama + Agent)             │
│  3. System displays connection status (🟢/🔴)                  │
│  4. System auto-detects and displays hardware info              │
│  5. System shows live resource usage (GPU, CPU, RAM)            │
│  6. System shows loaded models                                  │
│  7. Page auto-refreshes every 5 seconds                         │
│                                                                  │
│  Alternate Flows:                                                │
│  3a. Server offline → Show 🔴 with last seen timestamp          │
│  4a. Agent unreachable → Show "Hardware: Unknown"               │
│  5a. nvidia-smi fails → GPU metrics show as "N/A"              │
│                                                                  │
│  API Calls:                                                      │
│  - GET /api/servers                                             │
│  - GET /api/servers/{id}/metrics (polling)                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### UC2: Run Benchmark

```
┌─────────────────────────────────────────────────────────────────┐
│  USE CASE: UC2 - Run Benchmark                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Actor:       Engineer                                          │
│  Page:        /benchmark                                        │
│  Precondition: Both servers online, model loaded                │
│                                                                  │
│  Main Flow:                                                      │
│  1. User navigates to Benchmark page                            │
│  2. System runs preflight check (all green)                     │
│  3. User selects test suite (e.g., "All Suites")               │
│  4. User selects servers (both checked)                         │
│  5. User optionally adds notes and tags                         │
│  6. User clicks "▶ START BENCHMARK"                             │
│  7. System creates run record in DB (status: running)           │
│  8. System begins Phase 1-4 execution                           │
│  9. UI shows real-time progress bar (polling /api/progress)     │
│  10. UI shows live metrics (TPS, GPU%, test log)                │
│  11. Benchmark completes                                        │
│  12. System generates comparisons                               │
│  13. System updates run status to "completed"                   │
│  14. UI auto-redirects to Run Detail page                       │
│                                                                  │
│  Alternate Flows:                                                │
│  2a. Preflight fails → Show errors, disable Start button        │
│  6a. Benchmark already running → Show error 409                 │
│  8a. Individual test fails → Log error, continue to next        │
│  10a. User clicks "⏹ STOP" → Graceful stop, save partial       │
│  11a. Fatal error → Status "failed", show error log             │
│                                                                  │
│  API Calls:                                                      │
│  - POST /api/benchmark/start                                    │
│  - GET  /api/benchmark/progress (polling every 2s)              │
│  - POST /api/benchmark/stop (optional)                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### UC3: View History & Run Detail

```
┌─────────────────────────────────────────────────────────────────┐
│  USE CASE: UC3 - View History & Run Detail                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Actor:       Engineer / Sales                                  │
│  Pages:       /history, /history/{run_id}                       │
│  Precondition: At least 1 completed run exists                  │
│                                                                  │
│  Flow A: Browse History                                          │
│  1. User navigates to History page                              │
│  2. System displays paginated list of runs                      │
│  3. User optionally filters by status/suite/tag                 │
│  4. User optionally searches by run ID                          │
│  5. User clicks on a run row                                    │
│  6. System navigates to Run Detail page                         │
│                                                                  │
│  Flow B: View Run Detail                                         │
│  1. System loads run metadata, summary, comparisons             │
│  2. System displays summary cards (TPS Δ, TTFT Δ, Winner)      │
│  3. System renders charts via Chart.js:                         │
│     a. TPS by Tool (Bar chart)                                  │
│     b. Latency Comparison (Grouped bar)                         │
│     c. GPU Timeline (Line chart)                                │
│     d. Temperature Timeline (Line chart)                        │
│     e. Delta % Summary (Horizontal bar)                         │
│  4. System displays detailed results table                      │
│  5. System displays per-tool comparison table                   │
│  6. User can switch between chart tabs                          │
│  7. User can filter results table by tool/scenario/server       │
│                                                                  │
│  Flow C: Delete Run                                              │
│  1. User selects run(s) in History page                         │
│  2. User clicks "🗑 Delete Selected"                            │
│  3. System shows confirmation dialog                            │
│  4. User confirms                                               │
│  5. System deletes run + all related data (CASCADE)             │
│                                                                  │
│  API Calls:                                                      │
│  - GET /api/runs?limit=20&offset=0&status=completed             │
│  - GET /api/runs/{run_id}                                       │
│  - GET /api/charts/comparison/{run_id}                          │
│  - GET /api/charts/timeline/{run_id}                            │
│  - GET /api/charts/summary/{run_id}                             │
│  - DELETE /api/runs/{run_id}                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### UC4: Compare Two Runs

```
┌─────────────────────────────────────────────────────────────────┐
│  USE CASE: UC4 - Compare Two Runs                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Actor:       Engineer                                          │
│  Page:        /comparison                                       │
│  Precondition: At least 2 completed runs exist                  │
│                                                                  │
│  Main Flow:                                                      │
│  1. User navigates to Comparison page                           │
│     OR selects 2 runs in History and clicks "📊 Compare"        │
│  2. User selects Run A from dropdown                            │
│  3. User selects Run B from dropdown                            │
│  4. User clicks "⚖️ COMPARE"                                   │
│  5. System loads both run summaries                             │
│  6. System displays side-by-side summary table:                 │
│     - S2 Avg TPS, TTFT, P99 for both runs                      │
│     - TPS Gain (Δ%) for both runs                               │
│     - Winner for both runs                                      │
│     - Delta between runs (pp = percentage points)               │
│  7. System displays cross-run charts:                           │
│     - TPS by server per run (4-bar grouped chart)               │
│     - Improvement trend (horizontal bar)                        │
│  8. System displays per-tool cross-run comparison               │
│  9. System displays hardware context (GPU%, Temp for both)      │
│  10. User can export comparison as PDF/CSV                      │
│                                                                  │
│  Use when:                                                       │
│  - Comparing results before/after a config change               │
│  - Validating consistency across runs                           │
│  - Showing improvement trend to stakeholders                    │
│                                                                  │
│  API Calls:                                                      │
│  - GET /api/runs/{run_a_id}                                     │
│  - GET /api/runs/{run_b_id}                                     │
│  - GET /api/charts/comparison/{run_a_id}                        │
│  - GET /api/charts/comparison/{run_b_id}                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### UC5: Export Results

```
┌─────────────────────────────────────────────────────────────────┐
│  USE CASE: UC5 - Export Results                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Actor:       Engineer / Sales                                  │
│  Page:        /history/{run_id}                                 │
│  Precondition: Run completed                                    │
│                                                                  │
│  Flow A: Export CSV                                              │
│  1. User clicks "📊 Export CSV"                                 │
│  2. System generates CSV with all result rows                   │
│  3. Browser downloads file: run_YYYYMMDD_HHMMSS.csv             │
│                                                                  │
│  Flow B: Export PDF Report                                       │
│  1. User clicks "📄 Export PDF"                                 │
│  2. System generates PDF with:                                  │
│     - Cover page (run ID, date, winner)                         │
│     - Executive summary (key metrics)                           │
│     - Hardware specifications table                             │
│     - Comparison summary table                                  │
│     - Charts (TPS, Latency, Delta, GPU Timeline)                │
│     - Detailed results table                                    │
│     - Methodology notes                                         │
│  3. Browser downloads file: benchmark_report_YYYYMMDD.pdf       │
│                                                                  │
│  Flow C: Export JSON                                             │
│  1. User calls GET /api/runs/{run_id}/export?format=json        │
│  2. System returns full JSON with run + results + comparisons   │
│                                                                  │
│  Flow D: Copy Summary                                            │
│  1. User clicks "📋 Copy Summary"                               │
│  2. System copies formatted text to clipboard:                  │
│     ─────────────────────────────────────────                   │
│     aiDaptive Benchmark Results                                 │
│     Run: run_20240415_143022                                    │
│     Date: Apr 15, 2024                                          │
│     Model: llama3.2:1b                                          │
│                                                                  │
│     TPS:  S1=45.2  S2=58.7  Δ=+29.9%                           │
│     TTFT: S1=150ms S2=125ms Δ=-16.8%                           │
│     P99:  S1=2500ms S2=1800ms Δ=-28.0%                         │
│                                                                  │
│     Winner: 🏆 Server 2 (aiDaptive+ Enabled)                   │
│     ─────────────────────────────────────────                   │
│                                                                  │
│  API Calls:                                                      │
│  - GET /api/runs/{run_id}/export?format=csv                     │
│  - GET /api/runs/{run_id}/export?format=json                    │
│  - GET /api/runs/{run_id}/export?format=pdf                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### UC6: Configure Settings

```
┌─────────────────────────────────────────────────────────────────┐
│  USE CASE: UC6 - Configure Settings                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Actor:       Engineer (Admin)                                  │
│  Page:        /settings                                         │
│  Precondition: App is running                                   │
│                                                                  │
│  Main Flow:                                                      │
│  1. User navigates to Settings page                             │
│  2. System displays current configuration                       │
│  3. User can modify:                                            │
│     a. Server Configuration                                     │
│        - Server names, Ollama URLs, Agent URLs                  │
│        - aiDaptive+ toggle                                      │
│        - Test Connection button                                 │
│     b. Benchmark Defaults                                       │
│        - Default model                                          │
│        - Warmup requests, repeat count                          │
│        - Concurrency levels                                     │
│        - Request timeout, cooldown                              │
│        - Max tokens, temperature                                │
│     c. Scenarios                                                │
│        - Enable/disable scenarios                               │
│        - Add custom scenarios                                   │
│     d. Active Tools                                             │
│        - Enable/disable benchmark tools                         │
│     e. Database                                                 │
│        - Connection string (read-only display)                  │
│        - Data retention settings                                │
│        - Purge/Export/Reset buttons                              │
│     f. Appearance                                               │
│        - Dark/Light/System theme                                │
│        - Chart style                                            │
│        - Auto-refresh interval                                  │
│  4. User clicks "💾 SAVE SETTINGS"                              │
│  5. System validates and saves configuration                    │
│  6. System shows success notification                           │
│                                                                  │
│  Alternate Flows:                                                │
│  3a-1. Test Connection fails → Show error with details          │
│  4a. Invalid config → Show validation errors inline             │
│  5a-1. "🗑 Purge Old Data" → Confirmation → Delete old snapshots│
│  5a-2. "🔄 Reset Database" → Double confirmation → DROP+CREATE  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 9.4 State Machine: Benchmark Run Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BENCHMARK RUN STATE MACHINE                                │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────┐
                    │             │
       POST /start │   PENDING   │
      ────────────>│             │
                    │  (created)  │
                    └──────┬──────┘
                           │
                    Orchestrator picks up
                           │
                           ▼
                    ┌─────────────┐
                    │             │
                    │   RUNNING   │◄──────────────────────┐
                    │             │                        │
                    │  Phases:    │                        │
                    │  1.Preflight│          Progress      │
                    │  2.Warmup   │          updates       │
                    │  3.Benchmark│──────────────────────>│
                    │  4.Finalize │                        │
                    └──────┬──────┘
                           │
              ┌────────────┼─────────────┐
              │            │             │
         All tests    User clicks   Fatal error
         completed    "STOP"         occurs
              │            │             │
              ▼            ▼             ▼
       ┌───────────┐ ┌──────────┐ ┌──────────┐
       │           │ │          │ │          │
       │ COMPLETED │ │ STOPPED  │ │  FAILED  │
       │           │ │          │ │          │
       │ All data  │ │ Partial  │ │ Partial  │
       │ saved     │ │ results  │ │ results  │
       │ Compare-  │ │ saved    │ │ may be   │
       │ isons     │ │ No compa-│ │ saved    │
       │ generated │ │ risons   │ │ Error    │
       │           │ │          │ │ logged   │
       └───────────┘ └──────────┘ └──────────┘
              │            │             │
              └────────────┼─────────────┘
                           │
                    Can be viewed
                    in History
                           │
                           ▼
                    ┌─────────────┐
                    │   DELETED   │  (via DELETE /api/runs/{id})
                    │  CASCADE    │
                    │  removes    │
                    │  all data   │
                    └─────────────┘

State Transitions:
┌──────────────┬──────────────┬────────────────────────────────┐
│ From         │ To           │ Trigger                         │
├──────────────┼──────────────┼────────────────────────────────┤
│ (none)       │ PENDING      │ POST /api/benchmark/start      │
│ PENDING      │ RUNNING      │ Orchestrator._execute() called │
│ RUNNING      │ COMPLETED    │ All tests finished normally     │
│ RUNNING      │ STOPPED      │ POST /api/benchmark/stop       │
│ RUNNING      │ FAILED       │ Unrecoverable error            │
│ COMPLETED    │ (deleted)    │ DELETE /api/runs/{id}           │
│ STOPPED      │ (deleted)    │ DELETE /api/runs/{id}           │
│ FAILED       │ (deleted)    │ DELETE /api/runs/{id}           │
└──────────────┴──────────────┴────────────────────────────────┘
```

## 9.5 Scenario: Sales Demo Flow



```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SALES DEMO SCENARIO                                        │
│                    (15-minute live demo for potential customer)               │
└─────────────────────────────────────────────────────────────────────────────┘

Time    Action                                      What audience sees
─────   ──────────────────────────────────────────  ─────────────────────────

0:00    Open Dashboard                              Quick stats, server status
        "Here's our benchmark platform..."          Both servers green
                                                    Win rate 100%, trend chart

0:02    Navigate to Servers                         Hardware specs side-by-side
        "Server 1 is a powerful RTX 4090."          S1: RTX 4090, 24GB VRAM
        "Server 2 is a RTX 3070 with aiDaptive+."  S2: RTX 3070, 8GB VRAM
                                                    Hardware comparison table
                                                    "S1 has 3x the GPU power"

0:04    Navigate to Benchmark                       Config panel, preflight ✓
        "Let's run a quick test live..."            All checks green
        Select: "Single Request" suite              Estimated: ~8 minutes
        Click "▶ START BENCHMARK"

0:05    Watch progress (live)                       Progress bar advancing
        "We're testing 7 different tools             42 tests running
        across 6 scenarios..."                      Live TPS numbers appearing
        "Notice the live GPU utilization..."         GPU 78% S1, 85% S2

0:06    Point out live metrics                      Test log scrolling
        "Server 2 is already showing higher          S2 TPS: 58.7 vs S1: 45.2
        tokens per second..."                       Green indicators

0:10    Benchmark completes                         Auto-redirect to results
        "And we're done! Let's look at               Summary cards appear
        the results..."                             🏆 Server 2 wins

0:11    Walk through Summary Cards                  4 green delta cards
        "TPS improved 29.9%"                        +29.9% TPS
        "First token 16.8% faster"                  -16.8% TTFT
        "Tail latency dropped 28%"                  -28.0% P99
        "Error rate cut by 40%"                     -40.0% Error Rate

0:12    Show Charts                                 Bar chart, side-by-side
        "Every tool shows the same pattern..."      All bars: S2 > S1
        "Even the weakest GPU wins with              Delta chart: all green
        aiDaptive+."                                GPU timeline overlay

0:13    Show Detailed Table                         Per-tool breakdown
        "Across all 42 test combinations,            42/42 wins for S2
        Server 2 with aiDaptive+ wins every          Consistent improvement
        single one."

0:14    Navigate to History                         List of past runs
        "And this isn't a one-time result.           All showing S2 wins
        Here are our last 10 runs..."               100% win rate

0:15    Export PDF                                  PDF downloading
        "I'll send you the full report               Professional report
        with all the data."                         with charts + tables
        
        "Questions?"

─────────────────────────────────────────────────────────────────────────────

KEY TALKING POINTS:
• "Server 2 has 3x LESS GPU power but STILL outperforms"
• "This is not one tool's opinion - 7 independent tools agree"
• "Every scenario - chat, code, long text - all faster"
• "These are reproducible results you can verify yourself"
• "aiDaptive+ delivers 30% improvement on weaker hardware"
```

## 9.6 Scenario: Engineering Regression Test

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ENGINEERING REGRESSION TEST                                │
│                    (After aiDaptive+ version update)                         │
└─────────────────────────────────────────────────────────────────────────────┘

GOAL: Verify that aiDaptive+ v2.1 maintains or improves performance
      compared to aiDaptive+ v2.0 baseline.

STEP 1: BASELINE (already exists)
─────────────────────────────────
• Run ID: run_20240415_143022 (v2.0, completed, TPS Δ = +29.9%)
• This is our reference point

STEP 2: UPDATE aiDaptive+
─────────────────────────
• SSH to Server 2
• sudo aidaptive-plus update --version 2.1
• sudo systemctl restart ollama
• Verify: sudo aidaptive-plus status → v2.1 ENABLED

STEP 3: RUN NEW BENCHMARK
──────────────────────────
• Open Web UI → Benchmark page
• Verify both servers online
• Configure:
  - Suite: "All Suites"
  - Notes: "Regression test after aiDaptive+ v2.1 update"
  - Tags: [regression] [v2.1]
• Start benchmark
• Wait for completion (~25 min)

STEP 4: COMPARE RESULTS
────────────────────────
• Navigate to Comparison page
• Select Run A: run_20240416_100000 (v2.1, new)
• Select Run B: run_20240415_143022 (v2.0, baseline)
• Click "⚖️ COMPARE"

STEP 5: ANALYZE
────────────────
Expected outcomes:

┌─────────────────────────────────────────────────────────────────┐
│  Scenario         │ v2.0 TPS Δ │ v2.1 TPS Δ │ Result          │
│  ──────────────────┼────────────┼────────────┼──────────────── │
│  A. Improved       │ +29.9%     │ +33.5%     │ ✓ PASS (+3.6pp)│
│  B. Maintained     │ +29.9%     │ +29.2%     │ ✓ PASS (within │
│                    │            │            │   margin)       │
│  C. Degraded       │ +29.9%     │ +22.0%     │ ✗ FAIL (-7.9pp)│
│                    │            │            │   INVESTIGATE   │
└─────────────────────────────────────────────────────────────────┘

ACCEPTANCE CRITERIA:
• TPS Δ must be ≥ 25% (within 5pp of baseline)
• TTFT Δ must be ≥ 12% (within 5pp of baseline)
• Error rate must not increase
• No new failures in any tool/scenario combination

STEP 6: REPORT
───────────────
• If PASS: Export PDF, update changelog, approve release
• If FAIL: Export CSV, analyze per-tool breakdown, file bug
```

## 9.7 Scenario: Multi-Model Benchmark Campaign

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MULTI-MODEL BENCHMARK CAMPAIGN                            │
│                    (Test aiDaptive+ across different LLM models)             │
└─────────────────────────────────────────────────────────────────────────────┘

GOAL: Prove aiDaptive+ improvement is consistent across model sizes.

CAMPAIGN PLAN:
┌──────────────────────┬──────────┬───────────┬──────────────────┐
│ Run # │ Model        │ Size     │ Tags                         │
├───────┼──────────────┼──────────┼──────────────────────────────┤
│ 1     │ llama3.2:1b  │ 1.3 GB   │ [campaign] [small-model]     │
│ 2     │ llama3.2:3b  │ 2.0 GB   │ [campaign] [medium-model]    │
│ 3     │ llama3.1:8b  │ 4.7 GB   │ [campaign] [large-model]     │
│ 4     │ mistral:7b   │ 4.1 GB   │ [campaign] [mistral]         │
│ 5     │ phi3:mini    │ 2.3 GB   │ [campaign] [phi3]            │
└───────┴──────────────┴──────────┴──────────────────────────────┘

EXECUTION SEQUENCE:

For each model:
  1. Pull model on BOTH servers:
     Server 1: ollama pull {model}
     Server 2: ollama pull {model}
  
  2. Update Settings → Default Model → {model}
  
  3. Navigate to Benchmark → Start
     Suite: "All Suites"
     Notes: "Campaign: {model} benchmark"
     Tags: [campaign] [{model-tag}]
  
  4. Wait for completion
  
  5. Review results, note TPS Δ%

EXPECTED RESULTS:

┌──────────────┬──────────┬──────────┬──────────┬────────────────┐
│ Model        │ S1 TPS   │ S2 TPS   │ TPS Δ    │ Hypothesis     │
├──────────────┼──────────┼──────────┼──────────┼────────────────┤
│ llama3.2:1b  │ ~45      │ ~59      │ ~+30%    │ Strong gain    │
│ llama3.2:3b  │ ~28      │ ~36      │ ~+28%    │ Strong gain    │
│ llama3.1:8b  │ ~12      │ ~15      │ ~+25%    │ Moderate gain  │
│ mistral:7b   │ ~14      │ ~18      │ ~+28%    │ Strong gain    │
│ phi3:mini    │ ~32      │ ~41      │ ~+28%    │ Strong gain    │
└──────────────┴──────────┴──────────┴──────────┴────────────────┘

ANALYSIS (Post-Campaign):

1. Navigate to History → Filter by tag "campaign"
2. For each pair, use Comparison page
3. Create summary matrix (as above)
4. Key insight: "aiDaptive+ delivers 25-30% improvement 
   regardless of model size"

DELIVERABLE:
• 5 individual PDF reports
• 1 summary campaign report (manual compilation)
• CSV data for all runs
```

## 9.8 Scenario: Troubleshooting Failed Benchmark

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TROUBLESHOOTING FAILED BENCHMARK                          │
└─────────────────────────────────────────────────────────────────────────────┘

SYMPTOM: Benchmark failed at 15/84 tests

STEP 1: CHECK RUN DETAIL
─────────────────────────
• Navigate to History → Click failed run
• Status: ✗ Failed
• Completed: 15/84 tests
• Error log visible in progress section

STEP 2: READ ERROR LOG
───────────────────────
Common errors and solutions:

┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  ERROR: "Preflight: server1_ollama returned 502"                        │
│  ─────────────────────────────────────────────────                       │
│  Cause: Ollama service crashed or restarting                            │
│  Fix:   SSH to Server 1 → systemctl restart ollama                      │
│         Wait 30 seconds → Retry benchmark                               │
│                                                                          │
│  ERROR: "Preflight: server2_agent unreachable - Connection refused"     │
│  ─────────────────────────────────────────────────────────────────       │
│  Cause: Agent not running on Server 2                                   │
│  Fix:   SSH to Server 2 → systemctl start aidaptive-agent               │
│         Check: curl http://localhost:9100/                               │
│                                                                          │
│  ERROR: "server1/code_gen/ollama_native: Request timeout after 120s"    │
│  ─────────────────────────────────────────────────────────────────       │
│  Cause: Model too slow for prompt, VRAM pressure                        │
│  Fix:   Increase REQUEST_TIMEOUT to 180s in Settings                    │
│         Or reduce MAX_TOKENS                                            │
│         Or use smaller model                                            │
│                                                                          │
│  ERROR: "server2/simple_chat/oha: Command failed: oha not found"       │
│  ─────────────────────────────────────────────────────────────────       │
│  Cause: oha binary not installed on controller                          │
│  Fix:   Run: ./scripts/setup_tools.sh                                   │
│         Or: cargo install oha                                           │
│                                                                          │
│  ERROR: "CUDA out of memory"                                            │
│  ────────────────────────────                                            │
│  Cause: VRAM exhausted during inference                                 │
│  Fix:   Reduce concurrency levels                                       │
│         Reduce MAX_TOKENS                                               │
│         Use smaller model                                               │
│         Set OLLAMA_MAX_LOADED_MODELS=1                                  │
│         Restart Ollama to clear VRAM                                    │
│                                                                          │
│  ERROR: "Fatal: All preflight checks failed"                            │
│  ────────────────────────────────────────────                            │
│  Cause: Network connectivity issue                                      │
│  Fix:   Check firewall: sudo ufw status                                 │
│         Check routing: ping <server-ip>                                  │
│         Check ports: nc -zv <server-ip> 11434                           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

STEP 3: FIX AND RETRY
──────────────────────
1. Apply fix from above
2. Verify: make check-servers
3. Navigate to Benchmark page
4. Preflight should now be all green ✓
5. Start new benchmark run
6. Delete the failed run if desired

STEP 4: VERIFY FIX
───────────────────
• New run completes successfully (status: ✓ Completed)
• All 84/84 tests passed
• Results consistent with previous successful runs

DIAGNOSTIC COMMANDS CHEAT SHEET:
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  # From controller:                                             │
│  make check-servers                                             │
│  curl http://localhost:8000/api/status | python -m json.tool    │
│                                                                  │
│  # From AI Server:                                              │
│  nvidia-smi                                                     │
│  systemctl status ollama                                        │
│  systemctl status aidaptive-agent                               │
│  curl localhost:11434/api/tags                                  │
│  curl localhost:9100/metrics                                    │
│  journalctl -u ollama --since "1 hour ago"                      │
│  dmesg | grep -i "out of memory"                                │
│  free -h                                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 9.9 Scenario: Scheduled Daily Benchmarks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SCHEDULED DAILY BENCHMARKS                                │
│                    (Automated via cron + CLI)                                │
└─────────────────────────────────────────────────────────────────────────────┘

GOAL: Run benchmarks automatically every night at 2:00 AM
      to track performance consistency over time.

STEP 1: CREATE CLI SCRIPT
──────────────────────────

File: scripts/daily_benchmark.sh

┌─────────────────────────────────────────────────────────────────┐
│  #!/bin/bash                                                     │
│  #                                                               │
│  # Daily Automated Benchmark                                     │
│  # Run via cron at 2:00 AM daily                                │
│  #                                                               │
│                                                                  │
│  set -e                                                          │
│                                                                  │
│  API_URL="http://localhost:8000"                                 │
│  LOG_FILE="/var/log/aidaptive/daily_benchmark.log"               │
│  DATE=$(date +%Y-%m-%d)                                         │
│                                                                  │
│  log() {                                                         │
│      echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE│
│  }                                                               │
│                                                                  │
│  # ─── 1. Check servers are online ───                           │
│  log "Starting daily benchmark..."                               │
│                                                                  │
│  STATUS=$(curl -s "$API_URL/api/status")                         │
│  S1_ONLINE=$(echo $STATUS | python3 -c \                         │
│    "import sys,json; \                                           │
│     d=json.load(sys.stdin); \                                    │
│     print(d['servers'][0]['ollama_online'])")                     │
│  S2_ONLINE=$(echo $STATUS | python3 -c \                         │
│    "import sys,json; \                                           │
│     d=json.load(sys.stdin); \                                    │
│     print(d['servers'][1]['ollama_online'])")                     │
│                                                                  │
│  if [ "$S1_ONLINE" != "True" ] || [ "$S2_ONLINE" != "True" ]; then│
│      log "ERROR: Servers offline. S1=$S1_ONLINE S2=$S2_ONLINE"   │
│      exit 1                                                      │
│  fi                                                              │
│                                                                  │
│  # ─── 2. Check no benchmark already running ───                 │
│  IS_RUNNING=$(echo $STATUS | python3 -c \                        │
│    "import sys,json; \                                           │
│     d=json.load(sys.stdin); \                                    │
│     print(d['benchmark']['is_running'])")                        │
│                                                                  │
│  if [ "$IS_RUNNING" = "True" ]; then                             │
│      log "ERROR: Benchmark already running. Skipping."           │
│      exit 1                                                      │
│  fi                                                              │
│                                                                  │
│  # ─── 3. Start benchmark ───                                    │
│  log "Starting benchmark..."                                     │
│  RESULT=$(curl -s -X POST "$API_URL/api/benchmark/start" \       │
│    -H "Content-Type: application/json" \                         │
│    -d "{                                                         │
│      \"suite\": \"single_request\",                              │
│      \"server\": \"all\",                                        │
│      \"environment\": \"lan\",                                   │
│      \"notes\": \"Automated daily benchmark $DATE\",             │
│      \"tags\": [\"daily\", \"automated\", \"$DATE\"]             │
│    }")                                                           │
│                                                                  │
│  RUN_ID=$(echo $RESULT | python3 -c \                            │
│    "import sys,json; print(json.load(sys.stdin)['run_id'])")     │
│  log "Run started: $RUN_ID"                                      │
│                                                                  │
│  # ─── 4. Wait for completion ───                                │
│  TIMEOUT=2400  # 40 minutes max                                  │
│  ELAPSED=0                                                       │
│  INTERVAL=30                                                     │
│                                                                  │
│  while [ $ELAPSED -lt $TIMEOUT ]; do                             │
│      sleep $INTERVAL                                             │
│      ELAPSED=$((ELAPSED + INTERVAL))                             │
│                                                                  │
│      PROGRESS=$(curl -s "$API_URL/api/benchmark/progress")       │
│      PCT=$(echo $PROGRESS | python3 -c \                         │
│        "import sys,json; print(json.load(sys.stdin)['percent'])")│
│      STAT=$(echo $PROGRESS | python3 -c \                        │
│        "import sys,json; print(json.load(sys.stdin)['status'])")│
│                                                                  │
│      log "Progress: $PCT% | Status: $STAT"                       │
│                                                                  │
│      if [ "$STAT" = "completed" ]; then                          │
│          log "Benchmark completed successfully!"                 │
│          break                                                   │
│      fi                                                          │
│                                                                  │
│      if [ "$STAT" = "failed" ]; then                             │
│          log "ERROR: Benchmark failed!"                          │
│          exit 1                                                  │
│      fi                                                          │
│  done                                                            │
│                                                                  │
│  if [ $ELAPSED -ge $TIMEOUT ]; then                              │
│      log "ERROR: Benchmark timed out after ${TIMEOUT}s"          │
│      curl -s -X POST "$API_URL/api/benchmark/stop"               │
│      exit 1                                                      │
│  fi                                                              │
│                                                                  │
│  # ─── 5. Export results ───                                     │
│  EXPORT_DIR="/var/lib/aidaptive/exports"                         │
│  mkdir -p "$EXPORT_DIR"                                          │
│                                                                  │
│  curl -s "$API_URL/api/runs/${RUN_ID}/export?format=csv" \       │
│    > "$EXPORT_DIR/${RUN_ID}.csv"                                 │
│                                                                  │
│  log "CSV exported to $EXPORT_DIR/${RUN_ID}.csv"                 │
│                                                                  │
│  # ─── 6. Log summary ───                                        │
│  SUMMARY=$(curl -s "$API_URL/api/runs/$RUN_ID")                  │
│  TPS_DELTA=$(echo $SUMMARY | python3 -c \                        │
│    "import sys,json; \                                           │
│     d=json.load(sys.stdin); \                                    │
│     print(d['summary']['comparison'].get('tps_delta_pct','N/A'))")│
│  WINNER=$(echo $SUMMARY | python3 -c \                           │
│    "import sys,json; \                                           │
│     d=json.load(sys.stdin); \                                    │
│     print(d['summary']['comparison'].get('winner','N/A'))")      │
│                                                                  │
│  log "=== DAILY SUMMARY ==="                                     │
│  log "Run ID: $RUN_ID"                                           │
│  log "TPS Delta: ${TPS_DELTA}%"                                  │
│  log "Winner: $WINNER"                                           │
│  log "====================="                                     │
│                                                                  │
│  log "Daily benchmark complete."                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘


STEP 2: SET UP CRON
────────────────────

$ chmod +x scripts/daily_benchmark.sh

$ crontab -e
# Add:
0 2 * * * /opt/benchmark-suite/scripts/daily_benchmark.sh >> /var/log/aidaptive/cron.log 2>&1


STEP 3: SET UP LOG ROTATION
────────────────────────────

File: /etc/logrotate.d/aidaptive

┌─────────────────────────────────────────────────────────────────┐
│  /var/log/aidaptive/*.log {                                     │
│      daily                                                       │
│      rotate 30                                                   │
│      compress                                                    │
│      delaycompress                                               │
│      missingok                                                   │
│      notifempty                                                  │
│      create 0644 root root                                       │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘


STEP 4: WEEKLY TREND REVIEW
────────────────────────────
Every Monday:
1. Open Dashboard → Check Performance Trend chart (last 7 runs)
2. Navigate to History → Filter by tag "daily"
3. Verify consistency: TPS Δ should be stable ±3pp
4. Compare oldest vs newest daily run if needed
5. Flag any anomalies for investigation
```

## 9.10 Data Flow Summary: End-to-End

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COMPLETE DATA FLOW: END-TO-END                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────┐     ┌───────────┐     ┌──────────────┐     ┌──────────────┐
│  User   │     │  Web UI   │     │   FastAPI     │     │ Orchestrator │
│ Browser │     │ (Jinja2)  │     │  (REST API)   │     │              │
└────┬────┘     └─────┬─────┘     └──────┬───────┘     └──────┬───────┘
     │                │                   │                    │
     │  1. GET /      │                   │                    │
     │───────────────>│                   │                    │
     │                │  2. Fetch data    │                    │
     │                │──────────────────>│                    │
     │                │                   │  3. Query DB       │
     │                │                   │───────────────┐    │
     │                │                   │               │    │
     │                │                   │<──────────────┘    │
     │                │  4. Render HTML   │                    │
     │                │<──────────────────│                    │
     │  5. HTML Page  │                   │                    │
     │<───────────────│                   │                    │
     │                │                   │                    │
     │  6. POST /api/benchmark/start      │                    │
     │───────────────────────────────────>│                    │
     │                │                   │  7. Create run     │
     │                │                   │───────────────────>│
     │                │                   │                    │
     │                │                   │  8. {run_id}       │
     │                │                   │<───────────────────│
     │  9. {run_id, started}              │                    │
     │<───────────────────────────────────│                    │
     │                │                   │                    │

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Orchestrator │     │   Adapters   │     │  AI Servers  │
│  (async)     │     │  (7 tools)   │     │  (Ollama)    │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │ 10. Preflight      │                    │
       │────────────────────┼───────────────────>│
       │                    │                    │
       │ 11. OK             │                    │
       │<───────────────────┼────────────────────│
       │                    │                    │
       │ 12. Warmup         │                    │
       │────────────────────┼───────────────────>│
       │                    │                    │
       │<───────────────────┼────────────────────│
       │                    │                    │
       │ 13. For each test: │                    │
       │──────────────>     │                    │
       │  adapter.run()     │  14. HTTP POST     │
       │                    │───────────────────>│
       │                    │                    │
       │                    │  15. Response      │
       │                    │   (streaming)      │
       │                    │<───────────────────│
       │                    │                    │
       │  16. Parsed result │                    │
       │<──────────────     │                    │
       │                    │                    │

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Orchestrator │     │  Data Sink   │     │  PostgreSQL  │
│  (continue)  │     │              │     │              │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │ 17. Write result   │                    │
       │───────────────────>│                    │
       │                    │ 18. INSERT         │
       │                    │───────────────────>│
       │                    │                    │
       │                    │ 19. OK             │
       │                    │<───────────────────│
       │                    │                    │

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Metric       │     │  AI Server   │     │  PostgreSQL  │
│ Collector    │     │  Agent:9100  │     │              │
│ (background) │     │              │     │              │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │ 20. GET /metrics   │                    │
       │ (every 1 sec)      │                    │
       │───────────────────>│                    │
       │                    │                    │
       │ 21. GPU/CPU data   │                    │
       │<───────────────────│                    │
       │                    │                    │
       │ 22. Write snapshot                      │
       │────────────────────────────────────────>│
       │                    │                    │

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Orchestrator │     │  Aggregator  │     │  PostgreSQL  │
│ (finalize)   │     │              │     │              │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │ 23. Compare S1/S2  │                    │
       │───────────────────>│                    │
       │                    │ 24. Read results   │
       │                    │───────────────────>│
       │                    │<───────────────────│
       │                    │                    │
       │                    │ 25. Calculate Δ%   │
       │                    │ Determine winners  │
       │                    │                    │
       │ 26. Comparisons    │                    │
       │<───────────────────│                    │
       │                    │                    │
       │ 27. Write comparisons                   │
       │────────────────────────────────────────>│
       │                    │                    │
       │ 28. Update run     │                    │
       │ status=completed   │                    │
       │────────────────────────────────────────>│
       │                    │                    │

┌─────────┐     ┌───────────┐     ┌──────────────┐     ┌──────────────┐
│  User   │     │  Web UI   │     │   FastAPI     │     │  PostgreSQL  │
│ Browser │     │ Chart.js  │     │  (REST API)   │     │              │
└────┬────┘     └─────┬─────┘     └──────┬───────┘     └──────┬───────┘
     │                │                   │                    │
     │ 29. GET /api/benchmark/progress    │                    │
     │ (polling every 2s)                 │                    │
     │───────────────────────────────────>│                    │
     │                                    │                    │
     │ 30. {status: completed}            │                    │
     │<───────────────────────────────────│                    │
     │                │                   │                    │
     │ 31. Redirect to /history/{run_id}  │                    │
     │───────────────>│                   │                    │
     │                │ 32. Fetch all data│                    │
     │                │──────────────────>│                    │
     │                │                   │ 33. Query          │
     │                │                   │───────────────────>│
     │                │                   │<───────────────────│
     │                │                   │                    │
     │                │ 34. Render page   │                    │
     │                │ with Chart.js     │                    │
     │                │<──────────────────│                    │
     │                │                   │                    │
     │ 35. Full results page              │                    │
     │ with charts, tables, summary       │                    │
     │<───────────────│                   │                    │
     │                │                   │                    │
     │ 36. Export CSV/PDF                 │                    │
     │───────────────────────────────────>│                    │
     │                                    │ 37. Generate       │
     │                                    │───────────────────>│
     │                                    │<───────────────────│
     │ 38. File download                  │                    │
     │<───────────────────────────────────│                    │
     │                │                   │                    │
```

---

# 10. PHỤ LỤC

## 10.1 Glossary (Thuật ngữ)

| Thuật ngữ | Giải thích |
|-----------|-----------|
| **LLM** | Large Language Model - Mô hình ngôn ngữ lớn |
| **Inference** | Quá trình chạy model để sinh output |
| **Token** | Đơn vị nhỏ nhất của text (~ 4 ký tự tiếng Anh) |
| **TTFT** | Time To First Token - Thời gian từ gửi request đến nhận token đầu tiên |
| **TPOT** | Time Per Output Token - Thời gian trung bình để sinh 1 token |
| **TPS** | Tokens Per Second - Số token sinh ra mỗi giây |
| **ITL** | Inter-Token Latency - Khoảng cách thời gian giữa 2 token liên tiếp |
| **RPS** | Requests Per Second - Số request xử lý hoàn tất mỗi giây |
| **P50/P95/P99** | Percentile - Phân vị (P99 = 99% request nhanh hơn giá trị này) |
| **Goodput** | Throughput chỉ tính các request thành công |
| **Concurrency** | Số request đồng thời gửi cùng lúc |
| **Streaming** | Nhận response theo từng token thay vì đợi toàn bộ |
| **SSE** | Server-Sent Events - Giao thức streaming server → client |
| **VRAM** | Video RAM - Bộ nhớ GPU |
| **Ollama** | Phần mềm chạy LLM trên local (hỗ trợ GGUF format) |
| **GGUF** | Format lưu trữ model được lượng tử hóa (quantized) |
| **Quantization** | Kỹ thuật nén model (Q4_0 = 4-bit precision) |
| **aiDaptive+** | Phần mềm tối ưu hóa AI inference của aiDaptive Inc. |
| **Warmup** | Gửi request thử trước benchmark chính để "hâm nóng" GPU/model |
| **Cooldown** | Thời gian nghỉ giữa các test để tránh ảnh hưởng nhiệt |
| **Adapter** | Module wrapper cho mỗi benchmark tool |
| **Orchestrator** | Module điều phối toàn bộ flow benchmark |
| **Data Sink** | Abstraction layer ghi data vào database |
| **Agent** | Lightweight service chạy trên AI server, expose hardware metrics |
| **Delta (Δ)** | Sự chênh lệch giữa 2 giá trị (thường tính theo %) |
| **pp** | Percentage Points - Điểm phần trăm (khác với %) |

## 10.2 Configuration Reference

### `config/scenarios.yaml`

```yaml
# ═══════════════════════════════════════════
#  Prompt Scenarios Configuration
# ═══════════════════════════════════════════

scenarios:
  - id: simple_chat
    name: Simple Chat
    category: conversation
    prompt: "Explain quantum computing in simple terms that a high school student could understand."
    expected_tokens: 200
    description: "Basic conversational prompt, moderate output length"
  
  - id: code_generation
    name: Code Generation
    category: code
    prompt: "Write a Python function called merge_sorted_lists that takes two sorted lists and returns a single merged sorted list. Include error handling, type hints, and docstring."
    expected_tokens: 300
    description: "Code generation with specific requirements"
  
  - id: long_output
    name: Long Output
    category: generation
    prompt: "Write a detailed 1000-word essay about the impact of climate change on ocean ecosystems. Include specific examples of affected species, coral reef degradation, and potential solutions."
    expected_tokens: 500
    description: "Long-form text generation, tests sustained throughput"
  
  - id: reasoning
    name: Reasoning / Math
    category: logic
    prompt: "A train leaves Station A heading east at 60 mph. At the same time, another train leaves Station B heading west at 80 mph. The stations are 280 miles apart. When will the trains meet? What distance will each train have traveled? Show all your work step by step."
    expected_tokens: 250
    description: "Multi-step reasoning and calculation"
  
  - id: translation
    name: Translation
    category: translation
    prompt: "Translate the following paragraph to French, maintaining the original tone and style:\n\n'The rapid development of artificial intelligence has transformed how businesses operate across every industry. From healthcare diagnostics to financial modeling, AI systems now assist human experts in making better, faster decisions. However, this transformation also raises important questions about privacy, bias, and the future of work.'"
    expected_tokens: 150
    description: "Language translation task"
  
  - id: summarization
    name: Summarization
    category: summary
    prompt: "Summarize the following article in exactly 3 bullet points, each no longer than 2 sentences:\n\nArtificial intelligence is rapidly transforming the healthcare industry. Machine learning algorithms can now detect certain types of cancer from medical images with accuracy rates exceeding those of human radiologists. Natural language processing enables the extraction of valuable insights from millions of medical records, helping researchers identify patterns and potential treatments. AI-powered drug discovery platforms have reduced the time to identify promising drug candidates from years to months. Robotic surgery systems, guided by AI, enable procedures with greater precision and smaller incisions. However, challenges remain in areas such as data privacy, algorithmic bias, and regulatory approval. The integration of AI into clinical workflows requires careful validation and ongoing monitoring to ensure patient safety."
    expected_tokens: 100
    description: "Summarization with specific format constraints"
```

### `config/defaults.yaml`

```yaml
# ═══════════════════════════════════════════
#  Default Configuration Values
# ═══════════════════════════════════════════

benchmark:
  default_model: "llama3.2:1b"
  warmup_requests: 3
  repeat_count: 5
  request_timeout_seconds: 120
  cooldown_between_tests_seconds: 10
  max_tokens: 512
  temperature: 0.7
  
  concurrency_levels:
    single_request: [1]
    concurrent_load: [5, 10, 20]
    all: [1, 5, 10, 20]

tools:
  ollama_native:
    enabled: true
    supports_streaming: true
    supports_concurrency: false
  oha:
    enabled: true
    supports_streaming: false
    supports_concurrency: true
    binary_path: "oha"
  k6:
    enabled: true
    supports_streaming: false
    supports_concurrency: true
    binary_path: "k6"
  litellm:
    enabled: true
    supports_streaming: true
    supports_concurrency: false
  locust:
    enabled: true
    supports_streaming: false
    supports_concurrency: true
  llmperf:
    enabled: true
    supports_streaming: true
    supports_concurrency: true
  vllm_bench:
    enabled: true
    supports_streaming: true
    supports_concurrency: true
    script_path: "scripts/benchmark_serving.py"

metrics:
  poll_interval_seconds: 1.0
  
data_retention:
  hardware_snapshots_days: 90
  benchmark_results_days: -1  # unlimited
  
ui:
  theme: "dark"
  auto_refresh_interval_seconds: 5
  chart_style: "default"
  items_per_page: 20
```

## 10.3 Database Migration Scripts

### `database/migrations/001_initial.sql`

```sql
-- ═══════════════════════════════════════════
--  Migration 001: Initial Schema
--  aiDaptive Benchmark Suite v2.0
-- ═══════════════════════════════════════════

BEGIN;

-- ─── benchmark_runs ───
CREATE TABLE IF NOT EXISTS benchmark_runs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    duration_seconds FLOAT,
    suite VARCHAR(50),
    environment VARCHAR(50),
    model VARCHAR(100),
    config_snapshot JSONB,
    notes TEXT,
    tags TEXT[],
    total_tests INTEGER DEFAULT 0,
    completed_tests INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── benchmark_results ───
CREATE TABLE IF NOT EXISTS benchmark_results (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) REFERENCES benchmark_runs(run_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    server VARCHAR(50) NOT NULL,
    tool VARCHAR(50) NOT NULL,
    scenario VARCHAR(100),
    model VARCHAR(100),
    concurrency INTEGER,
    ttft_ms FLOAT,
    tpot_ms FLOAT,
    itl_ms FLOAT,
    latency_p50_ms FLOAT,
    latency_p95_ms FLOAT,
    latency_p99_ms FLOAT,
    tps FLOAT,
    rps FLOAT,
    goodput FLOAT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    total_requests INTEGER,
    successful_requests INTEGER,
    failed_requests INTEGER,
    error_rate FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── hardware_snapshots ───
CREATE TABLE IF NOT EXISTS hardware_snapshots (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50),
    server VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    gpu_util_pct FLOAT,
    gpu_memory_util_pct FLOAT,
    vram_used_gb FLOAT,
    vram_total_gb FLOAT,
    gpu_power_watts FLOAT,
    gpu_temperature_c FLOAT,
    cpu_pct FLOAT,
    ram_used_gb FLOAT,
    ram_total_gb FLOAT,
    load_avg_1m FLOAT,
    load_avg_5m FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── server_comparisons ───
CREATE TABLE IF NOT EXISTS server_comparisons (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) REFERENCES benchmark_runs(run_id) ON DELETE CASCADE,
    tool VARCHAR(50),
    scenario VARCHAR(100),
    concurrency INTEGER DEFAULT 1,
    s1_ttft_ms FLOAT,
    s1_tpot_ms FLOAT,
    s1_tps FLOAT,
    s1_rps FLOAT,
    s1_p99_ms FLOAT,
    s1_error_rate FLOAT,
    s2_ttft_ms FLOAT,
    s2_tpot_ms FLOAT,
    s2_tps FLOAT,
    s2_rps FLOAT,
    s2_p99_ms FLOAT,
    s2_error_rate FLOAT,
    delta_ttft_pct FLOAT,
    delta_tps_pct FLOAT,
    delta_p99_pct FLOAT,
    overall_winner VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── server_profiles ───
CREATE TABLE IF NOT EXISTS server_profiles (
    id SERIAL PRIMARY KEY,
    server_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100),
    description TEXT,
    ollama_url VARCHAR(255),
    agent_url VARCHAR(255),
    aidaptive_enabled BOOLEAN DEFAULT FALSE,
    gpu_name VARCHAR(100),
    gpu_vram_gb FLOAT,
    gpu_driver VARCHAR(50),
    cpu_name VARCHAR(100),
    cpu_cores INTEGER,
    ram_total_gb FLOAT,
    hostname VARCHAR(100),
    os_version VARCHAR(100),
    last_seen_at TIMESTAMP,
    is_online BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Seed server profiles ───
INSERT INTO server_profiles (server_id, name, description, ollama_url, agent_url, aidaptive_enabled)
VALUES 
  ('server1', 'aiDaptive+ Disabled', 'Baseline server without aiDaptive+ optimization',
   'http://35.186.159.250:11434', 'http://35.186.159.250:9100', false),
  ('server2', 'aiDaptive+ Enabled', 'Server with aiDaptive+ optimization enabled',
   'http://34.142.222.133:11434', 'http://34.142.222.133:9100', true)
ON CONFLICT (server_id) DO NOTHING;

COMMIT;
```

### `database/migrations/002_add_indexes.sql`

```sql
-- ═══════════════════════════════════════════
--  Migration 002: Add Performance Indexes
-- ═══════════════════════════════════════════

BEGIN;

-- benchmark_runs indexes
CREATE INDEX IF NOT EXISTS idx_runs_status ON benchmark_runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created ON benchmark_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_suite ON benchmark_runs(suite);
CREATE INDEX IF NOT EXISTS idx_runs_tags ON benchmark_runs USING GIN(tags);

-- benchmark_results indexes
CREATE INDEX IF NOT EXISTS idx_results_run_id ON benchmark_results(run_id);
CREATE INDEX IF NOT EXISTS idx_results_server ON benchmark_results(server);
CREATE INDEX IF NOT EXISTS idx_results_tool ON benchmark_results(tool);
CREATE INDEX IF NOT EXISTS idx_results_scenario ON benchmark_results(scenario);
CREATE INDEX IF NOT EXISTS idx_results_timestamp ON benchmark_results(timestamp);
CREATE INDEX IF NOT EXISTS idx_results_composite 
    ON benchmark_results(run_id, server, tool, scenario);

-- hardware_snapshots indexes
CREATE INDEX IF NOT EXISTS idx_snapshots_run_id ON hardware_snapshots(run_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_server ON hardware_snapshots(server);
CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON hardware_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_snapshots_composite 
    ON hardware_snapshots(run_id, server, timestamp);

-- server_comparisons indexes
CREATE INDEX IF NOT EXISTS idx_comparisons_run_id ON server_comparisons(run_id);
CREATE INDEX IF NOT EXISTS idx_comparisons_tool ON server_comparisons(tool);
CREATE INDEX IF NOT EXISTS idx_comparisons_winner ON server_comparisons(overall_winner);

COMMIT;
```

## 10.4 Version History

| Version | Date | Changes |
|---------|------|---------|
| **v1.0** | 2024-03-01 | Initial release. Basic Ollama benchmark with CLI only. |
| **v1.5** | 2024-03-15 | Added Web UI (Flask), 3 benchmark tools, PostgreSQL. |
| **v2.0** | 2024-04-15 | **Current version.** Complete rewrite: FastAPI, 7 tools, Chart.js, comparison engine, PDF export, Docker support, automated daily benchmark. |

## 10.5 License & Contact

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  aiDaptive Benchmark Suite v2.0                                 │
│  © 2024 aiDaptive Inc. All rights reserved.                     │
│                                                                  │
│  Internal Use Only - Proprietary and Confidential               │
│                                                                  │
│  Contact:                                                        │
│  • Engineering: eng@aidaptive.com                               │
│  • Support: support@aidaptive.com                               │
│  • Documentation: docs@aidaptive.com                            │
│                                                                  │
│  Repository: https://github.com/aidaptive/benchmark-suite       │
│  Wiki: https://wiki.aidaptive.com/benchmark                     │
│  Slack: #benchmark-suite                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

**═══ END OF DOCUMENT ═══**
