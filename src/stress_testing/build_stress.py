"""
Phase 9 stress.

The monthly portfolio returns and the SARON series are already published.
This module reads them. It does not estimate weights again.

Four shocks are parameters in src/config.py. A market shock replaces the
last month. A rate shock shifts annual SARON and leaves portfolio returns
unchanged. A recession replaces the last months with one common return.
A volatility shock scales deviations from the mean. The baseline row
must match phase 5 and phase 6. A difference stops the run.
"""

import math

import numpy as np
import pandas as pd

from src.config import (
    MARKET_SHOCK_RETURN,
    MONTHS_PER_YEAR,
    RATE_SHOCK_ANNUAL_POINTS,
    RECESSION_SHOCK_MONTHS,
    RECESSION_SHOCK_RETURN,
    STRESS_DATA,
    VOLATILITY_SHOCK_MULTIPLIER,
)
from src.portfolio_construction.build_portfolios import (
    METRICS_FILE,
    MONTHLY_RETURNS_FILE,
    STRATEGY_IDS,
    WEIGHTS_FILE,
    estimation_window,
    write_csv_atomically,
)
from src.portfolio_monitoring.build_monitoring import PATH_FILE
from src.preparation.quality_treatment import SARON_TREATED
from src.utils.logger import logger


AGREEMENT = 1e-8
SHOCK_IDS = ("aucun", "marche", "taux", "recession", "volatilite")
RESULTS_FILE = STRESS_DATA / "stress_results.csv"
PATHS_FILE = STRESS_DATA / "stress_paths.csv"
RESULT_COLUMNS = (
    "strategy",
    "shock",
    "months",
    "window_start",
    "window_end",
    "terminal_wealth",
    "maximum_drawdown",
    "annualized_volatility",
    "sharpe_ratio",
)
PATH_COLUMNS = (
    "strategy",
    "shock",
    "month",
    "portfolio_return",
    "risk_free_return",
    "cumulative_wealth",
    "drawdown",
)


def _ordered(frame, strategy):
    """One strategy, in calendar order."""
    block = frame.loc[frame["strategy"].eq(strategy)].copy()
    block["month"] = block["month"].astype(str)
    block = block.sort_values("month", kind="mergesort")
    if block["month"].duplicated().any():
        raise RuntimeError(f"{strategy} repeats a month.")
    if block.empty:
        raise RuntimeError(f"{strategy} has no published months.")
    return block


def _require_weights(weights, months):
    """Every published month is fully invested. A missing weight stops the run."""
    scoped = weights.loc[weights["month"].astype(str).isin(months)]
    if scoped.empty:
        raise RuntimeError("The weight file has none of the scored months.")
    totals = scoped.groupby(["strategy", "month"], observed=True)["weight"].sum()
    gap = (totals - 1).abs()
    if float(gap.max()) > AGREEMENT:
        raise RuntimeError("A stressed month is not fully invested.")
    present = set(scoped["strategy"].astype(str))
    if present != set(STRATEGY_IDS):
        raise RuntimeError("The weight file does not cover the three strategies.")


def _risk_free(saron, points):
    """Monthly SARON after an annual percentage-point shift."""
    shifted = saron.copy()
    shifted["value"] = pd.to_numeric(shifted["value"], errors="coerce") + points
    if shifted["value"].isna().any():
        raise RuntimeError("SARON has an empty value.")
    _scored, _prices, monthly = estimation_window(shifted)
    return monthly


def _measure(returns, risk_free):
    """Wealth, drawdown, volatility and Sharpe on one shocked series."""
    rate = risk_free.reindex(returns.index)
    if rate.isna().any():
        raise RuntimeError("A stressed month has no SARON return.")
    excess = returns - rate
    growth = float(np.prod(1 + returns.to_numpy(dtype=float)))
    if not np.isfinite(growth) or growth <= 0:
        raise RuntimeError("Stressed wealth is not positive.")
    wealth = (1 + returns).cumprod()
    drawdown = wealth / wealth.cummax() - 1
    volatility = float(excess.std(ddof=1))
    if not np.isfinite(volatility) or volatility == 0:
        raise RuntimeError("Stressed excess volatility is zero.")
    return {
        "terminal_wealth": float(wealth.iloc[-1]),
        "maximum_drawdown": float(drawdown.min()),
        "annualized_volatility": float(returns.std(ddof=1) * math.sqrt(MONTHS_PER_YEAR)),
        "sharpe_ratio": float(excess.mean() / volatility * math.sqrt(MONTHS_PER_YEAR)),
        "wealth": wealth,
        "drawdown": drawdown,
        "risk_free": rate,
    }


