"""
Phase 11. Management presentation, ten to fifteen slides, PowerPoint.

For a non technical audience: one message per slide, a figure or a
short table, few words. Every sentence and every table cell is a
Statement already checked against the pipeline files. After the file
is written, its text is read back and checked again as a whole.

Output
------
reports/management/presentation_management.pptx
"""

from __future__ import annotations

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from src.config import MANAGEMENT_REPORTS
from src.reporting import report_content as content
from src.reporting.commentary import (
    BOOKS,
    DISCLAIMER,
    FUND,
    LABELS,
    MONTHS,
    NAMES,
    BASIS_NOTE,
    PENDING,
    PORTFOLIO_LABEL,
    pick,
    UNIVERSE_NOTE,
    REAL_DATA_NOTE,
    SCOPE_NOTE,
    WINDOW_END,
    WINDOW_START,
    config,
    LIMITS,
    perf,
    quality_summary,
    reconciliation,
    resolve,
    risk,
    stress,
)
from src.reporting.executive_report import plain
from src.reporting.number_check import AUTO_LABEL, Draft, fact


DECK_FILE = MANAGEMENT_REPORTS / "presentation_management.pptx"
MIN_SLIDES = 10
MAX_SLIDES = 15
NAVY = RGBColor(0x1F, 0x4E, 0x79)
INK = RGBColor(0x0B, 0x0B, 0x0B)
SECONDARY = RGBColor(0x52, 0x51, 0x4E)
BAND = RGBColor(0xEE, 0xF3, 0xF8)
AMBER = RGBColor(0x9C, 0x57, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
WIDTH = Inches(13.333)
HEIGHT = Inches(7.5)
MARGIN = Inches(0.6)


AUTHOR = "Pipeline du projet (généré automatiquement)"


class Deck:
    def __init__(self, generated):
        self.generated = generated
        self.presentation = Presentation()
        properties = self.presentation.core_properties
        properties.author = AUTHOR
        properties.last_modified_by = AUTHOR
        properties.title = "Trois portefeuilles ODD en CHF"
        self.presentation.slide_width = WIDTH
        self.presentation.slide_height = HEIGHT
        self.statements = []
        self.footers = []
        self.blank = self.presentation.slide_layouts[6]

    def keep(self, statement):
        self.statements.append(statement)
        return statement

    def _text(self, slide, left, top, width, height, text, size, bold=False, color=INK, italic=False, align=PP_ALIGN.LEFT):
        box = slide.shapes.add_textbox(left, top, width, height)
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_left = frame.margin_right = 0
        paragraph = frame.paragraphs[0]
        paragraph.alignment = align
        run = paragraph.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = color
        run.font.name = "Calibri"
        return box

    def slide(self, title, message=None):
        """New slide with its title, its one-line message and the footer."""
        slide = self.presentation.slides.add_slide(self.blank)
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.18), HEIGHT)
        bar.fill.solid()
        bar.fill.fore_color.rgb = NAVY
        bar.line.fill.background()
        self._text(slide, MARGIN, Inches(0.35), WIDTH - 2 * MARGIN, Inches(0.7), title, 28, bold=True, color=NAVY)
        if message is not None:
            self.keep(message)
            self._text(slide, MARGIN, Inches(1.05), WIDTH - 2 * MARGIN, Inches(0.7), message.text, 16, color=SECONDARY)
        number = len(self.presentation.slides)
        mark = f"Diapositive {number}"
        self.footers.append(mark)
        self._text(slide, MARGIN, HEIGHT - Inches(0.45), Inches(9.5), Inches(0.3), f"{AUTO_LABEL} {PORTFOLIO_LABEL}.", 10, color=AMBER, italic=True)
        self._text(slide, WIDTH - MARGIN - Inches(2), HEIGHT - Inches(0.45), Inches(2), Inches(0.3), mark, 10, color=SECONDARY, align=PP_ALIGN.RIGHT)
        return slide

    def bullets(self, slide, statements, left=MARGIN, top=Inches(1.9), width=None, height=Inches(4.8), size=16):
        width = width or WIDTH - 2 * MARGIN
        box = slide.shapes.add_textbox(left, top, width, height)
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_left = frame.margin_right = 0
        first = True
        for statement in statements:
            self.keep(statement)
            paragraph = frame.paragraphs[0] if first else frame.add_paragraph()
            first = False
            paragraph.space_after = Pt(size * 0.55)
            if statement.kind == "alerte":
                lead = paragraph.add_run()
                lead.text = "Alerte. "
                lead.font.bold = True
                lead.font.size = Pt(size)
                lead.font.color.rgb = AMBER
                lead.font.name = "Calibri"
            run = paragraph.add_run()
            run.text = ("" if statement.kind == "alerte" else "• ") + statement.text
            run.font.size = Pt(size)
            run.font.color.rgb = INK
            run.font.name = "Calibri"
        return box

    def table(self, slide, built, left=MARGIN, top=Inches(1.9), width=None, row_height=Inches(0.42), size=13, first_width=None):
        header, rows, statement = built
        self.keep(statement)
        width = width or WIDTH - 2 * MARGIN
        shape = slide.shapes.add_table(len(rows) + 1, len(header), left, top, width, row_height * (len(rows) + 1))
        table = shape.table
        if first_width is not None:
            table.columns[0].width = first_width
            rest = int((width - first_width) / (len(header) - 1))
            for index in range(1, len(header)):
                table.columns[index].width = Emu(rest)
        for column, text in enumerate(header):
            self._cell(table.cell(0, column), text, size, bold=True, color=WHITE, fill=NAVY)
        for row_index, row in enumerate(rows, 1):
            for column, text in enumerate(row):
                self._cell(table.cell(row_index, column), text, size, bold=(column == 0), fill=BAND if row_index % 2 == 0 else WHITE)
        return shape

    @staticmethod
    def _cell(cell, text, size, bold=False, color=INK, fill=WHITE):
        cell.text = ""
        cell.fill.solid()
        cell.fill.fore_color.rgb = fill
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = cell.margin_right = Inches(0.08)
        run = cell.text_frame.paragraphs[0].add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = "Calibri"

    def picture(self, slide, path, left, top, width):
        return slide.shapes.add_picture(str(path), left, top, width=width)

    def save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.presentation.save(str(path))


