"""SQLAlchemy ORM table definitions"""

import enum
from src.time_utils import get_local_time
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(20), default=RunStatus.PENDING.value, nullable=False)
    started_at = Column(DateTime, default=get_local_time)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    config_snapshot = Column(JSON, nullable=True)
    suite = Column(String(50), nullable=True)
    environment = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    total_tests = Column(Integer, default=0)
    completed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)

    results = relationship(
        "BenchmarkResultRow",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    hardware_snapshots = relationship(
        "HardwareSnapshot",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    comparisons = relationship(
        "ServerComparison",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class BenchmarkResultRow(Base):
    __tablename__ = "benchmark_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(
        String(64), ForeignKey("benchmark_runs.run_id"), nullable=False
    )
    timestamp = Column(DateTime, default=get_local_time)
    server = Column(String(50), nullable=False)
    tool = Column(String(50), nullable=False)
    environment = Column(String(50), nullable=False)
    scenario = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    concurrency = Column(Integer, default=1)

    ttft_ms = Column(Float, nullable=True)
    tpot_ms = Column(Float, nullable=True)
    itl_ms = Column(Float, nullable=True)
    tps = Column(Float, nullable=True)

    rps = Column(Float, nullable=True)
    latency_p50_ms = Column(Float, nullable=True)
    latency_p95_ms = Column(Float, nullable=True)
    latency_p99_ms = Column(Float, nullable=True)

    total_tokens = Column(Integer, nullable=True)
    total_requests = Column(Integer, nullable=True)
    successful_requests = Column(Integer, nullable=True)
    failed_requests = Column(Integer, nullable=True)
    error_rate = Column(Float, nullable=True)

    goodput = Column(Float, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)

    raw_output = Column(JSON, nullable=True)

    run = relationship("BenchmarkRun", back_populates="results")

    __table_args__ = (
        Index("idx_results_run_id", "run_id"),
        Index("idx_results_server", "server"),
        Index("idx_results_tool", "tool"),
        Index("idx_results_scenario", "scenario"),
        Index("idx_results_server_tool", "server", "tool"),
    )


class HardwareSnapshot(Base):
    __tablename__ = "hardware_snapshots"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(
        String(64), ForeignKey("benchmark_runs.run_id"), nullable=False
    )
    timestamp = Column(DateTime, default=get_local_time)
    server = Column(String(50), nullable=False)

    gpu_name = Column(String(200), nullable=True)
    gpu_util_pct = Column(Float, nullable=True)
    vram_used_gb = Column(Float, nullable=True)
    vram_total_gb = Column(Float, nullable=True)
    gpu_power_watts = Column(Float, nullable=True)
    gpu_temperature_c = Column(Float, nullable=True)
    gpu_memory_bandwidth_gbps = Column(Float, nullable=True)

    cpu_pct = Column(Float, nullable=True)
    ram_used_gb = Column(Float, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    disk_read_mbps = Column(Float, nullable=True)
    disk_write_mbps = Column(Float, nullable=True)
    network_rx_mbps = Column(Float, nullable=True)
    network_tx_mbps = Column(Float, nullable=True)

    run = relationship("BenchmarkRun", back_populates="hardware_snapshots")

    __table_args__ = (Index("idx_hw_run_server", "run_id", "server"),)


class ServerComparison(Base):
    __tablename__ = "server_comparisons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        String(64), ForeignKey("benchmark_runs.run_id"), nullable=False
    )
    created_at = Column(DateTime, default=get_local_time)

    environment = Column(String(50), nullable=True)
    scenario = Column(String(100), nullable=True)
    tool = Column(String(50), nullable=True)
    concurrency = Column(Integer, nullable=True)

    s1_ttft_ms = Column(Float, nullable=True)
    s1_tpot_ms = Column(Float, nullable=True)
    s1_tps = Column(Float, nullable=True)
    s1_rps = Column(Float, nullable=True)
    s1_p99_ms = Column(Float, nullable=True)
    s1_gpu_util_pct = Column(Float, nullable=True)
    s1_power_watts = Column(Float, nullable=True)

    s2_ttft_ms = Column(Float, nullable=True)
    s2_tpot_ms = Column(Float, nullable=True)
    s2_tps = Column(Float, nullable=True)
    s2_rps = Column(Float, nullable=True)
    s2_p99_ms = Column(Float, nullable=True)
    s2_gpu_util_pct = Column(Float, nullable=True)
    s2_power_watts = Column(Float, nullable=True)

    delta_ttft_pct = Column(Float, nullable=True)
    delta_tpot_pct = Column(Float, nullable=True)
    delta_tps_pct = Column(Float, nullable=True)
    delta_rps_pct = Column(Float, nullable=True)
    delta_p99_pct = Column(Float, nullable=True)

    s1_cost_per_million_tokens = Column(Float, nullable=True)
    s2_cost_per_million_tokens = Column(Float, nullable=True)
    cost_savings_pct = Column(Float, nullable=True)

    overall_winner = Column(String(20), nullable=True)

    run = relationship("BenchmarkRun", back_populates="comparisons")


class ServerProfile(Base):
    __tablename__ = "server_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(String(50), nullable=False, index=True, unique=True)
    recorded_at = Column(DateTime, default=get_local_time)
    name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    gpu_name = Column(String(200), nullable=True)
    gpu_count = Column(Integer, nullable=True)
    vram_total_gb = Column(Float, nullable=True)
    cpu_model = Column(String(200), nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    hardware_cost_usd = Column(Float, nullable=True)
    monthly_power_usd = Column(Float, nullable=True)
    ollama_version = Column(String(50), nullable=True)
    models_available = Column(JSON, nullable=True)
    aidaptive_version = Column(String(50), nullable=True)
    aidaptive_firmware = Column(String(50), nullable=True)