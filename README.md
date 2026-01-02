# Operations Risk & Loss Prevention Dashboard

A Python-based operations decision-support system for analyzing facility-level resource utilization, loss, and cost leakage.  
The tool computes operational KPIs, classifies site risk using transparent rules, and delivers both executive-ready reports and an interactive analytics dashboard.

This project is designed for operations analysts, operations managers, and public-sector reviewers, and reflects how internal operations analytics tools are typically structured in enterprise and regulated environments — with an emphasis on explainability, auditability, and actionable decision support.


## What This Tool Does

### Problem This Tool Solves

Operational leaders often lack a consolidated view of emerging risk drivers across sites until losses have already materialized. Data is typically fragmented across metrics, making it difficult to identify which locations require attention and what actions should be prioritized. This tool aggregates operational indicators into structured risk tiers and decision outputs, enabling earlier intervention and more consistent, data-driven resource allocation.
The system ingests daily, site-level operational data and produces:

- Utilization and loss KPIs  
- Cost leakage estimates  
- Rule-based site risk classification:
  - **Normal**
  - **Watch**
  - **Intervention Required**
- Loss driver attribution (why losses are occurring)
- Actionable recommendations tied to dominant loss drivers

The outputs are designed to support:
- Operations reviews
- Risk identification
- Resource planning decisions
- Process improvement prioritization



## Tech Stack

- **Python** — core language
- **Pandas** — data manipulation and KPI computation
- **NumPy** — numerical operations
- **Matplotlib** — static visualizations for executive reporting
- **ReportLab** — programmatic PDF report generation
- **Streamlit** — interactive analytics dashboard

## Inputs

The tool operates on tabular, site-level operational data, where each row represents a site-day observation.
- [`site_master.csv`](data/sample/site_master.csv) — site metadata  
- [`daily_site_resource.csv`](data/sample/daily_site_resource.csv) — daily site-level operational observations



Key inputs include:
- Site identifier and metadata
- Resource utilization metrics
- Loss or waste quantities
- Cost parameters
- Observation date

> **DISCLAIMER:**  
> The included datasets are synthetic, created to demonstrate system logic and structure without exposing proprietary or sensitive operational data.  
> Data generation is deterministic and reproducible.


## Key Outputs

### 1. Executive PDF Report
- One-command generation
- Executive summary
- Overall KPIs
- Top-risk sites with recommended actions
- Cost leakage trends
- Loss driver mix

### 2. Interactive Dashboard (Streamlit)
- KPI summary tiles
- Site risk table with visual status indicators
- Cost leakage and loss-rate trends
- Loss driver mix
- Site-level drilldowns


## Project Structure

```text
site_resource_ops_tool/
├── data/
│   └── sample/
│       ├── site_master.csv
│       └── daily_site_resource.csv
├── outputs/
│   └── site_resource_ops_report.pdf
├── src/
│   ├── app.py           # Streamlit dashboard
│   ├── kpis.py          # KPI computation logic
│   ├── rules.py         # Risk classification & actions
│   ├── report_pdf.py    # Executive PDF generation
│   └── main.py          # Orchestration entry point
├── requirements.txt
└── README.md

```

## How to Run
> Note: All commands should be run from repository root. This project uses a `src/`-based layout. Some environments require the repository root to be added to `PYTHONPATH`.



### Install dependencies

All required Python dependencies are listed in [`requirements.txt`](requirements.txt).

```
python -m pip install -r requirements.txt
```
### Generate executive PDF report

**macOS/Linux** - ```PYTHONPATH="$(pwd)" python -m src.main```

**Windows** - ```python -m src.main```


## Output:

reports/site_resource_ops_report.pdf

## Launch interactive dashboard


**macOS / Linux** - 
```PYTHONPATH="$(pwd)" python3 -m streamlit run src/app.py``` 

**Windows** - ```$env:PYTHONPATH="."streamlit run src/app.py ```
> By default, the dashboard uses the sample dataset in data/sample/.
To run against local development data, set OPS_DATA_DIR=raw.


## Screenshots & Sample Outputs


### Interactive Dashboard

![Dashboard Screenshot](docs/screenshots/dashboard%20screenshot.png)

### KPI tables

![KPI Screenshot](docs/screenshots/kpi%20screenshot.png)

### Generated PDF report

[`site_resource_ops_report.pdf`](reports/site_resource_ops_report.pdf) 

## Design Choices

### Rule-Based Classification

Rule-based logic was chosen for transparency, auditability, and explainability.
This approach aligns with enterprise and public-sector environments where decisions must be traceable and defensible.

### Synthetic Data

Synthetic data is used to demonstrate system behavior without exposing real operational data.
The focus is on logic, structure, and decision flow, not the data source itself.

### Separation of Concerns

Data processing, decision logic, reporting, and user interface layers are fully decoupled.
This allows future extensions without modifying the core analytics engine.

### Limitations

Thresholds and rules are illustrative and would require calibration using real operational data.

The system is descriptive and diagnostic, not predictive.

External drivers (e.g., weather, labor availability, supplier variability) are not explicitly modeled.

## Future Enhancements

Predictive risk scoring

Scenario simulation (what-if analysis)

Automated alerting

Integration with real-time data sources

Role-based access and configurable report templates

## Summary

This project demonstrates how operational data can be translated into:

Clear risk signals

Actionable recommendations

Executive- and analyst-ready artifacts

It reflects real-world practices used in operations, logistics, and risk management teams.

