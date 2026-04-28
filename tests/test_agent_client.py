"""
Test Suite 2: Agent Client — JSON Key Mapping
Tests that agent_client.py correctly normalizes JSON from the remote agent.
Uses mock HTTP responses to simulate the agent on vm01.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.collectors.agent_client import AgentClient
from src.models import HardwareMetrics


# ---------- Helpers ----------

def run_async(coro):
    """Run async coroutine in sync test"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture
def client():
    """AgentClient pointing to a fake agent"""
    return AgentClient(
        agent_url="http://fake-agent:9100",
        ollama_url="http://fake-ollama:11434",
        server_id="server1",
    )


def _mock_response(json_data, status_code=200):
    """Create a mock httpx.Response"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


def _patch_httpx(mock_get_fn):
    """Context manager to patch httpx.AsyncClient with a mock get function"""
    mock_instance = MagicMock()
    mock_instance.get = mock_get_fn
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=False)
    return patch("httpx.AsyncClient", return_value=mock_instance)


# ---------- GPU Metrics ----------

class TestGetGpuMetrics:
    """Test get_gpu_metrics() normalization from agent /metrics/gpu"""

    def test_normalizes_gpu_array(self, client):
        """TC-A01: Should extract gpus[0] and normalize keys"""
        agent_response = {
            "gpus": [{
                "index": 0,
                "name": "NVIDIA RTX 4090",
                "memory_total_mb": 24576.0,
                "memory_used_mb": 8192.0,
                "memory_free_mb": 16384.0,
                "gpu_util_pct": 45.0,
                "memory_util_pct": 33.3,
                "temperature_c": 65.0,
                "power_w": 250.0,
            }],
            "timestamp": "2026-04-28T10:00:00"
        }

        async def mock_get(url, **kwargs):
            return _mock_response(agent_response)

        with _patch_httpx(mock_get):
            result = run_async(client.get_gpu_metrics())

        assert result is not None
        assert result["gpu_util_pct"] == 45.0
        assert result["vram_used_gb"] == pytest.approx(8.0, rel=0.01)
        assert result["vram_total_gb"] == pytest.approx(24.0, rel=0.01)
        assert result["gpu_power_watts"] == 250.0
        assert result["gpu_temperature_c"] == 65.0
        assert result["gpu_name"] == "NVIDIA RTX 4090"

    def test_empty_gpu_array(self, client):
        """TC-A02: Should return None when gpus array is empty (no GPU)"""
        agent_response = {"error": "nvidia-smi not found", "gpus": []}

        async def mock_get(url, **kwargs):
            return _mock_response(agent_response)

        with _patch_httpx(mock_get):
            result = run_async(client.get_gpu_metrics())

        assert result is None

    def test_agent_unreachable(self, client):
        """TC-A03: Should return None when agent is offline"""
        async def mock_get(url, **kwargs):
            raise Exception("Connection refused")

        with _patch_httpx(mock_get):
            result = run_async(client.get_gpu_metrics())

        assert result is None


# ---------- System Metrics ----------

class TestGetSystemMetrics:
    """Test system metrics passthrough from agent /metrics/system"""

    def test_returns_raw_json(self, client):
        """TC-A04: get_system_metrics returns raw agent JSON"""
        agent_response = {
            "cpu_usage_pct": 3.1,
            "memory_total_mb": 7939,
            "memory_used_mb": 2503,
            "memory_free_mb": 3706,
            "load_avg_1m": 0.15,
            "timestamp": "2026-04-28T10:00:00"
        }

        async def mock_get(url, **kwargs):
            return _mock_response(agent_response)

        with _patch_httpx(mock_get):
            result = run_async(client.get_system_metrics())

        assert result is not None
        assert result["cpu_usage_pct"] == 3.1
        assert result["memory_used_mb"] == 2503


# ---------- get_all_metrics (Combined) ----------

class TestGetAllMetrics:
    """Test get_all_metrics() combines GPU + system into HardwareMetrics"""

    def test_combines_gpu_and_system(self, client):
        """TC-A05: Full pipeline: agent JSON → HardwareMetrics object"""
        gpu_response = {
            "gpus": [{
                "index": 0,
                "name": "NVIDIA T4",
                "memory_total_mb": 15360.0,
                "memory_used_mb": 4096.0,
                "gpu_util_pct": 78.0,
                "temperature_c": 55.0,
                "power_w": 70.0,
                "memory_free_mb": 11264.0,
                "memory_util_pct": 26.7,
            }],
            "timestamp": "2026-04-28T10:00:00"
        }
        sys_response = {
            "cpu_usage_pct": 51.4,
            "memory_total_mb": 7939,
            "memory_used_mb": 2503,
            "memory_free_mb": 5436,
            "timestamp": "2026-04-28T10:00:00"
        }

        async def mock_get(url, **kwargs):
            if "/metrics/gpu" in url:
                return _mock_response(gpu_response)
            elif "/metrics/system" in url:
                return _mock_response(sys_response)
            return _mock_response({}, 404)

        with _patch_httpx(mock_get):
            metrics = run_async(client.get_all_metrics())

        assert isinstance(metrics, HardwareMetrics)
        assert metrics.server == "server1"

        # GPU fields
        assert metrics.gpu_util_pct == 78.0
        assert metrics.vram_used_gb == pytest.approx(4.0, rel=0.01)
        assert metrics.vram_total_gb == pytest.approx(15.0, rel=0.01)
        assert metrics.gpu_power_watts == 70.0
        assert metrics.gpu_temperature_c == 55.0
        assert metrics.gpu_name == "NVIDIA T4"

        # System fields
        assert metrics.cpu_pct == 51.4
        assert metrics.ram_used_gb == pytest.approx(2503 / 1024, rel=0.01)
        assert metrics.ram_total_gb == pytest.approx(7939 / 1024, rel=0.01)

    def test_system_only_no_gpu(self, client):
        """TC-A06: System metrics only (no GPU on server)"""
        gpu_response = {"gpus": [], "error": "nvidia-smi not found"}
        sys_response = {
            "cpu_usage_pct": 12.0,
            "memory_total_mb": 16000,
            "memory_used_mb": 8000,
            "memory_free_mb": 8000,
        }

        async def mock_get(url, **kwargs):
            if "/metrics/gpu" in url:
                return _mock_response(gpu_response)
            elif "/metrics/system" in url:
                return _mock_response(sys_response)
            return _mock_response({}, 404)

        with _patch_httpx(mock_get):
            metrics = run_async(client.get_all_metrics())

        assert metrics is not None
        assert metrics.gpu_util_pct is None
        assert metrics.vram_used_gb is None
        assert metrics.cpu_pct == 12.0
        assert metrics.ram_used_gb == pytest.approx(8000 / 1024, rel=0.01)

    def test_both_offline(self, client):
        """TC-A07: Return None when both GPU and system endpoints fail"""
        async def mock_get(url, **kwargs):
            raise Exception("Connection refused")

        with _patch_httpx(mock_get):
            metrics = run_async(client.get_all_metrics())

        assert metrics is None


# ---------- Health Checks ----------

class TestHealthChecks:
    """Test agent and ollama health check methods"""

    def test_agent_healthy(self, client):
        """TC-A08: Agent responds 200"""
        async def mock_get(url, **kwargs):
            return _mock_response({"status": "ok"})

        with _patch_httpx(mock_get):
            assert run_async(client.check_agent_health()) is True

    def test_agent_offline(self, client):
        """TC-A09: Agent connection refused"""
        async def mock_get(url, **kwargs):
            raise Exception("Refused")

        with _patch_httpx(mock_get):
            assert run_async(client.check_agent_health()) is False

    def test_ollama_healthy(self, client):
        """TC-A10: Ollama responds 200"""
        async def mock_get(url, **kwargs):
            return _mock_response({"models": []})

        with _patch_httpx(mock_get):
            assert run_async(client.check_ollama_health()) is True


# ---------- Server Status ----------

class TestGetServerStatus:
    """Test get_server_status() combines health + GPU info"""

    def test_full_status(self, client):
        """TC-A11: Fully online server with GPU"""
        gpu_response = {
            "gpus": [{
                "name": "NVIDIA RTX 4090",
                "memory_total_mb": 24576.0,
                "memory_used_mb": 8192.0,
                "memory_free_mb": 16384.0,
                "gpu_util_pct": 10.0,
                "memory_util_pct": 33.0,
                "temperature_c": 40.0,
                "power_w": 50.0,
            }]
        }
        models_response = {
            "models": [
                {"name": "llama3:8b"},
                {"name": "llama3.2:latest"},
            ]
        }
        version_response = {"version": "0.1.34"}

        call_map = {
            "/health": _mock_response({"status": "ok"}),
            "/api/tags": _mock_response(models_response),
            "/api/version": _mock_response(version_response),
            "/metrics/gpu": _mock_response(gpu_response),
        }

        async def mock_get(url, **kwargs):
            for path, resp in call_map.items():
                if path in url:
                    return resp
            return _mock_response({}, 404)

        with _patch_httpx(mock_get):
            status = run_async(client.get_server_status("AI Server 1"))

        assert status.server_id == "server1"
        assert status.server_name == "AI Server 1"
        assert status.agent_online is True
        assert status.ollama_online is True
        assert len(status.models_loaded) == 2
        assert status.gpu_name == "NVIDIA RTX 4090"
        assert status.vram_total_gb == pytest.approx(24.0, rel=0.01)
        assert status.ollama_version == "0.1.34"
