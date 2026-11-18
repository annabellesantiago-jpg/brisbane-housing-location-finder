"""Shared pytest fixtures.

The ``spark`` fixture gives tests a Spark session in two places:

* On a PC or in GitHub Actions CI (default): a small local PySpark session.
  Uses no Databricks compute, so it does not count towards the Free Edition quota.
* On Databricks: the session of the notebook that runs the tests. The runner
  notebook ``notebooks/run_tests`` sets ``BHF_TEST_SPARK=databricks`` before it
  calls pytest.

Tests that need Spark take ``spark`` as an argument and are marked
``@pytest.mark.spark``, so they can be selected or skipped with
``pytest -m spark`` / ``pytest -m "not spark"``.
"""

import os
import sys
from collections.abc import Iterator

import pytest
from pyspark.sql import SparkSession

SPARK_MODE_VARIABLE = "BHF_TEST_SPARK"


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
