# Coding Standards

## Style
- Follow PEP8, `ruff check .` must pass before every PR
- Naming convention:
    - *functions and variables* - snake_case
    - *classes* - PascalCase
    - *constants* - UPPER_CASE
- Type hints and a docstring on every public function.

## Code Locations
- Pipeline logic goes in `src/brisbane_house_finder/`; notebooks only call it.
- No hard-coded catalog names. 
  The catalog (brisbane_housing_dev / brisbane_housing_prod) is passed in as a parameter, so the same code runs in DEV and PROD.

## PySpark
- Transformation functions take a DataFrame and return a DataFrame. That keeps them testable.
- No `.cache()`: it isn’t supported on serverless.
- No `.collect()` / `.toPandas()` on large data.
- Column names in snake_case.

## Logging
- Logging is configured once per run with the shared helper in brisbane_house_finder; modules never call `print()`. 
- One logger per module: `logger = logging.getLogger(__name__)`. 
  This reads as: get a logger named after this file, so each log line shows where it came from.
- Levels: *INFO* for progress (e.g. row counts), *WARNING* for recoverable issues, *ERROR* for failures.

## Error Handling
- Catch specific exceptions, never a bare `except:`.
- Never hide an error: log it and re-raise, or raise a clearer one.
- Fail fast on bad data, e.g. a Bronze row count that doesn’t match the source count raises an error.

## Secrets
- Never in code, notebooks or the repo. Use Databricks secrets and GitHub Secrets.

## Git
- Branches: `feature/<short-description>`.
- Commits: `PRxxx: <what changed>`. Example: `PR001`, `PR100`
- PRs go into dev, merged with Squash and merge.

## Testing
- Use pytest: one `tests/test_<module>.py` per module.
- Tests use small in-memory data, never the real files.