def _replace_tail(returns, count, value):
    """Replace the last months. Earlier months stay published."""
    if count < 1 or count > len(returns):
        raise RuntimeError("The shock does not fit in the published window.")
    shocked = returns.copy()
    shocked.iloc[-count:] = value
    return shocked


def _scale(returns):
    """Keep the mean and multiply deviations from it."""
    center = float(returns.mean())
    return center + VOLATILITY_SHOCK_MULTIPLIER * (returns - center)


def _scenario(name, returns, risk_free):
    """One shock, or the published series when the name is aucun."""
    if name == "aucun":
        shocked = returns
        rate = risk_free
    elif name == "marche":
        shocked = _replace_tail(returns, 1, MARKET_SHOCK_RETURN)
        rate = risk_free
    elif name == "taux":
        shocked = returns
        rate = risk_free
    elif name == "recession":
        shocked = _replace_tail(returns, RECESSION_SHOCK_MONTHS, RECESSION_SHOCK_RETURN)
        rate = risk_free
    elif name == "volatilite":
        shocked = _scale(returns)
        rate = risk_free
    else:
        raise RuntimeError(f"Unknown shock: {name}")
    measured = _measure(shocked, rate)
    measured["returns"] = shocked
    return measured


def _check_baseline(strategy, measured, metrics, path):
    """The unshocked row must already be published."""
    official = metrics.loc[metrics["strategy"].eq(strategy)].iloc[0]
    wealth = path.loc[path["strategy"].eq(strategy), "cumulative_wealth"].astype(float)
    pairs = (
        ("sharpe_ratio", "sharpe_ratio"),
        ("maximum_drawdown", "maximum_drawdown"),
        ("annualized_volatility", "annualized_volatility"),
    )
    for published_name, measured_name in pairs:
        gap = abs(float(official[published_name]) - measured[measured_name])
        if gap > AGREEMENT:
            raise RuntimeError(f"{strategy} {published_name} does not match phase 5.")
    if abs(float(wealth.iloc[-1]) - measured["terminal_wealth"]) > AGREEMENT:
        raise RuntimeError(f"{strategy} terminal wealth does not match the path.")


def _check_identity(strategy, baseline, rate, scaled, market, recession):
    """The shocks have to do what the method says, not a nearby variant."""
    if not np.allclose(rate["returns"].to_numpy(), baseline["returns"].to_numpy(), atol=AGREEMENT):
        raise RuntimeError(f"{strategy} rate shock changed a portfolio return.")
    for name in ("terminal_wealth", "maximum_drawdown", "annualized_volatility"):
        if abs(rate[name] - baseline[name]) > AGREEMENT:
            raise RuntimeError(f"{strategy} rate shock changed {name}.")
    ratio = scaled["annualized_volatility"] / baseline["annualized_volatility"]
    if abs(ratio - VOLATILITY_SHOCK_MULTIPLIER) > AGREEMENT:
        raise RuntimeError(f"{strategy} volatility shock did not scale the deviation.")
    if abs(float(scaled["returns"].mean()) - float(baseline["returns"].mean())) > AGREEMENT:
        raise RuntimeError(f"{strategy} volatility shock moved the mean.")
    if abs(float(market["returns"].iloc[-1]) - MARKET_SHOCK_RETURN) > AGREEMENT:
        raise RuntimeError(f"{strategy} market shock did not replace the last month.")
    tail = recession["returns"].iloc[-RECESSION_SHOCK_MONTHS :]
    if float(np.max(np.abs(tail.to_numpy() - RECESSION_SHOCK_RETURN))) > AGREEMENT:
        raise RuntimeError(f"{strategy} recession shock did not replace the last months.")


