# System Architecture & Technical Specifications

## 1. Architectural Philosophy: Lean, High-Signal, Production-Appropriate

The system adheres strictly to the principle of **simplest production-appropriate engineering**:
- **No Over-Engineering**: Avoid premature distributed infrastructure (Kafka, Spark, Kubernetes, Celery, Vector DBs, LLM agents).
- **In-Process & Modular**: Data pipelines, analytical queries, forecasting routines, and risk scoring are built as composable Python modules backed by SQL storage.
- **Contract-Driven**: Strict separation between data contracts (Pydantic), persistent relational schemas (SQLAlchemy DDL), analytical transformations, and statistical models.
- **Deterministic & Reproducible**: Fully reproducible synthetic telemetry using pseudo-random seeds (`seed=42`) to enable rigorous integration testing and regression benchmarking.
- **Strict Quality Gating**: Automated 40-check validation suite gating all persistent database ingestion.

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

    subgraph S3 [Phase 3: Analytics & Marts]
        DB --> SQL[SQL Mart Aggregations<br/>ABC/XYZ Velocity, Turn Rates, Lead Time Variance]
    end

    subgraph S4 [Phase 4: Forecasting Engine]
        SQL --> FC[Time-Series Forecast Engine<br/>Rolling Baselines & Gradient Boosted Regression]
    end

    subgraph S5 [Phase 5: Risk & Decision Engine]
        FC --> RE[Operational Risk Engine<br/>Days-of-Supply, Stockout & Excess Scoring]
        RE --> REC[Action Recommendation Engine<br/>Reorder Alerts & Facility Rebalancing]
    end

    subgraph S6 [Phase 6: Presentation]
        REC --> API[FastAPI / Operational Service]
        REC --> UI[Planner Streamlit Dashboard]
    end
```

---

## 3. Relational Data Model & Dataset Scale

The data contract is built on 8 normalized relational tables populated by the generator (`seed=42`, 365 calendar days):

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
  -------------------------------------------------------------
  Total Database Rows  : 52,050 rows
```

```mermaid
erDiagram
    PRODUCTS ||--o{ SALES_TRANSACTIONS : "demanded in"
    LOCATIONS ||--o{ SALES_TRANSACTIONS : "sold at"
    PROMOTIONS ||--o{ SALES_TRANSACTIONS : "applied to"
    CALENDAR_DIM ||--o{ SALES_TRANSACTIONS : "transacted on"

    PRODUCTS ||--o{ INVENTORY_SNAPSHOTS : "stocked in"
    LOCATIONS ||--o{ INVENTORY_SNAPSHOTS : "stored at"
    CALENDAR_DIM ||--o{ INVENTORY_SNAPSHOTS : "recorded on"

    SUPPLIERS ||--o{ SUPPLIER_DELIVERIES : "supplied by"
    PRODUCTS ||--o{ SUPPLIER_DELIVERIES : "purchased of"
    LOCATIONS ||--o{ SUPPLIER_DELIVERIES : "delivered to"

    PRODUCTS {
        string product_id PK
        string sku UK
        string name
        string category
        string subcategory
        float unit_cost
        float unit_price
        int reorder_point_units
        int min_order_qty
        int standard_lead_time_days
        boolean is_active
    }

    LOCATIONS {
        string location_id PK
        string location_code UK
        string location_name
        string location_type
        string region
        string city
        string state
        int storage_capacity_units
        boolean is_active
    }

    PROMOTIONS {
        string promotion_id PK
        string promo_code UK
        string promo_name
        string promo_type
        float discount_pct
        date start_date
        date end_date
        boolean is_active
    }

    CALENDAR_DIM {
        date date_key PK
        int day_of_week
        string day_name
        int month
        string month_name
        int quarter
        int year
        boolean is_weekend
        boolean is_holiday
        string holiday_name
    }

    SALES_TRANSACTIONS {
        string transaction_id PK
        date transaction_date FK
        string product_id FK
        string location_id FK
        string promotion_id FK
        int units_demanded
        int units_sold
        int unfulfilled_units
        float unit_selling_price
        float discount_pct
        float total_revenue
    }

    INVENTORY_SNAPSHOTS {
        string snapshot_id PK
        date snapshot_date FK
        string product_id FK
        string location_id FK
        int on_hand_qty
        int in_transit_qty
        int reserved_qty
        int available_qty
        int stockout_flag
    }

    SUPPLIERS {
        string supplier_id PK
        string supplier_name
        string country
        float reliability_score
        int default_lead_time_days
        boolean is_active
    }

    SUPPLIER_DELIVERIES {
        string po_id PK
        string supplier_id FK
        string product_id FK
        string destination_location_id FK
        date order_date
        date promised_delivery_date
        date actual_delivery_date
        int qty_ordered
        int qty_received
        int lead_time_days
        int delay_days
        string po_status
    }
```

