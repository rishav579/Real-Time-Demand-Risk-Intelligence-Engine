# Real-Time Demand & Risk Intelligence Engine

> **Project Stage**: Phase 3 — Analytics & Risk Intelligence  
> **Notice**: This repository is a realistic synthetic enterprise work-sample designed to showcase production-grade data modeling, analytics engineering, forecasting, and operational risk intelligence. Time-series forecasting, machine learning models, API endpoints, and dashboards will be built in subsequent phases.

---

## 1. Executive Summary & Business Problem

Retail and distribution networks operating across regional fulfillment centers and retail outlets face persistent supply chain friction:
- **Unpredictable Demand Surges**: Promotional campaigns and localized seasonality drive sharp demand spikes that standard rule-based min-max reordering fails to catch.
- **Stockout & Lost Revenue**: Critical SKUs stock out during peak velocity windows, degrading customer fill rates and brand loyalty.
- **Excess Inventory & Working Capital Lockup**: Over-ordering in low-velocity categories causes bloated holding costs, warehouse capacity strain, and markdown erosion.
- **Supplier Lead Time Volatility**: Unreliable supplier fulfillment and inbound delays amplify upstream bullwhip effects.

Traditional inventory management relies on static historical averages or disconnected spreadsheets. The **Real-Time Demand & Risk Intelligence Engine** is designed to bridge transaction-level telemetry with proactive operational decision support.

---

## 2. Why This System Exists

The system answers four fundamental operational questions:
1. **What demand is expected?** Probabilistic short-term demand forecasts across product-location nodes.
2. **Where is operational risk brewing?** Proactive detection of imminent stockouts (runout days < lead time) and excess capital accumulation.
3. **What is driving the risk?** Root-cause attribution distinguishing promotional lift, seasonality, supplier lead-time slippage, or baseline trend shifts.
4. **What should planners do next?** Ranked, actionable replenishment and inventory rebalancing recommendations.

---

## 3. Target User Personas

| Persona | Core Job-to-be-Done | Key Decision Surface |
| :--- | :--- | :--- |
| **Inventory & Replenishment Planners** | Prevent stockouts without inflating working capital. | Recommended Purchase Orders, Expedited Transfers, Buffer Adjustment. |
| **Category & Brand Managers** | Optimize promotion performance and prevent promotional stockouts. | Promo lift projections, category demand elasticity. |
| **Supply Chain Operations Leaders** | Track supplier reliability and cross-facility fulfillment risks. | Lead time variance, facility capacity utilization, fill-rate metrics. |

---

## 4. Planned End-to-End Workflow

```
[ Deterministic Synthetic Enterprise Data (Seed 42) ]
                      ↓
[ Ingestion & Data Quality Validation Layer (40 Integrity Checks) ]
                      ↓  (PASS / REJECT Gating)
[ Relational Storage (SQLite with Enforced Foreign Keys) ]
                      ↓
[ Analytical Data Marts (ABC/XYZ Segmentation, Supplier Scorecards, DoS) ]
                      ↓
[ Baseline & Statistical Time-Series Forecasting ]
                      ↓
[ Operational Risk Engine (Stockout / Excess / Lead Time Drift) ]
                      ↓
[ Business Interpretation & Recommendation Layer ]
                      ↓
[ Lightweight Operational API & Visual Dashboard ]
```

---

## 5. Current Status & Phased Roadmap

| Phase | Milestone | Scope | Status |
| :---: | :--- | :--- | :---: |
| **0** | **Foundation & Data Contract** | Schema design, Pydantic contracts, SQLite/SQLAlchemy DDL, business questions, test suite. | **Complete** |
| **1** | **Deterministic Data Engine** | Seeded synthetic generator with planted causal patterns (promotions, supplier delays, seasonality). | **Complete** |
| **2** | **Data Quality & Ingestion** | 40-check validation suite, strict ingestion gating, corrupted fixture detectors, pipeline runner. | **Complete** |
| **3** | **SQL & Statistical Analytics** | ABC/XYZ 9-cell segmentation, supplier OTIF scorecards, Days-of-Supply, 5-tier risk taxonomy. | **Complete** |
| **4** | **Forecasting Engine** | Baseline moving averages, exponential smoothing, and gradient-boosted time-series forecasting. | Planned |
| **5** | **Risk & Recommendation Engine** | Days-of-supply simulation, stockout risk scoring, reorder/rebalancing recommendation logic. | Planned |
| **6** | **Serving & Presentation** | REST API endpoints, interactive planner dashboard, and scenario-testing UI. | Planned |

---

## 6. Analytical Marts & Operational Intelligence

Phase 3 establishes the SQL-first analytical intelligence foundation over persistent relational data:

