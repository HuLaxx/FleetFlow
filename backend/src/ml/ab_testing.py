"""
ML A/B Testing Framework for FleetFlow.

Enables running experiments with multiple model versions,
collecting metrics, and determining winners.
"""

import random
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class ExperimentStatus(str, Enum):
    """Experiment lifecycle states."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TrafficSplitStrategy(str, Enum):
    """How to split traffic between variants."""

    RANDOM = "random"  # Pure random assignment
    STICKY = "sticky"  # Same user always gets same variant
    WEIGHTED = "weighted"  # Custom weights per variant


class ModelVariant(BaseModel):
    """A variant in an A/B experiment."""

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str
    model_version: str
    model_path: str | None = None
    weight: float = Field(default=0.5, ge=0, le=1)  # Traffic percentage

    # Metrics
    total_requests: int = 0
    total_success: int = 0
    total_latency_ms: float = 0.0

    # Custom metrics for ML
    total_distance_saved_km: float = 0.0
    total_routes_optimized: int = 0
    avg_optimization_score: float = 0.0


class Experiment(BaseModel):
    """An A/B experiment configuration."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str | None = None
    model_name: str  # e.g., "route_optimizer", "demand_forecaster"

    # Variants
    control: ModelVariant
    treatment: ModelVariant

    # Configuration
    traffic_split: TrafficSplitStrategy = TrafficSplitStrategy.RANDOM
    target_sample_size: int = 1000
    confidence_level: float = 0.95

    # State
    status: ExperimentStatus = ExperimentStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Winner
    winner_variant_id: str | None = None
    winner_confidence: float | None = None


class ExperimentResult(BaseModel):
    """Result of an experiment evaluation."""

    experiment_id: UUID
    variant_id: str
    variant_name: str

    # Core metrics
    sample_size: int
    success_rate: float
    avg_latency_ms: float

    # ML-specific metrics
    avg_distance_saved_km: float
    avg_optimization_score: float

    # Statistical
    p_value: float | None = None
    is_significant: bool = False
    lift_percent: float | None = None


