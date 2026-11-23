# Production packaging for FleetFlow's real FastAPI application.
# The source MUST be copied before 'pip install .' for Hatchling to build it.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN groupadd --system fleetflow && useradd --system --gid fleetflow fleetflow

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN python -m pip install .

RUN chown -R fleetflow:fleetflow /app
USER fleetflow

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" || exit 1

EXPOSE 8000

# Single worker required by the existing in-process WebSocket/Kafka consumer
# architecture. Multiple Uvicorn workers would diverge their subscribed state.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
