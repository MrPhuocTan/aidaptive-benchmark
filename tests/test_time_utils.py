"""
Test Suite 7: Time Utils
Tests for the timezone-aware time utility.
"""

import pytest
from datetime import datetime, timedelta

from src.time_utils import get_local_time


class TestGetLocalTime:
    """Test get_local_time() — UTC+7 helper"""

    def test_returns_datetime(self):
        """TC-T01: Should return a datetime object"""
        result = get_local_time()
        assert isinstance(result, datetime)

    def test_roughly_utc_plus_7(self):
        """TC-T02: Should be approximately UTC+7"""
        result = get_local_time()
        utc_now = datetime.utcnow()
        diff = result - utc_now
        # Should be approximately 7 hours (allow ±30 seconds for test execution)
        expected_diff = timedelta(hours=7)
        assert abs(diff - expected_diff) < timedelta(seconds=30)

    def test_returns_naive_datetime(self):
        """TC-T03: Should return naive datetime (no tzinfo) for DB compatibility"""
        result = get_local_time()
        assert result.tzinfo is None

    def test_monotonically_increasing(self):
        """TC-T04: Two consecutive calls should be non-decreasing"""
        t1 = get_local_time()
        t2 = get_local_time()
        assert t2 >= t1
