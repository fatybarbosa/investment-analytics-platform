"""
Phase 11. Every number of a text must come from a pipeline file.

A text is written with facts. A fact names a pipeline file, a row filter,
a column and an operation. The check does not trust the value the writer
loaded: it reads the file again, extracts every number of the text, and
requires each one to be a declared fact at the precision the text prints.

Two levels
----------
check_statement : one sentence against the facts declared for it.
check_document  : the text extracted from a finished file (PDF, PPTX,
                  Markdown) against every fact declared for that file.

A number that matches no fact raises NumberCheckError, and the pipeline
stops. No tolerance is tuned here: a printed number matches a file value
only if rounding the file value to the printed decimals gives that number.

Sources a fact may name
-----------------------
*.csv            a published CSV, relative to the project root
*.xlsx           a sheet of a pipeline workbook, with its header row
py:<module>      a constant of a pipeline module (src.config for the caps)
"""

from __future__ import annotations

import importlib
import math
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

from src.config import PROJECT_ROOT


AUTO_LABEL = "Généré automatiquement, à relire avant diffusion."
NBSP = " "
OPERATIONS = ("cell", "count", "sum", "max", "min", "last", "maxabs")
# ratio   : file value 0.0529, printed "5,29 %" or, without a percent sign, "0,05"
# percent : file value 99.68 already in percent, printed "99,68 %"
# raw     : file value printed as it is (count, ratio without unit, multiple)
# text    : file value is a label such as a month "2016-11"
SCALES = ("ratio", "percent", "raw", "text")

MONTH_PATTERN = re.compile(r"(?<![\w-])\d{4}-\d{2}(?![\w-])")
NUMBER_PATTERN = re.compile(
    r"(?<![\w.,])(?<!\w-)"
    r"(?P<body>-?\d+(?:[   ]\d{3})*(?:,\d+)?(?:e-?\d+)?)"
    r"(?![\w])"
    r"(?P<percent>[   ]?%)?"
)


class NumberCheckError(RuntimeError):
    """A number of a text is not in the pipeline files."""


@dataclass(frozen=True)
class Fact:
    source: str
    column: str
    where: tuple = ()
    op: str = "cell"
    scale: str = "raw"
    sheet: str | None = None
    header: int = 0

    def label(self):
        place = self.source if self.sheet is None else f"{self.source}[{self.sheet}]"
        rows = ", ".join(f"{key}={value}" for key, value in self.where)
        return f"{place} | {self.op} {self.column}" + (f" | {rows}" if rows else "")


def fact(source, column, where=None, op="cell", scale="raw", sheet=None, header=0):
    if op not in OPERATIONS:
        raise ValueError(f"Unknown operation: {op}")
    if scale not in SCALES:
        raise ValueError(f"Unknown scale: {scale}")
    items = tuple(sorted((where or {}).items()))
    return Fact(str(source).replace("\\", "/"), str(column), items, op, scale, sheet, header)


@lru_cache(maxsize=None)
def _frame(source, sheet, header):
    path = PROJECT_ROOT / source
    if not path.exists():
        raise NumberCheckError(f"Pipeline file missing: {source}")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return pd.read_excel(path, sheet_name=sheet, header=header)
    raise NumberCheckError(f"Unsupported pipeline file: {source}")


def clear_cache():
    """Forget the files already read. Call before a new check."""
    _frame.cache_clear()


def resolve(item):
    """Read the fact from disk again. The writer's value is not used."""
    if item.source.startswith("py:"):
        module = importlib.import_module(item.source[3:])
        if not hasattr(module, item.column):
            raise NumberCheckError(f"{item.source} has no constant {item.column}")
        return getattr(module, item.column)
    frame = _frame(item.source, item.sheet, item.header)
    rows = frame
    for key, value in item.where:
        if key not in rows.columns:
            raise NumberCheckError(f"{item.label()}: column {key} is absent")
        rows = rows.loc[rows[key].astype(str) == str(value)]
    if item.op == "count":
        return int(len(rows))
    if item.column not in rows.columns:
        raise NumberCheckError(f"{item.label()}: column {item.column} is absent")
    values = rows[item.column]
    if item.op == "cell":
        if len(values) != 1:
            raise NumberCheckError(f"{item.label()}: {len(values)} rows, one expected")
        value = values.iloc[0]
    elif item.op == "last":
        if values.empty:
            raise NumberCheckError(f"{item.label()}: no row")
        value = values.iloc[-1]
    elif values.empty:
        raise NumberCheckError(f"{item.label()}: no row")
    else:
        numbers = pd.to_numeric(values, errors="coerce").dropna()
        if numbers.empty:
            raise NumberCheckError(f"{item.label()}: no numeric row")
        if item.op == "sum":
            value = numbers.sum()
        elif item.op == "max":
            value = numbers.max()
        elif item.op == "maxabs":
            value = numbers.abs().max()
        else:
            value = numbers.min()
    if hasattr(value, "item"):
        value = value.item()
    return value


def french(value, decimals):
    """Format a number the way the texts print it: comma, no-break spaces."""
    rounded = round(float(value), decimals)
    if rounded == 0:
        rounded = 0.0
    text = f"{abs(rounded):,.{decimals}f}".replace(",", NBSP).replace(".", ",")
    return ("-" if rounded < 0 else "") + text


