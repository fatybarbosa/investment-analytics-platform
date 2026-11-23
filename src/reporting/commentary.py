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

from src.config import (
    CAP_TOLERANCE,
    DATA_CONTROL_CENTER_FILE,
    EXCEL_REPORTS,
    EXECUTIVE_REPORTS,
    MONITORING_DATA,
    PERFORMANCE_DATA,
    PORTFOLIO_DATA,
    RISK_DATA,
    STRESS_DATA,
    source_id,
)
from src.reporting.number_check import AUTO_LABEL, Draft, fact, resolve


COMMENT_MD = EXECUTIVE_REPORTS / "commentaires_automatises.md"
COMMENT_JSON = EXECUTIVE_REPORTS / "commentaires_automatises.json"

METRICS = source_id(PORTFOLIO_DATA / "portfolio_metrics.csv")
MEMBERSHIP = source_id(PORTFOLIO_DATA / "portfolio_membership.csv")
PERFORMANCE = source_id(PERFORMANCE_DATA / "performance_metrics.csv")
EPISODES = source_id(PERFORMANCE_DATA / "drawdown_episode.csv")
RISK = source_id(RISK_DATA / "risk_by_strategy.csv")
TAIL = source_id(RISK_DATA / "var_tail.csv")
CORRELATION = source_id(RISK_DATA / "universe_correlation.csv")
MATRIX = source_id(RISK_DATA / "correlation_matrix.csv")
STRESS = source_id(STRESS_DATA / "stress_results.csv")
REPORT = source_id(MONITORING_DATA / "monthly_report.csv")
LIMITS = source_id(MONITORING_DATA / "limit_watch.csv")
TURNOVER = source_id(MONITORING_DATA / "turnover.csv")
HOLDINGS = source_id(MONITORING_DATA / "allocation_by_holding.csv")
PATH = source_id(MONITORING_DATA / "portfolio_path.csv")
FUND_RETURNS = source_id(PERFORMANCE_DATA / "benchmark_monthly_return.csv")
QUALITY = source_id(DATA_CONTROL_CENTER_FILE)
ANNEX = source_id(EXCEL_REPORTS / "annexe_reporting.xlsx")
EXPORT = source_id(EXCEL_REPORTS / "power_bi_export.csv")
CONFIG = "py:src.config"
RISK_MODULE = "py:src.risk.build_risk"
MONITORING_MODULE = "py:src.portfolio_monitoring.build_monitoring"
STRESS_MODULE = "py:src.stress_testing.build_stress"
FEASIBILITY = source_id(MONITORING_DATA / "mandate_feasibility.csv")

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
BASIS_NOTE = (
    "Les livres sont mesurés en rendement total brut : dividendes réinvestis par le cours ajusté, avant frais et avant impôt à la source. "
    "Le fonds est mesuré par le rendement de sa valeur liquidative, net de ses frais : la comparaison avantage donc les livres."
)
SCOPE_NOTE = (
    f"{PORTFOLIO_LABEL} : ils n'ont jamais été détenus. {REAL_DATA_NOTE} "
    "Pas de données de conservation et pas de frais. "
    + BASIS_NOTE
)
UNIVERSE_NOTE = (
    "La liste de titres est la composition actuelle du fonds de référence, et l'éligibilité ODD a été jugée à la date de saisie du registre puis appliquée à tout l'historique : "
    "les sociétés sorties du fonds n'y figurent pas, ce qui peut embellir le résultat."
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
    d = Draft()
    listed = ", ".join(
        f"{LABELS[book]} {d.pct(perf(book, 'annualized_return'))}" for book in BOOKS
    )
    above = [book for book in BOOKS if float(resolve(perf(book, "annualized_return"))) > fund_return]
    if not above:
        verdict = "Aucun livre ne dépasse le fonds sur la fenêtre."
    elif len(above) == len(BOOKS):
        verdict = f"Les trois livres dépassent le fonds sur la fenêtre, le livre {LABELS[best]} le plus nettement."
    else:
        verdict = (
            f"{'Le livre' if len(above) == 1 else 'Les livres'} "
            + ", ".join(LABELS[book] for book in above)
            + f" dépasse{'nt' if len(above) > 1 else ''} le fonds sur la fenêtre."
        )
    out.append(d.done("faits", (
        f"Rendement annualisé en CHF : {listed}, contre {d.pct(perf(FUND, 'annualized_return'))} "
        f"pour le fonds iShares, rendement de la valeur liquidative converti en CHF. {verdict} "
        + BASIS_NOTE
    ), tag="rendement"))

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
    ), tag="volatilite"))

    d = Draft()
    level = fact(RISK_MODULE, "VAR_LEVEL", scale="ratio")
    listed = "; ".join(
        f"{LABELS[book]} VaR {d.pct(risk(book, 'var_95'))} et expected shortfall {d.pct(risk(book, 'expected_shortfall_95'))}"
        for book in BOOKS + (FUND,)
    )
    out.append(d.done("risques", (
        f"Perte mensuelle historique, lue sur les {d.pct(level, 0)} de mois les plus défavorables : {listed}. "
        "Ce sont des rendements mensuels observés, sans loi normale et sans annualisation."
    ), tag="var"))

    d = Draft()
    months = fact(RISK, "months", {"strategy": "equal_weight"})
    tail_size = fact(TAIL, "rank", {"strategy": "equal_weight"}, op="count")
    out.append(d.done("risques", (
        f"Limite de l'échantillon : la VaR est lue sur {d.count(months)} mois, et l'expected shortfall est la moyenne des {d.count(tail_size)} pires mois. "
        "Ce sont de petits échantillons : aucun intervalle de confiance n'est calculé, et un seul mois de plus ou de moins déplace ces chiffres."
    ), tag="echantillon"))

    d = Draft()
    parts = []
    for book in BOOKS:
        worst_month = fact(TAIL, "month", {"strategy": book, "rank": 1}, scale="text")
        worst = fact(TAIL, "portfolio_return", {"strategy": book, "rank": 1}, scale="ratio")
        parts.append(f"{LABELS[book]} {d.pct(worst)} en {d.text(worst_month)}")
    out.append(d.done("risques", f"Pire mois de la fenêtre : {', '.join(parts)}.", tag="pire_mois"))

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
    out.append(d.done("risques", f"Drawdown maximal : {'; '.join(parts)}.{tail}", tag="drawdown"))

    d = Draft()
    first, second = _top_pair()
    pair = fact(MATRIX, second, {"symbol": first})
    out.append(d.done("risques", (
        f"Corrélation : la moyenne des paires de la liste est de {d.num(fact(CORRELATION, 'average_correlation', op='last'))} "
        f"sur {d.count(fact(CORRELATION, 'names', op='last'))} titres. La paire la plus liée est "
        f"{d.label(_holding_name(first))} et {d.label(_holding_name(second))}, à {d.num(pair)}. "
        "Une corrélation moyenne basse ne protège pas dans un mois de baisse générale : les pires mois des trois livres sont proches."
    ), tag="correlation"))

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
    ), tag="concentration"))

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
    ), tag="chocs"))

    d = Draft()
    shock = float(resolve(fact(CONFIG, "MARKET_SHOCK_RETURN")))
    worst_observed = min(float(resolve(fact(TAIL, "portfolio_return", {"strategy": book, "rank": 1}))) for book in BOOKS)
    harsher = "plus sévère" if shock < worst_observed else "moins sévère"
    worst_book = min(BOOKS, key=lambda book: float(resolve(fact(TAIL, "portfolio_return", {"strategy": book, "rank": 1}))))
    out.append(d.done("risques", (
        f"Le choc de marché ({d.pct(config('MARKET_SHOCK_RETURN'), 0)} sur le dernier mois) est {harsher} que le pire mois réellement observé "
        f"({d.pct(fact(TAIL, 'portfolio_return', {'strategy': worst_book, 'rank': 1}, scale='ratio'))}, livre {LABELS[worst_book]}). "
        "Le choc de taux ne change pas le rendement des actions : il ne modifie que le taux sans risque, donc le ratio de Sharpe. "
        "Ce n'est pas un test de sensibilité des titres aux taux. Aucun scénario daté n'est rejoué en dehors des pires mois observés ci-dessus."
    ), tag="chocs_limites"))

    d = Draft()
    out.append(d.done("risques", (
        f"Éligibilité ODD : sur {d.count(fact(MEMBERSHIP, 'yahoo_symbol', op='count'))} titres examinés, "
        f"{d.count(fact(MEMBERSHIP, 'yahoo_symbol', {'odd_status': 'Eligible'}, op='count'))} sont Eligible, "
        f"{d.count(fact(MEMBERSHIP, 'yahoo_symbol', {'odd_status': 'Indeterminate'}, op='count'))} Indeterminate et "
        f"{d.count(fact(MEMBERSHIP, 'yahoo_symbol', {'odd_status': 'Not_Eligible'}, op='count'))} Not_Eligible. "
        "Les statuts sont saisis par un seul analyste à partir de rapports de sociétés qui ne sont pas versionnés : un tiers ne peut pas les rejouer depuis ce dépôt. "
        + UNIVERSE_NOTE
    ), tag="odd"))
    return out


