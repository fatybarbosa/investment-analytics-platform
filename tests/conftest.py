"""
Skip the tests whose prerequisites are not on the machine.

office        Excel, through COM. Windows with Office only.
needs_inputs  the raw price file and the local database, which are not versioned.
"""

from __future__ import annotations

import platform
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INPUT_FILES = (
    ROOT / "data" / "02_processed" / "market" / "market_prices_chf.csv",
    ROOT / "database" / "sdg_investment.db",
)


def excel_installed():
    if platform.system() != "Windows":
        return False
    try:
        import winreg

        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Excel.Application"))
        return True
    except OSError:
        return False


def pytest_collection_modifyitems(config, items):
    office = excel_installed()
    inputs = all(path.exists() for path in INPUT_FILES)
    no_office = pytest.mark.skip(reason="Excel is not installed on this machine")
    no_inputs = pytest.mark.skip(reason="the raw prices and the local database are not on this machine")
    for item in items:
        if "office" in item.keywords and not office:
            item.add_marker(no_office)
        if "needs_inputs" in item.keywords and not inputs:
            item.add_marker(no_inputs)