@dataclass
class Token:
    text: str
    kind: str
    value: float | str
    decimals: int = 0
    percent: bool = False
    significant: int = 0


def tokenize(text, structural=()):
    """Every number of a text. Structural strings are removed first, by exact match."""
    work = str(text).replace("−", "-")
    for literal in sorted(structural, key=len, reverse=True):
        work = work.replace(literal, " § ")
    tokens = []
    for match in MONTH_PATTERN.finditer(work):
        tokens.append(Token(match.group(0), "month", match.group(0)))
    work = MONTH_PATTERN.sub(" § ", work)
    for match in NUMBER_PATTERN.finditer(work):
        body = match.group("body")
        compact = re.sub(r"[   ]", "", body)
        if "e" in compact:
            mantissa = compact.split("e")[0]
            digits = len(mantissa.replace("-", "").replace(",", ""))
            tokens.append(
                Token(body, "scientific", float(compact.replace(",", ".")), significant=digits)
            )
            continue
        decimals = len(compact.split(",")[1]) if "," in compact else 0
        tokens.append(
            Token(
                body + (match.group("percent") or ""),
                "number",
                float(compact.replace(",", ".")),
                decimals=decimals,
                percent=bool(match.group("percent")),
            )
        )
    return tokens


def _matches(token, item, value):
    if token.kind == "month":
        return item.scale == "text" and str(value) == token.value
    if item.scale == "text" or isinstance(value, str) or value is None:
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    if math.isnan(number):
        return False
    if token.kind == "scientific":
        if number == 0:
            return token.value == 0
        shown = float(f"{number:.{max(token.significant - 1, 0)}e}")
        return math.isclose(shown, token.value, rel_tol=1e-12)
    if token.percent:
        if item.scale == "ratio":
            number *= 100.0
        elif item.scale != "percent":
            return False
    return french(number, token.decimals) == french(token.value, token.decimals)


def check_tokens(text, facts, structural=(), where=""):
    """Return one audit row per number. Raise if a number has no fact."""
    resolved = [(item, resolve(item)) for item in facts]
    rows = []
    missing = []
    for token in tokenize(text, structural):
        hit = next((item for item, value in resolved if _matches(token, item, value)), None)
        if hit is None:
            missing.append(token.text)
            continue
        rows.append({"emplacement": where, "nombre": token.text, "source": hit.label()})
    if missing:
        listed = ", ".join(f"« {value} »" for value in missing)
        raise NumberCheckError(
            f"{where or 'texte'} : {listed} ne se retrouve dans aucun fichier du pipeline déclaré pour ce texte. "
            f"Texte : {str(text)[:240]}"
        )
    return rows


@dataclass
class Statement:
    """One sentence or one table cell, with the facts it prints."""

    section: str
    text: str
    facts: tuple = ()
    kind: str = "constat"
    structural: tuple = ()

    def check(self, where=None):
        return check_tokens(self.text, self.facts, structural=self.structural, where=where or self.section)


@dataclass
class Draft:
    """Collects the facts a sentence prints while it is being written."""

    facts: list = field(default_factory=list)
    labels: list = field(default_factory=list)

    def label(self, value):
        """A name read in a file (company, sector). Its digits are not numbers of the text."""
        value = str(value)
        if re.search(r"\d", value):
            self.labels.append(value)
        return value

    def _keep(self, item):
        self.facts.append(item)
        value = resolve(item)
        if value is None or (isinstance(value, float) and math.isnan(value)):
            raise NumberCheckError(f"{item.label()} : la valeur est vide dans le fichier, elle ne peut pas être citée.")
        return value

    def pct(self, item, decimals=2):
        value = self._keep(item)
        factor = 100.0 if item.scale == "ratio" else 1.0
        return f"{french(float(value) * factor, decimals)}{NBSP}%"

    def num(self, item, decimals=2):
        return french(self._keep(item), decimals)

    def count(self, item):
        return french(self._keep(item), 0)

    def text(self, item):
        return str(self._keep(item))

    def sci(self, item):
        value = float(self._keep(item))
        mantissa, exponent = f"{value:.0e}".split("e")
        return f"{mantissa}e{int(exponent)}"

    def value(self, item):
        """The file value, for a decision. The fact is declared only if printed."""
        return resolve(item)

    def done(self, section, text, kind="constat"):
        statement = Statement(section, text, tuple(self.facts), kind, tuple(self.labels))
        statement.check()
        return statement


def check_statements(statements):
    """Check every statement. Return the audit rows."""
    clear_cache()
    rows = []
    for index, statement in enumerate(statements, 1):
        rows.extend(statement.check(where=f"{statement.section} #{index}"))
    return rows


def check_document(text, statements, structural=(), where="document"):
    """Check the text read back from a finished file against all its facts."""
    clear_cache()
    facts = []
    seen = set()
    structural = tuple(structural) + tuple(
        label for statement in statements for label in statement.structural
    )
    for statement in statements:
        for item in statement.facts:
            if item not in seen:
                seen.add(item)
                facts.append(item)
    if AUTO_LABEL.casefold() not in " ".join(str(text).split()).casefold():
        raise NumberCheckError(f"{where} : la mention « {AUTO_LABEL} » est absente.")
    return check_tokens(text, facts, structural=structural, where=where)


def relative(path):
    return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
