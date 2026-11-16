"""
Load the three published books into the local SQLite database.

The source registry loads market data. The books are files the pipeline
writes later, so they are not in that registry. This module replaces
three tables from those files: weights, monthly returns, and the
contribution of each name. It does not compute a weight or a return.

The database file is local and is not part of the repository. A missing
published file stops the command.
"""

import sqlite3

import pandas as pd

from src.config import DATABASE_FILE, MONITORING_DATA, PORTFOLIO_DATA
from src.database.load_database import normalize_dataframe_columns


PUBLISHED_TABLES = (
    ("published_weights", PORTFOLIO_DATA / "portfolio_weights.csv"),
    ("published_returns", PORTFOLIO_DATA / "portfolio_monthly_returns.csv"),
    ("published_contributions", MONITORING_DATA / "holding_contribution.csv"),
)


def load_published_books():
    """Replace the three book tables. Return the table names and row counts."""
    if not DATABASE_FILE.exists():
        raise FileNotFoundError("The local database is absent. Run the pipeline refresh first.")
    loaded = []
    connection = sqlite3.connect(DATABASE_FILE)
    try:
        for name, path in PUBLISHED_TABLES:
            if not path.exists():
                raise FileNotFoundError(f"Published book file is absent: {path.name}")
            frame = normalize_dataframe_columns(pd.read_csv(path))
            frame.to_sql(name, connection, if_exists="replace", index=False)
            loaded.append((name, len(frame)))
        connection.commit()
    finally:
        connection.close()
    return loaded
