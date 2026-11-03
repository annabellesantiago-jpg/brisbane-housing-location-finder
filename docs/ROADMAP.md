# Brisbane Housing Location Finder: Flood, Crime, Amenity & Transport Scoring Pipeline — Project Roadmap

**Repo name:** `brisbane-housing-location-finder`
**Architecture:** Medallion (Bronze → Silver → Gold) on Databricks Free Edition, Unity Catalog, Delta Lake, native spatial SQL (`ST_` functions).
**Roles (peer development):** Annabelle is Lead Architect and owns the business and data-modelling decisions. Both of us write code, taking turns driving and reviewing. Every piece of code is reviewed by the other before it is committed.
**Data policy:** free, publicly downloadable data only.

---

## 1. Business problem

> *Which Brisbane suburbs best combine low flood risk, low crime, good public transport, and nearness to schools, hospitals/clinics and groceries/malls?*

**Users**
1. Annabelle's family, relocating to Brisbane: full detail in Databricks (dashboard + Genie).
2. Other families in the same situation: a free public web page.

**Output:** one score and rank per suburb, plus the facts behind it:

| Factor | Measures |
|---|---|
| Flood | % of suburb area in each flood-likelihood band (High / Medium / Low / Very Low); % flooded in Jan 1974 and Jan 2011 |
| Crime | offence rate of the police division the suburb belongs to, recent 12 months and trend |
| Amenities | distance to nearest school, hospital/clinic, grocery/mall; counts within a chosen radius |
| Transport | distance to nearest stop; number of services per hour at nearby stops |

**Limits of the result.** These must be shown wherever the score appears.
- Suburb-level screening, not advice. For a specific address, use Brisbane City Council's **FloodWise Property Report**.
- The council flood-likelihood map was created in **June 2013**; its data was last edited **17 Oct 2024** (layer metadata, checked 3 Nov 2026).
- Crime is published by **police division** (several suburbs each), not by suburb.
- No house prices or rents (no free source found).

---

## 2. Platform facts that shape the design

| Fact | Design consequence |
|---|---|
| Databricks Free Edition: serverless compute only; no caching, no RDD API; most Spark configurations can't be set. | Lean, column-pruned code. No `.cache()`. |
| Public DBFS root disabled. | Landing zone is a Unity Catalog **Volume**. |
| Outbound internet restricted. | Datasets are downloaded by hand and uploaded to the Volume. |
| Native spatial functions **verified 5 Oct 2026** on serverless notebook compute and the Serverless Starter Warehouse. | Spatial work uses built-in `ST_` functions; no external libraries. |
| Sharing dashboards with non-workspace users needs an account console. Free Edition has none. | Databricks serves Annabelle only. The public gets a static page outside Databricks. |
| Genie availability on Free Edition **not yet confirmed**. | Create one test Genie space before relying on it. |
| Account-wide serverless quota has been hit before. | Start each hands-on session with `spark.range(1).show()`. |

---

## 3. Structural overview

```
 Manual download (free sources)            Unity Catalog: <catalog>
 BCC · QLD Govt · QPS · Translink · OSM   ┌───────────────────────────────────────────────────┐
        │                                 │ LANDING (Volume)  raw GeoJSON / CSV / GTFS files  │
        └── upload ─────────────────────► │      ▼  ingest as-is + audit columns             │
                                          │ BRONZE  one table per source                      │
                                          │      ▼  parse geometry · fix coordinate system    │
                                          │      ▼  standardise · de-duplicate · validate     │
                                          │ SILVER  suburbs · flood_zones · flood_extents ·   │
                                          │         schools · health_facilities · shops ·     │
                                          │         police_divisions · offences_monthly ·     │
                                          │         transit_stops · stop_service_frequency    │
                                          │      ▼  overlap · nearest distance · weighting    │
                                          │ GOLD    dim_suburb · suburb_flood_exposure ·      │
                                          │         suburb_crime · suburb_amenity_access ·    │
                                          │         suburb_transport_access · suburb_score    │
                                          │ OPS     run log · data-quality results            │
                                          └──────────────┬──────────────────────┬─────────────┘
                                                         │                      │
                                  PRIVATE (Annabelle)    ▼                      ▼  PUBLIC (free)
                                  AI/BI dashboard + Genie space     GitHub Actions: query Gold via the
                                                                    Databricks SQL API → JSON + CSV
                                                                    → GitHub Pages: filter page +
                                                                      CSV download
```

