"""
Phase 11. Executive reporting.

Writes the automated comments, the executive report and the management
deck from the published files, then checks every number of the three
texts against those files. A number that is not found stops the run:
the deliverable stays on disk for inspection, the command fails, and
the cause is in logs/technical.log.

Order
-----
1. Write every sentence with its facts. Each one is checked as it is written.
2. Write the comments (Markdown and JSON). Read the Markdown back and check it.
3. Draw the figures from the published CSV files.
4. Write the PDF. Read its text back, check it, and check the page count.
5. Write the deck. Read its text back, check it, and check the slide count.
6. Write the audit trail: one row per number, with the file it comes from.

Outputs
-------
reports/executive/commentaires_automatises.md
reports/executive/commentaires_automatises.json
reports/executive/rapport_executif.pdf
reports/executive/controle_des_nombres.csv
reports/executive/figures/*.png
reports/management/presentation_management.pptx
reports/clients/rapport_client.pdf
reports/clients/rapport_gerant.pdf
reports/clients/monthly_report_client.pdf
reports/clients/monthly_report_manager.pdf
reports/executive/cas_d_investigation.md
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from src.config import EXECUTIVE_REPORTS
from src.reporting import report_content
from src.reporting.commentary import (
    COMMENT_MD,
    all_statements,
    build_statements,
    write_commentary,
)
from src.reporting.client_reports import build_client_reports, check_client_pages
from src.reporting.executive_report import build_report, check_pages, read_report
from src.reporting.investigations import build_investigations
from src.reporting.management_deck import build_deck, check_slides, read_deck
from src.reporting.number_check import NumberCheckError, check_document, check_statements
from src.utils.logger import logger


AUDIT_FILE = EXECUTIVE_REPORTS / "controle_des_nombres.csv"
AUDIT_COLUMNS = ("livrable", "emplacement", "nombre", "source")


def _tag(rows, deliverable):
    return [{"livrable": deliverable, **row} for row in rows]


def build_executive():
    """Write the three deliverables and stop if a number has no source."""
    logger.info("Executive reporting started")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    audit = []
    try:
        sections = build_statements()
        statements = all_statements(sections)
        audit += _tag(check_statements(statements), "commentaires (phrase par phrase)")
        logger.info("Automated comments: %s sentences, %s numbers checked", len(statements), len(audit))

        comment_md, comment_json = write_commentary(sections, generated)
        rows = check_document(
            COMMENT_MD.read_text(encoding="utf-8"), statements, structural=(generated,), where="commentaires_automatises.md"
        )
        audit += _tag(rows, "commentaires_automatises.md")
        logger.info("Comments written and read back: %s, %s numbers checked", comment_md, len(rows))

        figures = report_content.build_figures()
        logger.info("Figures: %s", len(figures))

        report_file, report_statements, report_structural = build_report(sections, figures, generated)
        text, pages = read_report(report_file)
        rows = check_document(text, report_statements, structural=report_structural, where="rapport_executif.pdf")
        audit += _tag(rows, "rapport_executif.pdf")
        check_pages(pages)
        logger.info("Executive report: %s, %s pages, %s numbers checked", report_file, pages, len(rows))

        deck_file, deck_statements, deck_structural = build_deck(sections, figures, generated)
        text, slides = read_deck(deck_file)
        rows = check_document(text, deck_statements, structural=deck_structural, where="presentation_management.pptx")
        audit += _tag(rows, "presentation_management.pptx")
        check_slides(slides)
        logger.info("Management deck: %s, %s slides, %s numbers checked", deck_file, slides, len(rows))

        client_files = []
        for client_file, client_statements, client_structural in build_client_reports(sections, figures, generated):
            text, client_pages = read_report(client_file)
            rows = check_document(text, client_statements, structural=client_structural, where=client_file.name)
            audit += _tag(rows, client_file.name)
            check_client_pages(client_pages, client_file)
            client_files.append((client_file, client_pages))
            logger.info("Client report: %s, %s pages, %s numbers checked", client_file, client_pages, len(rows))

        cases_file, case_statements = build_investigations(generated)
        rows = check_document(
            cases_file.read_text(encoding="utf-8"), case_statements, structural=(generated,), where=cases_file.name
        )
        audit += _tag(rows, cases_file.name)
        logger.info("Investigation cases: %s, %s numbers checked", cases_file, len(rows))
    except NumberCheckError as error:
        logger.error("Number check failed, the pipeline stops: %s", error)
        raise
    finally:
        if audit:
            EXECUTIVE_REPORTS.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(audit, columns=AUDIT_COLUMNS).to_csv(AUDIT_FILE, index=False, encoding="utf-8-sig")
    alerts = sum(1 for statement in statements if statement.kind == "alerte")
    logger.info("Executive reporting completed: %s numbers traced in %s, %s alerts", len(audit), AUDIT_FILE, alerts)
    return {
        "comments": comment_md,
        "comments_json": comment_json,
        "report": report_file,
        "pages": pages,
        "deck": deck_file,
        "slides": slides,
        "clients": client_files,
        "cases": cases_file,
        "numbers_checked": len(audit),
        "alerts": alerts,
        "audit": AUDIT_FILE,
    }


if __name__ == "__main__":
    outcome = build_executive()
    for key, value in outcome.items():
        print(f"{key}: {value}")
