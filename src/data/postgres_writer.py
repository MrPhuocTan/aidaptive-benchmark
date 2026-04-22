"""PostgreSQL writer - structured persistent storage"""

from src.time_utils import get_local_time
from datetime import datetime
from typing import Optional, List

from src.config import PostgresConfig
from src.database.engine import Database
from src.database.tables import (
    BenchmarkRun,
    BenchmarkResultRow,
    HardwareSnapshot,
    ServerComparison,
    ServerProfile,
    RunStatus,
)
from src.models import BenchmarkResult, HardwareMetrics


class PostgresWriter:
    """Direct PostgreSQL write operations (used by DataSink)"""

    def __init__(self, database: Database):
        self.database = database

    def is_connected(self) -> bool:
        return self.database.is_connected()

    # --------------------------------------------------
    # Benchmark Runs
    # --------------------------------------------------
    def create_run(
        self,
        run_id: str,
        suite: str = "",
        environment: str = "",
        model: str = "",
        config_snapshot: dict = None,
        notes: str = "",
        tags: list = None,
    ) -> Optional[BenchmarkRun]:
        session = self.database.get_sync_session()
        try:
            run = BenchmarkRun(
                run_id=run_id,
                status=RunStatus.PENDING.value,
                started_at=get_local_time(),
                suite=suite,
                environment=environment,
                model=model,
                config_snapshot=config_snapshot or {},
                notes=notes,
                tags=tags or [],
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return run
        except Exception as e:
            session.rollback()
            print(f"  PostgreSQL create_run error: {e}")
            return None
        finally:
            session.close()

    def update_run_status(self, run_id: str, status: str, **kwargs):
        session = self.database.get_sync_session()
        try:
            run = session.query(BenchmarkRun).filter_by(run_id=run_id).first()
            if not run:
                return

            run.status = status
            if status in (RunStatus.COMPLETED.value, RunStatus.FAILED.value):
                run.finished_at = get_local_time()
                if run.started_at:
                    run.duration_seconds = (
                        run.finished_at - run.started_at
                    ).total_seconds()

            for key, value in kwargs.items():
                if hasattr(run, key):
                    setattr(run, key, value)

            session.commit()
        except Exception as e:
            session.rollback()
            print(f"  PostgreSQL update_run error: {e}")
        finally:
            session.close()

    def get_run(self, run_id: str) -> Optional[BenchmarkRun]:
        session = self.database.get_sync_session()
        try:
            return session.query(BenchmarkRun).filter_by(run_id=run_id).first()
        finally:
            session.close()

    # --------------------------------------------------
    # Benchmark Results
    # --------------------------------------------------
    def write_result(self, result: BenchmarkResult, run_id: str) -> bool:
        session = self.database.get_sync_session()
        try:
            db_result = BenchmarkResultRow(
                run_id=run_id,
                timestamp=result.timestamp or get_local_time(),
                server=result.server or "",
                tool=result.tool or "",
                environment=result.environment or "",
                scenario=result.scenario or "",
                model=result.model or "",
                concurrency=result.concurrency or 1,
                ttft_ms=result.ttft_ms,
                tpot_ms=result.tpot_ms,
                itl_ms=result.itl_ms,
                tps=result.tps,
                rps=result.rps,
                latency_p50_ms=result.latency_p50_ms,
                latency_p95_ms=result.latency_p95_ms,
                latency_p99_ms=result.latency_p99_ms,
                total_tokens=result.total_tokens,
                total_requests=result.total_requests,
                successful_requests=result.successful_requests,
                failed_requests=result.failed_requests,
                error_rate=result.error_rate,
                goodput=result.goodput,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                raw_output=result.to_dict(),
            )
            session.add(db_result)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"  PostgreSQL write_result error: {e}")
            return False
        finally:
            session.close()

    def write_results_batch(
        self, results: List[BenchmarkResult], run_id: str
    ) -> int:
        session = self.database.get_sync_session()
        count = 0
        try:
            for result in results:
                db_result = BenchmarkResultRow(
                    run_id=run_id,
                    timestamp=result.timestamp or get_local_time(),
                    server=result.server or "",
                    tool=result.tool or "",
                    environment=result.environment or "",
                    scenario=result.scenario or "",
                    model=result.model or "",
                    concurrency=result.concurrency or 1,
                    ttft_ms=result.ttft_ms,
                    tpot_ms=result.tpot_ms,
                    itl_ms=result.itl_ms,
                    tps=result.tps,
                    rps=result.rps,
                    latency_p50_ms=result.latency_p50_ms,
                    latency_p95_ms=result.latency_p95_ms,
                    latency_p99_ms=result.latency_p99_ms,
                    total_tokens=result.total_tokens,
                    total_requests=result.total_requests,
                    successful_requests=result.successful_requests,
                    failed_requests=result.failed_requests,
                    error_rate=result.error_rate,
                    goodput=result.goodput,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    raw_output=result.to_dict(),
                )
                session.add(db_result)
                count += 1

            session.commit()
            return count
        except Exception as e:
            session.rollback()
            print(f"  PostgreSQL write_results_batch error: {e}")
            return 0
        finally:
            session.close()

    # --------------------------------------------------
    # Hardware Snapshots
    # --------------------------------------------------
    def write_hardware_snapshot(
        self, metrics: HardwareMetrics, run_id: str
    ) -> bool:
        session = self.database.get_sync_session()
        try:
            snapshot = HardwareSnapshot(
                run_id=run_id,
                timestamp=metrics.timestamp or get_local_time(),
                server=metrics.server or "",
                gpu_name=metrics.gpu_name or "",
                gpu_util_pct=metrics.gpu_util_pct,
                vram_used_gb=metrics.vram_used_gb,
                vram_total_gb=metrics.vram_total_gb,
                gpu_power_watts=metrics.gpu_power_watts,
                gpu_temperature_c=metrics.gpu_temperature_c,
                gpu_memory_bandwidth_gbps=metrics.gpu_memory_bandwidth_gbps,
                cpu_pct=metrics.cpu_pct,
                ram_used_gb=metrics.ram_used_gb,
                ram_total_gb=metrics.ram_total_gb,
                disk_read_mbps=metrics.disk_read_mbps,
                disk_write_mbps=metrics.disk_write_mbps,
                network_rx_mbps=metrics.network_rx_mbps,
                network_tx_mbps=metrics.network_tx_mbps,
            )
            session.add(snapshot)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"  PostgreSQL write_hardware error: {e}")
            return False
        finally:
            session.close()

    # --------------------------------------------------
    # Server Comparisons
    # --------------------------------------------------
    def write_comparison(self, run_id: str, **kwargs) -> bool:
        session = self.database.get_sync_session()
        try:
            comparison = ServerComparison(
                run_id=run_id,
                created_at=get_local_time(),
                **kwargs,
            )
            session.add(comparison)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"  PostgreSQL write_comparison error: {e}")
            return False
        finally:
            session.close()

    # --------------------------------------------------
    # Server Profiles
    # --------------------------------------------------
    def write_server_profile(self, profile_data: dict) -> bool:
        session = self.database.get_sync_session()
        try:
            server_id = profile_data.get("server_id")
            if not server_id:
                return False
                
            profile = session.query(ServerProfile).filter_by(server_id=server_id).first()
            if not profile:
                profile = ServerProfile(server_id=server_id)
                session.add(profile)
                
            profile.recorded_at = get_local_time()
            for key, value in profile_data.items():
                if key != "server_id" and hasattr(profile, key):
                    setattr(profile, key, value)
                    
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"  PostgreSQL write_profile error: {e}")
            return False
        finally:
            session.close()

    def get_latest_profile(self, server_id: str) -> Optional[ServerProfile]:
        session = self.database.get_sync_session()
        try:
            from sqlalchemy import desc
            return (
                session.query(ServerProfile)
                .filter_by(server_id=server_id)
                .order_by(desc(ServerProfile.recorded_at))
                .first()
            )
        finally:
            session.close()

    # --------------------------------------------------
    # Cleanup
    # --------------------------------------------------
    def delete_run(self, run_id: str) -> bool:
        session = self.database.get_sync_session()
        try:
            run = session.query(BenchmarkRun).filter_by(run_id=run_id).first()
            if run:
                session.delete(run)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"  PostgreSQL delete_run error: {e}")
            return False
        finally:
            session.close()

    def delete_old_hardware_snapshots(self, days: int = 30) -> int:
        """Delete hardware snapshots older than N days"""
        from datetime import timedelta

        session = self.database.get_sync_session()
        try:
            cutoff = get_local_time() - timedelta(days=days)
            count = (
                session.query(HardwareSnapshot)
                .filter(HardwareSnapshot.timestamp < cutoff)
                .delete()
            )
            session.commit()
            return count
        except Exception as e:
            session.rollback()
            print(f"  PostgreSQL cleanup error: {e}")
            return 0
        finally:
            session.close()