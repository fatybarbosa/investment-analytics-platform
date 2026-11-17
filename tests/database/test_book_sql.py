"""
The SQL files that read the published book tables.

A temporary database is built from the published files, so the test needs
neither the real database nor the network. The control queries must return
nothing, the chained wealth must match the published one, and the ranking and
window queries must return the rows they promise.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.database.load_books import BOOK_TABLES, load_book_tables
from src.reporting.data_dictionary import SQL_DIR, _statements

BOOKS = ("equal_weight", "minimum_volatility", "maximum_sharpe")
TOLERANCE = 1e-8


@pytest.fixture(scope="module")
def connection():
    handle = sqlite3.connect(":memory:")
    load_book_tables(handle)
    yield handle
    handle.close()


def run(connection, name):
    text = (SQL_DIR / name).read_text(encoding="utf-8")
    frames = [pd.read_sql(statement, connection) for statement in _statements(text)]
    assert len(frames) == 1
    return frames[0]


def test_every_book_file_is_loaded_unchanged(connection):
    for table, path in BOOK_TABLES.items():
        stored = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert stored == len(pd.read_csv(path)), table


def test_the_weights_of_every_book_and_month_make_one(connection):
    assert run(connection, "12_controle_somme_des_poids.sql").empty


def test_the_rotation_is_the_sum_of_the_weight_changes(connection):
    assert run(connection, "15_controle_rotation.sql").empty


def test_a_third_calculation_in_sql_gives_the_published_wealth(connection):
    result = run(connection, "13_richesse_chainee.sql")
    assert set(result["strategy"]) == set(BOOKS)
    assert len(result) == len(BOOKS)
    assert (result["ecart"] <= TOLERANCE).all()


def test_the_sector_weights_of_a_book_add_up_to_its_share_of_one(connection):
    result = run(connection, "10_poids_par_secteur.sql")
    assert set(result["strategy"]) == set(BOOKS)
    sums = result.groupby("strategy")["part_du_livre"].sum()
    assert (sums.sub(1.0).abs() < 1e-3).all()


def test_five_contributors_and_five_detractors_per_book(connection):
    result = run(connection, "11_contributeurs_detracteurs.sql")
    counts = result.groupby(["strategy", "role"]).size()
    for book in BOOKS:
        assert counts[(book, "contributeur")] == 5
        assert counts[(book, "détracteur")] == 5
    top = result.loc[result["role"].eq("contributeur")].groupby("strategy")["contribution_cumulee"].min()
    bottom = result.loc[result["role"].eq("détracteur")].groupby("strategy")["contribution_cumulee"].max()
    assert (top.values >= bottom.values).all()


def test_the_last_rebalance_moves_are_listed_for_every_book_that_traded(connection):
    result = run(connection, "14_mouvements_du_dernier_reequilibrage.sql")
    assert set(result["strategy"]) <= set(BOOKS)
    assert not result.empty


def test_limits_hold_at_every_decision_month(connection):
    result = run(connection, "16_depassements_de_plafond.sql")
    assert set(result["strategy"]) == set(BOOKS)
    assert (result["mois_au_dessus_aux_decisions"] == 0).all()


def test_a_broken_weight_is_caught_by_the_sum_control():
    handle = sqlite3.connect(":memory:")
    load_book_tables(handle)
    handle.execute(
        "UPDATE book_weights SET weight = weight + 0.01 "
        "WHERE rowid = (SELECT MIN(rowid) FROM book_weights)"
    )
    broken = run(handle, "12_controle_somme_des_poids.sql")
    handle.close()
    assert len(broken) == 1
