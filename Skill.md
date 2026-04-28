# Skill Guide — aiDaptive Benchmark Suite

> Tài liệu kỹ năng dành cho nhà phát triển mới tham gia dự án.  
> Mục đích: Hiểu nhanh cách hoạt động, quy ước code, và các kỹ thuật cốt lõi để có thể đóng góp ngay.

---

## 1. Tổng quan Kiến trúc

Hệ thống gồm **3 thành phần chính** chạy trên **2 server riêng biệt**:

```
┌──────────────────────────────────────────────────────────────┐
│  benchmarktool (GCP asia-southeast1-c)                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  FastAPI     │  │ Orchestrator │  │ PostgreSQL (local) │  │
│  │  Web UI      │──│ + Adapters   │──│ aidaptive_benchmark│  │
│  │  Port: 8443  │  │              │  │ Port: 5432         │  │
│  └─────────────┘  └──────┬───────┘  └────────────────────┘  │
│                          │                                    │
└──────────────────────────┼────────────────────────────────────┘
                           │ HTTP
         ┌─────────────────┼──────────────────┐
         ▼                 ▼                  ▼
   ┌──────────┐      ┌──────────┐       ┌──────────┐
   │ AI Server│      │ AI Server│       │ AI Server│
   │ (vm01)   │      │ (vm02)   │       │ (vmN)    │
   │ Agent    │      │ Agent    │       │ Agent    │
   │ :9100    │      │ :9100    │       │ :9100    │
   │ Ollama   │      │ Ollama   │       │ Ollama   │
   │ :11434   │      │ :11434   │       │ :11434   │
   └──────────┘      └──────────┘       └──────────┘
```

### Các cổng (Port) quan trọng

| Port | Service | Mô tả |
|------|---------|-------|
| `8443` | FastAPI (benchmarktool) | Web UI + REST API |
| `5432` | PostgreSQL (benchmarktool) | Database chính |
| `9100` | aidaptive-agent (mỗi AI server) | Agent thu thập hardware metrics |
| `11434` | Ollama (mỗi AI server) | LLM inference engine |

---

## 2. Cấu trúc thư mục

```
aidaptive-benchmark/
├── benchmark.yaml           # Cấu hình tĩnh (models, tools, suites)
├── src/
│   ├── app.py               # FastAPI routes + middleware (1221 lines)
│   ├── orchestrator.py       # Luồng chạy benchmark end-to-end (881 lines)
│   ├── config.py             # Dataclass config loader từ YAML
│   ├── models.py             # Dataclass: BenchmarkResult, HardwareMetrics, ServerStatus
│   ├── i18n.py               # Đa ngôn ngữ EN/VI/ZH (772 lines)
│   ├── background.py         # Background task: đồng bộ server profiles
│   ├── time_utils.py         # get_local_time() helper
│   ├── adapters/             # 6 tool adapters (mỗi tool 1 file)
│   │   ├── base.py           # BaseToolAdapter abstract class
│   │   ├── ollama_adapter.py
│   │   ├── oha_adapter.py
│   │   ├── litellm_adapter.py
│   │   ├── locust_adapter.py
│   │   ├── llmperf_adapter.py
│   │   └── vllm_bench_adapter.py
│   ├── collectors/           # Hardware monitoring
│   │   ├── agent_client.py   # HTTP client → Agent trên AI server
│   │   ├── metric_collector.py # Background thread polling metrics
│   │   └── server_discovery.py # Tự động phát hiện server mới
│   ├── data/
│   │   ├── data_sink.py      # Writes to PostgreSQL
│   │   └── normalizer.py     # Chuẩn hoá metrics trước khi lưu
│   ├── database/
│   │   ├── engine.py         # SQLAlchemy engine + session factory
│   │   ├── tables.py         # ORM models (6 tables)
│   │   ├── repository.py     # CRUD + aggregation queries
│   │   └── seed.py           # Seed data + profile sync helper
│   ├── routers/
│   │   ├── reports.py        # Report pages + download
│   │   └── prompts.py        # Prompt set CRUD + Excel upload
│   └── reports/              # PDF generation
├── templates/                # Jinja2 HTML templates (11 files)
├── static/
│   ├── css/theme.css         # Styling
│   └── js/app.js             # Frontend logic (polling, charts, forms)
├── command/                  # Shell scripts (start/stop server)
└── debug_thing/              # Debug/test files (git-ignored)
```

