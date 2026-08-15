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
- Forecasting: Statistical baselines and lightweight gradient-boosted regression.
- Testing: Pytest with fast in-memory execution.
- Serving: FastAPI and Streamlit in later phases.

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
