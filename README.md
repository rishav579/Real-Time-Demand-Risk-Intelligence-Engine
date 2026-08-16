# Real-Time Demand & Risk Intelligence Engine

> **Project Stage**: Phase 4 — Multi-Horizon Demand Forecasting Engine  
> **Notice**: This repository is a realistic synthetic enterprise work-sample designed to showcase production-grade data modeling, analytics engineering, time-series forecasting, and operational risk intelligence. Operational risk scoring, reorder recommendations, API endpoints, and dashboards will be built in subsequent phases.

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
[ Multi-Horizon Demand Forecasting (LightGBM vs Baselines) ]
                      ↓
[ Operational Risk Engine (Stockout / Excess / Lead Time Drift) ]
                      ↓
[ Prescriptive Action & Recommendation Engine ]
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
| **5** | **Risk & Recommendation Engine** | Days-of-supply simulation, stockout risk scoring, reorder/rebalancing recommendation logic. | Planned |
| **6** | **Serving & Presentation** | REST API endpoints, interactive planner dashboard, and scenario-testing UI. | Planned |

---

## 6. Demand Forecasting Engine & Measured Benchmark Results (Phase 4)

Phase 4 introduces multi-horizon forecasting of true unconstrained customer demand (`units_demanded = units_sold + unfulfilled_units`) using strict chronological validation (Train: Jan-Sep, Validation: Oct-mid Nov, Test Holdout: mid Nov-Dec).

### A. Global Multi-Horizon Model Benchmark (Test Holdout: 3,060 Predictions)

| Model | Model Class | WAPE | MAE | RMSE | Forecast Bias | Status vs Baseline |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **LightGBM** | Gradient Boosted Trees | **10.97%** | **1.43** | **2.00** | **+0.0042** | **Champion (Beats all baselines)** |
| **Exponential Smoothing** | Simple Exp. Smoothing ($\alpha=0.3$) | 21.30% | 2.77 | 3.90 | +0.0191 | Benchmark Baseline |
| **Naive** | Last Observed Persistence | 21.52% | 2.80 | 4.31 | -0.1000 | Benchmark Baseline |
| **Seasonal Naive** | 7-Day Cyclical Persistence | 35.42% | 4.60 | 6.92 | +0.0730 | Benchmark Baseline |

### B. Multi-Horizon Accuracy Breakdown

| Horizon | LightGBM WAPE | Naive WAPE | Exp. Smoothing WAPE | Seasonal Naive WAPE |
| :---: | :---: | :---: | :---: | :---: |
| **7 Days Ahead** | **10.61%** | 21.32% | 21.66% | 36.77% |
| **14 Days Ahead** | **10.77%** | 21.40% | 21.15% | 35.80% |
| **30 Days Ahead** | **11.15%** | 21.61% | 21.28% | 34.93% |

### C. Segment Performance Breakdown (ABC / XYZ Velocity Matrix)

| Segment | Representative SKUs | LightGBM WAPE | Naive WAPE | Exp. Smoothing WAPE |
| :---: | :--- | :---: | :---: | :---: |
| **AX** | Cold Brew, Facial Cleanser, Chips (Top Revenue Staples) | **10.37%** | 20.89% | 20.81% |
| **BX** | Dish Soap, Chocolate, Hydration Drink (Mid-Tier Volume) | **11.11%** | 22.03% | 22.35% |
| **CX** | Mineral Water (Low Revenue Predictable Baseline) | **9.85%** | 22.39% | 19.28% |
| **CZ** | Industrial Degreaser, Steel Polish (Intermittent Tail) | *Intermittent ($<0.2\text{ units/day}$)* | *High Tail Error* | *High Tail Error* |

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
│   └── models/            # Pydantic validation contracts and domain entities
│       ├── __init__.py
│       └── contracts.py
└── tests/
    ├── unit/              # Config, contract, generator, quality, analytics, and forecasting tests
    │   ├── test_baselines.py
    │   ├── test_config.py
    │   ├── test_contracts.py
    │   ├── test_evaluate.py
    │   ├── test_features.py
    │   ├── test_generator.py
    │   ├── test_inventory_health.py
    │   ├── test_model.py
    │   ├── test_quality.py
    │   ├── test_segmentation.py
    │   ├── test_splits.py
    │   └── test_supplier_analytics.py
    └── integration/       # DDL, generation, ingestion, marts, and forecasting integration tests
        ├── test_analytical_marts.py
        ├── test_data_generation.py
        ├── test_forecasting_pipeline.py
        ├── test_ingestion.py
        └── test_schema_ddl.py
```

---

## 8. Getting Started & Verification

### Prerequisites
- Python 3.10+

### Run Full Pipeline & Test Suite (78 Tests)
```bash
# 1. Ingest clean data and seed SQLite database
python -m src.data.ingestion

# 2. Execute complete test suite (78 tests)
python -m pytest
```
