"""
FleetFlow API - Real-Time Delivery Optimization Backend

FastAPI application with:
- REST API endpoints for orders, drivers, routes
- WebSocket for real-time updates
- Kafka integration for event streaming
- OR-Tools for route optimization
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Header, HTTPException
import structlog

from src.config import get_settings
from src.events import get_kafka_producer
from src.api.routes import orders, drivers, routes, vehicles, optimization, auth, monitoring, experiments
from src.middleware.security import configure_security
from src.monitoring import PrometheusMiddleware, configure_sentry
from src.graphql import graphql_router
from src.llm import router as rag_router

logger = structlog.get_logger()
settings = get_settings()

# Initialize Sentry error tracking
configure_sentry(
    app_name=settings.app_name,
    environment=settings.environment
)

def require_api_key(x_api_key: str = Header(default="")) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting FleetFlow API", version=settings.app_version)
    
    # Initialize database connection pool
    from src.database import init_db
    await init_db()
    logger.info("Database connection pool initialized")
    
    # Initialize Kafka producer and create topics
    producer = get_kafka_producer()
    await producer.ensure_topics_exist()
    logger.info("Kafka producer initialized")
    
    # Start Kafka consumers
    from src.consumers import (
        GPSLocationConsumer,
        DriverStatusConsumer,
        OrderEventsConsumer,
        RouteEventsConsumer,
    )
    
    gps_consumer = GPSLocationConsumer()
    driver_consumer = DriverStatusConsumer()
    order_consumer = OrderEventsConsumer()
    route_consumer = RouteEventsConsumer()
    
    # Inject WebSocket manager (if running in same process)
    # Note: In production, consumers should run as separate services
    try:
        from src.websocket_server import manager as ws_manager
        gps_consumer.set_websocket_manager(ws_manager)
        driver_consumer.set_websocket_manager(ws_manager)
        order_consumer.set_websocket_manager(ws_manager)
        route_consumer.set_websocket_manager(ws_manager)
        logger.info("WebSocket manager injected into consumers")
    except ImportError:
        logger.warning("WebSocket server not available")
    
    consumer_tasks = [
        await gps_consumer.start(),
        await driver_consumer.start(),
        await order_consumer.start(),
        await route_consumer.start(),
    ]
    logger.info("Kafka consumers started", count=len(consumer_tasks))
    
    yield
    
    # Shutdown consumers
    logger.info("Shutting down Kafka consumers...")
    for task in consumer_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    await gps_consumer.stop()
    await driver_consumer.stop()
    await order_consumer.stop()
    await route_consumer.stop()
    
    # Shutdown database and producer
    from src.database import close_db
    await close_db()
    producer.close()
    logger.info("FleetFlow API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Real-Time Delivery Optimization Platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    dependencies=[Depends(require_api_key)],
)

# Configure security middleware (CORS, rate limiting, security headers)
configure_security(app)

# Add Prometheus metrics middleware
app.add_middleware(PrometheusMiddleware)

# Include routers
app.include_router(monitoring.router, tags=["Monitoring"])  # No auth required for metrics
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(drivers.router, prefix="/api/v1/drivers", tags=["Drivers"])
app.include_router(routes.router, prefix="/api/v1/routes", tags=["Routes"])
app.include_router(vehicles.router, prefix="/api/v1/vehicles", tags=["Vehicles"])
app.include_router(optimization.router, prefix="/api/v1/optimization", tags=["Optimization"])
app.include_router(experiments.router, prefix="/api/v1", tags=["A/B Testing"])
app.include_router(rag_router, tags=["RAG"])

# GraphQL API
app.include_router(graphql_router, prefix="/graphql", tags=["GraphQL"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from src.database import check_db_health
    
    db_health = await check_db_health()
    kafka_stats = get_kafka_producer().stats
    
    overall_status = "healthy" if db_health["status"] == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "version": settings.app_version,
        "database": db_health,
        "kafka": kafka_stats,
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
