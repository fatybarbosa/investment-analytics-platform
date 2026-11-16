"""
Phase 11. Tables and figures shared by the PDF report and the deck.

A table is returned with a Statement that lists the fact behind every
printed cell, so the number check covers the tables too. A figure is
drawn straight from the published CSV files. Its tick labels are part
of the picture, not of the checked text.

Series colours are the first three categorical slots of the project
palette, in a fixed order. The fund is the reference: grey, dashed.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.config import EXECUTIVE_REPORTS, PROJECT_ROOT
from src.reporting.commentary import (
    ANNEX,
    BOOKS,
    FUND,
    LABELS,
    LIMITS,
    PATH,
    PENDING,
    QUALITY,
    SHOCK_LABELS,
    TAIL,
    TOLERANCE,
    config,
    perf,
    reconciliation,
    report,
    risk,
    stress,
)
from src.reporting.number_check import Draft, fact, resolve


FIGURES_DIR = EXECUTIVE_REPORTS / "figures"
SERIES_COLORS = {
    "equal_weight": "#2a78d6",
    "minimum_volatility": "#eb6834",
    "maximum_sharpe": "#1baf7a",
    "benchmark": "#52514e",
}
INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#ffffff"
NOT_DEFINED = "n. d."


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------

def _table(section, header, rows, draft):
    text = " | ".join(" | ".join(row) for row in rows)
    return header, rows, draft.done(section, text, "tableau")


def performance_table():
    d = Draft()
    header = ["Série", "Rendement annualisé", "Volatilité", "Sharpe", "Sortino", "Drawdown maximal", "Écart de suivi", "Ratio d'information"]
    rows = []
    for series in BOOKS + (FUND,):
        is_fund = series == FUND
        rows.append([
            LABELS[series],
            d.pct(perf(series, "annualized_return")),
            d.pct(perf(series, "annualized_volatility")),
            d.num(perf(series, "sharpe_ratio", "raw")),
            d.num(perf(series, "sortino_ratio", "raw")),
            d.pct(perf(series, "maximum_drawdown")),
            NOT_DEFINED if is_fund else d.pct(perf(series, "tracking_error")),
            NOT_DEFINED if is_fund else d.num(perf(series, "information_ratio", "raw")),
        ])
    return _table("tableau performance", header, rows, d)


def risk_table():
    d = Draft()
    header = ["Série", "Volatilité annualisée", "VaR mensuelle", "Expected shortfall mensuel", "Pire mois", "Rendement du pire mois"]
    rows = []
    for series in BOOKS + (FUND,):
        worst = {"strategy": series, "rank": 1}
        rows.append([
            LABELS[series],
            d.pct(risk(series, "annualized_volatility")),
            d.pct(risk(series, "var_95")),
            d.pct(risk(series, "expected_shortfall_95")),
            d.text(fact(TAIL, "month", worst, scale="text")),
            d.pct(fact(TAIL, "portfolio_return", worst, scale="ratio")),
        ])
    return _table("tableau risque", header, rows, d)


def stress_table(column="terminal_wealth"):
    d = Draft()
    shocks = ("aucun", "marche", "taux", "recession", "volatilite")
    header = ["Livre"] + [SHOCK_LABELS[shock] for shock in shocks]
    rows = []
    for book in BOOKS:
        cells = [LABELS[book]]
        for shock in shocks:
            item = stress(book, shock, column, "ratio" if column != "terminal_wealth" and column != "sharpe_ratio" else "raw")
            cells.append(d.pct(item) if item.scale == "ratio" else d.num(item))
        rows.append(cells)
    return _table(f"tableau chocs {column}", header, rows, d)


def shock_definitions():
    """The four written shocks, from src/config.py."""
    d = Draft()
    rows = [
        ["Marché", f"Le dernier mois est remplacé par un rendement de {d.pct(config('MARKET_SHOCK_RETURN'), 0)}."],
        ["Taux", f"Le SARON annuel monte de {d.num(config('RATE_SHOCK_ANNUAL_POINTS', 'raw'), 0)} points. Le rendement du portefeuille ne change pas, le Sharpe baisse."],
        ["Récession", f"Les {d.count(config('RECESSION_SHOCK_MONTHS', 'raw'))} derniers mois sont remplacés par {d.pct(config('RECESSION_SHOCK_RETURN'), 0)} chacun."],
        ["Volatilité", f"Les écarts à la moyenne sont multipliés par {d.num(config('VOLATILITY_SHOCK_MULTIPLIER', 'raw'), 1)}. La moyenne est conservée."],
    ]
    return _table("définition des chocs", ["Choc", "Ce qui est appliqué"], rows, d)


def limits_table(cap_label="Plafond du mandat", span_word="à"):
    d = Draft()
    header = ["Livre", "Lignes investies", "Poids maximal", "Premier secteur", "Première zone", "Première devise"]
    rows = []
    for book in BOOKS:
        rows.append([
            LABELS[book],
            d.count(report(book, "invested_names", "raw")),
            d.pct(report(book, "maximum_weight")),
            f"{d.label(resolve(report(book, 'largest_sector', 'text')))} {d.pct(report(book, 'largest_sector_weight'))}",
            f"{d.label(resolve(report(book, 'largest_zone', 'text')))} {d.pct(report(book, 'largest_zone_weight'))}",
            f"{d.label(resolve(report(book, 'largest_currency', 'text')))} {d.pct(report(book, 'largest_currency_weight'))}",
        ])
    rows.append([
        cap_label,
        f"{d.count(config('MIN_POSITIONS', 'raw'))} {span_word} {d.count(config('MAX_POSITIONS', 'raw'))}",
        d.pct(config("ISSUER_WEIGHT_CAP"), 0),
        d.pct(config("SECTOR_WEIGHT_CAP"), 0),
        d.pct(config("ZONE_WEIGHT_CAP"), 0),
        d.pct(config("CURRENCY_WEIGHT_CAP"), 0),
    ])
    return _table("tableau limites", header, rows, d)


def quality_table():
    d = Draft()
    frame = pd.read_excel(PROJECT_ROOT / QUALITY, sheet_name="Quality Dashboard", header=4)
    header = ["Contrôle", "Taux de conformité", "Statut"]
    rows = []
    for record in frame.itertuples(index=False):
        item = fact(QUALITY, "value", {"metric": record.metric}, scale="percent", sheet="Quality Dashboard", header=4)
        rows.append([str(record.metric), d.pct(item), str(record.status)])
    return _table("tableau qualité", header, rows, d)


def reconciliation_table():
    d = Draft()
    header = ["Comparaison", "OK", "EXCEPTION", "Autre statut"]
    rows = [
        [
            "Python contre Excel",
            d.count(reconciliation("statut", {"statut": "OK"})),
            d.count(reconciliation("statut", {"statut": "EXCEPTION"})),
            f"{d.count(reconciliation('statut', {'statut': 'non publié'}))} non publié",
        ],
        [
            "Power BI contre Excel",
            d.count(reconciliation("statut_power_bi", {"statut_power_bi": "OK"})),
            d.count(reconciliation("statut_power_bi", {"statut_power_bi": "EXCEPTION"})),
            f"{d.count(reconciliation('statut_power_bi', {'statut_power_bi': PENDING}))} en attente d'export, "
            f"{d.count(reconciliation('statut_power_bi', {'statut_power_bi': 'non publié'}))} non publié",
        ],
    ]
    return _table("tableau réconciliation", header, rows, d)


def reconciliation_sentence():
    d = Draft()
    gap = reconciliation("ecart", op="maxabs")
    value = float(resolve(gap))
    mantissa, exponent = f"{value:.0e}".split("e")
    d.facts.append(gap)
    return d.done("réconciliation", (
        f"Plus grand écart absolu entre Python et Excel : {mantissa}e{int(exponent)}, pour une tolérance de {d.sci(TOLERANCE)} "
        f"fixée avant la comparaison, sur {d.count(reconciliation('indicateur'))} lignes."
    ))


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------

def _style(axis):
    axis.set_facecolor(SURFACE)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axis.spines[side].set_color(AXIS)
    axis.tick_params(colors=MUTED, labelsize=8, length=0)
    axis.grid(axis="y", color=GRID, linewidth=0.6)
    axis.set_axisbelow(True)


def _save(figure, name):
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / name
    figure.savefig(path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    plt.close(figure)
    return path


def wealth_figure():
    """Cumulative wealth of the three books and of the fund, base 1."""
    path = pd.read_csv(PROJECT_ROOT / PATH)
    fund = pd.read_csv(PROJECT_ROOT / "data/06_performance/benchmark_monthly_return.csv")
    figure, axis = plt.subplots(figsize=(7.4, 3.0))
    _style(axis)
    fund_months = pd.to_datetime(fund["month"].astype(str) + "-01")
    fund_wealth = (1.0 + fund["benchmark_return_chf"].astype(float)).cumprod()
    axis.plot(fund_months, fund_wealth, color=SERIES_COLORS[FUND], linewidth=1.4, linestyle=(0, (4, 2)), label=LABELS[FUND])
    ends = [(float(fund_wealth.iloc[-1]), LABELS[FUND], SERIES_COLORS[FUND])]
    for book in BOOKS:
        rows = path.loc[path["strategy"].astype(str).eq(book)].sort_values("month")
        months = pd.to_datetime(rows["month"].astype(str) + "-01")
        axis.plot(months, rows["cumulative_wealth"].astype(float), color=SERIES_COLORS[book], linewidth=1.8, label=LABELS[book])
        ends.append((float(rows["cumulative_wealth"].iloc[-1]), LABELS[book], SERIES_COLORS[book]))
    axis.axhline(1.0, color=AXIS, linewidth=0.8)
    axis.set_ylabel("Richesse, base une unité", fontsize=8, color=MUTED)
    axis.legend(loc="upper left", fontsize=8, frameon=False, ncol=4, handlelength=1.6, columnspacing=1.2, bbox_to_anchor=(0, 1.14))
    return _save(figure, "richesse_cumulee.png")


def stress_figure():
    """Terminal wealth by shock, one group per book. Illustrative shocks."""
    frame = pd.read_csv(PROJECT_ROOT / "data/08_stress/stress_results.csv")
    shocks = ("aucun", "marche", "taux", "recession", "volatilite")
    shades = ("#898781", "#104281", "#256abf", "#5598e7", "#9ec5f4")
    figure, axis = plt.subplots(figsize=(7.4, 2.8))
    _style(axis)
    width = 0.15
    for index, shock in enumerate(shocks):
        values = [
            float(frame.loc[frame["strategy"].eq(book) & frame["shock"].eq(shock), "terminal_wealth"].iloc[0])
            for book in BOOKS
        ]
        positions = [group + (index - 2) * (width + 0.015) for group in range(len(BOOKS))]
        axis.bar(positions, values, width=width, color=shades[index], label=SHOCK_LABELS[shock])
    axis.axhline(1.0, color=INK, linewidth=0.8, linestyle=(0, (2, 2)))
    axis.set_xticks(range(len(BOOKS)))
    axis.set_xticklabels([LABELS[book] for book in BOOKS], fontsize=9, color=INK)
    axis.set_ylabel("Richesse finale, base une unité", fontsize=8, color=MUTED)
    axis.legend(loc="upper left", fontsize=8, frameon=False, ncol=5, handlelength=1.2, columnspacing=1.2, bbox_to_anchor=(0, 1.16))
    return _save(figure, "chocs_richesse_finale.png")


def tail_figure():
    """Monthly VaR and expected shortfall, one pair of bars per series."""
    frame = pd.read_csv(PROJECT_ROOT / "data/07_risk/risk_by_strategy.csv").set_index("strategy")
    series = BOOKS + (FUND,)
    figure, axis = plt.subplots(figsize=(7.4, 2.8))
    _style(axis)
    width = 0.32
    var = [float(frame.loc[name, "var_95"]) * 100 for name in series]
    shortfall = [float(frame.loc[name, "expected_shortfall_95"]) * 100 for name in series]
    positions = range(len(series))
    axis.bar([p - width / 2 - 0.01 for p in positions], var, width=width, color="#86b6ef", label="VaR mensuelle")
    axis.bar([p + width / 2 + 0.01 for p in positions], shortfall, width=width, color="#184f95", label="Expected shortfall mensuel")
    axis.axhline(0, color=AXIS, linewidth=0.8)
    axis.set_xticks(list(positions))
    axis.set_xticklabels([LABELS[name] for name in series], fontsize=9, color=INK)
    axis.set_ylabel("Rendement mensuel, en %", fontsize=8, color=MUTED)
    axis.legend(loc="lower left", fontsize=8, frameon=False, ncol=2, bbox_to_anchor=(0, 1.0))
    return _save(figure, "var_expected_shortfall.png")


def sector_figure():
    """Largest sector weight of each book over time, against the cap."""
    frame = pd.read_csv(PROJECT_ROOT / LIMITS)
    figure, axis = plt.subplots(figsize=(7.4, 2.8))
    _style(axis)
    for book in BOOKS:
        rows = frame.loc[frame["strategy"].astype(str).eq(book)].sort_values("month")
        months = pd.to_datetime(rows["month"].astype(str) + "-01")
        axis.plot(months, rows["largest_sector_weight"].astype(float) * 100, color=SERIES_COLORS[book], linewidth=1.8, label=LABELS[book])
    cap = float(resolve(config("SECTOR_WEIGHT_CAP"))) * 100
    axis.axhline(cap, color="#d03b3b", linewidth=1.2, linestyle=(0, (4, 2)), label="Plafond du mandat")
    axis.set_ylabel("Poids du premier secteur, en %", fontsize=8, color=MUTED)
    axis.legend(loc="lower left", fontsize=8, frameon=False, ncol=4, handlelength=1.6, columnspacing=1.2, bbox_to_anchor=(0, 1.0))
    return _save(figure, "premier_secteur.png")


def build_figures():
    return {
        "wealth": wealth_figure(),
        "stress": stress_figure(),
        "tail": tail_figure(),
        "sector": sector_figure(),
    }
