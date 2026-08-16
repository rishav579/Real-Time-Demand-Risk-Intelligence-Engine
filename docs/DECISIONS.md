# Architecture Decision Records (ADRs)

## ADR 001: Contract-First Modeling with Pydantic & SQLAlchemy

### Context
The intelligence engine processes transactions, inventory levels, supplier deliveries, and promotions across multiple facilities. Ensuring strict data integrity, type safety, and clear schema boundaries between operational inputs and database tables is essential.

### Decision
We use **Pydantic v2** for validation contracts and entity serialization, and **SQLAlchemy 2.0 Core/ORM DDL** for relational database schemas. Pydantic models define domain boundaries, type coercion, and business validation rules. SQLAlchemy DDL manages schema definitions, primary/foreign key constraints, and performance indexes.

### Consequences
- **Positive**: Clean separation of domain validation from persistence logic. Prevents silent data corruption and invalid transactions early in the pipeline.
- **Negative**: Minor redundancy between Pydantic and SQLAlchemy definitions, mitigated by keeping the schema lean (8 normalized tables).

---

## ADR 002: Deterministic Synthetic Telemetry with Planted Causal Signals

### Context
Public retail datasets (e.g., standard Kaggle competitions) often lack paired upstream supplier delivery telemetry, lead-time variance, real-time unfulfilled demand tracking, or controlled promotion/supply shock interventions.

### Decision
Generate custom, deterministic synthetic enterprise data locally using fixed pseudo-random seeds. Plant explicit, measurable causal signals:
1. Promotional demand surge (+35% lift).
2. Upstream supplier fulfillment delay (+9 days).
3. Coupled inventory runout and stockout crisis.
4. Regional seasonal patterns and slow-moving excess stock.

### Consequences
- **Positive**: Exact ground truth is known, enabling objective evaluation of whether the forecasting and risk engines correctly isolate root causes and prescribe correct remedies. Zero external download dependencies.
- **Negative**: Requires careful parameter tuning in Phase 1 to mirror realistic statistical distributions.

---

## ADR 003: Lean, In-Process Technology Stack

### Context
Data science and ML projects frequently suffer from premature infrastructure complexity (deploying Spark, Kafka, Airflow, Celery, Redis, Kubernetes, or vector databases when in-memory/in-process execution is orders of magnitude faster and simpler to develop, test, and maintain).

### Decision
Adopt a strictly lean, modular architecture:
- Database: Embedded SQLite for local development/testing with straightforward migration to PostgreSQL.
- Computation: Python standard library, Pandas, and NumPy.
- Forecasting: Statistical baselines and lightweight gradient-boosted regression (LightGBM).
- Serving: FastAPI for REST endpoints and Streamlit for interactive planning.
- Testing: Pytest with fast in-memory execution.

### Consequences
- **Positive**: Fast local iteration, zero external daemon requirements, high developer velocity, and friction-free reproducibility for reviewers.
- **Negative**: Scale is limited to single-node memory capacity, which is more than sufficient for regional retail enterprise simulation.

---

## ADR 004: Decoupled Multi-Horizon Forecasting and Prescriptive Risk Layers

### Context
Many demand forecasting systems stop at calculating predicted units, leaving inventory managers to perform ad-hoc mental math to assess stockout risks or order quantities.

### Decision
Explicitly separate:
1. **Demand Forecasting Layer**: Outputs point forecasts and prediction intervals.
2. **Operational Risk Engine**: Combines forecasts with current inventory balances, lead times, safety stock targets, and supplier reliability to compute runout probability, days of supply, and stockout severity.
3. **Prescriptive Action Layer**: Converts risk scores into concrete, explainable business recommendations (Purchase Orders, Transfer Rebalancing).

### Consequences
- **Positive**: Clear modularity. Planners receive direct decision support with root-cause transparency rather than raw model numbers.
- **Negative**: Requires careful modeling of lead times and safety stock formulas in Phase 5.

---

## ADR 005: Deterministic Data Engine via Explicit Instance RNG

### Context
Synthetic data generators often rely on global mutable pseudo-random states (e.g. `random.seed()` or `numpy.random.seed()`), which can produce non-deterministic side effects when tests or modules execute concurrently.

### Decision
Implement `DataGenerator` with an explicit instance-level random generator (`self.rng = random.Random(seed)`). Avoid any reliance on system clocks, UUID4, or OS randomness during generation.

### Consequences
- **Positive**: Guaranteed identical logical datasets across different runs and platforms when identical seeds are supplied (`seed=42`). Enables deterministic integration tests and regression benchmarks.
- **Negative**: All stochastic methods must receive and use the instance RNG explicitly.

---

## ADR 006: Pre-Ingestion Data Quality Gating and Strict Failure Policy

### Context
Downstream analytical marts and time-series forecasting models produce erratic outputs or silent failures if corrupt records (orphan keys, negative stock, price below cost, or broken fulfillment arithmetic) enter relational storage.

### Decision
Implement a pre-ingestion validation gate (`DataQualityValidator` and `ingest_dataset`). Ingestion evaluates 40 deterministic checks across uniqueness, referential integrity, ranges, date ordering, and business logic before any SQL `INSERT` is executed. Any failure on critical checks raises `DataQualityError` and blocks database loading completely.

### Consequences
- **Positive**: Guaranteed pristine data layer for downstream analytics. Corrupted data is caught and attributed at the ingestion boundary rather than deep within forecasting models.
- **Negative**: Requires maintenance of validation rules aligned with schema evolution.

---

## ADR 007: SQL-First Analytical Marts & 5-Tier Operational Risk Taxonomy

