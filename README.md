# Real-Time Demand & Risk Intelligence Engine

> **Project Stage**: Phase 7 — Production Readiness & Security Hardening (Complete Production-Grade Decision Engine)  
> **Notice**: This repository is a realistic synthetic enterprise work-sample showcasing production-grade data modeling, analytics engineering, multi-horizon demand forecasting, operational risk intelligence, and interactive decision support.

---

## 1. Executive Summary & Business Problem

Retail and distribution networks operating across regional fulfillment centers and retail outlets face persistent supply chain friction:
- **Unpredictable Demand Surges**: Promotional campaigns and localized seasonality drive sharp demand spikes that standard rule-based min-max reordering fails to catch.
- **Stockout & Lost Revenue**: Critical SKUs stock out during peak velocity windows, degrading customer fill rates and brand loyalty.
- **Excess Inventory & Working Capital Lockup**: Over-ordering in low-velocity categories causes bloated holding costs, warehouse capacity strain, and markdown erosion.
- **Supplier Lead Time Volatility**: Unreliable supplier fulfillment and inbound delays amplify upstream bullwhip effects.

Traditional inventory management relies on static historical averages or disconnected spreadsheets. The **Real-Time Demand & Risk Intelligence Engine** bridges transaction-level telemetry with proactive operational decision support over daily batch snapshots (`as_of_date`).

> **Operational Architecture Note**: The system provides interactive decision support over deterministic daily batch snapshots. Analytics, multi-horizon demand forecasting, and prescriptive risk engines execute in-memory queries against a relational snapshot database to deliver instant operational recommendations for replenishment planners.

---

## 2. Why This System Exists

The system answers four fundamental operational questions:
1. **What demand is expected?** Probabilistic multi-horizon demand forecasts across product-location nodes.
2. **Where is operational risk brewing?** Proactive detection of imminent stockouts (runout days < lead time) and excess capital accumulation.
3. **What is driving the risk?** Root-cause attribution distinguishing promotional lift, seasonality, supplier lead-time slippage, or baseline trend shifts.
4. **What should planners do next?** Ranked, actionable replenishment recommendations (Supplier POs and DC-to-Store expedited transfers).

---

## 3. Target User Personas

| Persona | Core Job-to-be-Done | Key Decision Surface |
| :--- | :--- | :--- |
| **Inventory & Replenishment Planners** | Prevent stockouts without inflating working capital. | Recommended Purchase Orders, Expedited Transfers, Buffer Adjustment. |
| **Category & Brand Managers** | Optimize promotion performance and prevent promotional stockouts. | Promo lift projections, category demand elasticity. |
| **Supply Chain Operations Leaders** | Track supplier reliability and cross-facility fulfillment risks. | Lead time variance, facility capacity utilization, fill-rate metrics. |

---

## 4. End-to-End System Architecture

```
[ Deterministic Synthetic Enterprise Data (Seed 42) ]
                      ↓
[ Ingestion & Data Quality Validation Layer (40 Integrity Checks) ]
                      ↓  (PASS / REJECT Gating)
[ Relational Storage (SQLite with Enforced Foreign Keys) ]
                      ↓
[ Analytical Data Marts (ABC/XYZ Segmentation, Supplier Scorecards, DoS) ]
                      ↓
[ Multi-Horizon Demand Forecasting (LightGBM vs Baselines) ]
                      ↓
[ Daily Inventory Simulation & Runout Date Engine ]
                      ↓
[ Predictive Risk Engine & Root-Cause Attribution ]
                      ↓
[ Prescriptive Replenishment Engine (Supplier POs & DC Transfers) ]
                      ↓
[ FastAPI REST API Service ]  ←→  [ Interactive Streamlit Dashboard ]
```

---

## 5. Phased Roadmap & Completed Milestones

