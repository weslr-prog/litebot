"""
Market Hours utilities
Purpose: Guard entry/exit logic with exchange RTH windows and handle DST/UTC conversions.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, time, timedelta
import pytz

ET = pytz.timezone("US/Eastern")
UTC = pytz.utc

REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)

@dataclass(frozen=True)
class Session:
    open_utc: datetime
    close_utc: datetime

def to_et(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = UTC.localize(dt)
    return dt.astimezone(ET)

def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = ET.localize(dt)
    return dt.astimezone(UTC)

def rth_session_for_date(d: datetime) -> Session:
    # Input can be naive or tz-aware
    et = to_et(d)
    open_et = et.replace(hour=REGULAR_OPEN.hour, minute=REGULAR_OPEN.minute, second=0, microsecond=0)
    close_et = et.replace(hour=REGULAR_CLOSE.hour, minute=REGULAR_CLOSE.minute, second=0, microsecond=0)
    return Session(open_utc=to_utc(open_et), close_utc=to_utc(close_et))

def is_regular_session_now(now: datetime | None = None) -> bool:
    now = now or datetime.utcnow().replace(tzinfo=UTC)
    sess = rth_session_for_date(now)
    return sess.open_utc <= now.astimezone(UTC) < sess.close_utc

def seconds_until_next_open(now: datetime | None = None) -> int:
    now = now or datetime.utcnow().replace(tzinfo=UTC)
    sess = rth_session_for_date(now)
    if now < sess.open_utc:
        return int((sess.open_utc - now).total_seconds())
    # Move to next calendar day in ET
    et = to_et(now) + timedelta(days=1)
    next_sess = rth_session_for_date(et)
    return int((next_sess.open_utc - now).total_seconds())

def seconds_until_close(now: datetime | None = None) -> int:
    now = now or datetime.utcnow().replace(tzinfo=UTC)
    sess = rth_session_for_date(now)
    return max(0, int((sess.close_utc - now).total_seconds()))

def clamp_to_rth(now: datetime) -> datetime:
    sess = rth_session_for_date(now)
    if now < sess.open_utc:
        return sess.open_utc
    if now > sess.close_utc:
        return sess.close_utc
    return now

from datetime import datetime, timezone, timedelta
from core.trader import get_clock

def market_status():
    """
    Returns (is_open: bool, next_open: datetime, next_close: datetime) in UTC.
    """
    clock = get_clock()
    return clock.is_open, clock.next_open, clock.next_close

def wait_seconds_until(dt_utc) -> int:
    now = datetime.now(timezone.utc)
    return max(0, int((dt_utc - now).total_seconds()))

def premarket_window(next_open: datetime, minutes_before: int = 45) -> tuple[datetime, datetime]:
    """
    Returns (start, end) UTC for a premarket window ending at next_open.
    """
    start = next_open - timedelta(minutes=minutes_before)
    return start, next_open