def _messages():
    """Short sentences written for the slides. Each is checked like the others."""
    out = {}
    d = Draft()
    out["window"] = d.done("diapositive", (
        f"{d.count(MONTHS)} mois observés, de {d.text(WINDOW_START)} à {d.text(WINDOW_END)}, sur {d.count(NAMES)} titres."
    ))
    d = Draft()
    best = max(BOOKS, key=lambda book: float(resolve(perf(book, "annualized_return"))))
    out["performance"] = d.done("diapositive", (
        f"Le meilleur livre, {LABELS[best]}, rend {d.pct(perf(best, 'annualized_return'), 1)} par an. "
        f"Le fonds iShares rend {d.pct(perf(FUND, 'annualized_return'), 1)} par an."
    ))
    d = Draft()
    worst = min(BOOKS, key=lambda book: float(resolve(perf(book, "maximum_drawdown"))))
    out["risk"] = d.done("diapositive", (
        f"Dans les plus mauvais mois de la fenêtre, la perte mensuelle va de {d.pct(risk(max(BOOKS, key=lambda b: float(resolve(risk(b, 'var_95')))), 'var_95'), 1)} "
        f"à {d.pct(risk(min(BOOKS, key=lambda b: float(resolve(risk(b, 'var_95')))), 'var_95'), 1)} selon le livre. "
        f"La baisse la plus profonde atteint {d.pct(perf(worst, 'maximum_drawdown'), 1)} ({LABELS[worst]})."
    ))
    d = Draft()
    ips_breaches = float(resolve(fact(LIMITS, "sector_over_ips_cap", op="sum")))
    if ips_breaches > 0:
        out["limits"] = d.done("diapositive", (
            f"Le plafond de secteur écrit dans le mandat ({d.pct(config('IPS_SECTOR_WEIGHT_CAP'), 0)}) est dépassé par les livres, "
            f"construits avec un plafond de travail de {d.pct(config('SECTOR_WEIGHT_CAP'), 0)} que le client n'a pas approuvé."
        ))
    else:
        out["limits"] = d.done("diapositive", "Les livres respectent le plafond de secteur écrit dans le mandat.")
    out["breaches"] = ips_breaches
    d = Draft()
    book = min(BOOKS, key=lambda b: min(float(resolve(stress(b, s, "terminal_wealth"))) for s in ("marche", "taux", "recession", "volatilite")))
    shock = min(("marche", "taux", "recession", "volatilite"), key=lambda s: float(resolve(stress(book, s, "terminal_wealth"))))
    out["stress"] = d.done("diapositive", (
        f"Dans le choc le plus dur, la richesse finale du livre {LABELS[book]} passe de {d.num(stress(book, 'aucun', 'terminal_wealth'))} "
        f"à {d.num(stress(book, shock, 'terminal_wealth'))} pour une unité investie."
    ))
    d = Draft()
    out["quality"] = d.done("diapositive", (
        f"Score de qualité {d.pct(quality_summary('global_quality_score', 'percent'))}, note {resolve(quality_summary('global_quality_grade', 'text'))}, "
        f"statut {resolve(quality_summary('global_status', 'text'))}. Les anomalies détectées sont listées, aucune n'est masquée."
    ))
    d = Draft()
    out["control"] = d.done("diapositive", (
        f"{d.count(reconciliation('statut', {'statut': 'OK'}))} indicateurs sur {d.count(reconciliation('indicateur'))} sont retrouvés par un second calcul dans Excel. "
        f"{d.count(reconciliation('statut_power_bi', {'statut_power_bi': 'OK'}))} sont aussi retrouvés dans Power BI, "
        f"{d.count(reconciliation('statut_power_bi', {'statut_power_bi': PENDING}))} y restent en attente."
    ))
    return out


