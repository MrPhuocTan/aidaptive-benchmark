"""
Test Suite 4: Configuration Loader
Tests for config.py — YAML parsing and default values.
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.config import load_config, Config, AppConfig, PostgresConfig


class TestLoadConfig:
    """Test config YAML loading"""

    def test_loads_production_config(self):
        """TC-C01: Load actual benchmark.yaml without errors"""
        config = load_config("benchmark.yaml")
        assert isinstance(config, Config)
        assert config.app.name != ""
        assert config.app.port > 0

    def test_models_loaded(self):
        """TC-C02: Models list should be populated"""
        config = load_config("benchmark.yaml")
        assert len(config.models) > 0
        assert isinstance(config.models[0], str)

    def test_tools_loaded(self):
        """TC-C03: Tools dict should be populated"""
        config = load_config("benchmark.yaml")
        assert len(config.tools) > 0
        # At least ollama_native should exist
        assert "ollama_native" in config.tools

    def test_concurrency_levels(self):
        """TC-C04: Concurrency levels should be a non-empty list"""
        config = load_config("benchmark.yaml")
        assert len(config.benchmark.concurrency_levels) > 0
        assert all(isinstance(c, int) for c in config.benchmark.concurrency_levels)

    def test_postgres_url_format(self):
        """TC-C05: PostgreSQL URLs should have correct prefix"""
        config = load_config("benchmark.yaml")
        assert config.postgres.sync_url.startswith("postgresql://")
        assert config.postgres.async_url.startswith("postgresql+asyncpg://")

    def test_missing_config_raises(self):
        """TC-C06: Missing config file should raise FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")

    def test_minimal_yaml(self):
        """TC-C07: Minimal YAML should load with defaults"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, dir="."
        ) as f:
            f.write("app:\n  name: TestApp\nmodels:\n  - llama3:8b\n")
            f.flush()
            try:
                config = load_config(f.name)
                assert config.app.name == "TestApp"
                assert config.models == ["llama3:8b"]
                # Defaults
                assert config.app.port == 8443
                assert config.benchmark.warmup_requests == 3
            finally:
                os.unlink(f.name)


class TestDefaultValues:
    """Test dataclass default values"""

    def test_app_config_defaults(self):
        """TC-C08: AppConfig defaults"""
        cfg = AppConfig()
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 8443

    def test_postgres_config_defaults(self):
        """TC-C09: PostgresConfig defaults"""
        cfg = PostgresConfig()
        assert cfg.host == "localhost"
        assert cfg.port == 5432
        assert cfg.database == "aidaptive_benchmark"
