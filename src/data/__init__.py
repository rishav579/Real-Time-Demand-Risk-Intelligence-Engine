"""Data access, schema definition, synthetic generation, and quality validation package."""

from src.data.generator import (
    DataGenerator,
    SyntheticDataset,
    run_generation,
    seed_database,
)
from src.data.ingestion import (
    DataQualityError,
    ingest_dataset,
    run_ingestion_pipeline,
)
from src.data.quality import (
    CheckSeverity,
    CheckStatus,
    DataQualityValidator,
    QualityCheckResult,
    QualityReport,
    validate_dataset,
)
from src.data.schema import (
    calendar_dim,
    create_all_tables,
    drop_all_tables,
    get_metadata,
    inventory_snapshots,
    locations,
    metadata,
    products,
    promotions,
    sales_transactions,
    supplier_deliveries,
    suppliers,
)

__all__ = [
    # Schema & DDL
    "metadata",
    "get_metadata",
    "create_all_tables",
    "drop_all_tables",
    "products",
    "locations",
    "suppliers",
    "promotions",
    "calendar_dim",
    "sales_transactions",
    "inventory_snapshots",
    "supplier_deliveries",
    # Generator
    "DataGenerator",
    "SyntheticDataset",
    "seed_database",
    "run_generation",
    # Quality & Validation
    "CheckStatus",
    "CheckSeverity",
    "QualityCheckResult",
    "QualityReport",
    "DataQualityValidator",
    "validate_dataset",
    # Ingestion
    "DataQualityError",
    "ingest_dataset",
    "run_ingestion_pipeline",
]
