"""
Write the data dictionary from the files that are on disk.

The page lists column names and row counts. It does not interpret a
result, and it does not type a number by hand. The SQLite section is
written only when the local database is present: that file is not part
of the repository. The SQL files in sql/ are executed against it when
it is present, and a failing statement stops the command.
"""

import sqlite3

import pandas as pd

from src.config import (
    DATABASE_FILE,
    MONITORING_DATA,
    PERFORMANCE_DATA,
    PORTFOLIO_DATA,
    PROJECT_ROOT,
    RAW_DIR,
    RISK_DATA,
    STRESS_DATA,
    UNIVERSE_DIR,
    source_id,
)
from src.utils.files import replace_file


DICTIONARY_FILE = PROJECT_ROOT / "documentation" / "DICTIONNAIRE_DONNEES.md"
SQL_DIR = PROJECT_ROOT / "sql"
FAILING_ROW_CONTROLS = ("12_controle_somme_des_poids.sql", "15_controle_rotation.sql")
LABEL = "Généré automatiquement, à relire avant diffusion."

GROUPS = (
    ("Données brutes", source_id(RAW_DIR)),
    ("Univers", source_id(UNIVERSE_DIR)),
    ("Portefeuilles", source_id(PORTFOLIO_DATA)),
    ("Suivi", source_id(MONITORING_DATA)),
    ("Performance", source_id(PERFORMANCE_DATA)),
    ("Risque", source_id(RISK_DATA)),
    ("Résistance", source_id(STRESS_DATA)),
)


def _csv_files():
    found = []
    for title, relative in GROUPS:
        folder = PROJECT_ROOT / relative
        if not folder.exists():
            continue
        paths = sorted(
            path
            for path in folder.rglob("*.csv")
            if "Sources" not in path.parts and ".ipynb_checkpoints" not in path.parts
        )
        found.append((title, paths))
    return found


def _csv_section(title, paths):
    lines = [f"## {title}", ""]
    if not paths:
        lines.append("Aucun fichier dans ce dossier.")
        lines.append("")
        return lines
    for path in paths:
        frame = pd.read_csv(path, nrows=0)
        full = pd.read_csv(path)
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        lines.append(f"### `{relative}`")
        lines.append("")
        lines.append(f"Lignes : {len(full)}.")
        lines.append("")
        lines.append("| Colonne |")
        lines.append("|---|")
        for column in frame.columns:
            lines.append(f"| `{column}` |")
        lines.append("")
    return lines


def _database_section():
    lines = ["## Base SQLite", ""]
    if not DATABASE_FILE.exists():
        lines.append(
            f"`{DATABASE_FILE.relative_to(PROJECT_ROOT).as_posix()}` n'est pas sur ce disque. "
            "Le fichier n'est pas versionné. `python -m src.pipeline.refresh` le reconstruit "
            "à partir du registre des sources."
        )
        lines.append("")
        return lines
    connection = sqlite3.connect(DATABASE_FILE)
    try:
        names = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        ]
        lines.append(
            f"Fichier local `{DATABASE_FILE.relative_to(PROJECT_ROOT).as_posix()}`. "
            f"Tables : {len(names)}."
        )
        lines.append("")
        for name in names:
            columns = [
                row[1]
                for row in connection.execute(f'PRAGMA table_info("{name}")')
            ]
            count = connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            lines.append(f"### `{name}`")
            lines.append("")
            lines.append(f"Lignes : {count}.")
            lines.append("")
            lines.append("| Colonne |")
            lines.append("|---|")
            for column in columns:
                lines.append(f"| `{column}` |")
            lines.append("")
    finally:
        connection.close()
    return lines


def _statements(text):
    """SQL statements, with the comment lines removed."""
    statements = []
    for part in text.split(";"):
        lines = [
            line
            for line in part.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        statement = "\n".join(lines).strip()
        if statement:
            statements.append(statement)
    return statements


def execute_sql():
    """Run every statement file. Raise if the database is missing or a statement fails."""
    if not DATABASE_FILE.exists():
        raise RuntimeError("The SQL files need the local database, and it is absent.")
    scripts = sorted(SQL_DIR.glob("*.sql"))
    if not scripts:
        raise RuntimeError("No SQL file is published.")
    from src.database.load_books import load_book_tables

    connection = sqlite3.connect(DATABASE_FILE)
    try:
        load_book_tables(connection)
        for script in scripts:
            for statement in _statements(script.read_text(encoding="utf-8")):
                rows = connection.execute(statement).fetchall()
                # These queries return a row only when their check fails.
                if script.name in FAILING_ROW_CONTROLS and rows:
                    raise RuntimeError(f"SQL control {script.name} failed on {len(rows)} row(s): {rows[0]}")
    finally:
        connection.close()
    return scripts


def render_dictionary():
    """The dictionary text. Column names and counts come from the files."""
    lines = [
        "# Dictionnaire de données",
        "",
        LABEL,
        "",
        "Ce dictionnaire est réécrit par `python -m src.reporting.data_dictionary`. "
        "Il décrit les colonnes. Il ne commente pas un résultat.",
        "",
        "Les rapports de société utilisés pour l'éligibilité restent hors du dépôt.",
        "",
    ]
    for title, paths in _csv_files():
        lines.extend(_csv_section(title, paths))
    lines.extend(_database_section())
    lines.append("## Requêtes SQL")
    lines.append("")
    lines.append(
        "Les fichiers de `sql/` s'exécutent sur la base locale. "
        "Ils posent une question de contrôle. Ils ne publient pas un indicateur de portefeuille : "
        "ces indicateurs sont dans les fichiers des phases 5 à 9."
    )
    lines.append("")
    for script in sorted(SQL_DIR.glob("*.sql")):
        lines.append(f"- `{script.relative_to(PROJECT_ROOT).as_posix()}`")
    lines.append("")
    return "\n".join(lines)


def write_dictionary():
    """Write the dictionary and prove that the SQL files run."""
    scripts = execute_sql() if DATABASE_FILE.exists() else []
    DICTIONARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    text = render_dictionary()
    if not DATABASE_FILE.exists() and "n'est pas sur ce disque" not in text:
        raise RuntimeError("The dictionary does not say that the database is absent.")
    temporary = DICTIONARY_FILE.with_suffix(".md.tmp")
    temporary.write_text(text, encoding="utf-8")
    replace_file(temporary, DICTIONARY_FILE)
    return {"dictionary": DICTIONARY_FILE, "sql": scripts}


def main():
    written = write_dictionary()
    print(written["dictionary"])
    print(f"{len(written['sql'])} SQL files executed")


if __name__ == "__main__":
    main()
