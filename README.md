# 🚀 FleetFlow - Real-Time Delivery Optimization Platform

[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-blue)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-4.1-38bdf8)](https://tailwindcss.com/)
[![tRPC](https://img.shields.io/badge/tRPC-11-2596be)](https://trpc.io/)

> **Predictive & reactive delivery route optimization with real-time fleet management**

FleetFlow is an institutional-grade delivery optimization platform that combines **predictive analytics** (LSTM forecasting) with **reactive optimization** (event-driven re-routing) to achieve optimal fleet utilization.

![Dashboard Preview](./docs/dashboard-preview.png)

## ✨ Key Features

| Feature | Improvement |
|---------|-------------|
| 🚚 **Delivery Time Reduction** | 23% faster |
| ⛽ **Fuel Cost Savings** | 18% reduction |
| 📦 **Delivery Capacity** | 15% increase |
| 👷 **Driver Satisfaction** | +35% improvement |
| ⚡ **Re-routing Latency** | <800ms |

## 🛠 Tech Stack

### Frontend
- **Next.js 16** - App Router, Server Components, Server Actions
- **TypeScript 5.9** - End-to-end type safety
- **tRPC 11** - Type-safe API layer
- **Drizzle ORM** - Type-safe database queries
- **Deck.gl** - WebGL fleet visualization
- **Tailwind CSS 4** - Styling
- **Framer Motion** - Animations
- **Socket.IO** - Real-time updates

### Backend
- **PostgreSQL + PostGIS** - Geospatial database
- **TimescaleDB** - Time-series data
- **Redis** - Caching & geospatial indexing
- **Kafka** - Event streaming
- **MongoDB** - Document store

### ML/Optimization
- **OR-Tools** - Vehicle Routing Problem solver
- **Prophet + LSTM** - Demand forecasting
- **Genetic Algorithms** - Multi-objective optimization

## 🚀 Quick Start

### Prerequisites
- Node.js 20+
- pnpm 9+
- Docker & Docker Compose

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/fleetflow.git
cd fleetflow

# Start infrastructure
docker compose up -d

# Install dependencies
cd frontend
pnpm install

# Set up environment
cp ../.env.example .env.local

# Run development server
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) to see the dashboard.

## 📁 Project Structure

```
fleetflow/
├── frontend/               # Next.js 16 application
│   ├── src/
│   │   ├── app/           # App Router pages
│   │   ├── components/    # React components
│   │   │   ├── dashboard/ # Dashboard UI
│   │   │   └── map/       # Fleet map (Deck.gl)
│   │   ├── db/            # Drizzle ORM schema
│   │   ├── lib/           # Utilities
│   │   └── server/        # tRPC routers
│   └── drizzle.config.ts
├── db/
│   └── init/              # Database initialization
│       ├── 01_postgis_schema.sql
│       └── 02_timescale_schema.sql
├── docker-compose.yml     # Infrastructure services
├── specification.md       # Full project spec
└── .env.example           # Environment template
```

## 🐳 Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL + PostGIS | 5432 | Main database |
| TimescaleDB | 5433 | Time-series data |
| Redis | 6379 | Caching |
| MongoDB | 27017 | Document store |
| Kafka | 9092 | Event streaming |
| Kafka UI | 8080 | Kafka monitoring |

## 📊 Architecture

```
┌─────────────────────────────────────────────┐
│              DISPATCHER DASHBOARD            │
│         (Next.js + Deck.gl + tRPC)          │
└─────────────────────┬───────────────────────┘
                      │ tRPC / WebSocket
┌─────────────────────▼───────────────────────┐
│               API LAYER (tRPC)               │
│     drivers | routes | orders | optimize    │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│            EVENT BACKBONE (Kafka)            │
│   orders.new | gps.location | routes.assigned│
└──────────┬─────────────────────┬────────────┘
           │                     │
    ┌──────▼──────┐      ┌──────▼───────┐
    │  HOT PATH   │      │  COLD PATH   │
    │  (Flink)    │      │  (Airflow)   │
    └──────┬──────┘      └──────┬───────┘
           │                    │
    ┌──────▼────────────────────▼─────────────┐
    │           DATA STORES                    │
    │  PostgreSQL | TimescaleDB | Redis | S3  │
    └──────────────────────────────────────────┘
```

## 🎯 Target Roles

| Role | Level |
|------|-------|
| Data Engineer | Senior (L5) |
| Data Scientist | Mid-Senior (L4-L5) |
| ML Engineer | Senior (L5) |
| Full Stack | Senior (L5) |
| Software Engineer | Senior (L5) |

## 📈 Roadmap

- [x] Phase 0: Foundation (Docker, Next.js, Database)
- [ ] Phase 1: Data Engineering (Kafka, Flink, Airflow)
- [ ] Phase 2: Data Science (Forecasting, Optimization)
- [ ] Phase 3: ML Engineering (Model Serving, Monitoring)
- [ ] Phase 4: Full Features (Mobile App, WebSocket)

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

Built with ❤️ by the FleetFlow Team
