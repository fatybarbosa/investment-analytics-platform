"""
Phase 11b. Investigation cases, written from the pipeline files.

Each case has a symptom, a cause, a decision and a trace. The numbers
come from the quality workbook, the membership file, the exclusion file
and the module constants. Nothing is typed by hand, and the text is
checked by src.reporting.number_check after it is written.

The cases describe what the pipeline did with a defect. They do not
describe a correction: a missing rate or a bad bar is left out, with
its reason written, and the controls stay as they are.

Output
------
reports/executive/cas_d_investigation.md
"""

from __future__ import annotations

from src.config import CAPITAL_RETURNS_FILE, EXECUTIVE_REPORTS, PROCESSED_MARKET, source_id
from src.reporting.commentary import FUND_RETURNS, MEMBERSHIP, QUALITY, config
from src.reporting.number_check import AUTO_LABEL, Draft, fact, resolve


CASES_FILE = EXECUTIVE_REPORTS / "cas_d_investigation.md"
EXCLUSIONS = source_id(PROCESSED_MARKET / "market_price_exclusions.csv")
ACTIONS = source_id(PROCESSED_MARKET / "corporate_action_check.csv")
CAPITAL = source_id(CAPITAL_RETURNS_FILE)
FUND_MODULE = "py:src.performance.benchmark_return"


def issue(dataset, control, column, scale="raw"):
    return fact(QUALITY, column, {"dataset_id": dataset, "control_id": control}, scale=scale, sheet="Quality Issues")


def exclusions(reason):
    return fact(EXCLUSIONS, "symbol", {"reason": reason}, op="count")


def _case_fx():
    import pandas as pd

    from src.config import PROJECT_ROOT

    members = pd.read_csv(PROJECT_ROOT / MEMBERSHIP)
    blocked = members.loc[members["history_reason"].astype(str).eq("no_snb_series")]
    currencies = sorted(blocked["listing_currency"].astype(str).unique())
    d = Draft()
    per_currency = ", ".join(
        f"{d.label(currency)} {d.count(fact(MEMBERSHIP, 'yahoo_symbol', {'history_reason': 'no_snb_series', 'listing_currency': currency}, op='count'))}"
        for currency in currencies
    )
    return [
        d.done("cas change", (
            f"Symptôme. Le contrôle de cohérence des devises signale {d.count(issue('DS-002', 'QC-005', 'issue_count'))} titres "
            f"du référentiel sur {d.count(issue('DS-002', 'QC-005', 'records_checked'))} sans série de change, "
            f"gravité {resolve(issue('DS-002', 'QC-005', 'severity', 'text'))}. Par devise : {per_currency}."
        )),
        plain_case(
            "Cause. Le cube de change de la Banque nationale suisse ne publie pas ces devises. "
            "Un cours en devise sans taux contre le franc ne peut pas être converti."
        ),
        d2_decision(),
        plain_case(
            "Trace. Le fichier des exclusions de cours garde chaque séance écartée avec sa raison, "
            "le fichier d'appartenance garde le titre avec la cause, et le contrôle reste en avertissement à chaque passage. "
            "Aucun taux croisé n'a été construit à partir d'une autre devise."
        ),
    ]


def d2_decision():
    d = Draft()
    return d.done("cas change", (
        f"Décision. Les titres restent hors des livres, dont {d.count(fact(MEMBERSHIP, 'yahoo_symbol', {'reason': 'no_snb_series'}, op='count'))} "
        "au statut Eligible qui seraient entrés sinon. Le pipeline n'invente pas de taux. "
        "La tolérance du contrôle n'a pas été modifiée pour faire passer la table."
    ))


