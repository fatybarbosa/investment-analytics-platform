"""
The number check must catch a false number in an automated comment.

Each test works on text in memory. No pipeline file and no deliverable
is written. The clean comments must pass: if they did not, a failure
on the falsified ones would prove nothing.
"""

from __future__ import annotations

import hashlib
import re
import sys
import warnings
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore", category=UserWarning)

from src.reporting.commentary import (
    PERFORMANCE,
    all_statements,
    build_statements,
    perf,
    render_markdown,
)
from src.reporting.number_check import (
    AUTO_LABEL,
    Draft,
    NumberCheckError,
    Statement,
    check_document,
    check_statements,
    french,
    resolve,
    tokenize,
)


GENERATED = "test"


@pytest.fixture(scope="module")
def production_digest():
    return hashlib.sha256((ROOT / PERFORMANCE).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def sections(production_digest):
    return build_statements()


@pytest.fixture(scope="module")
def return_sentence(sections):
    """The automated sentence that prints the annualized returns."""
    printed = french(float(resolve(perf("equal_weight", "annualized_return"))) * 100, 2)
    for statement in sections["faits"]:
        if printed in statement.text:
            return statement, printed
    raise RuntimeError("The comment on annualized returns was not generated.")


def _falsify(printed):
    """Same format, last digit changed: the smallest false number one can type."""
    last = printed[-1]
    return printed[:-1] + ("0" if last != "0" else "1")


def test_clean_comments_pass(sections):
    statements = all_statements(sections)
    rows = check_statements(statements)
    assert len(statements) >= 10
    assert len(rows) >= 50
    assert all(row["source"] for row in rows)


def test_clean_document_passes(sections):
    text = render_markdown(sections, GENERATED)
    rows = check_document(text, all_statements(sections), where="markdown")
    assert rows


def test_false_number_in_a_comment_is_detected(return_sentence):
    statement, printed = return_sentence
    false = _falsify(printed)
    assert false != printed
    tampered = replace(statement, text=statement.text.replace(printed, false, 1))
    with pytest.raises(NumberCheckError) as caught:
        tampered.check()
    assert false in str(caught.value)


def test_false_number_in_the_written_file_is_detected(sections, return_sentence):
    _, printed = return_sentence
    false = _falsify(printed)
    text = render_markdown(sections, GENERATED).replace(printed, false, 1)
    with pytest.raises(NumberCheckError) as caught:
        check_document(text, all_statements(sections), where="markdown")
    assert false in str(caught.value)


def test_added_number_with_no_source_is_detected(sections):
    text = render_markdown(sections, GENERATED) + "\nLe rendement attendu est de 12,34 % par an.\n"
    with pytest.raises(NumberCheckError, match="12,34"):
        check_document(text, all_statements(sections), where="markdown")


def test_percent_of_the_wrong_scale_is_detected():
    """0,05 printed as a percentage is not the 5,29 % of the file."""
    item = perf("equal_weight", "annualized_return")
    value = float(resolve(item))
    wrong = Statement("test", f"Le rendement est de {french(value, 2)} %.", (item,))
    with pytest.raises(NumberCheckError):
        wrong.check()


def test_number_without_any_fact_is_detected():
    with pytest.raises(NumberCheckError):
        Statement("test", "Le portefeuille compte 31 titres.").check()


def test_missing_label_is_detected(sections):
    text = render_markdown(sections, GENERATED).replace(AUTO_LABEL, "")
    with pytest.raises(NumberCheckError, match="mention"):
        check_document(text, all_statements(sections), where="markdown")


def test_empty_file_value_cannot_be_cited():
    """The fund has no information ratio. A sentence cannot print one."""
    draft = Draft()
    with pytest.raises(NumberCheckError):
        draft.num(perf("benchmark", "information_ratio", "raw"))


def test_tokenizer_reads_french_numbers():
    tokens = tokenize("De 2016-11 à 2026-10 : -26,44 %, 661 586 lignes, tolérance 1e-8, DS-003 et CLIENT001.")
    assert [token.text for token in tokens if token.kind == "month"] == ["2016-11", "2026-10"]
    values = [token.value for token in tokens if token.kind == "number"]
    assert values == [-26.44, 661586.0]
    assert [token.value for token in tokens if token.kind == "scientific"] == [1e-8]
    assert not re.search(r"003|001", " ".join(token.text for token in tokens))


def test_two_numbers_swapped_inside_a_sentence_are_detected(sections, return_sentence):
    """Each swapped number is still a declared fact. Only the sentence itself catches the swap."""
    statement, first = return_sentence
    second = french(float(resolve(perf("minimum_volatility", "annualized_return"))) * 100, 2)
    assert first != second
    swapped = statement.text.replace(first, "@@", 1).replace(second, first, 1).replace("@@", second, 1)
    assert swapped != statement.text
    text = render_markdown(sections, GENERATED).replace(statement.text, swapped, 1)
    # The numbers alone pass: both values are facts of the same document.
    check_document(text, all_statements(sections), where="markdown", integrity=False)
    with pytest.raises(NumberCheckError, match="plus celles qui ont été vérifiées"):
        check_document(text, all_statements(sections), where="markdown")


def test_a_deleted_sentence_is_detected(sections):
    statement = sections["alertes"][0]
    text = render_markdown(sections, GENERATED).replace(statement.text, "", 1)
    with pytest.raises(NumberCheckError, match="plus celles qui ont été vérifiées"):
        check_document(text, all_statements(sections), where="markdown")


def test_pipeline_step_stops_on_a_false_number(sections, return_sentence, tmp_path, monkeypatch):
    """The step called by src.pipeline.refresh raises when the written comment is false.

    The step is redirected to a temporary folder, and the writer is replaced
    by one that types a false number. Nothing is written in reports/.
    """
    import src.reporting.build_executive as step

    _, printed = return_sentence
    false = _falsify(printed)
    target = tmp_path / "commentaires_automatises.md"

    def tampered_writer(built, generated):
        target.write_text(render_markdown(built, generated).replace(printed, false, 1), encoding="utf-8")
        return target, tmp_path / "commentaires_automatises.json"

    monkeypatch.setattr(step, "write_commentary", tampered_writer)
    monkeypatch.setattr(step, "COMMENT_MD", target)
    monkeypatch.setattr(step, "EXECUTIVE_REPORTS", tmp_path)
    monkeypatch.setattr(step, "AUDIT_FILE", tmp_path / "controle_des_nombres.csv")
    with pytest.raises(NumberCheckError) as caught:
        step.build_executive()
    assert false in str(caught.value)
    assert not (tmp_path / "rapport_executif.pdf").exists()


def test_production_file_is_unchanged(production_digest):
    digest = hashlib.sha256((ROOT / PERFORMANCE).read_bytes()).hexdigest()
    assert digest == production_digest