### Spatial concepts used (one line each)
- **Geometry**: a shape in a column — a point (school) or a polygon (suburb, flood zone).
- **Coordinate system (SRID)**: latitude/longitude is SRID **4326** (degrees). Brisbane's projected grid, MGA zone 56, is SRID **28356** (metres). Areas and distances are measured in 28356, after `st_transform`.
- **Point-in-polygon**: "is this school inside this suburb?" → `st_contains`.
- **Overlap**: "how much of this suburb is in a High flood zone?" → intersect the shapes, then measure the area.
- **Distance**: "how far to the nearest hospital?" → `st_distance` in metres.

---

## 4. Roadmap

Each factor is added as its own stage. Every stage runs Bronze → Silver → Gold for its datasets and ends with a working, updated score.

### Step 0 — Foundations
- **Deliverables:** GitHub repo in a Databricks Git Folder; repo skeleton; Unity Catalog catalog, schemas (`landing`, `bronze`, `silver`, `gold`, `ops`) and landing Volume; coding standards (PEP 8, logging, error handling); pytest; GitHub Actions running lint and unit tests; one test Genie space to confirm Free Edition support; service principal test (create, OAuth secret, job run-as, grants).
- **Decisions:** catalog layout (decided: `brisbane_housing_dev` / `brisbane_housing_prod`); repo name (decided: `brisbane-housing-location-finder`); branching (decided).

### Stage 1 — Flood + amenities (MVP)
- **Datasets:** suburb boundaries, flood risk zones, 1974 and 2011 flood extents, schools, hospitals/clinics, groceries/malls (OpenStreetMap).
- **Bronze:** each file loaded as-is with audit columns. GeoJSON `FeatureCollection` files become one row per feature (`explode` of `features`), geometry kept as raw text.
- **Silver:** geometry parsed and tagged with its SRID; invalid geometries quarantined; facilities standardised and de-duplicated; each facility assigned to a suburb.
- **Gold:** `dim_suburb`, `suburb_flood_exposure`, `suburb_amenity_access`, first `suburb_score`.
- **Serving (private):** AI/BI dashboard (suburb map + shortlist) and Genie space.
- **Orchestration:** Lakeflow Job, Bronze → Silver → Gold, with retries and failure notification.
- **Decisions:** facility types that count; scoring weights; how the four flood bands combine into one number; radius for "nearby"; any hard exclusion (e.g. more than X% of area in the High band).

### Stage 2 — Crime
- **Datasets:** QPS offence numbers and rates by police division (monthly, from July 2001); QPS division boundaries.
- **Pipeline:** each suburb is mapped to its police division by spatial overlap. Monthly offence data gives a time series: recent 12-month rate and trend.
- **Check on download:** whether each file holds the full history or only new months. That decides between append-only loading and `MERGE` (upsert).
- **Decisions:** which offence categories count (e.g. offences against the person and property, not traffic); suburbs that straddle two divisions; rate vs count.

### Stage 3 — Transport
- **Datasets:** Translink timetable feed (GTFS): `stops`, `trips`, `stop_times`, `calendar`, `routes`.
- **Pipeline:** stops become points; `stop_times` (millions of rows) aggregated into services per hour per stop for a typical weekday peak; nearest-stop distance and nearby service level per suburb.
- **Decisions:** which modes count (bus, train, ferry); peak window; "frequent service" threshold.

### Stage 4 — Public page (free)
- **Deliverables:**
  - a GitHub Actions workflow that queries the Gold `suburb_score` table through the Databricks SQL API (token in GitHub Secrets) and writes `suburb_scores.json` and `suburb_scores.csv`
  - a static page on **GitHub Pages**: suburb map, filters and weight sliders that re-rank suburbs in the browser, and a CSV download link
  - a short "ask your own AI" guide with example questions for the CSV
  - an attribution and disclaimer section
- **Decisions:** which columns are public; refresh schedule; page layout.

