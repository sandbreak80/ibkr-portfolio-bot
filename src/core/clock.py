"""US market calendar and timezone handling."""
from datetime import datetime, time
from typing import Optional

import pandas as pd
import pytz
from pandas_market_calendars import get_calendar

# Timezones
ET = pytz.timezone("America/New_York")
UTC = pytz.UTC


def get_market_calendar() -> pd.DataFrame:
    """
    Get US market calendar (XNYS).

    Returns:
        DataFrame with market calendar dates
    """
    cal = get_calendar("XNYS")
    # Get schedule for a wide date range (adjust as needed)
    schedule = cal.schedule(start_date="2015-01-01", end_date="2030-12-31")
    return schedule


def is_market_open(date: datetime, calendar: Optional[pd.DataFrame] = None) -> bool:
    """
    Check if market is open on a given date.

    Args:
        date: Date to check (ET timezone)
        calendar: Market calendar DataFrame (optional, will fetch if not provided)

    Returns:
        True if market is open
    """
    if calendar is None:
        calendar = get_market_calendar()

    # Convert to ET if needed
    if date.tzinfo is None:
        date = ET.localize(date)
    elif date.tzinfo != ET:
        date = date.astimezone(ET)

    # Check if date is in calendar
    date_only = date.date()
    market_dates = calendar.index.date if hasattr(calendar.index, "date") else [d.date() for d in calendar.index]

    return date_only in market_dates


def get_next_market_date(date: datetime, calendar: Optional[pd.DataFrame] = None) -> datetime:
    """
    Get the next market open date after the given date.

    Args:
        date: Starting date (ET timezone)
        calendar: Market calendar DataFrame (optional)

    Returns:
        Next market open date (ET timezone)
    """
    if calendar is None:
        calendar = get_market_calendar()

    # Convert to ET if needed
    if date.tzinfo is None:
        date = ET.localize(date)
    elif date.tzinfo != ET:
        date = date.astimezone(ET)

    # Find next market date
    market_dates = calendar.index
    # Convert date to pandas Timestamp (timezone-naive for comparison with calendar)
    date_ts = pd.Timestamp(date.replace(tzinfo=None))
    future_dates = market_dates[market_dates > date_ts]

    if len(future_dates) == 0:
        raise ValueError(f"No market dates found after {date}")

    return future_dates[0].to_pydatetime().replace(tzinfo=ET)


def parse_rebalance_time(time_str: str) -> time:
    """
    Parse rebalance time string (HH:MM format).

    Args:
        time_str: Time string in HH:MM format

    Returns:
        time object
    """
    hour, minute = map(int, time_str.split(":"))
    return time(hour, minute)


def get_rebalance_datetime(date: datetime, time_str: str = "15:55") -> datetime:
    """
    Get rebalance datetime for a given date and time.

    Args:
        date: Date (ET timezone)
        time_str: Time string in HH:MM format (default: 15:55)

    Returns:
        Datetime with specified time (ET timezone)
    """
    rebalance_time = parse_rebalance_time(time_str)

    # Convert to ET if needed
    if date.tzinfo is None:
        date = ET.localize(date)
    elif date.tzinfo != ET:
        date = date.astimezone(ET)

    # Combine date and time
    return datetime.combine(date.date(), rebalance_time, tzinfo=ET)


def et_to_utc(dt: datetime) -> datetime:
    """
    Convert ET datetime to UTC.

    Args:
        dt: Datetime in ET

    Returns:
        Datetime in UTC
    """
    if dt.tzinfo is None:
        dt = ET.localize(dt)
    elif dt.tzinfo != ET:
        dt = dt.astimezone(ET)

    return dt.astimezone(UTC)


def utc_to_et(dt: datetime) -> datetime:
    """
    Convert UTC datetime to ET.

    Args:
        dt: Datetime in UTC

    Returns:
        Datetime in ET
    """
    if dt.tzinfo is None:
        dt = UTC.localize(dt)
    elif dt.tzinfo != UTC:
        dt = dt.astimezone(UTC)

    return dt.astimezone(ET)


def get_current_et_time() -> datetime:
    """
    Get current time in ET.

    Returns:
        Current datetime in ET
    """
    return datetime.now(ET)
