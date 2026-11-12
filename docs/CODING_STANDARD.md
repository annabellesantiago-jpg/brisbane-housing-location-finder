**STYLE:**
- ruff check . must pass before every PR
- Naming convention:
    - *functions and variables* - snake_case
    - *classes* - CamelCase
    - *constants* - UPPER_CASE
- Type hints and a docstring on every public functions

**CODE LOCATIONS:**
- Pipeline logic goes in src/brisbane_house_finder/; notebooks only call it.
- No hard-coded catalog names. 
  The catalog (brisbane_housing_dev / brisbane_housing_prod) is passed in as a parameter, so the same code runs in DEV and PROD.

**PYSPARK:**
- Transformation functions take a DataFrame and return a DataFrame. That keeps them testable.
- No .cache(): it isn’t supported on serverless.
- No .collect() / .toPandas() on large data.
- Column names in snake_case.

**LOGGING:**
- Create a common function for logging, never use print(). 
- One logger per module: logger = logging.getLogger(__name__). 
  This reads as: get a logger named after this file, so each log line shows where it came from.
- Levels: INFO for progress (e.g. row counts), WARNING for recoverable issues, ERROR for failures.

**ERROR HANDLING:**
- Catch specific exceptions, never a bare except:.
- Never hide an error: log it and re-raise, or raise a clearer one.
- Fail fast on bad data, e.g. a Bronze row count that doesn’t match the source count raises an error.

**SECRETS:**
- Never in code, notebooks or the repo. Use Databricks secrets and GitHub Secrets.

**GIT:**
- Branches: feature/<short-description>.
- Commits: PRxxx: <what changed>. Example: PR001, PR100
- PRs go into dev, merged with Squash and merge.

**TESTING:**
- Use pytest: one tests/test_<module>.py per module.
- Tests use small in-memory data, never the real files.
