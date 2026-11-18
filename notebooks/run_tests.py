# Databricks notebook source
# MAGIC %md
# MAGIC # Run unit tests on Databricks
# MAGIC Runs the repo's pytest suite on serverless compute before a PR is opened.
# MAGIC Tests use this notebook's Spark session (see `tests/conftest.py`).
# MAGIC Uses Free Edition quota, so run it once per PR, not on every change.

# COMMAND ----------

# MAGIC %pip install pytest==9.2.0

# COMMAND ----------

import os
import sys

import pytest

# Tell tests/conftest.py to use this notebook's Spark session.
os.environ["BHF_TEST_SPARK"] = "databricks"

# Do not write .pyc files into the Git folder.
sys.dont_write_bytecode = True

# Run from the repo root (the parent of this notebook's folder), so pytest
# finds pyproject.toml and the tests/ folder.
notebook_path = (
    dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()  # noqa: F821
)
repo_root = os.path.dirname(os.path.dirname(notebook_path))
os.chdir(f"/Workspace{repo_root}")

# -p no:cacheprovider: do not write a .pytest_cache folder into the Git folder.
retcode = pytest.main(["tests", "-v", "-p", "no:cacheprovider"])
assert retcode == 0, "Some tests failed. Read the output above."
