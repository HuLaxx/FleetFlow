"""
FleetFlow Real-Time Inference Pipeline

Streaming inference for:
- GPS location processing
- Real-time ETA updates
- Dynamic re-routing triggers
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from collections import deque
import logging

try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
except ImportError:
    AIOKafkaConsumer = None
    AIOKafkaProducer = None

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DriverState:
    """Real-time driver state."""
    driver_id: str
    latitude: float = 0.0
    longitude: float = 0.0
    speed_kmh: float = 0.0
    heading: float = 0.0
    current_route_id: Optional[str] = None
    current_stop_index: int = 0
    eta_to_next_stop: Optional[datetime] = None
    last_update: datetime = field(default_factory=datetime.utcnow)
    location_history: deque = field(default_factory=lambda: deque(maxlen=100))


@dataclass
class InferenceResult:
    """Result from inference pipeline."""
    inference_type: str
    driver_id: Optional[str]
    route_id: Optional[str]
    prediction: Dict[str, Any]
    confidence: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ETAPredictor:
    """
    Real-time ETA prediction model.
    
    Uses:
    - Current speed and location
    - Historical traffic patterns
    - Remaining stops
    """
    
    def __init__(self):
        self.traffic_patterns: Dict[str, float] = {}
    
    def predict(
        self,
        current_location: tuple,
        destination: tuple,
        current_speed: float,
        hour: int,
        day_of_week: int
    ) -> Dict[str, Any]:
        """
        Predict ETA to destination.
        
        Returns:
            - eta_minutes: Predicted ETA
            - confidence: Prediction confidence
            - factors: Contributing factors
        """
        # Calculate distance
        lat1, lon1 = current_location
        lat2, lon2 = destination
        distance_km = self._haversine(lat1, lon1, lat2, lon2)
        
        # Base speed (use current if moving, else default)
        base_speed = max(current_speed, 25)  # km/h
        
        # Time of day factor
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            time_factor = 1.4  # Rush hour
        elif 22 <= hour or hour <= 5:
            time_factor = 0.8  # Night
        else:
            time_factor = 1.0
        
        # Day of week factor
        if day_of_week >= 5:  # Weekend
            time_factor *= 0.85
        
        # Calculate ETA
        effective_speed = base_speed / time_factor
        eta_minutes = (distance_km / effective_speed) * 60
        
        # Add service time buffer
        eta_minutes += 2  # Buffer
        
        # Confidence based on distance and speed variability
        confidence = min(0.95, 0.6 + 0.1 * (10 / max(distance_km, 1)))
        
        return {
            "eta_minutes": round(eta_minutes, 1),
            "distance_km": round(distance_km, 2),
            "effective_speed_kmh": round(effective_speed, 1),
            "confidence": round(confidence, 3),
            "factors": {
                "time_of_day": time_factor,
                "distance": distance_km,
            }
        }
    
    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in km."""
        R = 6371
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))


class ReRoutingDetector:
    """
    Detects when re-routing is needed.
    
    Triggers:
    - Significant delay detected
    - Driver off-route
    - Traffic incident
    - Order cancellation
    """
    
    def __init__(
        self,
        delay_threshold_minutes: float = 15,
        off_route_threshold_km: float = 0.5
    ):
        self.delay_threshold = delay_threshold_minutes
        self.off_route_threshold = off_route_threshold_km
    
    def check_rerouting_needed(
        self,
        driver_state: DriverState,
        planned_locations: List[tuple],
        planned_etas: List[datetime]
    ) -> Dict[str, Any]:
        """
        Check if re-routing is needed.
        
        Returns:
            - needs_rerouting: bool
            - reason: Reason for rerouting
            - severity: low/medium/high
        """
        if not planned_locations or driver_state.current_stop_index >= len(planned_locations):
            return {"needs_rerouting": False, "reason": None, "severity": None}
        
        current_loc = (driver_state.latitude, driver_state.longitude)
        next_stop = planned_locations[driver_state.current_stop_index]
        planned_eta = planned_etas[driver_state.current_stop_index]
        
        # Check delay
        if driver_state.eta_to_next_stop:
            delay = (driver_state.eta_to_next_stop - planned_eta).total_seconds() / 60
            
            if delay > self.delay_threshold:
                return {
                    "needs_rerouting": True,
                    "reason": "significant_delay",
                    "severity": "high" if delay > 30 else "medium",
                    "delay_minutes": delay
                }
        
        # Check off-route (simplified - would use route geometry)
        # This is a basic check using distance to next stop vs expected
        
        return {"needs_rerouting": False, "reason": None, "severity": None}


