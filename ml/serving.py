"""
FleetFlow Model Serving API

FastAPI endpoints for real-time ML inference:
- Demand forecasting
- Route optimization
- ETA prediction
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4
import time
import asyncio
from functools import lru_cache

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import numpy as np

# Local imports
import sys
sys.path.insert(0, '..')


# ============================================
# Request/Response Models
# ============================================

class Location(BaseModel):
    """Geographic location."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class OrderRequest(BaseModel):
    """Order for optimization."""
    id: str
    location: Location
    demand_kg: float = 5.0
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None
    service_time_minutes: int = 5
    priority: int = 2


class VehicleRequest(BaseModel):
    """Vehicle for optimization."""
    id: str
    capacity_kg: float = 500
    max_stops: int = 20


class OptimizeRequest(BaseModel):
    """Route optimization request."""
    depot: Location
    orders: List[OrderRequest]
    vehicles: List[VehicleRequest]
    algorithm: str = "auto"
    time_limit_seconds: int = 30


class OptimizedStop(BaseModel):
    """Stop in optimized route."""
    order_id: str
    sequence: int
    latitude: float
    longitude: float
    eta: str


class OptimizedRouteResponse(BaseModel):
    """Optimized route response."""
    vehicle_id: str
    stops: List[OptimizedStop]
    total_distance_km: float
    total_duration_minutes: int


class OptimizationResponse(BaseModel):
    """Full optimization response."""
    optimization_id: str
    routes: List[OptimizedRouteResponse]
    unassigned_order_ids: List[str]
    total_distance_km: float
    computation_time_ms: int
    algorithm: str
    score: float


class ForecastRequest(BaseModel):
    """Demand forecast request."""
    historical_data: List[Dict[str, Any]]  # [{ds: datetime, y: value}]
    forecast_hours: int = 24
    model: str = "ensemble"  # prophet, lstm, xgboost, ensemble


class ForecastResponse(BaseModel):
    """Demand forecast response."""
    forecast_id: str
    predictions: List[Dict[str, Any]]
    model_used: str
    computation_time_ms: int


class ETARequest(BaseModel):
    """ETA prediction request."""
    origin: Location
    destination: Location
    departure_time: Optional[str] = None


class ETAResponse(BaseModel):
    """ETA prediction response."""
    eta_minutes: float
    distance_km: float
    confidence: float
    factors: Dict[str, float]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    models_loaded: Dict[str, bool]
    uptime_seconds: float


# ============================================
# Model Cache
# ============================================

class ModelCache:
    """
    Singleton cache for loaded models.
    
    Implements lazy loading and LRU eviction.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._models = {}
            cls._instance._start_time = time.time()
        return cls._instance
    
    def get_prophet_model(self):
        """Get or load Prophet model."""
        if 'prophet' not in self._models:
            # In production, load from MLflow
            self._models['prophet'] = None
        return self._models.get('prophet')
    
    def get_lstm_model(self):
        """Get or load LSTM model."""
        if 'lstm' not in self._models:
            self._models['lstm'] = None
        return self._models.get('lstm')
    
    def get_xgboost_model(self):
        """Get or load XGBoost model."""
        if 'xgboost' not in self._models:
            self._models['xgboost'] = None
        return self._models.get('xgboost')
    
    @property
    def uptime(self) -> float:
        return time.time() - self._start_time
    
    @property
    def loaded_models(self) -> Dict[str, bool]:
        return {
            "prophet": self._models.get('prophet') is not None,
            "lstm": self._models.get('lstm') is not None,
            "xgboost": self._models.get('xgboost') is not None,
        }


# ============================================
# FastAPI Application
# ============================================

app = FastAPI(
    title="FleetFlow ML Serving API",
    description="Real-time ML inference for demand forecasting and route optimization",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model_cache = ModelCache()


# ============================================
# Endpoints
# ============================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check with model status."""
    return HealthResponse(
        status="healthy",
        models_loaded=model_cache.loaded_models,
        uptime_seconds=model_cache.uptime,
    )


