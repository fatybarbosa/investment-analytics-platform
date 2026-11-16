"""
Phase 10b. Real export of the Power BI measures.

Power BI Desktop runs a local Analysis Services engine while a report is
open. This module finds its port, runs one DAX query per reconciliation
line through ADOMD.NET, and writes what the engine answers to
reports/excel/power_bi_export.csv.

Nothing here computes a value: the engine does. Two measures of the model
recompute their indicator in DAX from the monthly returns (chained return,
maximum drawdown). The others return the published cell. A line the engine
gives no value for stays "en attente d'export Power BI". If Desktop is
closed, the module stops and writes nothing. It never saves the report
and never changes the model.

The value is the one the engine returns for the measure in the filter
of the line (book, shock, last month). A visual shows the same value
rounded by its display format.

Run:  python -m src.reporting.power_bi_export
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.config import EXCEL_REPORTS
from src.portfolio_construction.build_portfolios import STRATEGY_IDS
from src.stress_testing.build_stress import SHOCK_IDS
from src.utils.logger import logger


EXPORT_FILE = EXCEL_REPORTS / "power_bi_export.csv"
EXPORT_COLUMNS = (
    "mesure",
    "livre",
    "mesure_dax",
    "requete_dax",
    "valeur_exportee",
    "exporte_le",
    "moteur",
    "donnees_actualisees_le",
)
WORKSPACE_ROOTS = (
    Path(os.environ.get("USERPROFILE", "")) / "Microsoft" / "Power BI Desktop Store App" / "AnalysisServicesWorkspaces",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Power BI Desktop" / "AnalysisServicesWorkspaces",
)
# Reconciliation indicator -> DAX measure of the model. An indicator that is
# absent has no measure: it is left pending, with the reason below.
# Two measures recompute the indicator in DAX from the monthly returns of
# RendementActif. The others return the published cell (SELECTEDVALUE or MAX).
COMPUTED_IN_DAX = ("rendement_chaine", "drawdown_maximal")
FUND_HAS_NO_LINE = ("ratio_information", "rendement_chaine")
BOOK_MEASURES = {
    "rendement_chaine": "Rendement chaîné calculé",
    "drawdown_maximal": "Drawdown maximal calculé",
    "rendement_annualise": "Rendement annualisé",
    "volatilite_annualisee": "Volatilité",
    "sharpe": "Sharpe",
    "sortino": "Sortino",
    "ecart_de_suivi": "Écart de suivi",
    "ratio_information": "Ratio d'information",
    "var_historique": "VaR",
    "expected_shortfall": "Expected shortfall",
}
WEALTH_MEASURE = "Performance cumulée"
STRESS_MEASURES = {
    "stress_richesse_finale": "Richesse finale",
    "stress_drawdown_maximal": "Drawdown stressé",
    "stress_volatilite_annualisee": "Volatilité stressée",
    "stress_sharpe": "Sharpe stressé",
}
NOT_EXPORTED = {
    "richesse_finale / benchmark": "La table Chemin ne contient pas le fonds.",
}
NO_ANSWER = "Power BI Desktop n'a renvoyé aucune valeur pour cette mesure lors du dernier export."


class PowerBiUnavailable(RuntimeError):
    """Desktop is closed, or its engine did not answer."""


def find_port():
    """Port of the running Desktop engine, read from its workspace folder."""
    found = []
    for root in WORKSPACE_ROOTS:
        if not root.is_dir():
            continue
        for port_file in root.glob("*/Data/msmdsrv.port.txt"):
            text = port_file.read_text(encoding="utf-16-le").strip().lstrip("\ufeff")
            if text.isdigit():
                found.append((port_file.stat().st_mtime, int(text)))
    if not found:
        raise PowerBiUnavailable(
            "No msmdsrv.port.txt under the Power BI Desktop workspace folders: Desktop is not open."
        )
    return max(found)[1]


def _queries():
    rows = []

    def add(mesure, livre, dax_measure, expression):
        rows.append(
            {
                "mesure": mesure,
                "livre": livre,
                "mesure_dax": dax_measure,
                "requete_dax": f'EVALUATE ROW ( "v", {expression} )',
            }
        )

    for strategy in tuple(STRATEGY_IDS) + ("benchmark",):
        book = f'Strategie[strategy] = "{strategy}"'
        if strategy != "benchmark":
            add(
                "richesse_finale",
                strategy,
                WEALTH_MEASURE,
                f"VAR Dernier = CALCULATE ( MAX ( Chemin[month] ), ALL ( Chemin ) ) "
                f"RETURN CALCULATE ( [{WEALTH_MEASURE}], {book}, Chemin[month] = Dernier )",
            )
        for mesure, dax_measure in BOOK_MEASURES.items():
            if strategy == "benchmark" and mesure in FUND_HAS_NO_LINE:
                continue
            add(mesure, strategy, dax_measure, f"CALCULATE ( [{dax_measure}], {book} )")
    for strategy in STRATEGY_IDS:
        for shock in SHOCK_IDS:
            for mesure, dax_measure in STRESS_MEASURES.items():
                add(
                    mesure,
                    f"{strategy} / {shock}",
                    dax_measure,
                    f'CALCULATE ( [{dax_measure}], Strategie[strategy] = "{strategy}", Choc[shock] = "{shock}" )',
                )
    return rows


POWERSHELL = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$package = Get-AppxPackage Microsoft.MicrosoftPowerBIDesktop
$candidates = @()
if ($package) { $candidates += (Join-Path $package.InstallLocation 'bin\Microsoft.PowerBI.AdomdClient.dll') }
$candidates += 'C:\Program Files\Microsoft Power BI Desktop\bin\Microsoft.PowerBI.AdomdClient.dll'
$dll = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $dll) { throw 'Microsoft.PowerBI.AdomdClient.dll not found.' }
Add-Type -Path $dll
$queries = Get-Content -Raw -Encoding UTF8 '__QUERIES__' | ConvertFrom-Json
$connection = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection('Data Source=localhost:__PORT__')
$connection.Open()
$invariant = [Globalization.CultureInfo]::InvariantCulture
try {
  $command = $connection.CreateCommand()
  $command.CommandText = 'select [RefreshedTime] from $SYSTEM.TMSCHEMA_PARTITIONS'
  $reader = $command.ExecuteReader()
  $times = @()
  while ($reader.Read()) { if (-not $reader.IsDBNull(0)) { $times += [datetime]$reader.GetValue(0) } }
  $reader.Close()
  $oldest = ($times | Sort-Object | Select-Object -First 1)
  $newest = ($times | Sort-Object | Select-Object -Last 1)
  $answers = @()
  foreach ($query in $queries) {
    $command = $connection.CreateCommand()
    $command.CommandText = $query.requete_dax
    $reader = $command.ExecuteReader()
    $value = $null
    $kind = 'blank'
    if ($reader.Read() -and -not $reader.IsDBNull(0)) {
      $raw = $reader.GetValue(0)
      $kind = $raw.GetType().Name
      if ($raw -is [double] -or $raw -is [decimal] -or $raw -is [long] -or $raw -is [int]) {
        $value = ([double]$raw).ToString('R', $invariant)
      } else {
        $value = [string]$raw
      }
    }
    $reader.Close()
    $answers += [pscustomobject]@{ mesure = $query.mesure; livre = $query.livre; valeur = $value; type = $kind }
  }
  [pscustomobject]@{
    server = $connection.ServerVersion
    oldest_refresh = if ($oldest) { $oldest.ToString('s') } else { $null }
    newest_refresh = if ($newest) { $newest.ToString('s') } else { $null }
    answers = $answers
  } | ConvertTo-Json -Depth 4 -Compress
} finally {
  $connection.Close()
}
"""


