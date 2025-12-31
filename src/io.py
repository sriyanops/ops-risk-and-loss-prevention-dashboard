# src/io.py
from __future__ import annotations

from typing import Iterable
import pandas as pd

from src.config import (
    SITE_MASTER_PATH,
    DAILY_DATA_PATH,
    COL_SITE_ID,
    COL_DATE,
    COL_PLANNED_UNITS,
    COL_ACTUAL_UNITS,
    COL_DISPOSED_UNITS,
    COL_UNIT_COST,
    COL_LOSS_REASON,
)


def _validate_columns(df: pd.DataFrame, required: Iterable[str], name: str) -> None:
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(
            f"{name} is missing required columns: {sorted(missing)}. "
            f"Found columns: {list(df.columns)}"
        )


def load_site_master(path: str | None = None) -> pd.DataFrame:
    """
    Load site metadata.
    """
    csv_path = path or SITE_MASTER_PATH
    df = pd.read_csv(csv_path)

    _validate_columns(
        df,
        required=[COL_SITE_ID],
        name="site_master.csv",
    )

    return df


def load_daily_data(path: str | None = None) -> pd.DataFrame:
    """
    Load daily site-level operational data and enforce schema.
    """
    csv_path = path or DAILY_DATA_PATH
    df = pd.read_csv(csv_path)

    required_columns = [
        COL_SITE_ID,
        COL_DATE,
        COL_PLANNED_UNITS,
        COL_ACTUAL_UNITS,
        COL_DISPOSED_UNITS,
        COL_UNIT_COST,
        COL_LOSS_REASON,
    ]

    _validate_columns(
        df,
        required=required_columns,
        name="daily_site_resource.csv",
    )

    # Parse dates
    df[COL_DATE] = pd.to_datetime(df[COL_DATE], errors="raise")

    return df
