"""Normalize outputs from different tools into unified format"""

from src.models import BenchmarkResult


class Normalizer:
    """Ensures all results follow the same schema"""

    @staticmethod
    def normalize(result: BenchmarkResult) -> BenchmarkResult:
        """Clean and validate a benchmark result"""

        # Ensure non-negative values
        if result.ttft_ms is not None and result.ttft_ms < 0:
            result.ttft_ms = None

        if result.tpot_ms is not None and result.tpot_ms < 0:
            result.tpot_ms = None

        if result.tps is not None and result.tps < 0:
            result.tps = None

        if result.itl_ms is not None and result.itl_ms < 0:
            result.itl_ms = None

        # Ensure error_rate between 0 and 1
        if result.error_rate is not None:
            result.error_rate = max(0.0, min(1.0, result.error_rate))

        # Calculate goodput if not set
        if result.goodput is None and result.tps is not None:
            if result.error_rate is not None:
                result.goodput = result.tps * (1.0 - result.error_rate)
            else:
                result.goodput = result.tps

        return result

    @staticmethod
    def is_valid(result: BenchmarkResult) -> bool:
        """Check if result has minimum required data"""
        has_any_metric = any([
            result.ttft_ms is not None,
            result.tpot_ms is not None,
            result.tps is not None,
            result.rps is not None,
            result.latency_p99_ms is not None,
        ])
        has_request_outcome = any([
            result.total_requests is not None,
            result.successful_requests is not None,
            result.failed_requests is not None,
            result.error_rate is not None,
        ])
        return has_any_metric or has_request_outcome
