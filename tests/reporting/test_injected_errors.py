"""
Three injected errors, on a copy, calculated by Excel.

The production monthly-return file is only read. Each case has its own
wealth chain. A clean copy of the same months must stay OK: if it did
not, an EXCEPTION on the dirty copies would not prove that the error
was detected.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.portfolio_construction.build_portfolios import MONTHLY_RETURNS_FILE
from src.reporting.build_workbook import calculate_in_excel


MONTHS = 12
SAMPLE = "equal_weight"


def _annualized(values, periods_per_year):
    growth = 1.0
    for value in values:
        growth *= 1.0 + float(value)
    return growth ** (periods_per_year / len(values)) - 1.0


def _sample():
    frame = pd.read_csv(MONTHLY_RETURNS_FILE)
    book = frame.loc[frame["strategy"].astype(str).eq(SAMPLE)].sort_values("month")
    months = book["month"].astype(str).tolist()[:MONTHS]
    returns = [float(value) for value in book["portfolio_return"].tolist()[:MONTHS]]
    if len(months) != MONTHS:
        raise RuntimeError("The published file does not have twelve months to copy.")
    return months, returns


def _table(worksheet, name, ref):
    table = Table(displayName=name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    worksheet.add_table(table)


def _wealth(worksheet, first, count):
    worksheet.cell(first, 3, "=1+B" + str(first))
    for index in range(first + 1, first + count):
        worksheet.cell(index, 3, f"=C{index - 1}*(1+B{index})")


def _write(path, months, returns):
    published = _annualized(returns, 12)
    falsified = list(returns)
    falsified[-1] = falsified[-1] + 0.05
    shifted = list(months)
    shifted[5] = "1999-01"

    workbook = Workbook()
    parameters = workbook.active
    parameters.title = "Parametres"
    parameters["A3"] = "Tolerance"
    parameters["B3"] = 1e-8
    parameters["A4"] = "MoisParAn"
    parameters["B4"] = 12
    workbook.defined_names.add(DefinedName(name="Tolerance", attr_text="Parametres!$B$3"))
    workbook.defined_names.add(DefinedName(name="MoisParAn", attr_text="Parametres!$B$4"))

    clean = workbook.create_sheet("Copie_propre")
    dirty = workbook.create_sheet("Copie_rendement")
    for worksheet, values, labels, table_name in (
        (clean, returns, months, "Propre"),
        (dirty, falsified, months, "Falsifie"),
    ):
        worksheet["A3"] = "month"
        worksheet["B3"] = "portfolio_return"
        for index, (month, value) in enumerate(zip(labels, values), 4):
            worksheet.cell(index, 1, month)
            worksheet.cell(index, 2, value)
        _table(worksheet, table_name, f"A3:B{3 + MONTHS}")
        _wealth(worksheet, 4, MONTHS)

    lookup = workbook.create_sheet("Copie_dates")
    lookup["A3"] = "month"
    lookup["B3"] = "portfolio_return"
    for index, (month, value) in enumerate(zip(months, returns), 4):
        lookup.cell(index, 1, month)
        lookup.cell(index, 2, value)
    _table(lookup, "DatesDecalees", f"A3:B{3 + MONTHS}")

    asked = workbook.create_sheet("Mois_demandes")
    for index, month in enumerate(shifted, 4):
        asked.cell(index, 1, month)
        asked.cell(
            index,
            2,
            (
                f'=IF(COUNTIFS(DatesDecalees[month],A{index})<>1,NA(),'
                f'SUMIFS(DatesDecalees[portfolio_return],DatesDecalees[month],A{index}))'
            ),
        )
    _wealth(asked, 4, MONTHS)

    sheet = workbook.create_sheet("Reconciliation")
    headers = (
        "cas",
        "valeur_python",
        "valeur_excel",
        "ecart",
        "tolerance",
        "statut",
        "cause",
        "cloture",
    )
    for column, header in enumerate(headers, 1):
        sheet.cell(4, column, header)
    cases = (
        ("copie propre", published, f"=Copie_propre!C{3 + MONTHS}^(MoisParAn/{MONTHS})-1"),
        ("rendement mensuel falsifie", published, f"=Copie_rendement!C{3 + MONTHS}^(MoisParAn/{MONTHS})-1"),
        ("date decalee d'un mois", published, f"=Mois_demandes!C{3 + MONTHS}^(MoisParAn/{MONTHS})-1"),
        ("annualisation sur 252", published, f"=Copie_propre!C{3 + MONTHS}^(252/{MONTHS})-1"),
    )
    for offset, (label, python_value, formula) in enumerate(cases):
        row = 5 + offset
        sheet.cell(row, 1, label)
        sheet.cell(row, 2, python_value)
        sheet.cell(row, 3, formula)
        sheet.cell(row, 4, f'=IF(NOT(ISNUMBER(C{row})),"",C{row}-B{row})')
        sheet.cell(row, 5, "=Tolerance")
        sheet.cell(
            row,
            6,
            f'=IF(NOT(ISNUMBER(C{row})),"EXCEPTION",IF(ABS(C{row}-B{row})<=E{row},"OK","EXCEPTION"))',
        )
        sheet.cell(row, 7, None)
        sheet.cell(row, 8, f'=IF(F{row}="OK","clos",IF(G{row}="","ouvert","clos"))')
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def _read(path):
    calculated = load_workbook(path, data_only=True)
    sheet = calculated["Reconciliation"]
    rows = {}
    for row in range(5, 9):
        rows[sheet.cell(row, 1).value] = {
            "cas": sheet.cell(row, 1).value,
            "excel": sheet.cell(row, 3).value,
            "statut": sheet.cell(row, 6).value,
            "cloture": sheet.cell(row, 8).value,
        }
    calculated.close()
    return rows


def _require_exception(row):
    """Fail when an injected error is still OK. That failure is the check."""
    if row["statut"] != "EXCEPTION" or row["cloture"] != "ouvert":
        raise AssertionError(f"injected error was not detected: {row}")


@pytest.fixture(scope="module")
def production_digest():
    return hashlib.sha256(MONTHLY_RETURNS_FILE.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def calculated(tmp_path_factory, production_digest):
    path = tmp_path_factory.mktemp("injection") / "injection_annexe.xlsx"
    months, returns = _sample()
    _write(path, months, returns)
    calculate_in_excel(path)
    rows = _read(path)
    digest = hashlib.sha256(MONTHLY_RETURNS_FILE.read_bytes()).hexdigest()
    if digest != production_digest:
        raise RuntimeError("The injection test wrote the production monthly returns.")
    return rows


def test_clean_copy_stays_ok(calculated):
    row = calculated["copie propre"]
    assert row["statut"] == "OK"
    assert row["cloture"] == "clos"
    assert isinstance(row["excel"], float)


def test_falsified_return_is_exception(calculated):
    _require_exception(calculated["rendement mensuel falsifie"])


def test_shifted_month_is_exception(calculated):
    _require_exception(calculated["date decalee d'un mois"])


def test_wrong_annualization_is_exception(calculated):
    _require_exception(calculated["annualisation sur 252"])


def test_undetected_error_fails_the_check():
    missed = {
        "cas": "rendement mensuel falsifie",
        "statut": "OK",
        "cloture": "clos",
    }
    with pytest.raises(AssertionError, match="not detected"):
        _require_exception(missed)


def test_production_file_is_unchanged(production_digest):
    digest = hashlib.sha256(MONTHLY_RETURNS_FILE.read_bytes()).hexdigest()
    assert digest == production_digest
