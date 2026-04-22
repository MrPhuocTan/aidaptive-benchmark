"""Unified data sink - writes to both PostgreSQL and InfluxDB"""

from src.config import Config
from src.data.influxdb_writer import InfluxDBWriter
from src.data.normalizer import Normalizer
from src.database.engine import Database
from src.database.repository import Repository
from src.database.tables import (
    BenchmarkResultRow,
    HardwareSnapshot,
    ServerComparison,
)
from src.models import BenchmarkResult, HardwareMetrics


class DataSink:
    """
    Unified writer that sends data to both:
    - PostgreSQL (structured, persistent, queryable for history)
    - InfluxDB (time-series, realtime Grafana dashboards)
    """

    def __init__(self, config: Config):
        self.config = config

        # PostgreSQL
        self.db = Database(config.postgres)
        self.db.create_tables()

        # InfluxDB
        self.influx = InfluxDBWriter(config.influxdb)
        try:
            self.influx.connect()
        except Exception as e:
            print(f"  InfluxDB connection warning: {e}")

    def close(self):
        try:
            self.influx.close()
        except Exception:
            pass

    def get_repository(self) -> Repository:
        session = self.db.get_sync_session()
        return Repository(session)

    def write_benchmark_result(self, result: BenchmarkResult, run_id: str):
        """Write benchmark result to BOTH databases"""

        # Normalize first
        result = Normalizer.normalize(result)

        if not Normalizer.is_valid(result):
            return

        # 1. PostgreSQL
        session = self.db.get_sync_session()
        try:
            db_result = BenchmarkResultRow(
                run_id=run_id,
                timestamp=result.timestamp,
                server=result.server,
                tool=result.tool,
                environment=result.environment,
                scenario=result.scenario,
                model=result.model,
                concurrency=result.concurrency,
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
        except Exception as e:
            session.rollback()
            print(f"  PostgreSQL write error (benchmark): {e}")
        finally:
            session.close()

        # 2. InfluxDB
        try:
            result.run_id = run_id
            self.influx.write_benchmark_result(result)
        except Exception as e:
            print(f"  InfluxDB write error (benchmark): {e}")

    def write_hardware_metrics(self, metrics: HardwareMetrics, run_id: str):
        """Write hardware metrics to BOTH databases"""

        # 1. PostgreSQL
        session = self.db.get_sync_session()
        try:
            snapshot = HardwareSnapshot(
                run_id=run_id,
                timestamp=metrics.timestamp,
                server=metrics.server,
                gpu_name=metrics.gpu_name,
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
        except Exception as e:
            session.rollback()
            print(f"  PostgreSQL write error (hardware): {e}")
        finally:
            session.close()

        # 2. InfluxDB
        try:
            self.influx.write_hardware_metrics(metrics)
        except Exception as e:
            print(f"  InfluxDB write error (hardware): {e}")

    def write_comparison(self, run_id: str, **kwargs):
        """Write server comparison to PostgreSQL only (not time-series)"""

        session = self.db.get_sync_session()
        try:
            comparison = ServerComparison(run_id=run_id, **kwargs)
            session.add(comparison)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"  PostgreSQL write error (comparison): {e}")
        finally:
            session.close()

    def delete_run(self, run_id: str):
        """Delete all data for a run from BOTH databases"""

        # 1. PostgreSQL (cascade deletes via foreign keys)
        repo = self.get_repository()
        repo_session = repo.session
        try:
            from src.database.tables import BenchmarkRun
            run = repo_session.query(BenchmarkRun).filter_by(run_id=run_id).first()
            if run:
                repo_session.delete(run)
                repo_session.commit()
        except Exception as e:
            repo_session.rollback()
            print(f"  PostgreSQL delete error: {e}")
        finally:
            repo_session.close()

        # 2. InfluxDB
        try:
            self.influx.delete_run_data(run_id)
        except Exception as e:
            print(f"  InfluxDB delete error: {e}")