---

## 4. Data Quality & Ingestion Validation Architecture

Before data is written to SQLite or PostgreSQL, it passes through `DataQualityValidator` evaluating **40 discrete checks**:

| Category | Check Count | Sample Rules Enforced | Severity Policy |
| :--- | :---: | :--- | :--- |
| **Table Sanity** | 8 | All 8 dimension and fact tables contain non-zero records. | CRITICAL |
| **Uniqueness** | 12 | Primary keys (`product_id`, `location_id`, etc.) and composite keys (`(snapshot_date, product_id, location_id)`) contain zero duplicates. | CRITICAL |
| **Referential Integrity** | 11 | All foreign keys in `sales_transactions`, `inventory_snapshots`, and `supplier_deliveries` strictly resolve to dimension tables. | CRITICAL |
| **Value Ranges** | 4 | `unit_price >= unit_cost > 0`, `reliability_score \in [0, 1]`, non-negative inventory and demand quantities. | CRITICAL |
| **Date Consistency** | 2 | `promotion.start_date <= promotion.end_date`, `order_date <= promised_delivery_date <= actual_delivery_date`. | CRITICAL |
| **Business Logic** | 3 | Exact arithmetic: `unfulfilled == demanded - sold`, `available == on_hand - reserved`, `stockout_flag == (1 if on_hand == 0 else 0)`. | CRITICAL |

---

## 5. Planted Causal Signals & Verified Ground Truth

The synthetic data engine embeds deterministic causal dynamics with verified measured ground truth:

1. **Promotional Demand Shock**:
   - Promotion: `PRM-SUMMER-26` (June 1 - June 14, 2026, 20% discount).
   - Target SKU: `PRD-BEV-001` (Cold Brew Coffee 12oz).
   - **Verified Ground Truth**: Non-promo mean demand = 34.56 units/day $\rightarrow$ Promo mean demand = 46.86 units/day (**+35.57% measured lift**).
2. **Upstream Supplier Inbound Delay**:
   - Inbound PO: `PO-000907` placed on 2026-05-24 by Store `LOC-ST-01` with `SUP-001`.
   - Promised Delivery Date: 2026-05-29 (5-day standard lead time).
   - Actual Delivery Date: 2026-06-07.
   - **Verified Ground Truth**: **+9 days measured delivery delay**.
3. **Causal Stockout Crisis**:
   $$\text{Promotional Surge (+35.57\%)} + \text{Inbound PO Delay (+9 Days)} \longrightarrow \text{Inventory Depletion} \longrightarrow \text{Stockout Crisis}$$
   - **Verified Ground Truth**: 8 stockout days recorded (2026-06-01 to 2026-06-06, 2026-06-11 to 2026-06-12) with **334 total unfulfilled customer demand units**.
4. **Regional Seasonal Wave**:
   - Target SKU: `PRD-SEA-001` (Electrolyte Hydration Drink).
   - **Verified Ground Truth**: South Region (`LOC-ST-03` Miami) summer mean demand = 18.74 units/day vs. winter mean demand = 10.64 units/day (**1.76x summer uplift**).
5. **Slow-Moving Capital Drag**:
   - Target SKU: `PRD-HOU-003` (Industrial Floor Degreaser 1Gal).
   - **Verified Ground Truth**: Daily demand = 0.199 units/day, Average Store Stock = 85.1 units (**428.3 days of supply**).
6. **Steady-State Benchmark**:
   - Target SKU: `PRD-BEV-003` (Classic Mineral Water 1L).
   - **Verified Ground Truth**: 0 stockout days across all stores over the full 365-day year.

---

## 6. Evaluation Framework

| Evaluation Dimension | Metric / Validation Method | Target / Standard |
| :--- | :--- | :--- |
| **Data Integrity & Contracts** | Automated 40-check validation suite, `PRAGMA foreign_key_check`, zero orphan records. | 100% contract compliance, zero orphan records (Verified in Phase 2). |
| **Forecast Accuracy** | WAPE (Weighted Absolute Percentage Error), MAE, RMSE, Forecast Bias. | *To be measured in Phase 4.* |
| **Segment Error Analysis** | Accuracy sliced by ABC/XYZ velocity tiers and regional clusters. | *To be measured in Phase 4.* |
| **Risk Detection Precision** | Precision, Recall, and F1-score for predicting stockouts $\le 7$ days in advance. | *To be measured in Phase 5.* |
| **Prescriptive Impact** | Simulated avoided stockout revenue vs. incremental holding/expedite cost. | *To be measured in Phase 5.* |
| **Reproducibility** | Deterministic pipeline rerun with fixed seed (`seed=42`). | Identical logical records and 100% passing quality checks across repeated runs. |
