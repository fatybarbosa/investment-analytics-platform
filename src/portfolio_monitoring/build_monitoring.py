"""
Phase 6 portfolio monitoring.

The three portfolios already have published weights. This module
describes the last month's book and the path of the quarterly decisions.
It does not estimate the weights again. The allocation below is the
situation at the report month. Earlier months can differ.

Sector and country come from the benchmark holdings. Exposure is the
listing currency. A country that is not in the zone map stays in the book as
"Non classé". A missing holdings row does the same. The weight is
kept in every total.

Outputs
-------
data/05_monitoring/allocation_by_holding.csv
data/05_monitoring/allocation_by_sector.csv
data/05_monitoring/allocation_by_zone.csv
data/05_monitoring/exposure.csv
data/05_monitoring/concentration.csv
data/05_monitoring/concentration_history.csv
data/05_monitoring/limit_watch.csv
data/05_monitoring/turnover.csv
data/05_monitoring/top10_positions.csv
data/05_monitoring/monthly_report.csv
data/05_monitoring/portfolio_path.csv
data/05_monitoring/sector_contribution.csv
data/05_monitoring/holding_contribution.csv
data/05_monitoring/weight_changes.csv
data/05_monitoring/mandate_feasibility.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    CAP_TOLERANCE,
    CURRENCY_WEIGHT_CAP,
    IPS_SECTOR_WEIGHT_CAP,
    ISSUER_WEIGHT_CAP,
    MAX_POSITIONS,
    MIN_POSITIONS,
    MONITORING_DATA,
    POSITION_WEIGHT_FLOOR,
    QUARTERLY_TURNOVER_CAP,
    SECTOR_WEIGHT_CAP,
    ZONE_WEIGHT_CAP,
)
from src.governance.source_registry import (
    DATASET_KEY,
    OUTPUT_FILE_KEY,
    build_resolved_registry,
    get_parameters,
)
from src.portfolio_construction.build_portfolios import (
    METRICS_FILE,
    MONTHLY_RETURNS_FILE,
    STRATEGY_IDS,
    WEIGHTS_FILE,
    estimation_window,
    load_construction_inputs,
    month_end_levels,
    pre_trade_weights,
    shared_membership,
    shared_monthly_returns,
    write_csv_atomically,
)
from src.preparation.securities_candidates import (
    WORKSHEET_PARAMETER,
    extract_worksheet_content,
    extract_worksheet_rows,
    find_header_row,
    read_text_file,
    reconstruct_holdings,
    resolve_preparation_paths,
    select_preparation_configuration,
)
from src.utils.logger import logger


TOP_POSITIONS = 10
UNCLASSIFIED = "Non classé"
CANDIDATES_OUTPUT = "security_candidates.csv"
WEIGHT_SUM_TOLERANCE = 1e-8
METRIC_TOLERANCE = 1e-6
MISSING_LABELS = {"", "--", "nan", "none"}
# Location strings published by the holdings file. A new country is
# reported as unclassified instead of being forced into a zone.
COUNTRY_ZONES = {
    "Australia": "Asie-Pacifique",
    "China": "Asie-Pacifique",
    "Hong Kong": "Asie-Pacifique",
    "India": "Asie-Pacifique",
    "Japan": "Asie-Pacifique",
    "Korea (South)": "Asie-Pacifique",
    "Malaysia": "Asie-Pacifique",
    "Singapore": "Asie-Pacifique",
    "Taiwan": "Asie-Pacifique",
    "Thailand": "Asie-Pacifique",
    "Austria": "Europe",
    "Belgium": "Europe",
    "Denmark": "Europe",
    "European Union": "Europe",
    "France": "Europe",
    "Germany": "Europe",
    "Italy": "Europe",
    "Norway": "Europe",
    "Portugal": "Europe",
    "Spain": "Europe",
    "Sweden": "Europe",
    "Switzerland": "Europe",
    "United Kingdom": "Europe",
    "Brazil": "Amériques",
    "Canada": "Amériques",
    "Chile": "Amériques",
    "Mexico": "Amériques",
    "United States": "Amériques",
    "Israel": "Moyen-Orient et Afrique",
    "Saudi Arabia": "Moyen-Orient et Afrique",
    "South Africa": "Moyen-Orient et Afrique",
}

HOLDING_COLUMNS = (
    "strategy",
    "yahoo_symbol",
    "ticker",
    "name",
    "listing_currency",
    "weight",
    "sector",
    "country",
    "zone",
    "asset_class",
    "exposure",
)
SECTOR_COLUMNS = ("strategy", "sector", "weight", "names")
ZONE_COLUMNS = ("strategy", "zone", "weight", "names")
EXPOSURE_COLUMNS = ("strategy", "exposure", "weight", "names")
CONCENTRATION_COLUMNS = (
    "strategy",
    "window_start",
    "window_end",
    "names",
    "invested_names",
    "maximum_weight",
    "top_10_weight",
    "hhi",
    "effective_holdings",
    "concentration_multiple",
)
CONCENTRATION_HISTORY_COLUMNS = (
    "month",
    "strategy",
    "names",
    "invested_names",
    "maximum_weight",
    "top_10_weight",
    "hhi",
    "effective_holdings",
    "concentration_multiple",
)
LIMIT_COLUMNS = (
    "month",
    "strategy",
    "largest_issuer",
    "largest_issuer_weight",
    "largest_sector",
    "largest_sector_weight",
    "largest_zone",
    "largest_zone_weight",
    "largest_currency",
    "largest_currency_weight",
    "issuer_over_cap",
    "sector_over_cap",
    "zone_over_cap",
    "currency_over_cap",
    "invested_names",
    "positions_outside_band",
    "rebalance_month",
    "sector_over_ips_cap",
)
FEASIBILITY_COLUMNS = (
    "sector",
    "names",
    "issuer_cap",
    "sector_cap_ips",
    "capacity_ips",
    "sector_cap_working",
    "capacity_working",
)
FEASIBILITY_FILE = MONITORING_DATA / "mandate_feasibility.csv"
TURNOVER_COLUMNS = (
    "month",
    "strategy",
    "gross_turnover",
    "over_quarterly_cap",
    "trailing_annual_turnover",
    "over_annual_cap",
)
REBALANCE_MONTHS = (1, 4, 7, 10)
QUARTERS_PER_YEAR = len(REBALANCE_MONTHS)
ANNUAL_TURNOVER_CAP = QUARTERS_PER_YEAR * QUARTERLY_TURNOVER_CAP
TOP10_COLUMNS = (
    "strategy",
    "rank",
    "yahoo_symbol",
    "ticker",
    "name",
    "weight",
    "sector",
    "zone",
    "exposure",
)
REPORT_COLUMNS = (
    "strategy",
    "report_month",
    "window_start",
    "window_end",
    "names",
    "invested_names",
    "maximum_weight",
    "top_10_weight",
    "hhi",
    "effective_holdings",
    "concentration_multiple",
    "largest_sector",
    "largest_sector_weight",
    "largest_zone",
    "largest_zone_weight",
    "largest_currency",
    "largest_currency_weight",
)
PATH_COLUMNS = (
    "month",
    "strategy",
    "portfolio_return",
    "cumulative_wealth",
    "drawdown",
)
CONTRIBUTION_COLUMNS = (
    "month",
    "strategy",
    "sector",
    "month_contribution",
    "cumulative_contribution",
)

HOLDINGS_FILE = MONITORING_DATA / "allocation_by_holding.csv"
SECTOR_FILE = MONITORING_DATA / "allocation_by_sector.csv"
ZONE_FILE = MONITORING_DATA / "allocation_by_zone.csv"
EXPOSURE_FILE = MONITORING_DATA / "exposure.csv"
CONCENTRATION_FILE = MONITORING_DATA / "concentration.csv"
CONCENTRATION_HISTORY_FILE = MONITORING_DATA / "concentration_history.csv"
LIMIT_FILE = MONITORING_DATA / "limit_watch.csv"
TURNOVER_FILE = MONITORING_DATA / "turnover.csv"
TOP10_FILE = MONITORING_DATA / "top10_positions.csv"
REPORT_FILE = MONITORING_DATA / "monthly_report.csv"
PATH_FILE = MONITORING_DATA / "portfolio_path.csv"
CONTRIBUTION_FILE = MONITORING_DATA / "sector_contribution.csv"
HOLDING_CONTRIBUTION_FILE = MONITORING_DATA / "holding_contribution.csv"
HOLDING_CONTRIBUTION_COLUMNS = (
    "month",
    "strategy",
    "yahoo_symbol",
    "name",
    "sector",
    "weight",
    "asset_return",
    "month_contribution",
    "cumulative_contribution",
)
WEIGHT_CHANGES_FILE = MONITORING_DATA / "weight_changes.csv"
WEIGHT_CHANGE_COLUMNS = (
    "month",
    "strategy",
    "yahoo_symbol",
    "name",
    "weight_before",
    "weight_after",
    "weight_change",
)
CONTRIBUTION_TOLERANCE = 1e-8


def published_label(value):
    """Keep a source label. Treat the holdings missing markers as empty."""
    text = str(value).strip()
    if text.casefold() in MISSING_LABELS:
        return ""
    return text


def zone_for(country):
    if country == "":
        return UNCLASSIFIED
    return COUNTRY_ZONES.get(country, UNCLASSIFIED)


def require_weight_sum(weights, strategy):
    total = float(weights.sum())
    if abs(total - 1) > WEIGHT_SUM_TOLERANCE:
        raise RuntimeError(
            f"{strategy} weights sum to {total}, so the allocation is not renormalized."
        )


def load_holding_classification():
    """Read sector, country and asset class from the holdings worksheet."""
    registry = build_resolved_registry()
    output_name = registry[OUTPUT_FILE_KEY].astype(str).map(
        lambda value: Path(value).name.casefold()
    )
    matched = registry.loc[output_name.eq(CANDIDATES_OUTPUT)]
    if len(matched) != 1:
        raise RuntimeError(
            "The security candidates file is not produced by exactly one active dataset."
        )
    dataset_id = matched.iloc[0][DATASET_KEY]
    configuration = select_preparation_configuration(dataset_id, registry=registry)
    parameters = get_parameters(configuration)
    if WORKSHEET_PARAMETER not in parameters:
        raise RuntimeError("The holdings worksheet name is not in the registry parameters.")
    input_path, _output_path = resolve_preparation_paths(
        configuration,
        registry=registry,
    )
    workbook = read_text_file(input_path)
    worksheet = extract_worksheet_content(workbook, parameters[WORKSHEET_PARAMETER])
    rows = extract_worksheet_rows(worksheet)
    holdings = reconstruct_holdings(rows, find_header_row(rows))
    required = ("Ticker", "Sector", "Asset Class", "Location")
    missing = [column for column in required if column not in holdings.columns]
    if missing:
        raise RuntimeError(
            "The holdings file has no classification column: " + ", ".join(missing)
        )
    classified = holdings.loc[:, list(required)].copy()
    for column in classified.columns:
        classified[column] = classified[column].map(published_label)
    if classified["Ticker"].eq("").any():
        raise RuntimeError("A holding row has no ticker, so it cannot be classified.")
    if classified["Ticker"].duplicated().any():
        raise RuntimeError("A holding ticker is repeated, so its sector is ambiguous.")
    return classified.rename(
        columns={
            "Ticker": "ticker",
            "Sector": "sector",
            "Asset Class": "asset_class",
            "Location": "country",
        }
    )


def load_published_portfolios():
    weights = pd.read_csv(
        WEIGHTS_FILE,
        dtype={"strategy": str, "yahoo_symbol": str, "ticker": str, "name": str},
    )
    metrics = pd.read_csv(METRICS_FILE, dtype={"strategy": str})
    weights["weight"] = pd.to_numeric(weights["weight"], errors="coerce")
    if weights["weight"].isna().any() or weights["weight"].lt(0).any():
        raise RuntimeError("A published weight is empty or negative.")
    if set(weights["strategy"]) != set(STRATEGY_IDS):
        raise RuntimeError("The weight file does not contain the three strategies.")
    if set(metrics["strategy"]) != set(STRATEGY_IDS):
        raise RuntimeError("The metrics file does not contain the three strategies.")
    if "month" not in weights.columns:
        raise RuntimeError("The weight file has no month.")
    weights["month"] = weights["month"].astype(str)
    if weights.duplicated(["strategy", "month", "yahoo_symbol"]).any():
        raise RuntimeError("A strategy lists the same symbol twice in one month.")
    if metrics["window_start"].nunique() != 1 or metrics["window_end"].nunique() != 1:
        raise RuntimeError("The strategies do not share one estimation window.")
    return weights, metrics


def classify_holdings(weights, classification):
    classified = weights.merge(classification, on="ticker", how="left", indicator=True)
    missing = classified.loc[classified["_merge"].ne("both"), "yahoo_symbol"]
    if not missing.empty:
        logger.warning(
            "Holdings classification missing for %s",
            ", ".join(sorted(missing.astype(str).unique())),
        )
    for column in ("sector", "country", "asset_class"):
        classified[column] = classified[column].map(published_label)
    unknown = sorted(
        {
            country
            for country in classified["country"]
            if country and country not in COUNTRY_ZONES
        }
    )
    if unknown:
        logger.warning(
            "Countries without a zone, kept as %s: %s",
            UNCLASSIFIED,
            ", ".join(unknown),
        )
    classified["sector"] = classified["sector"].map(lambda value: value or UNCLASSIFIED)
    classified["zone"] = classified["country"].map(zone_for)
    classified["country"] = classified["country"].map(lambda value: value or UNCLASSIFIED)
    classified["asset_class"] = classified["asset_class"].map(
        lambda value: value or UNCLASSIFIED
    )
    classified["exposure"] = classified["listing_currency"].map(
        lambda value: published_label(value) or UNCLASSIFIED
    )
    return classified.drop(columns="_merge")


def group_allocation(classified, key, key_column):
    frames = []
    for strategy in STRATEGY_IDS:
        group = classified.loc[classified["strategy"].eq(strategy)]
        require_weight_sum(group["weight"], strategy)
        invested = group.loc[group["weight"].gt(POSITION_WEIGHT_FLOOR)]
        grouped = (
            invested.groupby(key, as_index=False)
            .agg(weight=("weight", "sum"), names=("yahoo_symbol", "nunique"))
            .rename(columns={key: key_column})
        )
        grouped.insert(0, "strategy", strategy)
        frames.append(grouped.sort_values(["weight", key_column], ascending=[False, True]))
    return pd.concat(frames, ignore_index=True)


def build_exposure(classified):
    """Listing-currency weights. The mandate cap is on this currency, not on a bond or ETF bucket."""
    return group_allocation(classified, "exposure", "exposure")


def build_top10(classified):
    frames = []
    for strategy in STRATEGY_IDS:
        group = classified.loc[classified["strategy"].eq(strategy)].sort_values(
            ["weight", "yahoo_symbol"],
            ascending=[False, True],
        )
        chosen = group.head(TOP_POSITIONS).copy()
        chosen["rank"] = np.arange(1, len(chosen) + 1)
        frames.append(chosen)
    return pd.concat(frames, ignore_index=True)


def concentration_facts(group):
    """Herfindahl and the top 10 use every published weight, including zeros."""
    values = group["weight"].to_numpy(dtype=float)
    if values.size == 0:
        raise RuntimeError("A strategy has no weight row in a month.")
    hhi = float(np.square(values).sum())
    if hhi <= 0:
        raise RuntimeError("A month has no positive weight, so the effective number is undefined.")
    ordered = np.sort(values)[::-1]
    names = int(values.size)
    return {
        "names": names,
        "invested_names": int(np.count_nonzero(values > POSITION_WEIGHT_FLOOR)),
        "maximum_weight": float(ordered[0]),
        "top_10_weight": float(ordered[:TOP_POSITIONS].sum()),
        "hhi": hhi,
        "effective_holdings": 1.0 / hhi,
        "concentration_multiple": hhi * names,
    }


def over_cap(weight, cap):
    return int(float(weight) > float(cap) + CAP_TOLERANCE)


def outside_band(strategy, invested):
    """The 25–40 band binds the two optimized books. Equal weight is the full list."""
    if strategy == "equal_weight":
        return 0
    count = int(invested)
    return int(count < MIN_POSITIONS or count > MAX_POSITIONS)


def largest_slice(group, key):
    """Largest invested line, or the largest invested group. Ties follow the label."""
    invested = group.loc[group["weight"].gt(POSITION_WEIGHT_FLOOR)]
    if invested.empty:
        raise RuntimeError("A month has no invested line.")
    if key == "name":
        ordered = invested.sort_values(["weight", "yahoo_symbol"], ascending=[False, True])
        row = ordered.iloc[0]
        return str(row["name"]), float(row["weight"])
    totals = (
        invested.groupby(key, as_index=False)["weight"]
        .sum()
        .sort_values(["weight", key], ascending=[False, True])
    )
    row = totals.iloc[0]
    return str(row[key]), float(row["weight"])


def build_concentration_history(classified):
    frames = []
    for strategy in STRATEGY_IDS:
        book = classified.loc[classified["strategy"].eq(strategy)]
        rows = []
        for month, group in book.groupby("month", sort=True):
            facts = concentration_facts(group)
            facts["month"] = str(month)
            facts["strategy"] = strategy
            rows.append(facts)
        frames.append(pd.DataFrame(rows))
    return pd.concat(frames, ignore_index=True)


def decision_months(months):
    """The first scored month and every quarter start: the months a book may trade."""
    ordered = sorted(str(month) for month in months)
    return {ordered[0]} | {month for month in ordered if int(month[5:7]) in REBALANCE_MONTHS}


def build_limit_watch(classified):
    """One row per month. A flag is 1 when the weight the month starts with is above a cap.

    The caps are checked at each decision. Between two decisions a weight can pass a cap
    by drift alone: that is a passive breach, and `rebalance_month` tells the two apart.
    `sector_over_cap` uses the working cap of the books. `sector_over_ips_cap` uses the
    sector limit written in the IPS.
    """
    frames = []
    decisions = decision_months(classified["month"].unique())
    for strategy in STRATEGY_IDS:
        book = classified.loc[classified["strategy"].eq(strategy)]
        rows = []
        for month, group in book.groupby("month", sort=True):
            issuer, issuer_weight = largest_slice(group, "name")
            sector, sector_weight = largest_slice(group, "sector")
            zone, zone_weight = largest_slice(group, "zone")
            currency, currency_weight = largest_slice(group, "exposure")
            invested = int(np.count_nonzero(group["weight"].to_numpy(dtype=float) > POSITION_WEIGHT_FLOOR))
            rows.append(
                {
                    "month": str(month),
                    "strategy": strategy,
                    "largest_issuer": issuer,
                    "largest_issuer_weight": issuer_weight,
                    "largest_sector": sector,
                    "largest_sector_weight": sector_weight,
                    "largest_zone": zone,
                    "largest_zone_weight": zone_weight,
                    "largest_currency": currency,
                    "largest_currency_weight": currency_weight,
                    "issuer_over_cap": over_cap(issuer_weight, ISSUER_WEIGHT_CAP),
                    "sector_over_cap": over_cap(sector_weight, SECTOR_WEIGHT_CAP),
                    "zone_over_cap": over_cap(zone_weight, ZONE_WEIGHT_CAP),
                    "currency_over_cap": over_cap(currency_weight, CURRENCY_WEIGHT_CAP),
                    "invested_names": invested,
                    "positions_outside_band": outside_band(strategy, invested),
                    "rebalance_month": int(str(month) in decisions),
                    "sector_over_ips_cap": over_cap(sector_weight, IPS_SECTOR_WEIGHT_CAP),
                }
            )
        frames.append(pd.DataFrame(rows))
    return pd.concat(frames, ignore_index=True)


def build_turnover(weights, asset_returns):
    """Gross turnover of each quarterly trade, measured against the drifted book.

    A quarter's trade moves the book from where the market left it to the
    decided weights. Gross turnover is the sum of absolute weight changes,
    the definition of the quarterly cap. The first book has no predecessor.
    Inside a quarter nothing is traded: the weights must equal the previous
    month's book moved by its returns, or the run stops.
    The annual figure adds the four latest quarterly trades.
    """
    frames = []
    for strategy in STRATEGY_IDS:
        book = weights.loc[weights["strategy"].eq(strategy)]
        wide = book.pivot(index="month", columns="yahoo_symbol", values="weight").fillna(0.0).sort_index()
        wide.index = wide.index.astype(str)
        before = pre_trade_weights(wide, asset_returns)
        months = list(wide.index)
        previous_rebalance = None
        quarterly = []
        rows = []
        for month in months[1:]:
            change = float((wide.loc[month] - before.loc[month]).abs().sum())
            if int(month[5:7]) not in REBALANCE_MONTHS:
                if change > CAP_TOLERANCE:
                    raise RuntimeError(
                        f"{strategy} trades in {month}, outside a quarter start."
                    )
                continue
            if previous_rebalance is not None:
                gap = (pd.Period(month, freq="M") - pd.Period(previous_rebalance, freq="M")).n
                if gap != 3:
                    raise RuntimeError(
                        f"{strategy} rebalances in {month}, {gap} months after {previous_rebalance}."
                    )
            quarterly.append(change)
            window = quarterly[-QUARTERS_PER_YEAR:]
            complete = len(window) == QUARTERS_PER_YEAR
            annual = float(sum(window)) if complete else np.nan
            rows.append(
                {
                    "month": month,
                    "strategy": strategy,
                    "gross_turnover": change,
                    "over_quarterly_cap": int(change > QUARTERLY_TURNOVER_CAP + CAP_TOLERANCE),
                    "trailing_annual_turnover": annual,
                    "over_annual_cap": int(complete and annual > ANNUAL_TURNOVER_CAP + CAP_TOLERANCE),
                }
            )
            previous_rebalance = month
        if not rows:
            raise RuntimeError(f"{strategy} has no quarterly rebalance to measure.")
        frames.append(pd.DataFrame(rows))
    return pd.concat(frames, ignore_index=True)


def build_weight_changes(weights, turnover, asset_returns):
    """The weight of each name before and after a quarterly trade.

    `weight_before` is the weight the market left the name at, `weight_after` the
    decided weight. These are the movements of a hypothetical book. They are not
    transactions: no order was placed and no custody record exists. The absolute
    changes of a trade must add up to the gross turnover already published for
    that month. A difference stops the run.
    """
    names = weights.drop_duplicates("yahoo_symbol").set_index("yahoo_symbol")["name"].astype(str)
    frames = []
    for strategy in STRATEGY_IDS:
        wide = (
            weights.loc[weights["strategy"].eq(strategy)]
            .pivot(index="month", columns="yahoo_symbol", values="weight")
            .fillna(0.0)
            .sort_index()
        )
        wide.index = wide.index.astype(str)
        before = pre_trade_weights(wide, asset_returns)
        published = turnover.loc[turnover["strategy"].eq(strategy)].set_index("month")["gross_turnover"]
        for month in published.index:
            change = wide.loc[month] - before.loc[month]
            if abs(float(change.abs().sum()) - float(published.loc[month])) > CAP_TOLERANCE:
                raise RuntimeError(f"{strategy} weight changes of {month} do not rebuild the gross turnover.")
            moved = change.loc[change.abs() > POSITION_WEIGHT_FLOOR]
            frames.append(
                pd.DataFrame(
                    {
                        "month": month,
                        "strategy": strategy,
                        "yahoo_symbol": moved.index.astype(str),
                        "name": [names[symbol] for symbol in moved.index],
                        "weight_before": before.loc[month, moved.index].to_numpy(dtype=float),
                        "weight_after": wide.loc[month, moved.index].to_numpy(dtype=float),
                        "weight_change": moved.to_numpy(dtype=float),
                    }
                )
            )
    if not frames:
        return pd.DataFrame(columns=list(WEIGHT_CHANGE_COLUMNS))
    return pd.concat(frames, ignore_index=True)


def build_feasibility(classified_report_month):
    """Can a fully invested long-only book respect a sector cap on this list?

    A sector can hold at most its cap, and at most its number of names times the
    issuer cap. If the sectors cannot add up to the whole book, no book on the
    list respects the cap. The result is read by the reports, not typed in them.
    """
    book = classified_report_month.loc[
        classified_report_month["strategy"].eq(STRATEGY_IDS[0])
        & classified_report_month["weight"].gt(POSITION_WEIGHT_FLOOR)
    ]
    counts = book.groupby("sector")["yahoo_symbol"].nunique().sort_index()
    rows = []
    for sector, names in counts.items():
        room = float(names) * ISSUER_WEIGHT_CAP
        rows.append(
            {
                "sector": sector,
                "names": int(names),
                "issuer_cap": ISSUER_WEIGHT_CAP,
                "sector_cap_ips": IPS_SECTOR_WEIGHT_CAP,
                "capacity_ips": min(IPS_SECTOR_WEIGHT_CAP, room),
                "sector_cap_working": SECTOR_WEIGHT_CAP,
                "capacity_working": min(SECTOR_WEIGHT_CAP, room),
            }
        )
    frame = pd.DataFrame(rows, columns=list(FEASIBILITY_COLUMNS))
    total = {
        "sector": "TOTAL",
        "names": int(frame["names"].sum()),
        "issuer_cap": ISSUER_WEIGHT_CAP,
        "sector_cap_ips": IPS_SECTOR_WEIGHT_CAP,
        "capacity_ips": float(frame["capacity_ips"].sum()),
        "sector_cap_working": SECTOR_WEIGHT_CAP,
        "capacity_working": float(frame["capacity_working"].sum()),
    }
    return pd.concat([frame, pd.DataFrame([total])], ignore_index=True)


def build_concentration(history, metrics):
    """The report month of the history, checked against the phase 5 metrics."""
    rows = []
    indexed = metrics.set_index("strategy")
    for strategy in STRATEGY_IDS:
        published = indexed.loc[strategy]
        month = str(published["window_end"])
        matched = history.loc[
            history["strategy"].eq(strategy) & history["month"].astype(str).eq(month)
        ]
        if len(matched) != 1:
            raise RuntimeError(f"{strategy} has no concentration row for {month}.")
        facts = matched.iloc[0]
        if int(published["names"]) != int(facts["names"]):
            raise RuntimeError(f"{strategy} name count does not match the weight file.")
        if abs(float(published["maximum_weight"]) - float(facts["maximum_weight"])) > METRIC_TOLERANCE:
            raise RuntimeError(f"{strategy} maximum weight does not match phase 5.")
        if abs(float(published["effective_holdings"]) - float(facts["effective_holdings"])) > METRIC_TOLERANCE:
            raise RuntimeError(f"{strategy} effective holdings do not match phase 5.")
        rows.append(
            {
                "strategy": strategy,
                "window_start": published["window_start"],
                "window_end": published["window_end"],
                "names": int(facts["names"]),
                "invested_names": int(facts["invested_names"]),
                "maximum_weight": float(facts["maximum_weight"]),
                "top_10_weight": float(facts["top_10_weight"]),
                "hhi": float(facts["hhi"]),
                "effective_holdings": float(facts["effective_holdings"]),
                "concentration_multiple": float(facts["concentration_multiple"]),
            }
        )
    return pd.DataFrame(rows)


def largest_group(table, strategy, key):
    group = table.loc[table["strategy"].eq(strategy)].sort_values(
        ["weight", key],
        ascending=[False, True],
    )
    row = group.iloc[0]
    return str(row[key]), float(row["weight"])


def build_monthly_report(concentration, sectors, zones, exposure):
    rows = []
    for strategy in STRATEGY_IDS:
        facts = concentration.loc[concentration["strategy"].eq(strategy)].iloc[0]
        sector, sector_weight = largest_group(sectors, strategy, "sector")
        zone, zone_weight = largest_group(zones, strategy, "zone")
        currency, currency_weight = largest_group(exposure, strategy, "exposure")
        rows.append(
            {
                "strategy": strategy,
                "report_month": facts["window_end"],
                "window_start": facts["window_start"],
                "window_end": facts["window_end"],
                "names": int(facts["names"]),
                "invested_names": int(facts["invested_names"]),
                "maximum_weight": float(facts["maximum_weight"]),
                "top_10_weight": float(facts["top_10_weight"]),
                "hhi": float(facts["hhi"]),
                "effective_holdings": float(facts["effective_holdings"]),
                "concentration_multiple": float(facts["concentration_multiple"]),
                "largest_sector": sector,
                "largest_sector_weight": sector_weight,
                "largest_zone": zone,
                "largest_zone_weight": zone_weight,
                "largest_currency": currency,
                "largest_currency_weight": currency_weight,
            }
        )
    return pd.DataFrame(rows)


def shared_asset_returns():
    """Rebuild the scored monthly CHF returns already used to publish the portfolios."""
    prices, universe, saron = load_construction_inputs()
    levels = month_end_levels(prices)
    scored_months, price_months, _risk_free = estimation_window(saron)
    membership = shared_membership(universe, levels, price_months)
    history = shared_monthly_returns(
        levels,
        membership,
        pd.period_range(price_months[0] + 1, price_months[-1], freq="M"),
        price_months,
    )
    return history.loc[[str(month) for month in scored_months]]


def build_time_series(classified, weight_history, asset_returns):
    """Path of the monthly mandate weights, and the additive contribution of each sector and name.

    The contribution of a name in a month is its weight times its CHF return.
    The names of a month add up to the published portfolio return, and the
    names of a sector add up to the sector line. The cumulative column is the
    running sum of the monthly contributions. It is not compounded.
    """
    published = pd.read_csv(MONTHLY_RETURNS_FILE, dtype={"strategy": str, "month": str})
    sector_of = (
        classified.drop_duplicates("yahoo_symbol").set_index("yahoo_symbol")["sector"].astype(str)
    )
    name_of = (
        weight_history.drop_duplicates("yahoo_symbol").set_index("yahoo_symbol")["name"].astype(str)
    )
    path_frames = []
    contribution_frames = []
    holding_frames = []
    for strategy in STRATEGY_IDS:
        weight_symbols = set(
            weight_history.loc[weight_history["strategy"].eq(strategy), "yahoo_symbol"].astype(str)
        )
        # The return panel is every complete CHF history. The book is the Eligible part of it.
        columns = [column for column in asset_returns.columns if column in weight_symbols]
        if len(columns) != len(weight_symbols):
            raise RuntimeError(f"{strategy} has a weight with no CHF return.")
        panel = (
            weight_history.loc[weight_history["strategy"].eq(strategy)]
            .pivot(index="month", columns="yahoo_symbol", values="weight")
            .reindex(index=asset_returns.index, columns=columns)
        )
        if panel.isna().any().any():
            raise RuntimeError(f"{strategy} is missing a weight on a scored month.")
        contributed = asset_returns.loc[:, columns].mul(panel)
        contributed.index = contributed.index.astype(str)
        total = contributed.sum(axis=1)
        official = (
            published.loc[published["strategy"].eq(strategy)]
            .set_index("month")["portfolio_return"]
            .reindex(total.index)
        )
        if official.isna().any() or not np.allclose(
            total.to_numpy(),
            official.to_numpy(),
            atol=CONTRIBUTION_TOLERANCE,
            rtol=0,
        ):
            raise RuntimeError(f"{strategy} contributions do not rebuild the monthly return.")
        wealth = (1 + total).cumprod()
        path_frames.append(
            pd.DataFrame(
                {
                    "month": total.index,
                    "strategy": strategy,
                    "portfolio_return": total.to_numpy(),
                    "cumulative_wealth": wealth.to_numpy(),
                    "drawdown": (wealth / wealth.cummax().clip(lower=1.0) - 1).to_numpy(),
                }
            )
        )
        contributed.index.name = "month"
        contributed.columns.name = "yahoo_symbol"
        melted = contributed.stack().rename("month_contribution").reset_index()
        melted["sector"] = melted["yahoo_symbol"].map(sector_of)
        if melted["sector"].isna().any():
            raise RuntimeError("A name in the return panel has no sector.")
        by_name = melted.copy()
        by_name["weight"] = panel.set_axis(contributed.index).stack().to_numpy(dtype=float)
        by_name["asset_return"] = (
            asset_returns.loc[:, columns].set_axis(contributed.index).stack().to_numpy(dtype=float)
        )
        by_name["name"] = by_name["yahoo_symbol"].map(name_of)
        by_name = by_name.sort_values(["yahoo_symbol", "month"], kind="mergesort")
        by_name["cumulative_contribution"] = by_name.groupby("yahoo_symbol")["month_contribution"].cumsum()
        by_name.insert(1, "strategy", strategy)
        rebuilt = by_name.groupby("month")["month_contribution"].sum().reindex(total.index)
        if not np.allclose(rebuilt.to_numpy(), official.to_numpy(), atol=CONTRIBUTION_TOLERANCE, rtol=0):
            raise RuntimeError(f"{strategy} name contributions do not rebuild the monthly return.")
        holding_frames.append(by_name.sort_values(["month", "yahoo_symbol"], kind="mergesort"))
        grouped = melted.groupby(["month", "sector"], as_index=False)["month_contribution"].sum()
        kept = grouped.groupby("sector")["month_contribution"].transform(
            lambda values: values.abs().max() > POSITION_WEIGHT_FLOOR
        )
        grouped = grouped.loc[kept].sort_values(["sector", "month"])
        grouped["cumulative_contribution"] = grouped.groupby("sector")["month_contribution"].cumsum()
        grouped.insert(1, "strategy", strategy)
        contribution_frames.append(grouped)
    from src.performance.build_performance import BENCHMARK_RETURNS_FILE

    published_fund = pd.read_csv(BENCHMARK_RETURNS_FILE).sort_values("month", kind="mergesort")
    book_months = path_frames[0]["month"].astype(str).tolist()
    if published_fund["month"].astype(str).tolist() != book_months:
        raise RuntimeError("The fund path does not share the book months.")
    fund_return = published_fund["benchmark_return_chf"].astype(float)
    fund_wealth = (1 + fund_return).cumprod()
    path_frames.append(
        pd.DataFrame(
            {
                "month": book_months,
                "strategy": "benchmark",
                "portfolio_return": fund_return.to_numpy(),
                "cumulative_wealth": fund_wealth.to_numpy(),
                "drawdown": (fund_wealth / fund_wealth.cummax().clip(lower=1.0) - 1).to_numpy(),
            }
        )
    )
    return (
        pd.concat(path_frames, ignore_index=True),
        pd.concat(contribution_frames, ignore_index=True),
        pd.concat(holding_frames, ignore_index=True),
    )


def build_monitoring():
    """Publish the report-month book, and the concentration and caps of every month."""
    logger.info("Portfolio monitoring started")
    weights, metrics = load_published_portfolios()
    report_month = str(metrics["window_end"].iloc[0])
    if weights.loc[weights["month"].eq(report_month)].empty:
        raise RuntimeError("The weight file has no row for the report month.")
    classification = load_holding_classification()
    classified_all = classify_holdings(weights, classification)
    classified = classified_all.loc[classified_all["month"].eq(report_month)].copy()
    sectors = group_allocation(classified, "sector", "sector")
    zones = group_allocation(classified, "zone", "zone")
    exposure = build_exposure(classified)
    history = build_concentration_history(classified_all)
    limits = build_limit_watch(classified_all)
    asset_returns = shared_asset_returns()
    turnover = build_turnover(weights, asset_returns)
    concentration = build_concentration(history, metrics)
    top10 = build_top10(classified)
    report = build_monthly_report(concentration, sectors, zones, exposure)
    for strategy in STRATEGY_IDS:
        watched = limits.loc[
            limits["strategy"].eq(strategy) & limits["month"].eq(report_month)
        ].iloc[0]
        published = report.loc[report["strategy"].eq(strategy)].iloc[0]
        pairs = (
            ("largest_sector", "largest_sector_weight"),
            ("largest_zone", "largest_zone_weight"),
            ("largest_currency", "largest_currency_weight"),
        )
        for label, amount in pairs:
            if str(watched[label]) != str(published[label]):
                raise RuntimeError(f"{strategy} {label} disagrees with the monthly report.")
            if abs(float(watched[amount]) - float(published[amount])) > CAP_TOLERANCE:
                raise RuntimeError(f"{strategy} {amount} disagrees with the monthly report.")
    path, contributions, holding_contributions = build_time_series(classified, weights, asset_returns)
    by_sector = holding_contributions.groupby(["strategy", "month", "sector"])["month_contribution"].sum()
    published_sector = contributions.set_index(["strategy", "month", "sector"])["month_contribution"]
    if (by_sector.reindex(published_sector.index) - published_sector).abs().max() > CONTRIBUTION_TOLERANCE:
        raise RuntimeError("Name contributions do not rebuild the sector contributions.")
    weight_changes = build_weight_changes(weights, turnover, asset_returns)
    feasibility = build_feasibility(classified_all.loc[classified_all["month"].eq(report_month)])
    outputs = {
        "holdings": (classified, HOLDINGS_FILE, HOLDING_COLUMNS),
        "sectors": (sectors, SECTOR_FILE, SECTOR_COLUMNS),
        "zones": (zones, ZONE_FILE, ZONE_COLUMNS),
        "exposure": (exposure, EXPOSURE_FILE, EXPOSURE_COLUMNS),
        "concentration": (concentration, CONCENTRATION_FILE, CONCENTRATION_COLUMNS),
        "concentration_history": (
            history,
            CONCENTRATION_HISTORY_FILE,
            CONCENTRATION_HISTORY_COLUMNS,
        ),
        "limits": (limits, LIMIT_FILE, LIMIT_COLUMNS),
        "turnover": (turnover, TURNOVER_FILE, TURNOVER_COLUMNS),
        "top10": (top10, TOP10_FILE, TOP10_COLUMNS),
        "report": (report, REPORT_FILE, REPORT_COLUMNS),
        "path": (path, PATH_FILE, PATH_COLUMNS),
        "contributions": (contributions, CONTRIBUTION_FILE, CONTRIBUTION_COLUMNS),
        "holding_contributions": (
            holding_contributions,
            HOLDING_CONTRIBUTION_FILE,
            HOLDING_CONTRIBUTION_COLUMNS,
        ),
        "weight_changes": (weight_changes, WEIGHT_CHANGES_FILE, WEIGHT_CHANGE_COLUMNS),
        "feasibility": (feasibility, FEASIBILITY_FILE, FEASIBILITY_COLUMNS),
    }
    written = {}
    for name, (dataframe, path, columns) in outputs.items():
        write_csv_atomically(dataframe, path, columns)
        written[name] = path
        logger.info("Monitoring output %s written to %s (%s rows)", name, path, len(dataframe))
    from src.portfolio_monitoring.dashboard import write_dashboard

    written["dashboard"] = write_dashboard()
    logger.info("Monitoring dashboard written to %s", written["dashboard"])
    logger.info(
        "Portfolio monitoring finished: report month %s",
        report["report_month"].iloc[0],
    )
    return written


def main():
    written = build_monitoring()
    print(written["report"])


if __name__ == "__main__":
    main()
