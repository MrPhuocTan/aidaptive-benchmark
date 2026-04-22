"""Data models for benchmark results"""

from dataclasses import dataclass, field
from src.time_utils import get_local_time
from datetime import datetime
from enum import Enum
from typing import Optional


class ServerID(str, Enum):
    SERVER1 = "server1"
    SERVER2 = "server2"


class ToolName(str, Enum):
    OLLAMA_NATIVE = "ollama_native"
    LLMPERF = "llmperf"
    LITELLM = "litellm"
    LOCUST = "locust"
    OHA = "oha"
    VLLM_BENCH = "vllm_bench"


class TestScenario(str, Enum):
    SIMPLE_CHAT = "simple_chat"
    CODE_GENERATION = "code_generation"
    LONG_CONTEXT = "long_context"
    LONG_OUTPUT = "long_output"
    STRUCTURED_OUTPUT = "structured_output"
    MULTI_TURN = "multi_turn"


@dataclass
class BenchmarkResult:
    run_id: str = ""
    timestamp: datetime = field(default_factory=get_local_time)
    server: str = ""
    tool: str = ""
    environment: str = ""
    scenario: str = ""
    model: str = ""
    concurrency: int = 1

    ttft_ms: Optional[float] = None
    tpot_ms: Optional[float] = None
    itl_ms: Optional[float] = None
    tps: Optional[float] = None

    rps: Optional[float] = None
    latency_p50_ms: Optional[float] = None
    latency_p95_ms: Optional[float] = None
    latency_p99_ms: Optional[float] = None

    total_tokens: Optional[int] = None
    total_requests: Optional[int] = None
    successful_requests: Optional[int] = None
    failed_requests: Optional[int] = None
    error_rate: Optional[float] = None

    goodput: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

    def to_dict(self) -> dict:
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result


@dataclass
class HardwareMetrics:
    timestamp: datetime = field(default_factory=get_local_time)
    server: str = ""

    gpu_util_pct: Optional[float] = None
    vram_used_gb: Optional[float] = None
    vram_total_gb: Optional[float] = None
    gpu_power_watts: Optional[float] = None
    gpu_temperature_c: Optional[float] = None
    gpu_memory_bandwidth_gbps: Optional[float] = None
    gpu_name: str = ""

    cpu_pct: Optional[float] = None
    ram_used_gb: Optional[float] = None
    ram_total_gb: Optional[float] = None
    disk_read_mbps: Optional[float] = None
    disk_write_mbps: Optional[float] = None
    network_rx_mbps: Optional[float] = None
    network_tx_mbps: Optional[float] = None


@dataclass
class ServerStatus:
    server_id: str = ""
    server_name: str = ""
    ollama_online: bool = False
    agent_online: bool = False
    models_loaded: list = field(default_factory=list)
    gpu_name: str = ""
    vram_total_gb: float = 0
    ollama_version: str = ""