| Phase | Milestone | Scope | Status |
| :---: | :--- | :--- | :---: |
| **0** | **Foundation & Data Contract** | Schema design, Pydantic contracts, SQLite/SQLAlchemy DDL, business questions, test suite. | **Complete** |
| **1** | **Deterministic Data Engine** | Seeded synthetic generator with planted causal patterns (promotions, supplier delays, seasonality). | **Complete** |
| **2** | **Data Quality & Ingestion** | 40-check validation suite, strict ingestion gating, corrupted fixture detectors, pipeline runner. | **Complete** |
| **3** | **SQL & Statistical Analytics** | ABC/XYZ 9-cell segmentation, supplier OTIF scorecards, Days-of-Supply, 5-tier risk taxonomy. | **Complete** |
| **4** | **Forecasting Engine** | Multi-horizon demand forecasting (7d, 14d, 30d), strict chronological splits, LightGBM vs. Baselines. | **Complete** |
| **5** | **Risk & Recommendation Engine** | Daily simulation, tiered safety stock ($Z=2.05$), root-cause attribution, POs & DC transfers. | **Complete** |
| **6** | **Serving & Presentation** | FastAPI REST endpoints, OpenAPI schemas, and interactive Streamlit planner dashboard. | **Complete** |
| **7** | **Production Hardening & Security** | API Key authentication, environment CORS, container health probes, and structured logging. | **Complete** |

---

## 6. REST API Service & Endpoints

The API is built on **FastAPI** and provides typed, deterministic operational queries:

| Method | Endpoint | Description | Query Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Service health, version, database connectivity, and reference date. | None |
| `GET` | `/summary` | High-level executive KPIs across network inventory, risks, and forecasts. | None |
| `GET` | `/forecast` | Daily point demand forecasts from champion LightGBM model. | `location_id`, `product_id`, `horizon_days` |
| `GET` | `/risk` | Predictive stockout risk scores, days-to-runout, and root causes. | `location_id`, `product_id`, `risk_tier` |
| `GET` | `/inventory` | Baseline inventory positions, 30-day demand averages, and Days-of-Supply. | `location_id`, `product_id` |
| `GET` | `/recommendations` | Prescriptive replenishment recommendations (DC transfers & POs). | `location_id`, `product_id`, `action_type`, `priority_tier` |
| `GET` | `/docs` | Interactive Swagger / OpenAPI documentation UI. | None |

### Representative Response (`GET /summary`)
```json
{
  "as_of_date": "2026-12-31",
  "total_locations": 5,
  "total_products": 15,
  "total_node_positions": 75,
  "critical_stockout_risks": 26,
  "high_stockout_risks": 8,
  "medium_stockout_risks": 8,
  "low_stockout_risks": 33,
  "total_capital_at_risk": 5149.75,
  "total_annual_holding_cost": 1029.95,
  "champion_model_name": "LightGBM",
  "champion_model_wape": 0.1097,
  "total_recommendations": 48,
  "dc_transfer_recommendations": 12,
  "purchase_order_recommendations": 29,
  "hold_order_recommendations": 7,
  "urgent_priority_recommendations": 24
}
```

---

## 7. Interactive Decision Intelligence Dashboard

The **Streamlit** dashboard (`src/ui/app.py`) provides an interactive operational interface across 5 core views:
1. **📊 Executive Overview**: Real-time KPI summary cards, stockout vs. excess distribution charts, and top urgent action alerts.
2. **📈 Forecast Explorer**: Interactive time-series visualizer comparing true customer demand against LightGBM multi-horizon forecasts with horizon sliders and error metrics.
3. **🚨 Risk Explorer**: 75-node operational risk grid with multi-tier filters and deterministic root-cause breakdown.
4. **📋 Recommendation Center**: Prioritized action cards for expedited DC lateral transfers (2-day transit) and supplier purchase orders with full mathematical context and decision rationale.
5. **🔍 SKU Drill-Down**: Facility-specific daily balance simulation showing step-by-step buffer erosion, inbound deliveries, and exact runout date.

