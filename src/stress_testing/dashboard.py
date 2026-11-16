"""
Charts for the phase 9 stress reading.

The figures read the published shock file and the shocked paths.
They do not estimate weights again. write_dashboard publishes
reports/stress/dashboard.html.
"""

import pandas as pd
import plotly.express as px

from src.config import (
    MARKET_SHOCK_RETURN,
    RATE_SHOCK_ANNUAL_POINTS,
    RECESSION_SHOCK_MONTHS,
    RECESSION_SHOCK_RETURN,
    STRESS_REPORTS,
    VOLATILITY_SHOCK_MULTIPLIER,
)
from src.portfolio_monitoring.dashboard import STRATEGY_COLORS, STRATEGY_LABELS
from src.stress_testing.build_stress import PATHS_FILE, RESULTS_FILE, SHOCK_IDS


DASHBOARD_FILE = STRESS_REPORTS / "dashboard.html"
SHOCK_LABELS = {
    "aucun": "Sans choc",
    "marche": "Marché",
    "taux": "Taux",
    "recession": "Récession",
    "volatilite": "Volatilité",
}
SECTION_TITLES = (
    "Performance cumulée sous choc",
    "Drawdown maximal sous choc",
    "Volatilité sous choc",
    "Ratio de Sharpe sous choc",
    "Écart de richesse par rapport au chemin sans choc",
)


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


def _percent(value):
    return f"{float(value) * 100:.0f}".replace(".", ",")


def load_frames():
    """Read the shock table and the paths in the published order."""
    results = pd.read_csv(RESULTS_FILE)
    paths = pd.read_csv(PATHS_FILE)
    if set(results["strategy"].astype(str)) != set(STRATEGY_LABELS):
        raise RuntimeError("The stress file does not cover the three strategies.")
    if set(results["shock"].astype(str)) != set(SHOCK_IDS):
        raise RuntimeError("The stress file does not cover the four shocks.")
    results["strategy"] = pd.Categorical(
        results["strategy"].astype(str).map(STRATEGY_LABELS),
        categories=list(STRATEGY_LABELS.values()),
        ordered=True,
    )
    results["shock"] = pd.Categorical(
        results["shock"].astype(str).map(SHOCK_LABELS),
        categories=[SHOCK_LABELS[shock] for shock in SHOCK_IDS],
        ordered=True,
    )
    paths["strategy"] = pd.Categorical(
        paths["strategy"].astype(str).map(STRATEGY_LABELS),
        categories=list(STRATEGY_LABELS.values()),
        ordered=True,
    )
    paths["shock"] = pd.Categorical(
        paths["shock"].astype(str).map(SHOCK_LABELS),
        categories=[SHOCK_LABELS[shock] for shock in SHOCK_IDS],
        ordered=True,
    )
    paths["month"] = pd.to_datetime(paths["month"].astype(str))
    return {
        "results": results.sort_values(["shock", "strategy"], kind="mergesort"),
        "paths": paths.sort_values(["strategy", "shock", "month"], kind="mergesort"),
    }


def _bars(results, column, title, number_format):
    figure = px.bar(
        results,
        x="shock",
        y=column,
        color="strategy",
        barmode="group",
        color_discrete_map=STRATEGY_COLORS,
        category_orders={
            "shock": [SHOCK_LABELS[shock] for shock in SHOCK_IDS],
            "strategy": list(STRATEGY_LABELS.values()),
        },
    )
    figure.update_yaxes(title="", tickformat=number_format)
    figure.update_xaxes(title="")
    figure.update_traces(hovertemplate="%{x}<br>%{y}<extra>%{fullData.name}</extra>")
    return apply_layout(figure, title, 460)


