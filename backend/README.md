# FleetFlow Backend

## Quick Start

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e .

# Run the server
uvicorn src.main:app --reload --port 8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/orders` | GET/POST | Order management |
| `/api/v1/drivers` | GET | Driver management |
| `/api/v1/drivers/{id}/location` | POST | GPS tracking |
| `/api/v1/routes` | GET | Route management |
| `/api/v1/vehicles` | GET | Vehicle management |
| `/api/v1/optimization/optimize` | POST | Route optimization |

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
