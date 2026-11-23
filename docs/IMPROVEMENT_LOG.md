# FleetFlow improvement log

One entry per improvement PR. Every number below comes from a run that was
actually executed (CI or local) and the conditions are stated; synthetic data is
labelled as such. Status is one of **COMPLETED & VERIFIED**, **IMPLEMENTED BUT
NOT VERIFIED** or **BLOCKED**.

Context: a stack of open PRs (#1-#23) and the lakehouse PR (#25) already cover
the Backend Tests/lint fix (#1), the routing benchmark (#11, #20), Kafka
ingestion (#2, #7, #8) and the dispatch API (#4-#6). Entries here avoid
duplicating them.

## 2026-11-23 - Pipeline observability: run metrics, dbt source freshness, failure alerts

**Branch:** `improve/pipeline-observability-20261123` (backlog item 4)

**What changed**

- `data-engineering/observability/`: stdlib-only package `fleetflow_observability`
  - run store (JSONL; SQL via DB-API with upsert, tested on SQLite and PostgreSQL),
    `track_run` context manager and `track -- <cmd>` CLI that record duration,
    rows, status and error, and alert on failure without masking it;
  - parser for dbt `sources.json` that independently recomputes every freshness
    verdict from the timestamps and thresholds (dbt's exclusive `>` rule);
  - Prometheus text exposition (atomic textfile writes for node_exporter);
  - alerts: Slack-compatible webhook with retry/backoff (no retry on 4xx except
    429), http(s)-only URL validation, JSON-state de-duplication window, log sink;
  - Airflow `on_failure_callback` / `on_success_callback` (no Airflow import).
- `data-engineering/dbt/models/schema.yml`: freshness SLAs + `loaded_at_field` on
  `orders`, `drivers`, `routes`, `route_stops`; reference tables explicitly have none.
- `monitoring/alerts/pipeline_alerts.yml` (5 rules) + `promtool` unit tests;
  `prometheus.yml` loads them; `docker-compose.yml` mounts them and adds
  node_exporter with the textfile collector.
- Airflow DAGs `daily_optimization` and `hourly_forecast` wire the callbacks via
  an optional import.
- `.github/workflows/observability.yml`: unit tests + lint, promtool, a real
  `dbt source freshness` run against PostGIS with a **synthetic** stale ->
  recovered scenario, webhook delivery check, and a live node_exporter +
  Prometheus run asserting alerts fire and then resolve; results posted as a PR
  comment with log tails on failure.

**Evidence**

- Local (Python 3.13, sandbox without network; no dbt/PostGIS/Docker available):
  `pytest` 86 passed, 1 skipped (PostgreSQL store test needs a DSN); ruff and
  black clean.
- CI: _pending - filled in after the workflow runs._

**Status:** IMPLEMENTED BUT NOT VERIFIED (awaiting CI)

**Not done / honest limits:** no real paging endpoint is configured; Airflow
callbacks are tested with Airflow-shaped context objects, not a running
Airflow; SLA values are reasonable defaults, not agreed with an operations team.
