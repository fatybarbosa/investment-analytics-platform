"""
Open Power BI Desktop and refresh its model in memory.

The report keeps no data in its file: every opening asks for Refresh. This
module does that step without a click. It starts Desktop on the project file
if Desktop is closed, waits for the local Analysis Services engine, sends one
TMSL full refresh to it, and checks that every partition was refreshed after
the command was sent.

Nothing is saved: the report file and the model are not changed. A Desktop
window that this module opened is closed again, without saving, when the
export is done. A window that was already open is left open.

The engine is reached through ADOMD.NET, like the export in
power_bi_export.py.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

from src.config import POWERBI
from src.reporting.power_bi_export import PowerBiUnavailable, find_port
from src.utils.logger import logger


REPORT_FILE = POWERBI / "Investment Analytics.pbip"
ENGINE_WAIT_SECONDS = 420
ENGINE_RETRY_SECONDS = 10
REFRESH_TIMEOUT_SECONDS = 900

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
$connection = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection('Data Source=localhost:__PORT__')
$connection.Open()
function Get-Refreshes($connection) {
  $command = $connection.CreateCommand()
  $command.CommandText = 'select [RefreshedTime] from $SYSTEM.TMSCHEMA_PARTITIONS'
  $reader = $command.ExecuteReader()
  $times = @()
  while ($reader.Read()) { if (-not $reader.IsDBNull(0)) { $times += [datetime]$reader.GetValue(0) } }
  $reader.Close()
  return ,$times
}
try {
  $command = $connection.CreateCommand()
  $command.CommandText = 'select [CATALOG_NAME] from $SYSTEM.DBSCHEMA_CATALOGS'
  $reader = $command.ExecuteReader()
  $reader.Read() | Out-Null
  $database = $reader.GetString(0)
  $reader.Close()
  $before = Get-Refreshes $connection
  $newestBefore = ($before | Sort-Object | Select-Object -Last 1)
  $command = $connection.CreateCommand()
  $command.CommandText = '{"refresh":{"type":"full","objects":[{"database":"' + $database + '"}]}}'
  $command.ExecuteNonQuery() | Out-Null
  $after = Get-Refreshes $connection
  $oldestAfter = ($after | Sort-Object | Select-Object -First 1)
  $newestAfter = ($after | Sort-Object | Select-Object -Last 1)
  [pscustomobject]@{
    partitions = $after.Count
    newest_before = if ($newestBefore) { $newestBefore.ToString('s') } else { $null }
    oldest_after = if ($oldestAfter) { $oldestAfter.ToString('s') } else { $null }
    newest_after = if ($newestAfter) { $newestAfter.ToString('s') } else { $null }
  } | ConvertTo-Json -Compress
} finally {
  $connection.Close()
}
"""


def refresh_model(port):
    """Send one full refresh to the engine. Return the partition times before and after."""
    import json

    with tempfile.TemporaryDirectory() as temporary:
        script_file = Path(temporary) / "power_bi_refresh.ps1"
        script_file.write_text(POWERSHELL.replace("__PORT__", str(port)), encoding="utf-8-sig")
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_file)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=REFRESH_TIMEOUT_SECONDS,
        )
    if completed.returncode != 0:
        raise PowerBiUnavailable(completed.stderr or completed.stdout or "The engine did not refresh.")
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    if not result["partitions"] or not result["oldest_after"]:
        raise PowerBiUnavailable("The model has no partition after the refresh.")
    if result["newest_before"] and datetime.fromisoformat(result["oldest_after"]) <= datetime.fromisoformat(
        result["newest_before"]
    ):
        raise PowerBiUnavailable(
            "A partition was not refreshed: its time is not later than the previous refresh "
            f"({result['oldest_after']} against {result['newest_before']})."
        )
    return result


def desktop_is_open():
    """
    True when Desktop is running and left a port file.

    A port file can outlive a closed Desktop, so the process is checked too.
    """
    listing = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "@(Get-Process PBIDesktop -ErrorAction SilentlyContinue).Count"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if listing.stdout.strip() in ("", "0"):
        return False
    try:
        find_port()
    except PowerBiUnavailable:
        return False
    return True


def open_and_refresh():
    """
    Refresh the model, opening Desktop first if it is closed.

    Return True when this call opened Desktop, so the caller can close it
    after the export. Raise PowerBiUnavailable if the engine never answers.
    """
    if os.name != "nt":
        raise PowerBiUnavailable("Power BI Desktop runs on Windows only.")
    opened_here = not desktop_is_open()
    if opened_here:
        logger.info("Power BI Desktop is closed: opening %s", REPORT_FILE.name)
        os.startfile(str(REPORT_FILE))
    deadline = time.monotonic() + ENGINE_WAIT_SECONDS
    last_error = None
    while time.monotonic() < deadline:
        try:
            result = refresh_model(find_port())
        except (PowerBiUnavailable, subprocess.TimeoutExpired) as error:
            last_error = error
            time.sleep(ENGINE_RETRY_SECONDS)
            continue
        logger.info(
            "Power BI model refreshed: %s partitions, oldest %s, previous refresh %s",
            result["partitions"],
            result["oldest_after"],
            result["newest_before"],
        )
        return opened_here
    if opened_here:
        close_desktop()
    raise PowerBiUnavailable(f"The Power BI engine did not answer within {ENGINE_WAIT_SECONDS} s: {last_error}")


def close_desktop():
    """Close Desktop without saving. The report file is not changed."""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Process PBIDesktop -ErrorAction SilentlyContinue | Stop-Process -Force"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    logger.info("Power BI Desktop closed without saving")
