"""
Dividends and splits of the market price table.

Total return is rebuilt from the close and the declared dividend, the same
way for every name: the dividend is reinvested at the close of the ex-date.
When that bar is not usable, the last usable close before it is taken.

The adjusted close of the provider is not used to measure a return. On some
names it carries no dividend at all, and on one name it applies dividends
that are not on the same share basis as the price.

A return of capital that the data does not carry is read from a register
written by hand from the company's publication. Its cash is added to the
dividend of the ex-date, restated on the share basis of the prices, and only
if the split recorded that day matches the declared consolidation.

Four checks are recorded, one row each:

dividend_above_limit
    A single dividend above DIVIDEND_YIELD_LIMIT of the close. The amount
    and the price are then not comparable. A name with such a dividend
    inside the measured window leaves the books.
split_not_adjusted
    On a split day the price moves by the split factor, so the earlier
    prices were not restated as they should be. The row is recorded. The
    price is not corrected.
capital_return_added
    A return of capital of the register was added on that bar.
adjusted_close_without_dividend
    The adjusted close ignores a declared dividend. It explains why the
    adjusted close is not the basis of the returns.
"""

from __future__ import annotations

import pandas as pd

from src.config import (
    ADJUSTED_DIVIDEND_SHARE,
    DIVIDEND_YIELD_LIMIT,
    SPLIT_MINIMUM_MOVE,
)

ABOVE_LIMIT = "dividend_above_limit"
SPLIT_NOT_ADJUSTED = "split_not_adjusted"
WITHOUT_DIVIDEND = "adjusted_close_without_dividend"
CAPITAL_RETURN = "capital_return_added"
# The recorded split must equal new shares over old shares to this precision.
RATIO_TOLERANCE = 1e-4
CHECK_COLUMNS = ("symbol", "timestamp", "check", "observed", "reference_close")


def ordered_bars(prices):
    """Bars sorted by name and date, with numbers read as numbers."""
    bars = prices.copy()
    bars["symbol"] = bars["symbol"].astype(str)
    bars["timestamp"] = bars["timestamp"].astype(str).str.slice(0, 10)
    for column in ("close", "adj_close", "dividends", "stock_splits"):
        bars[column] = pd.to_numeric(bars[column], errors="coerce")
    bars["dividends"] = bars["dividends"].fillna(0.0)
    bars["stock_splits"] = bars["stock_splits"].fillna(0.0)
    if (bars["dividends"] < 0).any():
        raise RuntimeError("A declared dividend is negative.")
    return bars.sort_values(["symbol", "timestamp"], kind="mergesort")


def add_capital_returns(bars, register):
    """
    Add each declared return of capital to the dividend of its ex-date.

    The prices before the operation are restated on the consolidated shares,
    so the cash per old share is multiplied by old shares over new shares.
    Return the bars and a mask of the bars that received a return.
    """
    bars = bars.copy()
    covered = pd.Series(False, index=bars.index)
    for row in register.itertuples(index=False):
        at = bars.index[bars["symbol"].eq(row.symbol) & bars["timestamp"].eq(str(row.ex_date))]
        if len(at) != 1:
            raise RuntimeError(f"{row.symbol} has no single bar on {row.ex_date} for its return of capital.")
        declared = float(row.new_shares) / float(row.old_shares)
        recorded = float(bars.loc[at[0], "stock_splits"])
        if abs(recorded - declared) > RATIO_TOLERANCE:
            raise RuntimeError(
                f"{row.symbol} {row.ex_date}: the data records a split of {recorded}, the register declares {declared}."
            )
        if float(bars.loc[at[0], "dividends"]) != 0.0:
            raise RuntimeError(f"{row.symbol} {row.ex_date}: the data already carries a dividend. Nothing is added twice.")
        bars.loc[at[0], "dividends"] = float(row.cash_per_old_share) / declared
        covered.loc[at[0]] = True
    return bars, covered


def reference_closes(bars, usable):
    """
    For each bar, the close the dividend is reinvested at, and the usable close before it.

    The first is the bar's own close when it is usable, else the last usable one.
    """
    close = bars["close"].where(usable & bars["close"].gt(0))
    held = close.groupby(bars["symbol"]).ffill()
    previous = held.groupby(bars["symbol"]).shift(1)
    return held, previous


def dividend_factor(bars, usable):
    """Cumulated reinvestment factor: close times this factor is the total-return level."""
    held, _previous = reference_closes(bars, usable)
    step = 1.0 + (bars["dividends"] / held).where(bars["dividends"] > 0, 0.0).fillna(0.0)
    return step.groupby(bars["symbol"]).cumprod()


def find_corporate_actions(prices, usable, covered=None):
    """Every recorded check, one row per bar and check. `usable` marks the bars with a usable price."""
    bars = ordered_bars(prices)
    usable = usable.reindex(bars.index)
    held, previous = reference_closes(bars, usable)
    paid = bars["dividends"] > 0
    share = (bars["dividends"] / previous).where(paid)
    found = []

    def keep(mask, check, observed):
        rows = bars.loc[mask, ["symbol", "timestamp"]].copy()
        rows["check"] = check
        rows["observed"] = observed.loc[mask]
        rows["reference_close"] = previous.loc[mask]
        found.append(rows)

    keep(share > DIVIDEND_YIELD_LIMIT, ABOVE_LIMIT, share)

    ratio = held / previous
    split = bars["stock_splits"]
    moved = (
        split.gt(0)
        & (split - 1.0).abs().gt(SPLIT_MINIMUM_MOVE)
        & (ratio - split).abs().lt((ratio - 1.0).abs())
    )
    if covered is None:
        covered = pd.Series(False, index=bars.index)
    covered = covered.reindex(bars.index).fillna(False).astype(bool)
    keep(moved & ~covered, SPLIT_NOT_ADJUSTED, ratio)
    keep(covered, CAPITAL_RETURN, share)

    adjusted = bars["adj_close"].where(bars["adj_close"] > 0)
    adjusted_before = adjusted.groupby(bars["symbol"]).shift(1)
    applied = adjusted / adjusted_before - bars["close"] / previous
    ignored = paid & split.eq(0) & ~covered & (applied / share).lt(ADJUSTED_DIVIDEND_SHARE)
    keep(ignored, WITHOUT_DIVIDEND, share)

    table = pd.concat(found, ignore_index=True)
    return table.loc[:, list(CHECK_COLUMNS)].sort_values(
        ["check", "symbol", "timestamp"], kind="mergesort"
    ).reset_index(drop=True)
