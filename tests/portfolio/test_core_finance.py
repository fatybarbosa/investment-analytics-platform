"""
Unit tests of the finance functions, on small series that can be checked by hand.

Nothing here reads a published file or the database. Each expected value is
written from its definition, not read from the code under test. The weights
tests cover the part of the model that the published files cannot prove on
their own: a book that trades once a quarter drifts with the market in between.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.config import (
    CURRENCY_WEIGHT_CAP,
    ISSUER_WEIGHT_CAP,
    MARKET_SHOCK_RETURN,
    SECTOR_WEIGHT_CAP,
    VOLATILITY_SHOCK_MULTIPLIER,
    ZONE_WEIGHT_CAP,
)
from src.performance.build_performance import _active, _annualized_return, _drawdown, _sortino
from src.portfolio_construction.build_portfolios import (
    drift_weights,
    measure_strategy,
    portfolio_return,
    pre_trade_weights,
    project_mandate,
)
from src.risk.build_risk import _historical_tail, _rank_count
from src.stress_testing.build_stress import _measure, _replace_tail, _scale


def months(count, start="2020-01"):
    return pd.period_range(start, periods=count, freq="M").astype(str)


# ---------------------------------------------------------------- drift of the weights

def test_drift_moves_each_line_with_its_own_return():
    weights = pd.Series([0.5, 0.3, 0.2], index=["a", "b", "c"])
    returns = pd.Series([0.10, -0.10, 0.0], index=["a", "b", "c"])
    moved = drift_weights(weights, returns)
    total = 0.55 + 0.27 + 0.20
    assert moved["a"] == pytest.approx(0.55 / total)
    assert moved["b"] == pytest.approx(0.27 / total)
    assert moved["c"] == pytest.approx(0.20 / total)
    assert moved.sum() == pytest.approx(1.0)


def test_drift_leaves_a_zero_weight_at_zero():
    moved = drift_weights(pd.Series([0.6, 0.4, 0.0], index=list("abc")), pd.Series([0.5, 0.5, 9.0], index=list("abc")))
    assert moved["c"] == 0.0


def test_drift_stops_on_a_book_with_no_value():
    with pytest.raises(RuntimeError):
        drift_weights(pd.Series([1.0], index=["a"]), pd.Series([-1.0], index=["a"]))


def test_pre_trade_weights_are_the_previous_book_moved_by_its_returns():
    index = months(3)
    held = pd.DataFrame([[0.5, 0.5], [0.5, 0.5], [0.5, 0.5]], index=index, columns=["a", "b"])
    returns = pd.DataFrame([[0.20, 0.0], [0.0, 0.0], [0.0, 0.0]], index=index, columns=["a", "b"])
    before = pre_trade_weights(held, returns)
    assert before.iloc[0].isna().all()
    assert before.iloc[1]["a"] == pytest.approx(0.6 / 1.1)
    assert before.iloc[1]["b"] == pytest.approx(0.5 / 1.1)
    # No return in the second month: nothing moved, the third month starts where the second did.
    assert before.iloc[2].to_numpy() == pytest.approx(held.iloc[1].to_numpy())


def test_a_trade_is_the_gap_between_the_drifted_book_and_the_decision():
    index = months(2)
    held = pd.DataFrame([[0.5, 0.5], [0.5, 0.5]], index=index, columns=["a", "b"])
    returns = pd.DataFrame([[0.20, 0.0], [0.0, 0.0]], index=index, columns=["a", "b"])
    before = pre_trade_weights(held, returns)
    turnover = float((held.iloc[1] - before.iloc[1]).abs().sum())
    # Equal weight looks idle on paper. After a 20% move of one line it has to trade.
    assert turnover == pytest.approx(2 * (0.6 / 1.1 - 0.5))
    assert turnover > 0.0


def test_portfolio_return_uses_the_weights_the_month_starts_with():
    index = months(2)
    returns = pd.DataFrame([[0.10, 0.00], [0.00, 0.20]], index=index, columns=["a", "b"])
    weights = pd.DataFrame([[0.5, 0.5], [0.25, 0.75]], index=index, columns=["a", "b"])
    result = portfolio_return(returns, weights)
    assert result.iloc[0] == pytest.approx(0.05)
    assert result.iloc[1] == pytest.approx(0.15)


def test_portfolio_return_stops_when_a_weight_is_missing():
    index = months(1)
    returns = pd.DataFrame([[0.1, 0.1]], index=index, columns=["a", "b"])
    weights = pd.DataFrame([[0.5, np.nan]], index=index, columns=["a", "b"])
    with pytest.raises(RuntimeError):
        portfolio_return(returns, weights)


# ---------------------------------------------------------------- the mandate caps

def test_projection_respects_every_cap_and_stays_fully_invested():
    count = 30
    sectors = ["S1"] * 10 + ["S2"] * 10 + ["S3"] * 10
    zones = ["Z1"] * 15 + ["Z2"] * 15
    currencies = ["C1"] * 10 + ["C2"] * 10 + ["C3"] * 10
    start = np.array([1.0] * 10 + [0.0] * 20)
    weights = project_mandate(start, sectors, zones, currencies)
    assert weights.sum() == pytest.approx(1.0)
    assert weights.min() >= -1e-12
    assert weights.max() <= ISSUER_WEIGHT_CAP + 1e-8
    for labels, cap in ((sectors, SECTOR_WEIGHT_CAP), (zones, ZONE_WEIGHT_CAP), (currencies, CURRENCY_WEIGHT_CAP)):
        for label in set(labels):
            picked = [index for index, value in enumerate(labels) if value == label]
            assert weights[picked].sum() <= cap + 1e-8
    assert len(weights) == count


# ---------------------------------------------------------------- performance

def test_book_statistics_follow_their_definitions():
    rng = np.random.default_rng(7)
    index = months(36)
    returns = pd.Series(rng.normal(0.006, 0.04, 36), index=index)
    risk_free = pd.Series(0.001, index=index)
    last = pd.Series([0.5, 0.3, 0.2], index=list("abc"))
    measured = measure_strategy("test", returns, risk_free, last)
    excess = returns - risk_free
    assert measured["annualized_return"] == pytest.approx(float(np.prod(1 + returns)) ** (12 / 36) - 1)
    assert measured["annualized_volatility"] == pytest.approx(float(returns.std(ddof=1)) * math.sqrt(12))
    assert measured["sharpe_ratio"] == pytest.approx(float(excess.mean() / excess.std(ddof=1)) * math.sqrt(12))
    wealth = (1 + returns).cumprod()
    assert measured["maximum_drawdown"] == pytest.approx(float((wealth / wealth.cummax() - 1).min()))
    assert measured["maximum_weight"] == pytest.approx(0.5)
    assert measured["effective_holdings"] == pytest.approx(1 / (0.25 + 0.09 + 0.04))
    assert measured["months"] == 36


def test_annualization_uses_twelve_months_not_252():
    returns = pd.Series([0.01] * 12, index=months(12))
    assert _annualized_return(returns) == pytest.approx(1.01**12 - 1)
    half_year = pd.Series([0.01] * 6, index=months(6))
    assert _annualized_return(half_year) == pytest.approx(1.01**12 - 1)


def test_drawdown_is_the_fall_from_the_running_peak():
    wealth, drawdown = _drawdown(pd.Series([0.10, -0.20, 0.05], index=months(3)))
    assert wealth.iloc[1] == pytest.approx(0.88)
    assert drawdown.min() == pytest.approx(0.88 / 1.10 - 1)
    assert drawdown.iloc[0] == 0.0


def test_a_book_that_starts_below_the_invested_unit_is_already_in_drawdown():
    _wealth, drawdown = _drawdown(pd.Series([-0.10, 0.05, 0.10], index=months(3)))
    assert drawdown.iloc[0] == pytest.approx(-0.10)
    assert drawdown.iloc[1] == pytest.approx(0.945 - 1)
    assert drawdown.iloc[2] == 0.0


def test_sortino_counts_only_months_below_the_risk_free_rate():
    excess = pd.Series([0.01, -0.02, 0.03, -0.01], index=months(4))
    ratio, below = _sortino(excess)
    deviation = math.sqrt((0.02**2 + 0.01**2) / 3)
    assert below == 2
    assert ratio == pytest.approx(float(excess.mean()) / deviation * math.sqrt(12))


def test_sortino_is_empty_when_no_month_is_below():
    ratio, below = _sortino(pd.Series([0.01, 0.02, 0.03], index=months(3)))
    assert below == 0
    assert math.isnan(ratio)


def test_tracking_error_and_information_ratio_against_a_reference():
    book = pd.Series([0.02, 0.01, -0.01, 0.03], index=months(4))
    fund = pd.Series([0.01, 0.01, 0.00, 0.02], index=months(4))
    tracking, information = _active(book, fund)
    gap = book - fund
    assert tracking == pytest.approx(float(gap.std(ddof=1)) * math.sqrt(12))
    assert information == pytest.approx(float(gap.mean() / gap.std(ddof=1)) * math.sqrt(12))


def test_the_fund_against_itself_has_no_information_ratio():
    fund = pd.Series([0.01, 0.02, -0.01], index=months(3))
    tracking, information = _active(fund, fund)
    assert tracking == 0.0
    assert math.isnan(information)


# ---------------------------------------------------------------- risk

@pytest.mark.parametrize("count, expected", [(120, 6), (119, 6), (100, 5), (21, 2), (20, 1)])
def test_the_tail_holds_the_worst_five_percent_rounded_up(count, expected):
    assert _rank_count(count) == expected


def test_value_at_risk_and_expected_shortfall_are_read_on_the_worst_months():
    values = np.linspace(-0.12, 0.10, 120)
    block = pd.DataFrame({"month": months(120), "portfolio_return": values})
    var, shortfall, tail = _historical_tail(block)
    worst = np.sort(values)[:6]
    assert var == pytest.approx(worst[-1])
    assert shortfall == pytest.approx(worst.mean())
    assert shortfall <= var
    assert list(tail["rank"]) == [1, 2, 3, 4, 5, 6]


def test_a_tie_in_the_tail_goes_to_the_older_month():
    block = pd.DataFrame({"month": months(20), "portfolio_return": [0.0] * 20})
    _, _, tail = _historical_tail(block)
    assert tail["month"].iloc[0] == months(20)[0]


# ---------------------------------------------------------------- stress

def test_a_market_shock_replaces_only_the_last_month():
    returns = pd.Series([0.01, 0.02, 0.03], index=months(3))
    shocked = _replace_tail(returns, 1, MARKET_SHOCK_RETURN)
    assert list(shocked.iloc[:2]) == [0.01, 0.02]
    assert shocked.iloc[2] == MARKET_SHOCK_RETURN
    assert returns.iloc[2] == 0.03


def test_a_shock_longer_than_the_window_is_refused():
    with pytest.raises(RuntimeError):
        _replace_tail(pd.Series([0.01, 0.02], index=months(2)), 3, -0.03)


def test_the_volatility_shock_keeps_the_mean_and_scales_the_spread():
    returns = pd.Series([0.02, -0.01, 0.04, 0.00, 0.03], index=months(5))
    scaled = _scale(returns)
    assert scaled.mean() == pytest.approx(returns.mean())
    assert scaled.std(ddof=1) == pytest.approx(VOLATILITY_SHOCK_MULTIPLIER * returns.std(ddof=1))


def test_stressed_wealth_is_the_chained_shocked_return():
    returns = pd.Series([0.05, -0.10, 0.02], index=months(3))
    risk_free = pd.Series(0.001, index=months(3))
    measured = _measure(returns, risk_free)
    assert measured["terminal_wealth"] == pytest.approx(1.05 * 0.90 * 1.02)
    assert measured["maximum_drawdown"] == pytest.approx(-0.10)