### A. ABC Revenue & XYZ Volatility Segmentation Matrix
- **ABC Pareto Classification** (Annual Gross Revenue):
  - **Class A** ($\le 80\%$ cumulative revenue): 9 SKUs, \$945,187.96 (81.31% share)
  - **Class B** ($80\% - 95\%$ cumulative revenue): 3 SKUs, \$175,519.66 (15.10% share)
  - **Class C** ($> 95\%$ cumulative revenue): 3 SKUs, \$41,784.51 (3.59% share)
- **XYZ Volatility Classification** ($CV = \frac{\sigma}{\mu}$ of daily network demand):
  - **Class X** ($CV \le 0.50$): 13 predictable baseline & staple SKUs (average $CV = 0.24$)
  - **Class Z** ($CV > 1.00$): 2 erratic/intermittent slow-moving SKUs (`PRD-HOU-003` $CV=1.02$, `PRD-HOU-004` $CV=1.06$)
- **Combined 9-Cell Segments**: `AX` (9 SKUs), `BX` (3 SKUs), `CX` (1 SKU), `CZ` (2 SKUs).

### B. Supplier OTIF Scorecards & Lead-Time Variance
- **Apex Beverage Bottlers (`SUP-001`)**: 944 delivered POs, 99.89% OTIF rate, max delay = 9 days (planted crisis PO), \$178,563.60 inbound spend.
- **Pacific Coast Essentials (`SUP-003`)**: 689 delivered POs, 100.0% OTIF rate, 0 delay days, \$172,455.60 inbound spend.
- **Artisan Snackcraft Foods (`SUP-002`)**: 713 delivered POs, 65.08% OTIF rate (avg delay 1.17 days, max delay 5 days), \$145,439.50 inbound spend.
- **National Industrial Cleaners (`SUP-004`)**: Slow-moving supplier with zero replenishment triggers due to high initial stock.

### C. Inventory Health & 5-Tier Operational Risk Taxonomy
As-of Date: **2026-12-31** (75 active facility-SKU node positions):
- **CRITICAL** ($DoS \le \text{Lead Time}$): **39 positions** (immediate stockout risk before replenishment arrival)
- **LOW BUFFER** ($\text{Lead Time} < DoS \le 1.5 \times \text{Lead Time}$): **6 positions**
- **HEALTHY** ($1.5 \times \text{Lead Time} < DoS \le 45\text{ days}$): **20 positions**
- **EXCESS** ($DoS > 90\text{ days}$): **10 positions** (e.g. `PRD-HOU-003` with 296+ days of supply)

---

## 7. Project Foundation & Structure

```
real-time-demand-risk-engine/
├── .gitignore
├── pyproject.toml
├── README.md
├── docs/
│   ├── ARCHITECTURE.md    # System architecture and data flow design
│   ├── DECISIONS.md       # Architecture Decision Records (ADRs)
│   └── ROADMAP.md         # Detailed milestone deliverables and criteria
├── src/
│   ├── analytics/         # Analytical data marts and operational risk engine
│   │   ├── __init__.py
│   │   ├── inventory_health.py # Days-of-Supply and 5-tier risk taxonomy
│   │   ├── marts.py            # Unified analytical data marts builder
│   │   ├── segmentation.py     # ABC / XYZ / ABC-XYZ matrix calculation
│   │   └── supplier.py         # Supplier scorecards, OTIF, and lead-time variance
│   ├── config/            # Environment and engine configurations
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── data/              # Schema, generator, quality validator, and ingestion pipeline
│   │   ├── __init__.py
│   │   ├── generator.py   # Deterministic data generation engine (Seed 42)
│   │   ├── ingestion.py   # Ingestion orchestrator and gating policy
│   │   ├── quality.py     # 40-check data quality validation suite
│   │   └── schema.py      # SQLAlchemy 2.0 table definitions and DDL
│   └── models/            # Pydantic validation contracts and domain entities
│       ├── __init__.py
│       └── contracts.py
└── tests/
    ├── unit/              # Configuration, contract, generator, quality, and analytics tests
    │   ├── test_config.py
    │   ├── test_contracts.py
    │   ├── test_generator.py
    │   ├── test_inventory_health.py
    │   ├── test_quality.py
    │   ├── test_segmentation.py
    │   └── test_supplier_analytics.py
    └── integration/       # DDL, generation, ingestion, and data marts integration tests
        ├── test_analytical_marts.py
        ├── test_data_generation.py
        ├── test_ingestion.py
        └── test_schema_ddl.py
```

---

## 8. Getting Started & Verification

### Prerequisites
- Python 3.10+

### Run End-to-End Pipeline & Analytical Marts
```bash
# 1. Ingest clean data and seed SQLite database
python -m src.data.ingestion

# 2. Execute full test suite (61 tests)
python -m pytest
```
