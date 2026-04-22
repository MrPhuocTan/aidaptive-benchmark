"""InfluxDB time-series writer"""

from datetime import datetime
from typing import Optional

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from src.config import InfluxDBConfig
from src.models import BenchmarkResult, HardwareMetrics


class InfluxDBWriter:

    def __init__(self, config: InfluxDBConfig):
        self.config = config
        self.client: Optional[InfluxDBClient] = None
        self.write_api = None

    def connect(self):
        self.client = InfluxDBClient(
            url=self.config.url,
            token=self.config.token,
            org=self.config.org,
        )
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def close(self):
        if self.client:
            self.client.close()

    def is_connected(self) -> bool:
        try:
            if self.client is None:
                self.connect()
            return self.client.ping()
        except Exception:
            return False

    def write_benchmark_result(self, result: BenchmarkResult):
        if not self.write_api:
            self.connect()

        point = (
            Point("benchmark_results")
            .tag("server", result.server)
            .tag("tool", result.tool)
            .tag("environment", result.environment)
            .tag("scenario", result.scenario)
            .tag("model", result.model)
            .tag("run_id", result.run_id)
            .tag("concurrency", str(result.concurrency))
            .time(result.timestamp, WritePrecision.MS)
        )

        field_map = {
            "ttft_ms": result.ttft_ms,
            "tpot_ms": result.tpot_ms,
            "itl_ms": result.itl_ms,
            "tps": result.tps,
            "rps": result.rps,
            "latency_p50_ms": result.latency_p50_ms,
            "latency_p95_ms": result.latency_p95_ms,
            "latency_p99_ms": result.latency_p99_ms,
            "total_tokens": result.total_tokens,
            "total_requests": result.total_requests,
            "successful_requests": result.successful_requests,
            "failed_requests": result.failed_requests,
            "error_rate": result.error_rate,
            "goodput": result.goodput,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
        }

        for field_name, value in field_map.items():
            if value is not None:
                point = point.field(field_name, float(value))

        try:
            self.write_api.write(
                bucket=self.config.bucket,
                org=self.config.org,
                record=point,
            )
        except Exception as e:
            print(f"  InfluxDB write error (benchmark): {e}")

    def write_hardware_metrics(self, metrics: HardwareMetrics):
        if not self.write_api:
            self.connect()

        point = (
            Point("hardware_metrics")
            .tag("server", metrics.server)
            .tag("gpu_name", metrics.gpu_name)
            .time(metrics.timestamp, WritePrecision.MS)
        )

        field_map = {
            "gpu_util_pct": metrics.gpu_util_pct,
            "vram_used_gb": metrics.vram_used_gb,
            "vram_total_gb": metrics.vram_total_gb,
            "gpu_power_watts": metrics.gpu_power_watts,
            "gpu_temperature_c": metrics.gpu_temperature_c,
            "gpu_memory_bandwidth_gbps": metrics.gpu_memory_bandwidth_gbps,
            "cpu_pct": metrics.cpu_pct,
            "ram_used_gb": metrics.ram_used_gb,
            "ram_total_gb": metrics.ram_total_gb,
            "disk_read_mbps": metrics.disk_read_mbps,
            "disk_write_mbps": metrics.disk_write_mbps,
            "network_rx_mbps": metrics.network_rx_mbps,
            "network_tx_mbps": metrics.network_tx_mbps,
        }

        for field_name, value in field_map.items():
            if value is not None:
                point = point.field(field_name, float(value))

        try:
            self.write_api.write(
                bucket=self.config.bucket,
                org=self.config.org,
                record=point,
            )
        except Exception as e:
            print(f"  InfluxDB write error (hardware): {e}")

    def query_results(
        self,
        run_id: str = "",
        server: str = "",
        tool: str = "",
        time_range: str = "-30d",
    ) -> list:
        if not self.client:
            self.connect()

        query_api = self.client.query_api()

        filters = ['r._measurement == "benchmark_results"']
        if run_id:
            filters.append(f'r["run_id"] == "{run_id}"')
        if server:
            filters.append(f'r["server"] == "{server}"')
        if tool:
            filters.append(f'r["tool"] == "{tool}"')

        filter_str = " and ".join(filters)

        query = f"""
        from(bucket: "{self.config.bucket}")
            |> range(start: {time_range})
            |> filter(fn: (r) => {filter_str})
            |> pivot(
                rowKey: ["_time"],
                columnKey: ["_field"],
                valueColumn: "_value"
            )
        """

        try:
            result = query_api.query(query, org=self.config.org)
            records = []
            for table in result:
                for record in table.records:
                    records.append(record.values)
            return records
        except Exception as e:
            print(f"  InfluxDB query error: {e}")
            return []

    def query_hardware_metrics(
        self,
        server: str = "",
        time_range: str = "-1h",
    ) -> list:
        if not self.client:
            self.connect()

        query_api = self.client.query_api()

        filters = ['r._measurement == "hardware_metrics"']
        if server:
            filters.append(f'r["server"] == "{server}"')

        filter_str = " and ".join(filters)

        query = f"""
        from(bucket: "{self.config.bucket}")
            |> range(start: {time_range})
            |> filter(fn: (r) => {filter_str})
            |> pivot(
                rowKey: ["_time"],
                columnKey: ["_field"],
                valueColumn: "_value"
            )
        """

        try:
            result = query_api.query(query, org=self.config.org)
            records = []
            for table in result:
                for record in table.records:
                    records.append(record.values)
            return records
        except Exception as e:
            print(f"  InfluxDB query error: {e}")
            return []

    def delete_run_data(self, run_id: str):
        if not self.client:
            self.connect()

        delete_api = self.client.delete_api()

        try:
            delete_api.delete(
                start="1970-01-01T00:00:00Z",
                stop="2099-12-31T23:59:59Z",
                predicate=f'run_id="{run_id}"',
                bucket=self.config.bucket,
                org=self.config.org,
            )
        except Exception as e:
            print(f"  InfluxDB delete error: {e}")