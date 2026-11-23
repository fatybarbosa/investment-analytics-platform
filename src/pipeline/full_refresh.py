"""
One command for the complete monthly pass.

Order
-----
1. Close check: the Excel annex must not be open, or the command stops at once.
2. Data layer: `refresh --skip-office`, which acquires the datasets that are due
   and rebuilds the books, the monitoring, the performance, the risk, the
   shocks and the quality files.
3. Power BI: open Desktop if it is closed, refresh the model in memory, export
   the measures, and close Desktop again if this command opened it.
4. Full pass: `refresh`, which rebuilds the Excel annex, reconciles Python,
   Excel and Power BI, and writes the reports. It stops if a reconciliation line
   stays open or a number of a text is not in a pipeline file.
5. A list of what changed in git.

The command never commits and never pushes. The texts carry the label
"generated automatically, to be reviewed before distribution": a person reads
them, then versions them.

Windows with Excel and Power BI Desktop only.

Run:  python -m src.pipeline.full_refresh
"""

from __future__ import annotations

import os
import subprocess

from src.config import EXCEL_REPORTS, PROJECT_ROOT
from src.pipeline.refresh import refresh
from src.reporting.power_bi_export import export_power_bi
from src.reporting.power_bi_refresh import close_desktop, open_and_refresh
from src.utils.logger import logger

ANNEX_FILE = EXCEL_REPORTS / "annexe_reporting.xlsx"


def annex_is_locked():
    """True when the annex exists and another program holds it open."""
    if not ANNEX_FILE.exists():
        return False
    try:
        os.rename(ANNEX_FILE, ANNEX_FILE)
    except PermissionError:
        return True
    return False


def changed_files():
    completed = subprocess.run(
        ["git", "status", "--short"], cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8"
    )
    return [line for line in completed.stdout.splitlines() if line.strip()]


def full_refresh():
    if os.name != "nt":
        raise RuntimeError("The complete pass needs Windows, Excel and Power BI Desktop.")
    if annex_is_locked():
        raise RuntimeError(f"Close {ANNEX_FILE.name} in Excel, then run the command again.")

    logger.info("Full refresh, step 1 of 3: data layer")
    refresh(skip_office=True)

    logger.info("Full refresh, step 2 of 3: Power BI refresh and export")
    opened_here = open_and_refresh()
    try:
        export = export_power_bi()
    finally:
        if opened_here:
            close_desktop()
    if export["blanks"]:
        logger.warning("Power BI gave no value for %s measure(s)", len(export["blanks"]))

    logger.info("Full refresh, step 3 of 3: annex, reconciliation and reports")
    result = refresh()
    return {"export": export, "result": result, "changes": changed_files()}


def main():
    outcome = full_refresh()
    export = outcome["export"]
    executive = outcome["result"]["executive"]
    print(f"Power BI: {export['values']} values exported, model refreshed {export['refreshed']}")
    print(f"Executive report: {executive['report']} ({executive['pages']} pages)")
    print(f"Numbers checked: {executive['numbers_checked']}, alerts: {executive['alerts']}")
    print()
    print("Nothing is committed. Read the texts, then version them:")
    for line in outcome["changes"]:
        print(" ", line)
    if outcome["result"]["failures"]:
        for dataset_id, message in sorted(outcome["result"]["failures"].items()):
            print(f"FAILED {dataset_id}: {message}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
