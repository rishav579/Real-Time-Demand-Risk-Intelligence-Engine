"""Ingestion boundary orchestrating validation and relational database storage."""

from typing import Dict, Optional, Tuple
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.config.settings import get_settings
from src.data.generator import DataGenerator, SyntheticDataset, seed_database
from src.data.quality import QualityReport, validate_dataset


class DataQualityError(Exception):
    """Exception raised when dataset ingestion fails critical data quality rules."""

    def __init__(self, report: QualityReport, message: Optional[str] = None):
        self.report = report
        super().__init__(
            message or f"Ingestion rejected: {report.failed_checks} critical data quality check(s) failed."
        )


def ingest_dataset(
    dataset: SyntheticDataset,
    engine: Engine,
    strict: bool = True,
    recreate_tables: bool = True,
) -> Tuple[QualityReport, Dict[str, int]]:
    """Validate synthetic enterprise dataset and persist to database if quality standards pass.

    Args:
        dataset: The generated synthetic enterprise dataset.
        engine: SQLAlchemy Engine for target database.
        strict: If True, blocks database write on any critical check failure.
        recreate_tables: If True, drops and recreates schema before loading.

    Returns:
        Tuple of (QualityReport, Dict[table_name, inserted_rows]).

    Raises:
        DataQualityError: If strict is True and dataset fails critical quality checks.
    """
    # 1. Execute full quality validation suite
    report = validate_dataset(dataset)

    # 2. Evaluate Ingestion Policy
    if not report.is_ingestable:
        if strict:
            raise DataQualityError(
                report=report,
                message=f"Dataset ingestion rejected: {report.failed_checks} critical quality checks failed.",
            )
        return report, {}

    # 3. Ingest into relational storage
    counts = seed_database(engine=engine, dataset=dataset, recreate_tables=recreate_tables)
    return report, counts


def run_ingestion_pipeline(
    seed: int = 42,
    target_db_url: Optional[str] = None,
    num_days: int = 365,
) -> Tuple[QualityReport, Dict[str, int]]:
    """Execute complete deterministic pipeline: Generation -> Validation -> Ingestion."""
    settings = get_settings()
    db_url = target_db_url or settings.database_url

    print(f"\n[1/3] Generating synthetic enterprise telemetry (seed={seed}, days={num_days})...")
    generator = DataGenerator(seed=seed)
    dataset = generator.generate(num_days=num_days)

    print("[2/3] Executing data quality and contract validation suite...")
    report = validate_dataset(dataset)
    report.print_summary()

    if not report.is_ingestable:
        raise DataQualityError(report=report)

    print(f"[3/3] Ingesting verified dataset into database ({db_url})...")
    engine = create_engine(db_url, echo=False)
    report, counts = ingest_dataset(dataset=dataset, engine=engine, strict=True, recreate_tables=True)

    print("\n--- Ingestion Successful: Final Storage Summary ---")
    for table, count in counts.items():
        print(f"  {table:<25s}: {count:,} rows")
    print("=" * 80)

    return report, counts


if __name__ == "__main__":
    run_ingestion_pipeline()
