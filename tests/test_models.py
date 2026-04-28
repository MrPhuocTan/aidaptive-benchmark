"""
Test Suite 1: Models & Data Classes
Tests for BenchmarkResult, HardwareMetrics, ServerStatus dataclasses.
"""

import pytest
from datetime import datetime

from src.models import BenchmarkResult, HardwareMetrics, ServerStatus


class TestBenchmarkResult:
    """Test BenchmarkResult dataclass"""

    def test_default_initialization(self):
        """TC-M01: Default values should be empty/None"""
        result = BenchmarkResult()
        assert result.run_id == ""
        assert result.server == ""
        assert result.tool == ""
        assert result.concurrency == 1
        assert result.ttft_ms is None
        assert result.tps is None
        assert result.error_rate is None

    def test_full_initialization(self):
        """TC-M02: Fully populated result"""
        result = BenchmarkResult(
            run_id="run_001",
            server="server1",
            tool="ollama_native",
            environment="local",
            scenario="simple_chat",
            model="llama3:8b",
            concurrency=10,
            ttft_ms=120.5,
            tpot_ms=15.3,
            itl_ms=14.8,
            tps=65.2,
            rps=8.4,
            latency_p50_ms=100.0,
            latency_p95_ms=200.0,
            latency_p99_ms=350.0,
            total_tokens=5000,
            total_requests=100,
            successful_requests=98,
            failed_requests=2,
            error_rate=0.02,
        )
        assert result.run_id == "run_001"
        assert result.tps == 65.2
        assert result.error_rate == 0.02
        assert result.concurrency == 10

    def test_to_dict_excludes_none(self):
        """TC-M03: to_dict() should exclude None values"""
        result = BenchmarkResult(
            run_id="run_001",
            server="server1",
            tool="oha",
            tps=50.0,
        )
        d = result.to_dict()
        assert "tps" in d
        assert d["tps"] == 50.0
        assert "ttft_ms" not in d
        assert "error_rate" not in d

    def test_to_dict_serializes_timestamp(self):
        """TC-M04: to_dict() should ISO-serialize datetime"""
        result = BenchmarkResult(run_id="run_001", server="s1", tool="oha")
        d = result.to_dict()
        assert "timestamp" in d
        assert isinstance(d["timestamp"], str)
        # Should be parseable
        datetime.fromisoformat(d["timestamp"])


class TestHardwareMetrics:
    """Test HardwareMetrics dataclass"""

    def test_default_initialization(self):
        """TC-M05: Default hardware metrics"""
        m = HardwareMetrics()
        assert m.server == ""
        assert m.gpu_util_pct is None
        assert m.vram_used_gb is None
        assert m.cpu_pct is None
        assert m.ram_used_gb is None

    def test_gpu_fields(self):
        """TC-M06: GPU metric assignment"""
        m = HardwareMetrics(
            server="server1",
            gpu_util_pct=85.5,
            vram_used_gb=6.2,
            vram_total_gb=8.0,
            gpu_power_watts=180.0,
            gpu_temperature_c=72.0,
            gpu_name="NVIDIA RTX 4090",
        )
        assert m.gpu_util_pct == 85.5
        assert m.vram_used_gb == 6.2
        assert m.gpu_name == "NVIDIA RTX 4090"

    def test_system_fields(self):
        """TC-M07: CPU/RAM metric assignment"""
        m = HardwareMetrics(
            server="server1",
            cpu_pct=45.2,
            ram_used_gb=12.5,
            ram_total_gb=32.0,
        )
        assert m.cpu_pct == 45.2
        assert m.ram_used_gb == 12.5
        assert m.ram_total_gb == 32.0


class TestServerStatus:
    """Test ServerStatus dataclass"""

    def test_default_offline(self):
        """TC-M08: Default status should be offline"""
        status = ServerStatus()
        assert status.ollama_online is False
        assert status.agent_online is False
        assert status.models_loaded == []
        assert status.gpu_name == ""

    def test_fully_online(self):
        """TC-M09: Fully online server"""
        status = ServerStatus(
            server_id="server1",
            server_name="AI Server 1",
            ollama_online=True,
            agent_online=True,
            models_loaded=["llama3:8b", "llama3.2:latest"],
            gpu_name="NVIDIA RTX 4090",
            vram_total_gb=24.0,
            ollama_version="0.1.34",
        )
        assert status.ollama_online is True
        assert len(status.models_loaded) == 2
        assert status.vram_total_gb == 24.0
