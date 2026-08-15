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

## Phase 1: Deterministic Synthetic Data Engine
- [ ] Build parameterized synthetic data generator using fixed random seeds (`numpy` / standard library).
- [ ] Generate realistic store and distribution center topologies (regions, capacities, active flags).
- [ ] Generate product catalog with realistic cost/price margins and supplier assignments.
- [ ] Inject planted business signals:
  - Promotional lift waves.
  - Supplier lead time delays and fulfillment slippage.
  - Coupled stockout crisis scenarios (demand surge + late PO -> stockout).
  - Seasonal trend shifts and regional variation.
  - Fast-moving staple vs. slow-moving noisy tail SKUs.
- [ ] Export raw relational CSV/Parquet datasets with deterministic checksums.

---

## Phase 2: Data Quality & Ingestion Pipeline
- [ ] Create automated data quality validation suite (schema conformance, range checks, foreign key integrity).
- [ ] Validate temporal sequence consistency (order_date $\le$ promised_delivery_date $\le$ actual_delivery_date).
- [ ] Load and index datasets into SQLite / relational storage.
- [ ] Implement data quality test reports and pipeline run metadata logging.

---

## Phase 3: Analytical SQL Marts & Statistical Profiling
- [ ] Build analytical SQL views / tables:
  - `mart_daily_product_velocity`: Sales volume, revenue, out-of-stock lost sales estimation.
  - `mart_inventory_health`: Days of supply, inventory turn rates, stockout frequency.
  - `mart_supplier_performance`: On-time in-full (OTIF) rates, average lead time variance.
  - `mart_abc_xyz_segmentation`: Revenue-based (ABC) and volatility-based (XYZ) SKU clustering.
- [ ] Implement summary statistics and exploratory reporting modules.

---

## Phase 4: Demand Forecasting Engine
- [ ] Implement time-series split utilities with strict temporal holdouts (prevent data leakage).
- [ ] Construct baseline statistical models:
  - Naive & Seasonal Naive baselines.
  - Moving Averages and Exponential Smoothing (Holt-Winters).
- [ ] Build feature engineering pipeline (lag features, rolling stats, promotional flags, calendar indicators).
- [ ] Train machine learning forecasting model (e.g. LightGBM / Ridge / Scikit-learn regressors).
- [ ] Compute forecast evaluation metrics across horizons: WAPE, MAE, RMSE, and Forecast Bias per SKU segment.

---

## Phase 5: Operational Risk & Recommendation Engine
- [ ] Develop Days-of-Supply (DoS) and Runout Estimation engine combining current stock + pipeline POs - forecasted demand.
- [ ] Calculate Stockout Probability and Excess Inventory Risk indices.
- [ ] Root-Cause Attribution engine (decomposing risk into demand surge, supplier delay, or reorder point deficit).
- [ ] Prescriptive Action Generator:
  - Automated PO quantity suggestions ($Q = \text{Target Stock} - (\text{On Hand} + \text{In Transit})$).
  - Lateral DC-to-Store inventory transfer recommendations.
- [ ] Simulate economic impact (saved lost sales revenue vs. holding cost).

---

## Phase 6: Serving & Presentation Layer
- [ ] Develop lightweight FastAPI endpoints for risk queries and forecast lookups.
- [ ] Build interactive Streamlit Planner Dashboard:
  - Executive KPI summary (stockout risk %, at-risk revenue, supplier reliability).
  - SKU-Location risk drill-down and root-cause explorer.
  - Actionable recommendation center with scenario adjustment sliders.
- [ ] Comprehensive documentation walkthrough and reproducible end-to-end demonstration.
