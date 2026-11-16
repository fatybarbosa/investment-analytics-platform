"""
Phase 11b. Two customized monthly reports from the same published files.

CLIENT001 is the only client. One report is written for that client.
The other is written for the manager who follows the same books.
Both read the same files.

Client report : sector, region, currency, written limits, performance
against the fund, risk. Nothing at security level.

Manager report : the ten largest lines, the names that contributed most
and least over the window, the weight movements of the last rebalance,
currency exposure. Nothing on limits or stress.

Every sentence and every table cell is a Statement checked against the
pipeline files. The weight movements are those of a hypothetical book:
no order was placed, there is no transaction record.

Outputs
-------
reports/clients/rapport_client.pdf
reports/clients/rapport_gerant.pdf
reports/clients/monthly_report_client.pdf
reports/clients/monthly_report_manager.pdf
"""

from __future__ import annotations

import pandas as pd
from reportlab.lib.units import mm

from src.config import CLIENT_REPORTS, PROJECT_ROOT
from src.reporting import report_content as content
from src.reporting.commentary import (
    BOOKS,
    FUND,
    LABELS,
    MONTHS,
    PORTFOLIO_LABEL,
    REAL_DATA_NOTE,
    TURNOVER,
    WINDOW_END,
    WINDOW_START,
    config,
    perf,
    report,
)
from src.reporting.executive_report import LABEL, Report, SMALL, plain, read_report
from src.reporting.number_check import AUTO_LABEL, Draft, Statement, fact, resolve


PENSION_FILE = CLIENT_REPORTS / "rapport_client.pdf"
MANAGER_FILE = CLIENT_REPORTS / "rapport_gerant.pdf"
PENSION_FILE_EN = CLIENT_REPORTS / "monthly_report_client.pdf"
MANAGER_FILE_EN = CLIENT_REPORTS / "monthly_report_manager.pdf"
CLIENT_REPORT_MAX_PAGES = 4

SECTORS = "data/05_monitoring/allocation_by_sector.csv"
ZONES = "data/05_monitoring/allocation_by_zone.csv"
EXPOSURE = "data/05_monitoring/exposure.csv"
TOP10 = "data/05_monitoring/top10_positions.csv"
HOLDING_CONTRIBUTION = "data/05_monitoring/holding_contribution.csv"
WEIGHT_CHANGES = "data/05_monitoring/weight_changes.csv"
TOP_LINES = 5
NOT_HELD = "–"

PENSION_NEEDS = (
    "Rapport remis au client CLIENT001 : la répartition par secteur, zone et devise, la situation face à chaque limite "
    "écrite, la performance contre le fonds de référence en CHF, et les mesures de risque. "
    "Le client ne reçoit pas le détail des lignes."
)
MANAGER_NEEDS = (
    "Rapport remis au gérant des livres de CLIENT001 : les dix premières lignes de chaque livre, les titres qui ont le plus contribué "
    "et le plus pesé sur la période, les mouvements de poids du dernier rééquilibrage, et l'exposition par devise. "
    "Le gérant ne retrouve ici ni les limites du mandat, ni les tests de résistance."
)
MOVEMENT_NOTE = (
    "Les mouvements de poids sont ceux d'un livre hypothétique, recalculé chaque trimestre. "
    "Aucun ordre n'a été passé : ce ne sont pas des transactions, et il n'y a pas de relevé de dépositaire."
)
PENSION_NEEDS_EN = (
    "Report for the client CLIENT001: allocation by sector, region and currency, the position against each "
    "written limit, performance against the reference fund in CHF, and the risk measures. "
    "The client does not receive security-level detail."
)
MANAGER_NEEDS_EN = (
    "Report for the manager of the CLIENT001 books: the ten largest lines of each book, the names that contributed most "
    "and least over the window, the weight movements of the last rebalance, and currency exposure. "
    "The manager does not find the mandate limits or the stress tests here."
)
MOVEMENT_NOTE_EN = (
    "The weight movements are those of a hypothetical book, recalculated each quarter. "
    "No order was placed: these are not transactions, and there is no custody statement."
)
SCOPE_EN = (
    "Hypothetical portfolios built retrospectively on public data. They were never held. "
    "Prices, exchange rates and the SARON rate are real public data. The three books share the same "
    "list of names and are compared with the iShares MSCI Global Sustainable Development Goals fund, "
    "whose published return is converted into CHF. The books' return does not include dividends; the fund's does. "
    "There is no custody data. "
)


def _frame(source):
    return pd.read_csv(PROJECT_ROOT / source)


