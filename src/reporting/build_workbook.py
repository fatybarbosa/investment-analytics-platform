"""
Phase 10b. Excel annex.

The workbook recalculates the published indicators from the monthly
returns. It does not read portfolio_metrics, performance_metrics,
risk_by_strategy or stress_results inside those formulas. Those files
appear only on the reconciliation sheet.

Most Power BI measures return the published cell with SELECTEDVALUE or
MAX. Two of them recompute their indicator in DAX from the monthly
returns: the chained return and the maximum drawdown. The Excel formulas
follow the Python definitions, not the DAX.

The tolerance is the pipeline agreement, written on Parametres before
any comparison. A later step must not change it to force a pass.
"""

from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

from src.config import (
    CURRENCY_WEIGHT_CAP,
    DATA_CONTROL_CENTER_FILE,
    EXCEL_REPORTS,
    IPS_SECTOR_WEIGHT_CAP,
    ISSUER_WEIGHT_CAP,
    MARKET_SHOCK_RETURN,
    MAX_POSITIONS,
    MIN_POSITIONS,
    MONTHS_PER_YEAR,
    PROJECT_ROOT,
    RATE_SHOCK_ANNUAL_POINTS,
    RECESSION_SHOCK_MONTHS,
    RECESSION_SHOCK_RETURN,
    SECTOR_WEIGHT_CAP,
    VOLATILITY_SHOCK_MULTIPLIER,
    ZONE_WEIGHT_CAP,
)
from src.performance.build_performance import (
    BENCHMARK_RETURNS_FILE,
    METRICS_OUTPUT as PERFORMANCE_METRICS_FILE,
)
from src.portfolio_construction.build_portfolios import (
    METRICS_FILE,
    MONTHLY_RETURNS_FILE,
    STRATEGY_IDS,
    WEIGHTS_FILE,
)
from src.portfolio_monitoring.build_monitoring import (
    CONCENTRATION_HISTORY_FILE,
    CONTRIBUTION_FILE,
    CONTRIBUTION_TOLERANCE,
    EXPOSURE_FILE,
    HOLDINGS_FILE,
    LIMIT_FILE,
    PATH_FILE,
    REPORT_FILE,
    SECTOR_FILE,
    TOP10_FILE,
    TURNOVER_FILE,
    ZONE_FILE,
)
from src.preparation.quality_treatment import SARON_TREATED
from src.risk.build_risk import AGREEMENT as RISK_AGREEMENT
from src.risk.build_risk import MATRIX_FILE, METRICS_OUTPUT as RISK_METRICS_FILE, TAIL_FILE, VAR_LEVEL
from src.stress_testing.build_stress import AGREEMENT as STRESS_AGREEMENT
from src.stress_testing.build_stress import RESULTS_FILE, SHOCK_IDS
from src.reporting.power_bi_export import COMPUTED_IN_DAX, EXPORT_FILE, NO_ANSWER, NOT_EXPORTED, read_export
from src.utils.logger import logger


# The Power Query drafts carry this token instead of the folder of the machine that wrote them.
# The PowerShell step that loads them into Excel replaces it with the real project folder.
PROJECT_TOKEN = "{{ProjectRoot}}"
WORKBOOK_FILE = EXCEL_REPORTS / "annexe_reporting.xlsx"
EXPLANATIONS_FILE = EXCEL_REPORTS / "EXPLICATIONS.md"
EXPECTED_FILE = EXCEL_REPORTS / "expected_values.csv"
QUERY_DIR = EXCEL_REPORTS / "power_query"
BOOKS = tuple(STRATEGY_IDS)
SERIES = BOOKS + ("benchmark",)
SERIES_LABELS = {
    "equal_weight": "Équipondéré",
    "minimum_volatility": "Volatilité minimale",
    "maximum_sharpe": "Sharpe maximal",
    "benchmark": "iShares, rendement de la valeur liquidative en CHF",
}
FIELDS = (
    "return",
    "rf",
    "excess",
    "active",
    "wealth",
    "peak",
    "dd",
    "shortfall",
    "rank",
)
HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(color="FFFFFF", bold=True, name="Calibri")
TITLE_FONT = Font(bold=True, size=16, name="Calibri", color="1F4E79")
LABEL_FONT = Font(bold=True, name="Calibri")
ILLUSTRATIVE = Font(italic=True, color="9C5700", name="Calibri")


def _tolerances_agree():
    if not (CONTRIBUTION_TOLERANCE == RISK_AGREEMENT == STRESS_AGREEMENT):
        raise RuntimeError(
            "The pipeline agreements differ "
            f"({CONTRIBUTION_TOLERANCE}, {RISK_AGREEMENT}, {STRESS_AGREEMENT}). "
            "The workbook will not choose one."
        )
    return float(CONTRIBUTION_TOLERANCE)


