"""Test clock module."""
from datetime import datetime, time

import pandas as pd

from src.core.clock import (
    et_to_utc,
    get_current_et_time,
    get_market_calendar,
    get_next_market_date,
    get_rebalance_datetime,
    is_market_open,
    parse_rebalance_time,
    utc_to_et,
)


def test_parse_rebalance_time() -> None:
    """Test rebalance time parsing."""
    t = parse_rebalance_time("15:55")
    assert t == time(15, 55)


def test_get_rebalance_datetime() -> None:
    """Test rebalance datetime creation."""
    from pytz import timezone

    ET = timezone("America/New_York")
    date = ET.localize(datetime(2024, 1, 1))
    rebalance_dt = get_rebalance_datetime(date, "15:55")
    assert rebalance_dt.hour == 15
    assert rebalance_dt.minute == 55


def test_et_to_utc() -> None:
    """Test ET to UTC conversion."""
    from pytz import timezone

    ET = timezone("America/New_York")
    et_dt = ET.localize(datetime(2024, 1, 1, 15, 55))
    utc_dt = et_to_utc(et_dt)
    assert utc_dt.tzinfo.zone == "UTC"


def test_utc_to_et() -> None:
    """Test UTC to ET conversion."""
    from pytz import UTC

    utc_dt = UTC.localize(datetime(2024, 1, 1, 20, 55))
    et_dt = utc_to_et(utc_dt)
    assert et_dt.tzinfo.zone == "America/New_York"


def test_get_current_et_time() -> None:
    """Test getting current ET time."""
    et_time = get_current_et_time()
    assert et_time.tzinfo.zone == "America/New_York"


def test_get_market_calendar() -> None:
    """Test market calendar retrieval."""
    calendar = get_market_calendar()
    assert isinstance(calendar, pd.DataFrame)


def test_is_market_open() -> None:
    """Test market open check."""
    from pytz import timezone

    ET = timezone("America/New_York")
    # Use a known market day
    market_date = ET.localize(datetime(2024, 1, 2))  # Tuesday
    is_open = is_market_open(market_date)
    assert isinstance(is_open, bool)


def test_get_next_market_date() -> None:
    """Test getting next market date."""
    from pytz import timezone

    ET = timezone("America/New_York")
    date = ET.localize(datetime(2024, 1, 1))
    next_date = get_next_market_date(date)
    assert next_date > date