class ABTestingService:
    """
    Service for managing ML model A/B experiments.

    Features:
    - Experiment creation and management
    - Traffic splitting
    - Metrics collection
    - Winner determination
    """

    def __init__(self):
        self.experiments: dict[UUID, Experiment] = {}
        self.user_assignments: dict[str, dict[UUID, str]] = {}  # user_id -> {exp_id: variant_id}

    def create_experiment(
        self,
        name: str,
        model_name: str,
        control_version: str,
        treatment_version: str,
        control_weight: float = 0.5,
        description: str | None = None,
    ) -> Experiment:
        """Create a new A/B experiment."""
        experiment = Experiment(
            name=name,
            description=description,
            model_name=model_name,
            control=ModelVariant(
                name="control",
                model_version=control_version,
                weight=control_weight,
            ),
            treatment=ModelVariant(
                name="treatment",
                model_version=treatment_version,
                weight=1 - control_weight,
            ),
        )

        self.experiments[experiment.id] = experiment
        logger.info(
            "Created experiment", experiment_id=str(experiment.id), name=name, model_name=model_name
        )

        return experiment

    def start_experiment(self, experiment_id: UUID) -> Experiment:
        """Start an experiment."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.now(UTC)

        logger.info("Started experiment", experiment_id=str(experiment_id))
        return experiment

    def stop_experiment(self, experiment_id: UUID) -> Experiment:
        """Stop an experiment and determine winner."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = datetime.now(UTC)

        # Determine winner
        self._determine_winner(experiment)

        logger.info(
            "Stopped experiment",
            experiment_id=str(experiment_id),
            winner=experiment.winner_variant_id,
        )
        return experiment

    def assign_variant(self, experiment_id: UUID, user_id: str | None = None) -> ModelVariant:
        """Assign a variant to a user/request."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        if experiment.status != ExperimentStatus.RUNNING:
            # Return control for non-running experiments
            return experiment.control

        # Check for sticky assignment
        if user_id and experiment.traffic_split == TrafficSplitStrategy.STICKY:
            if user_id in self.user_assignments:
                if experiment_id in self.user_assignments[user_id]:
                    variant_id = self.user_assignments[user_id][experiment_id]
                    return (
                        experiment.control
                        if variant_id == experiment.control.id
                        else experiment.treatment
                    )

        # Random assignment based on weights
        if random.random() < experiment.control.weight:
            variant = experiment.control
        else:
            variant = experiment.treatment

        # Store sticky assignment
        if user_id and experiment.traffic_split == TrafficSplitStrategy.STICKY:
            if user_id not in self.user_assignments:
                self.user_assignments[user_id] = {}
            self.user_assignments[user_id][experiment_id] = variant.id

        return variant

    def record_result(
        self,
        experiment_id: UUID,
        variant_id: str,
        success: bool,
        latency_ms: float,
        distance_saved_km: float = 0.0,
        optimization_score: float = 0.0,
    ) -> None:
        """Record a result for a variant."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return

        # Find variant
        variant = None
        if experiment.control.id == variant_id:
            variant = experiment.control
        elif experiment.treatment.id == variant_id:
            variant = experiment.treatment

        if not variant:
            return

        # Update metrics
        variant.total_requests += 1
        if success:
            variant.total_success += 1
        variant.total_latency_ms += latency_ms
        variant.total_distance_saved_km += distance_saved_km
        variant.total_routes_optimized += 1 if distance_saved_km > 0 else 0

        # Running average for score
        n = variant.total_routes_optimized
        if n > 0:
            variant.avg_optimization_score = (
                variant.avg_optimization_score * (n - 1) + optimization_score
            ) / n

    def get_results(self, experiment_id: UUID) -> dict[str, ExperimentResult]:
        """Get current results for an experiment."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        results = {}
        for variant in [experiment.control, experiment.treatment]:
            n = variant.total_requests
            results[variant.id] = ExperimentResult(
                experiment_id=experiment_id,
                variant_id=variant.id,
                variant_name=variant.name,
                sample_size=n,
                success_rate=variant.total_success / n if n > 0 else 0,
                avg_latency_ms=variant.total_latency_ms / n if n > 0 else 0,
                avg_distance_saved_km=(
                    variant.total_distance_saved_km / variant.total_routes_optimized
                    if variant.total_routes_optimized > 0
                    else 0
                ),
                avg_optimization_score=variant.avg_optimization_score,
            )

        return results

    def _determine_winner(self, experiment: Experiment) -> None:
        """Determine the winning variant using statistical tests."""
        control = experiment.control
        treatment = experiment.treatment

        # Simple comparison (in production use proper statistical tests)
        control_score = self._calculate_score(control)
        treatment_score = self._calculate_score(treatment)

        # Need minimum sample size
        min_samples = experiment.target_sample_size // 2
        if control.total_requests < min_samples or treatment.total_requests < min_samples:
            experiment.winner_variant_id = None
            experiment.winner_confidence = None
            return

        # Determine winner
        if treatment_score > control_score * 1.05:  # 5% lift threshold
            experiment.winner_variant_id = treatment.id
            experiment.winner_confidence = 0.95
        elif control_score > treatment_score * 1.05:
            experiment.winner_variant_id = control.id
            experiment.winner_confidence = 0.95
        else:
            # No clear winner
            experiment.winner_variant_id = control.id  # Default to control
            experiment.winner_confidence = 0.5

    def _calculate_score(self, variant: ModelVariant) -> float:
        """Calculate composite score for a variant."""
        if variant.total_requests == 0:
            return 0.0

        success_rate = variant.total_success / variant.total_requests
        avg_latency = variant.total_latency_ms / variant.total_requests

        # Composite score (higher is better)
        # Weight: 50% success, 30% optimization score, 20% latency (inverted)
        latency_score = max(0, 1 - (avg_latency / 1000))  # Normalize to 0-1

        return 0.5 * success_rate + 0.3 * variant.avg_optimization_score + 0.2 * latency_score


# Singleton instance
_ab_testing_service: ABTestingService | None = None


def get_ab_testing_service() -> ABTestingService:
    """Get or create A/B testing service singleton."""
    global _ab_testing_service
    if _ab_testing_service is None:
        _ab_testing_service = ABTestingService()
    return _ab_testing_service
