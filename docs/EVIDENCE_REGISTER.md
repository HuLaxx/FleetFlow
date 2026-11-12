## Current verified five-job CI — 12 November 2026

- **PASS:** [Backend Tests workflow 43270546627](https://github.com/HuLaxx/FleetFlow/actions/runs/43270546627), commit `c5d706926859620d62f2d3ff5f483921fa1fd4d1`, checked against the PR head at the time of verification.
- **Backend tests, backend Ruff/Black, CPU ML smoke, Next.js frontend ESLint (0 errors; 13 non-blocking warnings), TypeScript, frontend production build and Trivy high/critical dependency scan all passed** in this same workflow.
- The production frontend compiles with patched Next.js 16.4.6, Auth.js/Drizzle and MapLibre 6.4.1; **a passing build is not an interactive browser smoke test** or proof all map controls work after the major MapLibre upgrade.
- Remaining P0 acceptance: authenticated end-to-end dispatch through actual seeded depot/orders, WebSocket event replay and duplicate-handling, route optimization benchmark, browser map smoke tests, hosted deployment and observability.
- Keep draft; no production deployment or merge until acceptance evidence is supplied.

## P0 extended CI and security review — 12 November 2026

- Backend pytest has **43 passing tests with zero skips**, with separate passing CPU ML smoke tests and backend Ruff/Black checks in current review-branch workflows.
- Following Next.js **16.4.6** and patched Auth.js, Drizzle ORM, MapLibre and transitive dependencies, the **high/critical dependency security scan passed** in [run 43265770572](https://github.com/HuLaxx/FleetFlow/actions/runs/43265770572). Backend, lint and ML jobs passed in that run.
- The new strict frontend lint/type/build job **remains red**. An earlier run showed 58 ESLint errors; a later completed run showed 26 after typed-map, dashboard and socket repairs. The latest source revisions and all static/build results still require verification on the current head.
- MapLibre was upgraded across major versions. A passing dependency scan is not evidence that map rendering or API integration works. Seeded dispatch, replay, idempotency, failure recovery and benchmark gates remain open.

# FleetFlow — Engineering Evidence Register

Updated: 2026-11-12. This is a truthful readiness inventory, not a claim of a production deployment.

## Status key
**Verified**: current execution evidence; **Implemented, unverified**: source path/config exists, integrated behaviour not reproduced here; **Mock**: illustrative data or incomplete workflow; **Planned**: proposal or template.

| Capability | Current status | Evidence | Next acceptance gate |
|---|---|---|---|
| Backend order/vehicle CRUD | Implemented, integration unverified | [API routes](../backend/src/api/routes/), [models](../backend/src/models/) | Seed and test order/driver/vehicle lifecycle |
| OR-Tools route candidate | Implemented, not persisted approval flow | [Optimizer](../ml/route_optimizer.py), [API](../backend/src/api/routes/optimization.py) | Compare baseline; accept and persist a feasible plan |
| Kafka event and WebSocket telemetry modules | Implemented, integrated behaviour unverified | [Event producer](../backend/src/events/producer.py), [WebSocket server](../backend/src/websocket_server.py) | Duplicate, retry, replay and live browser update tests |
| Flink-labelled processor | Simplified Python, **not** verified native Flink | [Processor](../data-engineering/flink/stream_processor.py), [README](../README.md) | Implement native Flink and prove job, or rename honestly |
| Airflow DAGs / dbt marts | Implemented, unverified | [Airflow](../data-engineering/airflow/dags/), [dbt](../data-engineering/dbt/models/) | Seed-to-warehouse data-quality and reconciliation checks |
| Hosted map | Uses sample/illustrative geometry | [Frontend](../frontend/), [README](../README.md) | Distinguish samples and genuine tracking states |
| Frontend and ML evaluation CI on `redesign/fleetflow-v2` (not main) | **Verified passing on that branch's inspected commit only** | [Run 2026-11-11](https://github.com/HuLaxx/FleetFlow/actions/runs/42981274657) | Preserve pass; independently run full-stack checks |
| Local full readiness | Not executed in this audit environment | [Readiness script](../scripts/validate-local.sh), [criteria](local-readiness.md) | Reproduce infra, seeds, APIs, frontend and ML results |
| AWS deployment | Not independently verified | [Local/infra docs](local-stack.md) | Define minimal serverless plan and seek explicit cost approval |

## New PR evidence (2026-11-12)

- New event-contract tests verify v1 schema version, generated IDs, UTC timestamps, invalid coordinates and JSON serialization. **All 7 new event-contract cases passed** in [PR run 43200462763](https://github.com/HuLaxx/FleetFlow/actions/runs/43200462763).
- Event models now emit a backwards-compatible `schema_version=1` and timezone-aware UTC `timestamp`. This does not implement consumer-side deduplication or replay.
- The earlier test suite had exception-swallowing Kafka consumer tests, which were replaced with explicit side-effect/rejection assertions; [PR run 43201270202](https://github.com/HuLaxx/FleetFlow/actions/runs/43201270202) verifies all **five rewritten consumer tests passing**; full broker delivery and exactly-once effects remain unverified.
- The existing backend CI run reported extensive Ruff debt (475 errors) plus older API fixture/consumer test failures. The `sqlalchemy[asyncio]` extra was added to address missing `greenlet` reported during imports. The latest run reports **19 passed, 6 skipped and 16 setup errors**, with legacy lint still failing. Full CI is **not green**.

## P0 observation
The inspected recent CI on branch `redesign/fleetflow-v2` checked frontend quality and ML evaluation and passed. This is not proof of CI on `main`. This does **not** prove the full Kafka-to-DB-to-optimiser-to-WebSocket-to-analytics chain, nor does it verify every optional Airflow, Flink, MLflow or OSRM service. The local readiness script can be resource intensive and requires Docker and multiple services.

## Required golden-path proof
1. Deterministic orders, drivers and vehicles, with event contract and UTC timestamps.
2. Idempotent ingestion with replay, DLQ and data-quality checks.
3. Constrained optimiser returning a candidate; separate explicit approval and durable dispatch.
4. Telemetry event reaches map and analytics; UI handles stale state and reconnect.
5. Compare distance, feasibility, unassigned stops and solve time to reproducible baseline.
6. Document local run steps, input seed/hash, logs, assertions, limits and AWS cost plan.

## Priority 1 — additional verified evidence (2026-11-12)

- [PR run 43247824892](https://github.com/HuLaxx/FleetFlow/actions/runs/43247824892): the backend test job **passed** with **37 tests passed, 6 skipped, no failures**, and **58% overall backend statement coverage**. The **separate lint job failed**, so overall CI is not green.
- The isolated PostGIS API fixtures exposed and helped fix real defects: missing required Customer geography on create, incorrectly typed SQL date filters, outdated Strawberry GraphQL IDE option, and asynchronous connection reuse between test event loops.
- Two new consumer tests proved **manual offset commits happen only after successful event processing**, and handler failures propagate without committing that offset. This is at-least-once behaviour, **not** end-to-end deduplication or exactly-once delivery.
- The six skips came from incorrect path-based imports and optional PyTorch. A subsequent change repairs the route optimizer import path and its metres-versus-kilometres assertion. That newer CI run must be checked before declaring the optimiser tests verified.
- The project still needs an outbox/inbox idempotency design and a broker-backed replay/DLQ integration test before it can be called reliable under restarts.

## ML CPU validation (2026-11-12)

- [Workflow run 43249222763](https://github.com/HuLaxx/FleetFlow/actions/runs/43249222763), job **ML CPU smoke (no GPU)**: **3/3 passed** in 2.89 seconds (OR-Tools distance units, PyTorch finite forward pass, one gradient-training step).
- These are implementation smoke tests, **not** forecasting-accuracy, generalisation or routing-efficiency benchmarks. Those require datasets, held-out baselines and reproducible evaluation.
- Separate backend lint remains failed in the same workflow. Do not badge the overall pipeline green.

## Current P0 release gate (2026-11-12)

- **PASS**: [Workflow 43257165244](https://github.com/HuLaxx/FleetFlow/actions/runs/43257165244), commit `6d0b6ccc79ac1be4b27132b6b30e85d83a2a08cd`, matches current draft PR head at time of verification. **43 backend tests passed, 0 skipped; ML CPU smoke passed; Ruff and Black passed**.
- Framework-specific B008 exemptions are documented in `backend/pyproject.toml` for FastAPI dependency descriptors; no failed tests were disabled or marked xfail.
- Correctness repairs include versioned UTC event contracts, manual Kafka commits after a successful handler, PostGIS-backed API tests, typed date filtering, proper assigned-route lookup, and stricter exception boundaries.
- **Not claimed:** complete broker-backed delivery, consumer inbox/outbox idempotency, approved-dispatch golden path, ML accuracy benchmark or cloud deployment. Current CI success does not verify these.

## Verification log
- 2026-11-12: repository structure, README, current workflow statuses and readiness script inspected via GitHub.
- 2026-11-12: **Full local readiness was not executed in this environment** (repository dependencies/services unavailable). No cloud resources created.
- Statuses must be updated only with links to current reproducible evidence.
