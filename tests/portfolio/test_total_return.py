"""
Unit tests of the total-return rule, on short series that can be checked by hand.

The published returns rest on this rule: the close, each declared dividend
reinvested on its ex-date. Nothing here reads a published file.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.config import DIVIDEND_YIELD_LIMIT
from src.quality.corporate_actions import (
    ABOVE_LIMIT,
    CAPITAL_RETURN,
    add_capital_returns,
    SPLIT_NOT_ADJUSTED,
    WITHOUT_DIVIDEND,
    dividend_factor,
    find_corporate_actions,
    ordered_bars,
)


def bars(close, dividends=None, splits=None, adjusted=None, symbol="AAA"):
    count = len(close)
    return ordered_bars(pd.DataFrame({
        "symbol": symbol,
        "timestamp": [f"2020-01-{day:02d}" for day in range(1, count + 1)],
        "close": close,
        "adj_close": adjusted if adjusted is not None else close,
        "dividends": dividends if dividends is not None else [0.0] * count,
        "stock_splits": splits if splits is not None else [0.0] * count,
    }))


def usable(frame):
    return frame["close"].notna()


def test_the_dividend_is_reinvested_at_the_close_of_its_ex_date():
    frame = bars([100.0, 98.0, 99.0], dividends=[0.0, 3.0, 0.0])
    level = frame["close"] * dividend_factor(frame, usable(frame))
    # The holder of one share has 98 plus 3 on the ex-date: the return is 101 / 100 - 1.
    assert level.iloc[1] / level.iloc[0] - 1 == pytest.approx(0.01)
    assert level.iloc[2] / level.iloc[1] - 1 == pytest.approx(99.0 / 98.0 - 1)


def test_a_dividend_on_an_unusable_bar_is_not_lost():
    frame = bars([100.0, None, 99.0], dividends=[0.0, 2.0, 0.0])
    factor = dividend_factor(frame, usable(frame))
    assert factor.iloc[2] == pytest.approx(1.02)


def test_the_factor_does_not_cross_from_one_name_to_the_next():
    frame = pd.concat([bars([100.0, 90.0], dividends=[0.0, 9.0]), bars([50.0, 50.0], symbol="BBB")], ignore_index=True)
    factor = dividend_factor(frame, usable(frame))
    assert factor.iloc[1] == pytest.approx(1.1)
    assert factor.iloc[2] == pytest.approx(1.0)


def test_a_dividend_above_the_limit_is_recorded():
    high = 100.0 * (DIVIDEND_YIELD_LIMIT + 0.01)
    low = 100.0 * (DIVIDEND_YIELD_LIMIT - 0.01)
    found = find_corporate_actions(
        bars([100.0, 90.0, 100.0], dividends=[0.0, high, 0.0], adjusted=[80.0, 90.0, 100.0]), pd.Series(True, index=range(3))
    )
    assert list(found.loc[found["check"].eq(ABOVE_LIMIT), "timestamp"]) == ["2020-01-02"]
    below = find_corporate_actions(
        bars([100.0, 93.0], dividends=[0.0, low], adjusted=[91.0, 93.0]), pd.Series(True, index=range(2))
    )
    assert below.loc[below["check"].eq(ABOVE_LIMIT)].empty


def test_a_price_that_moves_by_the_split_factor_is_recorded():
    kept = pd.Series(True, index=range(2))
    broken = find_corporate_actions(bars([100.0, 94.0], splits=[0.0, 0.9375]), kept)
    assert list(broken["check"]) == [SPLIT_NOT_ADJUSTED]
    restated = find_corporate_actions(bars([100.0, 100.5], splits=[0.0, 5.0]), kept)
    assert restated.empty


def test_an_adjusted_close_that_ignores_a_dividend_is_recorded():
    kept = pd.Series(True, index=range(2))
    ignored = find_corporate_actions(bars([100.0, 96.0], dividends=[0.0, 4.0], adjusted=[100.0, 96.0]), kept)
    assert list(ignored["check"]) == [WITHOUT_DIVIDEND]
    applied = find_corporate_actions(bars([100.0, 96.0], dividends=[0.0, 4.0], adjusted=[96.0, 96.0]), kept)
    assert applied.empty


def capital_register(ratio_new=15, ratio_old=16):
    return pd.DataFrame([{"symbol": "AAA", "ex_date": "2020-01-02", "cash_per_old_share": 6.0,
                          "new_shares": ratio_new, "old_shares": ratio_old}])


def test_a_declared_return_of_capital_is_added_on_the_basis_of_the_prices():
    # Prices before the consolidation are restated: the cash per old share is scaled by old over new.
    frame, covered = add_capital_returns(bars([103.0, 96.6], splits=[0.0, 0.9375]), capital_register())
    assert frame["dividends"].iloc[1] == pytest.approx(6.0 * 16 / 15)
    level = frame["close"] * dividend_factor(frame, usable(frame))
    assert level.iloc[1] / level.iloc[0] - 1 == pytest.approx((96.6 + 6.4) / 103.0 - 1)
    found = find_corporate_actions(frame, usable(frame), covered)
    assert list(found["check"]) == [CAPITAL_RETURN]


def test_a_register_that_does_not_match_the_recorded_split_stops():
    with pytest.raises(RuntimeError, match="register declares"):
        add_capital_returns(bars([103.0, 96.6], splits=[0.0, 0.5]), capital_register())


def test_a_negative_dividend_stops_the_preparation():
    with pytest.raises(RuntimeError, match="negative"):
        bars([100.0, 100.0], dividends=[0.0, -1.0])