def _scope(client_needs, lang="fr"):
    if lang == "en":
        return plain("scope", SCOPE_EN + client_needs)
    return plain("périmètre", (
        f"{PORTFOLIO_LABEL}. {REAL_DATA_NOTE} Les trois livres partagent la même liste de titres et sont comparés "
        "au fonds iShares MSCI Global Sustainable Development Goals, dont le rendement publié est converti en CHF. "
        "Le rendement des livres n'inclut pas les dividendes, celui du fonds les inclut. Pas de données de conservation. "
        + client_needs
    ))


def _window_sentence(lang="fr"):
    d = Draft()
    if lang == "en":
        return d.done("window", (
            f"Report month: {d.text(WINDOW_END)}. Measurement window: {d.count(MONTHS)} months, "
            f"from {d.text(WINDOW_START)} to {d.text(WINDOW_END)}."
        ))
    return d.done("fenêtre", (
        f"Mois de rapport : {d.text(WINDOW_END)}. Fenêtre de mesure : {d.count(MONTHS)} mois, "
        f"de {d.text(WINDOW_START)} à {d.text(WINDOW_END)}."
    ))


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------

def allocation_table(source, key, title):
    """One row per group, one column per book, read in the allocation file."""
    frame = _frame(source)
    d = Draft()
    header = [title] + [LABELS[book] for book in BOOKS]
    rows = []
    for group in sorted(frame[key].astype(str).unique()):
        cells = [d.label(group)]
        for book in BOOKS:
            present = frame.loc[frame["strategy"].astype(str).eq(book) & frame[key].astype(str).eq(group)]
            cells.append(d.pct(fact(source, "weight", {"strategy": book, key: group}, scale="ratio")) if len(present) else NOT_HELD)
        rows.append(cells)
    return content._table(f"tableau {title}", header, rows, d)


def top10_table(book, header=None):
    frame = _frame(TOP10)
    lines = frame.loc[frame["strategy"].astype(str).eq(book)].sort_values("rank")
    d = Draft()
    header = header or ["Rang", "Titre", "Secteur", "Devise", "Poids"]
    rows = []
    for record in lines.itertuples(index=False):
        where = {"strategy": book, "rank": int(record.rank)}
        rows.append([
            d.count(fact(TOP10, "rank", where)),
            d.label(str(record.name)),
            d.label(str(record.sector)),
            d.label(str(record.exposure)),
            d.pct(fact(TOP10, "weight", where, scale="ratio")),
        ])
    return content._table(f"top 10 {book}", header, rows, d)


def contributors_table(book, header=None):
    """Largest and smallest cumulative contributions over the window, by name."""
    frame = _frame(HOLDING_CONTRIBUTION)
    last = str(frame["month"].astype(str).max())
    lines = frame.loc[frame["strategy"].astype(str).eq(book) & frame["month"].astype(str).eq(last)]
    lines = lines.sort_values("cumulative_contribution", ascending=False)
    chosen = pd.concat([lines.head(TOP_LINES), lines.tail(TOP_LINES)])
    d = Draft()
    header = header or ["Titre", "Secteur", "Poids au mois de rapport", "Contribution cumulée"]
    rows = []
    for position, record in enumerate(chosen.itertuples(index=False)):
        where = {"strategy": book, "month": last, "yahoo_symbol": str(record.yahoo_symbol)}
        rows.append([
            ("▲ " if position < TOP_LINES else "▼ ") + d.label(str(record.name)),
            d.label(str(record.sector)),
            d.pct(fact(HOLDING_CONTRIBUTION, "weight", where, scale="ratio")),
            d.pct(fact(HOLDING_CONTRIBUTION, "cumulative_contribution", where, scale="ratio")),
        ])
    return content._table(f"contributeurs {book}", header, rows, d)


