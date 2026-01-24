"""
Unit tests for data fixtures and utilities.
"""

import pytest
from datetime import datetime


class TestSampleData:
    """Tests for sample data fixtures."""
    
    def test_sample_driver_data(self, sample_driver_data):
        """Test driver data fixture has required fields."""
        assert "name" in sample_driver_data
        assert "email" in sample_driver_data
        assert "employee_id" in sample_driver_data
        assert sample_driver_data["status"] == "available"
    
    def test_sample_order_data(self, sample_order_data):
        """Test order data fixture has required fields."""
        assert "order_number" in sample_order_data
        assert "customer_name" in sample_order_data
        assert "delivery_latitude" in sample_order_data
        assert "delivery_longitude" in sample_order_data
        assert sample_order_data["status"] == "pending"
    
    def test_sample_vehicle_data(self, sample_vehicle_data):
        """Test vehicle data fixture has required fields."""
        assert "vehicle_number" in sample_vehicle_data
        assert "capacity_kg" in sample_vehicle_data
        assert sample_vehicle_data["capacity_kg"] == 1000.0
    
    def test_sample_depot_data(self, sample_depot_data):
        """Test depot data fixture has required fields."""
        assert "name" in sample_depot_data
        assert "latitude" in sample_depot_data
        assert "longitude" in sample_depot_data


class TestDateUtilities:
    """Tests for date/time handling."""
    
    def test_datetime_format(self, sample_order_data):
        """Test datetime fields are properly formatted."""
        # Should be ISO format
        assert "time_window_start" in sample_order_data
        # Should be parseable
        datetime.fromisoformat(sample_order_data["time_window_start"])
    
    def test_order_date_is_today(self, sample_order_data):
        """Test order date is set correctly."""
        today = datetime.utcnow().date().isoformat()
        assert sample_order_data["delivery_date"] == today
