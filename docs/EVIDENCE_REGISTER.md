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

## P1 replay-contract integrity — stacked draft PR #3 (2026-11-13)

- [PR #3](https://github.com/HuLaxx/FleetFlow/pull/3) is stacked on PR #2, which is stacked on P0 PR #1. No changes were merged to `main`.
- [Successful full CI run 43319704238](https://github.com/HuLaxx/FleetFlow/actions/runs/43319704238) at code SHA `3fda7ca4882dad9c0118b68ff0cf0b164a52f1ac` passed all five jobs: **55 backend tests passing, three warnings, 60% aggregate statement coverage**, backend Ruff/Black, frontend lint/typecheck/build, CPU ML smoke and blocking high/critical security scan.
- Six new parametrised/standalone test cases verify rejection of nonstandard JSON `NaN`/`Infinity` and overflowed speed, value-redacted schema-validation quarantine diagnostics, and refusal to publish a replay when copied source bytes differ from the original SHA-256.
- Original raw data is **still preserved byte-for-byte**. Quarantine redaction is not anonymisation of the raw layer; permissions, retention rules and data minimisation remain required for any real telemetry.
- The earlier optional Codecov upload failed due to a missing token despite a green job. The workflow has since been changed to upload `backend/coverage.xml` as a GitHub Actions artifact; verify that artifact on the latest commit before claiming coverage is externally inspectable.
- This is **local batch replay only**, not live Kafka, durable event reconciliation, route approval, true vehicle tracking, an operational warehouse or AWS deployment.

## P1 dispatcher approval and factual KPI gate — 13 November 2026

- [Draft PR #4](https://github.com/HuLaxx/FleetFlow/pull/4) is stacked on replay-integrity PR #3; no main-branch merge or production change has occurred.
- [Successful CI 43427090167](https://github.com/HuLaxx/FleetFlow/actions/runs/43427090167) on code SHA `dbb42fe64f84bb6403c7019a34a6bd09b52f37f6` ran **60 passing backend tests**, **3 warnings**, **60% combined statement coverage**; all five jobs passed, including Ruff/Black, frontend lint/type/build, CPU ML smoke, and high/critical dependency scan. Downloadable GitHub Actions `backend-coverage` artifact ID **14036753627** contains coverage XML.
- Five new real PostGIS-backed tests exercise anonymous/VIEWER rejection, DISPATCHER/ADMIN approval, planned-route start rejection, proper approved start, mismatched driver identity, driver's own-assignment check, vehicle capacity, time windows and observed KPI reporting.
- A `planned` row is not automatically approved: the new `approved` state requires the explicit role-gated API operation. `start` requires the approved state and assigned driver.
- Former hard-coded 0.92 on-time and 0.87 fleet-efficiency percentages are removed. The on-time fraction is only calculated for completed stops with both observed and planned arrival timestamps, and sample size and definition are exposed. Fleet efficiency is `null` because no verified definition or measurement exists. Average duration is also null until actual completion data exists.
- **Known limitations:** route optimiser produces previews without persisting candidate routes; this PR approves only an already persisted planned route. An approval response identifies the reviewer but **does not yet store an immutable approval audit event**. No durable dispatch outbox, Kafka-backed integration, WebSocket tracking, complete duty-hour feasibility validation, production permissions review or reconciled warehouse KPI has been verified.
- No AWS deployment, paid resources, real fleet data or production route mutation was performed. The milestone is **verified isolated API behaviour**, not an end-to-end dispatch golden path.

## P1 signing-key safety gate — 13 November 2026

- [GitHub Actions run 43428864864](https://github.com/HuLaxx/FleetFlow/actions/runs/43428864864), code SHA `86802f4c277126ccd624622adc8142016c439849`, completed all five CI jobs successfully, including **66 passing Python tests (three warnings; 60% statement coverage)**, Ruff/Black, frontend checks, CPU ML smoke and blocking dependency security scan.
- The earlier authentication module used a known, hard-coded JWT signing-key fallback. This branch now **fails closed** on missing, short or documented placeholder `JWT_SECRET_KEY` values; it does not automatically provision a signing key. A real random signing key is required for local and deployed API use.
- The CI job generates a fresh ephemeral test-only key. Six additional parametrized/unit tests verify rejected defaults and an accepted non-template secret. Docker Compose requires an externally configured `JWT_SECRET_KEY`; `.env.example` documents generation without storing a real secret.
- **Compatibility note:** backend startup without a configured signing key will fail after this change; explicitly configure the key before running local Compose or any future deployment. No secret was committed, no running production deployment was modified, and no cloud resources were provisioned.
- **Remaining auth gaps:** token rotation/revocation policy, comprehensive API authorization audits and durable persisted dispatcher approval identity are not yet evidenced; a configured strong key is necessary but not sufficient to claim complete security.

## P1 candidate-route persistence — draft branch, 14 November 2026 (pending CI)

- New branch `feature/p1-persisted-optimizer-plans-2026-11-14` stacked on [draft PR #4](https://github.com/HuLaxx/FleetFlow/pull/4); **not merged or deployed**.
- Code now packages the previously repository-root-only OR-Tools solver in `backend/src/optimization` and reads delivery coordinates from related `Customer` records rather than nonexistent `Order.latitude` fields. The standalone `ml/route_optimizer.py` path is a compatibility wrapper, not another independent implementation.
- `POST /api/v1/optimization/routes/optimize` remains a non-mutating preview; dispatcher-only `POST /api/v1/optimization/routes/plan` writes actual planned route and stop rows atomically after post-solver integrity checks, with order/vehicle row locks and active-plan conflict detection. Plan creation never auto-approves dispatch.
- Added PostGIS-backed acceptance tests for preview, persisted routes, existing explicit approval, duplicate conflicts, missing location, unavailable vehicle, infeasible capacity and role enforcement; **test execution awaits GitHub Actions confirmation on the final branch SHA**.
- See [P1 planning scope and reproduction](P1_OPTIMIZER_PLANNED_ROUTES.md). Do **not** claim broker-backed ingestion, full GPS/UI tracking, an immutable approval event, true road distance or AWS deployment from these changes.

## FleetFlow P1 — approval audit and reliable messaging (14 Nov 2026, new draft)

- Proposed branch `feature/p1-approval-audit-outbox-2026-11-14` stacks on [PR #5](https://github.com/HuLaxx/FleetFlow/pull/5); previous PR #5 was [all five CI jobs green at SHA `dfe720ec`](https://github.com/HuLaxx/FleetFlow/actions/runs/43493598780).
- Added approval audit row, outbox row and route state in one DB transaction. The migration `db/init/03_dispatch_reliability.sql` installs a database-level append-only trigger; ORM-only test `create_all` does not install this trigger by itself.
- The manually started outbox worker requires a Kafka delivery callback ACK before marking published, with retry backoff. Events may be published twice after a crash; consumer inbox deduplicates IDs transactionally with its DB verification. No claims of end-to-end exactly-once effects.
- New acceptance tests for audit, pending event, duplicate approvals, broker timeout/retry, inbox dedup/rollback and trigger enforcement. Broker ACK tests use a controlled fake producer; real broker integration remains unverified.
- This PR is NOT a production deployment or merge and does not start worker processes or provision AWS. Exact current-head CI evidence **pending**; do not inherit PR #5's check results as proof this PR passed.

### Verified five-job P1 audit/outbox gate — 14 November 2026

- [GitHub Actions run 43504618864](https://github.com/HuLaxx/FleetFlow/actions/runs/43504618864), code commit `d3aa2aae3ab655e1a3f2df9a327a11624e9ffffb`: **all 5 jobs passed** — 80 backend tests passed, 3 warnings, **62% combined backend statement coverage**, Ruff/Black, Next.js lint/types/build, CPU ML smoke, and Trivy high/critical scan. The runner uploaded `backend-coverage` artifact **14075259185**. This evidence belongs to the named commit; subsequent documentation changes require their own check.
- New PostGIS integration assertions verify an approval writes one `route_approval_audit` and pending `dispatch_outbox` row, repeated approval conflicts, simulated NACK/timeout preserves pending and later ACK marks delivered, inbox deduplicates event IDs, inbox receipt rollback on handler error, and a SQL audit trigger blocks UPDATE and DELETE. Fake Kafka producer tests assert ACK, NACK, and no-ACK timeout behavior.
- **Not verified:** actual Kafka broker's on-network ACK semantics or cross-process crash recovery, database migration applied to an existing live service, concurrent outbox workers under load, live WebSocket reliability, dead-letter / alerting operations, or AWS. The worker is opt-in, not deployed.

## P1 real-broker restart and durable quarantine — 14 November 2026 (verified code CI)

- P1 next milestone builds on the **five-job green** [PR #6 final-head run 43505200400](https://github.com/HuLaxx/FleetFlow/actions/runs/43505200400) at `57a87cc14944b4591551ab4202846526883335a4`.
- Proposed: raw Kafka bytes are decoded inside the manual-offset processing boundary. Only permanently malformed route events are committed to the new `dispatch_message_quarantine` table (topic, partition, offset, SHA-256, byte count, bounded reason). The payload body and key are never stored. Quarantine is saved before broker offset commit; DB failure leaves the offset uncommitted.
- New dedicated [Kafka replay acceptance workflow](../.github/workflows/kafka-replay.yml) starts disposable local PostGIS and Redpanda, applies `03_dispatch_reliability.sql` and `04_dispatch_quarantine.sql`, verifies publisher ACK, consumer restart without offset ACK, duplicate outbox publication, receipt deduplication and real broker invalid JSON quarantine. New unit tests cover commit-after-quarantine and fail-stop when durable quarantine fails.
- **Verified code SHA `588835b6475f3b267f35d8de7c6b8f0ac822aae9`:** [real-broker acceptance 43611852641](https://github.com/HuLaxx/FleetFlow/actions/runs/43611852641) **1 actual Kafka/PostGIS test passed + 5 offset/quarantine tests passed**; [backend CI 43611852471](https://github.com/HuLaxx/FleetFlow/actions/runs/43611852471) **85 tests passed, 1 intentionally skipped broker-only test, 3 warnings, 62% statement coverage, all 5 jobs green**. Initial broker test failed on a missing Snappy decompression codec; added `python-snappy` as a **runtime** dependency, reran and verified. These two run URLs are evidence only for the named code SHA; a later documentation-only HEAD should be checked separately.
- This does not constitute an automatically replayable dead-letter topic, a real process kill, full GPS tracking or deployment. See [P1 broker acceptance contract](P1_BROKER_REPLAY_QUARANTINE.md).

## P1 local GPS-to-WebSocket tracking — 15 November 2026 (verified code CI)

- Previous stacked [PR #7](https://github.com/HuLaxx/FleetFlow/pull/7) verified [backend CI 43612129246](https://github.com/HuLaxx/FleetFlow/actions/runs/43612129246): 85 passing tests, 1 broker-only intentional skip, 62% coverage; and [real-broker 43612129347](https://github.com/HuLaxx/FleetFlow/actions/runs/43612129347): one non-skipped broker test + five focused tests.
- Proposed new P1 live slice: driver-only authorization for GPS ingestion; event outbox queued in the same database transaction; event-time-ordered PostGIS vehicle coordinates with `last_gps_at` / event ID and duplicate/late rejection; same-process /ws endpoint sharing Kafka consumer manager; local development-only subscriptions and verified snapshot-on-reconnect; authenticated remote socket still blocked.
- Added browser `/tracking` using only validated live/saved positions; no seeded markers; 60s staleness and disconnected warning. `/demo` and navbar are explicitly labelled seeded; health endpoint alone no longer claims Kafka is live. Existing WebSocket HTTP broadcast disabled unless a secret token is configured; standalone fake GPS simulation removed.
- **Verified code SHA `c27af41f38b4a14f535372465206249481d1a54d`:** [Backend five-job run 43688456913](https://github.com/HuLaxx/FleetFlow/actions/runs/43688456913) fully green: **91 tests passed, 2 intentional broker-only skips, 3 warnings, 65% statement coverage**, Ruff/Black, frontend lint/type/build, CPU ML smoke and dependency security passed. [Chromium Playwright run 43688456894](https://github.com/HuLaxx/FleetFlow/actions/runs/43688456894) **3 live-tracking tests passed without retries** (latest GPS, reconnect/stale, empty no-seed). [Actual Kafka run 43688250065](https://github.com/HuLaxx/FleetFlow/actions/runs/43688250065) passed **2 broker/PostGIS tests and 5 focused tests** on preceding SHA `febef2d2`; no backend source changed since that broker run (subsequent commits affect map/browser and docs). Browser test uses controlled mocked WebSocket packets; Kafka test validates up to a mocked WebSocket manager, so complete real broker → real browser remains unverified. Reviewed migration `db/init/05_gps_tracking.sql` not applied to production. Subsequent docs-only HEAD still needs a matching check.
- See [local GPS tracking documentation](P1_LIVE_GPS_TRACKING.md). No main merge, cloud deployment or AWS provisioning.

## P1 JWT-scoped GPS and real browser-to-broker acceptance — 16 November 2026 (PR #9)

- [Draft PR #9](https://github.com/HuLaxx/FleetFlow/pull/9) is stacked on [draft #8](https://github.com/HuLaxx/FleetFlow/pull/8), neither merged. Adds first-frame access-JWT WebSocket authentication, DB-backed driver/depot/admin scopes with NULL-by-default dispatcher depot assignment and migration `db/init/06_websocket_dispatch_scope.sql`. Rejects refresh/expired tokens and viewers, rechecks permissions/revocation on GPS broadcasts and snapshots. REST vehicle/driver responses redact unscoped coordinates, including per-vehicle location endpoint 401/403. The browser has an explicit login, no persistent token storage, subscription ACK and denied/revoked state.
- **Real, unmocked synthetic E2E**: [full-stack CI run 43926162453](https://github.com/HuLaxx/FleetFlow/actions/runs/43926162453) **1 Chromium test passed** on SHA `242d42888f5eea86bac460c5ad629525d29106c8`; covers FastAPI login → HTTP 202 GPS queued → real PostgreSQL outbox worker → disposable Redpanda → GPS consumer → persisted PostGIS → WebSocket subscriber → Chromium marker and scoped GET, then logout. This is not a public hosted deployment or performance benchmark. Earlier attempts surfaced and fixed legacy Passlib-bcrypt breakage (new Argon2id hash, verify old bcrypt) and naive/aware login timestamp mismatch.
- [Backend CI 43926162615](https://github.com/HuLaxx/FleetFlow/actions/runs/43926162615) on the same code SHA: **101 passed, 2 broker-only skips, 2 warnings, 67% statement coverage**; frontend, ML and security all passed but Ruff import order failed; it has been fixed in a newer commit. Do not mark this old CI run all-green. [Kafka 43926162472](https://github.com/HuLaxx/FleetFlow/actions/runs/43926162472) both real-broker tests + 5 focused tests passed, [mock-browser 43926162482](https://github.com/HuLaxx/FleetFlow/actions/runs/43926162482) 4 passed. The final code/docs head must be checked separately.
- The integration is **development-only**: no production authenticated WebSocket release, multi-instance fanout, GPS retention/privacy policy, measured throughput, costed AWS or main merge. See [full contract and reproduction](P1_AUTHENTICATED_GPS_END_TO_END.md).
