"""
A/B Testing API endpoints for ML experiments.
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.ml.ab_testing import (
    get_ab_testing_service,
    Experiment,
    ExperimentStatus,
    ExperimentResult,
    TrafficSplitStrategy,
)
from src.auth.dependencies import require_admin

router = APIRouter(prefix="/experiments", tags=["A/B Testing"])


# Request/Response Models
class CreateExperimentRequest(BaseModel):
    """Create experiment request."""
    name: str
    description: Optional[str] = None
    model_name: str
    control_version: str
    treatment_version: str
    control_weight: float = Field(default=0.5, ge=0.1, le=0.9)


class ExperimentResponse(BaseModel):
    """Experiment response."""
    id: str
    name: str
    model_name: str
    status: str
    control_version: str
    treatment_version: str
    control_weight: float
    created_at: str
    started_at: Optional[str] = None
    winner: Optional[str] = None


class RecordResultRequest(BaseModel):
    """Record experiment result."""
    variant_id: str
    success: bool
    latency_ms: float
    distance_saved_km: float = 0.0
    optimization_score: float = 0.0


# Endpoints
@router.post("", response_model=ExperimentResponse)
async def create_experiment(
    request: CreateExperimentRequest,
    admin = Depends(require_admin),
):
    """Create a new A/B experiment."""
    service = get_ab_testing_service()
    
    experiment = service.create_experiment(
        name=request.name,
        description=request.description,
        model_name=request.model_name,
        control_version=request.control_version,
        treatment_version=request.treatment_version,
        control_weight=request.control_weight,
    )
    
    return ExperimentResponse(
        id=str(experiment.id),
        name=experiment.name,
        model_name=experiment.model_name,
        status=experiment.status.value,
        control_version=experiment.control.model_version,
        treatment_version=experiment.treatment.model_version,
        control_weight=experiment.control.weight,
        created_at=experiment.created_at.isoformat(),
    )


@router.get("")
async def list_experiments():
    """List all experiments."""
    service = get_ab_testing_service()
    
    experiments = []
    for exp in service.experiments.values():
        experiments.append(ExperimentResponse(
            id=str(exp.id),
            name=exp.name,
            model_name=exp.model_name,
            status=exp.status.value,
            control_version=exp.control.model_version,
            treatment_version=exp.treatment.model_version,
            control_weight=exp.control.weight,
            created_at=exp.created_at.isoformat(),
            started_at=exp.started_at.isoformat() if exp.started_at else None,
            winner=exp.winner_variant_id,
        ))
    
    return {"experiments": experiments}


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: UUID):
    """Get experiment by ID."""
    service = get_ab_testing_service()
    exp = service.experiments.get(experiment_id)
    
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return ExperimentResponse(
        id=str(exp.id),
        name=exp.name,
        model_name=exp.model_name,
        status=exp.status.value,
        control_version=exp.control.model_version,
        treatment_version=exp.treatment.model_version,
        control_weight=exp.control.weight,
        created_at=exp.created_at.isoformat(),
        started_at=exp.started_at.isoformat() if exp.started_at else None,
        winner=exp.winner_variant_id,
    )


@router.post("/{experiment_id}/start")
async def start_experiment(
    experiment_id: UUID,
    admin = Depends(require_admin),
):
    """Start an experiment."""
    service = get_ab_testing_service()
    
    try:
        experiment = service.start_experiment(experiment_id)
        return {"status": "started", "experiment_id": str(experiment_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{experiment_id}/stop")
async def stop_experiment(
    experiment_id: UUID,
    admin = Depends(require_admin),
):
    """Stop an experiment and determine winner."""
    service = get_ab_testing_service()
    
    try:
        experiment = service.stop_experiment(experiment_id)
        return {
            "status": "completed",
            "experiment_id": str(experiment_id),
            "winner": experiment.winner_variant_id,
            "confidence": experiment.winner_confidence,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{experiment_id}/assign")
async def assign_variant(
    experiment_id: UUID,
    user_id: Optional[str] = None,
):
    """Get variant assignment for a user/request."""
    service = get_ab_testing_service()
    
    try:
        variant = service.assign_variant(experiment_id, user_id)
        return {
            "variant_id": variant.id,
            "variant_name": variant.name,
            "model_version": variant.model_version,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{experiment_id}/results")
async def record_result(
    experiment_id: UUID,
    request: RecordResultRequest,
):
    """Record a result for an experiment."""
    service = get_ab_testing_service()
    
    service.record_result(
        experiment_id=experiment_id,
        variant_id=request.variant_id,
        success=request.success,
        latency_ms=request.latency_ms,
        distance_saved_km=request.distance_saved_km,
        optimization_score=request.optimization_score,
    )
    
    return {"status": "recorded"}


@router.get("/{experiment_id}/metrics")
async def get_experiment_metrics(experiment_id: UUID):
    """Get current metrics for an experiment."""
    service = get_ab_testing_service()
    
    try:
        results = service.get_results(experiment_id)
        return {
            "experiment_id": str(experiment_id),
            "variants": {
                variant_id: {
                    "name": result.variant_name,
                    "sample_size": result.sample_size,
                    "success_rate": result.success_rate,
                    "avg_latency_ms": result.avg_latency_ms,
                    "avg_distance_saved_km": result.avg_distance_saved_km,
                    "avg_optimization_score": result.avg_optimization_score,
                }
                for variant_id, result in results.items()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