def build_deck(sections, figures, generated):
    """Write the deck. Return the file, its statements and its structural strings."""
    deck = Deck(generated)
    facts, risks, alerts, points = (sections[name] for name in ("faits", "risques", "alertes", "points"))
    messages = _messages()
    full = WIDTH - 2 * MARGIN

    # Title
    slide = deck.presentation.slides.add_slide(deck.blank)
    band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, WIDTH, Inches(4.1))
    band.fill.solid()
    band.fill.fore_color.rgb = NAVY
    band.line.fill.background()
    deck._text(slide, MARGIN, Inches(1.3), full, Inches(1.2), "Trois portefeuilles ODD en CHF", 44, bold=True, color=WHITE)
    deck._text(slide, MARGIN, Inches(2.5), full, Inches(0.8), "Performance, risque et contrôle des calculs. Présentation au management.", 22, color=WHITE)
    deck.keep(messages["window"])
    deck._text(slide, MARGIN, Inches(4.5), full, Inches(0.5), messages["window"].text, 18, color=INK)
    deck._text(slide, MARGIN, Inches(5.1), full, Inches(0.9), SCOPE_NOTE, 14, color=SECONDARY)
    deck._text(slide, MARGIN, Inches(6.3), full, Inches(0.4), f"{AUTO_LABEL} Produit par le pipeline le {generated}.", 12, color=AMBER, italic=True)
    deck.footers.append(generated)

    # Context
    slide = deck.slide("Contexte", plain("diapositive", "Un client fictif veut faire croître son capital avec des actions alignées sur les Objectifs de développement durable."))
    deck.bullets(slide, [
        plain("diapositive", "La question posée : trois façons de répartir le même panier de titres font-elles mieux que le fonds de référence, et avec quel risque ?"),
        plain("diapositive", "Trois livres : parts égales (équipondéré), le moins de variations possible (volatilité minimale), le meilleur rendement par unité de risque (Sharpe maximal)."),
        plain("diapositive", "Référence : le fonds iShares MSCI Global Sustainable Development Goals, converti en CHF."),
        plain("diapositive", "Ce travail est un exercice sur données publiques. Rien n'a été investi."),
    ], size=18)

    # Mandate
    slide = deck.slide("Mandat et limites", plain("diapositive", "Les règles sont écrites avant le calcul. Les livres doivent rester sous chaque plafond."))
    deck.table(slide, content.limits_table(), top=Inches(1.9), size=13, first_width=Inches(2.6))
    deck.bullets(slide, [
        plain("diapositive", "Actions cotées seulement, sans vente à découvert ni levier. Les poids sont revus chaque trimestre."),
        plain("diapositive", "Un titre n'entre que s'il a le statut Eligible du registre ODD et un historique complet en CHF."),
    ], top=Inches(4.6), height=Inches(1.8), size=16)

    # Method
    slide = deck.slide("Méthode", plain("diapositive", "Une seule commande refait toute la chaîne, des données aux livrables, et s'arrête si un contrôle échoue."))
    deck.bullets(slide, [
        plain("diapositive", "Collecte : positions et rendement du fonds (iShares), cours (Yahoo Finance), change et taux sans risque SARON (Banque nationale suisse)."),
        plain("diapositive", "Contrôle qualité des données, puis conversion des cours en CHF."),
        plain("diapositive", "Construction des trois livres, suivi des plafonds, performance, risque, tests de résistance."),
        plain("diapositive", "Second calcul indépendant dans Excel, lecture dans Power BI, puis comparaison des trois."),
        plain("diapositive", "Rapport, présentation et commentaires écrits à partir des fichiers : chaque nombre est relu dans sa source."),
        plain("diapositive", f"{REAL_DATA_NOTE} Pas de données de conservation : ni positions réelles, ni transactions, ni frais, ni flux."),
    ], size=17)

    # Performance
    slide = deck.slide("Performance", messages["performance"])
    deck.picture(slide, figures["wealth"], MARGIN, Inches(1.85), Inches(8.3))
    returns = {book: float(resolve(perf(book, "annualized_return"))) for book in BOOKS}
    fund_return = float(resolve(perf(FUND, "annualized_return")))
    ahead = [LABELS[book] for book in BOOKS if returns[book] > fund_return]
    verdict = (
        "Aucun des trois livres ne fait mieux que le fonds sur la période."
        if not ahead
        else f"Font mieux que le fonds sur la période : {', '.join(ahead)}."
    )
    deck.bullets(slide, [
        plain("diapositive", verdict),
        plain("diapositive", "Les livres sont mesurés en rendement total brut de frais, le fonds net de ses frais : la comparaison avantage donc les livres."),
        plain("diapositive", f"Le meilleur des trois livres sur la période est le livre {LABELS[max(returns, key=returns.get)]}."),
    ], left=Inches(9.2), top=Inches(1.9), width=Inches(3.6), size=15)

    # Performance table
    slide = deck.slide("Performance : les chiffres", plain("diapositive", "Rendement, risque et rendement par unité de risque, pour les trois livres et le fonds."))
    deck.table(slide, content.performance_table(), size=13, first_width=Inches(2.5))
    deck.bullets(slide, [
        plain("diapositive", "Sharpe et Sortino : rendement obtenu au-dessus du taux sans risque, rapporté aux variations. Plus c'est haut, mieux c'est."),
        plain("diapositive", "Écart de suivi : à quel point un livre s'éloigne du fonds d'un mois à l'autre."),
    ], top=Inches(4.5), height=Inches(1.9), size=15)

    # Risk
    slide = deck.slide("Risque", messages["risk"])
    deck.picture(slide, figures["tail"], MARGIN, Inches(1.95), Inches(7.6))
    deck.bullets(slide, [
        plain("diapositive", "VaR : la perte d'un mauvais mois. Expected shortfall : la perte moyenne des pires mois."),
        *pick(risks, "drawdown"),
    ], left=Inches(8.5), top=Inches(1.95), width=Inches(4.3), size=14)

    # Correlation and concentration
    slide = deck.slide("Corrélation et concentration", messages["limits"])
    deck.picture(slide, figures["sector"], MARGIN, Inches(1.95), Inches(7.6))
    deck.bullets(slide, pick(risks, "correlation") + pick(alerts, "ips_secteur") + pick(alerts, "vigilance")[:1],
                 left=Inches(8.5), top=Inches(1.95), width=Inches(4.3), size=13)

    # Stress
    slide = deck.slide("Tests de résistance (illustratifs)", messages["stress"])
    deck.picture(slide, figures["stress"], MARGIN, Inches(1.95), Inches(7.4))
    header, rows, statement = content.shock_definitions()
    deck.bullets(slide, [_shock_line(name, text, statement) for name, text in rows],
                 left=Inches(8.3), top=Inches(1.95), width=Inches(4.5), size=13)
    deck.bullets(slide, [plain("diapositive", "Ce sont des simulations écrites à l'avance, pas des prévisions.")], left=MARGIN, top=Inches(5.9), height=Inches(0.6), size=14)

    # Quality
    slide = deck.slide("Qualité des données", messages["quality"])
    deck.table(slide, content.quality_table(), width=Inches(6.6), size=13, first_width=Inches(3.0))
    deck.bullets(slide, pick(alerts, "qualite") + pick(alerts, "qualite_ponderation"), left=Inches(7.6), top=Inches(1.9), width=Inches(5.2), size=13)

    # Control
    slide = deck.slide("Contrôle des calculs", messages["control"])
    deck.table(slide, content.reconciliation_table(), size=14, first_width=Inches(3.2), row_height=Inches(0.5))
    deck.bullets(slide, [
        plain("diapositive", "Python calcule. Excel recalcule sans lire le résultat de Python. Power BI recalcule deux indicateurs et relit le chiffre publié pour les autres."),
        content.reconciliation_sentence(),
        plain("diapositive", "Ce que cela ne prouve pas : que les titres ont été détenus. Il n'y a pas de données de conservation."),
    ], top=Inches(3.8), height=Inches(2.6), size=15)

    # Alerts
    slide = deck.slide("Alertes", plain("diapositive", ("Des écarts avec le mandat restent ouverts. " if messages["breaches"] > 0 else "Aucun écart de plafond n'est ouvert. ") + "Les points ci-dessous demandent une attention avant le prochain rééquilibrage."))
    flagged = [statement for statement in alerts if statement.kind == "alerte"]
    deck.bullets(slide, flagged, size=13 if len(flagged) > 5 else 15)

    # Recommendations
    slide = deck.slide("Points à instruire", plain("diapositive", "Des points à instruire, liés aux limites du mandat. Pas de conseil d'investissement personnalisé."))
    deck.bullets(slide, points, size=15)
    deck.bullets(slide, [plain("diapositive", DISCLAIMER)], top=Inches(6.2), height=Inches(0.5), size=12)

    # Limits
    slide = deck.slide("Limites", plain("diapositive", "Ce que ces résultats ne permettent pas de dire."))
    deck.bullets(slide, [
        plain("diapositive", f"{PORTFOLIO_LABEL}. Aucun ordre n'a été passé, aucun frais ni impôt n'est déduit."),
        plain("diapositive", REAL_DATA_NOTE + " Ce qui est hypothétique, ce sont les portefeuilles, pas les données."),
        plain("diapositive", "Pas de données de conservation : ni positions réelles, ni transactions, ni flux."),
        plain("diapositive", UNIVERSE_NOTE),
        plain("diapositive", BASIS_NOTE),
        plain("diapositive", "Les chocs sont des hypothèses simples, appliquées au rendement global du livre et non titre par titre."),
        plain("diapositive", "Une performance passée ne préjuge pas d'une performance future."),
    ], size=16)

    deck.save(DECK_FILE)
    structural = tuple(sorted(set(deck.footers), key=len, reverse=True)) + ("CLIENT001",)
    return DECK_FILE, deck.statements, structural


def _shock_line(name, text, statement):
    """One row of the shock table as a bullet. It keeps the facts of the table."""
    from src.reporting.number_check import Statement

    line = Statement("diapositive", f"{name} : {text}", statement.facts)
    line.check()
    return line


def read_deck(path=DECK_FILE):
    """Text and slide count of the written deck."""
    presentation = Presentation(str(path))
    parts = []
    for slide in presentation.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                parts.append(shape.text_frame.text)
            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    parts.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(parts), len(presentation.slides)


def check_slides(count):
    if not MIN_SLIDES <= count <= MAX_SLIDES:
        raise RuntimeError(f"The deck has {count} slides. It must have {MIN_SLIDES} to {MAX_SLIDES}.")
    return count