### Throughout — CI/CD and packaging
Declarative Automation Bundle (`databricks.yml`) for the job; unit tests on every PR; README (problem → design → result); Architecture Decision Records; data dictionary; download manifest.

**Branching and deployment strategy (decided 6 Oct 2026):**

```
feature/<name>  ──PR──►  dev  ──PR──►  main
     │                    │              │
 local testing +     deploys to      deploys to
 bundle validate     DEV target      PROD target
```

| Branch | What happens |
|---|---|
| `feature/<name>` | Code written and unit-tested locally; `databricks bundle validate`. |
| PR → `dev` | CI runs lint + unit tests. On merge, the bundle deploys to the **DEV** target. |
| PR → `main` | On merge, the bundle deploys to the **PROD** target. |

**Free Edition constraint:** one workspace only. "DEV" and "PROD" are **bundle targets in the same workspace**, separated by catalog or schema (e.g. `dev_` and `prod_` prefixes), not separate workspaces.

**Identity and access principle (decided 6 Oct 2026):** use **service principals**, not personal accounts, for job ownership and data access, so the pipeline keeps running and access stays controlled if a person's account changes.

| Where | Identity |
|---|---|
| PROD job owner and "run as" | Service principal (bundle `run_as` on the PROD target) |
| PROD data access (catalog, schemas, Volume, tables) | Grants to the service principal, least privilege: `USE CATALOG`, `USE SCHEMA`, `READ VOLUME` / `WRITE VOLUME`, `SELECT` / `MODIFY` only where needed |
| GitHub Actions → Databricks (deploy, and later the public-page export) | Service principal with OAuth machine-to-machine credentials in GitHub Secrets, instead of a personal access token |
| DEV target | Developer's own identity (normal for development) |

**To verify in Step 0:** that Free Edition lets the workspace admin create a service principal, generate its OAuth secret, and set it as a job's "run as". The docs say workspace admins can add service principals from workspace admin settings; Free Edition has no account console. If any part is not possible, record it as a known limitation and an Architecture Decision Record.

---

## 5. Datasets (all free)

| Stage | Dataset | Publisher | Shape | Notes |
|---|---|---|---|---|
| 1 | Suburb Boundaries | Brisbane City Council (BCC) | Polygons | Brisbane LGA suburbs (localities) |
| 1 | Flood — Awareness — Flood Risk Overall | BCC | Polygons | `FLOOD_RISK`: High 5% / Medium 1% / Low 0.2% / Very Low 0.05% annual chance; `FLOOD_TYPE`; created June 2013, data last edited 17 Oct 2024 |
| 1 | Flood — Awareness — Historic — Brisbane River Floods — Jan 1974 | BCC | Polygons | |
| 1 | Flood — Awareness — Historic — Brisbane River Floods — Jan 2011 | BCC | Polygons | |
| 1 | State and non-state school details | Queensland Government | Points | Check lat/lon columns |
| 1 | Queensland public hospitals; Health and Medical Facilities | Queensland Government | Points | Check lat/lon columns |
| 1 | Supermarkets and shopping centres | OpenStreetMap (Overpass Turbo export or Geofabrik) | Points/polygons | Credit "© OpenStreetMap contributors" (ODbL) |
| 2 | Offence numbers / rates — police divisions — monthly from July 2001 | Queensland Police Service (QPS) | Table (CSV) | Division level, not suburb |
| 2 | QPS Divisions | QPS | Polygons | Updated monthly |
| 3 | Translink GTFS — South East Queensland | Translink | Tables (CSV in zip) | `stop_times` is the large table |

**Download notes**
- Export BCC polygon datasets as **GeoJSON** (SRID 4326 by specification). Record the coordinate system of every file in the manifest.
- Check each CSV's delimiter and header row before uploading.
- Record each dataset's licence and the attribution it requires. Queensland Government and BCC open data is generally CC BY 4.0; confirm per dataset.
- Keep raw downloads out of the Git repo (`.gitignore`).

---

## 6. Bronze — decisions for the Lead Architect