def build_stress():
    """Write the shock table, the shocked paths, and the simulation page."""
    logger.info("Stress testing started")
    returns = pd.read_csv(MONTHLY_RETURNS_FILE)
    weights = pd.read_csv(WEIGHTS_FILE)
    metrics = pd.read_csv(METRICS_FILE)
    path = pd.read_csv(PATH_FILE)
    saron = pd.read_csv(SARON_TREATED, dtype=str, keep_default_na=False)
    if set(returns["strategy"].astype(str)) != set(STRATEGY_IDS):
        raise RuntimeError("Monthly returns do not cover the three strategies.")
    months = _ordered(returns, STRATEGY_IDS[0])["month"].tolist()
    _require_weights(weights, set(months))
    published_rate = _risk_free(saron, 0.0).reindex(months)
    shifted_rate = _risk_free(saron, RATE_SHOCK_ANNUAL_POINTS).reindex(months)
    if published_rate.isna().any() or shifted_rate.isna().any():
        raise RuntimeError("SARON does not cover a scored month.")
    rows = []
    paths = []
    for strategy in STRATEGY_IDS:
        block = _ordered(returns, strategy)
        if block["month"].tolist() != months:
            raise RuntimeError(f"{strategy} does not share the scored months.")
        series = pd.Series(block["portfolio_return"].to_numpy(dtype=float), index=months)
        stored_rate = pd.Series(block["risk_free_return"].to_numpy(dtype=float), index=months)
        if float(np.max(np.abs(stored_rate.to_numpy() - published_rate.to_numpy()))) > AGREEMENT:
            raise RuntimeError(f"{strategy} SARON return does not match the treated file.")
        built = {
            "aucun": _scenario("aucun", series, published_rate),
            "marche": _scenario("marche", series, published_rate),
            "taux": _scenario("taux", series, shifted_rate),
            "recession": _scenario("recession", series, published_rate),
            "volatilite": _scenario("volatilite", series, published_rate),
        }
        _check_baseline(strategy, built["aucun"], metrics, _ordered(path, strategy))
        _check_identity(
            strategy,
            built["aucun"],
            built["taux"],
            built["volatilite"],
            built["marche"],
            built["recession"],
        )
        for shock in SHOCK_IDS:
            measured = built[shock]
            rows.append(
                {
                    "strategy": strategy,
                    "shock": shock,
                    "months": int(len(months)),
                    "window_start": months[0],
                    "window_end": months[-1],
                    "terminal_wealth": measured["terminal_wealth"],
                    "maximum_drawdown": measured["maximum_drawdown"],
                    "annualized_volatility": measured["annualized_volatility"],
                    "sharpe_ratio": measured["sharpe_ratio"],
                }
            )
            paths.append(
                pd.DataFrame(
                    {
                        "strategy": strategy,
                        "shock": shock,
                        "month": months,
                        "portfolio_return": measured["returns"].to_numpy(dtype=float),
                        "risk_free_return": measured["risk_free"].to_numpy(dtype=float),
                        "cumulative_wealth": measured["wealth"].to_numpy(dtype=float),
                        "drawdown": measured["drawdown"].to_numpy(dtype=float),
                    }
                )
            )
    table = pd.DataFrame(rows, columns=list(RESULT_COLUMNS))
    trails = pd.concat(paths, ignore_index=True).loc[:, list(PATH_COLUMNS)]
    write_csv_atomically(table, RESULTS_FILE, RESULT_COLUMNS)
    write_csv_atomically(trails, PATHS_FILE, PATH_COLUMNS)
    logger.info("Stress results written to %s", RESULTS_FILE)
    from src.stress_testing.dashboard import write_dashboard

    dashboard = write_dashboard()
    logger.info("Stress dashboard written to %s", dashboard)
    logger.info("Stress testing finished")
    return {"results": RESULTS_FILE, "paths": PATHS_FILE, "dashboard": dashboard}


if __name__ == "__main__":
    build_stress()