---

## 3. Quy ước Code (Conventions)

### 3.1 Pattern chính

| Pattern | File | Mô tả |
|---------|------|-------|
| **Adapter** | `src/adapters/*.py` | Mỗi tool benchmark kế thừa `BaseToolAdapter`, implement `run(prompts)` |
| **Repository** | `src/database/repository.py` | Sync (`Repository`) + Async (`AsyncRepository`) cho mọi DB operations |
| **Orchestrator** | `src/orchestrator.py` | Điều phối toàn bộ luồng benchmark: Preflight → Warmup → Execute → Compare → Finalize |
| **DataSink** | `src/data/data_sink.py` | Điểm ghi dữ liệu duy nhất: normalize → validate → write to PostgreSQL |

### 3.2 Quy tắc Import

```python
# ✅ Đúng: Import từ app.py cho các singleton
from src.app import database, config

# ❌ Sai: Tạo Database instance riêng (gây duplicate connection pool)
database = Database(config.postgres)  # KHÔNG LÀM THẾ NÀY
```

### 3.3 Quy tắc i18n

```python
# Trong route handler: dùng _t_for_request()
return JSONResponse({"error": _t_for_request(request, "api.server_not_found")})

# Trong template: dùng {{ t('key') }}
<h1>{{ t('dashboard.title') }}</h1>

# ❌ Sai: Hardcode tiếng Anh
return JSONResponse({"error": "Server not found"})
```

### 3.4 Quy tắc thời gian

```python
# Luôn dùng get_local_time() thay vì datetime.now() hay datetime.utcnow()
from src.time_utils import get_local_time
timestamp = get_local_time()
```

---

## 4. Luồng dữ liệu chính (Data Flows)

### 4.1 Thu thập Hardware Metrics

```
Agent (vm01:9100)                    Backend (benchmarktool)
─────────────────                    ────────────────────────
GET /metrics/gpu                     agent_client.get_gpu_metrics()
→ {"gpus": [{                        → Normalize: extract gpus[0],
    "gpu_util_pct": 45,                  memory_used_mb ÷ 1024 → vram_used_gb,
    "memory_used_mb": 2048,              power_w → gpu_power_watts
    "power_w": 120, ...}]}

GET /metrics/system                  agent_client.get_all_metrics()
→ {"cpu_usage_pct": 3.1,             → Map: cpu_usage_pct → cpu_pct,
    "memory_used_mb": 328,                memory_used_mb ÷ 1024 → ram_used_gb
    "memory_total_mb": 7939}

GET /info                            agent_client.get_server_specs()
→ {"cpu_model": "AMD EPYC",          → Parse: ram_gb (string) → float,
    "cpu_cores": "2",                     cpu_cores (string) → int
    "ram_gb": "7"}
```

> **⚠️ Gotcha quan trọng:** Agent trả key khác hoàn toàn so với Backend models. 
> `agent_client.py` là lớp normalize trung gian. Nếu thêm field mới, phải update mapping tại đây.

### 4.2 Benchmark Execution Flow

```
1. POST /api/benchmark/start
   → app.py tạo asyncio.Task(orchestrator.run_async(...))

2. orchestrator.run_async():
   a. Preflight: Verify agent health + ollama health + model availability
   b. Warmup: Send 3 dummy requests to preload model into VRAM
   c. Start MetricCollector (background thread, polls /metrics every 1s)
   d. Loop: For each (tool × server × scenario × concurrency):
      - adapter.run(prompts) → List[BenchmarkResult]
      - data_sink.write_benchmark_result(result, run_id)
   e. Stop MetricCollector
   f. Generate comparisons (Δ% calculations)
   g. Mark run as completed

3. Frontend polls GET /api/benchmark/progress every 2s
```

### 4.3 Report Generation Flow

