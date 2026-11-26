"""
A published Office file must not show the machine that wrote it: neither its
folders nor the name of its Office account.

The first tests read the published files. The others check the functions that
keep these out, on invented paths and names.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.config import PROJECT_AUTHOR
from src.reporting.build_workbook import remove_machine_traces
from src.reporting.export_acquisition_log import project_folder, without_machine_path
from src.reporting.management_deck import AUTHOR as DECK_AUTHOR

PUBLISHED = sorted(
    path
    for folder in ("audit", "reports", "data")
    for pattern in ("*.xlsx", "*.pptx")
    for path in (ROOT / folder).rglob(pattern)
    if ".ipynb_checkpoints" not in path.parts and not path.name.startswith("~$") and "01_raw" not in path.parts
)
USER_PATH = re.compile(r"(?i)[A-Z]:[\\/]+Users[\\/]+(?!user[\\/])")
PERSON = re.compile(r'<(?:dc:creator|cp:lastModifiedBy)\b[^>]*>([^<]+)<|\brefreshedBy="([^"]*)"')
RECORDED_NAMES = {PROJECT_AUTHOR, DECK_AUTHOR, "openpyxl"}


@pytest.mark.parametrize("path", PUBLISHED, ids=lambda path: path.name)
def test_a_published_office_file_shows_no_user_folder(path):
    with zipfile.ZipFile(path) as package:
        for item in package.namelist():
            text = package.read(item).decode("utf-8", "ignore")
            assert "absPath" not in text, item
            assert not USER_PATH.search(text), item
            for match in PERSON.finditer(text):
                assert (match.group(1) or match.group(2)) in RECORDED_NAMES, item


def test_a_storage_folder_is_written_from_the_project_root():
    root = "C:\\Users\\someone\\project"
    assert project_folder("C:\\Users\\someone\\project\\data\\01_raw", root) == "data/01_raw"
    assert project_folder("c:/users/SOMEONE/project/audit", root) == "audit"
    assert project_folder("C:\\Users\\someone\\Downloads\\old_copy", root) == "old_copy"
    assert project_folder(None, root) is None


def test_a_note_loses_the_project_and_user_folders():
    root = "C:\\Users\\someone\\project"
    note = "Missing file: C:\\Users\\someone\\project\\data\\prices.csv (see C:\\Users\\someone\\AppData\\log.txt)"
    cleaned = without_machine_path(note, root)
    assert "someone" not in cleaned
    assert "data\\prices.csv" in cleaned
    assert "C:\\Users\\user\\AppData" in cleaned


def test_only_the_machine_traces_leave_the_workbook(tmp_path):
    kept = '<workbook><workbookPr/><sheets><sheet name="A"/></sheets></workbook>'
    block = (
        '<mc:AlternateContent xmlns:mc="m"><mc:Choice Requires="x15">'
        '<x15ac:absPath url="C:\\Users\\someone\\project\\" xmlns:x15ac="a"/></mc:Choice></mc:AlternateContent>'
    )
    properties = "<p><dc:creator>openpyxl</dc:creator><cp:lastModifiedBy>Some ONE</cp:lastModifiedBy><dc:title>T</dc:title></p>"
    path = tmp_path / "annex.xlsx"
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("xl/workbook.xml", kept.replace("<workbookPr/>", "<workbookPr/>" + block))
        package.writestr("xl/worksheets/sheet1.xml", "<worksheet/>")
        package.writestr("docProps/core.xml", properties)
        package.writestr("xl/pivotCache/pivotCacheDefinition1.xml", '<pivotCacheDefinition refreshedBy="Some ONE" x="1"/>')
    remove_machine_traces(path)
    with zipfile.ZipFile(path) as package:
        assert package.read("xl/workbook.xml").decode("utf-8") == kept
        assert package.read("xl/worksheets/sheet1.xml") == b"<worksheet/>"
        written = package.read("docProps/core.xml").decode("utf-8")
        assert written == properties.replace("openpyxl", PROJECT_AUTHOR).replace("Some ONE", PROJECT_AUTHOR)
        pivot = package.read("xl/pivotCache/pivotCacheDefinition1.xml").decode("utf-8")
        assert pivot == f'<pivotCacheDefinition refreshedBy="{PROJECT_AUTHOR}" x="1"/>'
