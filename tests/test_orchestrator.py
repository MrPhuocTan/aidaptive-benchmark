"""
Test Suite 8: Orchestrator Logic
Tests for Orchestrator helper methods (no DB required).
"""

import pytest

from src.config import Config, ToolConfig, BenchmarkSuiteConfig
from src.orchestrator import Orchestrator


@pytest.fixture
def mock_config():
    """Config with tools enabled"""
    cfg = Config()
    cfg.tools = {
        "ollama_native": ToolConfig(enabled=True),
        "oha": ToolConfig(enabled=True, binary_path="/usr/bin/oha"),
        "litellm": ToolConfig(enabled=True),
        "locust": ToolConfig(enabled=False),  # Disabled
        "llmperf": ToolConfig(enabled=True),
        "vllm_bench": ToolConfig(enabled=True),
    }
    return cfg


class TestGetEnabledTools:
    """Test _get_enabled_tools()"""

    def test_returns_only_enabled(self, mock_config):
        """TC-O01: Should only return tools with enabled=True"""
        orch = Orchestrator.__new__(Orchestrator)
        orch.config = mock_config
        tools = orch._get_enabled_tools()
        tool_names = [t[0] for t in tools]
        assert "ollama_native" in tool_names
        assert "oha" in tool_names
        assert "litellm" in tool_names
        assert "locust" not in tool_names  # Disabled

    def test_filters_by_suite(self, mock_config):
        """TC-O02: Should filter tools by supported_suites"""
        mock_config.tools["oha"].supported_suites = ["concurrency_scaling"]
        orch = Orchestrator.__new__(Orchestrator)
        orch.config = mock_config
        tools = orch._get_enabled_tools(suite_name="single_request")
        tool_names = [t[0] for t in tools]
        assert "oha" not in tool_names  # Not supported for this suite

    def test_no_suite_filter(self, mock_config):
        """TC-O03: Without suite filter, all enabled tools returned"""
        orch = Orchestrator.__new__(Orchestrator)
        orch.config = mock_config
        tools = orch._get_enabled_tools(suite_name=None)
        assert len(tools) == 5  # All enabled (locust disabled)


class TestGenerateRunId:
    """Test run ID generation"""

    def test_format(self, mock_config):
        """TC-O04: Run ID should match run_YYYYMMDD_HHMMSS format"""
        orch = Orchestrator.__new__(Orchestrator)
        orch.config = mock_config
        run_id = orch.generate_run_id()
        assert run_id.startswith("run_")
        # Format: run_YYYYMMDD_HHMMSS → always 20 chars
        parts = run_id.split("_")
        assert len(parts) == 3  # ["run", "YYYYMMDD", "HHMMSS"]
        assert len(parts[1]) == 8  # Date part
        assert len(parts[2]) == 6  # Time part

    def test_unique(self, mock_config):
        """TC-O05: Two consecutive run IDs should be different (or same second)"""
        orch = Orchestrator.__new__(Orchestrator)
        orch.config = mock_config
        import time
        id1 = orch.generate_run_id()
        time.sleep(1.1)
        id2 = orch.generate_run_id()
        assert id1 != id2


class TestProgressTracking:
    """Test progress getter"""

    def test_idle_progress(self, mock_config):
        """TC-O06: Initial progress should be idle"""
        orch = Orchestrator.__new__(Orchestrator)
        orch.config = mock_config
        orch._progress = {
            "status": "idle",
            "run_id": "",
            "current_phase": "",
            "current_test": "",
            "total_tests": 0,
            "completed_tests": 0,
            "percent": 0,
            "started_at": None,
            "errors": [],
            "elapsed_seconds": 0,
            "estimated_remaining_seconds": None,
            "live_metrics": {},
        }
        orch._live_metrics = {}
        progress = orch.get_progress()
        assert progress["status"] == "idle"
        assert progress["total_tests"] == 0

    def test_is_running_false_when_idle(self, mock_config):
        """TC-O07: is_running() should be False when idle"""
        orch = Orchestrator.__new__(Orchestrator)
        orch._progress = {"status": "idle"}
        assert orch.is_running() is False

    def test_is_running_true(self, mock_config):
        """TC-O08: is_running() should be True when running"""
        orch = Orchestrator.__new__(Orchestrator)
        orch._progress = {"status": "running"}
        assert orch.is_running() is True
