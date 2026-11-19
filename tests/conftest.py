"""Shared pytest fixtures.

The ``spark`` fixture gives tests a Spark session in two places:

* On a PC or in GitHub Actions CI (default): a small local PySpark session.
  Uses no Databricks compute, so it does not count towards the Free Edition quota.
* On Databricks: the session of the notebook that runs the tests. The runner
  notebook ``notebooks/run_tests`` sets ``BHF_TEST_SPARK=databricks`` before it
  calls pytest.

The ``test_files_dir`` fixture gives each test an empty folder for files that
Spark will read:

* Locally: pytest's ``tmp_path``.
* On Databricks: a new folder in the Unity Catalog volume named by
  ``BHF_TEST_FILES_ROOT`` (set by the runner notebook). Serverless Spark cannot
  read the notebook's local disk, so test files must be in a volume.

Tests that need Spark take ``spark`` as an argument and are marked
``@pytest.mark.spark``, so they can be selected or skipped with
``pytest -m spark`` / ``pytest -m "not spark"``.
"""

import os
import shutil
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

SPARK_MODE_VARIABLE = "BHF_TEST_SPARK"
TEST_FILES_ROOT_VARIABLE = "BHF_TEST_FILES_ROOT"


@pytest.fixture(scope="session")
def spark() -> Iterator[SparkSession]:
    """Return one Spark session shared by all tests in the run."""
    if os.environ.get(SPARK_MODE_VARIABLE) == "databricks":
        # Inside a Databricks notebook: reuse the notebook's own session.
        active = SparkSession.getActiveSession()
        yield active if active is not None else SparkSession.builder.getOrCreate()
        return

    # Local: use this environment's Python for Spark's Python workers, so they
    # match the .venv (matters on Windows, where "python3" may not exist).
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    session = (
        SparkSession.builder.master("local[1]")
        .appName("brisbane-house-finder-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture
def test_files_dir(tmp_path: Path) -> Iterator[Path]:
    """Return an empty folder for test files that Spark reads."""
    root = os.environ.get(TEST_FILES_ROOT_VARIABLE)
    if root is None:
        yield tmp_path
        return

    # On Databricks: one new folder per test, deleted when the test ends.
    folder = Path(root) / f"pytest-{uuid.uuid4().hex}"
    folder.mkdir(parents=True)
    try:
        yield folder
    finally:
        shutil.rmtree(folder)