| # | Decision | Options |
|---|---|---|
| B1 | Ingestion approach | (a) PySpark + Auto Loader · (b) Lakeflow Spark Declarative Pipelines · (c) `COPY INTO` |
| B2 | Catalog | **Decided 9 Oct 2026:** two catalogs, `brisbane_housing_dev` and `brisbane_housing_prod`, each with schemas `landing`, `bronze`, `silver`, `gold`, `ops` |
| B3 | Landing folder convention | e.g. `<publisher>/<dataset>/<YYYY-MM-DD>/<file>` |
| B4 | Geometry in Bronze | raw GeoJSON text (parse in Silver) vs parsed `GEOMETRY` column |
| B5 | Column naming | keep source names vs normalise to snake_case |
| B6 | Audit columns | source file, file modified time, ingest timestamp, run ID, download date |
| B7 | Unexpected or bad records | rescued-data column vs fail the load vs quarantine table |
| B8 | Run logging | ops run-log table vs job logs only |

---

## 7. Decisions already made

| Date | Decision |
|---|---|
| 2026-10-05 | Project changed from transit analytics to housing location scoring. |
| 2026-10-06 | Four factors: flood, crime, amenities (school, hospital/clinic, grocery/mall), transport. Added in stages. |
| 2026-10-06 | Free, publicly downloadable data only. |
| 2026-10-06 | Private serving: AI/BI dashboard + Genie space. RAG not used (the data is tables, not documents). MCP not in scope. |
| 2026-10-06 | Hard deadline 28 Feb 2027: private dashboard + Genie live with all four factors. Public page (Stage 4) comes after the deadline. |
| 2026-10-06 | Capacity: 20 hours per week. |
| 2026-10-06 | Vacation 9 Dec 2026 – 12 Jan 2027: no project work. |
| 2026-10-06 | Buffer: keep full scope; add hours before the vacation. Checkpoint on 8 Dec. |
| 2026-10-06 | Branching: feature → PR → `dev` (deploys to DEV target) → PR → `main` (deploys to PROD target). DEV/PROD are bundle targets in the one Free Edition workspace. |
| 2026-10-06 | Project title: *Brisbane Housing Location Finder: Flood, Crime, Amenity & Transport Scoring Pipeline*. Repo: `brisbane-housing-location-finder`. |
| 2026-10-09 | Unity Catalog layout: two catalogs, `brisbane_housing_dev` and `brisbane_housing_prod`, each with schemas `landing`, `bronze`, `silver`, `gold`, `ops`. Project work started early (9 Oct). |
| 2026-10-09 | Overland Flow layer skipped for now: 1,256,924 shapes; the GeoJSON export fails on the council site. Deferred until after the 28 Feb deadline. Dashboard must state that overland (heavy-rain street) flooding is not included. |
| 2026-11-03 | Source ingestion is hybrid: static sources (suburbs, flood layers, schools, health facilities, OpenStreetMap) are downloaded by hand and uploaded to the landing volume; sources that change regularly (QPS crime, monthly; Translink GTFS) are pulled by REST/HTTP code run by a Lakeflow Job. Before Stage 2, test whether Free Edition serverless can reach those hosts; if not, the download code runs outside Databricks (PC or GitHub Actions) and uploads with the CLI. |
| 2026-11-03 | Catalogs, schemas and the landing volume are created by an idempotent SQL script (`setup/01_unity_catalog_setup.sql`), not by the bundle: bundle-managed schemas are dropped with their tables on `bundle destroy`, rename or removal from `databricks.yml`. The bundle (Step 6) manages jobs, pipelines, dashboard and Genie space only. |
| 2026-10-06 | Service principals, not personal accounts, own PROD jobs and hold PROD data access; GitHub Actions authenticates as a service principal. To verify on Free Edition in Step 0. |
| 2026-10-06 | DE Associate exam 20–25 Oct 2026; project work starts after the exam (26 Oct). |
| 2026-10-06 | Public serving: static GitHub Pages site with filters and weight sliders, plus a CSV download for visitors to use with their own AI tool. No hosted chatbot. |

---

## 8. Timeline

**Hard deadline, 28 Feb 2027:** private AI/BI dashboard + Genie space live, covering all four factors (flood, amenities, crime, transport).
**After the deadline:** Stage 4, the public page.
**Fixed dates:** DE Associate exam 20–25 Oct 2026. Vacation in the Philippines **9 Dec 2026 – 12 Jan 2027** (assumed: no project work).
**Capacity:** 20 hours per week baseline; more in the weeks before the vacation.

