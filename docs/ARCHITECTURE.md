# System Architecture & Technical Specifications

## 1. Architectural Philosophy: Lean, High-Signal, Production-Appropriate

The system adheres strictly to the principle of **simplest production-appropriate engineering**:
- **No Over-Engineering**: Avoid premature distributed infrastructure (Kafka, Spark, Kubernetes, Celery, Vector DBs, LLM agents).
- **In-Process & Modular**: Data pipelines, analytical queries, forecasting routines, and risk scoring are built as composable Python modules backed by SQL storage.
- **Contract-Driven**: Strict separation between data contracts (Pydantic), persistent relational schemas (SQLAlchemy DDL), analytical transformations, and statistical models.
- **Deterministic & Reproducible**: Fully reproducible synthetic telemetry using pseudo-random seeds (`seed=42`) to enable rigorous integration testing and regression benchmarking.
- **Strict Quality Gating**: Automated 40-check validation suite gating all persistent database ingestion.
- **SQL-First Analytical Marts**: High-performance analytical views and summary tables for segmentation, supplier intelligence, and operational risk classification.
- **Leakage-Free Multi-Horizon Forecasting**: Strict chronological train/validation/test holdouts with deterministic LightGBM gradient boosted regression beating classical statistical baselines.

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
        LGBM --> EVAL[Evaluation Matrix<br/>WAPE, MAE, RMSE, Bias by Horizon & Segment]
    end

    subgraph S5 [Phase 5: Risk & Decision Engine]
        LGBM --> RE[Operational Risk Engine<br/>Days-of-Supply, Stockout & Excess Scoring]
        MART4 --> RE
        RE --> REC[Action Recommendation Engine<br/>Reorder Alerts & Facility Rebalancing]
    end

    subgraph S6 [Phase 6: Presentation]
        REC --> API[FastAPI / Operational Service]
        REC --> UI[Planner Streamlit Dashboard]
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

### Analytical Data Marts
```
Analytical Marts Summary:
  mart_daily_product_velocity  : 21,900 rows (Daily sales, demanded units, revenue)
  mart_abc_xyz_segmentation    :     15 rows (SKU-level Pareto ABC + Volatility XYZ matrix)
  mart_supplier_performance    :      4 rows (Supplier OTIF, fill rate, lead-time stddev, spend)
  mart_supplier_sku_lead_times :     13 rows (Delivered supplier x SKU lead-time breakdowns)
  mart_inventory_health        :     75 rows (5 facilities x 15 SKUs as-of 2026-12-31)
```

---

## 4. Analytical & Forecasting Formulations

### A. Strict Chronological Time Splits
$$\text{Train} = [2026\text{-}01\text{-}01, 2026\text{-}09\text{-}30] \quad (16,380\text{ rows})$$
$$\text{Validation} = [2026\text{-}10\text{-}01, 2026\text{-}11\text{-}15] \quad (2,760\text{ rows})$$
$$\text{Test Holdout} = [2026\text{-}11\text{-}16, 2026\text{-}12\text{-}31] \quad (2,760\text{ rows})$$

### B. Target Variable Formulation
$$\text{Target Variable: } y_{t} = \text{units\_demanded}_t = \text{units\_sold}_t + \text{unfulfilled\_units}_t$$
Predicting true unconstrained demand rather than censored historical sales prevents under-replenishing high-velocity stockout items.

### C. Feature Engineering (Zero Data Leakage)
- **Autoregressive Lags**: $y_{t-1}, y_{t-7}, y_{t-14}, y_{t-28}$
- **Shifted Rolling Window Statistics**:
  $$\text{rolling\_mean\_7}_t = \frac{1}{7} \sum_{k=1}^{7} y_{t-k}, \quad \text{rolling\_mean\_14}_t = \frac{1}{14} \sum_{k=1}^{14} y_{t-k}$$
  $$\text{rolling\_std\_7}_t = \sqrt{\frac{1}{7} \sum_{k=1}^{7} (y_{t-k} - \text{rolling\_mean\_7}_t)^2}$$
- **Calendar & Promotion Indicators**: $\text{day\_of\_week}, \text{month}, \text{is\_weekend}, \text{is\_holiday}, \text{promotion\_active}, \text{discount\_pct}$
- **Operational & Financial Attributes**: $\text{unit\_price}, \text{unit\_cost}, \text{standard\_lead\_time\_days}$

### D. Forecasting Evaluation Metrics
$$\text{WAPE} = \frac{\sum_{t=1}^N |y_t - \hat{y}_t|}{\sum_{t=1}^N y_t}$$
$$\text{MAE} = \frac{1}{N} \sum_{t=1}^N |y_t - \hat{y}_t|, \quad \text{RMSE} = \sqrt{\frac{1}{N} \sum_{t=1}^N (y_t - \hat{y}_t)^2}$$
$$\text{Forecast Bias} = \frac{\sum_{t=1}^N (\hat{y}_t - y_t)}{\sum_{t=1}^N y_t}$$

---

## 5. Evaluation Framework & Measured Performance

| Evaluation Dimension | Metric / Validation Method | Target / Standard | Measured Result (Phase 4) |
| :--- | :--- | :--- | :--- |
| **Data Integrity & Contracts** | 40-check validation suite, `PRAGMA foreign_key_check`. | 100% contract compliance, zero orphan records. | **100.0% Pass (Phase 2)** |
| **Analytical Marts Integrity** | Relational joins, non-null velocity aggregates, 9-cell ABC/XYZ matrix, 5-tier risk taxonomy. | 100% complete coverage across 15 SKUs and 5 locations. | **100.0% Coverage (Phase 3)** |
| **Global Forecast Accuracy** | WAPE, MAE, RMSE, Forecast Bias on unseen test holdout. | Beat all statistical baselines with low bias. | **LightGBM WAPE: 10.97%** vs. Naive (21.52%), ES (21.30%), S.Naive (35.42%) |
| **Multi-Horizon Accuracy** | WAPE across 7d, 14d, and 30d forecast horizons. | Consistent accuracy across horizons without divergence. | **7d: 10.61% \| 14d: 10.77% \| 30d: 11.15%** |
| **Segment Error Analysis** | Accuracy sliced by ABC/XYZ velocity tiers. | High accuracy on volume-driving Class A SKUs. | **AX Segment WAPE: 10.37%** (vs Naive 20.89%) |
| **Risk Detection Precision** | Precision, Recall, and F1-score for predicting stockouts $\le 7$ days in advance. | *To be measured in Phase 5.* | Pending Phase 5 |
| **Prescriptive Impact** | Simulated avoided stockout revenue vs. incremental holding/expedite cost. | *To be measured in Phase 5.* | Pending Phase 5 |
| **Reproducibility** | Deterministic pipeline rerun with fixed seeds (`seed=42`). | Identical logical records, marts, and model predictions across repeated runs. | **100% Bit-Exact Match** |
