"""
Test Suite 6: Live Agent Integration Test
Tests against the REAL agent running on vm01 via SSH tunnel.
Only runs when agent is reachable (marks as skip otherwise).
"""

import pytest
import httpx

# The internal VPC IP of vm01 — only reachable from benchmarktool or via SSH tunnel
AGENT_BASE_URL = "http://10.148.0.13:9100"


async def _is_agent_reachable() -> bool:
    """Check if the live agent is reachable"""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{AGENT_BASE_URL}/health")
            return resp.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def agent_reachable():
    """Module-level fixture to check agent reachability"""
    import asyncio
    reachable = asyncio.run(_is_agent_reachable())
    if not reachable:
        pytest.skip("Agent on vm01 is not reachable (expected if running locally)")


class TestLiveAgentHealth:
    """Live integration tests against vm01 agent"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, agent_reachable):
        """TC-L01: /health returns status ok"""
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{AGENT_BASE_URL}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_system_metrics_keys(self, agent_reachable):
        """TC-L02: /metrics/system returns expected keys"""
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{AGENT_BASE_URL}/metrics/system")
        assert resp.status_code == 200
        data = resp.json()
        # These are the keys the agent MUST return for our mapping to work
        assert "cpu_usage_pct" in data
        assert "memory_total_mb" in data
        assert "memory_used_mb" in data
        assert "memory_free_mb" in data
        # Type checks
        assert isinstance(data["cpu_usage_pct"], (int, float))
        assert isinstance(data["memory_total_mb"], int)
        assert isinstance(data["memory_used_mb"], int)

    @pytest.mark.asyncio
    async def test_gpu_metrics_structure(self, agent_reachable):
        """TC-L03: /metrics/gpu returns gpus array"""
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{AGENT_BASE_URL}/metrics/gpu")
        assert resp.status_code == 200
        data = resp.json()
        assert "gpus" in data
        assert isinstance(data["gpus"], list)
        # vm01 has no GPU, so array should be empty
        # But if a GPU exists, check the keys
        if data["gpus"]:
            gpu = data["gpus"][0]
            assert "gpu_util_pct" in gpu
            assert "memory_used_mb" in gpu
            assert "memory_total_mb" in gpu
            assert "power_w" in gpu
            assert "temperature_c" in gpu
            assert "name" in gpu

    @pytest.mark.asyncio
    async def test_info_endpoint_keys(self, agent_reachable):
        """TC-L04: /info returns expected keys for background.py"""
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{AGENT_BASE_URL}/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "cpu_model" in data
        assert "cpu_cores" in data
        assert "ram_gb" in data
        assert "hostname" in data
        # Type checks — these are strings from the agent
        assert isinstance(data["cpu_cores"], str)
        assert isinstance(data["ram_gb"], str)
        # Should be parseable as numbers
        int(data["cpu_cores"])
        float(data["ram_gb"])

    @pytest.mark.asyncio
    async def test_agent_client_integration(self, agent_reachable):
        """TC-L05: Full AgentClient pipeline against live agent"""
        from src.collectors.agent_client import AgentClient

        client = AgentClient(
            agent_url=AGENT_BASE_URL,
            ollama_url="http://10.148.0.13:11434",
            server_id="vm01",
        )

        # Health check
        assert await client.check_agent_health() is True

        # System metrics via get_all_metrics
        metrics = await client.get_all_metrics()
        assert metrics is not None
        assert metrics.server == "vm01"
        assert metrics.cpu_pct is not None
        assert metrics.cpu_pct >= 0
        assert metrics.ram_used_gb is not None
        assert metrics.ram_used_gb > 0
        assert metrics.ram_total_gb is not None
        assert metrics.ram_total_gb > 0

        # Server specs
        specs = await client.get_server_specs()
        assert specs is not None
        assert "cpu_model" in specs
