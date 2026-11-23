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
- CI, workflow `Pipeline observability`, run 45093416417 on commit `9e1efe0`
  (GitHub-hosted ubuntu-latest, Python 3.11; all data **synthetic**):
  - `unit`: 87 passed, 0 failed, 0 skipped (including the PostgreSQL 16 run-store
    test); line+branch coverage of `fleetflow_observability` 98%; ruff 0.16.9 and
    black 26.5.1 clean; both DAG files compile.
  - `promtool` (Prometheus v2.53.2): `check config`, `check rules` and
    `test rules` passed (4 rule-test groups, 5 rules).
  - `e2e`: real `dbt source freshness` (dbt-core 1.8.8, dbt-postgres 1.8.2,
    PostGIS 15-3.3). Stale scenario: dbt exited 1 with orders=pass, routes=pass,
    drivers=warn (30 h old), route_stops=error (50 h old); every verdict matched
    the independent recomputation. After real `UPDATE`s fired the schema's
    `updated_at` triggers, all 4 sources passed and dbt exited 0. The webhook
    receiver got exactly 3 alerts (failed dbt run, drivers warn, route_stops error).
    In a live node_exporter v1.8.2 + Prometheus v2.53.2 run, the stale metrics fired
    `FleetflowPipelineRunFailed` and `FleetflowSourceFreshnessError{table="route_stops"}`,
    left `FleetflowSourceFreshnessWarn{table="drivers"}` pending (15 m `for`), and
    did not fire for orders. After the recovered metrics were swapped in, no
    alerts were active.
  - The first CI run failed only on black formatting (CI pinned black 24 while
    local used 26). Fixed by pinning the linters to the local versions.

**Status:** COMPLETED & VERIFIED

**Not done / honest limits:** no real paging endpoint is configured; Airflow
callbacks are tested with Airflow-shaped context objects, not a running
Airflow; SLA values are reasonable defaults, not agreed with an operations team.