def _case_prices():
    d = Draft()
    return [
        d.done("cas cours", (
            f"Symptôme. Sur {d.count(issue('DS-003', 'QC-003', 'records_checked'))} séances de cours, "
            f"{d.count(exclusions('outside_high_low'))} ont une clôture hors de la fourchette plus haut / plus bas ou négative, "
            f"et {d.count(issue('DS-003', 'QC-001', 'issue_count'))} ont un champ obligatoire vide."
        )),
        plain_case(
            "Cause. Les séances viennent d'une source gratuite, avec des barres incomplètes ou incohérentes sur certaines places. "
            "Une clôture hors fourchette ne peut pas être vraie en même temps que son plus haut et son plus bas."
        ),
        d.done("cas cours", (
            f"Décision. Chaque séance fautive est retirée de la série en CHF et inscrite dans le fichier des exclusions avec sa raison : "
            f"{d.count(exclusions('outside_high_low'))} séances hors fourchette et {d.count(exclusions('missing_close'))} sans clôture. "
            f"Aucune valeur n'est interpolée. "
            f"Le même fichier garde {d.count(exclusions('no_snb_series'))} séances sans série de change et "
            f"{d.count(exclusions('missing_monthly_fx'))} séances sans taux de fin de mois."
        )),
        plain_case(
            "Trace. Le contrôle reste en avertissement sur la table des cours. "
            "Le fichier des exclusions est relu par cette note à chaque génération."
        ),
    ]


def _flagged(check, reason=None):
    """Names behind one corporate-action check, read from the check file and the membership."""
    import pandas as pd

    from src.config import PROJECT_ROOT

    actions = pd.read_csv(PROJECT_ROOT / ACTIONS)
    names = sorted(actions.loc[actions["check"].eq(check), "symbol"].astype(str).unique())
    members = pd.read_csv(PROJECT_ROOT / MEMBERSHIP)
    known = members.set_index("yahoo_symbol")
    if reason is not None:
        return [s for s in names if s in known.index and str(known.loc[s, "reason"]) == reason]
    eligible = set(members.loc[members["odd_status"].eq("Eligible"), "yahoo_symbol"])
    return [s for s in names if s in eligible]


def pd_register():
    """The declared returns of capital."""
    import pandas as pd

    return pd.read_csv(CAPITAL_RETURNS_FILE, dtype={"symbol": str})


def _case_dividends():
    d = Draft()
    ignored = _flagged("adjusted_close_without_dividend")
    dropped = _flagged("dividend_above_limit", "dividend_not_comparable")
    splits = _flagged("split_not_adjusted")
    listed = lambda names: ", ".join(d.label(name) for name in names) if names else "aucun"

    def rows(check, symbol):
        return d.count(fact(ACTIONS, "symbol", {"check": check, "symbol": symbol}, op="count"))

    per_name = ", ".join(f"{d.label(s)} {rows('adjusted_close_without_dividend', s)}" for s in ignored) or "aucun"
    above = ", ".join(f"{d.label(s)} {rows('dividend_above_limit', s)}" for s in dropped) or "aucun"
    declared = pd_register()
    added = " ".join(
        f"{d.label(row.symbol)} : {d.count(fact(CAPITAL, 'cash_per_old_share', {'symbol': row.symbol}))} pence par ancienne action, "
        f"avec un regroupement de {d.count(fact(CAPITAL, 'old_shares', {'symbol': row.symbol}))} actions en "
        f"{d.count(fact(CAPITAL, 'new_shares', {'symbol': row.symbol}))}."
        for row in declared.itertuples(index=False)
    )
    return [
        d.done("cas dividendes", (
            f"Symptôme. Le cours ajusté du fournisseur ne reprend pas des dividendes déclarés. Titres éligibles concernés, "
            f"avec le nombre de dividendes ignorés sur tout l'historique : {per_name}. "
            f"Des dividendes dépassent aussi {d.pct(config('DIVIDEND_YIELD_LIMIT'), 0)} du cours précédent : {above}."
        )),
        plain_case(
            "Cause. L'ajustement du fournisseur n'est pas le même d'une place à l'autre. Pour un titre scindé, le cours passé a été "
            "retraité et le dividende ne l'a pas été : les deux ne sont plus sur la même base."
        ),
        d.done("cas dividendes", (
            f"Versement absent des données, ajouté depuis la publication de la société. {added} Le montant est ramené à la base "
            "des cours et la source est écrite dans le registre."
        )),
        d.done("cas dividendes", (
            "Décision. Le rendement total est reconstruit de la même façon pour tous les titres : le cours de clôture, avec chaque "
            "dividende déclaré réinvesti au cours du jour de détachement. Le cours ajusté reste dans le fichier et ne mesure plus "
            f"aucun rendement. Sort des livres, avec le motif dividend_not_comparable : {listed(dropped)}. "
            f"Une opération sur titres que le cours ne reflète pas est signalée et n'est pas corrigée : {listed(splits)}."
        )),
        plain_case(
            "Trace. Les versements déclarés sont dans data/01_raw/corporate_actions/capital_returns.csv. Chaque anomalie est une ligne "
            "de data/02_processed/market/corporate_action_check.csv, avec la séance et le cours de référence. Le contrôle des valeurs aberrantes compte les dividendes au-dessus de la limite."
        ),
    ]


