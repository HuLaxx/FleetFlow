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
| Frontend and ML evaluation CI | **Verified passing on inspected commit only** | [Run 2026-11-11](https://github.com/HuLaxx/FleetFlow/actions/runs/42981274657) | Preserve pass; independently run full-stack checks |
| Local full readiness | Not executed in this audit environment | [Readiness script](../scripts/validate-local.sh), [criteria](local-readiness.md) | Reproduce infra, seeds, APIs, frontend and ML results |
| AWS deployment | Not independently verified | [Local/infra docs](local-stack.md) | Define minimal serverless plan and seek explicit cost approval |

## P0 observation
The inspected recent CI checked frontend quality and ML evaluation and passed. This does **not** prove the full Kafka-to-DB-to-optimiser-to-WebSocket-to-analytics chain, nor does it verify every optional Airflow, Flink, MLflow or OSRM service. The local readiness script can be resource intensive and requires Docker and multiple services.

## Required golden-path proof
1. Deterministic orders, drivers and vehicles, with event contract and UTC timestamps.
2. Idempotent ingestion with replay, DLQ and data-quality checks.
3. Constrained optimiser returning a candidate; separate explicit approval and durable dispatch.
4. Telemetry event reaches map and analytics; UI handles stale state and reconnect.
5. Compare distance, feasibility, unassigned stops and solve time to reproducible baseline.
6. Document local run steps, input seed/hash, logs, assertions, limits and AWS cost plan.

## Verification log
- 2026-11-12: repository structure, README, current workflow statuses and readiness script inspected via GitHub.
- 2026-11-12: **Full local readiness was not executed in this environment** (repository dependencies/services unavailable). No cloud resources created.
- Statuses must be updated only with links to current reproducible evidence.
