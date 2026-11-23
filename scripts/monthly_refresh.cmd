@echo off
rem Monthly rebuild of the data layer, run by the Windows Task Scheduler.
rem It leaves out Excel and Power BI (--skip-office): the annex and the reports
rem keep describing the last full run, and the log says so.
rem The output goes to logs\monthly_refresh.log, which is not versioned.
cd /d "%~dp0.."
if not exist logs mkdir logs
echo ==== %date% %time% >> logs\monthly_refresh.log
python -m src.pipeline.refresh --skip-office >> logs\monthly_refresh.log 2>&1
set RC=%errorlevel%
echo exit code %RC% >> logs\monthly_refresh.log
if %RC%==0 (
    msg %username% /TIME:600 "Donnees reconstruites. Etape suivante : python -m src.pipeline.full_refresh" 2>nul
) else (
    msg %username% /TIME:600 "La reconstruction mensuelle a echoue. Voir logs\monthly_refresh.log" 2>nul
)
