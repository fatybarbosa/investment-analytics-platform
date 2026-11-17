"""
Phase 11b. Two customized monthly reports from the same published files.

CLIENT001 is the only client. One report is written for that client.
The other is written for the manager who follows the same books.
Both read the same files.

Client report : sector, region, currency and the written limits.
Performance, risk and stress stay in the executive report.
Nothing at security level.

Manager report : the ten largest lines, the names that contributed most
and least over the window, the weight movements of the last rebalance,
currency exposure. Nothing on limits or stress.

Every sentence and every table cell is a Statement checked against the
pipeline files. The weight movements are those of a hypothetical book:
no order was placed, there is no transaction record.

Outputs
-------
reports/client/rapport_client.pdf
reports/client/rapport_gerant.pdf
"""

from __future__ import annotations

import pandas as pd
from reportlab.lib.units import mm

from src.config import CLIENT_REPORTS, PROJECT_ROOT
from src.reporting import report_content as content
from src.reporting.commentary import (
    BASIS_NOTE,
    BOOKS,
    LABELS,
    MONTHS,
    pick,
    PORTFOLIO_LABEL,
    REAL_DATA_NOTE,
    TURNOVER,
    WINDOW_END,
    WINDOW_START,
    config,
)
from src.reporting.executive_report import LABEL, Report, SMALL, plain
from src.reporting.number_check import AUTO_LABEL, Draft, fact


PENSION_FILE = CLIENT_REPORTS / "rapport_client.pdf"
MANAGER_FILE = CLIENT_REPORTS / "rapport_gerant.pdf"
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
    "Rapport remis à CLIENT001 : la répartition par secteur, zone et devise, et la situation face à chaque limite écrite. "
    "La performance, le risque et les tests de résistance sont dans le rapport exécutif. "
    "CLIENT001 ne reçoit pas le détail des lignes."
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


def _frame(source):
    return pd.read_csv(PROJECT_ROOT / source)


def _scope(client_needs):
    return plain("périmètre", (
        f"{PORTFOLIO_LABEL}. {REAL_DATA_NOTE} Les trois livres partagent la même liste de titres et sont comparés "
        "au fonds iShares MSCI Global Sustainable Development Goals, dont le rendement publié est converti en CHF. "
        + BASIS_NOTE + " Pas de données de conservation. "
        + client_needs
    ))


def _window_sentence():
    d = Draft()
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
    header = header or ["Rôle", "Titre", "Secteur", "Poids au mois de rapport", "Contribution cumulée"]
    rows = []
    for position, record in enumerate(chosen.itertuples(index=False)):
        where = {"strategy": book, "month": last, "yahoo_symbol": str(record.yahoo_symbol)}
        rows.append([
            "Contributeur" if position < TOP_LINES else "Détracteur",
            d.label(str(record.name)),
            d.label(str(record.sector)),
            d.pct(fact(HOLDING_CONTRIBUTION, "weight", where, scale="ratio")),
            d.pct(fact(HOLDING_CONTRIBUTION, "cumulative_contribution", where, scale="ratio")),
        ])
    return content._table(f"contributeurs {book}", header, rows, d)


def movements(book):
    """Weight movements of the last rebalance, or the sentence that says there were none."""
    frame = _frame(WEIGHT_CHANGES)
    lines = frame.loc[frame["strategy"].astype(str).eq(book)]
    d = Draft()
    if lines.empty:
        text = (
            f"{LABELS[book]} : aucun mouvement de poids sur la fenêtre. La rotation brute la plus forte "
            f"observée est de {d.pct(fact(TURNOVER, 'gross_turnover', {'strategy': book}, op='max', scale='ratio'), 1)}."
        )
        return None, d.done("mouvements", text)
    last = str(lines["month"].astype(str).max())
    month_lines = lines.loc[lines["month"].astype(str).eq(last)]
    ordered = month_lines.reindex(month_lines["weight_change"].abs().sort_values(ascending=False).index)
    chosen = ordered.head(2 * TOP_LINES)
    text = (
        f"{LABELS[book]} : dernier rééquilibrage en {d.text(fact(TURNOVER, 'month', {'strategy': book}, op='last', scale='text'))}, "
        f"{d.count(fact(WEIGHT_CHANGES, 'yahoo_symbol', {'strategy': book, 'month': last}, op='count'))} lignes ont bougé, "
        f"rotation brute {d.pct(fact(TURNOVER, 'gross_turnover', {'strategy': book, 'month': last}, scale='ratio'), 1)} "
        f"pour un plafond trimestriel de {d.pct(config('QUARTERLY_TURNOVER_CAP'), 1)}. Les plus grands mouvements :"
    )
    sentence = d.done("mouvements", text)
    t = Draft()
    header = ["Titre", "Poids avant", "Poids après", "Variation"]
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


# --------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------

def _start(title, generated, needs):
    rep = Report(generated)
    rep.title(title)
    rep.story.append(_label_paragraph(generated))
    rep.para(_scope(needs))
    rep.para(_window_sentence())
    return rep


def _label_paragraph(generated):
    from reportlab.platypus import Paragraph

    return Paragraph(f"{AUTO_LABEL} Produit par le pipeline le {generated}.", LABEL)


def build_allocation_report(sections, _figures, generated):
    rep = _start("Rapport de CLIENT001", generated, PENSION_NEEDS)

    rep.heading("Limites du mandat et situation au mois de rapport")
    rep.table(content.limits_table(), widths=[36 * mm, 24 * mm, 22 * mm, 34 * mm, 34 * mm, 24 * mm])
    alerts = sections["alertes"]
    rep.bullets(
        pick(alerts, "limites_decision") + pick(alerts, "passifs") + pick(alerts, "ips_secteur") + pick(alerts, "vigilance")
    )

    rep.heading("Allocation")
    rep.table(allocation_table(SECTORS, "sector", "Secteur"), widths=[52 * mm, 36 * mm, 36 * mm, 36 * mm])
    rep.table(allocation_table(ZONES, "zone", "Zone"), widths=[52 * mm, 36 * mm, 36 * mm, 36 * mm])
    rep.table(allocation_table(EXPOSURE, "exposure", "Devise de cotation"), widths=[52 * mm, 36 * mm, 36 * mm, 36 * mm])

    rep.para(plain(
        "renvoi",
        "La performance contre le fonds, le risque et les tests de résistance sont dans le rapport exécutif. "
        "Ils ne sont pas repris ici.",
    ), SMALL)

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
        rep.table(contributors_table(book), widths=[24 * mm, 56 * mm, 34 * mm, 30 * mm, 30 * mm])

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


def build_client_reports(sections, figures, generated):
    """The client report and the manager report, in French."""
    return [
        build_allocation_report(sections, figures, generated),
        build_manager_report(sections, figures, generated),
    ]


def check_client_pages(pages, path):
    if pages > CLIENT_REPORT_MAX_PAGES:
        raise RuntimeError(f"{path.name} has {pages} pages, more than {CLIENT_REPORT_MAX_PAGES}.")
    return pages
