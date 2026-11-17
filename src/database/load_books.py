"""
Load the published book files into SQLite, so that SQL can question them.

The files are written by the portfolio, monitoring and performance phases.
This module copies them as they are, one table per file, with the prefix
`book_`. It computes nothing. The SQL files in sql/ read these tables to
check the books a second way: a sum of weights, a chained wealth, a turnover
rebuilt from the weight changes.

The tables are replaced at each load. The database is not versioned: the
tests build a temporary one from the published files.
"""

from __future__ import annotations

import pandas as pd

from src.performance.build_performance import BENCHMARK_RETURNS_FILE
from src.portfolio_construction.build_portfolios import (
    METRICS_FILE,
    MONTHLY_RETURNS_FILE,
    WEIGHTS_FILE,
)
from src.portfolio_monitoring.build_monitoring import (
    HOLDING_CONTRIBUTION_FILE,
    HOLDINGS_FILE,
    LIMIT_FILE,
    PATH_FILE,
    TURNOVER_FILE,
    WEIGHT_CHANGES_FILE,
)
from src.utils.logger import logger


BOOK_TABLES = {
    "book_weights": WEIGHTS_FILE,
    "book_returns": MONTHLY_RETURNS_FILE,
    "book_metrics": METRICS_FILE,
    "book_holdings": HOLDINGS_FILE,
    "book_contributions": HOLDING_CONTRIBUTION_FILE,
    "book_weight_changes": WEIGHT_CHANGES_FILE,
    "book_turnover": TURNOVER_FILE,
    "book_limits": LIMIT_FILE,
    "book_path": PATH_FILE,
    "fund_returns": BENCHMARK_RETURNS_FILE,
}


def load_book_tables(connection):
    """Copy every published book file into its table. Return the row counts."""
    counts = {}
    for name, path in BOOK_TABLES.items():
        if not path.exists():
            raise RuntimeError(f"The published file {path} is missing: run the pipeline first.")
        frame = pd.read_csv(path)
        frame.to_sql(name, connection, if_exists="replace", index=False)
        counts[name] = int(len(frame))
    logger.info("Book tables loaded in SQLite: %s", counts)
    return counts
