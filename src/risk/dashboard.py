"""
Charts for the phase 8 risk reading.

The figures read the published risk files. They do not estimate weights
again. write_dashboard publishes reports/risk/dashboard.html.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config import RISK_REPORTS
from src.portfolio_construction.build_portfolios import STRATEGY_IDS
from src.portfolio_monitoring.dashboard import FUND_LABEL, STRATEGY_COLORS, STRATEGY_LABELS
from src.risk.build_risk import METRICS_OUTPUT, SUMMARY_FILE, TAIL_FILE, VAR_LEVEL


DASHBOARD_FILE = RISK_REPORTS / "dashboard.html"
SECTION_TITLES = (
    "Queue historique à 95 %",
    "Mois de l'expected shortfall",
    "Corrélations hors diagonale",
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


def load_frames():
    metrics = pd.read_csv(METRICS_OUTPUT)
    tail = pd.read_csv(TAIL_FILE)
    summary = pd.read_csv(SUMMARY_FILE)
    labels = {**STRATEGY_LABELS, "benchmark": FUND_LABEL}
    categories = list(STRATEGY_LABELS.values()) + [FUND_LABEL]
    if set(metrics["strategy"].astype(str)) != set(labels):
        raise RuntimeError("The risk file does not cover the three books and the fund.")
    if set(tail["strategy"].astype(str)) != set(labels):
        raise RuntimeError("The historical tail does not cover the three books and the fund.")
    metrics["strategy"] = pd.Categorical(
        metrics["strategy"].astype(str).map(labels),
        categories=categories,
        ordered=True,
    )
    tail["strategy"] = pd.Categorical(
        tail["strategy"].astype(str).map(labels),
        categories=categories,
        ordered=True,
    )
    return {
        "metrics": metrics.sort_values("strategy", kind="mergesort"),
        "tail": tail.sort_values(["strategy", "rank"], kind="mergesort"),
        "summary": summary,
    }


def tail_bars(metrics):
    """Historical VaR and expected shortfall, one pair of bars per book."""
    long = metrics.melt(
        id_vars=["strategy"],
        value_vars=["var_95", "expected_shortfall_95"],
        var_name="measure",
        value_name="return",
    )
    long["measure"] = long["measure"].map(
        {
            "var_95": "VaR 95 %",
            "expected_shortfall_95": "Expected shortfall 95 %",
        }
    )
    figure = px.bar(
        long,
        x="strategy",
        y="return",
        color="measure",
        barmode="group",
        category_orders={"strategy": list(STRATEGY_LABELS.values()) + [FUND_LABEL]},
    )
    figure.update_yaxes(title="Rendement du mois", tickformat=".0%")
    figure.update_xaxes(title="")
    figure.update_traces(hovertemplate="%{x}<br>%{y:.1%}<extra></extra>")
    return apply_layout(figure, SECTION_TITLES[0], 460)


def tail_months(tail):
    """The months averaged into the expected shortfall."""
    figure = px.bar(
        tail,
        x="month",
        y="portfolio_return",
        color="strategy",
        barmode="group",
        color_discrete_map=STRATEGY_COLORS,
        category_orders={"strategy": list(STRATEGY_LABELS.values()) + [FUND_LABEL]},
    )
    figure.update_yaxes(title="Rendement", tickformat=".0%")
    figure.update_xaxes(title="")
    figure.update_traces(hovertemplate="%{x}<br>%{y:.1%}<extra>%{fullData.name}</extra>")
    return apply_layout(figure, SECTION_TITLES[1], 460)


def correlation_note(summary):
    """One number: how the shared list moves together."""
    average = float(summary["average_correlation"].iloc[0])
    names = int(summary["names"].iloc[0])
    figure = go.Figure(
        go.Indicator(
            mode="number",
            value=average,
            number={"valueformat": ".0%"},
            title={"text": f"Corrélation moyenne des {names} titres, hors diagonale"},
        )
    )
    return apply_layout(figure, SECTION_TITLES[2], 280)


def build_figures():
    frames = load_frames()
    return [
        tail_bars(frames["metrics"]),
        tail_months(frames["tail"]),
        correlation_note(frames["summary"]),
    ]


def render_dashboard_html():
    frames = load_frames()
    metrics = frames["metrics"]
    summary = frames["summary"].iloc[0]
    start = str(pd.read_csv(METRICS_OUTPUT)["window_start"].iloc[0])
    end = str(pd.read_csv(METRICS_OUTPUT)["window_end"].iloc[0])
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
    names = int(summary["names"])
    average = f"{float(summary['average_correlation']) * 100:.1f}".replace(".", ",")
    confidence = f"{(1 - VAR_LEVEL) * 100:.0f}".replace(".", ",")
    tail_share = f"{VAR_LEVEL * 100:.0f}".replace(".", ",")
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Risque des portefeuilles — {end}</title>
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
<h1>Risque des portefeuilles</h1>
<p>Période {start} – {end}. Le rendement est le rendement mensuel simple en francs
déjà publié, de fin de mois à fin de mois. Un chiffre négatif est une perte sur le mois.
La VaR et l'expected shortfall incluent le fonds iShares : son rendement mensuel en francs est publié.
La VaR est historique, au seuil de {confidence} % :
les rendements mensuels sont triés du plus mauvais au meilleur, et le rang retenu
est le plafond de {tail_share} % du nombre de mois. L'expected shortfall est la moyenne
des mois de ce rang et des mois pires. Aucune loi normale n'est supposée.
Ce n'est pas une prévision du mois suivant.
La corrélation moyenne des {names} titres inclus est {average} %, hors diagonale.
Le fonds n'est pas un trentième titre de cette liste.
Elle décrit la liste partagée, pas le poids choisi par un livre.
La concentration des poids reste dans le suivi.
La page est régénérée à chaque reconstruction.</p>
{body}
</body>
</html>
"""


def write_dashboard():
    """Write the risk page next to the risk report."""
    DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DASHBOARD_FILE.with_suffix(".html.tmp")
    temporary.write_text(render_dashboard_html(), encoding="utf-8")
    temporary.replace(DASHBOARD_FILE)
    return DASHBOARD_FILE
