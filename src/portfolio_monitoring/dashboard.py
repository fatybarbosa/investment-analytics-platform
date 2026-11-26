"""
Charts for the phase 6 monitoring snapshot.

The figures read data/05_monitoring. They do not recompute weights.
write_dashboard publishes the same figures as reports/monitoring/dashboard.html.
"""


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import (
    CURRENCY_WEIGHT_CAP,
    ISSUER_WEIGHT_CAP,
    MAX_POSITIONS,
    MIN_POSITIONS,
    MONITORING_DATA,
    MONITORING_REPORTS,
    QUARTERLY_TURNOVER_CAP,
    IPS_SECTOR_WEIGHT_CAP,
    SECTOR_WEIGHT_CAP,
    ZONE_WEIGHT_CAP,
)
from src.portfolio_construction.build_portfolios import STRATEGY_IDS
from src.portfolio_monitoring.build_monitoring import POSITION_WEIGHT_FLOOR
from src.utils.files import replace_file


STRATEGY_LABELS = {
    "equal_weight": "Équipondéré",
    "minimum_volatility": "Volatilité minimale",
    "maximum_sharpe": "Sharpe maximal",
}
FUND_LABEL = "Fonds iShares"
STRATEGY_COLORS = {
    "Équipondéré": "#1f4e79",
    "Volatilité minimale": "#2e7d4f",
    "Sharpe maximal": "#c47b17",
    FUND_LABEL: "#4A4A4A",
}
DASHBOARD_FILE = MONITORING_REPORTS / "dashboard.html"
SECTION_TITLES = (
    "Performance cumulée et drawdown",
    "Contributions cumulées par secteur",
    "Allocation par secteur",
    "Allocation par zone",
    "Allocation par titre",
    "Devises",
    "Concentration",
    "Nombre effectif dans le temps",
    "Plus grand secteur dans le temps",
    "Lignes investies dans le temps",
    "Rotation brute trimestrielle",
    "Dix principales positions",
)


def load_dashboard_frames():
    """Read the published monitoring files in strategy order."""
    report = pd.read_csv(MONITORING_DATA / "monthly_report.csv")
    sectors = pd.read_csv(MONITORING_DATA / "allocation_by_sector.csv")
    zones = pd.read_csv(MONITORING_DATA / "allocation_by_zone.csv")
    exposure = pd.read_csv(MONITORING_DATA / "exposure.csv")
    holdings = pd.read_csv(MONITORING_DATA / "allocation_by_holding.csv")
    top10 = pd.read_csv(MONITORING_DATA / "top10_positions.csv")
    path = pd.read_csv(MONITORING_DATA / "portfolio_path.csv")
    contributions = pd.read_csv(MONITORING_DATA / "sector_contribution.csv")
    history = pd.read_csv(MONITORING_DATA / "concentration_history.csv")
    limits = pd.read_csv(MONITORING_DATA / "limit_watch.csv")
    turnover = pd.read_csv(MONITORING_DATA / "turnover.csv")
    frames = {
        "report": report,
        "sectors": sectors,
        "zones": zones,
        "exposure": exposure,
        "holdings": holdings,
        "top10": top10,
        "path": path,
        "contributions": contributions,
        "history": history,
        "limits": limits,
        "turnover": turnover,
    }
    for name, frame in frames.items():
        missing = set(STRATEGY_IDS) - set(frame["strategy"])
        if missing:
            raise RuntimeError(f"{name} is missing strategies: {', '.join(sorted(missing))}")
        if name == "path":
            extra = set(frame["strategy"].astype(str)) - set(STRATEGY_IDS)
            if extra != {"benchmark"}:
                raise RuntimeError("The wealth path is missing the published fund.")
            frame = frame.loc[frame["strategy"].astype(str).isin(STRATEGY_IDS)].copy()
        elif set(frame["strategy"].astype(str)) != set(STRATEGY_IDS):
            raise RuntimeError(f"{name} contains a strategy that is not one of the three books.")
        frame["strategy"] = pd.Categorical(
            frame["strategy"].map(STRATEGY_LABELS),
            categories=list(STRATEGY_LABELS.values()),
            ordered=True,
        )
        sort_columns = ["strategy"]
        if "month" in frame.columns:
            sort_columns.append("month")
        frames[name] = frame.sort_values(sort_columns, kind="mergesort")
    return frames


