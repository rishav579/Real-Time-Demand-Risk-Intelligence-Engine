# System Architecture & Technical Specifications

## 1. Architectural Philosophy: Lean, High-Signal, Production-Appropriate

The system adheres strictly to the principle of **simplest production-appropriate engineering**:
- **No Over-Engineering**: Avoid premature distributed infrastructure (Kafka, Spark, Kubernetes, Celery, Vector DBs, LLM agents).
- **In-Process & Modular**: Data pipelines, analytical queries, forecasting routines, and risk scoring are built as composable Python modules backed by SQL storage.
- **Contract-Driven**: Strict separation between data contracts (Pydantic), persistent relational schemas (SQLAlchemy DDL), analytical transformations, and statistical models.
- **Deterministic & Reproducible**: Fully reproducible synthetic telemetry using pseudo-random seeds to enable rigorous integration testing and regression benchmarking.

---

## 2. End-to-End System Data Flow

```mermaid
flowchart TD
    subgraph S1 [Phase 1: Deterministic Ingestion]
        G[Synthetic Data Generator<br/>Fixed Seed & Planted Causal Signals] --> CSV[Raw Stage Datasets]
    end

    subgraph S2 [Phase 2: Data Quality & Storage]
        CSV --> DQ[Data Quality Validator<br/>Schema, Range, Null, Referential Integrity]
        DQ --> DB[(Relational Storage<br/>SQLite / PostgreSQL)]
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

## 3. Relational Data Model (Core Entities)

The data contract is built on 8 normalized, high-utility relational tables:

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

## 4. Core Business Questions Answered

### A. Demand Intelligence
- What is the expected daily/weekly demand for each SKU-location node over the 14-day and 30-day forecast horizons?
- How much incremental demand lift is attributable to active promotional campaigns vs. seasonal baseline variation?

### B. Operational Risk Detection
- Which product-location pairs will experience stockouts before the next replenishment delivery arrives?
- Which SKUs exceed the maximum holding capacity threshold or safe days-of-supply (>90 days of inventory)?

### C. Root-Cause Drivers
- Is an emerging stockout caused by:
  1. An unexpected demand surge (promotional or unmodeled spike)?
  2. Supplier fulfillment delay (actual lead time > promised lead time)?
  3. Under-replenishment (reorder point set too low relative to velocity)?

### D. Prescriptive Business Actions
- What specific purchase orders should be placed today (SKU, destination, recommended quantity)?
- Can an impending stockout at a retail store be mitigated via an expedited regional distribution center (DC) cross-dock transfer?

### E. Model & Performance Monitoring
- What is the out-of-sample forecast accuracy (MAE, WAPE, Bias) across product velocity categories (Fast-moving Class A vs. Slow-moving Class C)?
- What is the precision and recall of stockout alerts generated by the risk engine?

---

## 5. Planted Causal Signals (Synthetic Ground Truth)

To ensure the system is evaluated against ground truth, the synthetic data generator implements deterministic, causal business dynamics:

1. **Promotional Demand Shock**: A planned 2-week discount promotion (+35% demand lift) on high-velocity SKUs in specific urban stores.
2. **Upstream Supplier Bottleneck**: A key supplier experiences a 9-day fulfillment latency spike during the promotional period.
3. **Causal Stockout Crisis**:
   $$\text{Promotional Demand Surge} + \text{Supplier Inbound Delay} \longrightarrow \text{Inventory Depletion} \longrightarrow \text{Stockout (Unfulfilled Demand)}$$
4. **Seasonal Weather Wave**: Summer category demand uplift in Southern locations with corresponding decline in Northern regions.
5. **Slow-Moving Capital Drag**: Low-velocity SKUs subject to minimum order quantity batching, leading to >120 days of supply and excess holding costs.
6. **Reliable Steady-State Baselining**: Core staple SKUs exhibiting low-variance Poisson demand for baseline forecasting validation.

---

## 6. Evaluation Framework

| Evaluation Dimension | Metric / Validation Method | Target / Standard |
| :--- | :--- | :--- |
| **Data Integrity & Contracts** | Great Expectations / Pydantic schema validation, null checks, foreign key validity. | 100% contract compliance, zero orphan records. |
| **Forecast Accuracy** | WAPE (Weighted Absolute Percentage Error), MAE, RMSE, Forecast Bias. | *To be measured in later phases.* |
| **Segment Error Analysis** | Accuracy sliced by ABC/XYZ velocity tiers and regional clusters. | *To be measured in later phases.* |
| **Risk Detection Precision** | Precision, Recall, and F1-score for predicting stockouts $\le 7$ days in advance. | *To be measured in later phases.* |
| **Prescriptive Impact** | Simulated avoided stockout revenue vs. incremental holding/expedite cost. | *To be measured in later phases.* |
| **Reproducibility** | Deterministic pipeline rerun with fixed seed. | Identical checksums on generated tables. |
