"""
Fingerprint of the raw inputs a run was built from.

Yahoo Finance prices, SNB rates and the iShares holdings sheet change from
one download to the next, and the raw price file is too large and not ours to
redistribute, so it is not versioned. This manifest keeps what a reader needs
to know which inputs the published results come from: the SHA-256 of each
raw file, its size and its number of lines.

It does not make a run reproducible without the network. It makes a
difference visible: a later run that produces other numbers can be traced to
other inputs, because the fingerprint changed. The file has no timestamp, so
an unchanged input leaves it unchanged.

Output
------
data/input_manifest.json
"""

from __future__ import annotations

import hashlib
import json

from src.config import DATA_DIR, FX, MACRO, MARKET, BENCHMARK, ODD, PROJECT_ROOT
from src.utils.logger import logger
from src.utils.files import replace_file


MANIFEST_FILE = DATA_DIR / "input_manifest.json"
RAW_INPUTS = (
    MARKET / "market_prices.csv",
    FX / "fx_rates.csv",
    MACRO / "saron.csv",
    BENCHMARK / "benchmark_holdings.xls",
    ODD / "odd_assessment.csv",
)
CHUNK = 1024 * 1024


def fingerprint(path):
    """SHA-256, size in bytes and number of lines of one file."""
    digest = hashlib.sha256()
    size = 0
    lines = 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(CHUNK)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
            lines += chunk.count(b"\n")
    return {"sha256": digest.hexdigest(), "bytes": size, "lines": lines}


def write_input_manifest(inputs=RAW_INPUTS, destination=MANIFEST_FILE):
    """Write the manifest of the raw inputs. A missing input stops the run."""
    entries = {}
    for path in inputs:
        if not path.exists():
            raise RuntimeError(f"The raw input {path} is missing, so the manifest cannot be written.")
        entries[path.relative_to(PROJECT_ROOT).as_posix()] = fingerprint(path)
    payload = {
        "note": (
            "Fingerprint of the raw inputs of the last run. The raw price file is not versioned: "
            "a run from a fresh download can give other numbers, and a changed sha256 says why."
        ),
        "inputs": entries,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    replace_file(temporary, destination)
    logger.info("Input manifest written: %s inputs, %s", len(entries), destination)
    return destination
