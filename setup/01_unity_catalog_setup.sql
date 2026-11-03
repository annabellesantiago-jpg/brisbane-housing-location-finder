-- =============================================================================
-- 01_unity_catalog_setup.sql
-- Creates the Unity Catalog objects for the Brisbane Housing Location Finder.
--
-- Layout (decision S0-1, 9 Oct 2026): one catalog per environment, each with
-- the same five schemas, and one managed volume for raw landing files.
--
-- Safe to re-run: every statement uses IF NOT EXISTS.
-- Run in: Databricks SQL editor or a notebook %sql cell.
-- =============================================================================

-- ---------------------------------------------------------------- DEV ------
CREATE CATALOG IF NOT EXISTS brisbane_housing_dev
  COMMENT 'Brisbane Housing Location Finder - development environment';

CREATE SCHEMA IF NOT EXISTS brisbane_housing_dev.landing
  COMMENT 'Raw source files as downloaded, held in a volume';
CREATE SCHEMA IF NOT EXISTS brisbane_housing_dev.bronze
  COMMENT 'Raw data loaded as tables, plus audit columns';
CREATE SCHEMA IF NOT EXISTS brisbane_housing_dev.silver
  COMMENT 'Cleaned, typed, validated data';
CREATE SCHEMA IF NOT EXISTS brisbane_housing_dev.gold
  COMMENT 'Suburb-level scores and facts for the dashboard and Genie';
CREATE SCHEMA IF NOT EXISTS brisbane_housing_dev.ops
  COMMENT 'Run logs and data-quality results';

CREATE VOLUME IF NOT EXISTS brisbane_housing_dev.landing.raw_files
  COMMENT 'Landing zone: source files uploaded by hand';

-- ---------------------------------------------------------------- PROD -----
CREATE CATALOG IF NOT EXISTS brisbane_housing_prod
  COMMENT 'Brisbane Housing Location Finder - production environment';

CREATE SCHEMA IF NOT EXISTS brisbane_housing_prod.landing
  COMMENT 'Raw source files as downloaded, held in a volume';
CREATE SCHEMA IF NOT EXISTS brisbane_housing_prod.bronze
  COMMENT 'Raw data loaded as tables, plus audit columns';
CREATE SCHEMA IF NOT EXISTS brisbane_housing_prod.silver
  COMMENT 'Cleaned, typed, validated data';
CREATE SCHEMA IF NOT EXISTS brisbane_housing_prod.gold
  COMMENT 'Suburb-level scores and facts for the dashboard and Genie';
CREATE SCHEMA IF NOT EXISTS brisbane_housing_prod.ops
  COMMENT 'Run logs and data-quality results';

CREATE VOLUME IF NOT EXISTS brisbane_housing_prod.landing.raw_files
  COMMENT 'Landing zone: source files uploaded by hand';

-- ---------------------------------------------------------------- CHECK ----
SHOW SCHEMAS IN brisbane_housing_dev;
SHOW VOLUMES IN brisbane_housing_dev.landing;

SHOW SCHEMAS IN brisbane_housing_prod;
SHOW VOLUMES IN brisbane_housing_prod.landing;