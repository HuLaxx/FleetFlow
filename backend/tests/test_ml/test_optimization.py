"""
Tests for Route Optimization (VRP Solver).
Unit tests that don't require full app context.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock
import sys
import os

# Add ml directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ml'))


class TestVRPOptimizer:
    """Tests for VehicleRoutingOptimizer."""
    
    def test_optimizer_initialization(self):
        """Test optimizer can be initialized."""
        try:
            from route_optimizer import VehicleRoutingOptimizer
            optimizer = VehicleRoutingOptimizer()
            assert optimizer is not None
        except ImportError:
            pytest.skip("OR-Tools not installed")
    
    def test_haversine_distance_calculation(self):
        """Test distance calculation between coordinates."""
        try:
            from route_optimizer import VehicleRoutingOptimizer
            optimizer = VehicleRoutingOptimizer()
            
            # NYC to LA approximate distance
            nyc = (40.7128, -74.0060)
            la = (34.0522, -118.2437)
            
            distance = optimizer._haversine(nyc[0], nyc[1], la[0], la[1])
            
            # Should be ~3940 km
            assert 3900 < distance < 4000
        except ImportError:
            pytest.skip("OR-Tools not installed")
    
    def test_haversine_same_location(self):
        """Test distance between same point is zero."""
        try:
            from route_optimizer import VehicleRoutingOptimizer
            optimizer = VehicleRoutingOptimizer()
            distance = optimizer._haversine(40.7128, -74.0060, 40.7128, -74.0060)
            assert distance == 0.0
        except ImportError:
            pytest.skip("OR-Tools not installed")


class TestDemandForecaster:
    """Tests for LSTM demand forecasting model."""
    
    def test_model_initialization(self):
        """Test model can be initialized."""
        try:
            import torch
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ml', 'forecasting'))
            from model import DemandForecaster
            
            model = DemandForecaster(
                input_size=10,
                hidden_size=64,
                num_layers=2,
                output_size=1
            )
            assert model is not None
        except ImportError:
            pytest.skip("PyTorch not installed")
    
    def test_forward_pass(self):
        """Test model forward pass."""
        try:
            import torch
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ml', 'forecasting'))
            from model import DemandForecaster
            
            model = DemandForecaster(
                input_size=10,
                hidden_size=64,
                num_layers=2,
                output_size=1
            )
            
            # Create dummy input (batch=4, seq_len=24, features=10)
            x = torch.randn(4, 24, 10)
            output = model(x)
            
            assert output.shape == (4, 1)
        except ImportError:
            pytest.skip("PyTorch not installed")
    
    def test_model_can_train(self):
        """Test model can perform gradient update."""
        try:
            import torch
            import torch.nn as nn
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ml', 'forecasting'))
            from model import DemandForecaster
            
            model = DemandForecaster(
                input_size=10,
                hidden_size=32,
                num_layers=1,
                output_size=1
            )
            
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            criterion = nn.MSELoss()
            
            # Single training step
            x = torch.randn(4, 24, 10)
            y = torch.randn(4, 1)
            
            optimizer.zero_grad()
            output = model(x)
            loss = criterion(output, y)
            loss.backward()
            optimizer.step()
            
            assert loss.item() >= 0
        except ImportError:
            pytest.skip("PyTorch not installed")