def movements(book, lang="fr"):
    """Weight movements of the last rebalance, or the sentence that says there were none."""
    frame = _frame(WEIGHT_CHANGES)
    lines = frame.loc[frame["strategy"].astype(str).eq(book)]
    d = Draft()
    if lines.empty:
        if lang == "en":
            text = (
                f"{LABELS[book]}: no weight movement over the window. The largest gross turnover "
                f"observed is {d.pct(fact(TURNOVER, 'gross_turnover', {'strategy': book}, op='max', scale='ratio'), 1)}."
            )
        else:
            text = (
                f"{LABELS[book]} : aucun mouvement de poids sur la fenêtre. La rotation brute la plus forte "
                f"observée est de {d.pct(fact(TURNOVER, 'gross_turnover', {'strategy': book}, op='max', scale='ratio'), 1)}."
            )
        return None, d.done("mouvements", text)
    last = str(lines["month"].astype(str).max())
    month_lines = lines.loc[lines["month"].astype(str).eq(last)]
    ordered = month_lines.reindex(month_lines["weight_change"].abs().sort_values(ascending=False).index)
    chosen = ordered.head(2 * TOP_LINES)
    if lang == "en":
        text = (
            f"{LABELS[book]}: last rebalance in {d.text(fact(TURNOVER, 'month', {'strategy': book}, op='last', scale='text'))}, "
            f"{d.count(fact(WEIGHT_CHANGES, 'yahoo_symbol', {'strategy': book, 'month': last}, op='count'))} lines moved, "
            f"gross turnover {d.pct(fact(TURNOVER, 'gross_turnover', {'strategy': book, 'month': last}, scale='ratio'), 1)} "
            f"against a quarterly cap of {d.pct(config('QUARTERLY_TURNOVER_CAP'), 1)}. The largest movements:"
        )
    else:
        text = (
            f"{LABELS[book]} : dernier rééquilibrage en {d.text(fact(TURNOVER, 'month', {'strategy': book}, op='last', scale='text'))}, "
            f"{d.count(fact(WEIGHT_CHANGES, 'yahoo_symbol', {'strategy': book, 'month': last}, op='count'))} lignes ont bougé, "
            f"rotation brute {d.pct(fact(TURNOVER, 'gross_turnover', {'strategy': book, 'month': last}, scale='ratio'), 1)} "
            f"pour un plafond trimestriel de {d.pct(config('QUARTERLY_TURNOVER_CAP'), 1)}. Les plus grands mouvements :"
        )
    sentence = d.done("mouvements", text)
    t = Draft()
    header = (
        ["Name", "Weight before", "Weight after", "Change"]
        if lang == "en"
        else ["Titre", "Poids avant", "Poids après", "Variation"]
    )
    rows = []
    for record in chosen.itertuples(index=False):
        where = {"strategy": book, "month": last, "yahoo_symbol": str(record.yahoo_symbol)}
        rows.append([
            t.label(str(record.name)),
            t.pct(fact(WEIGHT_CHANGES, "weight_before", where, scale="ratio")),
            t.pct(fact(WEIGHT_CHANGES, "weight_after", where, scale="ratio")),
            t.pct(fact(WEIGHT_CHANGES, "weight_change", where, scale="ratio")),
        ])
    table = content._table(f"mouvements {book}", header, rows, t)
    return table, sentence


def performance_sentence(lang="fr"):
    d = Draft()
    best = max(BOOKS, key=lambda book: float(resolve(perf(book, "annualized_return"))))
    fund_return = float(resolve(perf(FUND, "annualized_return")))
    ahead = [LABELS[book] for book in BOOKS if float(resolve(perf(book, "annualized_return"))) > fund_return]
    if lang == "en":
        verdict = (
            "No book beats the fund over the window."
            if not ahead
            else f"Above the fund over the window: {', '.join(ahead)}."
        )
        text = (
            f"Among the three books, {LABELS[best]} has the highest annualised return, "
            f"{d.pct(perf(best, 'annualized_return'))} against {d.pct(perf(FUND, 'annualized_return'))} for the fund. {verdict}"
        )
    else:
        verdict = (
            "Aucun livre ne dépasse le fonds sur la fenêtre."
            if not ahead
            else f"Dépassent le fonds sur la fenêtre : {', '.join(ahead)}."
        )
        text = (
            f"Le livre {LABELS[best]} a le rendement annualisé le plus élevé des trois, "
            f"{d.pct(perf(best, 'annualized_return'))} contre {d.pct(perf(FUND, 'annualized_return'))} pour le fonds. {verdict}"
        )
    return d.done("performance", text)


# --------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------

def _start(title, generated, needs, lang="fr"):
    rep = Report(generated)
    rep.title(title)
    rep.story.append(_label_paragraph(generated))
    rep.para(_scope(needs, lang))
    rep.para(_window_sentence(lang))
    return rep


def _retitle(built, header):
    _header, rows, statement = built
    return header, rows, statement


def _label_paragraph(generated):
    from reportlab.platypus import Paragraph

    return Paragraph(f"{AUTO_LABEL} Produit par le pipeline le {generated}.", LABEL)