def run_queries(port, queries, work_dir):
    """Send every query to the engine. Return its answers, unchanged."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    query_file = work_dir / "power_bi_queries.json"
    query_file.write_text(json.dumps(queries, ensure_ascii=False), encoding="utf-8")
    script = POWERSHELL.replace("__QUERIES__", str(query_file)).replace("__PORT__", str(port))
    script_file = work_dir / "power_bi_export.ps1"
    script_file.write_text(script, encoding="utf-8-sig")
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )
    if completed.returncode != 0:
        raise PowerBiUnavailable(completed.stderr or completed.stdout or "The engine did not answer.")
    return json.loads(completed.stdout.strip().splitlines()[-1])


def export_power_bi(work_dir=None):
    """Query the open Desktop model and write the export file."""
    import tempfile

    logger.info("Power BI export started")
    port = find_port()
    queries = _queries()
    with tempfile.TemporaryDirectory() as temporary:
        result = run_queries(port, queries, work_dir or temporary)
    answers = {(row["mesure"], row["livre"]): row for row in result["answers"]}
    moment = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    engine = f"localhost:{port} (Analysis Services {result['server']}, ADOMD.NET)"
    refreshed = f"{result['oldest_refresh']} → {result['newest_refresh']} UTC"
    rows = []
    blanks = []
    for query in queries:
        answer = answers[(query["mesure"], query["livre"])]
        if answer["valeur"] is None:
            blanks.append(f"{query['mesure']} {query['livre']}")
            continue
        rows.append(
            {
                **query,
                "valeur_exportee": float(answer["valeur"]),
                "exporte_le": moment,
                "moteur": engine,
                "donnees_actualisees_le": refreshed,
            }
        )
    EXCEL_REPORTS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=EXPORT_COLUMNS).to_csv(EXPORT_FILE, index=False, float_format="%.17g")
    logger.info(
        "Power BI export: %s values from %s, %s blank answers, model refreshed %s",
        len(rows),
        engine,
        len(blanks),
        refreshed,
    )
    for blank in blanks:
        logger.warning("Power BI returned no value for %s", blank)
    return {"file": EXPORT_FILE, "values": len(rows), "blanks": blanks, "engine": engine, "refreshed": refreshed}


def read_export():
    """Exported values by (mesure, livre). Empty when no export file exists."""
    if not EXPORT_FILE.exists():
        return {}
    frame = pd.read_csv(EXPORT_FILE)
    return {
        (str(row.mesure), str(row.livre)): float(row.valeur_exportee)
        for row in frame.itertuples(index=False)
    }


if __name__ == "__main__":
    outcome = export_power_bi()
    print(f"{outcome['values']} valeurs exportées depuis {outcome['engine']}")
    print(f"Données du modèle actualisées : {outcome['refreshed']}")
    for missing in outcome["blanks"]:
        print("Sans valeur :", missing)
    print(outcome["file"])
