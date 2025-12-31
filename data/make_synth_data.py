# data/make_synth_data.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SynthConfig:
    seed: int = 42
    start_date: str = "2025-01-01"
    end_date: str = "2025-03-31"  # inclusive
    n_sites: int = 12
    site_types: tuple[str, ...] = ("facility", "warehouse", "service_site")

    # Baseline behavior
    base_planned_units: tuple[int, int] = (800, 2200)  # per day
    unit_cost_range: tuple[float, float] = (2.25, 12.50)

    # Loss & variance behavior
    typical_loss_rate_range: tuple[float, float] = (0.02, 0.06)  # 2–6%
    bad_site_loss_rate_range: tuple[float, float] = (0.08, 0.16)  # 8–16%
    bad_site_fraction: float = 0.25

    # Shocks (flags) that worsen loss
    p_staffing_shortfall: float = 0.08
    p_supplier_delay: float = 0.06
    p_temp_excursion: float = 0.04


LOSS_REASONS = ("overproduction", "spoilage", "damage", "timing_mismatch")


def _date_range_inclusive(start: str, end: str) -> pd.DatetimeIndex:
    return pd.date_range(start=start, end=end, freq="D")


def make_site_master(cfg: SynthConfig, rng: np.random.Generator) -> pd.DataFrame:
    site_ids = [f"S{str(i).zfill(3)}" for i in range(1, cfg.n_sites + 1)]
    site_type = rng.choice(cfg.site_types, size=cfg.n_sites, replace=True)
    capacity_units = rng.integers(2500, 6500, size=cfg.n_sites)
    operating_days_per_week = rng.integers(5, 7 + 1, size=cfg.n_sites)

    # Mark a subset of sites as "bad" (structural loss problem)
    n_bad = max(1, int(round(cfg.n_sites * cfg.bad_site_fraction)))
    bad_sites = set(rng.choice(site_ids, size=n_bad, replace=False).tolist())

    df = pd.DataFrame(
        {
            "site_id": site_ids,
            "site_type": site_type,
            "capacity_units": capacity_units,
            "operating_days_per_week": operating_days_per_week,
            "is_structurally_high_loss": [sid in bad_sites for sid in site_ids],
        }
    )
    return df


def make_daily_fact(cfg: SynthConfig, sites: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    dates = _date_range_inclusive(cfg.start_date, cfg.end_date)
    n_days = len(dates)

    rows = []
    for _, s in sites.iterrows():
        sid = s["site_id"]
        cap = int(s["capacity_units"])
        is_bad = bool(s["is_structurally_high_loss"])

        # Per-site baseline
        base_plan = rng.integers(cfg.base_planned_units[0], cfg.base_planned_units[1] + 1)
        unit_cost = float(rng.uniform(cfg.unit_cost_range[0], cfg.unit_cost_range[1]))

        # Loss baseline (bad sites are consistently worse)
        if is_bad:
            base_loss_rate = float(rng.uniform(cfg.bad_site_loss_rate_range[0], cfg.bad_site_loss_rate_range[1]))
        else:
            base_loss_rate = float(rng.uniform(cfg.typical_loss_rate_range[0], cfg.typical_loss_rate_range[1]))

        for d in dates:
            # Flags (operational shocks)
            staffing_shortfall_flag = rng.random() < cfg.p_staffing_shortfall
            supplier_delay_flag = rng.random() < cfg.p_supplier_delay
            temp_excursion_flag = rng.random() < cfg.p_temp_excursion

            # Planned units with mild weekday seasonality
            weekday = d.weekday()  # 0=Mon
            weekday_factor = 1.0 + (0.06 if weekday in (4, 5) else 0.0)  # Fri/Sat slightly higher
            planned_units = int(round(base_plan * weekday_factor))

            # Actual units deviate from plan (variance)
            # supplier delay tends to reduce actual; over-ordering tends to increase
            variance = rng.normal(loc=0.0, scale=0.06)  # ~6% std dev
            if supplier_delay_flag:
                variance -= rng.uniform(0.05, 0.12)
            actual_units = int(round(planned_units * (1.0 + variance)))

            # Clamp to realistic bounds
            actual_units = max(0, min(actual_units, cap))

            # Loss rate increases with shocks
            loss_rate = base_loss_rate
            if staffing_shortfall_flag:
                loss_rate += rng.uniform(0.01, 0.03)
            if temp_excursion_flag:
                loss_rate += rng.uniform(0.02, 0.05)
            if supplier_delay_flag:
                loss_rate += rng.uniform(0.005, 0.02)

            loss_rate = min(max(loss_rate, 0.0), 0.35)

            disposed_units = int(round(actual_units * loss_rate))
            disposed_units = min(disposed_units, actual_units)
            usable_units = actual_units - disposed_units

            # Pick a dominant loss reason (weighted by flags)
            weights = np.array([0.40, 0.20, 0.20, 0.20], dtype=float)
            if temp_excursion_flag:
                weights = np.array([0.25, 0.50, 0.15, 0.10], dtype=float)  # spoilage dominates
            elif staffing_shortfall_flag:
                weights = np.array([0.30, 0.20, 0.20, 0.30], dtype=float)  # timing mismatch rises
            elif supplier_delay_flag:
                weights = np.array([0.25, 0.20, 0.15, 0.40], dtype=float)  # timing mismatch dominates

            loss_reason = rng.choice(LOSS_REASONS, p=weights / weights.sum())

            rows.append(
                {
                    "date": d.date().isoformat(),
                    "site_id": sid,
                    "planned_units": planned_units,
                    "actual_units": actual_units,
                    "usable_units": usable_units,
                    "disposed_units": disposed_units,
                    "unit_cost": round(unit_cost, 2),
                    "loss_reason": loss_reason,
                    "staffing_shortfall_flag": int(staffing_shortfall_flag),
                    "supplier_delay_flag": int(supplier_delay_flag),
                    "temp_excursion_flag": int(temp_excursion_flag),
                }
            )

    df = pd.DataFrame(rows)

    # Basic integrity checks
    if (df["usable_units"] + df["disposed_units"] != df["actual_units"]).any():
        raise ValueError("Integrity check failed: usable + disposed must equal actual.")

    return df


def main() -> None:
    cfg = SynthConfig()
    rng = np.random.default_rng(cfg.seed)

    root = Path(__file__).resolve().parents[1]
    out_dir = root / "data" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    sites = make_site_master(cfg, rng)
    fact = make_daily_fact(cfg, sites, rng)

    sites_path = out_dir / "site_master.csv"
    fact_path = out_dir / "daily_site_resource.csv"

    sites.to_csv(sites_path, index=False)
    fact.to_csv(fact_path, index=False)

    print(f"Wrote: {sites_path}")
    print(f"Wrote: {fact_path}")
    print(f"Rows: {len(fact):,} | Sites: {len(sites)} | Dates: {cfg.start_date} → {cfg.end_date}")


if __name__ == "__main__":
    main()
