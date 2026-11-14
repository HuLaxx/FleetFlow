# FleetFlow P1 — actual Kafka replay and poison-message quarantine

**Proposed milestone:** A real Kafka-compatible disposable broker is exercised
in a dedicated GitHub Actions job, and the `routes.approved` consumer stores
permanently malformed records in PostGIS *before* acknowledging their offsets.
The implementation passed real-broker acceptance at code commit `588835b6`; subsequent documentation-only HEADs require their own checks.

## Verified CI evidence

- [Real Kafka + PostGIS run 43611852641](https://github.com/HuLaxx/FleetFlow/actions/runs/43611852641): **1 real broker test passed**, **5 offset/quarantine tests passed**. No test was skipped in the dedicated broker job.
- [Normal backend run 43611852471](https://github.com/HuLaxx/FleetFlow/actions/runs/43611852471): **85 tests passed, 1 broker-only test skipped, 3 warnings, 62% statement coverage**; frontend, Ruff/Black, CPU ML smoke and dependency security checks passed.
- Both runs tested code SHA `588835b6475f3b267f35d8de7c6b8f0ac822aae9`.
- The real broker run exposed a runtime decoder mismatch: the producer emits Snappy-compressed records. The fix adds `python-snappy` to backend **runtime** dependencies rather than treating CI as a special case.

## End-to-end boundary under test

The preceding milestone (#6) persists the approved route, audit and outbox
event atomically. This PR adds the following **local/CI** acceptance sequence:

1. Create an approved route and matching audit/outbox rows in isolated PostGIS.
2. Publish that outbox row using the real producer's broker-ACK callback.
3. Consume the event from a disposable Redpanda Kafka API broker and persist
   the receipt in the PostgreSQL `dispatch_consumer_inbox`.
4. Stop the Kafka consumer **without** committing its offset, modelling a
   consumer crash after a successful database transaction.
5. Simulate a publisher crash after ACK but before the published-status DB
   commit, then publish the same event ID again.
6. Restart with the same Kafka group ID. Redeliver the original record and
   consume the duplicate; the unique inbox receipt prevents a second DB
   processing effect.
7. Publish invalid raw JSON using an actual Kafka client. Its
   `topic/partition/offset` and SHA-256 hash are stored in
   `dispatch_message_quarantine`; no original message text is persisted.
   Only then is the Kafka offset committed. Reprocessing that same offset
   cannot create a second quarantine record.

The restart/crash windows are **process-behaviour simulations** using real
Kafka clients; CI does not forcibly kill a container or partition the network.
No production broker, backend deployment, paid AWS, or browser client is used.

## Poison handling is intentionally narrow

`BaseKafkaConsumer` now passes raw bytes to its processing boundary, rather
than parsing JSON in the Kafka library outside the error handler. Only
`RouteEventsConsumer` implements the durable quarantine callback.

**Permanent** problems include invalid JSON, invalid UTF-8, non-object JSON,
payloads larger than 128 KiB, missing/invalid route UUIDs, unsupported route
approval schema or an unexpected route topic. These are recorded with a fixed
reason and a payload digest; no raw address, email, secret or message key is
stored. A failed quarantine DB transaction raises, **so the broker offset is
not committed**.

**Transient or inconsistent-state** errors such as an unavailable Postgres
database or a route event with no supporting persisted approval audit remain
fail-stop and uncommitted. Other consumer classes also continue to fail-stop
on permanent errors until their own explicit quarantine contracts are
implemented. This is not a general-purpose Kafka dead-letter topic or
automatic poison-event replay UI.

## Migration and reproducibility

After `db/init/03_dispatch_reliability.sql`, apply the additive
`db/init/04_dispatch_quarantine.sql` on an approved isolated PostgreSQL
database. GitHub's real-broker CI job initializes PostGIS, applies both
additive migrations, and then runs acceptance tests:

```bash
# From repository root; no production migration is executed automatically.
# GitHub: .github/workflows/kafka-replay.yml
cd backend
FLEETFLOW_KAFKA_INTEGRATION=1 \
  KAFKA_BOOTSTRAP_SERVERS=localhost:19092 \
  DATABASE_URL=postgresql+asyncpg://fleetflow:fleetpass@localhost:5432/fleetflow_test \
  POSTGRES_PASSWORD=fleetpass POSTGRES_DB=fleetflow_test \
  pytest tests/test_kafka/test_broker_replay.py -v -rs

pytest tests/test_consumers/test_poison_offsets.py -v
```

The broker is pinned to a disposable Redpanda container and is torn down by
the job. The integration test does not silently substitute mocks when
`FLEETFLOW_KAFKA_INTEGRATION=1`; a broker connection failure fails CI.
Outside that explicit environment it is skipped, preventing hidden external
service usage in ordinary unit-test runs.

The local test database is forcibly scoped to `fleetflow_test` on
localhost/127.0.0.1. Append-only approval records are intentionally retained
in the disposable CI database until the entire test service is destroyed.

## Still outstanding

- True network/process-fault injection with abrupt OS kill at every commit
  boundary and multi-broker failover.
- Durable dead-letter *topic*, manual review/replay workflow, alert thresholds
  for growing quarantines, bounded retention, permissions, operator metrics.
- Order/driver/GPS handlers need their own schema validation and idempotency.
- WebSocket side effects are not transactional with inbox DB receipts.
- Full live GPS → WebSocket → UI, data warehouse marts and benchmarks remain
  unverified. No free-tier or paid cloud deployment was performed.
