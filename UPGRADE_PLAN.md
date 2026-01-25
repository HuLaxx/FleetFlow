# FleetFlow Upgrade Plan

> Scope: portfolio-first local powerhouse + free-tier deployment fallback
> Date: 2026-01-25

## 1) Goals (Ranked)
1. **Portfolio-first proof**: make evidence, workflows, and role coverage obvious and verifiable.
2. **Local full-power stack**: everything heavy runs locally (Kafka, Flink, Airflow, PostGIS, TimescaleDB, Redis, MongoDB, OSRM, MLflow).
3. **Free-tier deploy fallback**: live demo runs on Supabase + Upstash + Railway with clear limitations.
4. **RAG / LLM wrapper**: local indexes that learn from repo/docs; optional LLM provider.

---

## 2) Current Baseline (Already in repo)
- Frontend: Next.js + tRPC + Deck.gl + MapLibre + Tailwind.
- Backend: FastAPI + Kafka consumers + WebSocket + GraphQL.
- Infra: docker-compose, k8s manifests, monitoring stack.
- Data/ML: Airflow DAGs, dbt models, Flink job, ML scripts.
- Testing: pytest (backend), Playwright (frontend).

---

## 3) Upgrade Workstreams & Tasks

### A) Portfolio Presentation (Rank #1)
- [x] Dedicated `/portfolio` page with workflow + role evidence
- [x] Free-tier notice on landing + demo
- [x] Update frontend accent palette to teal/mint/green/black
- [ ] Add explicit "Local Full-Power" section + quickstart
- [ ] Add real GitHub + live demo URLs
- [ ] Add Evidence table linking to real files

**Deliverables**
- `frontend/src/app/portfolio/page.tsx`
- `README.md` updates

---

### B) Local Full-Power Stack
- [x] Add Airflow service to root `docker-compose.yml`
- [x] Add Flink service to root `docker-compose.yml`
- [x] Add MLflow service to root `docker-compose.yml`
- [x] Add OSRM data bootstrap script (download/build region)
- [x] Add `scripts/dev-up` to bring up full local stack
- [x] Add `scripts/run-local` to run infra + backend + frontend
- [x] Add local readiness validation scripts
- [x] Auto-pick host ports and write `.env.ports`
- [x] Auto-bootstrap backend venv + deps for local runs

**Deliverables**
- `docker-compose.yml`
- `scripts/dev-up.(ps1|sh)`
- `scripts/run-local.(ps1|sh)`
- `scripts/ports-auto.(ps1|sh)`
- `scripts/load-ports.(ps1|sh)`
- `scripts/backend-python.(ps1|sh)`
- `docs/local-stack.md`
- `scripts/validate-local.(ps1|sh)`
- `docs/local-readiness.md`
 - `scripts/osrm-bootstrap.(ps1|sh)`

---

### C) Free-Tier Deployment Fallback
- [x] UI notice for free-tier deployment
- [ ] Add demo "fallback mode" banner when env flag enabled
- [ ] Add feature flag to disable heavy pipelines in prod
- [ ] Document limitations on demo page

**Deliverables**
- `frontend/src/components/site/deployment-notice.tsx`
- `frontend/src/app/demo/page.tsx`
- `docs/deployment.md`

---

### D) RAG + LLM Wrapper
- [x] RAG storage + endpoints (/api/v1/rag/*)
- [x] TF-IDF vector store (local) + optional LLM client
- [ ] Add ingestion script for repo docs + specs
- [ ] Add default index ("fleetflow") on first run
- [ ] Add Gemini adapter (optional)

**Deliverables**
- `backend/src/llm/*`
- `scripts/rag-ingest.(ps1|sh)`
- `docs/rag.md`

---

### E) Database & Data Seeding
- [x] Postgres/PostGIS + Timescale init SQL
- [x] Seed script for demo data (drivers, orders, routes)
- [x] Seed Kafka topics for real-time events

**Deliverables**
- `db/seed/*.sql` or `backend/scripts/seed.py`
- `scripts/seed-db.(ps1|sh)`
- `scripts/replay-kafka.(ps1|sh)`

---

### F) Testing & QA
- [x] Backend pytest suite
- [x] Frontend Playwright test
- [ ] Add backend coverage badge + report artifact
- [ ] Add API smoke tests for RAG endpoints
- [ ] Add lint checks for frontend
- [x] Add ML determinism tests + optional slow training smoke test
- [x] Add ML training metrics summary output

**Deliverables**
- `.github/workflows/backend-tests.yml`
- `frontend/e2e/*.spec.ts`
- `backend/tests/test_rag.py`

---

### G) DevOps & Observability
- [x] Prometheus + Grafana configs
- [ ] Add docker profile for observability
- [ ] Document monitoring URLs

**Deliverables**
- `monitoring/docker-compose.yml`
- `docs/monitoring.md`

---

## 4) Fixes (Tracking)
- [ ] Remove tracked secrets (`backend/.env`, `frontend/.env.local`) if any
- [x] Add missing healthcheck endpoints or update Dockerfile healthcheck path
- [ ] Confirm OSRM volume/data path
- [ ] Ensure tRPC calls match FastAPI routes

---

## 5) Database Category
- [ ] Confirm schema migrations are consistent with API models
- [ ] Index critical query columns (driver_id, order status, timestamps)
- [ ] Add spatial indexes for geo queries (PostGIS)

---

## 6) Testing Category
- [ ] Run backend tests with coverage: `pytest --cov`
- [ ] Run Playwright tests: `pnpm test:e2e`
- [ ] Add smoke tests for RAG
- [x] Add strict local validation script

---

## 7) Documentation Category
- [x] `docs/local-stack.md` (full-power local run)
- [x] `docs/local-readiness.md` (strict local readiness gates)
- [x] `docs/ml-training.md` (training metrics + MLflow)
- [ ] `docs/deployment.md` (free-tier fallback)
- [ ] `docs/rag.md` (RAG usage + ingestion)
- [ ] `docs/monitoring.md` (Prometheus/Grafana)

---

## 8) Acceptance Criteria
- Local stack brings up all services with one command.
- Demo page clearly states free-tier limits and local-first capability.
- RAG can ingest repo docs and answer with citations.
- Tests run and produce at least basic coverage artifacts.

---

## 9) Next Steps (Pick order)
1. Expand `docker-compose.yml` with Airflow/Flink/MLflow + profiles.
2. Add seed scripts + OSRM bootstrap.
3. Add RAG ingestion pipeline + docs.
4. Add deployment fallback banners + env flag.

---

## 10) Status Log
- 2026-01-25: Portfolio page + free-tier notice + RAG wrapper added.
- 2026-01-25: Added Airflow/Flink/MLflow services, dev-up scripts, and local stack docs.
- 2026-01-25: Added strict local readiness rubric and validation scripts.
- 2026-01-25: Added OSRM bootstrap, deterministic DB seed, and Kafka replay scripts.
- 2026-01-25: Added deterministic ML data + training controls with ML tests.
- 2026-01-25: Added ML training metrics summaries and MLflow doc.
- 2026-01-25: Switched frontend accent palette to teal/mint/green/black.
- 2026-01-25: Added one-command local run scripts for infra + backend + frontend.
- 2026-01-25: Added auto-selected local ports with `.env.ports`.
- 2026-01-25: Added backend venv bootstrap for local scripts.
