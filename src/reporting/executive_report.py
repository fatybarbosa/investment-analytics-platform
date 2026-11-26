"""
Phase 11. Executive report, two to three pages, PDF.

Every sentence and every table cell is a Statement already checked
against the pipeline files. The module adds layout only. After the file
is written, its text is read back and checked again as a whole.

Output
------
reports/executive/rapport_executif.pdf
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from src.config import EXECUTIVE_REPORT_MAX_PAGES, EXECUTIVE_REPORTS
from src.reporting import report_content as content
from src.reporting.commentary import DISCLAIMER, PORTFOLIO_LABEL, SCOPE_NOTE, UNIVERSE_NOTE, pick
from src.reporting.number_check import AUTO_LABEL, Statement


REPORT_FILE = EXECUTIVE_REPORTS / "rapport_executif.pdf"
NAVY = colors.HexColor("#1F4E79")
INK = colors.HexColor("#0b0b0b")
SECONDARY = colors.HexColor("#52514e")
RULE = colors.HexColor("#c3c2b7")
BAND = colors.HexColor("#eef3f8")
ALERT = colors.HexColor("#9C5700")

BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=7.8, leading=9.5, textColor=INK, alignment=TA_LEFT, spaceAfter=1.8)
BULLET = ParagraphStyle("bullet", parent=BODY, leftIndent=9, bulletIndent=1, spaceAfter=1.3)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=7.3, leading=9.2, textColor=SECONDARY)
H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=NAVY, spaceAfter=2)
H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.2, leading=12.5, textColor=NAVY, spaceBefore=4, spaceAfter=2.2, keepWithNext=1)
LABEL = ParagraphStyle("label", fontName="Helvetica-Oblique", fontSize=8.3, leading=10.5, textColor=ALERT, spaceAfter=3)
CELL = ParagraphStyle("cell", fontName="Helvetica", fontSize=7.4, leading=9, textColor=INK)
CELL_HEAD = ParagraphStyle("cellhead", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)


def plain(section, text):
    """Prose with no number. The check fails if a digit slips in."""
    statement = Statement(section, text)
    statement.check()
    return statement


class Report:
    def __init__(self, generated, document_title="Rapport exécutif"):
        self.generated = generated
        self.document_title = document_title
        self.story = []
        self.statements = []
        self.footers = []

    def keep(self, statement):
        self.statements.append(statement)
        return statement

    def title(self, text):
        self.story.append(Paragraph(text, H1))

    def heading(self, text):
        self.story.append(Paragraph(text, H2))

    def para(self, statement, style=BODY):
        self.keep(statement)
        self.story.append(KeepTogether([Paragraph(_escape(statement.text), style)]))

    def bullets(self, statements):
        for statement in statements:
            self.keep(statement)
            lead = "<b>Alerte.</b> " if statement.kind == "alerte" else ""
            self.story.append(KeepTogether([Paragraph(lead + _escape(statement.text), BULLET, bulletText="•")]))

    def table(self, built, widths=None):
        header, rows, statement = built
        self.keep(statement)
        data = [[Paragraph(_escape(cell), CELL_HEAD) for cell in header]]
        data += [[Paragraph(_escape(cell), CELL) for cell in row] for row in rows]
        table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BAND]),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, RULE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        self.story.append(table)
        self.story.append(Spacer(1, 3))

    def figure(self, path, caption, width=150 * mm):
        from PIL import Image as PilImage

        with PilImage.open(path) as picture:
            ratio = picture.height / picture.width
        block = [Image(str(path), width=width, height=width * ratio)]
        statement = self.keep(plain("légende", caption))
        block.append(Paragraph(_escape(statement.text), SMALL))
        self.story.append(KeepTogether(block))

    def _footer(self, canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 6.6)
        canvas.setFillColor(SECONDARY)
        page = f"Page {document.page}"
        self.footers.append(page)
        canvas.drawString(18 * mm, 10 * mm, AUTO_LABEL)
        canvas.drawString(18 * mm, 7.2 * mm, f"{PORTFOLIO_LABEL}. Pas de données de conservation.")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, page)
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
        canvas.restoreState()

    def save(self, path):
        document = BaseDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=14 * mm,
            bottomMargin=16 * mm,
            title=self.document_title,
            author="Pipeline du projet (généré automatiquement)",
        )
        frame = Frame(document.leftMargin, document.bottomMargin, document.width, document.height, id="main", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        document.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=self._footer)])
        document.build(self.story)


def _power_bi_sentence():
    """What the Power BI column rests on, read from the export file and the annex."""
    from src.reporting.commentary import PENDING, reconciliation
    from src.reporting.number_check import resolve
    from src.reporting.power_bi_export import EXPORT_FILE

    if not EXPORT_FILE.exists():
        return (
            "Aucune valeur n'a été lue dans Power BI Desktop : toute la colonne Power BI reste en attente d'export, "
            "et elle ne prouve rien à ce stade."
        )
    text = (
        "Les valeurs Power BI ont été lues dans le moteur local de Power BI Desktop par requête DAX, sans modifier le rapport. "
        "Le rendement chaîné et le drawdown maximal y sont recalculés en DAX à partir des rendements mensuels. "
        "Pour les autres lignes, la mesure relit la cellule publiée : un statut OK montre alors que le modèle charge le bon fichier et la bonne colonne, pas un calcul indépendant."
    )
    if float(resolve(reconciliation("statut_power_bi", {"statut_power_bi": PENDING}))) > 0:
        text += (
            " Les lignes en attente sont celles pour lesquelles aucune valeur n'a pu être lue ; "
            "leur cause est écrite dans l'annexe, colonne cause_power_bi."
        )
    if float(resolve(reconciliation("statut_power_bi", {"statut_power_bi": "EXCEPTION"}))) > 0:
        text += " Des lignes Power BI sont en EXCEPTION : elles restent ouvertes et leur cause est à écrire dans l'annexe."
    return text


def _escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_report(sections, figures, generated):
    """Write the PDF. Return the file, its statements and its structural strings."""
    report = Report(generated)
    facts, risks, advice, alerts, points = (
        sections[name] for name in ("faits", "risques", "recommandations", "alertes", "points")
    )

    report.title("Rapport exécutif : trois portefeuilles ODD en CHF")
    report.story.append(Paragraph(f"{AUTO_LABEL} Produit par le pipeline le {generated}.", LABEL))
    report.para(plain("périmètre", (
        "Périmètre. Mandat fictif CLIENT001, actions internationales cotées, devise de référence CHF. Trois livres, "
        "équipondéré, volatilité minimale et Sharpe maximal, construits sur la même liste de titres et comparés au fonds "
        "iShares MSCI Global Sustainable Development Goals, dont le rendement publié est converti en CHF."
    )))
    report.para(plain("périmètre", (
        "Données. Sources publiques seulement : feuille de positions et rendement publiés par iShares, cours de clôture et dividendes déclarés de Yahoo Finance, "
        "change et SARON de la Banque nationale suisse, registre d'éligibilité ODD saisi à partir des rapports des sociétés."
    )))
    report.para(plain("périmètre", (
        "Limites. " + SCOPE_NOTE + " Les poids sont décidés chaque trimestre sur les mois déjà observés, puis dérivent avec le marché jusqu'à la décision suivante. "
        + UNIVERSE_NOTE
    )))

    report.heading("Faits marquants")
    # The Sharpe ratios, the final wealth and the control count are in the tables below.
    report.bullets(pick(facts, "fenetre") + pick(facts, "rendement"))

    report.heading("Recommandations")
    report.bullets(advice)
    report.para(plain("avertissement", DISCLAIMER), SMALL)
    report.figure(figures["link"], (
        "Chaque point est un mois : en abscisse le rendement du fonds, en ordonnée celui du livre, en CHF. "
        "Sur la diagonale en pointillé, les deux rendent autant. La droite ajustée a pour pente le bêta."
    ), width=122 * mm)

    report.heading("Performance contre le fonds iShares, en CHF")
    report.table(content.performance_table(), widths=[34 * mm, 22 * mm, 19 * mm, 15 * mm, 15 * mm, 24 * mm, 21 * mm, 24 * mm])
    report.figure(figures["wealth"], (
        "Richesse cumulée pour une unité investie au début de la fenêtre. Le fonds est en pointillé. "
        "Rendements totaux : livres bruts de frais et d'impôt à la source, fonds net de ses frais."
    ), width=115 * mm)

    report.heading("Risque : VaR, expected shortfall, corrélation")
    report.table(content.risk_table(), widths=[36 * mm, 29 * mm, 25 * mm, 33 * mm, 21 * mm, 30 * mm])
    report.bullets(
        pick(risks, "var") + pick(risks, "echantillon") + pick(risks, "drawdown")
        + pick(risks, "correlation") + pick(risks, "concentration")
    )

    report.heading("Tests de résistance (illustratifs)")
    report.table(content.shock_definitions(), widths=[24 * mm, 150 * mm])
    report.para(plain("chocs", (
        "Richesse finale pour une unité investie, par livre et par choc. Les chocs sont des paramètres écrits à l'avance, "
        "pas des prévisions :"
    )), SMALL)
    report.table(content.stress_table(), widths=[36 * mm, 24 * mm, 24 * mm, 24 * mm, 24 * mm, 24 * mm])
    report.bullets(pick(risks, "chocs_limites"))

    report.heading("Qualité des données")
    report.bullets(pick(alerts, "qualite") + pick(alerts, "qualite_ponderation"))
    report.table(content.quality_table(), widths=[52 * mm, 34 * mm, 28 * mm])

    report.heading("Contrôle des calculs : Python, Excel, Power BI")
    report.para(plain("contrôle", (
        "Trois lectures du même indicateur sont comparées dans l'annexe Excel. Python publie l'indicateur. Excel le recalcule "
        "à partir des seuls rendements mensuels, sans lire le chiffre de Python. Power BI recalcule en DAX deux indicateurs, "
        "le rendement chaîné et le drawdown maximal, et relit la cellule publiée pour tous les autres."
    )))
    report.table(content.reconciliation_table(), widths=[44 * mm, 18 * mm, 24 * mm, 88 * mm])
    report.para(content.reconciliation_sentence())
    report.para(plain("contrôle", (
        "Écarts et causes. Aucun écart ne dépasse la tolérance entre Python et Excel : le pipeline s'arrête sinon. La ligne non publiée est le ratio "
        "d'information du fonds : le fonds est la référence, son écart de suivi est nul et le ratio n'est pas défini. "
        + _power_bi_sentence()
    )))
    report.para(plain("contrôle", (
        "Ce que ce contrôle ne prouve pas. Il prouve que les formules se recoupent sur les mêmes rendements mensuels. "
        "Il ne prouve pas que les titres ont été détenus, que les cours sont ceux d'un dépositaire, ni que des frais ont été prélevés : "
        "il n'y a pas de données de conservation. Il ne valide pas non plus les rendements mensuels eux-mêmes, qui sont l'entrée commune des trois lectures : "
        "leur base (rendement total brut, poids qui dérivent entre deux rééquilibrages) et les définitions des indicateurs sont celles du pipeline, que les trois lectures reprennent."
    )))

    report.heading("Alertes liées aux limites du mandat")
    report.bullets([item for item in alerts if item.tag not in ("qualite", "qualite_ponderation")])
    report.bullets(pick(risks, "odd"))

    report.heading("Points à instruire")
    report.bullets(points)

    EXECUTIVE_REPORTS.mkdir(parents=True, exist_ok=True)
    report.save(REPORT_FILE)
    structural = tuple(sorted(set(report.footers))) + (generated, "CLIENT001")
    return REPORT_FILE, report.statements, structural


def read_report(path=REPORT_FILE):
    """Text and page count of the written PDF."""
    import fitz

    with fitz.open(str(path)) as document:
        pages = document.page_count
        text = "\n".join(page.get_text() for page in document)
    return text, pages


def check_pages(pages):
    if pages > EXECUTIVE_REPORT_MAX_PAGES:
        raise RuntimeError(
            f"The executive report has {pages} pages, more than EXECUTIVE_REPORT_MAX_PAGES ({EXECUTIVE_REPORT_MAX_PAGES})."
        )
    return pages