def build_allocation_report(sections, figures, generated):
    rep = _start("Rapport client — CLIENT001", generated, PENSION_NEEDS)

    rep.heading("Limites du mandat et situation au mois de rapport")
    rep.table(content.limits_table(), widths=[36 * mm, 24 * mm, 22 * mm, 34 * mm, 34 * mm, 24 * mm])
    cap_alerts = [s for s in sections["alertes"] if s.kind == "alerte" and "plafond" in s.text]
    rep.bullets([sections["alertes"][0]] + cap_alerts)

    rep.heading("Allocation")
    rep.table(allocation_table(SECTORS, "sector", "Secteur"), widths=[52 * mm, 36 * mm, 36 * mm, 36 * mm])
    rep.table(allocation_table(ZONES, "zone", "Zone"), widths=[52 * mm, 36 * mm, 36 * mm, 36 * mm])
    rep.table(allocation_table(EXPOSURE, "exposure", "Devise de cotation"), widths=[52 * mm, 36 * mm, 36 * mm, 36 * mm])

    rep.heading("Performance contre le fonds, en CHF")
    rep.table(content.performance_table(), widths=[34 * mm, 22 * mm, 19 * mm, 15 * mm, 15 * mm, 24 * mm, 21 * mm, 24 * mm])
    rep.para(performance_sentence())
    tracking = [s for s in sections["alertes"] if "Écart de suivi" in s.text]
    rep.bullets(tracking)
    rep.figure(figures["wealth"], "Richesse cumulée pour une unité investie. Le fonds est en pointillé.")

    rep.heading("Risque")
    rep.table(content.risk_table(), widths=[36 * mm, 29 * mm, 25 * mm, 33 * mm, 21 * mm, 30 * mm])
    drawdown = [s for s in sections["risques"] if s.text.startswith("Drawdown maximal")]
    rep.bullets(drawdown + [s for s in sections["alertes"] if s.text.startswith("Drawdown maximal au-delà")])
    rep.para(plain("note", "Les tests de résistance, le détail des lignes et la qualité des données sont dans le rapport exécutif, sur demande."), SMALL)

    CLIENT_REPORTS.mkdir(parents=True, exist_ok=True)
    rep.save(PENSION_FILE)
    return PENSION_FILE, rep.statements, tuple(sorted(set(rep.footers))) + (generated, "CLIENT001")


def build_manager_report(sections, figures, generated):
    rep = _start("Rapport gérant — livres de CLIENT001", generated, MANAGER_NEEDS)

    rep.heading("Dix premières lignes au mois de rapport")
    for book in BOOKS:
        rep.para(plain("livre", f"{LABELS[book]}."), SMALL)
        rep.table(top10_table(book), widths=[12 * mm, 70 * mm, 40 * mm, 18 * mm, 20 * mm])

    rep.heading("Contributeurs et détracteurs sur la fenêtre")
    rep.para(plain("contribution", (
        "La contribution d'un titre dans un mois est son poids multiplié par son rendement en CHF. "
        "Les titres d'un mois reconstituent le rendement du livre, et la colonne cumulée additionne les mois sans capitalisation. "
        "Les cinq premiers et les cinq derniers de chaque livre :"
    )), SMALL)
    for book in BOOKS:
        rep.para(plain("livre", f"{LABELS[book]}."), SMALL)
        rep.table(contributors_table(book), widths=[72 * mm, 40 * mm, 34 * mm, 34 * mm])

    rep.heading("Mouvements de poids du dernier rééquilibrage")
    rep.para(plain("mouvements", MOVEMENT_NOTE), SMALL)
    for book in BOOKS:
        table, sentence = movements(book)
        rep.para(sentence)
        if table is not None:
            rep.table(table, widths=[80 * mm, 30 * mm, 30 * mm, 30 * mm])

    rep.heading("Exposition par devise de cotation")
    rep.table(allocation_table(EXPOSURE, "exposure", "Devise de cotation"), widths=[52 * mm, 36 * mm, 36 * mm, 36 * mm])

    CLIENT_REPORTS.mkdir(parents=True, exist_ok=True)
    rep.save(MANAGER_FILE)
    return MANAGER_FILE, rep.statements, tuple(sorted(set(rep.footers))) + (generated, "CLIENT001")


