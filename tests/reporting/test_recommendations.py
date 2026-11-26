"""
The recommendations and the figures they rest on.

The link of a book with the fund is checked on short series whose answer is
known by hand. The rules are checked on the published files: each branch of a
sentence must follow the figure it reads. Nothing is written.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src import config
from src.performance.build_performance import measure_comovement
from src.portfolio_construction.build_portfolios import STRATEGY_IDS
from src.portfolio_monitoring.build_monitoring import build_feasibility
from src.reporting.commentary import BOOKS, LABELS, _recommendations, perf, resolve, retained_book
from src.reporting.number_check import check_statements


def active(fund, book):
    return pd.concat(
        [pd.DataFrame({"strategy": name, "portfolio_return": book, "benchmark_return_chf": fund}) for name in STRATEGY_IDS],
        ignore_index=True,
    )


def test_a_book_that_moves_half_as_much_as_the_fund():
    fund = [0.04, -0.02, 0.06, -0.08]
    book = [0.5 * value + 0.01 for value in fund]
    row = measure_comovement(active(fund, book)).iloc[0]
    assert row["beta"] == pytest.approx(0.5)
    assert row["correlation"] == pytest.approx(1.0)
    assert row["r_squared"] == pytest.approx(1.0)
    assert (row["fund_down_months"], row["fund_up_months"]) == (2, 2)
    assert row["fund_mean_fund_down"] == pytest.approx(-0.05)
    assert row["book_mean_fund_down"] == pytest.approx(-0.015)
    assert row["fund_mean_fund_up"] == pytest.approx(0.05)
    assert row["book_mean_fund_up"] == pytest.approx(0.035)


def test_the_t_statistic_is_the_mean_gap_over_its_standard_error():
    fund = [0.01, -0.01, 0.02, -0.02]
    gap = [0.02, 0.00, 0.02, 0.00]
    book = [value + extra for value, extra in zip(fund, gap)]
    row = measure_comovement(active(fund, book)).iloc[0]
    # Mean gap 0.01, sample standard deviation sqrt(4 * 0.0001 / 3), four months.
    assert row["active_t_statistic"] == pytest.approx(0.01 / (0.0004 / 3) ** 0.5 * 2)


def test_a_fund_that_never_falls_stops_the_measure():
    with pytest.raises(RuntimeError, match="falls"):
        measure_comovement(active([0.01, 0.02, 0.03], [0.02, 0.01, 0.05]))


def holdings(counts):
    rows = [
        {"strategy": STRATEGY_IDS[0], "sector": sector, "yahoo_symbol": f"{sector}{index}", "weight": 0.01}
        for sector, count in counts.items()
        for index in range(count)
    ]
    return pd.DataFrame(rows)


def test_the_number_of_missing_names_under_the_written_cap():
    # Caps of 20 % by sector and 5 % by issuer: five sectors of four names make a whole book.
    short = build_feasibility(holdings({"A": 10, "B": 10, "C": 4, "D": 4}))
    total = short.loc[short["sector"].eq("TOTAL")].iloc[0]
    assert total["capacity_ips"] == pytest.approx(0.8)
    assert total["names_short_ips"] == 4
    full = build_feasibility(holdings({sector: 4 for sector in "ABCDE"}))
    assert full.loc[full["sector"].eq("TOTAL"), "names_short_ips"].iloc[0] == 0


@pytest.fixture(scope="module")
def advice():
    return {statement.tag: statement for statement in _recommendations()}


def test_every_recommendation_passes_the_number_check(advice):
    assert list(advice) == ["retenir", "ecarter", "marche", "attente", "secteur"]
    assert check_statements(list(advice.values()))


def test_the_proposed_book_has_the_highest_sharpe_ratio(advice):
    ratios = {book: float(resolve(perf(book, "sharpe_ratio", "raw"))) for book in BOOKS}
    chosen = max(ratios, key=ratios.get)
    assert retained_book() == chosen
    assert LABELS[chosen] in advice["retenir"].text
    for book in BOOKS:
        assert (LABELS[book] in advice["ecarter"].text) == (book != chosen)


@pytest.mark.parametrize("threshold, opening", [(1000.0, "Ne pas promettre"), (0.0, "Continuer à mesurer")])
def test_a_lead_is_called_established_only_above_the_threshold(monkeypatch, threshold, opening):
    chosen = retained_book()
    ahead = float(resolve(perf(chosen, "annualized_return"))) > float(resolve(perf("benchmark", "annualized_return")))
    monkeypatch.setattr(config, "SIGNIFICANCE_T", threshold)
    sentence = {statement.tag: statement for statement in _recommendations()}["attente"]
    assert sentence.text.startswith(opening if ahead else "Ne pas retenir")


@pytest.mark.parametrize("share, wording", [(0.0, "suit en grande partie"), (1.0, "s'écarte largement")])
def test_the_link_with_the_fund_is_worded_from_the_share_of_variance(monkeypatch, share, wording):
    monkeypatch.setattr(config, "MARKET_LINK_MAJORITY", share)
    sentence = {statement.tag: statement for statement in _recommendations()}["marche"]
    assert wording in sentence.text
