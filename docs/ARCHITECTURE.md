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
- **Predictive Risk & Prescriptive Replenishment**: Forecast-aware daily inventory simulation, tiered statistical safety buffers, deterministic root-cause attribution, and prioritized replenishment recommendations (DC transfers & POs).

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

    subgraph S6 [Phase 6: Presentation]
        PRES --> API[FastAPI / Operational Service]
        PRES --> UI[Planner Streamlit Dashboard]
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

## 4. Predictive Risk & Prescriptive Formulations

### A. Daily Inventory Balance & Runout Calculation
$$\text{Stock}_t = \text{Stock}_{t-1} + \text{InboundDeliveries}_t - \hat{D}_t$$
$$\text{Days to Runout } (DTR) = \min \{ t \ge 1 \mid \text{Stock}_t \le 0 \}$$

### B. Tiered Safety Stock ($SS$) & Reorder Point ($ROP$)
$$SS = Z_{\text{SL}} \times \sqrt{LT \times \sigma_D^2 + D_{\text{avg}}^2 \times \sigma_{LT}^2}$$
- **Class A**: $Z = 2.05$ (98% Service Level)
- **Class B**: $Z = 1.65$ (95% Service Level)
- **Class C**: $Z = 1.28$ (90% Service Level)
$$ROP = \sum_{t=1}^{LT} \hat{D}_t + SS$$
$$\text{Target Inventory Level } S = ROP + (14 \times D_{\text{avg}})$$

### C. Stockout Risk Score ($SRS$) & Severity Tiers
$$SRS = \min\left(100.0, \max\left(0.0, \left(1.0 - \frac{DTR}{\max(1, LT)}\right) \times 100.0\right)\right)$$
- **CRITICAL**: $DTR \le LT$
- **HIGH**: $LT < DTR \le 1.5 \times LT$
- **MEDIUM**: $1.5 \times LT < DTR \le 2.0 \times LT$
- **LOW**: $DTR > 2.0 \times LT$

### D. Prescriptive Replenishment Hierarchy
1. **DC Lateral Transfer (`DC_TRANSFER`)**: If Store is CRITICAL and Central DC (`LOC-DC-01`) has available stock $> 2 \times \text{DC } SS$, recommend lateral transfer with **2-day transit time**:
   $$Q_{\text{transfer}} = \min(S - \text{Inventory Position}, \text{DC Surplus})$$
2. **Supplier Purchase Order (`PURCHASE_ORDER`)**: If DC transfer is unavailable or for DC replenishment:
   $$Q_{\text{PO}} = \lceil \max(0, S - \text{Inventory Position}) \rceil$$
3. **Excess Holding (`HOLD_ORDER`)**: If $DoS > 90$ days, pause reordering.

---

## 5. Evaluation Framework & Measured Performance

| Evaluation Dimension | Metric / Validation Method | Target / Standard | Measured Result (Phase 5) |
| :--- | :--- | :--- | :--- |
| **Data Integrity & Contracts** | 40-check validation suite, `PRAGMA foreign_key_check`. | 100% contract compliance, zero orphan records. | **100.0% Pass (Phase 2)** |
| **Analytical Marts Integrity** | Relational joins, non-null velocity aggregates, 9-cell ABC/XYZ matrix. | 100% complete coverage across 15 SKUs and 5 locations. | **100.0% Coverage (Phase 3)** |
| **Global Forecast Accuracy** | WAPE, MAE, RMSE, Forecast Bias on unseen test holdout. | Beat all statistical baselines with low bias. | **LightGBM WAPE: 10.97%** vs. Naive (21.52%) |
| **Stockout Risk Identification** | Node runout simulation across all 75 node positions. | Explicit categorization into CRITICAL, HIGH, MEDIUM, LOW. | **26 Critical, 8 High, 8 Medium, 33 Low** |
| **Root-Cause Attribution** | 6-category deterministic hierarchy. | 100% explainability across operational risks. | **Attributed across all 75 nodes** |
| **Prescriptive Action Plan** | DC transfer vs. PO optimization with priority ranking. | Actionable plan prioritized by urgency and revenue impact. | **12 DC Transfers, 29 POs, 7 Excess Holds** |
| **Reproducibility** | Deterministic pipeline rerun with fixed seeds (`seed=42`). | Identical logical records, forecasts, and recommendations across repeated runs. | **100% Bit-Exact Match** |
