# Project Roadmap & Milestone Deliverables

## Phase 0: Foundation & Business/Data Contract (Completed)
- [x] Define multi-location enterprise business problem and target personas.
- [x] Formulate core operational business questions (Demand, Risk, Drivers, Recommendations, Monitoring).
- [x] Design 8-table relational data contract with primary keys, foreign keys, and indexes.
- [x] Implement Pydantic data contract models with strict type and boundary validations.
- [x] Implement SQLAlchemy DDL table definitions and in-memory SQLite schema verification.
- [x] Set up unified configuration management via `pydantic-settings`.
- [x] Establish foundation unit and integration test suite with 100% passing tests.

---

## Phase 1: Deterministic Synthetic Data Engine (Completed)
- [x] Build parameterized synthetic data generator using explicit random seed (`seed=42`).
- [x] Generate realistic store and distribution center topologies (1 DC, 4 retail stores across regions).
- [x] Generate product catalog with 15 SKUs spanning high-velocity, medium, seasonal, staple, and slow-moving items.
- [x] Inject and verify planted business signals:
  - Promotional lift waves (+35.57% verified lift on target SKU).
  - Supplier lead time delays (+9 days verified latency on PO-000907).
  - Coupled stockout crisis scenarios (demand surge + late PO -> 8 stockout days, 334 unfulfilled units).
  - Seasonal trend shifts and regional variation (1.76x summer demand in South).
  - Slow-moving capital drag (428+ days of supply on industrial cleaner SKU).
  - Stable baseline benchmark item with 0 stockout days.
- [x] Implement CLI command `python -m src.data.generator` for automated generation and database seeding.
- [x] Write deterministic reproduction and foreign-key integrity test suite (28 passing tests).

---

## Phase 2: Data Quality & Ingestion Pipeline (Completed)
- [x] Create automated data quality validation suite (`src/data/quality.py`) with 40 deterministic checks:
  - Table sanity & non-empty master catalogs (8 checks).
  - Primary & composite uniqueness enforcement (12 checks).
  - Referential integrity & orphan key detection (11 checks).
  - Value ranges & non-negativity (4 checks).
  - Chronological date ordering consistency (2 checks).
  - Cross-column business logic & stockout flag arithmetic (3 checks).
- [x] Implement structured `QualityReport` and `QualityCheckResult` with PASS/WARN/FAIL status and CRITICAL/WARNING severity.
- [x] Build gated ingestion boundary (`src/data/ingestion.py`) rejecting invalid datasets via `DataQualityError`.
- [x] Develop comprehensive corrupted fixture tests across 13 distinct anomaly categories.
- [x] Implement CLI ingestion runner: `python -m src.data.ingestion`.
- [x] Verify full test suite passing (46/46 tests).

---

## Phase 3: Analytical SQL Marts & Statistical Profiling (Completed)
- [x] Build analytical data marts layer (`src/analytics/marts.py`):
  - `mart_daily_product_velocity`: Complete daily sales demand & revenue aggregations.
  - `mart_abc_xyz_segmentation`: ABC Pareto revenue (80/15/5) and XYZ CV volatility ($CV \le 0.5$, $0.5 < CV \le 1.0$, $CV > 1.0$) 9-cell matrix.
  - `mart_supplier_performance`: Comprehensive supplier scorecards (OTIF, lead-time variance, fill rates, inbound spend).
  - `mart_supplier_sku_lead_times`: Granular supplier $\times$ SKU lead-time distributions.
  - `mart_inventory_health`: SKU $\times$ Location inventory positions, $ADD_{30}$, Days-of-Supply ($DoS$), and 5-tier operational risk classification (CRITICAL, LOW_BUFFER, HEALTHY, ELEVATED_BUFFER, EXCESS).
- [x] Ensure analysis-date determinism (as-of `MAX(snapshot_date)` = `2026-12-31`).
- [x] Develop comprehensive unit and integration tests across segmentation, supplier analytics, inventory health, and relational joins (61/61 tests passing).

---

