"""
Phase 8 risk.

The monthly portfolio returns are already published. This module reads
them. It does not estimate weights again.

Volatility is the phase 5 definition. It must match
portfolio_metrics.csv. A difference stops the run.

Value at Risk is historical, at 95 percent. The returns of one strategy
are sorted from worst to best. The rank is ceil(0.05 * T), counting
from 1. VaR is the return at that rank. Expected shortfall is the mean
of the returns from rank 1 through that rank. Neither number assumes
a normal distribution.

Correlation is the Pearson correlation of the included names, on the
same months. The published summary is the mean of the off-diagonal
pairs. It describes the shared list, so it is the same for every
strategy. Weight concentration stays in phase 6.

Outputs
-------
data/07_risk/risk_by_strategy.csv
data/07_risk/var_tail.csv
data/07_risk/universe_correlation.csv
data/07_risk/correlation_matrix.csv
reports/risk/dashboard.html
"""

import math

import numpy as np
import pandas as pd

from src.config import MONTHS_PER_YEAR, RISK_DATA
from src.portfolio_construction.build_portfolios import (
    MEMBERSHIP_FILE,
    METRICS_FILE,
    MONTHLY_RETURNS_FILE,
    RETURN_LEVEL,
    STRATEGY_IDS,
    month_end_levels,
    write_csv_atomically,
)
from src.preparation.quality_treatment import MARKET_PRICES_CHF
from src.utils.logger import logger


VAR_LEVEL = 0.05
AGREEMENT = 1e-8
PAIR_LIST_FLOOR = 0.50
PAIR_LIST_TAIL = 0.70
METRICS_OUTPUT = RISK_DATA / "risk_by_strategy.csv"
TAIL_FILE = RISK_DATA / "var_tail.csv"
SUMMARY_FILE = RISK_DATA / "universe_correlation.csv"
MATRIX_FILE = RISK_DATA / "correlation_matrix.csv"
METRIC_COLUMNS = (
    "strategy",
    "months",
    "window_start",
    "window_end",
    "annualized_volatility",
    "var_95",
    "expected_shortfall_95",
)
TAIL_COLUMNS = (
    "strategy",
    "rank",
    "month",
    "portfolio_return",
)
SUMMARY_COLUMNS = (
    "names",
    "average_correlation",
    "months",
)


def _rank_count(months):
    """Number of months inside the worst 5 percent, at least one."""
    count = math.ceil(VAR_LEVEL * months)
    if count < 1:
        raise RuntimeError("The historical tail is empty.")
    return count


def _historical_tail(block):
    """VaR, expected shortfall, and the months that enter the shortfall."""
    ordered = block.sort_values(
        ["portfolio_return", "month"],
        ascending=[True, True],
        kind="mergesort",
    )
    count = _rank_count(len(ordered))
    tail = ordered.iloc[:count].copy()
    tail["rank"] = np.arange(1, count + 1)
    var = float(tail["portfolio_return"].iloc[-1])
    shortfall = float(tail["portfolio_return"].mean())
    if shortfall > var + AGREEMENT:
        raise RuntimeError("Expected shortfall is above the historical VaR.")
    return var, shortfall, tail


def measure_strategies(returns, published):
    """One risk row per strategy, stopped if volatility disagrees."""
    rows = []
    tails = []
    for strategy in STRATEGY_IDS:
        block = returns.loc[returns["strategy"].eq(strategy)].sort_values(
            "month",
            kind="mergesort",
        )
        series = block["portfolio_return"].astype(float)
        volatility = float(series.std(ddof=1) * math.sqrt(MONTHS_PER_YEAR))
        official = float(published.loc[strategy, "annualized_volatility"])
        if abs(volatility - official) > AGREEMENT:
            raise RuntimeError(
                f"{strategy} volatility does not match phase 5 "
                f"({volatility} against {official})."
            )
        var, shortfall, tail = _historical_tail(block)
        tails.append(tail.loc[:, list(TAIL_COLUMNS)])
        rows.append(
            {
                "strategy": strategy,
                "months": int(len(block)),
                "window_start": str(block["month"].iloc[0]),
                "window_end": str(block["month"].iloc[-1]),
                "annualized_volatility": official,
                "var_95": var,
                "expected_shortfall_95": shortfall,
            }
        )
    fund_row, fund_tail = _measure_benchmark()
    rows.append(fund_row)
    tails.append(fund_tail)
    return (
        pd.DataFrame(rows, columns=METRIC_COLUMNS),
        pd.concat(tails, ignore_index=True),
    )


def _measure_benchmark():
    """Historical tail of the iShares CHF NAV return, same rank rule."""
    from src.performance.build_performance import BENCHMARK_RETURNS_FILE

    benchmark = pd.read_csv(BENCHMARK_RETURNS_FILE)
    benchmark["month"] = benchmark["month"].astype(str)
    benchmark = benchmark.sort_values("month", kind="mergesort")
    block = pd.DataFrame(
        {
            "month": benchmark["month"],
            "strategy": "benchmark",
            "portfolio_return": pd.to_numeric(benchmark["benchmark_return_chf"], errors="coerce"),
        }
    )
    if block["portfolio_return"].isna().any():
        raise RuntimeError("The fund return has an empty month.")
    series = block["portfolio_return"].astype(float)
    volatility = float(series.std(ddof=1) * math.sqrt(MONTHS_PER_YEAR))
    var, shortfall, tail = _historical_tail(block)
    row = {
        "strategy": "benchmark",
        "months": int(len(block)),
        "window_start": str(block["month"].iloc[0]),
        "window_end": str(block["month"].iloc[-1]),
        "annualized_volatility": volatility,
        "var_95": var,
        "expected_shortfall_95": shortfall,
    }
    return row, tail.loc[:, list(TAIL_COLUMNS)]