```
1. GET /reports/{run_id}
   → repo.get_detailed_report_stats(run_id)     # Bảng số liệu
   → repo.get_dashboard_chart_data(run_id)       # Data cho 4 metric charts
   → repo.get_timeline_chart_data(run_id)        # Data cho hardware timeline
   
2. Template render: report_details.html
   - Nhúng JSON vào <script type="application/json">
   - Chart.js đọc và vẽ client-side
```

---

## 5. Bảng mapping JSON: Agent ↔ Backend ↔ Database

Đây là bảng đối chiếu đầy đủ giữa 3 tầng. **Bất kỳ thay đổi nào ở Agent đều phải cập nhật `agent_client.py`.**

### `/metrics/gpu` (GPU Metrics)

| Agent JSON Key | `agent_client.py` Normalized | `HardwareMetrics` Field | DB Column |
|---|---|---|---|
| `gpus[0].gpu_util_pct` | `gpu_util_pct` | `gpu_util_pct` | `gpu_util_pct` |
| `gpus[0].memory_used_mb` | `vram_used_gb` (÷1024) | `vram_used_gb` | `vram_used_gb` |
| `gpus[0].memory_total_mb` | `vram_total_gb` (÷1024) | `vram_total_gb` | `vram_total_gb` |
| `gpus[0].power_w` | `gpu_power_watts` | `gpu_power_watts` | `gpu_power_watts` |
| `gpus[0].temperature_c` | `gpu_temperature_c` | `gpu_temperature_c` | `gpu_temperature_c` |
| `gpus[0].name` | `gpu_name` | `gpu_name` | `gpu_name` |

### `/metrics/system` (System Metrics)

| Agent JSON Key | `agent_client.py` Mapping | `HardwareMetrics` Field | DB Column |
|---|---|---|---|
| `cpu_usage_pct` | `cpu_pct` | `cpu_pct` | `cpu_pct` |
| `memory_used_mb` | `ram_used_gb` (÷1024) | `ram_used_gb` | `ram_used_gb` |
| `memory_total_mb` | `ram_total_gb` (÷1024) | `ram_total_gb` | `ram_total_gb` |
| *(not available)* | `None` | `disk_read_mbps` | `disk_read_mbps` |
| *(not available)* | `None` | `network_rx_mbps` | `network_rx_mbps` |

### `/info` (Server Info — used by `background.py`)

| Agent JSON Key | Kiểu dữ liệu | Mapping trong `background.py` | DB Column |
|---|---|---|---|
| `cpu_model` | `string` | Truyền thẳng | `cpu_model` |
| `cpu_cores` | `string` ("2") | `int()` parse | `cpu_cores` |
| `ram_gb` | `string` ("7") | `float()` parse | `ram_total_gb` |
| `gpu_name` | `string` | Từ `get_server_status()` | `gpu_name` |

---

## 6. Database Schema

### 6 Tables chính

| Table | Mô tả | Quan hệ |
|-------|-------|---------|
| `benchmark_runs` | Metadata của mỗi lần chạy benchmark | Parent |
| `benchmark_results` | Kết quả chi tiết từng request | → `benchmark_runs.run_id` |
| `hardware_snapshots` | Hardware metrics theo thời gian | → `benchmark_runs.run_id` |
| `server_comparisons` | So sánh giữa các server | → `benchmark_runs.run_id` |
| `server_profiles` | Thông tin phần cứng của server (CRUD) | Standalone |
| `prompt_sets` + `prompt_entries` | Dataset câu hỏi upload từ Excel | Parent-Child |

### Cascade Delete
Xoá `BenchmarkRun` sẽ tự động xoá tất cả `results`, `hardware_snapshots`, `comparisons` liên quan (SQLAlchemy cascade).

---

## 7. Adapter Pattern — Thêm Tool mới

Để thêm một benchmark tool mới (ví dụ: `k6`):

```python
# 1. Tạo file: src/adapters/k6_adapter.py
from src.adapters.base import BaseToolAdapter
from src.models import BenchmarkResult

class K6Adapter(BaseToolAdapter):
    tool_name = "k6"

    def __init__(self, ollama_url: str, model: str, concurrency: int = 10, **kwargs):
        self.ollama_url = ollama_url
        self.model = model
        self.concurrency = concurrency

    async def run(self, prompts: list) -> list[BenchmarkResult]:
        results = []
        # ... logic chạy benchmark ...
        # Mỗi result phải có: ttft_ms, tps, tpot_ms, error_rate
        return results

    def is_available(self) -> bool:
        return self.check_binary("k6")

# 2. Đăng ký trong src/adapters/__init__.py
# 3. Thêm mapping trong orchestrator.py → tool_mapping dict
# 4. Thêm config trong benchmark.yaml → tools section
```

