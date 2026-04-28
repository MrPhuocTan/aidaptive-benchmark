"""
Test Suite 3: Data Normalizer
Tests that Normalizer correctly cleans, validates, and enriches BenchmarkResult.
"""

import pytest

from src.data.normalizer import Normalizer
from src.models import BenchmarkResult


class TestNormalizerNormalize:
    """Test Normalizer.normalize()"""

    def test_negative_ttft_becomes_none(self):
        """TC-N01: Negative TTFT should be nullified"""
        result = BenchmarkResult(ttft_ms=-10.0, tps=50.0)
        normalized = Normalizer.normalize(result)
        assert normalized.ttft_ms is None
        assert normalized.tps == 50.0  # Other fields untouched

    def test_negative_tpot_becomes_none(self):
        """TC-N02: Negative TPOT should be nullified"""
        result = BenchmarkResult(tpot_ms=-5.0)
        normalized = Normalizer.normalize(result)
        assert normalized.tpot_ms is None

    def test_negative_tps_becomes_none(self):
        """TC-N03: Negative TPS should be nullified"""
        result = BenchmarkResult(tps=-1.0)
        normalized = Normalizer.normalize(result)
        assert normalized.tps is None

    def test_negative_itl_becomes_none(self):
        """TC-N04: Negative ITL should be nullified"""
        result = BenchmarkResult(itl_ms=-2.0)
        normalized = Normalizer.normalize(result)
        assert normalized.itl_ms is None

    def test_error_rate_clamped_to_0_1(self):
        """TC-N05: Error rate >1 should be clamped to 1.0"""
        result = BenchmarkResult(error_rate=1.5, tps=10.0)
        normalized = Normalizer.normalize(result)
        assert normalized.error_rate == 1.0

    def test_error_rate_negative_clamped_to_0(self):
        """TC-N06: Error rate <0 should be clamped to 0.0"""
        result = BenchmarkResult(error_rate=-0.5, tps=10.0)
        normalized = Normalizer.normalize(result)
        assert normalized.error_rate == 0.0

    def test_goodput_calculated_from_tps_and_error_rate(self):
        """TC-N07: Goodput = TPS * (1 - error_rate)"""
        result = BenchmarkResult(tps=100.0, error_rate=0.1)
        normalized = Normalizer.normalize(result)
        assert normalized.goodput == pytest.approx(90.0, rel=0.01)

    def test_goodput_equals_tps_when_no_error_rate(self):
        """TC-N08: Goodput = TPS when error_rate is None"""
        result = BenchmarkResult(tps=100.0, error_rate=None)
        normalized = Normalizer.normalize(result)
        assert normalized.goodput == 100.0

    def test_goodput_not_overwritten_if_already_set(self):
        """TC-N09: Existing goodput should not be recalculated"""
        result = BenchmarkResult(tps=100.0, error_rate=0.1, goodput=85.0)
        normalized = Normalizer.normalize(result)
        assert normalized.goodput == 85.0  # Not recalculated

    def test_valid_positive_values_preserved(self):
        """TC-N10: Valid positive values should pass through unchanged"""
        result = BenchmarkResult(
            ttft_ms=120.0,
            tpot_ms=15.0,
            tps=65.0,
            itl_ms=14.0,
            error_rate=0.02,
        )
        normalized = Normalizer.normalize(result)
        assert normalized.ttft_ms == 120.0
        assert normalized.tpot_ms == 15.0
        assert normalized.tps == 65.0
        assert normalized.itl_ms == 14.0
        assert normalized.error_rate == 0.02


class TestNormalizerIsValid:
    """Test Normalizer.is_valid()"""

    def test_valid_with_tps(self):
        """TC-N11: Result with TPS is valid"""
        result = BenchmarkResult(tps=50.0)
        assert Normalizer.is_valid(result) is True

    def test_valid_with_ttft(self):
        """TC-N12: Result with TTFT is valid"""
        result = BenchmarkResult(ttft_ms=100.0)
        assert Normalizer.is_valid(result) is True

    def test_valid_with_error_rate_only(self):
        """TC-N13: Result with error_rate only is valid"""
        result = BenchmarkResult(error_rate=1.0)
        assert Normalizer.is_valid(result) is True

    def test_valid_with_total_requests_only(self):
        """TC-N14: Result with total_requests only is valid"""
        result = BenchmarkResult(total_requests=100)
        assert Normalizer.is_valid(result) is True

    def test_invalid_all_none(self):
        """TC-N15: Result with all None metrics is invalid"""
        result = BenchmarkResult(
            run_id="run_001",
            server="server1",
            tool="oha",
        )
        assert Normalizer.is_valid(result) is False

    def test_valid_with_latency_p99(self):
        """TC-N16: Result with P99 latency is valid"""
        result = BenchmarkResult(latency_p99_ms=350.0)
        assert Normalizer.is_valid(result) is True