def included_symbols(membership):
    """Yahoo symbols whose published decision is included, in file order."""
    included = membership.loc[
        membership["decision"].eq("included"),
        "yahoo_symbol",
    ].astype(str)
    if included.empty:
        raise RuntimeError("No included name is available for the correlation.")
    if included.duplicated().any():
        raise RuntimeError("An included symbol is repeated.")
    return included.tolist()


def shared_returns(prices, symbols, months):
    """Month-end CHF returns of the included names, on the scored months."""
    levels = month_end_levels(prices)
    first = pd.Period(str(months[0]), freq="M")
    last = pd.Period(str(months[-1]), freq="M")
    needed = pd.period_range(first - 1, last, freq="M")
    wide = levels.pivot(index="month", columns="symbol", values=RETURN_LEVEL)
    wide = wide.reindex(index=needed, columns=list(symbols))
    if wide.isna().any().any() or (wide <= 0).any().any():
        raise RuntimeError("An included name is missing a month-end CHF adjusted close.")
    returns = wide.pct_change().iloc[1:].copy()
    returns.index = returns.index.astype(str)
    if list(returns.index) != [str(month) for month in months]:
        raise RuntimeError("Asset returns do not cover the scored months.")
    flat = [
        symbol
        for symbol in returns.columns
        if float(returns[symbol].std(ddof=1)) == 0.0
    ]
    if flat:
        raise RuntimeError(
            "A constant monthly return reached the correlation: "
            + ", ".join(flat)
        )
    if not np.isfinite(returns.to_numpy()).all():
        raise RuntimeError("An asset return is not finite.")
    return returns


def correlation_tables(returns):
    """Pearson matrix and the mean of each pair once."""
    matrix = returns.corr(method="pearson")
    matrix = matrix.loc[list(returns.columns), list(returns.columns)]
    values = matrix.to_numpy(dtype=float)
    count = values.shape[0]
    if count < 2 or not np.isfinite(values).all():
        raise RuntimeError("The correlation matrix is not finite.")
    diagonal = np.diag(values)
    if float(np.max(np.abs(diagonal - 1))) > 1e-8:
        raise RuntimeError("A name is not correlated with itself at 1.")
    pairs = values[np.triu_indices(count, k=1)]
    average = float(pairs.mean())
    summary = pd.DataFrame(
        [
            {
                "names": int(count),
                "average_correlation": average,
                "months": int(len(returns)),
            }
        ],
        columns=SUMMARY_COLUMNS,
    )
    square = matrix.reset_index(names="symbol")
    return summary, square


def build_risk():
    """Write the historical tail and the shared correlation."""
    logger.info("Risk measurement started")
    returns = pd.read_csv(MONTHLY_RETURNS_FILE)
    returns["month"] = returns["month"].astype(str)
    returns["strategy"] = returns["strategy"].astype(str)
    if set(returns["strategy"]) != set(STRATEGY_IDS):
        raise RuntimeError("Monthly returns do not cover the three strategies.")
    published = pd.read_csv(METRICS_FILE).set_index("strategy")
    metrics, tail = measure_strategies(returns, published)
    months = (
        returns.loc[returns["strategy"].eq(STRATEGY_IDS[0])]
        .sort_values("month", kind="mergesort")["month"]
        .tolist()
    )
    membership = pd.read_csv(MEMBERSHIP_FILE, dtype={"yahoo_symbol": str})
    prices = pd.read_csv(
        MARKET_PRICES_CHF,
        usecols=["symbol", "timestamp", "close_chf", RETURN_LEVEL],
    )
    asset_returns = shared_returns(prices, included_symbols(membership), months)
    summary, matrix = correlation_tables(asset_returns)
    write_csv_atomically(metrics, METRICS_OUTPUT, METRIC_COLUMNS)
    write_csv_atomically(tail, TAIL_FILE, TAIL_COLUMNS)
    write_csv_atomically(summary, SUMMARY_FILE, SUMMARY_COLUMNS)
    write_csv_atomically(matrix, MATRIX_FILE, list(matrix.columns))
    logger.info("Risk metrics written to %s", METRICS_OUTPUT)
    from src.risk.dashboard import write_dashboard

    dashboard = write_dashboard()
    logger.info("Risk dashboard written to %s", dashboard)
    logger.info("Risk measurement finished")
    return {
        "metrics": METRICS_OUTPUT,
        "tail": TAIL_FILE,
        "summary": SUMMARY_FILE,
        "matrix": MATRIX_FILE,
        "dashboard": dashboard,
    }


def main():
    written = build_risk()
    print(written["metrics"])


if __name__ == "__main__":
    main()