def apply_layout(figure, title, height):
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=height,
        legend_title_text="",
        margin={"t": 70, "b": 70, "l": 60, "r": 30},
        font={"family": "Segoe UI, sans-serif", "size": 13},
    )
    return figure


def grouped_weights(frame, category, title, category_order, height=480):
    """Grouped bars. One color is one strategy. Weights stay on a 0–100% scale."""
    figure = px.bar(
        frame,
        x=category,
        y="weight",
        color="strategy",
        barmode="group",
        category_orders={
            category: category_order,
            "strategy": list(STRATEGY_LABELS.values()),
        },
        color_discrete_map=STRATEGY_COLORS,
        hover_data={"weight": ":.1%"},
    )
    figure.update_yaxes(tickformat=".0%", title="Poids", rangemode="tozero")
    figure.update_xaxes(title="")
    figure.update_traces(
        hovertemplate="%{x}<br>%{fullData.name}<br>%{y:.1%}<extra></extra>"
    )
    return apply_layout(figure, title, height)


def category_order(frame, category):
    reference = frame.loc[frame["strategy"].eq(STRATEGY_LABELS["equal_weight"])]
    return reference.sort_values("weight", ascending=False)[category].tolist()


def sector_figure(sectors):
    return grouped_weights(
        sectors,
        "sector",
        SECTION_TITLES[2],
        category_order(sectors, "sector"),
    )


def zone_figure(zones):
    return grouped_weights(
        zones,
        "zone",
        SECTION_TITLES[3],
        category_order(zones, "zone"),
        height=440,
    )


def exposure_figure(exposure):
    return grouped_weights(
        exposure,
        "exposure",
        SECTION_TITLES[5],
        category_order(exposure, "exposure"),
        height=440,
    )


def holdings_figure(holdings):
    """Every invested line. Dust from the optimizer is not a position."""
    invested = holdings.loc[holdings["weight"].gt(POSITION_WEIGHT_FLOOR)].copy()
    labels = list(STRATEGY_LABELS.values())
    figure = make_subplots(
        rows=len(labels),
        cols=1,
        subplot_titles=labels,
        vertical_spacing=0.04,
    )
    shared_max = float(invested["weight"].max()) * 1.12
    for index, label in enumerate(labels, start=1):
        rows = invested.loc[invested["strategy"].eq(label)].sort_values(
            ["weight", "name"],
            ascending=[True, False],
        )
        figure.add_trace(
            go.Bar(
                x=rows["weight"],
                y=rows["name"],
                orientation="h",
                marker_color=STRATEGY_COLORS[label],
                customdata=list(zip(rows["sector"], rows["zone"])),
                hovertemplate="%{y}<br>%{x:.1%}<br>%{customdata[0]} · %{customdata[1]}<extra></extra>",
                showlegend=False,
            ),
            row=index,
            col=1,
        )
        figure.update_xaxes(tickformat=".0%", range=[0, shared_max * 1.15], row=index, col=1)
        figure.update_yaxes(automargin=True, tickfont={"size": 11}, row=index, col=1)
    figure = apply_layout(figure, SECTION_TITLES[4], 2600)
    figure.update_layout(margin={"l": 360, "t": 80, "b": 40, "r": 30})
    return figure