### Context
Downstream forecasting models, scenario simulators, and inventory replenishment planners require aggregated velocity, product volatility tiering, supplier reliability, and stock risk classifications without recomputing complex multi-table joins on raw telemetry.

### Decision
Implement a SQL-first analytical data marts layer (`src/analytics/`):
1. `mart_daily_product_velocity`: Complete daily sales telemetry join.
2. `mart_abc_xyz_segmentation`: 80/15/5 cumulative revenue Pareto distribution and population Coefficient of Variation ($CV \le 0.5$, $0.5 < CV \le 1.0$, $CV > 1.0$) 9-cell matrix.
3. `mart_supplier_performance`: OTIF fulfillment rates, lead-time variance, and inbound spend.
4. `mart_inventory_health`: SKU $\times$ Location inventory positions as-of the latest snapshot date (`2026-12-31`), $ADD_{30}$, Days-of-Supply ($DoS$), and a 5-tier operational risk classification (CRITICAL, LOW_BUFFER, HEALTHY, ELEVATED_BUFFER, EXCESS).

### Consequences
- **Positive**: Standardized statistical feature and risk layer decoupled from raw tables. Enables downstream forecasting and UI layers to query pre-aggregated, verified marts.
- **Negative**: Adds 5 persistent analytical tables to relational storage, refreshed after data ingestion.

---

## ADR 008: Multi-Horizon Forecasting Engine, Strict Chronological Splitting, and Baseline Benchmarking

### Context
Retail inventory replenishment requires multi-horizon visibility (7 days for quick cross-dock rebalancing, 14 days for standard supplier lead-time coverage, and 30 days for monthly planning). Standard random train/test splits cause severe lookahead bias, and ML models frequently fail to prove utility against simple statistical heuristics.

### Decision
1. Enforce strict sequential chronological splits: Train (`2026-01-01` to `2026-09-30`), Validation (`2026-10-01` to `2026-11-15`), and Test Holdout (`2026-11-16` to `2026-12-31`). Zero random splitting.
2. Target variable is true unconstrained demand (`units_demanded = units_sold + unfulfilled_units`).
3. Construct 3 statistical baselines (Naive, 7-day Seasonal Naive, Simple Exponential Smoothing $\alpha=0.3$) and require that LightGBM beat all baselines across multi-horizon WAPE/RMSE on unseen holdouts.
4. Prevent data leakage by shifting all autoregressive and rolling statistics by at least 1 day.

### Consequences
- **Positive**: Rigorous, leakage-free benchmark. LightGBM champion achieves 10.97% WAPE (vs 21.52% Naive baseline).
- **Negative**: Adds `lightgbm` and `scikit-learn` dependencies to `pyproject.toml`.

---

## ADR 009: Predictive Runout Simulation, Tiered Safety Stock, and Prescriptive Replenishment

### Context
Inventory planners need dynamic simulation of future inventory balances, statistical safety buffers adjusted by revenue tier, explainable root-cause attribution, and prioritized action plans distinguishing between expedited internal transfers and external purchase orders.

### Decision
Implement a prescriptive risk and replenishment engine (`src/risk/`):
1. Discrete daily balance simulation consuming 30-day LightGBM point forecasts and trailing-7-day projections to calculate exact Days-to-Runout ($DTR$).
2. Statistical safety stock combining demand variance ($\sigma_D$) and supplier lead-time variance ($\sigma_{LT}$) with tiered service levels (Class A = 98%, Class B = 95%, Class C = 90%).
3. Standardized 0–100 Stockout Risk Score and 4-tier taxonomy (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
4. 6-category deterministic root-cause attribution hierarchy (`DEMAND_SURGE`, `SUPPLIER_DELAY`, `UNDER_REPLENISHED`, `INSUFFICIENT_SAFETY_BUFFER`, `SLOW_MOVING_DRAG`, `OVER_ORDER_EXCESS`).
5. Prescriptive replenishment engine preferring 2-day expedited DC-to-store lateral transfers when DC has surplus stock ($> 2 \times \text{DC } SS$) before generating supplier purchase orders.

### Consequences
- **Positive**: Converts ML demand forecasts into actionable operational decision support with complete natural language explanations and priority audit trails.
- **Negative**: Relies on accurate upstream supplier scorecard variance metrics and DC inventory visibility.

---

## ADR 010: Enterprise REST API & Streamlit Decision Intelligence Dashboard

### Context
End-users (planners, analysts, and executive stakeholders) need interactive access to forecast curves, risk matrices, and prioritized recommendations without executing raw Python scripts or SQL queries. Downstream systems also require standard JSON REST endpoints.

### Decision
1. Implement a **FastAPI** REST service (`src/api/`) exposing typed endpoints (`/health`, `/summary`, `/forecast`, `/risk`, `/inventory`, `/recommendations`) backed by Pydantic response models and OpenAPI specs.
2. Implement a **Streamlit** dashboard (`src/ui/app.py`) providing 5 core operational views (Executive Overview, Forecast Explorer, Risk Explorer, Recommendation Center, SKU Drill-Down).
3. Introduce an in-memory cached `IntelligenceService` singleton (`src/api/service.py`) that manages pre-computed marts, forecasts, and risk positions, guaranteeing sub-50ms query responses and eliminating redundant ML model fitting during UI interactions.

### Consequences
- **Positive**: High-performance, interactive, and decoupled presentation layer with complete API documentation at `/docs`.
- **Negative**: Adds `fastapi`, `uvicorn`, `httpx`, and `streamlit` dependencies.