## Phase 4: Demand Forecasting Engine (Completed)
- [x] Implement strict chronological train/val/test splitter (`src/forecasting/splits.py`):
  - Train: 2026-01-01 through 2026-09-30 (273 days, 16,380 rows).
  - Validation: 2026-10-01 through 2026-11-15 (46 days, 2,760 rows).
  - Test Holdout: 2026-11-16 through 2026-12-31 (46 days, 2,760 rows).
- [x] Build zero-leakage feature engineering pipeline (`src/forecasting/features.py`):
  - Autoregressive lags: `lag_1`, `lag_7`, `lag_14`, `lag_28`.
  - Shifted rolling stats: `rolling_mean_7`, `rolling_mean_14`, `rolling_std_7`.
  - Calendar & promotion attributes: `day_of_week`, `month`, `is_weekend`, `is_holiday`, `promotion_active`, `discount_pct`.
  - Product economics & supply: `unit_price`, `unit_cost`, `standard_lead_time_days`.
- [x] Build 3 statistical baseline models (`src/forecasting/baselines.py`):
  - Naive persistence forecaster.
  - 7-day cyclical Seasonal Naive forecaster.
  - Simple Exponential Smoothing (SES, $\alpha=0.3$) forecaster.
- [x] Implement LightGBM gradient-boosted demand forecaster (`src/forecasting/model.py`) with deterministic seed (`random_state=42`) and non-negative projection.
- [x] Build evaluation benchmark suite (`src/forecasting/evaluate.py`) computing WAPE, MAE, RMSE, and Forecast Bias across 7-day, 14-day, and 30-day horizons, sliced globally and by ABC/XYZ velocity segments.
- [x] Verify LightGBM champion performance: **10.97% Global WAPE** vs. **21.30% Exp. Smoothing**, **21.52% Naive**, and **35.42% Seasonal Naive**.
- [x] Complete unit and integration test suite (78/78 tests passing).

---

## Phase 5: Predictive Risk & Prescriptive Replenishment Engine (Completed)
- [x] Build forecast-aware inventory daily simulation engine (`src/risk/simulation.py`) computing exact Days-to-Runout ($DTR$) and distinguishing between 30-day window runouts vs. extended trailing-7-day projections.
- [x] Implement statistical multi-tier safety stock ($SS$) and dynamic reorder point ($ROP$) calculator (`src/risk/safety_stock.py`) with tiered service levels (Class A $Z=2.05$, Class B $Z=1.65$, Class C $Z=1.28$).
- [x] Build risk scoring module (`src/risk/risk_scoring.py`) computing 0–100 Stockout Risk Scores ($SRS$), 4-tier stockout taxonomy (CRITICAL, HIGH, MEDIUM, LOW), and excess capital-at-risk.
- [x] Implement deterministic 6-category root-cause attribution hierarchy (`src/risk/attribution.py`): `DEMAND_SURGE`, `SUPPLIER_DELAY`, `UNDER_REPLENISHED`, `INSUFFICIENT_SAFETY_BUFFER`, `SLOW_MOVING_DRAG`, `OVER_ORDER_EXCESS`.
- [x] Build prescriptive action generator (`src/risk/recommendations.py`):
  - 12 expedited DC-to-store lateral transfer recommendations (`DC_TRANSFER`) from Central DC (`LOC-DC-01`) with 2-day transit time.
  - 29 supplier purchase orders (`PURCHASE_ORDER`) sized to target inventory level $S$.
  - 7 excess holding actions (`HOLD_ORDER`).
  - Prioritized audit trail (`URGENT`, `HIGH`, `MEDIUM`, `LOW`) with natural language explanations.
- [x] Complete unit and integration test suite (94/94 tests passing).

---

## Phase 6: Serving & Presentation Layer
- [ ] Develop lightweight FastAPI endpoints for risk queries, forecast lookups, and recommendation retrieval.
- [ ] Build interactive Streamlit Planner Dashboard:
  - Executive KPI summary (stockout risk %, at-risk revenue, supplier reliability).
  - SKU-Location risk drill-down and root-cause explorer.
  - Actionable recommendation center with scenario adjustment sliders.
- [ ] Comprehensive documentation walkthrough and reproducible end-to-end demonstration.
