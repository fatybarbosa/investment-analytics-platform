"""
config.py

Configuration centrale du projet Investment Analytics Platform.

Ce fichier centralise :

- la devise de reporting et les paramètres globaux ;
- les chemins utilisés dans le projet.

Toute modification de structure ou de chemin doit être réalisée ici.
"""

from pathlib import Path

# ============================================================================
# REPORTING
# ============================================================================

REPORTING_CURRENCY = "CHF"

# ============================================================================
# ANALYSIS PARAMETERS
# ============================================================================

# Annualisation des séries mensuelles. Il n'y a pas de série quotidienne publiée.

MONTHS_PER_YEAR = 12

# Phase 9. These are shock parameters, not IPS limits.
MARKET_SHOCK_RETURN = -0.20
RATE_SHOCK_ANNUAL_POINTS = 2.0
RECESSION_SHOCK_RETURN = -0.03
RECESSION_SHOCK_MONTHS = 6
VOLATILITY_SHOCK_MULTIPLIER = 1.5

# ============================================================================
# PROJECT ROOT
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def source_id(path):
    """The project-relative, forward-slash name under which a file is cited in the number check."""
    return Path(path).relative_to(PROJECT_ROOT).as_posix()

# ============================================================================
# DATA
# ============================================================================

DATA_DIR = PROJECT_ROOT / "data"

RAW_DIR = DATA_DIR / "01_raw"
PROCESSED_DIR = DATA_DIR / "02_processed"
UNIVERSE_DIR = DATA_DIR / "03_universe"

# ---------------------------------------------------------------------------
# RAW DATASETS
# ---------------------------------------------------------------------------

BENCHMARK = RAW_DIR / "benchmark"
MARKET = RAW_DIR / "market"
MACRO = RAW_DIR / "macro"
FX = RAW_DIR / "fx"
ODD = RAW_DIR / "odd"
# Cash returned to holders that the market data does not carry, written by hand
# from the company's own publication, one row per operation with its source.
CAPITAL_RETURNS_FILE = RAW_DIR / "corporate_actions" / "capital_returns.csv"

# ---------------------------------------------------------------------------
# PROCESSED DATASETS
# ---------------------------------------------------------------------------

PROCESSED_MARKET = PROCESSED_DIR / "market"
PROCESSED_MACRO = PROCESSED_DIR / "macro"

# ---------------------------------------------------------------------------
# UNIVERSE DATASETS
# ---------------------------------------------------------------------------

ELIGIBLE_UNIVERSE = UNIVERSE_DIR / "eligible"

# ---------------------------------------------------------------------------
# PORTFOLIO DATASETS
# ---------------------------------------------------------------------------

PORTFOLIO_DATA = DATA_DIR / "04_portfolios"
MONITORING_DATA = DATA_DIR / "05_monitoring"
PERFORMANCE_DATA = DATA_DIR / "06_performance"
RISK_DATA = DATA_DIR / "07_risk"
STRESS_DATA = DATA_DIR / "08_stress"

# ============================================================================
# DATABASE
# ============================================================================

DATABASE_DIR = PROJECT_ROOT / "database"

DATABASE_FILE = DATABASE_DIR / "sdg_investment.db"

# ============================================================================
# REPORTS
# ============================================================================

REPORTS_DIR = PROJECT_ROOT / "reports"

DASHBOARDS_DIR = PROJECT_ROOT / "dashboards"

POWERBI = DASHBOARDS_DIR / "powerbi"

MONITORING_REPORTS = REPORTS_DIR / "monitoring"
PERFORMANCE_REPORTS = REPORTS_DIR / "performance"
RISK_REPORTS = REPORTS_DIR / "risk"
STRESS_REPORTS = REPORTS_DIR / "stress"
EXCEL_REPORTS = REPORTS_DIR / "excel"

MANAGEMENT_REPORTS = (
    REPORTS_DIR / "management"
)

EXECUTIVE_REPORTS = (
    REPORTS_DIR / "executive"
)

# Phase 11b. One report for CLIENT001, one for the manager of the same books.
CLIENT_REPORTS = REPORTS_DIR / "client"