def _case_fund_unit():
    import pandas as pd

    from src.config import PROJECT_ROOT

    fund = pd.read_csv(PROJECT_ROOT / FUND_RETURNS)
    currency = str(fund["fund_currency"].iloc[0])
    d = Draft()
    return [
        plain_case(
            "Symptôme. La feuille de performance publiée par le fonds donne un rendement mensuel sans indiquer son unité : "
            "décimal ou points de pourcentage. Lire la mauvaise unité multiplierait l'écart de suivi par cent."
        ),
        d.done("cas unité", (
            f"Cause. La colonne n'a pas d'étiquette. Le module compare le rendement publié à la variation de la valeur liquidative "
            f"sur au moins {d.count(fact(FUND_MODULE, 'MINIMUM_UNIT_CHECKS'))} mois sans distribution, "
            f"à {d.sci(fact(FUND_MODULE, 'UNIT_TOLERANCE'))} près, dans les deux unités."
        )),
        d.done("cas unité", (
            f"Décision. L'unité retenue est celle qui coïncide avec la valeur liquidative. Si aucune ne coïncide, le module s'arrête. "
            f"La série acceptée compte {d.count(fact(FUND_RETURNS, 'month', op='count'))} mois en {d.label(currency)}, "
            f"convertis en CHF avec le taux de fin de mois de la Banque nationale suisse."
        )),
        plain_case(
            "Trace. Le fichier de rendement du fonds garde, pour chaque mois, le rendement publié, le taux de change du mois et du mois précédent, "
            "et le rendement en CHF qui en résulte. L'annexe Excel le reconstruit à partir de ces colonnes."
        ),
    ]


def _case_history():
    d = Draft()
    return [
        d.done("cas historique", (
            f"Symptôme. {d.count(fact(MEMBERSHIP, 'yahoo_symbol', {'history_reason': 'incomplete_monthly_history'}, op='count'))} titres "
            f"du référentiel n'ont pas une clôture de fin de mois en CHF sur chaque mois de la fenêtre, "
            f"dont {d.count(fact(MEMBERSHIP, 'yahoo_symbol', {'reason': 'incomplete_monthly_history'}, op='count'))} au statut Eligible."
        )),
        plain_case(
            "Cause. Introduction en bourse après le début de la fenêtre, séances écartées par le contrôle des cours, "
            "ou mois sans taux de change de fin de mois."
        ),
        plain_case(
            "Décision. Un titre sans historique complet n'entre dans aucun livre. Les trois livres partagent une seule liste, "
            "pour que leurs rendements soient comparables sur les mêmes mois. Aucun cours n'est reconstitué."
        ),
        plain_case(
            "Trace. Le fichier d'appartenance garde la décision et la cause par titre, "
            "avec le nombre de mois disponibles et le nombre requis."
        ),
    ]


def plain_case(text):
    from src.reporting.number_check import Statement

    statement = Statement("cas", text)
    statement.check()
    return statement


CASES = (
    ("Titres sans série de change", _case_fx),
    ("Clôtures manquantes et cours hors fourchette", _case_prices),
    ("Dividendes et opérations sur titres", _case_dividends),
    ("Unité du rendement publié du fonds", _case_fund_unit),
    ("Historiques incomplets", _case_history),
)


def build_investigations(generated):
    """Write the cases. Return the file and its statements."""
    statements = []
    lines = [
        "# Cas d'investigation sur les données",
        "",
        f"**{AUTO_LABEL}**",
        "",
        f"Produit par le pipeline le {generated}. Chaque nombre est relu dans un fichier du pipeline. "
        "Les cas décrivent ce que le pipeline a fait d'un défaut : il l'écarte et l'écrit, il ne le corrige pas en silence.",
    ]
    for title, builder in CASES:
        built = builder()
        statements.extend(built)
        lines += ["", f"## {title}", ""]
        lines += [f"- {statement.text}" for statement in built]
    EXECUTIVE_REPORTS.mkdir(parents=True, exist_ok=True)
    CASES_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return CASES_FILE, statements
