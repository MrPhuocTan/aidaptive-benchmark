"""Time utilities for consistent timezone handling (+7)"""

from datetime import datetime, timedelta

def get_local_time() -> datetime:
    """Return current time in UTC+7 (naive datetime for DB compatibility)"""
    return datetime.utcnow() + timedelta(hours=7)