def concentration_figure(report):
    labels = [str(label) for label in report["strategy"]]
    colors = [STRATEGY_COLORS[label] for label in labels]
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            "Nombre effectif de titres",
            "Multiple de concentration",
        ),
    )
    figure.add_trace(
        go.Bar(
            x=labels,
            y=report["effective_holdings"],
            marker_color=colors,
            text=[f"{value:.1f}" for value in report["effective_holdings"]],
            textposition="outside",
            hovertemplate="%{x}<br>%{y:.2f} titres effectifs<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Bar(
            x=labels,
            y=report["concentration_multiple"],
            marker_color=colors,
            text=[f"{value:.2f}" for value in report["concentration_multiple"]],
            textposition="outside",
            hovertemplate="%{x}<br>multiple %{y:.2f}<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    figure.update_yaxes(rangemode="tozero")
    figure.update_xaxes(title="")
    return apply_layout(figure, SECTION_TITLES[6], 440)


def top10_figure(top10):
    labels = list(STRATEGY_LABELS.values())
    figure = make_subplots(
        rows=len(labels),
        cols=1,
        subplot_titles=labels,
        vertical_spacing=0.08,
    )
    shared_max = float(top10["weight"].max()) * 1.12
    for index, label in enumerate(labels, start=1):
        rows = top10.loc[top10["strategy"].eq(label)].sort_values("weight", ascending=True)
        figure.add_trace(
            go.Bar(
                x=rows["weight"],
                y=rows["name"],
                orientation="h",
                marker_color=STRATEGY_COLORS[label],
                text=rows["name"],
                textposition="outside",
                cliponaxis=False,
                customdata=list(zip(rows["sector"], rows["zone"])),
                hovertemplate="%{y}<br>%{x:.1%}<br>%{customdata[0]} · %{customdata[1]}<extra></extra>",
                showlegend=False,
            ),
            row=index,
            col=1,
        )
        figure.update_xaxes(
            tickformat=".0%",
            range=[0, shared_max * 2.6],
            row=index,
            col=1,
        )
    figure.update_yaxes(showticklabels=False)
    return apply_layout(figure, SECTION_TITLES[11], 980)


def as_dates(frame):
    """Dates in calendar order. A line follows this order, so it must not be shuffled."""
    dated = frame.copy()
    dated["month"] = pd.to_datetime(dated["month"])
    columns = ["strategy", "month"]
    if "sector" in dated.columns:
        columns = ["strategy", "sector", "month"]
    dated = dated.sort_values(columns, kind="mergesort")
    if not dated.groupby(["strategy"] + (["sector"] if "sector" in dated.columns else []), observed=True)["month"].apply(lambda values: values.is_monotonic_increasing).all():
        raise RuntimeError("A time series goes backwards.")
    return dated


def _fund_path():
    """CHF wealth of the published iShares NAV return. The fund is not one of the three books."""
    from src.performance.build_performance import BENCHMARK_RETURNS_FILE

    fund = pd.read_csv(BENCHMARK_RETURNS_FILE)
    fund["month"] = pd.to_datetime(fund["month"])
    fund = fund.sort_values("month", kind="mergesort")
    wealth = (1 + fund["benchmark_return_chf"].astype(float)).cumprod()
    return fund["month"], wealth, wealth / wealth.cummax().clip(lower=1.0) - 1


def path_figure(path):
    """Value of one franc, then the loss from the running peak. Each month uses its own weight."""
    dated = as_dates(path)
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=(
            "Placement de 1 CHF",
            "Drawdown",
        ),
    )
    for label in STRATEGY_LABELS.values():
        rows = dated.loc[dated["strategy"].eq(label)]
        figure.add_trace(
            go.Scatter(
                x=rows["month"],
                y=rows["cumulative_wealth"],
                mode="lines",
                name=label,
                line={"color": STRATEGY_COLORS[label]},
                legendgroup=label,
                hovertemplate="%{x|%Y-%m}<br>%{y:.2f} CHF<extra>" + label + "</extra>",
            ),
            row=1,
            col=1,
        )
        figure.add_trace(
            go.Scatter(
                x=rows["month"],
                y=rows["drawdown"],
                mode="lines",
                name=label,
                line={"color": STRATEGY_COLORS[label]},
                legendgroup=label,
                showlegend=False,
                hovertemplate="%{x|%Y-%m}<br>drawdown %{y:.1%}<extra>" + label + "</extra>",
            ),
            row=2,
            col=1,
        )
    months, wealth, drawdown = _fund_path()
    figure.add_trace(
        go.Scatter(
            x=months,
            y=wealth,
            mode="lines",
            name=FUND_LABEL,
            line={"color": STRATEGY_COLORS[FUND_LABEL]},
            legendgroup=FUND_LABEL,
            hovertemplate="%{x|%Y-%m}<br>%{y:.2f} CHF<extra>" + FUND_LABEL + "</extra>",
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=months,
            y=drawdown,
            mode="lines",
            name=FUND_LABEL,
            line={"color": STRATEGY_COLORS[FUND_LABEL]},
            legendgroup=FUND_LABEL,
            showlegend=False,
            hovertemplate="%{x|%Y-%m}<br>drawdown %{y:.1%}<extra>" + FUND_LABEL + "</extra>",
        ),
        row=2,
        col=1,
    )
    figure.update_yaxes(title="CHF", rangemode="tozero", row=1, col=1)
    figure.update_yaxes(tickformat=".0%", title="Drawdown", row=2, col=1)
    figure.update_xaxes(type="date", title="")
    return apply_layout(figure, SECTION_TITLES[0], 680)


def contribution_figure(contributions):
    """Additive sector contribution under the same weights, cumulated through the window."""
    dated = as_dates(contributions)
    figure = px.line(
        dated,
        x="month",
        y="cumulative_contribution",
        color="sector",
        facet_row="strategy",
        category_orders={"strategy": list(STRATEGY_LABELS.values())},
        hover_data={"cumulative_contribution": ":.1%"},
    )
    figure.update_yaxes(tickformat=".0%", title="")
    figure.update_xaxes(type="date", title="")
    figure.for_each_annotation(
        lambda annotation: annotation.update(text=annotation.text.split("=")[-1])
    )
    return apply_layout(figure, SECTION_TITLES[1], 860)


def effective_figure(history):
    """Effective holdings of every month, under that month's published weights."""
    dated = as_dates(history)
    figure = px.line(
        dated,
        x="month",
        y="effective_holdings",
        color="strategy",
        color_discrete_map=STRATEGY_COLORS,
        category_orders={"strategy": list(STRATEGY_LABELS.values())},
    )
    figure.update_yaxes(title="Titres effectifs", rangemode="tozero")
    figure.update_xaxes(type="date", title="")
    figure.update_traces(hovertemplate="%{x|%Y-%m}<br>%{y:.2f} titres effectifs<extra></extra>")
    return apply_layout(figure, SECTION_TITLES[7], 440)


def sector_limit_figure(limits):
    """Largest sector weight of every month, with the working cap and the cap written in the IPS."""
    dated = as_dates(limits)
    figure = px.line(
        dated,
        x="month",
        y="largest_sector_weight",
        color="strategy",
        color_discrete_map=STRATEGY_COLORS,
        category_orders={"strategy": list(STRATEGY_LABELS.values())},
    )
    figure.add_hline(
        y=SECTOR_WEIGHT_CAP,
        line_dash="dash",
        line_color="#666666",
        annotation_text=f"plafond de travail {SECTOR_WEIGHT_CAP * 100:.0f} %, non approuvé",
    )
    figure.add_hline(
        y=IPS_SECTOR_WEIGHT_CAP,
        line_dash="dot",
        line_color="#d03b3b",
        annotation_text=f"plafond écrit dans l'IPS {IPS_SECTOR_WEIGHT_CAP * 100:.0f} %",
        annotation_position="bottom right",
    )
    figure.update_yaxes(tickformat=".0%", title="Poids", rangemode="tozero")
    figure.update_xaxes(type="date", title="")
    figure.update_traces(hovertemplate="%{x|%Y-%m}<br>%{y:.1%}<extra></extra>")
    return apply_layout(figure, SECTION_TITLES[8], 440)


def invested_figure(limits):
    """Invested lines of every month. The band applies to the two optimized books."""
    dated = as_dates(limits)
    figure = px.line(
        dated,
        x="month",
        y="invested_names",
        color="strategy",
        color_discrete_map=STRATEGY_COLORS,
        category_orders={"strategy": list(STRATEGY_LABELS.values())},
    )
    figure.add_hline(
        y=MIN_POSITIONS,
        line_dash="dash",
        line_color="#666666",
        annotation_text=f"plancher {MIN_POSITIONS}",
    )
    figure.add_hline(
        y=MAX_POSITIONS,
        line_dash="dash",
        line_color="#666666",
        annotation_text=f"plafond {MAX_POSITIONS}",
    )
    figure.update_yaxes(title="Lignes", rangemode="tozero")
    figure.update_xaxes(type="date", title="")
    figure.update_traces(hovertemplate="%{x|%Y-%m}<br>%{y:.0f} lignes<extra></extra>")
    return apply_layout(figure, SECTION_TITLES[9], 440)


def turnover_figure(turnover):
    """Quarterly gross turnover, with the IPS cap of one quarter."""
    dated = as_dates(turnover)
    figure = px.line(
        dated,
        x="month",
        y="gross_turnover",
        color="strategy",
        color_discrete_map=STRATEGY_COLORS,
        category_orders={"strategy": list(STRATEGY_LABELS.values())},
    )
    figure.add_hline(
        y=QUARTERLY_TURNOVER_CAP,
        line_dash="dash",
        line_color="#666666",
        annotation_text=f"plafond {QUARTERLY_TURNOVER_CAP * 100:.1f} %",
    )
    figure.update_yaxes(tickformat=".0%", title="Rotation brute", rangemode="tozero")
    figure.update_xaxes(type="date", title="")
    figure.update_traces(hovertemplate="%{x|%Y-%m}<br>%{y:.1%}<extra></extra>")
    return apply_layout(figure, SECTION_TITLES[10], 440)


def build_figures():
    """The path through the window, the report-month book, then the cap watch."""
    frames = load_dashboard_frames()
    return [
        path_figure(frames["path"]),
        contribution_figure(frames["contributions"]),
        sector_figure(frames["sectors"]),
        zone_figure(frames["zones"]),
        holdings_figure(frames["holdings"]),
        exposure_figure(frames["exposure"]),
        concentration_figure(frames["report"]),
        effective_figure(frames["history"]),
        sector_limit_figure(frames["limits"]),
        invested_figure(frames["limits"]),
        turnover_figure(frames["turnover"]),
        top10_figure(frames["top10"]),
    ]


def render_dashboard_html():
    frames = load_dashboard_frames()
    report = frames["report"]
    month = str(report["report_month"].iloc[0])
    window_start = str(report["window_start"].iloc[0])
    window_end = str(report["window_end"].iloc[0])
    if report["report_month"].nunique() != 1:
        raise RuntimeError("The monitoring report has more than one month.")
    sections = []
    for index, figure in enumerate(build_figures()):
        sections.append(
            figure.to_html(
                full_html=False,
                include_plotlyjs=index == 0,
                config={"displayModeBar": False},
            )
        )
    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Suivi des portefeuilles — {month}</title>
<style>
html, body {{
  background: #ffffff;
  color: #1a1a1a;
}}
body {{
  font-family: "Segoe UI", sans-serif;
  margin: 2rem auto;
  max-width: 1100px;
  padding: 0 1rem 3rem;
}}
h1 {{ font-size: 1.7rem; margin-bottom: 0.3rem; }}
p {{ color: #333; line-height: 1.45; }}
</style>
</head>
<body>
<h1>Suivi des portefeuilles</h1>
<p>Situation au {month}. Période suivie {window_start} – {window_end}.
Les trois livres sont hypothétiques : ils ont été construits rétrospectivement sur des cours publics
et n'ont pas été détenus. Le fonds iShares est une série réelle, le rendement publié de sa valeur liquidative en francs.
Il figure sur le placement de 1 CHF et sur le drawdown. Il n'a pas de poids dans ces livres,
donc il n'est pas sur les graphiques d'allocation, de lignes, de rotation ni de concentration.
Le poids d'un trimestre est fixé avec les soixante mois de rendements déjà observés,
puis dérive avec le marché pendant les trois mois du trimestre.
Les plafonds de construction sont {ISSUER_WEIGHT_CAP * 100:.0f} % par émetteur,
{SECTOR_WEIGHT_CAP * 100:.0f} % par secteur, {ZONE_WEIGHT_CAP * 100:.0f} % par zone
et {CURRENCY_WEIGHT_CAP * 100:.0f} % par devise de cotation.
L'IPS écrit {IPS_SECTOR_WEIGHT_CAP * 100:.0f} % par secteur : la liste de titres ne le permet pas, et les
{SECTOR_WEIGHT_CAP * 100:.0f} % sont un plafond de travail que le client n'a pas approuvé.
Le premier graphique suit un placement de 1 CHF et son drawdown.
Le deuxième cumule les contributions mensuelles par secteur ; ce cumul n'est pas
une performance composée.
La situation du mois du rapport donne le secteur, la zone, chaque titre investi
et la devise de cotation. Ce sont les expositions du mandat.
Trois graphiques suivent ensuite toute la période : le nombre effectif de titres,
le poids du plus grand secteur avec son plafond, et le nombre de lignes investies.
La bande de {MIN_POSITIONS} à {MAX_POSITIONS} lignes vaut pour les deux portefeuilles optimisés.
La rotation brute d'un trimestre est la somme des valeurs absolues des changements de poids.
Son plafond est {QUARTERLY_TURNOVER_CAP * 100:.1f} %.
La page se termine par la concentration du mois et les dix principales lignes.
Elle est régénérée à chaque reconstruction.</p>
{body}
</body>
</html>
"""


def write_dashboard():
    """Write the browser page next to the monthly report notebook."""
    DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DASHBOARD_FILE.with_suffix(".html.tmp")
    temporary.write_text(render_dashboard_html(), encoding="utf-8")
    replace_file(temporary, DASHBOARD_FILE)
    return DASHBOARD_FILE
