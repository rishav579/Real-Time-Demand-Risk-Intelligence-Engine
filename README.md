# Real-Time Demand & Risk Intelligence Engine

> **Project Stage**: Phase 5 — Predictive Risk & Prescriptive Replenishment Engine  
> **Notice**: This repository is a realistic synthetic enterprise work-sample designed to showcase production-grade data modeling, analytics engineering, time-series forecasting, and operational risk intelligence. Serving REST APIs and the interactive Streamlit planner dashboard will be built in Phase 6.

---

## 1. Executive Summary & Business Problem

Retail and distribution networks operating across regional fulfillment centers and retail outlets face persistent supply chain friction:
- **Unpredictable Demand Surges**: Promotional campaigns and localized seasonality drive sharp demand spikes that standard rule-based min-max reordering fails to catch.
- **Stockout & Lost Revenue**: Critical SKUs stock out during peak velocity windows, degrading customer fill rates and brand loyalty.
- **Excess Inventory & Working Capital Lockup**: Over-ordering in low-velocity categories causes bloated holding costs, warehouse capacity strain, and markdown erosion.
- **Supplier Lead Time Volatility**: Unreliable supplier fulfillment and inbound delays amplify upstream bullwhip effects.

Traditional inventory management relies on static historical averages or disconnected spreadsheets. The **Real-Time Demand & Risk Intelligence Engine** bridges transaction-level telemetry with proactive operational decision support.

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
[ Multi-Horizon Demand Forecasting (LightGBM vs Baselines) ]
                      ↓
[ Daily Inventory Simulation & Runout Date Engine ]
                      ↓
[ Predictive Risk Engine & Root-Cause Attribution ]
                      ↓
[ Prescriptive Replenishment Engine (Supplier POs & DC Transfers) ]
                      ↓
[ Serving API & Planner Dashboard ]
```

---

## 5. Current Status & Phased Roadmap

| Phase | Milestone | Scope | Status |
| :---: | :--- | :--- | :---: |
| **0** | **Foundation & Data Contract** | Schema design, Pydantic contracts, SQLite/SQLAlchemy DDL, business questions, test suite. | **Complete** |
| **1** | **Deterministic Data Engine** | Seeded synthetic generator with planted causal patterns (promotions, supplier delays, seasonality). | **Complete** |
| **2** | **Data Quality & Ingestion** | 40-check validation suite, strict ingestion gating, corrupted fixture detectors, pipeline runner. | **Complete** |
| **3** | **SQL & Statistical Analytics** | ABC/XYZ 9-cell segmentation, supplier OTIF scorecards, Days-of-Supply, 5-tier risk taxonomy. | **Complete** |
| **4** | **Forecasting Engine** | Multi-horizon demand forecasting (7d, 14d, 30d), strict chronological splits, LightGBM vs. Baselines. | **Complete** |
| **5** | **Risk & Recommendation Engine** | Daily simulation, tiered safety stock ($Z=2.05$), root-cause attribution, POs & DC transfers. | **Complete** |
| **6** | **Serving & Presentation** | REST API endpoints, interactive planner dashboard, and scenario-testing UI. | Planned |

---

## 6. Predictive Risk & Prescriptive Replenishment Engine (Phase 5)

Phase 5 turns multi-horizon demand forecasts into actionable, prioritized supply chain recommendations across 75 active node positions:

### A. Daily Inventory Balance & Runout Simulation
- **Balance Equation**: $\text{Stock}_t = \text{Stock}_{t-1} + \text{InboundDeliveries}_t - \hat{D}_t$
- **30-Day Forecast Integration**: Consumes daily point forecasts directly; projects trailing-7-day forecast average for extended horizons ($30 < DTR \le 180$).
- **Runout Horizon Breakdown (As of 2026-12-31)**:
  - `WITHIN_30D`: **65 nodes**
  - `BEYOND_30D_PROJECTION`: **10 nodes** (slow-moving catalogue items & large stock buffers)

### B. Statistical Safety Stock ($SS$) & Reorder Point ($ROP$)
$$SS = Z_{\text{SL}} \times \sqrt{LT \times \sigma_D^2 + D_{\text{avg}}^2 \times \sigma_{LT}^2}$$
- **Tiered Service Levels**: Class A = 98% ($Z=2.05$), Class B = 95% ($Z=1.65$), Class C = 90% ($Z=1.28$).
- **Dynamic ROP**: $ROP = \sum_{t=1}^{LT} \hat{D}_t + SS$.

### C. Stockout Risk Tiers & Severity Scoring
- **Stockout Risk Score ($SRS$)**: $\min(100.0, \max(0.0, (1 - DTR/LT) \times 100))$.
- **CRITICAL** ($DTR \le LT$): **26 nodes** (Average $DTR = 1.94\text{ days}$, Average $SRS = 71.95$)
- **HIGH** ($LT < DTR \le 1.5 \times LT$): **8 nodes**
- **MEDIUM** ($1.5 \times LT < DTR \le 2.0 \times LT$): **8 nodes**
- **LOW** ($DTR > 2.0 \times LT$): **33 nodes**

### D. Deterministic Root-Cause Attribution
- `NOMINAL_STABLE`: **34 nodes** (adequate buffer coverage)
- `INSUFFICIENT_SAFETY_BUFFER`: **27 nodes** (lead-time/demand variance exceeded buffer)
- `UNDER_REPLENISHED`: **7 nodes** (inventory position breached ROP with 0 in-transit POs)
- `SLOW_MOVING_DRAG`: **7 nodes** (Class Z intermittent excess stock)

### E. Prescriptive Action Recommendations (48 Action Items Generated)
- **DC Transfers (`DC_TRANSFER`)**: **12 actions** (10 URGENT, 2 HIGH). Expedited 2-day transit from Central DC (`LOC-DC-01`) resolving critical store stockouts without vendor lead-time delay.
- **Supplier Purchase Orders (`PURCHASE_ORDER`)**: **29 actions** (14 URGENT, 4 HIGH, 11 MEDIUM). Sized to target level $S = ROP + 14 \times D_{\text{avg}}$.
- **Excess Holding Actions (`HOLD_ORDER`)**: **7 actions** (LOW). Pausing replenishment on excess long-tail inventory to mitigate working capital lockup.

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
│   └── risk/              # Predictive risk and prescriptive replenishment engine
│       ├── __init__.py
│       ├── attribution.py     # Deterministic 6-category root-cause attribution
│       ├── recommendations.py # Prescriptive PO and DC-to-Store transfer generator
│       ├── risk_scoring.py    # 0-100 stockout risk score & capital-at-risk
│       ├── safety_stock.py    # Multi-tier ABC safety stock & ROP calculator
│       └── simulation.py      # Daily inventory discrete balance & runout engine
└── tests/
    ├── unit/              # Config, contract, generator, quality, analytics, forecasting, risk
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
    └── integration/       # DDL, generation, ingestion, marts, forecasting, risk pipeline
        ├── test_analytical_marts.py
        ├── test_data_generation.py
        ├── test_forecasting_pipeline.py
        ├── test_ingestion.py
        ├── test_risk_and_prescriptive_pipeline.py
        └── test_schema_ddl.py
```

---

## 8. Getting Started & Verification

### Prerequisites
- Python 3.10+

### Run Full Pipeline & Test Suite (94 Tests)
```bash
# 1. Ingest clean data and seed SQLite database
python -m src.data.ingestion

# 2. Execute complete test suite (94 tests)
python -m pytest
```