CAP_RULES = (
    ("le premier secteur", "largest_sector", "largest_sector_weight", "SECTOR_WEIGHT_CAP", "sector_over_cap"),
    ("la première zone", "largest_zone", "largest_zone_weight", "ZONE_WEIGHT_CAP", "zone_over_cap"),
    ("la première devise de cotation", "largest_currency", "largest_currency_weight", "CURRENCY_WEIGHT_CAP", "currency_over_cap"),
)


def _breaches(where):
    """Month-books above each cap, for the months that match `where`."""
    flags = ("issuer_over_cap", "sector_over_cap", "zone_over_cap", "currency_over_cap", "positions_outside_band")
    return {flag: fact(LIMITS, flag, where, op="sum") for flag in flags}


def _alerts():
    out = []
    names = {
        "issuer_over_cap": "émetteur",
        "sector_over_cap": "secteur (plafond de travail)",
        "zone_over_cap": "zone",
        "currency_over_cap": "devise",
        "positions_outside_band": "bande de lignes",
    }

    d = Draft()
    decided = _breaches({"rebalance_month": 1})
    total = sum(float(resolve(item)) for item in decided.values())
    listed = ", ".join(f"{names[flag]} {d.count(item)}" for flag, item in decided.items())
    lead = (
        "Aux dates de décision, aucun livre ne dépasse un plafond de construction."
        if total == 0
        else "Aux dates de décision, des livres dépassent un plafond de construction."
    )
    out.append(d.done("alertes", (
        f"{lead} Mois-livres au-dessus d'une limite, comptés sur les {d.count(fact(LIMITS, 'month', {'rebalance_month': 1}, op='count'))} "
        f"mois-livres de décision (début de trimestre) : {listed}. "
        f"Plafonds : émetteur {d.pct(config('ISSUER_WEIGHT_CAP'), 0)}, zone {d.pct(config('ZONE_WEIGHT_CAP'), 0)}, "
        f"devise {d.pct(config('CURRENCY_WEIGHT_CAP'), 0)}, secteur {d.pct(config('SECTOR_WEIGHT_CAP'), 0)} (plafond de travail, voir ci-dessous), "
        f"{d.count(config('MIN_POSITIONS', 'raw'))} à {d.count(config('MAX_POSITIONS', 'raw'))} lignes pour les livres optimisés."
    ), "constat" if total == 0 else "alerte", tag="limites_decision"))

    d = Draft()
    passive = _breaches({"rebalance_month": 0})
    passive_total = sum(float(resolve(passive[flag])) for flag in ("issuer_over_cap", "sector_over_cap", "zone_over_cap", "currency_over_cap"))
    listed = ", ".join(
        f"{names[flag]} {d.count(passive[flag])}" for flag in ("issuer_over_cap", "sector_over_cap", "zone_over_cap", "currency_over_cap")
    )
    out.append(d.done("alertes", (
        f"Entre deux décisions, les poids dérivent avec le marché et un livre ne se corrige qu'au rééquilibrage suivant. "
        f"Dépassements passifs, en mois-livres sur {d.count(fact(LIMITS, 'month', {'rebalance_month': 0}, op='count'))} : {listed}. "
        f"Le plus gros poids d'un titre atteint {d.pct(fact(LIMITS, 'largest_issuer_weight', op='max', scale='ratio'))} "
        f"pour un plafond de {d.pct(config('ISSUER_WEIGHT_CAP'), 0)}. "
        "Le mandat ne dit pas si un dépassement passif est toléré jusqu'au prochain rééquilibrage : la décision est à prendre."
    ), "alerte" if passive_total > 0 else "constat", tag="passifs"))

    d = Draft()
    capacity = float(resolve(fact(FEASIBILITY, "capacity_ips", {"sector": "TOTAL"})))
    infeasible = capacity < 1.0 - CAP_TOLERANCE
    breach_item = fact(LIMITS, "sector_over_ips_cap", op="sum")
    feasibility_text = (
        f"Sur cette liste, un livre entièrement investi ne peut pas respecter ce plafond : au plus "
        f"{d.pct(fact(FEASIBILITY, 'capacity_ips', {'sector': 'TOTAL'}, scale='ratio'), 0)} du livre peut être placé "
        f"sous le plafond d'émetteur de {d.pct(config('ISSUER_WEIGHT_CAP'), 0)} et ce plafond de secteur. "
        f"Les livres sont donc construits avec un plafond de travail de {d.pct(config('SECTOR_WEIGHT_CAP'), 0)}, "
        "qui n'a pas été approuvé par le client. "
        if infeasible
        else "Un livre entièrement investi peut respecter ce plafond sur cette liste. "
    )
    out.append(d.done("alertes", (
        f"Plafond de secteur écrit dans le mandat : {d.pct(config('IPS_SECTOR_WEIGHT_CAP'), 0)}. "
        f"Il est dépassé dans {d.count(breach_item)} mois-livres sur {d.count(fact(LIMITS, 'month', op='count'))}. "
        + feasibility_text
        + "C'est un écart ouvert entre le mandat et la construction, pas une conformité."
    ), "alerte" if float(resolve(breach_item)) > 0 else "constat", tag="ips_secteur"))

    watch = float(resolve(config("REPORTING_WATCH_RATIO")))
    for book in BOOKS:
        for name, label_column, weight_column, cap_name, _ in CAP_RULES:
            weight = float(resolve(report(book, weight_column)))
            cap = float(resolve(config(cap_name)))
            if weight < watch * cap:
                continue
            d = Draft()
            cap_label = "plafond de travail" if cap_name == "SECTOR_WEIGHT_CAP" else "plafond"
            out.append(d.done("alertes", (
                f"{LABELS[book]} : {name} ({d.label(resolve(report(book, label_column, 'text')))}) pèse "
                f"{d.pct(report(book, weight_column))} pour un {cap_label} de {d.pct(config(cap_name), 0)}. "
                f"Le poids dépasse {d.pct(config('REPORTING_WATCH_RATIO'), 0)} du plafond, seuil de vigilance du rapport et non limite du mandat."
            ), "alerte", tag="vigilance"))

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
    ), "alerte" if above else "constat", tag="suivi"))

    reference = float(resolve(config("TEMPORARY_LOSS_REFERENCE")))
    beyond = [book for book in BOOKS if abs(float(resolve(perf(book, "maximum_drawdown")))) > reference]
    if beyond:
        d = Draft()
        listed = ", ".join(f"{LABELS[book]} {d.pct(perf(book, 'maximum_drawdown'))}" for book in beyond)
        out.append(d.done("alertes", (
            f"Drawdown maximal au-delà du repère de {d.pct(config('TEMPORARY_LOSS_REFERENCE'), 0)} du profil du client : {listed}. "
            "Le profil accepte une perte temporaire au-delà de ce repère et précise qu'il ne déclenche pas, à lui seul, une vente."
        ), "alerte", tag="drawdown_repere"))

    d = Draft()
    turnover_alert = 0.0
    parts = []
    for book in BOOKS:
        quarterly = fact(TURNOVER, "over_quarterly_cap", {"strategy": book}, op="sum")
        annual = fact(TURNOVER, "over_annual_cap", {"strategy": book}, op="sum")
        turnover_alert += float(resolve(quarterly)) + float(resolve(annual))
        parts.append(f"{LABELS[book]} : plafond trimestriel dépassé {d.count(quarterly)} fois, plafond annuel dépassé {d.count(annual)} fois")
    out.append(d.done("alertes", (
        f"Rotation brute, mesurée contre le livre que le marché a laissé, dérive comprise : {'; '.join(parts)}. "
        f"Plafonds : {d.pct(config('QUARTERLY_TURNOVER_CAP'), 1)} par trimestre. La rotation la plus forte observée est de "
        f"{d.pct(fact(TURNOVER, 'gross_turnover', op='max', scale='ratio'), 1)}. "
        "À la date de transaction, les plafonds de poids priment sur le budget de rotation : quand les deux ne tiennent pas ensemble, la rotation dépasse."
    ), "alerte" if turnover_alert > 0 else "constat", tag="rotation"))

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
    ), "alerte" if str(status) != "PASS" else "constat", tag="qualite"))

    d = Draft()
    market = issues.loc[issues["table_name"].astype(str).eq("market_prices")].iloc[0]
    out.append(d.done("alertes", (
        f"Le score de qualité est pondéré par les enregistrements : {d.count(fact(QUALITY, 'records_checked', {'issue_id': market['issue_id']}, sheet='Quality Issues'))} lignes de cours "
        f"sur {d.count(quality_summary('records_checked'))} enregistrements contrôlés. Il masque donc les défauts qui touchent peu de lignes mais des titres entiers : "
        f"le contrôle de cohérence des devises signale {d.count(issue_item('DS-002', 'QC-005', 'issue_count'))} titres sur {d.count(issue_item('DS-002', 'QC-005', 'records_checked'))} "
        f"({d.pct(issue_item('DS-002', 'QC-005', 'issue_rate', 'percent'))}) sans série de change."
    ), "constat", tag="qualite_ponderation"))

    d = Draft()
    pending = reconciliation("statut_power_bi", {"statut_power_bi": PENDING})
    power_ok = reconciliation("statut_power_bi", {"statut_power_bi": "OK"})
    power_exception = reconciliation("statut_power_bi", {"statut_power_bi": "EXCEPTION"})
    recomputed = reconciliation("nature_power_bi", {"nature_power_bi": "recalcul DAX"})
    echoed = reconciliation("nature_power_bi", {"nature_power_bi": "relecture"})
    has_alert = float(resolve(pending)) > 0 or float(resolve(power_exception)) > 0
    out.append(d.done("alertes", (
        f"Colonne Power BI de la réconciliation : {d.count(power_ok)} lignes OK sur une valeur lue dans Power BI Desktop, "
        f"{d.count(power_exception)} en EXCEPTION, {d.count(pending)} en attente d'export. "
        f"Sur ces lignes, {d.count(recomputed)} sont recalculées en DAX à partir des rendements et {d.count(echoed)} relisent la cellule publiée : "
        "ces dernières prouvent le chargement du bon fichier, pas un second calcul."
    ), "alerte" if has_alert else "constat", tag="power_bi"))
    return out


