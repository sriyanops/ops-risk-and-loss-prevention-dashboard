# src/config.py
from __future__ import annotations

from pathlib import Path
import os

# ============================================================
# Data environment configuration
# ============================================================
# Default: GitHub / portfolio demo data
# Local dev override: set OPS_DATA_DIR=raw
#
# PowerShell (local):
#   $env:OPS_DATA_DIR="raw"
#   python -m src.main
# ============================================================

DATA_ENV = os.getenv("OPS_DATA_DIR", "sample")

DATA_DIR = Path("data") / DATA_ENV
REPORTS_DIR = Path("reports")

SITE_MASTER_PATH = DATA_DIR / "site_master.csv"
DAILY_DATA_PATH = DATA_DIR / "daily_site_resource.csv"

REPORT_FILENAME = "site_resource_ops_report.pdf"
REPORT_PATH = REPORTS_DIR / REPORT_FILENAME

SCREENSHOTS_DIR = Path("docs") / "screenshots"

# ============================================================
# Column names (single source of truth)
# ============================================================

COL_SITE_ID = "site_id"
COL_DATE = "date"

COL_PLANNED_UNITS = "planned_units"
COL_ACTUAL_UNITS = "actual_units"
COL_USABLE_UNITS = "usable_units"
COL_DISPOSED_UNITS = "disposed_units"
COL_UNIT_COST = "unit_cost"
COL_LOSS_REASON = "loss_reason"

COL_STAFFING_FLAG = "staffing_shortfall_flag"
COL_SUPPLIER_DELAY_FLAG = "supplier_delay_flag"
COL_TEMP_EXCURSION_FLAG = "temp_excursion_flag"

# ============================================================
# Risk classification thresholds (illustrative defaults)
# ============================================================

WATCH_LOSS_RATE = 0.055          # 5.5%
INTERVENTION_LOSS_RATE = 0.085   # 8.5%

WATCH_COST_LEAKAGE = 25_000.0
INTERVENTION_COST_LEAKAGE = 50_000.0

# Shock / anomaly detection
SHOCK_ZSCORE_THRESHOLD = 2.5