---

## 8. Project Structure

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
│   ├── api/               # FastAPI REST service and schemas
│   │   ├── __init__.py
│   │   ├── main.py             # Application entrypoint & CORS middleware
│   │   ├── routes.py           # REST endpoints
│   │   ├── schemas.py          # Pydantic request/response models
│   │   └── service.py          # Cached IntelligenceService manager
│   ├── config/            # Environment and engine configurations
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── data/              # Schema, generator, quality validator, and ingestion pipeline
│   │   ├── __init__.py
│   │   ├── generator.py   # Deterministic data generation engine (Seed 42)
│   │   ├── ingestion.py   # Ingestion orchestrator and gating policy
│   │   ├── quality.py     # 40-check data quality validation suite
│   │   └── schema.py      # SQLAlchemy 2.0 table definitions and DDL
│   ├── forecasting/       # Multi-horizon demand forecasting and baseline benchmarks
│   │   ├── __init__.py
│   │   ├── baselines.py   # Naive, Seasonal Naive, Exponential Smoothing
│   │   ├── evaluate.py    # WAPE, MAE, RMSE, Bias, and multi-horizon benchmarks
│   │   ├── features.py    # Leakage-free lag, rolling, calendar, and promo features
│   │   ├── model.py       # LightGBM multi-horizon demand forecasting regressor
│   │   └── splits.py      # Strict chronological train/val/test splitter
│   ├── models/            # Pydantic validation contracts and domain entities
│   │   ├── __init__.py
│   │   └── contracts.py
│   ├── risk/              # Predictive risk and prescriptive replenishment engine
│   │   ├── __init__.py
│   │   ├── attribution.py     # Deterministic 6-category root-cause attribution
│   │   ├── recommendations.py # Prescriptive PO and DC-to-Store transfer generator
│   │   ├── risk_scoring.py    # 0-100 stockout risk score & capital-at-risk
│   │   ├── safety_stock.py    # Multi-tier ABC safety stock & ROP calculator
│   │   └── simulation.py      # Daily inventory discrete balance & runout engine
│   └── ui/                # Streamlit Decision Intelligence Dashboard
│       ├── __init__.py
│       └── app.py         # Multi-page interactive dashboard
└── tests/
    ├── unit/              # Config, contract, generator, quality, analytics, forecasting, risk, api
    │   ├── test_api_schemas.py
    │   ├── test_api_service.py
    │   ├── test_attribution.py
    │   ├── test_baselines.py
    │   ├── test_config.py
    │   ├── test_contracts.py
    │   ├── test_evaluate.py
    │   ├── test_features.py
    │   ├── test_generator.py
    │   ├── test_inventory_health.py
    │   ├── test_model.py
    │   ├── test_quality.py
    │   ├── test_recommendations.py
    │   ├── test_risk_scoring.py
    │   ├── test_safety_stock.py
    │   ├── test_segmentation.py
    │   ├── test_simulation.py
    │   ├── test_splits.py
    │   └── test_supplier_analytics.py
    └── integration/       # DDL, generation, ingestion, marts, forecasting, risk, api, ui smoke
        ├── test_analytical_marts.py
        ├── test_api_endpoints.py
        ├── test_data_generation.py
        ├── test_forecasting_pipeline.py
        ├── test_ingestion.py
        ├── test_risk_and_prescriptive_pipeline.py
        ├── test_schema_ddl.py
        └── test_ui_smoke.py
```

---

## 9. Getting Started & Verification

### Prerequisites
- Python 3.10+

### Quick Start Commands
```bash
# 1. Ingest clean data and seed SQLite database
python -m src.data.ingestion

# 2. Run complete test suite (119 tests)
python -m pytest

# 3. Launch FastAPI REST Service
uvicorn src.api.main:app --reload --port 8000

# 4. Launch Streamlit Decision Intelligence Dashboard
streamlit run src/ui/app.py
```