def issue_item(dataset, control, column, scale="raw"):
    return fact(QUALITY, column, {"dataset_id": dataset, "control_id": control}, scale=scale, sheet="Quality Issues")


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
    capacity = float(resolve(fact(FEASIBILITY, "capacity_ips", {"sector": "TOTAL"})))
    if capacity < 1.0 - CAP_TOLERANCE:
        d = Draft()
        out.append(d.done("points", (
            f"Faire approuver ou refuser par le client le plafond de travail de secteur de {d.pct(config('SECTOR_WEIGHT_CAP'), 0)}, "
            f"contre {d.pct(config('IPS_SECTOR_WEIGHT_CAP'), 0)} écrit dans le mandat. Tant qu'il ne l'est pas, le dépassement du plafond écrit reste ouvert."
        ), "point"))
    d = Draft()
    out.append(d.done("points", (
        "Décider du traitement des dépassements passifs : toléré jusqu'au rééquilibrage suivant, ou corrigé dès qu'il apparaît. "
        "Le mandat ne le dit pas."
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
        "pas que les titres ont été détenus, ni que les définitions sont les bonnes."
    ), "point"))
    d = Draft()
    out.append(d.done("points", (
        "Rendre la comparaison au fonds strictement homogène : le rendement total des livres est brut de frais et d'impôt à la source, "
        "celui du fonds est net de ses frais. Il manque une série de rendement du fonds avant frais."
    ), "point"))
    return out


def pick(statements, tag):
    """The statements of a section that carry a tag."""
    return [statement for statement in statements if statement.tag == tag]


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