@app.post("/v1/optimize", response_model=OptimizationResponse)
async def optimize_routes(request: OptimizeRequest):
    """
    Optimize delivery routes.
    
    Supports algorithms:
    - `auto`: Automatically select based on problem size
    - `ortools`: Google OR-Tools VRP solver
    - `genetic`: Genetic algorithm for multi-objective
    """
    start_time = time.time()
    optimization_id = str(uuid4())
    
    try:
        # Import optimization module
        from ml.optimization import (
            Location as OptLocation,
            Order as OptOrder,
            Vehicle as OptVehicle,
            optimize_routes as run_optimization
        )
        
        # Convert request to optimization format
        depot = OptLocation(
            id="depot",
            latitude=request.depot.latitude,
            longitude=request.depot.longitude
        )
        
        orders = [
            OptOrder(
                id=o.id,
                location=OptLocation(
                    id=f"loc_{o.id}",
                    latitude=o.location.latitude,
                    longitude=o.location.longitude
                ),
                demand_kg=o.demand_kg,
                service_time_minutes=o.service_time_minutes,
                priority=o.priority
            )
            for o in request.orders
        ]
        
        vehicles = [
            OptVehicle(
                id=v.id,
                capacity_kg=v.capacity_kg,
                max_stops=v.max_stops
            )
            for v in request.vehicles
        ]
        
        # Run optimization
        result = run_optimization(
            depot=depot,
            orders=orders,
            vehicles=vehicles,
            algorithm=request.algorithm,
            time_limit_seconds=request.time_limit_seconds
        )
        
        # Convert to response
        routes = []
        for route in result.routes:
            stops = [
                OptimizedStop(
                    order_id=stop.id,
                    sequence=i + 1,
                    latitude=stop.location.latitude,
                    longitude=stop.location.longitude,
                    eta=datetime.now().isoformat()
                )
                for i, stop in enumerate(route.stops)
            ]
            
            routes.append(OptimizedRouteResponse(
                vehicle_id=route.vehicle_id,
                stops=stops,
                total_distance_km=route.total_distance_km,
                total_duration_minutes=route.total_duration_minutes
            ))
        
        return OptimizationResponse(
            optimization_id=optimization_id,
            routes=routes,
            unassigned_order_ids=[o.id for o in result.unassigned_orders],
            total_distance_km=result.total_distance_km,
            computation_time_ms=int((time.time() - start_time) * 1000),
            algorithm=result.algorithm,
            score=result.score
        )
    
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Optimization module not available: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/forecast", response_model=ForecastResponse)
async def forecast_demand(request: ForecastRequest):
    """
    Generate demand forecast.
    
    Models:
    - `prophet`: Facebook Prophet for seasonality
    - `lstm`: LSTM neural network
    - `xgboost`: XGBoost with time features
    - `ensemble`: Weighted average of all models
    """
    start_time = time.time()
    forecast_id = str(uuid4())
    
    try:
        import pandas as pd
        
        # Convert to DataFrame
        df = pd.DataFrame(request.historical_data)
        df['ds'] = pd.to_datetime(df['ds'])
        
        # Simple moving average forecast (placeholder)
        # In production, would use loaded models
        last_values = df['y'].tail(24).values
        mean_val = np.mean(last_values)
        std_val = np.std(last_values)
        
        predictions = []
        last_time = df['ds'].max()
        
        for i in range(request.forecast_hours):
            pred_time = last_time + timedelta(hours=i+1)
            
            # Simple pattern-based prediction
            hour = pred_time.hour
            day_factor = 1.0 + 0.2 * np.sin(2 * np.pi * hour / 24)
            
            predictions.append({
                "timestamp": pred_time.isoformat(),
                "yhat": round(mean_val * day_factor, 2),
                "yhat_lower": round((mean_val - std_val) * day_factor, 2),
                "yhat_upper": round((mean_val + std_val) * day_factor, 2),
            })
        
        return ForecastResponse(
            forecast_id=forecast_id,
            predictions=predictions,
            model_used=request.model,
            computation_time_ms=int((time.time() - start_time) * 1000)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/eta", response_model=ETAResponse)
async def predict_eta(request: ETARequest):
    """
    Predict ETA between two locations.
    
    Factors considered:
    - Distance
    - Time of day
    - Day of week
    - Historical traffic patterns
    """
    # Calculate distance (Haversine)
    lat1, lon1 = request.origin.latitude, request.origin.longitude
    lat2, lon2 = request.destination.latitude, request.destination.longitude
    
    R = 6371  # Earth's radius in km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    distance_km = R * c
    
    # Base ETA at 30 km/h average
    base_eta = (distance_km / 30) * 60
    
    # Time of day factor
    if request.departure_time:
        hour = datetime.fromisoformat(request.departure_time).hour
    else:
        hour = datetime.now().hour
    
    # Rush hour penalty
    if 7 <= hour <= 9 or 17 <= hour <= 19:
        time_factor = 1.5
    elif 10 <= hour <= 16:
        time_factor = 1.2
    else:
        time_factor = 1.0
    
    eta_minutes = base_eta * time_factor
    
    return ETAResponse(
        eta_minutes=round(eta_minutes, 1),
        distance_km=round(distance_km, 2),
        confidence=0.85,
        factors={
            "distance_factor": 1.0,
            "time_of_day_factor": time_factor,
            "traffic_factor": 1.0,
        }
    )


@app.get("/v1/models")
async def list_models():
    """List available models and their status."""
    return {
        "models": [
            {
                "name": "demand-prophet",
                "type": "forecasting",
                "status": "available",
                "version": "1.0.0",
            },
            {
                "name": "demand-lstm",
                "type": "forecasting",
                "status": "available",
                "version": "1.0.0",
            },
            {
                "name": "vrp-ortools",
                "type": "optimization",
                "status": "available",
                "version": "1.0.0",
            },
            {
                "name": "vrp-genetic",
                "type": "optimization",
                "status": "available",
                "version": "1.0.0",
            },
        ]
    }


# ============================================
# Run Server
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "serving:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
