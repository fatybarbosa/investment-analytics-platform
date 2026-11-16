"""
Phase 11. Automated comments, written from the pipeline files.

Four sections: faits marquants, risques identifiés, alertes, points à
instruire. Every sentence is built with facts (file, row, column) and
checked by src.reporting.number_check before it is kept. A number that
is not in a pipeline file stops the run.

The comments state findings and alerts tied to the written limits of the
mandate. They do not give personalised investment advice. They carry the
label "Généré automatiquement, à relire avant diffusion."

The books are simulated on public prices. They were never held. Nothing
here is custody data.

Outputs
-------
reports/executive/commentaires_automatises.md
reports/executive/commentaires_automatises.json
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.config import EXECUTIVE_REPORTS
from src.reporting.number_check import AUTO_LABEL, Draft, fact, resolve


COMMENT_MD = EXECUTIVE_REPORTS / "commentaires_automatises.md"
COMMENT_JSON = EXECUTIVE_REPORTS / "commentaires_automatises.json"

METRICS = "data/04_portfolios/portfolio_metrics.csv"
MEMBERSHIP = "data/04_portfolios/portfolio_membership.csv"
PERFORMANCE = "data/06_performance/performance_metrics.csv"
EPISODES = "data/06_performance/drawdown_episode.csv"
RISK = "data/07_risk/risk_by_strategy.csv"
TAIL = "data/07_risk/var_tail.csv"
CORRELATION = "data/07_risk/universe_correlation.csv"
MATRIX = "data/07_risk/correlation_matrix.csv"
STRESS = "data/08_stress/stress_results.csv"
REPORT = "data/05_monitoring/monthly_report.csv"
LIMITS = "data/05_monitoring/limit_watch.csv"
TURNOVER = "data/05_monitoring/turnover.csv"
HOLDINGS = "data/05_monitoring/allocation_by_holding.csv"
PATH = "data/05_monitoring/portfolio_path.csv"
QUALITY = "audit/data_control_center.xlsx"
ANNEX = "reports/excel/annexe_reporting.xlsx"
EXPORT = "reports/excel/power_bi_export.csv"
CONFIG = "py:src.config"
RISK_MODULE = "py:src.risk.build_risk"
MONITORING_MODULE = "py:src.portfolio_monitoring.build_monitoring"
STRESS_MODULE = "py:src.stress_testing.build_stress"

BOOKS = ("equal_weight", "minimum_volatility", "maximum_sharpe")
FUND = "benchmark"
LABELS = {
    "equal_weight": "Équipondéré",
    "minimum_volatility": "Volatilité minimale",
    "maximum_sharpe": "Sharpe maximal",
    "benchmark": "Fonds iShares (CHF)",
}
SHOCKS = ("marche", "taux", "recession", "volatilite")
SHOCK_LABELS = {
    "aucun": "Sans choc",
    "marche": "Marché",
    "taux": "Taux",
    "recession": "Récession",
    "volatilite": "Volatilité",
}
PENDING = "en attente d'export Power BI"
DISCLAIMER = (
    "Ces points sont des constats et des alertes liés aux limites écrites du mandat. "
    "Ce ne sont pas des recommandations d'investissement personnalisées."
)
PORTFOLIO_LABEL = "Portefeuilles hypothétiques construits rétrospectivement sur des données publiques"
REAL_DATA_NOTE = "Les cours, les cours de change et le SARON sont des données réelles et publiques."
SCOPE_NOTE = (
    f"{PORTFOLIO_LABEL} : ils n'ont jamais été détenus. {REAL_DATA_NOTE} "
    "Pas de données de conservation, pas de frais, pas de dividendes dans le rendement des livres."
)
SECTION_TITLES = {
    "faits": "Faits marquants",
    "risques": "Risques identifiés",
    "alertes": "Alertes",
    "points": "Points à instruire",
}


# --------------------------------------------------------------------------
# Facts
# --------------------------------------------------------------------------

def perf(book, column, scale="ratio"):
    return fact(PERFORMANCE, column, {"strategy": book}, scale=scale)


def risk(book, column, scale="ratio"):
    return fact(RISK, column, {"strategy": book}, scale=scale)


def metric(book, column, scale="raw"):
    return fact(METRICS, column, {"strategy": book}, scale=scale)


def report(book, column, scale="ratio"):
    return fact(REPORT, column, {"strategy": book}, scale=scale)


def stress(book, shock, column, scale="raw"):
    return fact(STRESS, column, {"strategy": book, "shock": shock}, scale=scale)


def config(name, scale="ratio"):
    return fact(CONFIG, name, scale=scale)


def quality_summary(column, scale="raw"):
    """Last line of the quality history: the run the workbook was written for."""
    return fact(QUALITY, column, op="last", scale=scale, sheet="Quality History")


def reconciliation(column, where=None, op="count", scale="raw"):
    return fact(ANNEX, column, where, op=op, scale=scale, sheet="Reconciliation", header=3)


WINDOW_START = metric("equal_weight", "window_start", "text")
WINDOW_END = metric("equal_weight", "window_end", "text")
MONTHS = metric("equal_weight", "months")
NAMES = metric("equal_weight", "names")
TOLERANCE = fact("py:src.portfolio_monitoring.build_monitoring", "CONTRIBUTION_TOLERANCE")


def _best(books, item_of, highest=True):
    values = {book: float(resolve(item_of(book))) for book in books}
    return (max if highest else min)(values, key=values.get)


def _top_pair():
    matrix = pd.read_csv(resolve_path(MATRIX), index_col=0)
    values = matrix.to_numpy(dtype=float).copy()
    np.fill_diagonal(values, -np.inf)
    row, column = np.unravel_index(np.argmax(values), values.shape)
    return str(matrix.index[row]), str(matrix.columns[column])


def resolve_path(source):
    from src.config import PROJECT_ROOT

    return PROJECT_ROOT / source


def _holding_name(symbol):
    frame = pd.read_csv(resolve_path(HOLDINGS))
    rows = frame.loc[frame["yahoo_symbol"].astype(str).eq(symbol), "name"]
    return str(rows.iloc[0]) if len(rows) else symbol


# --------------------------------------------------------------------------
# Sentences
# --------------------------------------------------------------------------

def _highlights():
    out = []
    d = Draft()
    out.append(d.done("faits", (
        f"La fenêtre couvre {d.count(MONTHS)} mois, de {d.text(WINDOW_START)} à {d.text(WINDOW_END)}. "
        f"Les trois livres, hypothétiques et construits rétrospectivement sur des données publiques, partagent la même liste de {d.count(NAMES)} titres : "
        f"ce sont les titres au statut Eligible du registre ODD qui ont un historique complet en CHF, "
        f"sur {d.count(fact(MEMBERSHIP, 'yahoo_symbol', op='count'))} titres examinés."
    )))

    best = _best(BOOKS, lambda book: perf(book, "annualized_return"))
    fund_return = float(resolve(perf(FUND, "annualized_return")))
    best_return = float(resolve(perf(best, "annualized_return")))
    d = Draft()
    listed = ", ".join(
        f"{LABELS[book]} {d.pct(perf(book, 'annualized_return'))}" for book in BOOKS
    )
    verdict = (
        "Aucun livre ne dépasse le fonds sur la fenêtre."
        if best_return < fund_return
        else f"Le livre {LABELS[best]} dépasse le fonds sur la fenêtre."
    )
    out.append(d.done("faits", (
        f"Rendement annualisé en CHF : {listed}, contre {d.pct(perf(FUND, 'annualized_return'))} "
        f"pour le fonds iShares, rendement de la valeur liquidative converti en CHF. {verdict} "
        "La comparaison n'est pas à périmètre égal : le rendement des livres n'inclut pas les dividendes, "
        "celui du fonds est un rendement total publié."
    )))

    d = Draft()
    listed = ", ".join(f"{LABELS[book]} {d.num(perf(book, 'sharpe_ratio', 'raw'))}" for book in BOOKS)
    out.append(d.done("faits", (
        f"Ratio de Sharpe contre le SARON : {listed}, fonds {d.num(perf(FUND, 'sharpe_ratio', 'raw'))}. "
        f"Le livre {LABELS[_best(BOOKS, lambda book: perf(book, 'sharpe_ratio', 'raw'))]} a le Sharpe le plus élevé des trois livres."
    )))

    d = Draft()
    listed = ", ".join(
        f"{LABELS[book]} {d.num(stress(book, 'aucun', 'terminal_wealth'))}" for book in BOOKS
    )
    out.append(d.done("faits", (
        f"Richesse finale pour 1 investi au début de la fenêtre, sans choc : {listed}."
    ).replace("pour 1 investi", "pour une unité investie")))

    d = Draft()
    ok = reconciliation("statut", {"statut": "OK"})
    exceptions = reconciliation("statut", {"statut": "EXCEPTION"})
    unpublished = reconciliation("statut", {"statut": "non publié"})
    out.append(d.done("faits", (
        f"Contrôle des calculs : sur {d.count(reconciliation('indicateur'))} lignes de réconciliation, "
        f"{d.count(ok)} sont OK entre Python et Excel, {d.count(exceptions)} en EXCEPTION et "
        f"{d.count(unpublished)} non publiée. La tolérance est de {d.sci(TOLERANCE)}, fixée avant la comparaison."
    )))
    return out


def _risks():
    out = []
    d = Draft()
    listed = ", ".join(
        f"{LABELS[book]} {d.pct(risk(book, 'annualized_volatility'))}" for book in BOOKS
    )
    out.append(d.done("risques", (
        f"Volatilité annualisée : {listed}, fonds {d.pct(risk(FUND, 'annualized_volatility'))}."
    )))

    d = Draft()
    level = fact(RISK_MODULE, "VAR_LEVEL", scale="ratio")
    listed = "; ".join(
        f"{LABELS[book]} VaR {d.pct(risk(book, 'var_95'))} et expected shortfall {d.pct(risk(book, 'expected_shortfall_95'))}"
        for book in BOOKS + (FUND,)
    )
    out.append(d.done("risques", (
        f"Perte mensuelle historique, lue sur les {d.pct(level, 0)} de mois les plus défavorables : {listed}. "
        "Ce sont des rendements mensuels observés, sans loi normale et sans annualisation."
    )))

    d = Draft()
    parts = []
    for book in BOOKS:
        worst_month = fact(TAIL, "month", {"strategy": book, "rank": 1}, scale="text")
        worst = fact(TAIL, "portfolio_return", {"strategy": book, "rank": 1}, scale="ratio")
        parts.append(f"{LABELS[book]} {d.pct(worst)} en {d.text(worst_month)}")
    out.append(d.done("risques", f"Pire mois de la fenêtre : {', '.join(parts)}."))

    d = Draft()
    parts = []
    open_books = []
    for book in BOOKS:
        episode = {"strategy": book}
        recovered = resolve(fact(EPISODES, "recovered_month", episode, scale="text"))
        parts.append(
            f"{LABELS[book]} {d.pct(perf(book, 'maximum_drawdown'))}, "
            f"du sommet de {d.text(fact(EPISODES, 'peak_month', episode, scale='text'))} "
            f"au creux de {d.text(fact(EPISODES, 'trough_month', episode, scale='text'))}"
        )
        if recovered is None or (isinstance(recovered, float) and np.isnan(recovered)):
            open_books.append(LABELS[book])
    tail = (
        f" À la fin de la fenêtre, le sommet n'est pas retrouvé pour : {', '.join(open_books)}."
        if open_books
        else " Les trois livres ont retrouvé leur sommet avant la fin de la fenêtre."
    )
    out.append(d.done("risques", f"Drawdown maximal : {'; '.join(parts)}.{tail}"))

    d = Draft()
    first, second = _top_pair()
    pair = fact(MATRIX, second, {"symbol": first})
    out.append(d.done("risques", (
        f"Corrélation : la moyenne des paires de la liste est de {d.num(fact(CORRELATION, 'average_correlation', op='last'))} "
        f"sur {d.count(fact(CORRELATION, 'names', op='last'))} titres. La paire la plus liée est "
        f"{d.label(_holding_name(first))} et {d.label(_holding_name(second))}, à {d.num(pair)}. "
        "Une corrélation moyenne basse ne protège pas dans un mois de baisse générale : les pires mois des trois livres sont proches."
    )))

    d = Draft()
    parts = []
    for book in BOOKS:
        parts.append(
            f"{LABELS[book]} {d.pct(report(book, 'top_10_weight'))} sur les 10 premières lignes, "
            f"{d.num(report(book, 'effective_holdings', 'raw'), 1)} lignes effectives, "
            f"premier secteur {d.label(resolve(report(book, 'largest_sector', 'text')))} à {d.pct(report(book, 'largest_sector_weight'))}"
        )
    d.facts.append(fact(MONITORING_MODULE, "TOP_POSITIONS"))
    out.append(d.done("risques", (
        f"Concentration au mois de {d.text(report('equal_weight', 'report_month', 'text'))} : {'; '.join(parts)}."
    )))

    d = Draft()
    parts = []
    for book in BOOKS:
        worst_shock = min(SHOCKS, key=lambda shock: float(resolve(stress(book, shock, "terminal_wealth"))))
        parts.append(
            f"{LABELS[book]} {d.num(stress(book, worst_shock, 'terminal_wealth'))} avec le choc "
            f"{SHOCK_LABELS[worst_shock].lower()}, contre {d.num(stress(book, 'aucun', 'terminal_wealth'))} sans choc"
        )
    out.append(d.done("risques", (
        "Tests de résistance, illustratifs : richesse finale la plus basse des quatre chocs, pour une unité investie. "
        f"{'; '.join(parts)}. Les chocs sont des paramètres écrits à l'avance, appliqués aux rendements déjà publiés. "
        "Ce ne sont pas des prévisions."
    )))
    return out


CAP_RULES = (
    ("le premier secteur", "largest_sector", "largest_sector_weight", "SECTOR_WEIGHT_CAP", "sector_over_cap"),
    ("la première zone", "largest_zone", "largest_zone_weight", "ZONE_WEIGHT_CAP", "zone_over_cap"),
    ("la première devise de cotation", "largest_currency", "largest_currency_weight", "CURRENCY_WEIGHT_CAP", "currency_over_cap"),
)


def _alerts():
    out = []
    d = Draft()
    flags = ("issuer_over_cap", "sector_over_cap", "zone_over_cap", "currency_over_cap", "positions_outside_band")
    names = ("émetteur", "secteur", "zone", "devise", "bande de lignes")
    total = sum(float(resolve(fact(LIMITS, flag, op="sum"))) for flag in flags)
    listed = ", ".join(f"{name} {d.count(fact(LIMITS, flag, op='sum'))}" for name, flag in zip(names, flags))
    lead = "Aucun dépassement de plafond sur la fenêtre." if total == 0 else "Des mois dépassent un plafond du mandat."
    out.append(d.done("alertes", (
        f"{lead} Nombre de mois-livres au-dessus d'une limite : {listed}. "
        f"Plafonds du mandat : émetteur {d.pct(config('ISSUER_WEIGHT_CAP'), 0)}, secteur {d.pct(config('SECTOR_WEIGHT_CAP'), 0)}, "
        f"zone {d.pct(config('ZONE_WEIGHT_CAP'), 0)}, devise {d.pct(config('CURRENCY_WEIGHT_CAP'), 0)}, "
        f"{d.count(config('MIN_POSITIONS', 'raw'))} à {d.count(config('MAX_POSITIONS', 'raw'))} lignes pour les livres optimisés."
    ), "constat" if total == 0 else "alerte"))

    watch = float(resolve(config("REPORTING_WATCH_RATIO")))
    for book in BOOKS:
        for name, label_column, weight_column, cap_name, _ in CAP_RULES:
            weight = float(resolve(report(book, weight_column)))
            cap = float(resolve(config(cap_name)))
            if weight < watch * cap:
                continue
            d = Draft()
            out.append(d.done("alertes", (
                f"{LABELS[book]} : {name} ({d.label(resolve(report(book, label_column, 'text')))}) pèse "
                f"{d.pct(report(book, weight_column))} pour un plafond de {d.pct(config(cap_name), 0)}. "
                f"Le poids dépasse {d.pct(config('REPORTING_WATCH_RATIO'), 0)} du plafond, seuil de vigilance du rapport et non limite du mandat."
            ), "alerte"))

    target = float(resolve(config("TRACKING_ERROR_TARGET")))
    above = [book for book in BOOKS if float(resolve(perf(book, "tracking_error"))) > target]
    d = Draft()
    listed = ", ".join(f"{LABELS[book]} {d.pct(perf(book, 'tracking_error'))}" for book in BOOKS)
    verdict = (
        f"Au-dessus de la cible : {', '.join(LABELS[book] for book in above)}."
        if above
        else "Les trois livres sont sous la cible."
    )
    out.append(d.done("alertes", (
        f"Écart de suivi mesuré contre le fonds : {listed}, pour une cible ex ante de {d.pct(config('TRACKING_ERROR_TARGET'), 0)} "
        f"dans la politique d'investissement. {verdict} La cible n'est pas appliquée aux poids publiés : c'est une mesure après coup."
    ), "alerte" if above else "constat"))

    reference = float(resolve(config("TEMPORARY_LOSS_REFERENCE")))
    beyond = [book for book in BOOKS if abs(float(resolve(perf(book, "maximum_drawdown")))) > reference]
    if beyond:
        d = Draft()
        listed = ", ".join(f"{LABELS[book]} {d.pct(perf(book, 'maximum_drawdown'))}" for book in beyond)
        out.append(d.done("alertes", (
            f"Drawdown maximal au-delà du repère de {d.pct(config('TEMPORARY_LOSS_REFERENCE'), 0)} du profil du client : {listed}. "
            "Le profil accepte une perte temporaire au-delà de ce repère et précise qu'il ne déclenche pas, à lui seul, une vente."
        ), "alerte"))

    d = Draft()
    quarterly = fact(TURNOVER, "over_quarterly_cap", op="sum")
    annual = fact(TURNOVER, "over_annual_cap", op="sum")
    out.append(d.done("alertes", (
        f"Rotation : {d.count(quarterly)} rééquilibrage au-dessus du plafond trimestriel de {d.pct(config('QUARTERLY_TURNOVER_CAP'), 1)} "
        f"et {d.count(annual)} au-dessus du plafond annuel. La rotation la plus forte observée est de "
        f"{d.pct(fact(TURNOVER, 'gross_turnover', op='max', scale='ratio'), 1)}."
    )))

    d = Draft()
    issues = pd.read_excel(resolve_path(QUALITY), sheet_name="Quality Issues")
    worst = issues.sort_values("issue_rate", ascending=False).iloc[0]
    where = {"issue_id": worst["issue_id"]}
    status = resolve(quality_summary("global_status", "text"))
    out.append(d.done("alertes", (
        f"Qualité des données : score global {d.pct(quality_summary('global_quality_score', 'percent'))}, "
        f"note {resolve(quality_summary('global_quality_grade', 'text'))}, statut {status}. "
        f"{d.count(fact(QUALITY, 'issue_id', op='count', sheet='Quality Issues'))} catégories d'anomalies sur "
        f"{d.count(fact(QUALITY, 'control_id', op='count', sheet='Quality Controls'))} contrôles. "
        f"La plus étendue : {worst['control_name'].lower()} sur la table {worst['table_name']}, "
        f"{d.count(fact(QUALITY, 'issue_count', where, sheet='Quality Issues'))} lignes sur "
        f"{d.count(fact(QUALITY, 'records_checked', where, sheet='Quality Issues'))}, "
        f"soit {d.pct(fact(QUALITY, 'issue_rate', where, scale='percent', sheet='Quality Issues'))}, gravité {worst['severity']}."
    ), "alerte" if str(status) != "PASS" else "constat"))

    d = Draft()
    pending = reconciliation("statut_power_bi", {"statut_power_bi": PENDING})
    power_ok = reconciliation("statut_power_bi", {"statut_power_bi": "OK"})
    power_exception = reconciliation("statut_power_bi", {"statut_power_bi": "EXCEPTION"})
    has_alert = float(resolve(pending)) > 0 or float(resolve(power_exception)) > 0
    out.append(d.done("alertes", (
        f"Colonne Power BI de la réconciliation : {d.count(power_ok)} lignes OK sur une valeur lue dans Power BI Desktop, "
        f"{d.count(power_exception)} en EXCEPTION, {d.count(pending)} en attente d'export."
    ), "alerte" if has_alert else "constat"))
    return out


def _points():
    out = []
    watch = float(resolve(config("REPORTING_WATCH_RATIO")))
    near = [
        book
        for book in BOOKS
        if any(
            float(resolve(report(book, weight))) >= watch * float(resolve(config(cap)))
            for _, _, weight, cap, _ in CAP_RULES
        )
    ]
    if near:
        d = Draft()
        out.append(d.done("points", (
            f"Faire revoir par le gérant, avant le prochain rééquilibrage, les livres proches d'un plafond : "
            f"{', '.join(LABELS[book] for book in near)}. Une hausse relative du premier secteur ou de la première zone "
            "suffirait à franchir la limite entre deux rééquilibrages."
        ), "point"))
    target = float(resolve(config("TRACKING_ERROR_TARGET")))
    if any(float(resolve(perf(book, "tracking_error"))) > target for book in BOOKS):
        d = Draft()
        out.append(d.done("points", (
            f"Décider si la cible d'écart de suivi de {d.pct(config('TRACKING_ERROR_TARGET'), 0)} doit entrer dans la construction des poids. "
            "Aujourd'hui elle est écrite dans la politique mais n'est pas appliquée."
        ), "point"))
    d = Draft()
    issues = pd.read_excel(resolve_path(QUALITY), sheet_name="Quality Issues")
    medium = issues.loc[issues["severity"].astype(str).isin(["MEDIUM", "HIGH", "CRITICAL"])]
    if len(medium):
        row = medium.sort_values("issue_rate", ascending=False).iloc[0]
        where = {"issue_id": row["issue_id"]}
        out.append(d.done("points", (
            f"Traiter l'anomalie de gravité {row['severity']} du contrôle qualité : {row['control_name'].lower()}, "
            f"{d.count(fact(QUALITY, 'issue_count', where, sheet='Quality Issues'))} titres de la table {row['table_name']} "
            "sans série de change. Ces titres ne peuvent pas être convertis en CHF et restent hors des livres."
        ), "point"))
    pending = float(resolve(reconciliation("statut_power_bi", {"statut_power_bi": PENDING})))
    if pending:
        d = Draft()
        out.append(d.done("points", (
            f"Compléter le modèle Power BI ou accepter l'écart de périmètre : "
            f"{d.count(reconciliation('statut_power_bi', {'statut_power_bi': PENDING}))} lignes de la réconciliation "
            "n'ont pas de mesure à exporter et restent en attente."
        ), "point"))
    d = Draft()
    out.append(d.done("points", (
        "Avant toute présentation comme performance réelle : obtenir des données de conservation "
        "(positions, transactions, frais, flux). La réconciliation prouve que les formules se recoupent, "
        "pas que les titres ont été détenus."
    ), "point"))
    d = Draft()
    out.append(d.done("points", (
        "Ajouter les dividendes au rendement des livres, ou comparer au rendement en prix du fonds, "
        "pour rendre la comparaison au fonds homogène."
    ), "point"))
    return out


def build_statements():
    """Every automated sentence, by section. Each one is already checked."""
    return {
        "faits": _highlights(),
        "risques": _risks(),
        "alertes": _alerts(),
        "points": _points(),
    }


def all_statements(sections):
    return [statement for name in SECTION_TITLES for statement in sections[name]]


def render_markdown(sections, generated):
    lines = [
        "# Commentaires automatisés",
        "",
        f"**{AUTO_LABEL}**",
        "",
        f"Produit par `python -m src.pipeline.refresh` le {generated}. {SCOPE_NOTE}",
        "",
        "Chaque nombre de ce texte est relu dans un fichier du pipeline par `src/reporting/number_check.py`. "
        "La liste des nombres et de leur source est dans `controle_des_nombres.csv`.",
    ]
    for name, title in SECTION_TITLES.items():
        lines += ["", f"## {title}", ""]
        for statement in sections[name]:
            mark = "**Alerte.** " if statement.kind == "alerte" else ""
            lines.append(f"- {mark}{statement.text}")
        if name == "points":
            lines += ["", DISCLAIMER]
    return "\n".join(lines) + "\n"


def write_commentary(sections, generated):
    EXECUTIVE_REPORTS.mkdir(parents=True, exist_ok=True)
    COMMENT_MD.write_text(render_markdown(sections, generated), encoding="utf-8")
    payload = {
        "mention": AUTO_LABEL,
        "genere_le": generated,
        "perimetre": SCOPE_NOTE,
        "avertissement": DISCLAIMER,
        "sections": {
            name: [
                {
                    "type": statement.kind,
                    "texte": statement.text,
                    "sources": [item.label() for item in statement.facts],
                }
                for statement in sections[name]
            ]
            for name in SECTION_TITLES
        },
    }
    COMMENT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return COMMENT_MD, COMMENT_JSON
