# FleetFlow — Engineering Release Checklist (evidence-gated)

**Updated:** 2026-11-13 | **Target:** credible UK Data Engineering / Cloud Data Platform flagship | **Status:** DRAFT, NOT 10/10

Check an item only after a reviewer can reproduce the behaviour and inspect tests, logs, commit and proof. **[x] here means verified on a review branch, not deployed, merged, or production ready.** Link each substantive claim in [EVIDENCE_REGISTER.md](EVIDENCE_REGISTER.md). All synthetic/sample map data must remain labelled. No AWS provisioning or production changes without explicit approval.

## P0 — Integrity and reproducibility
- [x] Repaired backend tests, Ruff/Black, frontend quality, CPU ML smoke and dependency scan on review branch. [Current full CI: 43429154935](https://github.com/HuLaxx/FleetFlow/actions/runs/43429154935), [PR #4](https://github.com/HuLaxx/FleetFlow/pull/4).
- [x] Versioned GPS event contracts and UTC event timestamps tested on branch. [P0 PR #1](https://github.com/HuLaxx/FleetFlow/pull/1).
- [x] CI uploads an inspectable `backend-coverage` artifact instead of silently failing Codecov. [PR #3](https://github.com/HuLaxx/FleetFlow/pull/3).
- [x] Missing/template JWT signing keys now fail closed; CI uses ephemeral signing key. [Security CI 43428864864](https://github.com/HuLaxx/FleetFlow/actions/runs/43428864864).
- [ ] Prove full local readiness script with actual PostGIS, Kafka, Redis, OSRM as needed, frontend and API.
- [ ] Remove committed bytecode/pycache files and add robust ignore rules, with clean-tree assertion.
- [ ] Rename simplified Python `flink` processor or prove a real Flink job and integration test.
- [ ] Validate database migrations on a new isolated instance and an upgrade path.
- [ ] Review main-branch PR stack, test merge compatibility, and merge only after human review.

## P1 — One genuine source → dispatch → browser → analytics golden path
- [x] Local immutable JSONL → validated event-date Parquet → curated hourly telemetry, with replay, duplicates, quarantine and late-event test coverage. [PR #2](https://github.com/HuLaxx/FleetFlow/pull/2).
- [x] Invalid numeric values, quarantine diagnostics and source-file mutation are guarded with regression tests. [PR #3](https://github.com/HuLaxx/FleetFlow/pull/3).
- [x] Already-persisted planned routes can be explicitly approved by dispatcher/admin, with capacity/window/driver tests; this **does not create plans from optimiser previews**. [PR #4](https://github.com/HuLaxx/FleetFlow/pull/4).
- [x] Fabricated on-time/fleet-efficiency figures replaced by observed definitions or null. [PR #4](https://github.com/HuLaxx/FleetFlow/pull/4).
- [ ] Deterministically seed order, customer, depot, driver and vehicle lifecycle with reproducible command.
- [ ] Implement event producer → broker → consumer → versioned contract validation → durable database writes.
- [ ] Add database-backed inbox/outbox: idempotent event IDs, atomic writes, replay, DLQ, recoverable failures and backfill.
- [ ] Persist optimiser-generated **candidate** routes; make candidate, approved and dispatched states distinguishable.
- [ ] Record approver, approved time, candidate version and immutable audit event transactionally.
- [ ] Handle re-approval/race conditions, infeasible demands, duplicate orders, driver-hour constraints and stale route versions.
- [ ] Connect approved dispatch to real vehicle GPS → WebSocket → browser map with reconnect/stale/offline UI.
- [ ] Persist and reconcile dispatch/performance records in analytical tables.
- [ ] Verify one-command seeded smoke test for entire order → approved dispatch → location → KPI chain.
- [ ] Prove failure tests: duplicate, late, invalid, poison, broker outage, DB outage, replay and capacity/time-window infeasibility.

## P2 — Data engineering + optimisation depth
- [ ] Raw/clean/curated contracts, partition layout, schema evolution, bounded-memory processing and concurrency recovery.
- [ ] dbt staging/facts/dimensions compile, data-quality tests, freshness and incremental/late-event loads.
- [ ] Airflow task replay/backfill with meaningful error handling and lineage matching actual execution.
- [ ] Compare OR-Tools to deterministic nearest-neighbour/current planning on held-out fixtures: distance, time, unassigned, violations, solve time and cost.
- [ ] Evaluate ETA/demand model **only** with defensible data, chronological holdout, naive/seasonal baselines and uncertainty.
- [ ] Record material failure modes, reproducible commands and exact result artifacts.

## P3 — Security, reliability, cloud and costs
- [ ] Complete authz review (route creation, modification, approval, driver start/stop, analytics read).
- [ ] Structured logs, useful metrics, real alerts, runbooks, retries, DLQ and recovery drills.
- [ ] Measured load test with scripts, p95 latency, throughput, resource sizing and known limits.
- [ ] Terraform for minimal optional S3/Glue/Athena/EventBridge/Lambda or short-lived ECS plus IAM/OIDC, remote state safeguards and destroy path.
- [ ] Explicit approval and documented budget estimate before **any** `terraform apply`/paid infrastructure.
- [ ] Verify one real deployment only if authorised; distinguish deployed resources from template files.

## P4 — Presentation and publication gate
- [ ] Architecture diagram matches the **implemented** path; live, sample, simulated and aspirational systems separated.
- [ ] Responsive accessible demo, no broken links and clear stale-data/no-backend states.
- [ ] README includes seeded steps, tests, fixtures/licence, run artifacts, trade-offs, security limits and cost assumptions.
- [ ] Honest benchmarks, current CI badges, screenshots and a 5–8 minute interview walkthrough.
- [ ] Publish FleetFlow as lead Data Engineering project **only after** evidence/URLs are verified.

## Release decision
- **Current gate:** P0/partial P1 verified on stacked draft PRs; complete broker-backed dispatch golden path **not verified**.
- **Do not use a 10/10 badge**, represent an AWS template as a deployment, or claim route optimisation acceptance without a persisted plan.
- **Next smallest PR:** optimiser candidate persistence + approval audit migration + deterministic PostGIS-backed integration tests. No production or AWS action.
