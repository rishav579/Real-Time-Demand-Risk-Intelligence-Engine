# System Architecture & Technical Specifications

## 1. Architectural Philosophy: Lean, High-Signal, Production-Appropriate

The system adheres strictly to the principle of **simplest production-appropriate engineering**:
- **No Over-Engineering**: Avoid premature distributed infrastructure (Kafka, Spark, Kubernetes, Celery, Vector DBs, LLM agents).
- **In-Process & Modular**: Data pipelines, analytical queries, forecasting routines, risk scoring, and presentation services are built as composable Python modules backed by SQL storage.
- **Contract-Driven**: Strict separation between data contracts (Pydantic), persistent relational schemas (SQLAlchemy DDL), analytical transformations, and statistical models.
- **Deterministic & Reproducible**: Fully reproducible synthetic telemetry using pseudo-random seeds (`seed=42`) to enable rigorous integration testing and regression benchmarking.
- **Strict Quality Gating**: Automated 40-check validation suite gating all persistent database ingestion.
- **SQL-First Analytical Marts**: High-performance analytical views and summary tables for segmentation, supplier intelligence, and operational risk classification.
- **Leakage-Free Multi-Horizon Forecasting**: Strict chronological train/validation/test holdouts with deterministic LightGBM gradient boosted regression beating classical statistical baselines.
- **Predictive Risk & Prescriptive Replenishment**: Forecast-aware daily inventory simulation, tiered statistical safety buffers, deterministic root-cause attribution, and prioritized replenishment recommendations (DC transfers & POs).
- **Enterprise Serving & Decision Dashboard**: Typed FastAPI REST API endpoints and interactive Streamlit decision dashboard powered by an in-memory cached intelligence service.

---

## 2. End-to-End System Data Flow

```mermaid
flowchart TD
    subgraph S1 [Phase 1: Deterministic Ingestion - COMPLETED]
        G[Synthetic Data Generator<br/>Seed 42 & Planted Causal Signals] --> RAW[Raw In-Memory Telemetry]
    end

    subgraph S2 [Phase 2: Data Quality & Ingestion - COMPLETED]
        RAW --> DQ[Data Quality Validator<br/>40 Integrity & Boundary Checks]
        DQ --> GATE{Gating Policy<br/>All Critical Passed?}
        GATE -- NO --> REJ[DataQualityError<br/>Ingestion Blocked]
        GATE -- YES --> DB[(Relational Storage<br/>SQLite with Foreign Keys)]
    end

    subgraph S3 [Phase 3: Analytics & Marts - COMPLETED]
        DB --> MART1[mart_daily_product_velocity]
        DB --> MART2[mart_abc_xyz_segmentation<br/>80/15/5 Pareto & Population CV]
        DB --> MART3[mart_supplier_performance<br/>OTIF & Lead-Time Variance]
        DB --> MART4[mart_inventory_health<br/>ADD30, DoS & 5-Tier Risk Taxonomy]
    end

    subgraph S4 [Phase 4: Multi-Horizon Forecasting Engine - COMPLETED]
        MART1 --> SPLIT[Strict Chronological Splitter<br/>Train: Jan-Sep | Val: Oct-mid Nov | Test: mid Nov-Dec]
        SPLIT --> FEAT[Feature Pipeline<br/>Lags, Shifted Rolling Means, Calendar & Promo Flags]
        FEAT --> BASE[Statistical Baselines<br/>Naive | Seasonal Naive | Exponential Smoothing]
        FEAT --> LGBM[Champion LightGBM Regressor<br/>Multi-Horizon: 7d, 14d, 30d]
    end

    subgraph S5 [Phase 5: Predictive Risk & Prescriptive Engine - COMPLETED]
        LGBM --> SIM[Daily Inventory Balance Simulation<br/>30d Forecast Stream + Trailing-7d Continuation]
        MART2 --> SS[Tiered Safety Stock & ROP<br/>Class A: 98% Z=2.05 | Class B: 95% | Class C: 90%]
        MART3 --> SS
        SIM --> SCORE[Stockout & Excess Risk Scoring<br/>0-100 Risk Score, CRITICAL/HIGH/MEDIUM/LOW]
        SS --> SCORE
        SCORE --> ATTR[Root-Cause Attribution<br/>DEMAND_SURGE, SUPPLIER_DELAY, UNDER_REPLENISHED, etc.]
        ATTR --> PRES[Prescriptive Action Generator<br/>DC_TRANSFER (2d transit) | PURCHASE_ORDER | HOLD_ORDER]
    end

    subgraph S6 [Phase 6: Presentation & Serving Layer - COMPLETED]
        PRES --> SRV[IntelligenceService<br/>In-Memory Caching & Query Filter Layer]
        SRV --> API[FastAPI REST Service<br/>/summary, /forecast, /risk, /recommendations]
        SRV --> UI[Streamlit Decision Intelligence Dashboard<br/>5 Interactive Tabs & Visualizers]
    end
```

