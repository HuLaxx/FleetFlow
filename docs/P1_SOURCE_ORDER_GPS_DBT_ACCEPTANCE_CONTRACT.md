# P1 release gate: one source order through optimisation, approval, GPS and dbt

**Status: OPEN — executable cross-system acceptance has not been demonstrated.**
This is a fail-closed acceptance contract, **not** a passing test or a production-readiness claim. It supplements the existing real OR-Tools database integration test and the separate same-GPS-event Chromium→Kafka→PostGIS→Parquet→dbt CI run. Do not mark P1 complete merely because those independent slices are green.

## Required single-run topology

One disposable, local-only test runner must seed a deterministic depot, one synthetic order, a driver and a vehicle. The runner must invoke the **actual OR-Tools solver** (not a fabricated route), persist its candidate and prove that the persisted stop references the seeded `order_id`. An authenticated dispatcher must explicitly approve the candidate; a viewer/anonymous actor must be rejected with no audit or outbox side effects. The approval audit must carry the approving principal, route/version and the same event ID as its transactional outbox record.

The runner must then start **that approved route**, publish the real transactional-outbox dispatch event to a local broker, and show a consumer acknowledgement. It must submit a synthetic GPS event for the **assigned vehicle/driver**, through the real authenticated browser/API path, then verify the exact GPS `event_id` in the outbox, broker acknowledgement, PostGIS accepted vehicle state, Parquet raw/clean/curated outputs and a real dbt-built fact. A route/vehicle/driver association must be checked against the approved solver route; matching only the GPS UUID without an order→route→vehicle join **does not pass**.

## Required independently verified lineage fields

| Boundary | Required persisted proof |
|---|---|
| Seed → solver | `order_id`, `depot_id`, `vehicle_id`, `driver_id`, feasible solver assignment and stop ID |
| Solver → approval | Same `route_id` and `order_id`, candidate version, immutable approval audit and authenticated approver |
| Approval → dispatch | Same `route_id`, assigned driver/vehicle, unique start event ID, broker ACK and no duplicate dispatch |
| Dispatch → GPS | Accepted GPS event ID, matching assigned vehicle and driver, route association backed by DB joins, PostGIS state |
| GPS → Parquet/dbt | Exactly the same accepted GPS event UUID in raw/clean/curated manifests and dbt fact; source digest and observed row counts |

The evidence JSON must contain **only synthetic identifiers**, Git commit SHA, workflow/run URL, schema versions, source digest, observed stage counts, negative-case results and artifact paths. Do not upload signing keys, bearer tokens, private addresses, customer data or raw real GPS positions. The CI job must fail on missing IDs, mismatched joins, absent artifacts, duplicate records or an unverified broker ACK. Never manufacture missing stages from fixture defaults.

## Approval receipt validation added on the review branch (22 November 2026)

The offline `verify_order_gps_lineage.py` checker now rejects approval receipts without a UUID `approval_audit_id`, UUID `approver_id`, positive integer `candidate_version` (booleans rejected), or timezone-aware `approved_at`. Nine negative cases cover missing, malformed and naive timestamps/version values. **These fields are claims supplied by the receipt; the checker alone does not independently query the audit table, establish that the approver was authorised, or prove the solver and GPS stages ran on one order.** The integrated runner must fetch the approval audit and candidate version from the actual database and cross-check the authenticated principal, transactional outbox and route identity before the P1 gate can close. Exact-head CI for this addition must pass before treating its tests as verified.

## Mandatory negative cases

1. Viewer/anonymous approval or completion: 401/403, unchanged route/stop, no audit/outbox mutation.
2. Start before approval, stale candidate version or route/stop mismatch: reject with no new dispatch/completion event.
3. Duplicate dispatch/GPS/replay: one durable logical effect; duplicate event IDs cannot inflate dbt counts.
4. GPS for a different vehicle/driver or without an approved dispatched route: reject from **this order-linked acceptance**, even if a standalone telemetry endpoint legitimately accepts fleet-wide GPS.
5. Broker failure before ACK, database rollback, corrupt/late/out-of-range GPS, malformed Parquet or mismatched dbt source IDs: fail closed and preserve recoverable source state.
6. Re-run from clean checkout: deterministic counts, no unbounded external dependencies and no production endpoints.

## Evidence and exit criteria

Run real PostGIS, a local broker, FastAPI, Chromium and the existing Parquet/dbt pipeline in a single disposable CI workflow. Upload a sanitized JSON receipt, hashed source fixtures, schema/lineage manifest, solver result, approval audit receipt, broker/outbox reconciliation, Parquet metadata and dbt test/run results. Pin each receipt to the **same exact PR-head SHA** and publish the workflow and artifact URLs in `docs/EVIDENCE_REGISTER.md`. A reviewer must be able to replay it without credentials for paid providers.

**Current verified partial slices:** [solver→approval→dispatch→completion tests](../backend/tests/test_api/test_dispatch_planning.py) and [same-GPS-event local golden path](https://github.com/HuLaxx/FleetFlow/actions/runs/44972556644) both pass on commit `cd5c2f201ed6353d5701a5a5535d0489a4e5d69b` (five workflows green at inspection). They are **not** a continuous order-to-dbt journey. The referenced run is historical once this document commit changes the head.

**Release rule:** Keep P1 and the 68/100 FleetFlow readiness baseline open until this integrated acceptance is actually implemented and passes on its own exact head. P3 security/recovery and P4 licensing, hosting, production data, cost and merge approvals remain independent gates. No main merge, live dispatch, AWS apply or spending is authorized by this document.
