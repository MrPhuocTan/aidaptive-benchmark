"""Database repository - CRUD operations"""

from src.time_utils import get_local_time
from datetime import datetime
from typing import Optional

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.database.tables import (
    BenchmarkRun,
    BenchmarkResultRow,
    HardwareSnapshot,
    ServerComparison,
    ServerProfile,
    RunStatus,
)


class Repository:
    """Sync repository for CLI and background operations"""

    def __init__(self, session: Session):
        self.session = session

    def create_run(self, run_id: str, **kwargs) -> BenchmarkRun:
        run = BenchmarkRun(
            run_id=run_id,
            status=RunStatus.PENDING.value,
            started_at=get_local_time(),
            **kwargs,
        )
        self.session.add(run)
        self.session.commit()
        return run

    def update_run_status(self, run_id: str, status: str, **kwargs):
        run = (
            self.session.query(BenchmarkRun).filter_by(run_id=run_id).first()
        )
        if run:
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
            self.session.commit()

    def get_run(self, run_id: str) -> Optional[BenchmarkRun]:
        return (
            self.session.query(BenchmarkRun).filter_by(run_id=run_id).first()
        )

    def list_runs(self, limit: int = 50, offset: int = 0) -> list:
        return (
            self.session.query(BenchmarkRun)
            .order_by(desc(BenchmarkRun.started_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def add_result(self, result: BenchmarkResultRow):
        self.session.add(result)
        self.session.commit()

    def get_results_by_run(self, run_id: str, **filters) -> list:
        query = self.session.query(BenchmarkResultRow).filter_by(run_id=run_id)
        for key, val in filters.items():
            if val:
                query = query.filter_by(**{key: val})
        return query.order_by(BenchmarkResultRow.timestamp).all()

    def get_aggregated_results(self, run_id: str, server: str) -> dict:
        row = (
            self.session.query(
                func.avg(BenchmarkResultRow.ttft_ms).label("avg_ttft_ms"),
                func.avg(BenchmarkResultRow.tpot_ms).label("avg_tpot_ms"),
                func.avg(BenchmarkResultRow.tps).label("avg_tps"),
                func.avg(BenchmarkResultRow.rps).label("avg_rps"),
                func.avg(BenchmarkResultRow.latency_p99_ms).label("avg_p99_ms"),
                func.avg(BenchmarkResultRow.error_rate).label("avg_error_rate"),
                func.count(BenchmarkResultRow.id).label("result_count"),
            )
            .filter_by(run_id=run_id, server=server)
            .first()
        )
        return {
            "avg_ttft_ms": float(row.avg_ttft_ms) if row.avg_ttft_ms else None,
            "avg_tpot_ms": float(row.avg_tpot_ms) if row.avg_tpot_ms else None,
            "avg_tps": float(row.avg_tps) if row.avg_tps else None,
            "avg_rps": float(row.avg_rps) if row.avg_rps else None,
            "avg_p99_ms": float(row.avg_p99_ms) if row.avg_p99_ms else None,
            "avg_error_rate": float(row.avg_error_rate) if row.avg_error_rate else None,
            "result_count": row.result_count or 0,
        }

    def add_hardware_snapshot(self, snapshot: HardwareSnapshot):
        self.session.add(snapshot)
        self.session.commit()

    def add_comparison(self, comparison: ServerComparison):
        self.session.add(comparison)
        self.session.commit()


class AsyncRepository:
    """Async repository for web app"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_runs(self, limit: int = 50, offset: int = 0) -> list:
        result = await self.session.execute(
            select(BenchmarkRun)
            .order_by(desc(BenchmarkRun.started_at))
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_run(self, run_id: str) -> Optional[BenchmarkRun]:
        result = await self.session.execute(
            select(BenchmarkRun).filter_by(run_id=run_id)
        )
        return result.scalar_one_or_none()

    async def count_runs(self, status: str = "") -> int:
        stmt = select(func.count(BenchmarkRun.id))
        if status:
            stmt = stmt.filter(BenchmarkRun.status == status)
        result = await self.session.execute(stmt)
        return result.scalar()

    async def list_server_profiles(self) -> list:
        result = await self.session.execute(
            select(ServerProfile).order_by(ServerProfile.server_id, desc(ServerProfile.recorded_at))
        )
        rows = result.scalars().all()
        latest = {}
        for row in rows:
            latest.setdefault(row.server_id, row)
        return list(latest.values())

    async def get_current_running_run(self) -> Optional[BenchmarkRun]:
        result = await self.session.execute(
            select(BenchmarkRun)
            .filter_by(status="running")
            .order_by(desc(BenchmarkRun.started_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
        
    async def stop_run(self, run_id: str, status: str = "failed", error_message: str = "Stopped manually after server restart"):
        run = await self.get_run(run_id)
        if run:
            run.status = status
            run.error_message = error_message
            run.ended_at = get_local_time()
            await self.session.commit()
            return True
        return False

    async def get_results_by_run(self, run_id: str, **filters) -> list:
        stmt = select(BenchmarkResultRow).filter_by(run_id=run_id)
        for key, val in filters.items():
            if val:
                stmt = stmt.filter(
                    getattr(BenchmarkResultRow, key) == val
                )
        stmt = stmt.order_by(BenchmarkResultRow.timestamp)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_latest_hardware_metrics(self, server: str) -> Optional[HardwareSnapshot]:
        result = await self.session.execute(
            select(HardwareSnapshot)
            .filter_by(server=server)
            .order_by(desc(HardwareSnapshot.timestamp))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_hardware_metrics_by_run(self, run_id: str) -> list:
        result = await self.session.execute(
            select(HardwareSnapshot)
            .filter_by(run_id=run_id)
            .order_by(HardwareSnapshot.timestamp)
        )
        return result.scalars().all()

    async def get_comparisons_by_run(self, run_id: str) -> list:
        result = await self.session.execute(
            select(ServerComparison)
            .filter_by(run_id=run_id)
            .order_by(ServerComparison.id)
        )
        return result.scalars().all()

    async def get_run_summary_stats(self, run_id: str) -> dict:
        summary = {}
        for server in ["server1", "server2"]:
            result = await self.session.execute(
                select(
                    func.avg(BenchmarkResultRow.ttft_ms).label("avg_ttft"),
                    func.avg(BenchmarkResultRow.tpot_ms).label("avg_tpot"),
                    func.avg(BenchmarkResultRow.tps).label("avg_tps"),
                    func.avg(BenchmarkResultRow.rps).label("avg_rps"),
                    func.avg(BenchmarkResultRow.latency_p50_ms).label("avg_p50"),
                    func.avg(BenchmarkResultRow.latency_p95_ms).label("avg_p95"),
                    func.avg(BenchmarkResultRow.latency_p99_ms).label("avg_p99"),
                    func.sum(BenchmarkResultRow.total_tokens).label("total_tokens"),
                    func.sum(BenchmarkResultRow.total_requests).label("total_requests"),
                    func.sum(BenchmarkResultRow.successful_requests).label("successful_requests"),
                    func.sum(BenchmarkResultRow.failed_requests).label("failed_requests"),
                    func.avg(BenchmarkResultRow.error_rate).label("avg_error_rate"),
                    func.count(BenchmarkResultRow.id).label("count"),
                ).filter_by(run_id=run_id, server=server)
            )
            row = result.first()
            summary[server] = {
                "avg_ttft_ms": round(float(row.avg_ttft), 2) if row.avg_ttft else None,
                "avg_tpot_ms": round(float(row.avg_tpot), 2) if row.avg_tpot else None,
                "avg_tps": round(float(row.avg_tps), 2) if row.avg_tps else None,
                "avg_rps": round(float(row.avg_rps), 2) if row.avg_rps else None,
                "avg_p50_ms": round(float(row.avg_p50), 2) if row.avg_p50 else None,
                "avg_p95_ms": round(float(row.avg_p95), 2) if row.avg_p95 else None,
                "avg_p99_ms": round(float(row.avg_p99), 2) if row.avg_p99 else None,
                "total_tokens": int(row.total_tokens or 0),
                "total_requests": int(row.total_requests or 0),
                "successful_requests": int(row.successful_requests or 0),
                "failed_requests": int(row.failed_requests or 0),
                "error_rate": round(float(row.avg_error_rate), 4) if row.avg_error_rate is not None else None,
                "result_count": row.count,
            }
        return summary

    async def get_detailed_report_stats(self, run_id: str) -> dict:
        results = await self.get_results_by_run(run_id)
        
        tools_used = set()
        scenarios_used = set()
        servers_used = set()
        models_used = set()
        total_prompts_processed = 0
        
        # Breakdown: tool -> scenario -> server -> metrics
        breakdown = {}
        
        for r in results:
            if r.tool: tools_used.add(r.tool)
            if r.scenario: scenarios_used.add(r.scenario)
            if r.server: servers_used.add(r.server)
            if r.model: models_used.add(r.model)
            
            total_prompts_processed += r.total_requests or 0
            
            tool_dict = breakdown.setdefault(r.tool, {})
            scen_dict = tool_dict.setdefault(r.scenario, {})
            
            # If there are multiple records for the same tool/scenario/server, we should average them.
            # However, typically there is 1 result row per tool/scenario/server unless retries happened.
            # We will just overwrite for simplicity or assume 1 row.
            scen_dict[r.server] = {
                "tps": round(r.tps, 2) if r.tps else None,
                "rps": round(r.rps, 2) if r.rps else None,
                "ttft_ms": round(r.ttft_ms, 2) if r.ttft_ms else None,
                "latency_p99_ms": round(r.latency_p99_ms, 2) if r.latency_p99_ms else None,
                "error_rate": round(r.error_rate * 100, 2) if r.error_rate is not None else 0, # Percentage
                "total_requests": r.total_requests or 0,
            }
            
        return {
            "metadata": {
                "tools": sorted(list(tools_used)),
                "scenarios": sorted(list(scenarios_used)),
                "servers": sorted(list(servers_used)),
                "models": sorted(list(models_used)),
                "total_requests": total_prompts_processed,
            },
            "breakdown": breakdown
        }

    async def get_comparison_chart_data(self, run_id: str) -> dict:
        summary = await self.get_run_summary_stats(run_id)
        metrics = [
            ("TTFT", "avg_ttft_ms"),
            ("TPOT", "avg_tpot_ms"),
            ("TPS", "avg_tps"),
            ("RPS", "avg_rps"),
            ("P99", "avg_p99_ms"),
        ]
        return {
            "labels": [label for label, _ in metrics],
            "server1": [summary.get("server1", {}).get(key) for _, key in metrics],
            "server2": [summary.get("server2", {}).get(key) for _, key in metrics],
        }

    async def get_timeline_chart_data(self, run_id: str) -> dict:
        snapshots = await self.get_hardware_metrics_by_run(run_id)
        data = {}
        for snapshot in snapshots:
            server = data.setdefault(snapshot.server, {
                "timestamps": [],
                "gpu_util_pct": [],
                "cpu_pct": [],
                "vram_used_gb": [],
                "ram_used_gb": [],
            })
            server["timestamps"].append(snapshot.timestamp.isoformat() if snapshot.timestamp else None)
            server["gpu_util_pct"].append(snapshot.gpu_util_pct)
            server["cpu_pct"].append(snapshot.cpu_pct)
            server["vram_used_gb"].append(snapshot.vram_used_gb)
            server["ram_used_gb"].append(snapshot.ram_used_gb)
        
        return {
            "timestamps": next(iter(data.values())).get("timestamps", []) if data else [],
            "server1": data.get("server1", {}),
            "server2": data.get("server2", {}),
        }

    async def get_dashboard_chart_data(self, run_id: str) -> dict:
        from collections import defaultdict
        
        results = await self.get_results_by_run(run_id)
        
        agg = defaultdict(lambda: defaultdict(list))
        concurrencies_set = set()
        
        for r in results:
            # We group by server and concurrency
            if r.concurrency is not None:
                agg[r.server][r.concurrency].append(r)
                concurrencies_set.add(r.concurrency)
                
        concurrencies = sorted(list(concurrencies_set))
        
        def _get_val(rows, attr):
            vals = [getattr(r, attr) for r in rows if getattr(r, attr) is not None]
            return sum(vals) / len(vals) if vals else None

        chart_data = {
            "concurrencies": concurrencies,
            "ttft": {"server1": {"p50": [], "p95": [], "p99": []}, "server2": {"p50": [], "p95": [], "p99": []}},
            "itl": {"server1": {"p50": [], "p95": [], "p99": []}, "server2": {"p50": [], "p95": [], "p99": []}},
            "tps": {"server1": {"p50": [], "p95": [], "p99": []}, "server2": {"p50": [], "p95": [], "p99": []}},
            "latency": {"server1": {"p50": [], "p95": [], "p99": []}, "server2": {"p50": [], "p95": [], "p99": []}}
        }
        
        for srv in ["server1", "server2"]:
            for c in concurrencies:
                rows = agg.get(srv, {}).get(c, [])
                
                # TTFT (Assuming average is used for all percentiles if raw percentiles not available)
                ttft_avg = _get_val(rows, "ttft_ms")
                chart_data["ttft"][srv]["p50"].append(ttft_avg)
                chart_data["ttft"][srv]["p95"].append(ttft_avg)
                chart_data["ttft"][srv]["p99"].append(ttft_avg)
                
                # ITL
                itl_avg = _get_val(rows, "tpot_ms")
                chart_data["itl"][srv]["p50"].append(itl_avg)
                chart_data["itl"][srv]["p95"].append(itl_avg)
                chart_data["itl"][srv]["p99"].append(itl_avg)
                
                # TPS
                tps_avg = _get_val(rows, "tps")
                chart_data["tps"][srv]["p50"].append(tps_avg)
                chart_data["tps"][srv]["p95"].append(tps_avg)
                chart_data["tps"][srv]["p99"].append(tps_avg)
                
                # Request Latency (End-to-End)
                # Uses specific percentile fields if available, otherwise fallback to average
                chart_data["latency"][srv]["p50"].append(_get_val(rows, "latency_p50_ms"))
                chart_data["latency"][srv]["p95"].append(_get_val(rows, "latency_p95_ms"))
                chart_data["latency"][srv]["p99"].append(_get_val(rows, "latency_p99_ms"))
                
        return chart_data

    async def get_run_winner(self, run_id: str) -> Optional[str]:
        result = await self.session.execute(
            select(ServerComparison.overall_winner)
            .filter_by(run_id=run_id)
            .order_by(ServerComparison.id)
            .limit(1)
        )
        return result.scalar_one_or_none()
