# Real-Time Demand & Risk Intelligence Engine

> **Project Stage**: Phase 1 — Deterministic Synthetic Enterprise Data Engine  
> **Notice**: This repository is a realistic synthetic enterprise work-sample designed to showcase production-grade data modeling, analytics engineering, forecasting, and operational risk intelligence. Machine learning models, API endpoints, and dashboards will be built in subsequent phases.

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
[ Relational Schema / Data Contract (SQLAlchemy & Pydantic) ]
                      ↓
[ Data Quality & Anomaly Validation Suite ]
                      ↓
[ SQL & Exploratory Statistical Analysis ]
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
| **2** | **Data Quality & Ingestion** | Schema enforcement, boundary tests, missing data detection, and pipeline orchestration. | Planned |
| **3** | **SQL & Statistical Analytics** | Analytical marts, velocity tiering (ABC/XYZ), inventory turnover, supplier scorecard. | Planned |
| **4** | **Forecasting Engine** | Baseline moving averages, exponential smoothing, and gradient-boosted time-series forecasting. | Planned |
| **5** | **Risk & Recommendation Engine** | Days-of-supply simulation, stockout risk scoring, reorder/rebalancing recommendation logic. | Planned |
| **6** | **Serving & Presentation** | REST API endpoints, interactive planner dashboard, and scenario-testing UI. | Planned |

---

## 6. Synthetic Data Engine & Planted Signals

The dataset is generated deterministically using a fixed pseudo-random seed (`seed=42`) spanning **365 calendar days** across **15 SKUs**, **5 facilities** (1 DC, 4 stores), and **4 suppliers** (~52,050 rows total):

```
Table Row Counts:
  calendar_dim         :    365 rows
  products             :     15 rows
  locations            :      5 rows
  suppliers            :      4 rows
  promotions           :      3 rows
  sales_transactions   : 21,900 rows
  inventory_snapshots  : 27,375 rows
  supplier_deliveries  :  2,388 rows
```

### Verified Planted Ground Truth Signals
- **Promotional Demand Lift**: +35.57% verified demand surge during promo windows on target beverage SKU (`PRD-BEV-001`).
- **Supplier Delivery Delay**: Planted +9 day latency spike on inbound PO (`PO-000907`).
- **Stockout Crisis Causal Chain**: Surge demand + delayed inbound shipment $\rightarrow$ inventory depletion $\rightarrow$ 8 stockout days with 334 unfulfilled units.
- **Regional Seasonality**: 1.76x demand multiplier in Southern regions during summer months.
- **Slow-Moving Capital Drag**: Low-velocity SKUs with high minimum batch sizes generating 428+ days-of-supply.
- **Stable Baseline Benchmark**: Staple mineral water product (`PRD-BEV-003`) exhibiting zero stockouts and stationary demand.

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
│   ├── config/            # Environment and engine configurations
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── data/              # Relational schema, DDL, and synthetic data generator
│   │   ├── __init__.py
│   │   ├── generator.py   # Deterministic data generation engine (Seed 42)
│   │   └── schema.py      # SQLAlchemy 2.0 table definitions and DDL
│   └── models/            # Pydantic validation contracts and domain entities
│       ├── __init__.py
│       └── contracts.py
└── tests/
    ├── unit/              # Configuration, contract, and generator unit tests
    │   ├── test_config.py
    │   ├── test_contracts.py
    │   └── test_generator.py
    └── integration/       # DDL and database generation integration tests
        ├── test_data_generation.py
        └── test_schema_ddl.py
```

---

## 8. Getting Started & Verification

### Prerequisites
- Python 3.10+

### Generate Synthetic Database
```bash
# Generate deterministic synthetic data and seed local SQLite database
python -m src.data.generator
```

### Run Full Test Suite
```bash
# Execute unit and integration tests (28 tests)
python -m pytest
```