| Dates | Work | Hours (est.) | Milestone |
|---|---|---|---|
| until 25 Oct | **No project work:** Learning Festival, exam preparation, exam | — | Exam done |
| 26 Oct – 8 Nov | Step 0 foundations; download Stage 1 datasets; manifest | 40 | Repo, catalog and Volume ready |
| 9 Nov – 8 Dec | Stage 1a: suburbs, flood zones, 1974/2011 extents, schools, hospitals/clinics → Gold; first dashboard | 85 | **Before vacation:** flood + schools + hospitals scored, dashboard v1 |
| 9 Dec – 12 Jan | **No project work:** vacation | — | — |
| 13 Jan – 24 Jan | Stage 1b: groceries/malls (OpenStreetMap); Genie space; scoring weights finalised | 35 | Stage 1 complete, Genie live |
| 25 Jan – 7 Feb | Stage 2: crime | 40 | Crime added to score |
| 8 Feb – 21 Feb | Stage 3: transport | 40 | Transport added to score |
| 22 Feb – 28 Feb | Buffer; README, decision records, data dictionary, final checks | 20 | **28 Feb: private dashboard + Genie live, all four factors** |
| from 1 Mar | Stage 4: public page (GitHub Actions + GitHub Pages) | ~40 | Public page live |

**Capacity vs plan:** about 13 working weeks (6.3 before the vacation, 6.7 after) × 20 h ≈ 260 h. Planned work ≈ 260 h. **Buffer is one week only.**

**Buffer decision (6 Oct 2026):** keep full scope and add project hours in the weeks before the vacation (26 Oct – 8 Dec), amount managed by Annabelle. Not chosen: simplifying transport to nearest-stop distance; shortening Step 0 by reusing the market risk setup.

**Checkpoint, 8 Dec:** re-check the hour estimates against actual progress before the vacation. If Stage 1a is behind, decide then whether to simplify transport.

**Risk:** Stage 1 includes learning PySpark and spatial work together. If Stage 1a is not done by 8 Dec, it continues from 13 Jan and uses the buffer.

---

## Sources
- Databricks: [Free Edition limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations) · [Serverless compute limitations](https://docs.databricks.com/aws/en/compute/serverless/limitations) · [ST geospatial functions](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-st-geospatial-functions) · [Sharing AI/BI dashboards](https://www.databricks.com/blog/sharing-aibi-dashboards)
- Brisbane City Council: [Suburb Boundaries](https://data.brisbane.qld.gov.au/explore/dataset/suburb-boundaries/) · [Flood Risk Overall](https://data.brisbane.qld.gov.au/explore/dataset/flood-awareness-flood-risk-overall/) ([layer metadata](https://services2.arcgis.com/dEKgZETqwmDAh1rP/ArcGIS/rest/services/Flood_Awareness_Flood_Risk_Overall/FeatureServer/0)) · [Historic flood Jan 1974](https://www.data.qld.gov.au/dataset/flood-awareness-historic-brisbane-river-floods-jan-1974) · [Historic flood Jan 2011](https://www.spatial-data.brisbane.qld.gov.au/datasets/brisbane::flood-awareness-historic-brisbane-river-floods-jan2011/explore) · [Flooding in Brisbane / FloodWise](https://www.brisbane.qld.gov.au/community-support-and-safety/natural-disasters-and-emergencies/flooding-in-brisbane)
- Queensland Government: [State and non-state school details](https://www.data.qld.gov.au/dataset/state-and-non-state-school-details) · [Queensland public hospitals](https://www.data.qld.gov.au/dataset/queensland-public-hospitals) · [Health and Medical Facilities](https://queensland.opendatasoft.com/explore/dataset/health-and-medical-facilities/)
- Queensland Police Service: [Crime datasets](https://www.data.qld.gov.au/dataset/?tags=crime) · [QPS Divisions](https://www.data.qld.gov.au/dataset/qps-divisions)
- Translink: [GTFS — South East Queensland](https://www.data.qld.gov.au/dataset/general-transit-feed-specification-gtfs-translink)
- OpenStreetMap: [Geofabrik — Australia](https://download.geofabrik.de/australia-oceania/australia.html)
