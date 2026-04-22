"""Aggregator - cross-tool analysis and comparison generation"""

from src.time_utils import get_local_time
from datetime import datetime
from typing import Optional

from src.database.engine import Database
from src.database.repository import Repository
from src.database.tables import (
    BenchmarkResultRow,
    ServerComparison,
)


class Aggregator:
    """Analyzes results across tools and generates comparisons"""

    def __init__(self, database: Database):
        self.database = database

    def generate_comparisons(self, run_id: str):
        """Generate all comparison records for a run"""

        session = self.database.get_sync_session()
        repo = Repository(session)

        try:
            # Overall comparison
            self._generate_overall_comparison(repo, run_id, session)

            # Per-tool comparisons
            self._generate_per_tool_comparisons(repo, run_id, session)

            # Per-scenario comparisons
            self._generate_per_scenario_comparisons(repo, run_id, session)

            session.commit()

        except Exception as e:
            session.rollback()
            print(f"  Aggregation error: {e}")
        finally:
            session.close()

    def _generate_overall_comparison(self, repo, run_id, session):
        """Generate one overall comparison for the entire run"""

        s1 = repo.get_aggregated_results(run_id, "server1")
        s2 = repo.get_aggregated_results(run_id, "server2")

        if s1["result_count"] == 0 or s2["result_count"] == 0:
            return

        comparison = ServerComparison(
            run_id=run_id,
            created_at=get_local_time(),
            environment="all",
            scenario="all",
            tool="all",
            s1_ttft_ms=s1.get("avg_ttft_ms"),
            s2_ttft_ms=s2.get("avg_ttft_ms"),
            s1_tps=s1.get("avg_tps"),
            s2_tps=s2.get("avg_tps"),
            s1_rps=s1.get("avg_rps"),
            s2_rps=s2.get("avg_rps"),
            s1_p99_ms=s1.get("avg_p99_ms"),
            s2_p99_ms=s2.get("avg_p99_ms"),
            delta_ttft_pct=self._calc_delta(
                s1.get("avg_ttft_ms"),
                s2.get("avg_ttft_ms"),
                lower_is_better=True,
            ),
            delta_tps_pct=self._calc_delta(
                s1.get("avg_tps"),
                s2.get("avg_tps"),
            ),
            delta_rps_pct=self._calc_delta(
                s1.get("avg_rps"),
                s2.get("avg_rps"),
            ),
            delta_p99_pct=self._calc_delta(
                s1.get("avg_p99_ms"),
                s2.get("avg_p99_ms"),
                lower_is_better=True,
            ),
        )

        comparison.overall_winner = self._determine_winner(comparison)
        session.add(comparison)

    def _generate_per_tool_comparisons(self, repo, run_id, session):
        """Generate comparison for each tool"""

        from sqlalchemy import distinct
        tools = (
            session.query(distinct(BenchmarkResultRow.tool))
            .filter_by(run_id=run_id)
            .all()
        )

        for (tool_name,) in tools:
            s1_results = repo.get_results_by_run(
                run_id, server="server1", tool=tool_name
            )
            s2_results = repo.get_results_by_run(
                run_id, server="server2", tool=tool_name
            )

            if not s1_results or not s2_results:
                continue

            s1_avg = self._average_results(s1_results)
            s2_avg = self._average_results(s2_results)

            comparison = ServerComparison(
                run_id=run_id,
                created_at=get_local_time(),
                tool=tool_name,
                scenario="all",
                s1_ttft_ms=s1_avg.get("ttft_ms"),
                s2_ttft_ms=s2_avg.get("ttft_ms"),
                s1_tps=s1_avg.get("tps"),
                s2_tps=s2_avg.get("tps"),
                s1_rps=s1_avg.get("rps"),
                s2_rps=s2_avg.get("rps"),
                s1_p99_ms=s1_avg.get("p99_ms"),
                s2_p99_ms=s2_avg.get("p99_ms"),
                delta_ttft_pct=self._calc_delta(
                    s1_avg.get("ttft_ms"),
                    s2_avg.get("ttft_ms"),
                    lower_is_better=True,
                ),
                delta_tps_pct=self._calc_delta(
                    s1_avg.get("tps"),
                    s2_avg.get("tps"),
                ),
            )

            comparison.overall_winner = self._determine_winner(comparison)
            session.add(comparison)

    def _generate_per_scenario_comparisons(self, repo, run_id, session):
        """Generate comparison for each scenario"""

        from sqlalchemy import distinct
        scenarios = (
            session.query(distinct(BenchmarkResultRow.scenario))
            .filter_by(run_id=run_id)
            .all()
        )

        for (scenario_name,) in scenarios:
            s1_results = repo.get_results_by_run(
                run_id, server="server1", scenario=scenario_name
            )
            s2_results = repo.get_results_by_run(
                run_id, server="server2", scenario=scenario_name
            )

            if not s1_results or not s2_results:
                continue

            s1_avg = self._average_results(s1_results)
            s2_avg = self._average_results(s2_results)

            comparison = ServerComparison(
                run_id=run_id,
                created_at=get_local_time(),
                scenario=scenario_name,
                tool="all",
                s1_ttft_ms=s1_avg.get("ttft_ms"),
                s2_ttft_ms=s2_avg.get("ttft_ms"),
                s1_tps=s1_avg.get("tps"),
                s2_tps=s2_avg.get("tps"),
                s1_rps=s1_avg.get("rps"),
                s2_rps=s2_avg.get("rps"),
                s1_p99_ms=s1_avg.get("p99_ms"),
                s2_p99_ms=s2_avg.get("p99_ms"),
                delta_ttft_pct=self._calc_delta(
                    s1_avg.get("ttft_ms"),
                    s2_avg.get("ttft_ms"),
                    lower_is_better=True,
                ),
                delta_tps_pct=self._calc_delta(
                    s1_avg.get("tps"),
                    s2_avg.get("tps"),
                ),
            )

            comparison.overall_winner = self._determine_winner(comparison)
            session.add(comparison)

    @staticmethod
    def _average_results(results: list) -> dict:
        """Calculate averages from a list of BenchmarkResultRow"""

        fields = ["ttft_ms", "tpot_ms", "tps", "rps", "latency_p99_ms"]
        averages = {}

        for field in fields:
            values = [
                getattr(r, field)
                for r in results
                if getattr(r, field) is not None
            ]
            if values:
                key = field.replace("latency_", "")
                averages[key] = sum(values) / len(values)

        return averages

    @staticmethod
    def _calc_delta(
        s1_val: Optional[float],
        s2_val: Optional[float],
        lower_is_better: bool = False,
    ) -> Optional[float]:
        """
        Calculate percentage delta.
        Positive = server2 is better.
        """
        if s1_val and s2_val and s1_val != 0:
            delta = ((s2_val - s1_val) / abs(s1_val)) * 100
            if lower_is_better:
                delta = -delta
            return round(delta, 2)
        return None

    @staticmethod
    def _determine_winner(comparison: ServerComparison) -> str:
        """Determine overall winner based on deltas"""
        score = 0

        deltas = [
            comparison.delta_ttft_pct,
            comparison.delta_tps_pct,
            comparison.delta_rps_pct,
            comparison.delta_p99_pct,
        ]

        for delta in deltas:
            if delta is not None:
                if delta > 0:
                    score += 1
                elif delta < 0:
                    score -= 1

        if score > 0:
            return "server2"
        elif score < 0:
            return "server1"
        else:
            return "tie"