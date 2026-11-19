from datetime import date
from pathlib import Path

import pytest
from pyspark.errors import SparkRuntimeException

from brisbane_house_finder.bronze.audit_columns import add_audit_columns


def _read_landing_csv(spark, base: Path, date_folder: str):
    """Write a small CSV under base/raw_files/test_ds/<date_folder>/ and read it back."""
    csv_file = base / "raw_files" / "test_ds" / date_folder / "suburbs.csv"
    csv_file.parent.mkdir(parents=True)
    csv_file.write_text("suburb_name\nToowong\nIndooroopilly\n")
    return spark.read.option("header", True).csv(str(csv_file))


@pytest.mark.spark
def test_adds_audit_column_values(spark, test_files_dir):
    df = _read_landing_csv(spark, test_files_dir, "2026-11-03")

    rows = add_audit_columns(df, run_id="run-123").collect()

    assert len(rows) == 2
    for row in rows:
        assert row["_source_file"].endswith("/raw_files/test_ds/2026-11-03/suburbs.csv")
        assert row["_source_file_modified_at"] is not None
        assert row["_download_date"] == date(2026, 11, 3)
        assert row["_ingested_at"] is not None
        assert row["_run_id"] == "run-123"


@pytest.mark.spark
def test_keeps_original_columns_and_rows(spark, test_files_dir):
    df = _read_landing_csv(spark, test_files_dir, "2026-11-03")

    result = add_audit_columns(df, run_id="run-123")

    assert result.columns == [
        "suburb_name",
        "_source_file",
        "_source_file_modified_at",
        "_download_date",
        "_ingested_at",
        "_run_id",
    ]
    suburbs = sorted(row["suburb_name"] for row in result.collect())
    assert suburbs == ["Indooroopilly", "Toowong"]


@pytest.mark.spark
@pytest.mark.parametrize("date_folder", ["no-date", "2026-13-45", "2026-1-3"])
def test_fails_when_date_folder_is_not_a_date(spark, test_files_dir, date_folder):
    df = _read_landing_csv(spark, test_files_dir, date_folder)

    with pytest.raises(SparkRuntimeException, match="No valid date folder in the landing path"):
        add_audit_columns(df, run_id="run-123").collect()
