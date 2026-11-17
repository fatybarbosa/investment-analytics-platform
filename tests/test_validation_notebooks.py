"""
Run the validation notebooks of the phases under pytest.

Each notebook rebuilds its phase from the raw inputs and asserts the result.
They need the raw price file and the local database, so they are skipped on a
machine that only has the versioned files. They run in memory and are not saved.
"""

from __future__ import annotations

from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted(ROOT.glob("tests/*/phase_*_validation.ipynb"))

pytestmark = [pytest.mark.needs_inputs, pytest.mark.notebook]


@pytest.mark.parametrize("path", NOTEBOOKS, ids=[path.stem for path in NOTEBOOKS])
def test_validation_notebook_passes(path):
    notebook = nbformat.read(path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=1800,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    )
    client.execute()
