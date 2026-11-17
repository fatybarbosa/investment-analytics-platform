"""
The name-level files must rebuild what is already published.

Contributions by name add up to the monthly return of the book and to
the sector line. Weight movements add up to the gross turnover of the
rebalance. The tests read the published files; they do not rebuild
them and they do not write.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.portfolio_construction.build_portfolios import MONTHLY_RETURNS_FILE, STRATEGY_IDS
from src.portfolio_monitoring.build_monitoring import (
    CONTRIBUTION_FILE,
    CONTRIBUTION_TOLERANCE,
    HOLDING_CONTRIBUTION_FILE,
    TURNOVER_FILE,
    WEIGHT_CHANGES_FILE,
    WEIGHTS_FILE,
)


def test_name_contributions_rebuild_the_monthly_return():
    names = pd.read_csv(HOLDING_CONTRIBUTION_FILE)
    published = pd.read_csv(MONTHLY_RETURNS_FILE)
    rebuilt = names.groupby(["strategy", "month"])["month_contribution"].sum()
    official = published.set_index(["strategy", "month"])["portfolio_return"]
    assert set(rebuilt.index) == set(official.index)
    gap = (rebuilt - official.reindex(rebuilt.index)).abs().max()
    assert gap <= CONTRIBUTION_TOLERANCE


def test_name_contributions_rebuild_the_sector_lines():
    names = pd.read_csv(HOLDING_CONTRIBUTION_FILE)
    sectors = pd.read_csv(CONTRIBUTION_FILE)
    rebuilt = names.groupby(["strategy", "month", "sector"])["month_contribution"].sum()
    official = sectors.set_index(["strategy", "month", "sector"])["month_contribution"]
    gap = (rebuilt.reindex(official.index) - official).abs().max()
    assert gap <= CONTRIBUTION_TOLERANCE


def test_cumulative_contribution_is_the_running_sum():
    names = pd.read_csv(HOLDING_CONTRIBUTION_FILE).sort_values(["strategy", "yahoo_symbol", "month"])
    running = names.groupby(["strategy", "yahoo_symbol"])["month_contribution"].cumsum()
    assert np.allclose(running.to_numpy(), names["cumulative_contribution"].to_numpy(), atol=CONTRIBUTION_TOLERANCE, rtol=0)


def test_weight_changes_rebuild_the_gross_turnover():
    changes = pd.read_csv(WEIGHT_CHANGES_FILE)
    turnover = pd.read_csv(TURNOVER_FILE)
    rebuilt = changes.groupby(["strategy", "month"])["weight_change"].apply(lambda values: values.abs().sum())
    official = turnover.set_index(["strategy", "month"])["gross_turnover"]
    for key, value in rebuilt.items():
        assert abs(value - float(official.loc[key])) <= 1e-8
    # A rebalance with no movement has no row, and its turnover is zero.
    silent = official.drop(index=rebuilt.index, errors="ignore")
    assert (silent.abs() <= 1e-8).all()


def test_weight_changes_match_the_weight_file():
    changes = pd.read_csv(WEIGHT_CHANGES_FILE)
    weights = pd.read_csv(WEIGHTS_FILE).set_index(["strategy", "month", "yahoo_symbol"])["weight"]
    for record in changes.itertuples(index=False):
        assert record.strategy in STRATEGY_IDS
        after = float(weights.get((record.strategy, record.month, record.yahoo_symbol), 0.0))
        assert abs(after - record.weight_after) <= 1e-12
        assert abs(record.weight_after - record.weight_before - record.weight_change) <= 1e-12