class InferencePipeline:
    """
    Real-time streaming inference pipeline.
    
    Consumes GPS events and produces:
    - Updated ETAs
    - Rerouting triggers
    - Performance metrics
    """
    
    def __init__(
        self,
        kafka_bootstrap_servers: str = "localhost:9092",
        consumer_group: str = "fleetflow-inference"
    ):
        self.bootstrap_servers = kafka_bootstrap_servers
        self.consumer_group = consumer_group
        
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._producer: Optional[AIOKafkaProducer] = None
        
        # State management
        self.driver_states: Dict[str, DriverState] = {}
        
        # Models
        self.eta_predictor = ETAPredictor()
        self.rerouting_detector = ReRoutingDetector()
        
        # Callbacks
        self._inference_callbacks: List[Callable[[InferenceResult], None]] = []
        
        self._running = False
    
    def add_callback(self, callback: Callable[[InferenceResult], None]) -> None:
        """Add inference result callback."""
        self._inference_callbacks.append(callback)
    
    def _emit_result(self, result: InferenceResult) -> None:
        """Emit inference result to callbacks."""
        for callback in self._inference_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    async def _process_gps_event(self, event: Dict[str, Any]) -> None:
        """Process a GPS location event."""
        driver_id = event.get('driver_id')
        if not driver_id:
            return
        
        location = event.get('location') or {}
        latitude = event.get('latitude', location.get('latitude'))
        longitude = event.get('longitude', location.get('longitude'))

        # Update driver state
        if driver_id not in self.driver_states:
            self.driver_states[driver_id] = DriverState(driver_id=driver_id)
        
        state = self.driver_states[driver_id]
        if latitude is not None:
            state.latitude = latitude
        if longitude is not None:
            state.longitude = longitude
        state.speed_kmh = event.get('speed_kmh', state.speed_kmh)
        state.heading = event.get('heading', state.heading)
        state.last_update = datetime.utcnow()
        
        # Add to history
        state.location_history.append({
            'lat': state.latitude,
            'lon': state.longitude,
            'speed': state.speed_kmh,
            'time': state.last_update
        })
        
        # Run ETA prediction if driver has active route
        if state.current_route_id:
            # Get next stop (would come from route data)
            next_stop = (40.7484, -73.9857)  # Placeholder
            
            now = datetime.utcnow()
            prediction = self.eta_predictor.predict(
                current_location=(state.latitude, state.longitude),
                destination=next_stop,
                current_speed=state.speed_kmh,
                hour=now.hour,
                day_of_week=now.weekday()
            )
            
            # Update ETA
            state.eta_to_next_stop = now + timedelta(minutes=prediction['eta_minutes'])
            
            # Emit result
            self._emit_result(InferenceResult(
                inference_type="eta_update",
                driver_id=driver_id,
                route_id=state.current_route_id,
                prediction=prediction,
                confidence=prediction['confidence']
            ))
            
            # Check for rerouting
            # (Would need planned route data)
    
    async def _process_route_event(self, event: Dict[str, Any]) -> None:
        """Process route assignment event."""
        driver_id = event.get('driver_id')
        route_id = event.get('route_id')
        
        if driver_id and route_id:
            if driver_id not in self.driver_states:
                self.driver_states[driver_id] = DriverState(driver_id=driver_id)
            
            state = self.driver_states[driver_id]
            state.current_route_id = route_id
            state.current_stop_index = 0
    
    async def start(self) -> None:
        """Start the inference pipeline."""
        if AIOKafkaConsumer is None:
            logger.warning("aiokafka not installed, running in demo mode")
            return
        
        self._consumer = AIOKafkaConsumer(
            'gps.location',
            'routes.created',
            'routes.started',
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.consumer_group,
            auto_offset_reset='latest',
            value_deserializer=lambda v: json.loads(v.decode('utf-8'))
        )
        
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        await self._consumer.start()
        await self._producer.start()
        
        self._running = True
        logger.info("Inference pipeline started")
        
        try:
            async for message in self._consumer:
                if not self._running:
                    break
                
                topic = message.topic
                event = message.value
                
                if topic == 'gps.location':
                    await self._process_gps_event(event)
                elif topic in ('routes.created', 'routes.started'):
                    await self._process_route_event(event)
        
        finally:
            await self._consumer.stop()
            await self._producer.stop()
    
    async def stop(self) -> None:
        """Stop the pipeline."""
        self._running = False
    
    def get_driver_state(self, driver_id: str) -> Optional[DriverState]:
        """Get current state for a driver."""
        return self.driver_states.get(driver_id)
    
    def get_all_etas(self) -> Dict[str, Dict[str, Any]]:
        """Get current ETAs for all active drivers."""
        etas = {}
        for driver_id, state in self.driver_states.items():
            if state.eta_to_next_stop:
                etas[driver_id] = {
                    "route_id": state.current_route_id,
                    "current_stop": state.current_stop_index,
                    "eta": state.eta_to_next_stop.isoformat(),
                    "location": {
                        "latitude": state.latitude,
                        "longitude": state.longitude,
                    },
                    "speed_kmh": state.speed_kmh,
                }
        return etas


# Demo runner
async def demo_pipeline():
    """Run demo inference pipeline."""
    pipeline = InferencePipeline()
    
    def print_result(result: InferenceResult):
        print(f"[{result.inference_type}] Driver {result.driver_id}: {result.prediction}")
    
    pipeline.add_callback(print_result)
    
    # Simulate GPS events
    for i in range(10):
        await pipeline._process_gps_event({
            "driver_id": "driver_1",
            "latitude": 40.7128 + i * 0.001,
            "longitude": -74.0060 + i * 0.001,
            "speed_kmh": 35 + np.random.uniform(-5, 5),
            "heading": 45.0,
        })
        
        # Simulate having a route
        pipeline.driver_states["driver_1"].current_route_id = "route_1"
        
        await asyncio.sleep(0.5)
    
    print("\nFinal ETAs:", pipeline.get_all_etas())


if __name__ == "__main__":
    asyncio.run(demo_pipeline())
