"""Configuration loader and data models"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class AppConfig:
    name: str = "Benchmark AI Server System"
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8443


@dataclass
class PostgresConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "aidaptive_benchmark"
    user: str = "aidaptive"
    password: str = "aidaptive2024"

    @property
    def sync_url(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    @property
    def async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


@dataclass
class InfluxDBConfig:
    url: str = "http://localhost:8086"
    token: str = ""
    org: str = "aidaptive"
    bucket: str = "benchmarks"


@dataclass
class GrafanaConfig:
    url: str = "http://localhost:3000"
    admin_user: str = "admin"
    admin_password: str = ""


@dataclass
class ServerConfig:
    name: str = ""
    description: str = ""
    ollama_url: str = ""
    agent_url: str = ""
    hardware_cost_usd: float = 0
    monthly_power_usd: float = 0


@dataclass
class EnvironmentConfig:
    name: str = ""
    server1_url: str = ""
    server2_url: str = ""
    enabled: bool = True


@dataclass
class BenchmarkSuiteConfig:
    enabled: bool = True
    description: str = ""
    scenarios: list = field(default_factory=list)
    requests_per_scenario: int = 50
    duration_seconds: int = 120
    concurrency: int = 10
    concurrency_levels: list = field(default_factory=list)
    pattern: str = ""
    interval_seconds: int = 60


@dataclass
class BenchmarkConfig:
    warmup_requests: int = 3
    cooldown_seconds: int = 10
    concurrency_levels: list = field(default_factory=lambda: [1, 5, 10, 25, 50])
    test_suites: dict = field(default_factory=dict)


@dataclass
class ToolConfig:
    enabled: bool = True
    binary_path: str = ""
    supported_suites: list = field(default_factory=list)


@dataclass
class MetricsConfig:
    gpu_poll_interval_seconds: int = 1
    system_poll_interval_seconds: int = 5


@dataclass
class ReportsConfig:
    output_dir: str = "./reports"
    generate_pdf: bool = True
    generate_csv: bool = True


@dataclass
class Config:
    app: AppConfig = field(default_factory=AppConfig)
    postgres: PostgresConfig = field(default_factory=PostgresConfig)
    influxdb: InfluxDBConfig = field(default_factory=InfluxDBConfig)
    grafana: GrafanaConfig = field(default_factory=GrafanaConfig)
    servers: dict = field(default_factory=dict)
    models: list = field(default_factory=list)
    environments: dict = field(default_factory=dict)
    benchmark: BenchmarkConfig = field(default_factory=BenchmarkConfig)
    tools: dict = field(default_factory=dict)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    reports: ReportsConfig = field(default_factory=ReportsConfig)


def load_config(path: str = "benchmark.yaml") -> Config:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    cfg = Config()

    if "app" in raw:
        cfg.app = AppConfig(**raw["app"])

    if "postgres" in raw:
        cfg.postgres = PostgresConfig(**raw["postgres"])

    if "influxdb" in raw:
        cfg.influxdb = InfluxDBConfig(**raw["influxdb"])

    if "grafana" in raw:
        cfg.grafana = GrafanaConfig(**raw["grafana"])

    if "servers" in raw:
        for key, val in raw["servers"].items():
            cfg.servers[key] = ServerConfig(**val)

    cfg.models = raw.get("models", ["llama3:8b"])

    if "environments" in raw:
        for key, val in raw["environments"].items():
            cfg.environments[key] = EnvironmentConfig(**val)

    if "benchmark" in raw:
        bm = raw["benchmark"]
        cfg.benchmark.warmup_requests = bm.get("warmup_requests", 3)
        cfg.benchmark.cooldown_seconds = bm.get("cooldown_seconds", 10)
        cfg.benchmark.concurrency_levels = bm.get(
            "concurrency_levels", [1, 5, 10, 25, 50]
        )
        if "test_suites" in bm:
            for key, val in bm["test_suites"].items():
                cfg.benchmark.test_suites[key] = BenchmarkSuiteConfig(**val)

    if "tools" in raw:
        for key, val in raw["tools"].items():
            cfg.tools[key] = ToolConfig(**val)

    if "metrics" in raw:
        cfg.metrics = MetricsConfig(**raw["metrics"])

    if "reports" in raw:
        cfg.reports = ReportsConfig(**raw["reports"])

    return cfg
