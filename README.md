# Operations Risk & Loss Prevention Dashboard

A Python-based operations decision-support system that analyzes facility-level resource utilization, loss, and cost leakage.  
The tool computes operational KPIs, classifies site risk using transparent rules, and delivers both executive-ready reports and an interactive analytics dashboard.

This project mirrors how operations analytics tools are structured in enterprise and public-sector environments, with an emphasis on explainability, auditability, and decision support.


## What This Tool Does

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
- Resource planning
- Process improvement prioritization



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
│   └── raw/
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

### Install dependencies
pip install -r requirements.txt

### Generate executive PDF report
python src/main.py

Output:
outputs/site_resource_ops_report.pdf

### Launch interactive dashboard
streamlit run src/app.py





## Design Choices

### Rule-Based Classification
- Chosen for transparency, auditability, and explainability.
This approach is well-suited for regulated and public-sector environments where decisions must be traceable.

### Synthetic Data
- The dataset is synthetic to demonstrate system logic and structure without exposing proprietary information.
Data generation is deterministic and reproducible.

### Separation of Concerns
- Data processing, decision logic, reporting, and user interface layers are fully decoupled.
This enables future extension without modifying the core analytics engine.

## Limitations
- Thresholds and rules are illustrative and would require calibration using real operational data.

- The system is descriptive and diagnostic, not predictive.

- External drivers (e.g., weather, labor availability, supplier variability) are not explicitly modeled.

## Future Enhancements

- Predictive risk scoring

- Scenario simulation (what-if analysis)

- Automated alerting

- Integration with real-time data sources

- Role-based access and report templates

## Summary

This project demonstrates how operational data can be translated into:

- Clear risk signals

- Actionable recommendations

- Executive- and analyst-ready artifacts

- It reflects real-world practices used in operations, logistics, and risk management teams.