---

## 8. i18n — Thêm ngôn ngữ hoặc chuỗi mới

File `src/i18n.py` chứa dict `TRANSLATIONS` với 3 ngôn ngữ:
- `en` (English) — Mặc định
- `vi` (Tiếng Việt)
- `zh` (简体中文)

### Thêm chuỗi mới
Phải thêm vào **CẢ 3 section** trong `TRANSLATIONS`:

```python
TRANSLATIONS = {
    "en": {
        "my_new.key": "English text",
        # ...
    },
    "vi": {
        "my_new.key": "Tiếng Việt text",
        # ...
    },
    "zh": {
        "my_new.key": "中文 text",
        # ...
    },
}
```

### Naming convention cho key
- `nav.*` — Navigation items
- `dashboard.*` — Dashboard page
- `servers.*` — Server management page
- `benchmark.*` — Benchmark page
- `api.*` — API error/success messages
- `js.*` — Client-side JavaScript messages
- `report_details.*` — Report page

---

## 9. Infrastructure — SSH Access

```bash
# SSH vào Benchmark Server (Controller)
gcloud compute ssh --zone "asia-southeast1-c" "benchmarktool" \
  --project "project-4b9f2d52-8daa-40bf-ba0"

# SSH vào AI Server (vm01)
gcloud compute ssh --zone "asia-southeast1-b" "vm01" \
  --project "project-4b9f2d52-8daa-40bf-ba0"

# Restart benchmark app trên server
cd aidaptive-benchmark && ./command/start_server.sh

# Check agent status trên AI server
sudo systemctl status aidaptive-agent

# Curl test agent API
curl -s http://localhost:9100/health
curl -s http://localhost:9100/metrics/system
curl -s http://localhost:9100/metrics/gpu
curl -s http://localhost:9100/info
```

---

## 10. Gotchas & Known Issues

| Issue | Mô tả | Giải pháp |
|-------|-------|-----------|
| **VM Freeze** | AI server có thể bị đóng băng (SSH timeout). | `gcloud compute instances reset vm01 --zone asia-southeast1-b` |
| **No GPU** | vm01 hiện là `e2-standard-2` (không có GPU). GPU metrics luôn trả `{"gpus": []}`. | Deploy agent lên VM có GPU thật. |
| **Agent key mismatch** | Agent trả JSON key khác Backend. | Luôn normalize trong `agent_client.py`, KHÔNG sửa Agent. |
| **Duplicate DB pool** | Nếu tạo `Database()` mới trong router → leak connection. | Import `database` singleton từ `src.app`. |
| **Chart blank** | Chart.js không vẽ khi chỉ có 1 data point hoặc toàn null. | Frontend đã có fix: `pointRadius=4`, filter null, axis min/max clamp. |
| **NoCacheMiddleware** | Mọi response đều `no-cache`. | Cần thiết cho dev, nhưng cân nhắc bỏ cho production (static assets). |

---

## 11. Hướng phát triển đề xuất

1. **Agent nâng cấp:** Thêm `disk_read_mbps`, `disk_write_mbps`, `network_rx_mbps`, `network_tx_mbps` vào `/metrics/system` trên agent.py.
2. **GPU Server thật:** Deploy agent lên VM có GPU (ví dụ: `n1-standard-4` + NVIDIA T4) để test GPU charts.
3. **Automated tests:** Thêm `pytest` với mock HTTP responses cho `agent_client.py` để ngăn regression mapping.
4. **WebSocket:** Thay polling (`setInterval 2s`) bằng WebSocket cho real-time progress.
5. **Report PDF Server-side:** Tích hợp Playwright trên server để sinh PDF offline thay vì client-side download.
6. **Multi-model benchmark:** Hỗ trợ benchmark nhiều model trong cùng 1 run (hiện tại chỉ chọn 1 model).