def path_figure(paths):
    """Gap versus the unshocked path. The rate shock does not move portfolio wealth, so it is not drawn."""
    dated = paths.copy()
    dated["month"] = pd.to_datetime(dated["month"])
    visible = [SHOCK_LABELS[shock] for shock in ("marche", "recession", "volatilite")]
    base = dated.loc[dated["shock"].eq(SHOCK_LABELS["aucun"]), ["strategy", "month", "cumulative_wealth"]]
    base = base.rename(columns={"cumulative_wealth": "base_wealth"})
    moving = dated.loc[dated["shock"].isin(visible)]
    shown = moving.merge(base, on=["strategy", "month"], how="inner")
    if len(shown) != len(moving):
        raise RuntimeError("A shocked month has no unshocked wealth.")
    shown["gap"] = shown["cumulative_wealth"] - shown["base_wealth"]
    figure = px.line(
        shown,
        x="month",
        y="gap",
        color="shock",
        facet_row="strategy",
        category_orders={
            "shock": visible,
            "strategy": list(STRATEGY_LABELS.values()),
        },
    )
    figure.add_hline(y=0, line_dash="dash", line_color="#666666")
    figure.update_yaxes(title="")
    figure.update_xaxes(title="")
    figure.update_traces(hovertemplate="%{x|%Y-%m}<br>%{y:.2f}<extra>%{fullData.name}</extra>")
    figure.for_each_annotation(lambda annotation: annotation.update(text=annotation.text.split("=")[-1]))
    return apply_layout(figure, SECTION_TITLES[4], 860)


def build_figures():
    """The five stress readings, in the page order."""
    frames = load_frames()
    results = frames["results"]
    return [
        _bars(results, "terminal_wealth", SECTION_TITLES[0], ".2f"),
        _bars(results, "maximum_drawdown", SECTION_TITLES[1], ".0%"),
        _bars(results, "annualized_volatility", SECTION_TITLES[2], ".0%"),
        _bars(results, "sharpe_ratio", SECTION_TITLES[3], ".2f"),
        path_figure(frames["paths"]),
    ]


def render_dashboard_html():
    """One page. The shock sizes are the parameters. The bars are the file."""
    results = pd.read_csv(RESULTS_FILE)
    start = str(results["window_start"].iloc[0])
    end = str(results["window_end"].iloc[0])
    sections = []
    for index, figure in enumerate(build_figures()):
        sections.append(
            figure.to_html(
                full_html=False,
                include_plotlyjs=index == 0,
                config={"displayModeBar": False},
            )
        )
    market = _percent(MARKET_SHOCK_RETURN)
    points = f"{RATE_SHOCK_ANNUAL_POINTS:.0f}".replace(".", ",")
    recession = _percent(RECESSION_SHOCK_RETURN)
    multiplier = f"{VOLATILITY_SHOCK_MULTIPLIER:.1f}".replace(".", ",")
    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tests de résistance — {end}</title>
<style>
html, body {{ background: #ffffff; color: #1a1a1a; }}
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
<h1>Tests de résistance</h1>
<p>Période {start} – {end}. Le rendement est le rendement mensuel simple en francs
déjà publié. Un chiffre négatif est une perte sur le mois. Les poids ne sont pas réestimés.
Le choc de marché remplace le dernier mois par {market} %.
Le choc de taux ajoute {points} points au SARON annuel et laisse le rendement du portefeuille inchangé.
Le choc de récession remplace chacun des {RECESSION_SHOCK_MONTHS} derniers mois par {recession} %.
Le choc de volatilité multiplie les écarts à la moyenne par {multiplier}.
Ce n'est pas une prévision, ni un scénario daté. Les chocs portent sur les trois livres.
Le fonds n'est pas un quatrième portefeuille choqué : c'est la référence, et il n'est pas sur cette page.
Le graphique du temps est l'écart de richesse avec le chemin sans choc, pour le marché, la récession et la volatilité.
Sans choc est la ligne zéro. Le choc de taux ne change pas le rendement du portefeuille, donc il n'est pas tracé.
Il reste dans les barres, parce qu'il change le Sharpe.
Le marché ne s'écarte qu'au dernier mois, la récession sur ses derniers mois.
La page est régénérée à chaque reconstruction.</p>
{body}
</body>
</html>
"""


def write_dashboard():
    """Write the simulation page next to the stress report."""
    DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DASHBOARD_FILE.with_suffix(".html.tmp")
    temporary.write_text(render_dashboard_html(), encoding="utf-8")
    temporary.replace(DASHBOARD_FILE)
    return DASHBOARD_FILE
