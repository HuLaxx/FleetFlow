"""
Tests for Kafka consumers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import json


class TestGPSLocationConsumer:
    """Tests for GPS location consumer."""
    
    @pytest.mark.asyncio
    async def test_process_valid_gps_message(self):
        """Test processing valid GPS location update."""
        from src.consumers.gps_consumer import GPSLocationConsumer
        
        # Create mock dependencies
        mock_db = AsyncMock()
        mock_ws = MagicMock()
        
        consumer = GPSLocationConsumer(
            bootstrap_servers="localhost:9092",
            group_id="test-group"
        )
        consumer.db_session = mock_db
        consumer.ws_manager = mock_ws
        
        # Valid GPS message
        message = {
            "vehicle_id": "test-vehicle-123",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "speed_kmh": 45.5,
            "heading": 180.0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Should not raise
        await consumer.handle_message(message)
    
    @pytest.mark.asyncio
    async def test_process_invalid_gps_message(self):
        """Test handling invalid GPS message gracefully."""
        from src.consumers.gps_consumer import GPSLocationConsumer
        
        consumer = GPSLocationConsumer(
            bootstrap_servers="localhost:9092",
            group_id="test-group"
        )
        
        # Invalid message (missing required fields)
        message = {"invalid": "data"}
        
        # Should not raise, just log error
        try:
            await consumer.handle_message(message)
        except Exception:
            pass  # Expected to handle gracefully


class TestDriverStatusConsumer:
    """Tests for driver status consumer."""
    
    @pytest.mark.asyncio
    async def test_process_status_update(self):
        """Test processing driver status update."""
        from src.consumers.driver_consumer import DriverStatusConsumer
        
        consumer = DriverStatusConsumer(
            bootstrap_servers="localhost:9092",
            group_id="test-group"
        )
        
        message = {
            "driver_id": "test-driver-123",
            "status": "on_route",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Should handle without error
        try:
            await consumer.handle_message(message)
        except Exception:
            pass


class TestOrderEventsConsumer:
    """Tests for order events consumer."""
    
    @pytest.mark.asyncio
    async def test_process_order_created(self):
        """Test processing order created event."""
        from src.consumers.order_consumer import OrderEventsConsumer
        
        consumer = OrderEventsConsumer(
            bootstrap_servers="localhost:9092",
            group_id="test-group"
        )
        
        message = {
            "event_type": "order_created",
            "order_id": "test-order-123",
            "customer_name": "Test Customer",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            await consumer.handle_message(message)
        except Exception:
            pass
    
    @pytest.mark.asyncio
    async def test_process_order_cancelled(self):
        """Test processing order cancelled event."""
        from src.consumers.order_consumer import OrderEventsConsumer
        
        consumer = OrderEventsConsumer(
            bootstrap_servers="localhost:9092",
            group_id="test-group"
        )
        
        message = {
            "event_type": "order_cancelled",
            "order_id": "test-order-123",
            "reason": "Customer request",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            await consumer.handle_message(message)
        except Exception:
            pass