# ============================================================================
# AUDIT & GOVERNANCE
# ============================================================================

AUDIT_DIR = PROJECT_ROOT / "audit"

SOURCE_REGISTRY_FILE = (
    AUDIT_DIR / "source_registry.xlsx"
)

ACQUISITION_LOG_FILE = (
    AUDIT_DIR / "acquisition_log.xlsx"
)

DATA_CONTROL_CENTER_FILE = (
    AUDIT_DIR / "data_control_center.xlsx"
)

# ============================================================================
# LOGGING
# ============================================================================

LOGS_DIR = PROJECT_ROOT / "logs"

TECHNICAL_LOG = LOGS_DIR / "technical.log"

# ============================================================================
# MARKET DATA
# ============================================================================

MARKET_HISTORY_YEARS = 10
# Months of past returns used to set the next quarter's weights.
# Five years is the risk horizon. The month being scored is excluded.
ESTIMATION_MONTHS = 60
# Dividends. A single dividend above this share of the close is not on the same
# basis as the price: a name with one inside the measured window leaves the books.
# The largest regular or special dividend of the other eligible names is under 9%.
DIVIDEND_YIELD_LIMIT = 0.10
# A split is recorded as not adjusted when the price moves by its factor and the
# factor is further than this from one.
SPLIT_MINIMUM_MOVE = 0.03
# The adjusted close is recorded as ignoring a dividend when it applies less than
# this share of it.
ADJUSTED_DIVIDEND_SHARE = 0.3
# CLIENT001 IPS limits for a long-only equity mandate.
# Issuer 5%, sector 20%, region 50%, listing currency 40%.
# The written sector limit of the IPS is 20%. On the Eligible names with a
# complete CHF history, a fully invested long-only book cannot respect it:
# the sectors cannot hold 100% between them under the issuer cap. The books
# are therefore built with a WORKING sector cap of 40%. The working cap is not
# a limit of the client. It has not been approved by the client, and the
# reports show the breach of the written limit instead of hiding it.
# Issuer, region, currency, and the 25–40 name band are unchanged.
# The optimized books keep 25 to 40 names. Gross turnover is at most
# 50% a year, applied as 12.5% at each quarterly rebalance.
ISSUER_WEIGHT_CAP = 0.05
IPS_SECTOR_WEIGHT_CAP = 0.20
SECTOR_WEIGHT_CAP = 0.40
ZONE_WEIGHT_CAP = 0.50
CURRENCY_WEIGHT_CAP = 0.40
MIN_POSITIONS = 25
MAX_POSITIONS = 40
QUARTERLY_TURNOVER_CAP = 0.125
# A weight above a cap by less than this is on the cap, not over it.
CAP_TOLERANCE = 1e-8
# A weight at or below this floor is optimizer dust, not a line.
# Monitoring uses the same floor when it counts invested names.
POSITION_WEIGHT_FLOOR = 1e-8

# Phase 11 reporting references. They are read by the automated comments.
# They do not choose a weight and they are not used by the optimizer.
# IPS: ex ante tracking error target against the investable proxy.
TRACKING_ERROR_TARGET = 0.08
# Client profile: a temporary loss is accepted beyond this level.
# The profile says this level does not, by itself, trigger a sale.
TEMPORARY_LOSS_REFERENCE = 0.30
# Reporting watch level, as a share of a written cap. This is a reading
# threshold of the report. It is not a limit of the mandate.
REPORTING_WATCH_RATIO = 0.95
# The name recorded in the published Office files, whatever the Office account of the machine.
PROJECT_AUTHOR = "Faty Barbosa"
# Reading thresholds of the recommendations. They choose no weight.
# Share of variance above which a book is said to follow the fund for the most part.
MARKET_LINK_MAJORITY = 0.5
# Student t of the mean monthly gap with the fund below which a lead is not
# called established. About the usual two-sided 5 % level.
SIGNIFICANCE_T = 2.0
# The executive report must fit in this number of pages.
EXECUTIVE_REPORT_MAX_PAGES = 3