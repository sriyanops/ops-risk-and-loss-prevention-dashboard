# src/main.py
from __future__ import annotations

from src.config import REPORT_PATH
from src.io import load_daily_data
from src.kpis import compute_kpis
from src.rules import classify_sites
from src.report_pdf import build_pdf



def main() -> None:
    # Load + validate data (single source of truth)
    df = load_daily_data()

    # Compute KPIs
    kpis = compute_kpis(df)

    # Classify sites (risk + actions)
    site_status = classify_sites(
        kpis.by_site,
        kpis.by_site_day,
        kpis.loss_mix_by_site,
    )

    # Console summary (quick verification)
    print("\n=== OVERALL ===")
    print(kpis.overall.to_string(index=False))

    print("\n=== SITE STATUS (TOP RISK FIRST) ===")
    print(site_status.head(12).to_string(index=False))

    # Ensure reports directory exists
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Build PDF report
    build_pdf(
        output_path=str(REPORT_PATH),
        overall=kpis.overall,
        by_site=kpis.by_site,
        by_site_day=kpis.by_site_day,
        loss_mix_by_site=kpis.loss_mix_by_site,
        site_status=site_status,
    )

    print(f"\nWrote PDF: {REPORT_PATH}")


if __name__ == "__main__":
    main()