def build_allocation_report_en(sections, figures, generated):
    """English client report. Same files and the same facts as the French one."""
    rep = _start("Client report — CLIENT001", generated, PENSION_NEEDS_EN, lang="en")

    rep.heading("Mandate limits at the report month")
    rep.table(
        _retitle(
            content.limits_table(cap_label="Mandate cap", span_word="to"),
            ["Book", "Invested lines", "Largest weight", "Largest sector", "Largest region", "Largest currency"],
        ),
        widths=[36 * mm, 24 * mm, 22 * mm, 34 * mm, 34 * mm, 24 * mm],
    )

    rep.heading("Allocation")
    rep.table(allocation_table(SECTORS, "sector", "Sector"), widths=[52 * mm, 36 * mm, 36 * mm, 36 * mm])
    rep.table(allocation_table(ZONES, "zone", "Region"), widths=[52 * mm, 36 * mm, 36 * mm, 36 * mm])
    rep.table(allocation_table(EXPOSURE, "exposure", "Listing currency"), widths=[52 * mm, 36 * mm, 36 * mm, 36 * mm])

    rep.heading("Performance against the fund, in CHF")
    rep.table(
        _retitle(
            content.performance_table(),
            ["Series", "Annualised return", "Volatility", "Sharpe", "Sortino", "Maximum drawdown", "Tracking error", "Information ratio"],
        ),
        widths=[34 * mm, 22 * mm, 19 * mm, 15 * mm, 15 * mm, 24 * mm, 21 * mm, 24 * mm],
    )
    rep.para(performance_sentence("en"))
    rep.figure(figures["wealth"], "Cumulative wealth of one unit invested. The fund is the dotted line.")

    rep.heading("Risk")
    rep.table(
        _retitle(
            content.risk_table(),
            ["Series", "Annualised volatility", "Monthly VaR", "Monthly expected shortfall", "Worst month", "Return of the worst month"],
        ),
        widths=[36 * mm, 29 * mm, 25 * mm, 33 * mm, 21 * mm, 30 * mm],
    )
    rep.para(plain("note", "Stress tests, security-level detail and data quality are in the executive report, on request."), SMALL)

    CLIENT_REPORTS.mkdir(parents=True, exist_ok=True)
    rep.save(PENSION_FILE_EN)
    return PENSION_FILE_EN, rep.statements, tuple(sorted(set(rep.footers))) + (generated, "CLIENT001")


def build_manager_report_en(sections, figures, generated):
    """English manager report. Same files and the same facts as the French one."""
    rep = _start("Manager report — CLIENT001 books", generated, MANAGER_NEEDS_EN, lang="en")

    rep.heading("Ten largest lines at the report month")
    for book in BOOKS:
        rep.para(plain("book", f"{LABELS[book]}."), SMALL)
        rep.table(
            top10_table(book, ["Rank", "Name", "Sector", "Currency", "Weight"]),
            widths=[12 * mm, 70 * mm, 40 * mm, 18 * mm, 20 * mm],
        )

    rep.heading("Contributors and detractors over the window")
    rep.para(plain("contribution", (
        "A name's contribution in a month is its weight multiplied by its return in CHF. "
        "The names of a month rebuild the book's return, and the cumulative column adds the months without compounding. "
        "The five largest and the five smallest of each book:"
    )), SMALL)
    for book in BOOKS:
        rep.para(plain("book", f"{LABELS[book]}."), SMALL)
        rep.table(
            contributors_table(book, ["Name", "Sector", "Weight at the report month", "Cumulative contribution"]),
            widths=[72 * mm, 40 * mm, 34 * mm, 34 * mm],
        )

    rep.heading("Weight movements of the last rebalance")
    rep.para(plain("movements", MOVEMENT_NOTE_EN), SMALL)
    for book in BOOKS:
        table, sentence = movements(book, lang="en")
        rep.para(sentence)
        if table is not None:
            rep.table(table, widths=[80 * mm, 30 * mm, 30 * mm, 30 * mm])

    rep.heading("Exposure by listing currency")
    rep.table(allocation_table(EXPOSURE, "exposure", "Listing currency"), widths=[52 * mm, 36 * mm, 36 * mm, 36 * mm])

    CLIENT_REPORTS.mkdir(parents=True, exist_ok=True)
    rep.save(MANAGER_FILE_EN)
    return MANAGER_FILE_EN, rep.statements, tuple(sorted(set(rep.footers))) + (generated, "CLIENT001")


def build_client_reports(sections, figures, generated):
    """French and English reports. Return one (file, statements, structural) per report."""
    return [
        build_allocation_report(sections, figures, generated),
        build_manager_report(sections, figures, generated),
        build_allocation_report_en(sections, figures, generated),
        build_manager_report_en(sections, figures, generated),
    ]


def check_client_pages(pages, path):
    if pages > CLIENT_REPORT_MAX_PAGES:
        raise RuntimeError(f"{path.name} has {pages} pages, more than {CLIENT_REPORT_MAX_PAGES}.")
    return pages