---

## 3. Relational Data Model & Analytical Marts

### Core Entity Tables
```
Table Scale Summary:
  calendar_dim         :    365 rows (Full year 2026 daily calendar dimension)
  products             :     15 rows (Catalog across Beverages, Snacks, Household, Personal Care)
  locations            :      5 rows (1 Central DC, 4 Regional Stores: NYC, BOS, MIA, SEA)
  suppliers            :      4 rows (Vendors with distinct lead time & reliability profiles)
  promotions           :      3 rows (Summer Refreshment, Fall Blitz, Holiday Event)
  sales_transactions   : 21,900 rows (365 days x 4 stores x 15 SKUs)
  inventory_snapshots  : 27,375 rows (365 days x 5 facilities x 15 SKUs)
  supplier_deliveries  :  2,388 rows (Inbound Purchase Orders & gate deliveries)
```

---

## 4. Evaluation Framework & Measured Performance

| Evaluation Dimension | Metric / Validation Method | Target / Standard | Measured Result (Phase 6) |
| :--- | :--- | :--- | :--- |
| **Data Integrity & Contracts** | 40-check validation suite, `PRAGMA foreign_key_check`. | 100% contract compliance, zero orphan records. | **100.0% Pass (Phase 2)** |
| **Analytical Marts Integrity** | Relational joins, non-null velocity aggregates, 9-cell ABC/XYZ matrix. | 100% complete coverage across 15 SKUs and 5 locations. | **100.0% Coverage (Phase 3)** |
| **Global Forecast Accuracy** | WAPE, MAE, RMSE, Forecast Bias on unseen test holdout. | Beat all statistical baselines with low bias. | **LightGBM WAPE: 10.97%** vs. Naive (21.52%) |
| **Stockout Risk Identification** | Node runout simulation across all 75 node positions. | Explicit categorization into CRITICAL, HIGH, MEDIUM, LOW. | **26 Critical, 8 High, 8 Medium, 33 Low** |
| **Root-Cause Attribution** | 6-category deterministic hierarchy. | 100% explainability across operational risks. | **Attributed across all 75 nodes** |
| **Prescriptive Action Plan** | DC transfer vs. PO optimization with priority ranking. | Actionable plan prioritized by urgency and revenue impact. | **12 DC Transfers, 29 POs, 7 Excess Holds** |
| **REST API Serving** | FastAPI endpoints (`/health`, `/summary`, `/forecast`, `/risk`, `/inventory`, `/recommendations`). | Valid OpenAPI specs, Pydantic schemas, sub-50ms latency. | **100% Endpoints Verified** |
| **Interactive Dashboard** | 5-tab Streamlit visualizer with cached analytical layer. | Instantaneous filter responses, zero unnecessary model re-fits. | **100% Views Functional** |
| **Reproducibility** | Deterministic pipeline rerun with fixed seeds (`seed=42`). | Identical logical records, forecasts, and recommendations across repeated runs. | **100% Bit-Exact Match** |