def _clean(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    return value


def _write_frame(worksheet, frame, table_name, header_row=3):
    headers = [str(column) for column in frame.columns]
    worksheet.cell(header_row, 1)
    for column, header in enumerate(headers, 1):
        cell = worksheet.cell(header_row, column, header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    for row_offset, record in enumerate(frame.itertuples(index=False), 1):
        for column, value in enumerate(record, 1):
            worksheet.cell(header_row + row_offset, column, _clean(value))
    last_row = header_row + len(frame)
    last_column = get_column_letter(len(headers))
    table = Table(displayName=table_name, ref=f"A{header_row}:{last_column}{last_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    worksheet.add_table(table)
    worksheet.freeze_panes = f"A{header_row + 1}"
    for column, header in enumerate(headers, 1):
        worksheet.column_dimensions[get_column_letter(column)].width = max(14, min(36, len(header) + 2))
    return header_row, last_row


def _title(worksheet, text, note=None):
    worksheet["A1"] = text
    worksheet["A1"].font = TITLE_FONT
    if note:
        worksheet["A2"] = note
        worksheet["A2"].alignment = Alignment(wrap_text=True)
    worksheet.row_dimensions[1].height = 22
    worksheet.sheet_view.showGridLines = False


def _name(workbook, name, reference):
    workbook.defined_names.add(DefinedName(name=name, attr_text=reference))


def _series_column(series_index, field):
    return 2 + series_index * len(FIELDS) + FIELDS.index(field)


def _load_inputs():
    tolerance = _tolerances_agree()
    returns = pd.read_csv(MONTHLY_RETURNS_FILE)
    benchmark = pd.read_csv(BENCHMARK_RETURNS_FILE)
    saron = pd.read_csv(SARON_TREATED)
    metrics = pd.read_csv(METRICS_FILE)
    performance = pd.read_csv(PERFORMANCE_METRICS_FILE)
    risk = pd.read_csv(RISK_METRICS_FILE)
    stress = pd.read_csv(RESULTS_FILE)
    path = pd.read_csv(PATH_FILE)
    weights = pd.read_csv(WEIGHTS_FILE)
    sectors = pd.read_csv(SECTOR_FILE)
    zones = pd.read_csv(ZONE_FILE)
    currencies = pd.read_csv(EXPOSURE_FILE)
    holdings = pd.read_csv(HOLDINGS_FILE)
    limits = pd.read_csv(LIMIT_FILE)
    contributions = pd.read_csv(CONTRIBUTION_FILE)
    top10 = pd.read_csv(TOP10_FILE)
    matrix = pd.read_csv(MATRIX_FILE)
    history = pd.read_csv(CONCENTRATION_HISTORY_FILE)
    turnover = pd.read_csv(TURNOVER_FILE)
    report = pd.read_csv(REPORT_FILE)
    tail = pd.read_csv(TAIL_FILE)
    months = sorted(returns.loc[returns["strategy"].eq(BOOKS[0]), "month"].astype(str))
    if list(benchmark["month"].astype(str)) != months:
        raise RuntimeError("The fund months are not the portfolio months.")
    for strategy in BOOKS:
        book_months = sorted(returns.loc[returns["strategy"].eq(strategy), "month"].astype(str))
        if book_months != months:
            raise RuntimeError(f"{strategy} does not share the scored months.")
    quality = _quality_frames()
    loaded = {
        "tolerance": tolerance,
        "returns": returns,
        "benchmark": benchmark,
        "saron": saron,
        "metrics": metrics,
        "performance": performance,
        "risk": risk,
        "stress": stress,
        "path": path,
        "weights": weights,
        "sectors": sectors,
        "zones": zones,
        "currencies": currencies,
        "holdings": holdings,
        "limits": limits,
        "contributions": contributions,
        "top10": top10,
        "matrix": matrix,
        "history": history,
        "turnover": turnover,
        "report": report,
        "tail": tail,
        "months": months,
        "quality": quality,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    loaded["expected"] = _expected_frame(loaded)
    loaded["cross"] = _cross_source(loaded)
    return loaded


def _expected_frame(inputs):
    """Pipeline values the Power BI column may later be checked against."""
    period = f"{inputs['months'][0]} → {inputs['months'][-1]}"
    performance = inputs["performance"].set_index("strategy")
    metrics = inputs["metrics"].set_index("strategy")
    risk = inputs["risk"].set_index("strategy")
    last = inputs["months"][-1]
    rows = []

    def add(mesure, livre, value):
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return
        rows.append(
            {
                "mesure": mesure,
                "livre": str(livre),
                "periode": period,
                "valeur_attendue": float(value),
            }
        )

    path = inputs["path"]
    for strategy in BOOKS:
        wealth_rows = path.loc[
            path["strategy"].astype(str).eq(strategy) & path["month"].astype(str).eq(last),
            "cumulative_wealth",
        ]
        wealth = float(wealth_rows.iloc[0])
        add("richesse_finale", strategy, wealth)
        add("rendement_chaine", strategy, wealth - 1)
        add("rendement_annualise", strategy, metrics.loc[strategy, "annualized_return"])
        add("volatilite_annualisee", strategy, metrics.loc[strategy, "annualized_volatility"])
        add("sharpe", strategy, metrics.loc[strategy, "sharpe_ratio"])
        add("sortino", strategy, performance.loc[strategy, "sortino_ratio"])
        add("drawdown_maximal", strategy, metrics.loc[strategy, "maximum_drawdown"])
        add("ecart_de_suivi", strategy, performance.loc[strategy, "tracking_error"])
        add("ratio_information", strategy, performance.loc[strategy, "information_ratio"])
        add("var_historique", strategy, risk.loc[strategy, "var_95"])
        add("expected_shortfall", strategy, risk.loc[strategy, "expected_shortfall_95"])
    for mesure, column in (
        ("rendement_annualise", "annualized_return"),
        ("volatilite_annualisee", "annualized_volatility"),
        ("sharpe", "sharpe_ratio"),
        ("sortino", "sortino_ratio"),
        ("drawdown_maximal", "maximum_drawdown"),
        ("ecart_de_suivi", "tracking_error"),
    ):
        add(mesure, "benchmark", performance.loc["benchmark", column])
    add("var_historique", "benchmark", risk.loc["benchmark", "var_95"])
    add("expected_shortfall", "benchmark", risk.loc["benchmark", "expected_shortfall_95"])
    stress_map = {
        "stress_richesse_finale": "terminal_wealth",
        "stress_drawdown_maximal": "maximum_drawdown",
        "stress_volatilite_annualisee": "annualized_volatility",
        "stress_sharpe": "sharpe_ratio",
    }
    for record in inputs["stress"].itertuples(index=False):
        livre = f"{record.strategy} / {record.shock}"
        for mesure, column in stress_map.items():
            add(mesure, livre, getattr(record, column))
    return pd.DataFrame(rows, columns=["mesure", "livre", "periode", "valeur_attendue"])


def _cross_source(inputs):
    """One cache for the three pivots, so one slicer can drive all of them."""
    last = inputs["months"][-1]
    rows = []
    for record in inputs["returns"].itertuples(index=False):
        rows.append(
            {
                "famille": "rendement",
                "strategy": str(record.strategy),
                "periode": str(record.month),
                "libelle": "portefeuille",
                "mesure": "portfolio_return",
                "valeur": float(record.portfolio_return),
            }
        )
    for record in inputs["benchmark"].itertuples(index=False):
        rows.append(
            {
                "famille": "rendement",
                "strategy": "benchmark",
                "periode": str(record.month),
                "libelle": "fonds",
                "mesure": "benchmark_return_chf",
                "valeur": float(record.benchmark_return_chf),
            }
        )
    for record in inputs["sectors"].itertuples(index=False):
        rows.append(
            {
                "famille": "poids",
                "strategy": str(record.strategy),
                "periode": last,
                "libelle": str(record.sector),
                "mesure": "poids",
                "valeur": float(record.weight),
            }
        )
    for record in inputs["contributions"].itertuples(index=False):
        rows.append(
            {
                "famille": "contribution",
                "strategy": str(record.strategy),
                "periode": str(record.month),
                "libelle": str(record.sector),
                "mesure": "contribution_mensuelle",
                "valeur": float(record.month_contribution),
            }
        )
    stress_measures = (
        ("terminal_wealth", "richesse_finale"),
        ("maximum_drawdown", "drawdown_maximal"),
        ("annualized_volatility", "volatilite"),
        ("sharpe_ratio", "sharpe"),
    )
    for record in inputs["stress"].itertuples(index=False):
        for column, label in stress_measures:
            rows.append(
                {
                    "famille": "stress",
                    "strategy": str(record.strategy),
                    "periode": str(record.window_end),
                    "libelle": str(record.shock),
                    "mesure": label,
                    "valeur": float(getattr(record, column)),
                }
            )
    return pd.DataFrame(rows, columns=["famille", "strategy", "periode", "libelle", "mesure", "valeur"])


def _quality_frames():
    if not DATA_CONTROL_CENTER_FILE.exists():
        raise RuntimeError(f"Quality workbook missing: {DATA_CONTROL_CENTER_FILE}")
    controls = pd.read_excel(DATA_CONTROL_CENTER_FILE, sheet_name="Quality Controls")
    issues = pd.read_excel(DATA_CONTROL_CENTER_FILE, sheet_name="Quality Issues")
    history = pd.read_excel(DATA_CONTROL_CENTER_FILE, sheet_name="Quality History")
    return {"controls": controls, "issues": issues, "history": history}


def _parameters(workbook, inputs):
    worksheet = workbook.active
    worksheet.title = "Parametres"
    _title(worksheet, "Paramètres du classeur")
    worksheet["A2"] = (
        "Ces cellules sont des paramètres de méthode ou la tolérance de réconciliation. "
        "Ce ne sont pas des résultats mesurés. La tolérance est écrite avant la comparaison."
    )
    rows = [
        (3, "Tolerance", inputs["tolerance"], "0.00E+00", "Écart absolu accepté, égal à l'agreement du pipeline."),
        (4, "MoisParAn", MONTHS_PER_YEAR, "0", "Annualisation mensuelle. Pas 252."),
        (5, "NiveauVaR", VAR_LEVEL, "0%", "Part de la queue historique."),
        (6, "ChocMarche", MARKET_SHOCK_RETURN, "0%", "Remplace le dernier mois. Paramètre, pas un résultat."),
        (7, "ChocTauxPoints", RATE_SHOCK_ANNUAL_POINTS, "0.0", "Points ajoutés au SARON annuel."),
        (8, "ChocRecession", RECESSION_SHOCK_RETURN, "0%", "Rendement de remplacement."),
        (9, "ChocRecessionMois", RECESSION_SHOCK_MONTHS, "0", "Nombre de derniers mois remplacés."),
        (10, "ChocVol", VOLATILITY_SHOCK_MULTIPLIER, "0.0", "Multiplie l'écart à la moyenne."),
        (11, "PlafondEmetteur", ISSUER_WEIGHT_CAP, "0%", "Plafond IPS par ligne."),
        (12, "PlafondSecteur", SECTOR_WEIGHT_CAP, "0%", "Plafond de TRAVAIL par secteur, utilisé pour construire les livres. Non approuvé par le client."),
        (13, "PlafondZone", ZONE_WEIGHT_CAP, "0%", "Plafond IPS par zone."),
        (14, "PlafondDevise", CURRENCY_WEIGHT_CAP, "0%", "Plafond IPS par devise de cotation."),
        (15, "PlancherLignes", MIN_POSITIONS, "0", "Plancher de lignes des livres optimisés."),
        (16, "PlafondLignes", MAX_POSITIONS, "0", "Plafond de lignes des livres optimisés."),
        (17, "PlafondSecteurIPS", IPS_SECTOR_WEIGHT_CAP, "0%", "Plafond par secteur ÉCRIT dans l'IPS. Non satisfaisable sur cette liste : voir mandate_feasibility.csv."),
    ]
    for row, name, value, number_format, gloss in rows:
        worksheet.cell(row, 1, name).font = LABEL_FONT
        cell = worksheet.cell(row, 2, value)
        cell.number_format = number_format
        worksheet.cell(row, 3, gloss)
        _name(workbook, name, f"Parametres!$B${row}")
    worksheet["A18"] = "Livre affiché"
    worksheet["A18"].font = LABEL_FONT
    worksheet["B18"] = BOOKS[0]
    _name(workbook, "LivreChoisi", "Parametres!$B$18")
    worksheet["A19"] = "Titre affiché"
    worksheet["A19"].font = LABEL_FONT
    tickers = sorted(inputs["holdings"]["ticker"].astype(str).unique())
    worksheet["B19"] = tickers[0]
    _name(workbook, "TitreChoisi", "Parametres!$B$19")
    for index, strategy in enumerate(BOOKS):
        worksheet.cell(40 + index, 2, strategy)
        worksheet.cell(40 + index, 3, SERIES_LABELS[strategy])
    validation = DataValidation(type="list", formula1="Parametres!$B$40:$B$42", allow_blank=False)
    validation.add(worksheet["B18"])
    worksheet.add_data_validation(validation)
    for index, ticker in enumerate(tickers):
        worksheet.cell(40 + index, 5, ticker)
    ticker_validation = DataValidation(
        type="list",
        formula1=f"Parametres!$E$40:$E${39 + len(tickers)}",
        allow_blank=False,
    )
    ticker_validation.add(worksheet["B19"])
    worksheet.add_data_validation(ticker_validation)
    worksheet.column_dimensions["A"].width = 24
    worksheet.column_dimensions["B"].width = 22
    worksheet.column_dimensions["C"].width = 78
    worksheet.column_dimensions["E"].width = 16


def _data_sheets(workbook, inputs):
    sheets = [
        ("Donnees_Rendements", "Requête Rendements. Recalcul lit cette table. Actualiser tout la recharge.", "Rendements", inputs["returns"]),
        ("Donnees_Benchmark", "Requête Benchmark. Recalcul lit cette table. Actualiser tout la recharge.", "Benchmark", inputs["benchmark"]),
        ("Donnees_Saron", "SARON annuel publié par la BNS, en pourcentage. Sert au choc de taux.", "Saron", inputs["saron"]),
        ("Donnees_Chemin", "Richesse publiée. Lue seulement par la réconciliation.", "Chemin", inputs["path"]),
        ("Donnees_Metriques", "Indicateurs de la phase 5. Lus seulement par la réconciliation.", "Metriques", inputs["metrics"]),
        ("Donnees_Performance", "Indicateurs de la phase 7. Lus seulement par la réconciliation.", "PerformancePubliee", inputs["performance"]),
        ("Donnees_Risque", "VaR et expected shortfall publiés. Lus seulement par la réconciliation.", "RisquePublie", inputs["risk"]),
        ("Donnees_Stress", "Requête StressPublie. La réconciliation et SourcesCroisees lisent cette requête.", "StressPublie", inputs["stress"]),
        ("Donnees_Poids", "Poids mensuels publiés.", "Poids", inputs["weights"]),
        ("Donnees_Secteurs", "Requête Secteurs. La vue d'ensemble et SourcesCroisees lisent cette requête.", "Secteurs", inputs["sectors"]),
        ("Donnees_Zones", "Requête Zones. La vue d'ensemble lit cette table.", "Zones", inputs["zones"]),
        ("Donnees_Devises", "Requête Devises. La vue d'ensemble lit cette table.", "Devises", inputs["currencies"]),
        ("Donnees_Positions", "Requête Positions, avec le rang et les clés. La vue d'ensemble lit cette table.", "Positions", inputs["holdings"]),
        ("Donnees_Limites", "Suivi mensuel des plafonds.", "Limites", inputs["limits"]),
        ("Donnees_Contributions", "Requête Contributions. Les contrôles et SourcesCroisees lisent cette requête.", "Contributions", inputs["contributions"]),
        ("Donnees_Top10", "Dix premières lignes publiées du dernier mois.", "Classement", inputs["top10"]),
        ("Donnees_Effectif", "Nombre effectif de titres, chaque mois.", "Effectif", inputs["history"]),
        ("Donnees_Rotation", "Rotation brute des trimestres de rebalancement.", "Rotation", inputs["turnover"]),
        ("Donnees_Rapport", "Situation du mois du rapport.", "RapportMois", inputs["report"]),
        ("Donnees_Queue", "Mois de la queue historique publiée.", "QueueMois", inputs["tail"]),
        ("Donnees_Correlation", "Corrélation de Pearson publiée par la phase 8. Non recalculée ici.", "Correlation", inputs["matrix"]),
        ("Donnees_Controles", "Contrôles réels du journal de qualité. Aucun contrôle ajouté.", "ControlesQualite", inputs["quality"]["controls"]),
        ("Donnees_Anomalies", "Anomalies réelles du journal de qualité.", "AnomaliesQualite", inputs["quality"]["issues"]),
        ("Donnees_Historique", "Historique réel des passages de qualité.", "HistoriqueQualite", inputs["quality"]["history"]),
        ("Donnees_Attendus", "Valeurs attendues du pipeline pour la colonne Power BI. Ce n'est pas un export Desktop.", "Attendus", inputs["expected"]),
        ("Donnees_Croise", "Requête SourcesCroisees. Elle référence Rendements, Benchmark, Secteurs, Contributions et StressPublie. Elle ne relit pas les fichiers.", "SourcesCroisees", inputs["cross"]),
    ]
    for title, note, table_name, frame in sheets:
        worksheet = workbook.create_sheet(title)
        _title(worksheet, title.replace("_", " "), note)
        _write_frame(worksheet, frame, table_name)
    _position_keys(workbook["Donnees_Positions"], inputs["holdings"])


def _position_keys(worksheet, holdings):
    header_row = 3
    first = header_row + 1
    last = header_row + len(holdings)
    rank_column = holdings.shape[1] + 1
    key_column = rank_column + 1
    title_column = key_column + 1
    worksheet.cell(header_row, rank_column, "rang").fill = HEADER_FILL
    worksheet.cell(header_row, rank_column).font = HEADER_FONT
    worksheet.cell(header_row, key_column, "cle_rang").fill = HEADER_FILL
    worksheet.cell(header_row, key_column).font = HEADER_FONT
    worksheet.cell(header_row, title_column, "cle_titre").fill = HEADER_FILL
    worksheet.cell(header_row, title_column).font = HEADER_FONT
    strategy_letter = "A"
    ticker_letter = "C"
    weight_letter = "F"
    for row in range(first, last + 1):
        worksheet.cell(
            row,
            rank_column,
            (
                f'=SUMPRODUCT((${strategy_letter}${first}:${strategy_letter}${last}={strategy_letter}{row})'
                f'*(${weight_letter}${first}:${weight_letter}${last}>{weight_letter}{row}))'
                f'+SUMPRODUCT((${strategy_letter}${first}:${strategy_letter}${last}={strategy_letter}{row})'
                f'*(${weight_letter}${first}:${weight_letter}${last}={weight_letter}{row})'
                f'*(${ticker_letter}${first}:${ticker_letter}${last}<={ticker_letter}{row}))'
            ),
        )
        worksheet.cell(row, key_column, f"={strategy_letter}{row}&\"|\"&{get_column_letter(rank_column)}{row}")
        worksheet.cell(row, title_column, f"={strategy_letter}{row}&\"|\"&{ticker_letter}{row}")
    table = worksheet.tables["Positions"]
    table.ref = f"A{header_row}:{get_column_letter(title_column)}{last}"


def _recalcul(workbook, inputs):
    worksheet = workbook.create_sheet("Recalcul")
    _title(
        worksheet,
        "Recalcul à partir des rendements mensuels",
        "Aucune formule de cette feuille ne lit Metriques, PerformancePubliee, RisquePublie ou StressPublie.",
    )
    months = inputs["months"]
    start = 20
    end = start + len(months) - 1
    worksheet.cell(19, 1, "month").font = LABEL_FONT
    for series_index, series in enumerate(SERIES):
        for field_index, field in enumerate(FIELDS):
            column = _series_column(series_index, field)
            worksheet.cell(18, column, series).font = LABEL_FONT
            worksheet.cell(19, column, field).font = LABEL_FONT
    benchmark_return = get_column_letter(_series_column(3, "return"))
    for offset, month in enumerate(months):
        row = start + offset
        worksheet.cell(row, 1, month)
        for series_index, series in enumerate(SERIES):
            return_column = _series_column(series_index, "return")
            letter = get_column_letter(return_column)
            if series == "benchmark":
                formula = (
                    f'=IF(COUNTIFS(Benchmark[month],A{row})<>1,NA(),'
                    f'SUMIFS(Benchmark[benchmark_return_chf],Benchmark[month],A{row}))'
                )
            else:
                formula = (
                    f'=IF(COUNTIFS(Rendements[strategy],{letter}$18,Rendements[month],A{row})<>1,NA(),'
                    f'SUMIFS(Rendements[portfolio_return],Rendements[strategy],{letter}$18,Rendements[month],A{row}))'
                )
            worksheet.cell(row, return_column, formula)
            rf_column = _series_column(series_index, "rf")
            worksheet.cell(
                row,
                rf_column,
                (
                    f'=IF(COUNTIFS(Rendements[strategy],"{BOOKS[0]}",Rendements[month],A{row})<>1,NA(),'
                    f'SUMIFS(Rendements[risk_free_return],Rendements[strategy],"{BOOKS[0]}",Rendements[month],A{row}))'
                ),
            )
            excess_column = _series_column(series_index, "excess")
            worksheet.cell(
                row,
                excess_column,
                f"={get_column_letter(return_column)}{row}-{get_column_letter(rf_column)}{row}",
            )
            active_column = _series_column(series_index, "active")
            if series == "benchmark":
                worksheet.cell(row, active_column, f"={letter}{row}-{benchmark_return}{row}")
            else:
                worksheet.cell(
                    row,
                    active_column,
                    f"={get_column_letter(return_column)}{row}-{benchmark_return}{row}",
                )
            wealth_column = _series_column(series_index, "wealth")
            wealth_letter = get_column_letter(wealth_column)
            if offset == 0:
                worksheet.cell(row, wealth_column, f"=1+{letter}{row}")
            else:
                worksheet.cell(row, wealth_column, f"={wealth_letter}{row - 1}*(1+{letter}{row})")
            peak_column = _series_column(series_index, "peak")
            peak_letter = get_column_letter(peak_column)
            if offset == 0:
                worksheet.cell(row, peak_column, f"=MAX(1,{wealth_letter}{row})")
            else:
                worksheet.cell(row, peak_column, f"=MAX({peak_letter}{row - 1},{wealth_letter}{row})")
            worksheet.cell(
                row,
                _series_column(series_index, "dd"),
                f"={wealth_letter}{row}/{peak_letter}{row}-1",
            )
            worksheet.cell(
                row,
                _series_column(series_index, "shortfall"),
                f"=MIN({get_column_letter(excess_column)}{row},0)",
            )
            rank_column = _series_column(series_index, "rank")
            worksheet.cell(
                row,
                rank_column,
                (
                    f'=COUNTIF({letter}${start}:{letter}${end},"<"&{letter}{row})'
                    f'+COUNTIFS({letter}${start}:{letter}${end},{letter}{row},$A${start}:$A${end},"<="&A{row})'
                ),
            )
    _name(workbook, "DebutFenetre", f"Recalcul!$A${start}")
    _name(workbook, "FinFenetre", f"Recalcul!$A${end}")
    _name(workbook, "DernierMois", f"Recalcul!$A${end}")
    recession_row = end - RECESSION_SHOCK_MONTHS + 1
    _name(workbook, "DebutRecession", f"Recalcul!$A${recession_row}")
    summary = end + 3
    worksheet.cell(summary, 1, "Indicateur recalculé").font = TITLE_FONT
    headers = (
        "livre",
        "mois",
        "richesse_finale",
        "rendement_chaine",
        "rendement_annualise",
        "volatilite_annualisee",
        "sharpe",
        "sortino",
        "drawdown_maximal",
        "ecart_de_suivi",
        "ratio_information",
        "var_historique",
        "expected_shortfall",
        "mois_sous_saron",
    )
    for column, header in enumerate(headers, 1):
        cell = worksheet.cell(summary + 1, column, header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    for series_index, series in enumerate(SERIES):
        row = summary + 2 + series_index
        return_letter = get_column_letter(_series_column(series_index, "return"))
        excess_letter = get_column_letter(_series_column(series_index, "excess"))
        wealth_letter = get_column_letter(_series_column(series_index, "wealth"))
        shortfall_letter = get_column_letter(_series_column(series_index, "shortfall"))
        dd_letter = get_column_letter(_series_column(series_index, "dd"))
        rank_letter = get_column_letter(_series_column(series_index, "rank"))
        active_letter = get_column_letter(_series_column(series_index, "active"))
        block = f"{return_letter}${start}:{return_letter}${end}"
        excess = f"{excess_letter}${start}:{excess_letter}${end}"
        worksheet.cell(row, 1, series)
        worksheet.cell(row, 2, f"=COUNT({block})")
        worksheet.cell(row, 3, f"={wealth_letter}{end}")
        worksheet.cell(row, 4, f"=C{row}-1")
        worksheet.cell(row, 5, f"=C{row}^(MoisParAn/B{row})-1")
        worksheet.cell(row, 6, f"=_xlfn.STDEV.S({block})*SQRT(MoisParAn)")
        worksheet.cell(row, 7, f"=AVERAGE({excess})/_xlfn.STDEV.S({excess})*SQRT(MoisParAn)")
        worksheet.cell(
            row,
            8,
            f"=AVERAGE({excess})/SQRT(SUMSQ({shortfall_letter}${start}:{shortfall_letter}${end})/(B{row}-1))*SQRT(MoisParAn)",
        )
        worksheet.cell(row, 9, f"=MIN({dd_letter}${start}:{dd_letter}${end})")
        if series == "benchmark":
            active = f"{active_letter}${start}:{active_letter}${end}"
            worksheet.cell(row, 10, f"=_xlfn.STDEV.S({active})*SQRT(MoisParAn)")
            worksheet.cell(row, 11, None)
        else:
            active = f"{active_letter}${start}:{active_letter}${end}"
            worksheet.cell(row, 10, f"=_xlfn.STDEV.S({active})*SQRT(MoisParAn)")
            worksheet.cell(row, 11, f"=AVERAGE({active})/_xlfn.STDEV.S({active})*SQRT(MoisParAn)")
        k_cut = f"_xlfn.CEILING.MATH(NiveauVaR*B{row},1)"
        rank_block = f"{rank_letter}${start}:{rank_letter}${end}"
        worksheet.cell(row, 12, f'=INDEX({block},MATCH({k_cut},{rank_block},0))')
        worksheet.cell(row, 13, f'=AVERAGEIFS({block},{rank_block},"<="&{k_cut})')
        worksheet.cell(row, 14, f'=COUNTIF({excess},"<0")')
        for column, fmt in ((3, "0.000"), (4, "0.00%"), (5, "0.00%"), (6, "0.00%"), (7, "0.000"), (8, "0.000"), (9, "0.00%"), (10, "0.00%"), (11, "0.000"), (12, "0.00%"), (13, "0.00%")):
            worksheet.cell(row, column).number_format = fmt
    worksheet.column_dimensions["A"].width = 22
    worksheet.freeze_panes = "B20"
    return {"start": start, "end": end, "summary": summary + 2}


def _stress(workbook, inputs, recalcul):
    worksheet = workbook.create_sheet("Stress")
    _title(
        worksheet,
        "Chocs recalculés",
        "Illustratif. Le choc s'applique au rendement mensuel du portefeuille déjà agrégé. "
        "Les poids ne sont pas réestimés. Le choc de taux change le SARON et laisse le rendement du portefeuille inchangé.",
    )
    worksheet["A2"].font = ILLUSTRATIVE
    headers = (
        "strategy",
        "shock",
        "month",
        "base_return",
        "shocked_return",
        "risk_free",
        "excess",
        "wealth",
        "peak",
        "drawdown",
    )
    for column, header in enumerate(headers, 1):
        cell = worksheet.cell(4, column, header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    months = inputs["months"]
    row = 5
    blocks = {}
    for strategy in BOOKS:
        for shock in SHOCK_IDS:
            first = row
            for month_index, month in enumerate(months):
                worksheet.cell(row, 1, strategy)
                worksheet.cell(row, 2, shock)
                worksheet.cell(row, 3, f"=Recalcul!A{recalcul['start'] + month_index}")
                base_column = get_column_letter(_series_column(BOOKS.index(strategy), "return"))
                worksheet.cell(row, 4, f"=Recalcul!{base_column}{recalcul['start'] + month_index}")
                worksheet.cell(
                    row,
                    5,
                    (
                        f'=IF(B{row}="aucun",D{row},'
                        f'IF(B{row}="marche",IF(C{row}=DernierMois,ChocMarche,D{row}),'
                        f'IF(B{row}="taux",D{row},'
                        f'IF(B{row}="recession",IF(C{row}>=DebutRecession,ChocRecession,D{row}),'
                        f'IF(B{row}="volatilite",AVERAGEIF($A$5:$A${4 + len(BOOKS) * len(SHOCK_IDS) * len(months)},A{row},$D$5:$D${4 + len(BOOKS) * len(SHOCK_IDS) * len(months)})'
                        f'+ChocVol*(D{row}-AVERAGEIF($A$5:$A${4 + len(BOOKS) * len(SHOCK_IDS) * len(months)},A{row},$D$5:$D${4 + len(BOOKS) * len(SHOCK_IDS) * len(months)})),NA())))))'
                    ),
                )
                worksheet.cell(
                    row,
                    6,
                    (
                        f'=IF(B{row}="taux",'
                        f'(1+(SUMIFS(Saron[value],Saron[date],C{row})+ChocTauxPoints)/100)^(1/MoisParAn)-1,'
                        f'SUMIFS(Rendements[risk_free_return],Rendements[strategy],A{row},Rendements[month],C{row}))'
                    ),
                )
                worksheet.cell(row, 7, f"=E{row}-F{row}")
                if month_index == 0:
                    worksheet.cell(row, 8, f"=1+E{row}")
                    worksheet.cell(row, 9, f"=MAX(1,H{row})")
                else:
                    worksheet.cell(row, 8, f'=IF(OR(A{row}<>A{row - 1},B{row}<>B{row - 1}),1+E{row},H{row - 1}*(1+E{row}))')
                    worksheet.cell(row, 9, f'=IF(OR(A{row}<>A{row - 1},B{row}<>B{row - 1}),MAX(1,H{row}),MAX(I{row - 1},H{row}))')
                worksheet.cell(row, 10, f"=H{row}/I{row}-1")
                row += 1
            blocks[(strategy, shock)] = (first, row - 1)
    summary = 4
    summary_headers = (
        "strategy",
        "shock",
        "richesse_finale",
        "drawdown_maximal",
        "volatilite_annualisee",
        "sharpe",
    )
    for column, header in enumerate(summary_headers, 12):
        cell = worksheet.cell(summary, column, header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    for index, (strategy, shock) in enumerate(blocks):
        first, last = blocks[(strategy, shock)]
        target = summary + 1 + index
        worksheet.cell(target, 12, f"=A{first}")
        worksheet.cell(target, 13, f"=B{first}")
        worksheet.cell(target, 14, f"=H{last}")
        worksheet.cell(target, 15, f"=MIN(J{first}:J{last})")
        worksheet.cell(target, 16, f"=_xlfn.STDEV.S(E{first}:E{last})*SQRT(MoisParAn)")
        worksheet.cell(target, 17, f"=AVERAGE(G{first}:G{last})/_xlfn.STDEV.S(G{first}:G{last})*SQRT(MoisParAn)")
        for column in (14, 15, 16):
            worksheet.cell(target, column).number_format = "0.00%"
        worksheet.cell(target, 17).number_format = "0.000"
    worksheet.freeze_panes = "A5"
    return {"summary_start": summary + 1, "summary_count": len(blocks)}


def _power_bi_cells(worksheet, row, exported=None, indicator=None, book=None):
    """Expected pipeline value. The status stays pending until a real Desktop export.

    export_power_bi receives only a value read in power_bi_export.csv, which
    the Desktop engine answered. A line the model has no measure for stays empty.
    """
    worksheet.cell(
        row,
        6,
        f'=IF(COUNTIFS(Attendus[mesure],A{row},Attendus[livre],B{row})=0,"",SUMIFS(Attendus[valeur_attendue],Attendus[mesure],A{row},Attendus[livre],B{row}))',
    )
    value = None if exported is None else exported.get((indicator, book))
    worksheet.cell(row, 12, value)
    if indicator == "ratio_information" and book == "benchmark":
        nature = "non publié"
    elif indicator in COMPUTED_IN_DAX:
        nature = "recalcul DAX"
    else:
        nature = "relecture"
    worksheet.cell(row, 15, nature)
    if value is None and not (indicator == "ratio_information" and book == "benchmark"):
        reason = NOT_EXPORTED.get(f"{indicator} / {book}") or NOT_EXPORTED.get(indicator) or NO_ANSWER
        if exported and reason:
            worksheet.cell(row, 14, reason)
    worksheet.cell(
        row,
        13,
        (
            f'=IF(AND(A{row}="ratio_information",B{row}="benchmark"),"non publié",'
            f'IF(L{row}="","en attente d\'export Power BI",'
            f'IF(NOT(ISNUMBER(L{row})),"EXCEPTION",IF(ABS(L{row}-E{row})<=H{row},"OK","EXCEPTION"))))'
        ),
    )


def _reconciliation(workbook, recalcul, stress):
    worksheet = workbook.create_sheet("Reconciliation")
    _title(
        worksheet,
        "Réconciliation",
        "La colonne valeur_power_bi contient la valeur attendue du pipeline (expected_values.csv). "
        "Le statut Power BI reste « en attente d'export Power BI » tant que export_power_bi est vide. "
        "Coller l'export Desktop dans export_power_bi : la formule compare alors cette cellule à Excel. "
        "Un écart Python/Excel sans cause reste ouvert. La tolérance n'est pas une cellule à ajuster après coup.",
    )
    headers = (
        "indicateur",
        "livre",
        "periode",
        "valeur_python",
        "valeur_excel",
        "valeur_power_bi",
        "ecart",
        "tolerance",
        "statut",
        "cause",
        "cloture",
        "export_power_bi",
        "statut_power_bi",
        "cause_power_bi",
        "nature_power_bi",
    )
    exported = read_export()
    for column, header in enumerate(headers, 1):
        cell = worksheet.cell(4, column, header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    published = {
        "richesse_finale": ('SUMIFS(Chemin[cumulative_wealth],Chemin[strategy],B{row},Chemin[month],DernierMois)', 3),
        "rendement_chaine": ('SUMIFS(Chemin[cumulative_wealth],Chemin[strategy],B{row},Chemin[month],DernierMois)-1', 4),
        "rendement_annualise": ('SUMIFS(Metriques[annualized_return],Metriques[strategy],B{row})', 5),
        "volatilite_annualisee": ('SUMIFS(Metriques[annualized_volatility],Metriques[strategy],B{row})', 6),
        "sharpe": ('SUMIFS(Metriques[sharpe_ratio],Metriques[strategy],B{row})', 7),
        "sortino": ('SUMIFS(PerformancePubliee[sortino_ratio],PerformancePubliee[strategy],B{row})', 8),
        "drawdown_maximal": ('SUMIFS(Metriques[maximum_drawdown],Metriques[strategy],B{row})', 9),
        "ecart_de_suivi": ('SUMIFS(PerformancePubliee[tracking_error],PerformancePubliee[strategy],B{row})', 10),
        "ratio_information": ('SUMIFS(PerformancePubliee[information_ratio],PerformancePubliee[strategy],B{row})', 11),
        "var_historique": ('SUMIFS(RisquePublie[var_95],RisquePublie[strategy],B{row})', 12),
        "expected_shortfall": ('SUMIFS(RisquePublie[expected_shortfall_95],RisquePublie[strategy],B{row})', 13),
    }
    row = 5
    for series_index, series in enumerate(BOOKS):
        for indicator, (python_formula, excel_column) in published.items():
            worksheet.cell(row, 1, indicator)
            worksheet.cell(row, 2, series)
            worksheet.cell(row, 3, '=DebutFenetre&" → "&FinFenetre')
            worksheet.cell(row, 4, "=" + python_formula.format(row=row))
            worksheet.cell(row, 5, f"=Recalcul!{get_column_letter(excel_column)}{recalcul['summary'] + series_index}")
            worksheet.cell(row, 7, f'=IF(OR(D{row}="",NOT(ISNUMBER(E{row}))),"",E{row}-D{row})')
            worksheet.cell(row, 8, "=Tolerance")
            worksheet.cell(
                row,
                9,
                f'=IF(D{row}="","non publié",IF(NOT(ISNUMBER(E{row})),"EXCEPTION",IF(ABS(E{row}-D{row})<=H{row},"OK","EXCEPTION")))',
            )
            worksheet.cell(row, 10, None)
            worksheet.cell(
                row,
                11,
                f'=IF(I{row}="OK","clos",IF(I{row}="non publié","clos",IF(J{row}="","ouvert","clos")))',
            )
            _power_bi_cells(worksheet, row, exported, indicator, series)
            row += 1
    benchmark_row = recalcul["summary"] + 3
    benchmark_published = {
        "rendement_annualise": ('SUMIFS(PerformancePubliee[annualized_return],PerformancePubliee[strategy],"benchmark")', 5),
        "volatilite_annualisee": ('SUMIFS(PerformancePubliee[annualized_volatility],PerformancePubliee[strategy],"benchmark")', 6),
        "sharpe": ('SUMIFS(PerformancePubliee[sharpe_ratio],PerformancePubliee[strategy],"benchmark")', 7),
        "sortino": ('SUMIFS(PerformancePubliee[sortino_ratio],PerformancePubliee[strategy],"benchmark")', 8),
        "drawdown_maximal": ('SUMIFS(PerformancePubliee[maximum_drawdown],PerformancePubliee[strategy],"benchmark")', 9),
        "ecart_de_suivi": ('SUMIFS(PerformancePubliee[tracking_error],PerformancePubliee[strategy],"benchmark")', 10),
        "var_historique": ('SUMIFS(RisquePublie[var_95],RisquePublie[strategy],"benchmark")', 12),
        "expected_shortfall": ('SUMIFS(RisquePublie[expected_shortfall_95],RisquePublie[strategy],"benchmark")', 13),
    }
    for indicator, (python_formula, excel_column) in benchmark_published.items():
        worksheet.cell(row, 1, indicator)
        worksheet.cell(row, 2, "benchmark")
        worksheet.cell(row, 3, '=DebutFenetre&" → "&FinFenetre')
        worksheet.cell(row, 4, "=" + python_formula)
        worksheet.cell(row, 5, f"=Recalcul!{get_column_letter(excel_column)}{benchmark_row}")
        worksheet.cell(row, 7, f'=IF(OR(D{row}="",NOT(ISNUMBER(E{row}))),"",E{row}-D{row})')
        worksheet.cell(row, 8, "=Tolerance")
        worksheet.cell(
            row,
            9,
            f'=IF(D{row}="","non publié",IF(NOT(ISNUMBER(E{row})),"EXCEPTION",IF(ABS(E{row}-D{row})<=H{row},"OK","EXCEPTION")))',
        )
        worksheet.cell(row, 10, None)
        worksheet.cell(
            row,
            11,
            f'=IF(I{row}="OK","clos",IF(I{row}="non publié","clos",IF(J{row}="","ouvert","clos")))',
        )
        _power_bi_cells(worksheet, row, exported, indicator, "benchmark")
        row += 1
    worksheet.cell(row, 1, "ratio_information")
    worksheet.cell(row, 2, "benchmark")
    worksheet.cell(row, 3, '=DebutFenetre&" → "&FinFenetre')
    worksheet.cell(row, 8, "=Tolerance")
    worksheet.cell(row, 9, '="non publié"')
    worksheet.cell(row, 10, "Le fonds est la référence. L'écart de suivi est nul, donc le ratio d'information n'est pas défini.")
    worksheet.cell(row, 11, '="clos"')
    _power_bi_cells(worksheet, row, exported, "ratio_information", "benchmark")
    row += 1
    stress_map = {
        "richesse_finale": (14, "terminal_wealth"),
        "drawdown_maximal": (15, "maximum_drawdown"),
        "volatilite_annualisee": (16, "annualized_volatility"),
        "sharpe": (17, "sharpe_ratio"),
    }
    for offset in range(stress["summary_count"]):
        source = stress["summary_start"] + offset
        for indicator, (excel_column, python_column) in stress_map.items():
            worksheet.cell(row, 1, f"stress_{indicator}")
            worksheet.cell(row, 2, f'=Stress!L{source}&" / "&Stress!M{source}')
            worksheet.cell(row, 3, '=DebutFenetre&" → "&FinFenetre')
            worksheet.cell(
                row,
                4,
                (
                    f'=SUMIFS(StressPublie[{python_column}],StressPublie[strategy],Stress!L{source},'
                    f'StressPublie[shock],Stress!M{source})'
                ),
            )
            worksheet.cell(row, 5, f"=Stress!{get_column_letter(excel_column)}{source}")
            worksheet.cell(row, 7, f'=IF(OR(D{row}="",NOT(ISNUMBER(E{row}))),"",E{row}-D{row})')
            worksheet.cell(row, 8, "=Tolerance")
            worksheet.cell(row, 9, f'=IF(D{row}="","non publié",IF(NOT(ISNUMBER(E{row})),"EXCEPTION",IF(ABS(E{row}-D{row})<=H{row},"OK","EXCEPTION")))')
            worksheet.cell(row, 10, None)
            worksheet.cell(row, 11, f'=IF(I{row}="OK","clos",IF(I{row}="non publié","clos",IF(J{row}="","ouvert","clos")))')
            stress_book = f"{BOOKS[offset // len(SHOCK_IDS)]} / {SHOCK_IDS[offset % len(SHOCK_IDS)]}"
            _power_bi_cells(worksheet, row, exported, f"stress_{indicator}", stress_book)
            row += 1
    last = row - 1
    table = Table(displayName="Reconciliation", ref=f"A4:O{last}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    worksheet.add_table(table)
    worksheet.freeze_panes = "A5"
    worksheet.column_dimensions["A"].width = 28
    worksheet.column_dimensions["B"].width = 42
    worksheet.column_dimensions["C"].width = 24
    worksheet.column_dimensions["J"].width = 62
    for column in ("D", "E", "F", "G"):
        worksheet.column_dimensions[column].width = 18
    worksheet.column_dimensions["L"].width = 22
    worksheet.column_dimensions["M"].width = 32
    worksheet.column_dimensions["N"].width = 62
    worksheet.column_dimensions["O"].width = 18
    worksheet.conditional_formatting.add(f"M5:M{last}", CellIsRule(operator="equal", formula=['"EXCEPTION"'], fill=PatternFill("solid", fgColor="F4B183")))
    worksheet.conditional_formatting.add(f"I5:I{last}", CellIsRule(operator="equal", formula=['"EXCEPTION"'], fill=PatternFill("solid", fgColor="F4B183")))
    worksheet.conditional_formatting.add(f"K5:K{last}", CellIsRule(operator="equal", formula=['"ouvert"'], fill=PatternFill("solid", fgColor="FF6B6B")))
    worksheet.conditional_formatting.add(
        f"M5:M{last}",
        CellIsRule(operator="equal", formula=['"en attente d\'export Power BI"'], fill=PatternFill("solid", fgColor="D6DCE4")),
    )
    return last


def _views(workbook, inputs):
    overview = workbook.create_sheet("Vue_ensemble")
    _title(overview, "Vue d'ensemble du livre choisi", "Les poids viennent du dernier mois publié. Les plafonds sont les paramètres IPS.")
    overview["A4"] = "Livre"
    overview["B4"] = "=LivreChoisi"
    overview["A5"] = "Libellé"
    overview["B5"] = '=INDEX(Parametres!C40:C42,MATCH(LivreChoisi,Parametres!B40:B42,0))'
    overview["A7"] = "Secteur"
    overview["B7"] = "Poids"
    sectors = list(inputs["sectors"]["sector"].astype(str).unique())
    for index, sector in enumerate(sectors):
        overview.cell(8 + index, 1, sector)
        overview.cell(8 + index, 2, f'=SUMIFS(Secteurs[weight],Secteurs[strategy],LivreChoisi,Secteurs[sector],A{8 + index})')
        overview.cell(8 + index, 2).number_format = "0.0%"
    overview.conditional_formatting.add(
        f"B8:B{7 + len(sectors)}",
        CellIsRule(operator="greaterThan", formula=["PlafondSecteur"], fill=PatternFill("solid", fgColor="F4B183")),
    )
    overview["D7"] = "Zone"
    overview["E7"] = "Poids"
    zones = list(inputs["zones"]["zone"].astype(str).unique())
    for index, zone in enumerate(zones):
        overview.cell(8 + index, 4, zone)
        overview.cell(8 + index, 5, f'=SUMIFS(Zones[weight],Zones[strategy],LivreChoisi,Zones[zone],D{8 + index})')
        overview.cell(8 + index, 5).number_format = "0.0%"
    overview.conditional_formatting.add(
        f"E8:E{7 + len(zones)}",
        CellIsRule(operator="greaterThan", formula=["PlafondZone"], fill=PatternFill("solid", fgColor="F4B183")),
    )
    overview["G7"] = "Devise de cotation"
    overview["H7"] = "Poids"
    currencies = list(inputs["currencies"]["exposure"].astype(str).unique())
    for index, currency in enumerate(currencies):
        overview.cell(8 + index, 7, currency)
        overview.cell(8 + index, 8, f'=SUMIFS(Devises[weight],Devises[strategy],LivreChoisi,Devises[exposure],G{8 + index})')
        overview.cell(8 + index, 8).number_format = "0.0%"
    overview.conditional_formatting.add(
        f"H8:H{7 + len(currencies)}",
        CellIsRule(operator="greaterThan", formula=["PlafondDevise"], fill=PatternFill("solid", fgColor="F4B183")),
    )
    top_row = 8 + max(len(sectors), len(zones), len(currencies)) + 2
    overview.cell(top_row, 1, "Top 10 du livre choisi").font = TITLE_FONT
    for column, header in enumerate(("rang", "ticker", "nom", "poids", "secteur", "zone", "devise"), 1):
        cell = overview.cell(top_row + 1, column, header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    for rank in range(1, 11):
        row = top_row + 1 + rank
        overview.cell(row, 1, rank)
        key = f'LivreChoisi&"|{rank}"'
        overview.cell(row, 2, f'=INDEX(Positions[ticker],MATCH({key},Positions[cle_rang],0))')
        overview.cell(row, 3, f'=INDEX(Positions[name],MATCH({key},Positions[cle_rang],0))')
        overview.cell(row, 4, f'=INDEX(Positions[weight],MATCH({key},Positions[cle_rang],0))')
        overview.cell(row, 4).number_format = "0.0%"
        overview.cell(row, 5, f'=INDEX(Positions[sector],MATCH({key},Positions[cle_rang],0))')
        overview.cell(row, 6, f'=INDEX(Positions[zone],MATCH({key},Positions[cle_rang],0))')
        overview.cell(row, 7, f'=INDEX(Positions[listing_currency],MATCH({key},Positions[cle_rang],0))')
    overview.cell(top_row, 9, "Top 10 par tableau dynamique FILTER et SORTBY. Pas un tableau croisé dynamique.")
    overview.cell(top_row, 9).font = TITLE_FONT
    overview.cell(
        top_row + 1,
        9,
        '=_xlfn._xlws.SORTBY(_xlfn._xlws.FILTER(Positions[ticker],(Positions[strategy]=LivreChoisi)*(Positions[rang]<=10)),_xlfn._xlws.FILTER(Positions[rang],(Positions[strategy]=LivreChoisi)*(Positions[rang]<=10)),1)',
    )
    overview.column_dimensions["I"].width = 42
    overview.conditional_formatting.add(
        f"D{top_row + 2}:D{top_row + 11}",
        CellIsRule(operator="greaterThan", formula=["PlafondEmetteur"], fill=PatternFill("solid", fgColor="F4B183")),
    )
    card = top_row + 14
    overview.cell(card, 1, "Fiche titre").font = TITLE_FONT
    overview["A" + str(card + 1)] = "Saisir le code dans Parametres, cellule TitreChoisi."
    labels = (
        ("Code", "=TitreChoisi"),
        ("Nom", '=INDEX(Positions[name],MATCH(LivreChoisi&"|"&TitreChoisi,Positions[cle_titre],0))'),
        ("Secteur", '=INDEX(Positions[sector],MATCH(LivreChoisi&"|"&TitreChoisi,Positions[cle_titre],0))'),
        ("Zone", '=INDEX(Positions[zone],MATCH(LivreChoisi&"|"&TitreChoisi,Positions[cle_titre],0))'),
        ("Devise de cotation", '=INDEX(Positions[listing_currency],MATCH(LivreChoisi&"|"&TitreChoisi,Positions[cle_titre],0))'),
        ("Poids", '=INDEX(Positions[weight],MATCH(LivreChoisi&"|"&TitreChoisi,Positions[cle_titre],0))'),
    )
    lookups = (
        ("Nom", "name"),
        ("Secteur", "sector"),
        ("Zone", "zone"),
        ("Devise de cotation", "listing_currency"),
        ("Poids", "weight"),
    )
    for offset, (label, formula) in enumerate(labels):
        overview.cell(card + 3 + offset, 1, label).font = LABEL_FONT
        overview.cell(card + 3 + offset, 2, formula)
    overview.cell(card + 2, 4, "XLOOKUP").font = LABEL_FONT
    for offset, (label, column) in enumerate(lookups):
        overview.cell(
            card + 4 + offset,
            4,
            f'=_xlfn.XLOOKUP(LivreChoisi&"|"&TitreChoisi,Positions[cle_titre],Positions[{column}],"")',
        )
    overview.cell(card + 8, 2).number_format = "0.0%"
    overview.cell(card + 8, 4).number_format = "0.0%"
    overview.column_dimensions["A"].width = 28
    overview.column_dimensions["B"].width = 36
    overview.column_dimensions["C"].width = 28

    performance = workbook.create_sheet("Indicateurs")
    _title(performance, "Indicateurs", "Le tableau lit la feuille Recalcul. La courbe de richesse est sur la feuille Performance.")
    performance["A4"] = "month"
    for column, series in enumerate(SERIES, 2):
        performance.cell(4, column, SERIES_LABELS[series])
    for offset, _month in enumerate(inputs["months"]):
        row = 5 + offset
        performance.cell(row, 1, f"=Recalcul!A{20 + offset}")
        for series_index in range(4):
            letter = get_column_letter(_series_column(series_index, "wealth"))
            performance.cell(row, 2 + series_index, f"=Recalcul!{letter}{20 + offset}")
            performance.cell(row, 2 + series_index).number_format = "0.00"
    table_row = 4
    performance.cell(table_row, 8, "Indicateurs recalculés").font = TITLE_FONT
    for column, header in enumerate(("livre", "rendement annualisé", "volatilité", "Sharpe", "Sortino", "drawdown", "écart de suivi", "ratio d'information"), 8):
        cell = performance.cell(table_row + 1, column, header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    for series_index, series in enumerate(SERIES):
        row = table_row + 2 + series_index
        source = 20 + len(inputs["months"]) - 1 + 3 + 2 + series_index
        performance.cell(row, 8, f"=Recalcul!A{source}")
        for offset, source_column in enumerate((5, 6, 7, 8, 9, 10, 11), 9):
            performance.cell(row, offset, f"=Recalcul!{get_column_letter(source_column)}{source}")
        for column in (9, 10, 13, 14):
            performance.cell(row, column).number_format = "0.00%"
    performance["H12"] = "Contribution sectorielle du dernier mois"
    performance["H12"].font = TITLE_FONT
    performance["H13"] = "Secteur"
    performance["I13"] = "Contribution cumulée publiée"
    for index, sector in enumerate(sectors):
        performance.cell(14 + index, 8, sector)
        performance.cell(
            14 + index,
            9,
            f'=SUMIFS(Contributions[cumulative_contribution],Contributions[strategy],LivreChoisi,Contributions[sector],H{14 + index},Contributions[month],DernierMois)',
        )
        performance.cell(14 + index, 9).number_format = "0.00%"
    performance["H22"] = (
        "La contribution cumulée est la somme des contributions mensuelles poids × rendement. "
        "Ce n'est pas une performance composée."
    )

    risk = workbook.create_sheet("Correlation")
    _title(risk, "Corrélation", "VaR et expected shortfall sont recalculés. La matrice est celle publiée par la phase 8. Les graphiques de queue sont sur la feuille Risque.")
    risk["A4"] = "Livre"
    risk["B4"] = "Volatilité annualisée"
    risk["C4"] = "VaR historique 95 %"
    risk["D4"] = "Expected shortfall 95 %"
    for column in range(1, 5):
        risk.cell(4, column).fill = HEADER_FILL
        risk.cell(4, column).font = HEADER_FONT
    for series_index, series in enumerate(BOOKS):
        source = 20 + len(inputs["months"]) - 1 + 3 + 2 + series_index
        risk.cell(5 + series_index, 1, f"=Recalcul!A{source}")
        risk.cell(5 + series_index, 2, f"=Recalcul!F{source}")
        risk.cell(5 + series_index, 3, f"=Recalcul!L{source}")
        risk.cell(5 + series_index, 4, f"=Recalcul!M{source}")
        risk.cell(5 + series_index, 2).number_format = "0.00%"
        risk.cell(5 + series_index, 3).number_format = "0.00%"
        risk.cell(5 + series_index, 4).number_format = "0.00%"
    risk["A9"] = "La volatilité est annualisée. La VaR et l'expected shortfall sont des rendements mensuels."
    risk["A11"] = "Matrice de corrélation publiée, Pearson, phase 8. Elle n'est pas recalculée dans ce classeur."
    symbols = [str(symbol) for symbol in inputs["matrix"].columns[1:]]
    matrix_last_column = get_column_letter(1 + len(symbols))
    matrix_last_row = 3 + len(symbols)
    risk.cell(13, 1, "symbol")
    for column, symbol in enumerate(symbols, 2):
        risk.cell(13, column, symbol)
        risk.cell(14 + column - 2, 1, symbol)
    for row_index in range(len(symbols)):
        for column_index in range(len(symbols)):
            risk.cell(
                14 + row_index,
                2 + column_index,
                (
                    f"=INDEX(Donnees_Correlation!$B$4:${matrix_last_column}${matrix_last_row},"
                    f"MATCH($A{14 + row_index},Donnees_Correlation!$A$4:$A${matrix_last_row},0),"
                    f"MATCH({get_column_letter(2 + column_index)}$13,Donnees_Correlation!$B$3:${matrix_last_column}$3,0))"
                ),
            )
            risk.cell(14 + row_index, 2 + column_index).number_format = "0%"
    last = 13 + len(symbols)
    risk.conditional_formatting.add(
        f"B14:{matrix_last_column}{last}",
        ColorScaleRule(start_type="num", start_value=-1, start_color="B2182B", mid_type="num", mid_value=0, mid_color="F7F7F7", end_type="num", end_value=1, end_color="2166AC"),
    )

    quality = workbook.create_sheet("Qualite")
    _title(quality, "Qualité des données", "Synthèse du journal réel. Aucun contrôle n'est inventé ici.")
    quality["A4"] = "Score du dernier passage"
    quality["B4"] = "=MAX(HistoriqueQualite[global_quality_score])"
    quality["A5"] = "Note"
    quality["B5"] = '=INDEX(HistoriqueQualite[global_quality_grade],MATCH(B4,HistoriqueQualite[global_quality_score],0))'
    quality["A6"] = "Statut"
    quality["B6"] = '=INDEX(HistoriqueQualite[global_status],MATCH(B4,HistoriqueQualite[global_quality_score],0))'
    quality["A8"] = "Contrôles par statut"
    quality["A9"] = "PASS"
    quality["B9"] = '=COUNTIF(ControlesQualite[status],"PASS")'
    quality["A10"] = "WARNING"
    quality["B10"] = '=COUNTIF(ControlesQualite[status],"WARNING")'
    quality["A11"] = "FAIL"
    quality["B11"] = '=COUNTIF(ControlesQualite[status],"FAIL")'
    quality["A13"] = "Le détail est dans Donnees_Controles, Donnees_Anomalies et Donnees_Historique."


def _controls(workbook, inputs, recalcul):
    worksheet = workbook.create_sheet("Controles")
    _title(
        worksheet,
        "Contrôles de cohérence",
        "La bande de 25 à 40 lignes ne s'applique pas à l'équipondéré. Un mois optimisé hors bande est une ERREUR de mandat déjà suivie, pas un échec de formule.",
    )
    headers = (
        "strategy",
        "month",
        "somme_des_poids",
        "statut_poids",
        "somme_des_contributions",
        "rendement_du_mois",
        "statut_contribution",
        "lignes",
        "statut_bande",
    )
    for column, header in enumerate(headers, 1):
        cell = worksheet.cell(4, column, header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    row = 5
    for strategy in BOOKS:
        for offset, _month in enumerate(inputs["months"]):
            month_cell = f"Recalcul!A{recalcul['start'] + offset}"
            worksheet.cell(row, 1, strategy)
            worksheet.cell(row, 2, f"={month_cell}")
            worksheet.cell(row, 3, f"=SUMIFS(Poids[weight],Poids[strategy],A{row},Poids[month],B{row})")
            worksheet.cell(row, 4, f'=IF(ABS(C{row}-1)<=Tolerance,"OK","ERREUR")')
            worksheet.cell(row, 5, f"=SUMIFS(Contributions[month_contribution],Contributions[strategy],A{row},Contributions[month],B{row})")
            worksheet.cell(row, 6, f"=SUMIFS(Rendements[portfolio_return],Rendements[strategy],A{row},Rendements[month],B{row})")
            worksheet.cell(row, 7, f'=IF(ABS(E{row}-F{row})<=Tolerance,"OK","ERREUR")')
            worksheet.cell(
                row,
                8,
                f'=SUMPRODUCT((Poids[strategy]=A{row})*(Poids[month]=B{row})*(Poids[weight]>Tolerance))',
            )
            if strategy == BOOKS[0]:
                worksheet.cell(row, 9, "non applicable")
            else:
                worksheet.cell(row, 9, f'=IF(OR(H{row}<PlancherLignes,H{row}>PlafondLignes),"ERREUR","OK")')
            worksheet.cell(row, 3).number_format = "0.00%"
            worksheet.cell(row, 5).number_format = "0.00%"
            worksheet.cell(row, 6).number_format = "0.00%"
            row += 1
    last = row - 1
    worksheet["K4"] = "Synthèse des formules"
    worksheet["K4"].font = TITLE_FONT
    worksheet["K5"] = '=IF(AND(COUNTIF(D5:D' + str(last) + ',"ERREUR")=0,COUNTIF(G5:G' + str(last) + ',"ERREUR")=0),"OK","ERREUR")'
    worksheet["L5"] = "Poids et contributions. La bande de lignes n'entre pas dans cette synthèse."
    worksheet["K6"] = f'=COUNTIF(I5:I{last},"ERREUR")'
    worksheet["L6"] = "Mois optimisés hors de la bande 25 à 40. Informatif."
    worksheet["K8"] = "Même source"
    worksheet["K8"].font = TITLE_FONT
    worksheet["K9"] = "=ROWS(Rendements[portfolio_return])+ROWS(Benchmark[benchmark_return_chf])"
    worksheet["L9"] = "Lignes lues par Recalcul : tables Rendements et Benchmark."
    worksheet["K10"] = '=COUNTIFS(SourcesCroisees[famille],"rendement")'
    worksheet["L10"] = "Lignes de rendement dans la source des trois tableaux croisés."
    worksheet["K11"] = "=SUM(Rendements[portfolio_return])+SUM(Benchmark[benchmark_return_chf])"
    worksheet["L11"] = "Somme des rendements lue par les formules."
    worksheet["K12"] = '=SUMIFS(SourcesCroisees[valeur],SourcesCroisees[famille],"rendement")'
    worksheet["L12"] = "Somme des rendements lue par les tableaux croisés."
    worksheet["K13"] = '=IF(AND(K9=K10,ABS(K11-K12)<=Tolerance),"OK","ERREUR")'
    worksheet["L13"] = "OK seulement si le nombre de lignes et la somme coïncident. La tolérance n'est pas ajustée."
    worksheet["K11"].number_format = "0.000000"
    worksheet["K12"].number_format = "0.000000"
    worksheet.conditional_formatting.add("K13", CellIsRule(operator="equal", formula=['"ERREUR"'], fill=PatternFill("solid", fgColor="F4B183")))
    _name(workbook, "SyntheseControles", "Controles!$K$5")
    worksheet.conditional_formatting.add(f"D5:D{last}", CellIsRule(operator="equal", formula=['"ERREUR"'], fill=PatternFill("solid", fgColor="F4B183")))
    worksheet.conditional_formatting.add(f"G5:G{last}", CellIsRule(operator="equal", formula=['"ERREUR"'], fill=PatternFill("solid", fgColor="F4B183")))
    worksheet.conditional_formatting.add(f"I5:I{last}", CellIsRule(operator="equal", formula=['"ERREUR"'], fill=PatternFill("solid", fgColor="F4B183")))
    worksheet.freeze_panes = "A5"
    return last


def _readme(workbook, inputs):
    worksheet = workbook.create_sheet("Lisez_moi", 0)
    _title(worksheet, "Annexe Excel — reporting")
    lines = [
        "Sources. Les cours sont les cours de clôture ajustés des dividendes, publics, convertis en CHF au cours de fin de mois. Le change et le SARON viennent de la Banque nationale suisse. Le fonds de comparaison est l'iShares MSCI Global Sustainable Development Goals ETF : son rendement mensuel publié de la valeur liquidative est converti en CHF au cours BNS de fin de mois.",
        f"Actualisation du classeur : {inputs['generated']}. La fenêtre affichée est la formule DebutFenetre → FinFenetre, lue sur les mois du fichier de rendements.",
        "Tolérance : la cellule nommée Tolerance. Elle est égale à l'agreement du pipeline et elle est fixée avant la comparaison.",
        "Périmètre : trois livres d'actions cotées en CHF, plus le fonds iShares en CHF. Pas de données de conservation. Les rendements des livres sont des rendements totaux bruts : dividendes réinvestis, avant frais et avant impôt à la source. Les poids dérivent avec le marché entre deux rééquilibrages trimestriels.",
        "Illustratif : les quatre chocs de la feuille Stress sont des simulations. Ils ne sont pas une prévision et ils ne réestiment pas les poids.",
        "Power BI lit les cellules publiées. Il ne recalcule pas le Sharpe, la VaR ni les chocs. Ce classeur recalcule ces indicateurs à partir des rendements mensuels. Suivi, Performance, Risque et Chocs portent les titres des pages HTML et des visuels Power BI correspondants. Les formules des graphiques sont sur la feuille Series.",
        "La colonne valeur_power_bi reprend expected_values.csv. Le statut Power BI reste « en attente d'export Power BI » tant que la colonne export_power_bi est vide. La procédure de collage est dans EXPLICATIONS.md.",
    ]
    for index, line in enumerate(lines):
        worksheet.cell(3 + index, 1, line)
        worksheet.cell(3 + index, 1).alignment = Alignment(wrap_text=True)
        worksheet.row_dimensions[3 + index].height = 32
    worksheet.column_dimensions["A"].width = 140
    worksheet["A11"] = "Fenêtre"
    worksheet["B11"] = '=DebutFenetre&" → "&FinFenetre'
    worksheet["A12"] = "Tolérance"
    worksheet["B12"] = "=Tolerance"
    worksheet["B12"].number_format = "0.00E+00"


def _m_type(series):
    if pd.api.types.is_bool_dtype(series):
        return "type logical"
    if pd.api.types.is_integer_dtype(series):
        return "Int64.Type"
    if pd.api.types.is_float_dtype(series):
        return "type number"
    return "type text"


def _queries(inputs):
    QUERY_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "Rendements": (MONTHLY_RETURNS_FILE, inputs["returns"]),
        "Benchmark": (BENCHMARK_RETURNS_FILE, inputs["benchmark"]),
        "Saron": (SARON_TREATED, inputs["saron"]),
        "Metriques": (METRICS_FILE, inputs["metrics"]),
        "PerformancePubliee": (PERFORMANCE_METRICS_FILE, inputs["performance"]),
        "RisquePublie": (RISK_METRICS_FILE, inputs["risk"]),
        "StressPublie": (RESULTS_FILE, inputs["stress"]),
        "Chemin": (PATH_FILE, inputs["path"]),
        "Poids": (WEIGHTS_FILE, inputs["weights"]),
        "Secteurs": (SECTOR_FILE, inputs["sectors"]),
        "Zones": (ZONE_FILE, inputs["zones"]),
        "Devises": (EXPOSURE_FILE, inputs["currencies"]),
        "Positions": (HOLDINGS_FILE, inputs["holdings"]),
        "Limites": (LIMIT_FILE, inputs["limits"]),
        "Contributions": (CONTRIBUTION_FILE, inputs["contributions"]),
        "Classement": (TOP10_FILE, inputs["top10"]),
        "Correlation": (MATRIX_FILE, inputs["matrix"]),
        "Effectif": (CONCENTRATION_HISTORY_FILE, inputs["history"]),
        "Rotation": (TURNOVER_FILE, inputs["turnover"]),
        "RapportMois": (REPORT_FILE, inputs["report"]),
        "QueueMois": (TAIL_FILE, inputs["tail"]),
    }
    written = []
    for name, (path, frame) in files.items():
        pairs = ", ".join(
            '{{"{0}", {1}}}'.format(str(column).replace('"', '""'), _m_type(frame[column]))
            for column in frame.columns
        )
        text = (
            "let\n"
            f'    Source = Csv.Document(File.Contents("{PROJECT_TOKEN}/{path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()}"), '
            "[Delimiter = \",\", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),\n"
            "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),\n"
            f"    Typed = Table.TransformColumnTypes(Promoted, {{{pairs}}})\n"
            "in\n"
            "    Typed\n"
        )
        target = QUERY_DIR / f"{name}.m"
        target.write_text(text, encoding="utf-8")
        written.append(target)
    positions = QUERY_DIR / "Positions.m"
    positions.write_text(
        positions.read_text(encoding="utf-8").replace(
            "in\n    Typed\n",
            ",\n    Ranked = Table.AddColumn(Typed, \"rang\", each\n"
            "        let\n"
            "            strategy = [strategy],\n"
            "            weight = [weight],\n"
            "            ticker = [ticker]\n"
            "        in\n"
            "            Table.RowCount(Table.SelectRows(Typed, each [strategy] = strategy and ([weight] > weight or ([weight] = weight and [ticker] <= ticker))))),\n"
            "    WithRank = Table.AddColumn(Ranked, \"cle_rang\", each [strategy] & \"|\" & Text.From([rang])),\n"
            "    WithTitle = Table.AddColumn(WithRank, \"cle_titre\", each [strategy] & \"|\" & [ticker])\n"
            "in\n"
            "    WithTitle\n",
        ),
        encoding="utf-8",
    )
    cross = QUERY_DIR / "SourcesCroisees.m"
    cross.write_text(
        "\n".join(
            [
                "let",
                "    DernierMois = List.Max(Rendements[month]),",
                "    RendementLignes =",
                "        let",
                "            Base = Table.SelectColumns(Rendements, {\"strategy\", \"month\", \"portfolio_return\"}),",
                "            A = Table.AddColumn(Base, \"famille\", each \"rendement\"),",
                "            B = Table.AddColumn(A, \"libelle\", each \"portefeuille\"),",
                "            C = Table.AddColumn(B, \"mesure\", each \"portfolio_return\"),",
                "            D = Table.RenameColumns(C, {{\"month\", \"periode\"}, {\"portfolio_return\", \"valeur\"}})",
                "        in",
                "            Table.SelectColumns(D, {\"famille\", \"strategy\", \"periode\", \"libelle\", \"mesure\", \"valeur\"}),",
                "    FondsLignes =",
                "        let",
                "            Base = Table.SelectColumns(Benchmark, {\"month\", \"benchmark_return_chf\"}),",
                "            A = Table.AddColumn(Base, \"strategy\", each \"benchmark\"),",
                "            B = Table.AddColumn(A, \"famille\", each \"rendement\"),",
                "            C = Table.AddColumn(B, \"libelle\", each \"fonds\"),",
                "            D = Table.AddColumn(C, \"mesure\", each \"benchmark_return_chf\"),",
                "            E = Table.RenameColumns(D, {{\"month\", \"periode\"}, {\"benchmark_return_chf\", \"valeur\"}})",
                "        in",
                "            Table.SelectColumns(E, {\"famille\", \"strategy\", \"periode\", \"libelle\", \"mesure\", \"valeur\"}),",
                "    PoidsLignes =",
                "        let",
                "            Base = Table.SelectColumns(Secteurs, {\"strategy\", \"sector\", \"weight\"}),",
                "            A = Table.AddColumn(Base, \"famille\", each \"poids\"),",
                "            B = Table.AddColumn(A, \"periode\", each DernierMois),",
                "            C = Table.AddColumn(B, \"mesure\", each \"poids\"),",
                "            D = Table.RenameColumns(C, {{\"sector\", \"libelle\"}, {\"weight\", \"valeur\"}})",
                "        in",
                "            Table.SelectColumns(D, {\"famille\", \"strategy\", \"periode\", \"libelle\", \"mesure\", \"valeur\"}),",
                "    ContributionLignes =",
                "        let",
                "            Base = Table.SelectColumns(Contributions, {\"strategy\", \"month\", \"sector\", \"month_contribution\"}),",
                "            A = Table.AddColumn(Base, \"famille\", each \"contribution\"),",
                "            B = Table.AddColumn(A, \"mesure\", each \"contribution_mensuelle\"),",
                "            C = Table.RenameColumns(B, {{\"month\", \"periode\"}, {\"sector\", \"libelle\"}, {\"month_contribution\", \"valeur\"}})",
                "        in",
                "            Table.SelectColumns(C, {\"famille\", \"strategy\", \"periode\", \"libelle\", \"mesure\", \"valeur\"}),",
                "    StressNarrow = Table.Unpivot(Table.SelectColumns(StressPublie, {\"strategy\", \"shock\", \"window_end\", \"terminal_wealth\", \"maximum_drawdown\", \"annualized_volatility\", \"sharpe_ratio\"}), {\"terminal_wealth\", \"maximum_drawdown\", \"annualized_volatility\", \"sharpe_ratio\"}, \"mesure_source\", \"valeur\"),",
                "    StressMapped = Table.AddColumn(StressNarrow, \"mesure\", each if [mesure_source] = \"terminal_wealth\" then \"richesse_finale\" else if [mesure_source] = \"maximum_drawdown\" then \"drawdown_maximal\" else if [mesure_source] = \"annualized_volatility\" then \"volatilite\" else \"sharpe\"),",
                "    StressLignes =",
                "        let",
                "            A = Table.AddColumn(StressMapped, \"famille\", each \"stress\"),",
                "            B = Table.RenameColumns(A, {{\"shock\", \"libelle\"}, {\"window_end\", \"periode\"}})",
                "        in",
                "            Table.SelectColumns(B, {\"famille\", \"strategy\", \"periode\", \"libelle\", \"mesure\", \"valeur\"}),",
                "    Combined = Table.Combine({RendementLignes, FondsLignes, PoidsLignes, ContributionLignes, StressLignes}),",
                "    TypedOut = Table.TransformColumnTypes(Combined, {{\"famille\", type text}, {\"strategy\", type text}, {\"periode\", type text}, {\"libelle\", type text}, {\"mesure\", type text}, {\"valeur\", type number}})",
                "in",
                "    TypedOut",
                "",
            ]
        ),
        encoding="utf-8",
    )
    written.append(cross)
    pivot = QUERY_DIR / "tableau_croise.txt"
    pivot.write_text(
        "\n".join(
            [
                "Trois tableaux croisés dynamiques, un seul cache, table SourcesCroisees.",
                "SourcesCroisees référence les requêtes Rendements, Benchmark, Secteurs, Contributions et StressPublie.",
                "Elle ne relit pas les CSV. Recalcul et la vue d'ensemble lisent les tables chargées par ces mêmes requêtes.",
                "La famille rendement sert au contrôle : même nombre de lignes et même somme que Rendements plus Benchmark.",
                "Croise_secteurs : famille = poids, lignes = libelle, colonnes = strategy, somme de valeur.",
                "Croise_contributions : famille = contribution, mêmes axes, somme de valeur.",
                "Croise_stress : famille = stress, lignes = libelle puis mesure, colonnes = strategy, somme de valeur.",
                "Segments strategy et periode, reliés aux trois tableaux parce qu'ils partagent le cache.",
                "Les poids sectoriels n'ont pas de mois dans le CSV : leur période est le dernier mois publié.",
                "Le stress est rattaché au dernier mois de la fenêtre. Un segment de mois antérieur le masque.",
                "Le journal de qualité est un classeur, pas un CSV : il n'a pas de requête dans ce dossier.",
                "",
                "Les fichiers .m sont aussi créés dans le classeur par Excel (Queries.Add).",
                "S'ils manquent : Données, Obtenir les données, Requête vide, Éditeur avancé, coller le .m.",
            ]
        ),
        encoding="utf-8",
    )
    written.append(pivot)
    return written


def _arrange(workbook):
    front = (
        "Lisez_moi",
        "Suivi",
        "Performance",
        "Risque",
        "Chocs",
        "Vue_ensemble",
        "Indicateurs",
        "Correlation",
        "Reconciliation",
        "Controles",
        "Qualite",
        "Parametres",
        "Recalcul",
        "Stress",
        "Series",
    )
    for index, name in enumerate(front):
        current = workbook.sheetnames.index(name)
        workbook.move_sheet(name, offset=index - current)


def _build_file(inputs):
    workbook = Workbook()
    _parameters(workbook, inputs)
    _data_sheets(workbook, inputs)
    recalcul = _recalcul(workbook, inputs)
    stress = _stress(workbook, inputs, recalcul)
    last_reconciliation = _reconciliation(workbook, recalcul, stress)
    _views(workbook, inputs)
    _controls(workbook, inputs, recalcul)
    _readme(workbook, inputs)
    from src.reporting.workbook_dashboard import add_dashboard
    add_dashboard(workbook, inputs, recalcul)
    _arrange(workbook)
    EXCEL_REPORTS.mkdir(parents=True, exist_ok=True)
    workbook.save(WORKBOOK_FILE)
    return last_reconciliation


def calculate_in_excel(path):
    """Recalculate with the installed Excel. Leave the formulas in the file."""
    import subprocess

    target = str(Path(path).resolve())
    script = """
$ErrorActionPreference = 'Stop'
$excel = $null
try {
  $excel = New-Object -ComObject Excel.Application
  $excel.Visible = $false
  $excel.DisplayAlerts = $false
  $excel.AskToUpdateLinks = $false
  $wb = $excel.Workbooks.Open($env:ANNEX_PATH)
  $excel.CalculateFull()
  $wb.Save()
  $wb.Close($true)
} finally {
  if ($null -ne $excel) { $excel.Quit() }
}
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "ANNEX_PATH": target},
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout or "Excel did not calculate the workbook.")


def _calculated_rows(path):
    calculated = load_workbook(path, data_only=True)
    worksheet = calculated["Reconciliation"]
    rows = []
    for row in range(5, worksheet.max_row + 1):
        indicator = worksheet.cell(row, 1).value
        if indicator is None:
            continue
        rows.append(
            {
                "indicateur": indicator,
                "livre": worksheet.cell(row, 2).value,
                "python": worksheet.cell(row, 4).value,
                "excel": worksheet.cell(row, 5).value,
                "ecart": worksheet.cell(row, 7).value,
                "statut": worksheet.cell(row, 9).value,
                "cause": worksheet.cell(row, 10).value,
                "cloture": worksheet.cell(row, 11).value,
                "power_bi": worksheet.cell(row, 6).value,
                "export_power_bi": worksheet.cell(row, 12).value,
                "statut_power_bi": worksheet.cell(row, 13).value,
                "cause_power_bi": worksheet.cell(row, 14).value,
            }
        )
    controls = calculated["Controles"]["K5"].value
    source = calculated["Controles"]["K13"].value
    errors = []
    for sheet in calculated.worksheets:
        for cell_row in sheet.iter_rows():
            for cell in cell_row:
                if isinstance(cell.value, str) and cell.value.startswith("#"):
                    errors.append(f"{sheet.title}!{cell.coordinate} {cell.value}")
    return rows, controls, errors, source


def _power_bi_text(pending, power_exceptions):
    """How export_power_bi was filled, read from the export file itself."""
    manual = (
        "Sans export automatique, la saisie reste manuelle : ouvrir le projet dans Desktop, Actualiser, "
        "puis copier la valeur d'une mesure dans `export_power_bi`, sur la ligne du même indicateur et du même livre. "
        "`valeur_power_bi` reste la valeur attendue du pipeline. Tolerance reste la valeur écrite avant la comparaison."
    )
    if not EXPORT_FILE.exists():
        return (
            "Aucun export réel n'a été fait : `power_bi_export.csv` n'existe pas. Toute la colonne reste en attente.\n\n"
            "Pour le produire : ouvrir `dashboards/powerbi/Investment Analytics.pbip` dans Power BI Desktop, cliquer sur Actualiser, "
            "puis lancer `python -m src.reporting.power_bi_export`, puis `python -m src.pipeline.refresh`. " + manual
        )
    export = pd.read_csv(EXPORT_FILE)
    first = export.iloc[0]
    lines = [
        f"`export_power_bi` contient {len(export)} valeurs lues dans Power BI Desktop le {first['exporte_le']}, "
        f"sur le moteur {first['moteur']}. Les données du modèle avaient été actualisées dans Desktop entre {first['donnees_actualisees_le']}.",
        "",
        "Méthode. Pendant qu'un rapport est ouvert, Desktop fait tourner un moteur Analysis Services local. "
        "`python -m src.reporting.power_bi_export` lit son port dans le dossier de travail de Desktop, s'y connecte avec ADOMD.NET "
        "et envoie une requête DAX `EVALUATE` par ligne : la mesure du modèle, filtrée sur le livre, le choc ou le dernier mois. "
        "La requête de chaque ligne est écrite dans `power_bi_export.csv`. Le rapport n'est ni modifié ni enregistré.",
        "",
        "Ce que la valeur est. C'est la valeur que le moteur renvoie pour la mesure, avec tous ses chiffres. "
        "Un visuel affiche la même valeur arrondie par son format. Ce n'est pas une lecture d'écran.",
        "",
        "Ce que l'export prouve. Pour le rendement chaîné et le drawdown maximal, la mesure recalcule l'indicateur en DAX à partir des rendements mensuels : "
        "un statut OK est alors un troisième calcul, après Python et Excel. Pour les autres lignes, la mesure est un `SELECTEDVALUE` ou un `MAX` de la colonne publiée : "
        "Power BI relit le chiffre du pipeline, et un statut OK prouve que le modèle a chargé le bon fichier, la bonne colonne et le bon filtre, pas un calcul indépendant.",
        "",
        "Durée de validité. Le pipeline recopie ce fichier à chaque génération. Si les données changent après l'export, la formule compare l'ancien export aux nouvelles valeurs "
        "et la ligne passe en EXCEPTION : l'actualisation de Desktop et un nouvel export rétablissent la ligne. Tolerance reste la valeur écrite avant la comparaison.",
    ]
    if pending:
        lines += ["", "Lignes restées en attente, avec leur cause (colonne `cause_power_bi`) :", ""]
        lines += [f"- {row['indicateur']} / {row['livre']} : {row.get('cause_power_bi') or 'cause non écrite'}" for row in pending]
    if power_exceptions:
        lines += ["", "Lignes en EXCEPTION. Elles restent ouvertes côté Power BI, la cause est à écrire dans `cause_power_bi` :", ""]
        lines += [
            f"- {row['indicateur']} / {row['livre']} : export {row.get('export_power_bi')}, Excel {row['excel']}"
            for row in power_exceptions
        ]
    lines += ["", manual]
    return "\n".join(lines)


def _write_explanations(rows):
    exceptions = [row for row in rows if row["statut"] == "EXCEPTION"]
    unpublished = [row for row in rows if row["statut"] == "non publié"]
    pending = [row for row in rows if row.get("statut_power_bi") == "en attente d'export Power BI"]
    power_ok = [row for row in rows if row.get("statut_power_bi") == "OK"]
    power_exceptions = [row for row in rows if row.get("statut_power_bi") == "EXCEPTION"]
    power_text = _power_bi_text(pending, power_exceptions)
    if exceptions:
        finding = "Des écarts dépassent la tolérance. Ils restent ouverts tant que la cause n'est pas écrite dans la feuille.\n\n"
        finding += "\n".join(
            f"- {row['indicateur']} / {row['livre']} : écart {row['ecart']}"
            for row in exceptions
        )
    else:
        finding = (
            "Tous les indicateurs publiés par le pipeline coïncident avec le recalcul Excel "
            "à l'intérieur de la tolérance. Aucun écart n'a été inventé pour les faire coïncider."
        )
    text = f"""# Annexe Excel

## Formules

Le recalcul part des rendements mensuels. Il ne lit pas les indicateurs déjà écrits par Python.

Ces rendements mensuels sont ceux du pipeline : rendement total en CHF, avec les dividendes déclarés réinvestis au jour de détachement, au cours BNS de fin de mois, et des poids qui dérivent entre deux rééquilibrages trimestriels. Excel ne refait pas cette étape. Il ne peut donc pas détecter une erreur de base de rendement ou de dérive : il vérifie que les indicateurs sont bien calculés à partir de ces rendements.

Le rendement chaîné est le produit des `1 + r`, moins un. Le rendement annualisé est ce produit élevé à la puissance `12 / T`, moins un. `T` est le nombre de mois. L'annualisation n'utilise pas 252.

La volatilité annualisée est l'écart-type d'échantillon des rendements du portefeuille, diviseur `T - 1`, multiplié par la racine de 12. Ce n'est pas l'écart-type de l'excédent.

Le Sharpe est la moyenne de l'excédent sur le SARON, divisée par l'écart-type d'échantillon de cet excédent, multipliée par la racine de 12. Le SARON mensuel est `(1 + taux annuel en pourcentage / 100) ^ (1 / 12) - 1`.

Le Sortino met au numérateur la même moyenne d'excédent. Au dénominateur, chaque mois au-dessus du SARON contribue 0 et chaque mois en dessous contribue le carré de l'excédent. Le diviseur reste `T - 1`, puis on annualise par la racine de 12.

Le drawdown est la richesse divisée par son plus haut déjà atteint, moins un. La mise de départ, une unité, est le premier plus haut : un livre qui commence en baisse est déjà en drawdown. La richesse vaut `1 + r` à la fin du premier mois. Le drawdown maximal est le minimum de cette série.

La VaR historique à 95 % est le rendement du rang `k = plafond(0,05 × T)`, après tri du pire vers le meilleur. À rendement égal, le mois le plus ancien vient d'abord. L'expected shortfall est la moyenne des rangs 1 à k. Ce ne sont pas des rendements annualisés et ce n'est pas une loi normale.

L'écart de suivi est l'écart-type d'échantillon de `rendement du livre − rendement du fonds en CHF`, multiplié par la racine de 12. Le ratio d'information est la moyenne de cet écart divisée par son écart-type, multipliée par la racine de 12.

Le choc de marché remplace le dernier rendement par le paramètre −20 %. Le choc de récession remplace les six derniers mois par −3 %. Le choc de volatilité conserve la moyenne et multiplie les écarts à la moyenne par 1,5. Le choc de taux ajoute 2 points au SARON annuel, reconvertit le mois, et ne change pas le rendement du portefeuille. Ces chocs sont illustratifs.

## Feuilles

Lisez-moi donne les sources, la date de génération, la tolérance et le périmètre. Suivi, Performance, Risque et Chocs portent les titres des pages HTML et des visuels Power BI correspondants. Les séries sont les mêmes. Les formules de ces graphiques sont sur Series. Parametres tient la tolérance, les plafonds et les paramètres de choc. Recalcul, la vue d'ensemble et les trois tableaux croisés lisent des tables chargées par Power Query. Actualiser tout recharge ces tables. SourcesCroisees ne relit pas les fichiers : elle référence les requêtes Rendements, Benchmark, Secteurs, Contributions et StressPublie. Recalcul porte les formules. Reconciliation compare Python et Excel. valeur_power_bi est la valeur attendue du pipeline. statut_power_bi reste en attente tant qu'une valeur lue dans Desktop n'est pas écrite dans export_power_bi. Vue_ensemble porte la fiche en INDEX/MATCH et la même fiche en XLOOKUP, plus un Top 10 en FILTER et SORTBY. Indicateurs, Correlation, Stress et Qualite présentent le détail. Croise_secteurs, Croise_contributions et Croise_stress sont trois tableaux croisés sur le cache SourcesCroisees, avec les segments strategy et periode. Controles vérifie que les poids somment à 1 et que les contributions sectorielles reconstruisent le rendement du mois. La même feuille compare le nombre de lignes et la somme des rendements entre les tables lues par les formules et les lignes de rendement de SourcesCroisees. Le résultat est OK ou ERREUR. Une ligne compte si son poids dépasse la tolérance, ce qui est le seuil du pipeline. L'équipondéré n'est pas soumis à la bande de 25 à 40 lignes. Un mois optimisé hors bande est affiché en ERREUR et ne fait pas échouer la commande : ce n'est pas un écart de formule.

## Power BI

La plupart des mesures DAX utilisent `SELECTEDVALUE` ou `MAX` sur la cellule publiée : elles ne refont pas le calcul. `Rendement chaîné calculé` et `Drawdown maximal calculé` recalculent en DAX, avec la définition du pipeline, uniquement pour la réconciliation. Elles ne sont pas posées sur une page et ne lisent ni `maximum_drawdown` ni `cumulative_wealth`. La page Performance calcule aussi le multiple contre le SARON, le multiple contre le fonds et le rendement glissant sur 12 mois, à partir des rendements mensuels. Le fonds y est une ligne : son rendement est le sien, son écart contre lui-même est nul. Les pages d'allocation, de suivi et de chocs ne proposent pas le fonds dans le filtre. Le graphique du temps des chocs est l'écart de richesse. Il n'y a pas de superposition des cinq chemins. Une valeur collée depuis un visuel doit rejoindre la colonne Python, à l'arrondi d'affichage près. Si l'écart vient seulement de cet arrondi, la cause est écrite et la ligne est close. La tolérance reste celle écrite avant la comparaison.

## Résultat de cette génération

{finding}

Lignes laissées « non publié » : {len(unpublished)}. Le ratio d'information du fonds n'est pas défini : le fonds est la référence et son écart de suivi est nul. La cause est écrite et la clôture est close.

Lignes Power BI en attente d'export : {len(pending)}. Lignes Power BI passées OK par la formule : {len(power_ok)}. Lignes Power BI en EXCEPTION : {len(power_exceptions)}. Une valeur attendue ne peut pas rendre cette colonne OK : seule une valeur lue dans Power BI Desktop le peut.

## Export Power BI

{power_text}

## Dix questions

1. Pourquoi le recalcul est-il indépendant ? Recalcul ne lit que les rendements mensuels, le SARON et les paramètres. Il ne lit pas Metriques, PerformancePubliee, RisquePublie ni StressPublie. La réconciliation compare ensuite les deux résultats. Si Excel lisait le chiffre de Python, l'écart serait nul par construction.
2. Comment la tolérance a-t-elle été fixée ? Elle est égale à l'agreement du pipeline, 1e-8, la même constante pour les contributions, le risque et les chocs. Elle est écrite dans Parametres avant la comparaison. Elle n'est pas ajustée pour faire coïncider une ligne.
3. Pourquoi l'écart-type est-il celui de l'échantillon ? Le diviseur est T − 1, `STDEV.S` dans Excel et `std(ddof=1)` dans Python. Les mois de la fenêtre servent à estimer une dispersion, ils ne sont pas traités comme la population entière. `STDEV.P` n'est pas utilisé.
4. Comment le TWR est-il calculé ? Le rendement chaîné est le produit des (1 + r) mensuels, moins un. Chaque r est déjà le rendement du livre de fin de mois à fin de mois, poids du mois compris. En l'absence de flux externe, ce produit est le rendement pondéré par le temps. Il n'y a pas de fichier de conservation, donc pas de flux à retirer, et ce n'est pas un rendement de Dietz.
5. Comment la VaR historique fonctionne-t-elle ? Les rendements mensuels sont triés du pire au meilleur, puis par mois croissant. k est le plafond de 5 % de T. La VaR est le rendement du rang k. L'expected shortfall est la moyenne des rangs 1 à k. Pas de loi normale, pas d'annualisation.
6. Que ne prouve pas la réconciliation ? Elle prouve que les formules Excel retrouvent les chiffres publiés par le pipeline, à la tolérance près. Elle ne prouve pas que les titres ont été détenus, que les cours sont ceux d'un conservateur, ni que des frais ont été prélevés. Il n'y a pas de données de conservation. Elle ne prouve pas non plus que les définitions sont les bonnes : Excel applique celles du pipeline, écrites par le même auteur, et la plupart des lignes Power BI relisent simplement la cellule publiée. Elle trouve une erreur de calcul, pas une erreur de méthode.
7. Comment un écart serait-il traité ? Le statut passe à EXCEPTION et la clôture reste ouverte tant que la cause n'est pas écrite. La commande du pipeline s'arrête. On documente la cause. On ne modifie pas la tolérance et on n'ajuste pas une formule pour forcer OK. Un écart qui vient d'une définition différente est un résultat, pas une erreur à masquer.
8. Pourquoi le ratio d'information du fonds n'est-il pas publié ? L'écart de suivi du fonds contre lui-même est nul. Diviser la moyenne de cet écart par un écart-type nul n'est pas défini. Le Sharpe, le Sortino, la VaR et l'expected shortfall du fonds sont publiés, avec les mêmes définitions que pour les livres.
9. Pourquoi la colonne Power BI n'est-elle jamais OK avant un export Desktop ? `valeur_power_bi` est la valeur attendue, lue dans expected_values.csv. Ce n'est pas une copie d'écran de Desktop. Le statut reste « en attente d'export Power BI » tant que `export_power_bi` est vide. Une valeur lue dans Desktop, écrite par `src.reporting.power_bi_export` ou collée à la main, fait basculer la formule vers OK ou EXCEPTION.
10. Pourquoi les trois tableaux croisés partagent-ils un cache ? Excel ne relie un segment à plusieurs tableaux que s'ils ont le même cache. SourcesCroisees référence les requêtes Rendements, Benchmark, Secteurs, Contributions et StressPublie. Elle ne relit pas les CSV. Recalcul lit les tables Rendements et Benchmark, chargées par ces mêmes requêtes. La vue d'ensemble lit Secteurs, Zones, Devises et Positions, chargées par leurs requêtes. Le contrôle de la feuille Contrôles compare le nombre de lignes et la somme des rendements. Il est OK seulement si les deux côtés coïncident, à la tolérance près. Les segments Livre et Période pilotent les trois tableaux. Le journal de qualité vient d'un classeur, pas d'un CSV, donc il n'a pas de requête Power Query.
"""
    EXPLANATIONS_FILE.write_text(text, encoding="utf-8")


def present_in_excel(path):
    """Add the three pivots, both slicers, and one Power Query per CSV."""
    import subprocess

    target = str(Path(path).resolve())
    query_dir = str(QUERY_DIR.resolve())
    script = r"""
$ErrorActionPreference = 'Continue'
$excel = $null
$report = New-Object System.Collections.Generic.List[string]
function Add-CrossPivot($workbook, $cache, $sheetName, $pivotName, $famille, $withMeasure) {
  $sheet = $workbook.Worksheets.Add()
  $sheet.Name = $sheetName
  $pivot = $cache.CreatePivotTable($sheet.Range('A3'), $pivotName)
  $pivot.PivotFields('libelle').Orientation = 1
  if ($withMeasure) { $pivot.PivotFields('mesure').Orientation = 1 }
  $pivot.PivotFields('strategy').Orientation = 2
  $null = $pivot.AddDataField($pivot.PivotFields('valeur'), 'Somme', -4157)
  $page = $pivot.PivotFields('famille')
  $page.Orientation = 3
  $page.CurrentPage = $famille
  if (-not $withMeasure) {
    try { $pivot.DataBodyRange.NumberFormat = '0.0%' } catch {}
  }
  $sheet.Range('A1').Value2 = 'Tableau croise dynamique. Cache SourcesCroisees. Famille : ' + $famille + '. Segments : strategy et periode, relies aux trois tableaux.'
  $sheet.Move([System.Reflection.Missing]::Value, $workbook.Worksheets.Item($workbook.Worksheets.Count))
  return $pivot
}
try {
  $excel = New-Object -ComObject Excel.Application
  $excel.Visible = $false
  $excel.DisplayAlerts = $false
  $excel.AskToUpdateLinks = $false
  $wb = $excel.Workbooks.Open($env:ANNEX_PATH)
  try { $excel.Calculation = -4135 } catch { $report.Add('calc_mode_fail') }
  try { $wb.Queries.FastCombine = $true } catch { $report.Add('fastcombine_fail') }
  Get-ChildItem -Path $env:ANNEX_QUERY_DIR -Filter '*.m' | ForEach-Object {
    try {
      $text = (Get-Content -Raw -Path $_.FullName).Replace('{{ProjectRoot}}', $env:ANNEX_PROJECT_ROOT)
      $wb.Queries.Add($_.BaseName, $text) | Out-Null
      $report.Add('csv:' + $_.BaseName)
    } catch {
      $report.Add('csv_fail:' + $_.BaseName)
    }
  }
  $bound = $false
  try {
    $targets = @(
      @{ Query = 'Rendements'; Sheet = 'Donnees_Rendements'; Table = 'Rendements' },
      @{ Query = 'Benchmark'; Sheet = 'Donnees_Benchmark'; Table = 'Benchmark' },
      @{ Query = 'Secteurs'; Sheet = 'Donnees_Secteurs'; Table = 'Secteurs' },
      @{ Query = 'Zones'; Sheet = 'Donnees_Zones'; Table = 'Zones' },
      @{ Query = 'Devises'; Sheet = 'Donnees_Devises'; Table = 'Devises' },
      @{ Query = 'Positions'; Sheet = 'Donnees_Positions'; Table = 'Positions' },
      @{ Query = 'Contributions'; Sheet = 'Donnees_Contributions'; Table = 'Contributions' },
      @{ Query = 'StressPublie'; Sheet = 'Donnees_Stress'; Table = 'StressPublie' },
      @{ Query = 'SourcesCroisees'; Sheet = 'Donnees_Croise'; Table = 'SourcesCroisees' }
    )
    $names = @($targets | ForEach-Object { $_.Table })
    $bounds = @()
    foreach ($item in $targets) {
      $sheet = $wb.Worksheets.Item($item.Sheet)
      $lo = $sheet.ListObjects.Item($item.Table)
      $area = $lo.Range
      $bounds += [pscustomobject]@{ Sheet = $item.Sheet; R1 = $area.Row; R2 = ($area.Row + $area.Rows.Count - 1); C1 = $area.Column; C2 = ($area.Column + $area.Columns.Count - 1) }
    }
    $saved = New-Object System.Collections.Generic.List[object]
    foreach ($ws in @($wb.Worksheets)) {
      $used = $ws.UsedRange
      $formulas = $used.Formula
      if ($formulas -is [System.Array]) {
        $lowerR = $formulas.GetLowerBound(0)
        $upperR = $formulas.GetUpperBound(0)
        $lowerC = $formulas.GetLowerBound(1)
        $upperC = $formulas.GetUpperBound(1)
        for ($r = $lowerR; $r -le $upperR; $r++) {
          for ($c = $lowerC; $c -le $upperC; $c++) {
            $formula = [string]$formulas.GetValue($r, $c)
            if (-not $formula.StartsWith('=')) { continue }
            $hit = $false
            foreach ($name in $names) { if ($formula.Contains($name + '[')) { $hit = $true; break } }
            if (-not $hit) { continue }
            $absRow = $used.Row + ($r - $lowerR)
            $absCol = $used.Column + ($c - $lowerC)
            $inside = $false
            foreach ($area in $bounds) {
              if ($area.Sheet -eq $ws.Name -and $absRow -ge $area.R1 -and $absRow -le $area.R2 -and $absCol -ge $area.C1 -and $absCol -le $area.C2) { $inside = $true; break }
            }
            if ($inside) { continue }
            $saved.Add([pscustomobject]@{ Sheet = $ws.Name; Row = $absRow; Col = $absCol; Formula = $formula })
          }
        }
      }
    }
    if ($saved.Count -lt 1) { throw 'no formula references the source tables' }
    foreach ($item in $targets) {
      $sheet = $wb.Worksheets.Item($item.Sheet)
      $sheet.ListObjects.Item($item.Table).Delete()
      $cs = 'OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=$Workbook$;Location=' + $item.Query + ';Extended Properties=""'
      $wb.Connections.Add2($item.Query, $item.Query, $cs, ('SELECT * FROM [' + $item.Query + ']'), 2) | Out-Null
      $conn = $wb.Connections.Item($item.Query)
      $loaded = $sheet.ListObjects.Add(3, $conn, [Type]::Missing, 1, $sheet.Range('A3'))
      $loaded.Name = $item.Table
      $loaded.QueryTable.BackgroundQuery = $false
      $loaded.QueryTable.AdjustColumnWidth = $false
      try {
        $null = $loaded.QueryTable.Refresh()
      } catch {
        throw ($item.Query + ': ' + $_.Exception.Message)
      }
      $report.Add('linked:' + $item.Table + ':' + $loaded.ListRows.Count)
    }
    foreach ($item in $saved) {
      $wb.Worksheets.Item($item.Sheet).Cells.Item($item.Row, $item.Col).Formula = $item.Formula
    }
    $report.Add('formulas_restored:' + $saved.Count)
    $bound = $true
  } catch {
    $report.Add('bind_fail:' + $_.Exception.Message.Replace("`n", ' ').Replace("`r", ' '))
  }
  if ($bound -eq $true) {
  try {
    $cache = $wb.PivotCaches().Create(1, 'SourcesCroisees')
    $weights = Add-CrossPivot $wb $cache 'Croise_secteurs' 'CroiseSecteurs' 'poids' $false
    $contrib = Add-CrossPivot $wb $cache 'Croise_contributions' 'CroiseContributions' 'contribution' $false
    $stress = Add-CrossPivot $wb $cache 'Croise_stress' 'CroiseStress' 'stress' $true
    $report.Add('pivot:secteurs')
    $report.Add('pivot:contributions')
    $report.Add('pivot:stress')
    $byBook = $wb.SlicerCaches.Add($weights, 'strategy')
    $byBook.PivotTables.AddPivotTable($contrib) | Out-Null
    $byBook.PivotTables.AddPivotTable($stress) | Out-Null
    $null = $byBook.Slicers.Add($wb.Worksheets.Item('Croise_secteurs'))
    $byPeriod = $wb.SlicerCaches.Add($weights, 'periode')
    $byPeriod.PivotTables.AddPivotTable($contrib) | Out-Null
    $byPeriod.PivotTables.AddPivotTable($stress) | Out-Null
    $null = $byPeriod.Slicers.Add($wb.Worksheets.Item('Croise_contributions'))
    $report.Add('slicer:strategy')
    $report.Add('slicer:periode')
  } catch {
    $report.Add('pivot_fail:' + $_.Exception.Message.Replace("`n", ' '))
  }
  try {
    $wb.RefreshAll()
    try { $excel.CalculateUntilAsyncQueriesDone() } catch {}
    $excel.Calculation = -4105
    $excel.Calculate()
    $report.Add('refresh')
  } catch {
    $report.Add('refresh_fail:' + $_.Exception.Message.Replace("`n", ' ').Replace("`r", ' '))
  }
  try {
    $vue = $wb.Worksheets.Item('Vue_ensemble')
    for ($row = 1; $row -le 80; $row++) {
      $cell = $vue.Cells.Item($row, 9)
      if ([string]$cell.Formula -like '=*FILTER*') {
        $cell.Formula2 = $cell.Formula
        $excel.Calculate()
        $spill = 0
        try { $spill = $cell.SpillingToRange.Rows.Count } catch { $spill = 0 }
        if ($spill -eq 10) { $report.Add('spill:10') } else { $report.Add('spill_fail:' + $spill) }
        break
      }
    }
  } catch {
    $report.Add('spill_fail:' + $_.Exception.Message.Replace("`n", ' '))
  }
  try {
    $controls = $wb.Worksheets.Item('Controles')
    $report.Add('k5:' + $controls.Range('K5').Text)
    $report.Add('source:' + $controls.Range('K13').Text)
    $report.Add('rows_formules:' + $controls.Range('K9').Value2)
    $report.Add('rows_croises:' + $controls.Range('K10').Value2)
    $report.Add('somme_formules:' + $controls.Range('K11').Value2)
    $report.Add('somme_croises:' + $controls.Range('K12').Value2)
  } catch {
    $report.Add('source_fail:' + $_.Exception.Message.Replace("`n", ' ').Replace("`r", ' '))
  }
  }
  $failed = $false
  foreach ($line in $report) {
    if ($line.StartsWith('bind_fail') -or $line.StartsWith('pivot_fail') -or $line.StartsWith('refresh_fail')) { $failed = $true }
  }
  if ($failed) { $wb.Close($false) } else { $wb.Save(); $wb.Close($true) }
} finally {
  if ($null -ne $excel) { $excel.Quit() }
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}
$report -join ','
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=900,
        env={
            **os.environ,
            "ANNEX_PATH": target,
            "ANNEX_QUERY_DIR": query_dir,
            "ANNEX_PROJECT_ROOT": PROJECT_ROOT.resolve().as_posix(),
        },
    )
    report = (completed.stdout or "").strip().splitlines()
    summary = report[-1] if report else ""
    if completed.returncode != 0 or "pivot:secteurs" not in summary:
        logger.info("Excel pivot was not added: %s", completed.stderr or summary)
    return summary


def build_workbook():
    """Write the annex, calculate it in Excel, and stop on an open exception."""
    logger.info("Excel annex started")
    inputs = _load_inputs()
    EXCEL_REPORTS.mkdir(parents=True, exist_ok=True)
    inputs["expected"].to_csv(EXPECTED_FILE, index=False)
    _build_file(inputs)
    queries = _queries(inputs)
    logger.info("Excel annex written to %s", WORKBOOK_FILE)
    calculate_in_excel(WORKBOOK_FILE)
    rows, controls, errors, source = _calculated_rows(WORKBOOK_FILE)
    if not rows:
        raise RuntimeError("Excel did not cache the reconciliation values.")
    if errors:
        raise RuntimeError("Formula errors: " + "; ".join(errors[:12]))
    if controls != "OK":
        raise RuntimeError(f"Weight or contribution controls are {controls}.")
    if source != "OK":
        raise RuntimeError(f"Return source control is {source}.")
    open_rows = [row for row in rows if row["cloture"] == "ouvert"]
    _write_explanations(rows)
    if open_rows:
        detail = "; ".join(f"{row['indicateur']} {row['livre']}" for row in open_rows[:12])
        raise RuntimeError(f"Open reconciliation exceptions: {detail}")
    exported = read_export()
    for row in rows:
        key = (str(row["indicateur"]), str(row["livre"]))
        pasted = row.get("export_power_bi")
        if pasted is None:
            continue
        # Paste integrity only: Excel keeps 15 significant digits of a double.
        # This is not the reconciliation tolerance.
        if key not in exported or abs(float(pasted) - exported[key]) > 1e-13 * max(1.0, abs(exported[key])):
            raise RuntimeError(f"export_power_bi of {key} is not the value of power_bi_export.csv.")
    power = {}
    for row in rows:
        power[row["statut_power_bi"]] = power.get(row["statut_power_bi"], 0) + 1
    logger.info("Power BI column: %s", power)
    for row in rows:
        if row["statut_power_bi"] == "EXCEPTION":
            logger.warning(
                "Power BI EXCEPTION left open: %s %s export %s excel %s",
                row["indicateur"], row["livre"], row["export_power_bi"], row["excel"],
            )
    logger.info("Excel annex calculated: %s rows, controls %s", len(rows), controls)
    presented = present_in_excel(WORKBOOK_FILE)
    logger.info("Excel presentation: %s", presented)
    required = (
        "pivot:secteurs",
        "pivot:contributions",
        "pivot:stress",
        "slicer:strategy",
        "slicer:periode",
        "spill:10",
        "source:OK",
        "linked:Rendements",
        "linked:SourcesCroisees",
    )
    if any(token not in presented for token in required) or any(
        token in presented for token in ("pivot_fail", "csv_fail", "bind_fail", "refresh_fail", "source_fail")
    ):
        raise RuntimeError(f"Excel presentation is incomplete: {presented}")
    refreshed, refreshed_controls, refreshed_errors, refreshed_source = _calculated_rows(WORKBOOK_FILE)
    if refreshed_errors:
        raise RuntimeError("Formula errors after refresh: " + "; ".join(refreshed_errors[:12]))
    if refreshed_controls != "OK" or refreshed_source != "OK":
        raise RuntimeError(f"Controls after refresh: weights {refreshed_controls}, source {refreshed_source}.")
    if any(row["cloture"] == "ouvert" for row in refreshed):
        raise RuntimeError("Refresh opened a reconciliation exception.")
    logger.info("Power Query drafts: %s", len(queries))
    return {
        "workbook": WORKBOOK_FILE,
        "explanations": EXPLANATIONS_FILE,
        "rows": len(rows),
        "presentation": presented,
    }


if __name__ == "__main__":
    build_workbook()
