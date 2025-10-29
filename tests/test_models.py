"""
Unit tests for data models.

Tests the functionality of Airport, WeatherData, FlightInfo, and WeatherResult models.
Requirements: 1.2, 2.4
"""

import pytest
from datetime import datetime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.models import (
    Airport, WeatherData, FlightInfo, WeatherResult,
    WeatherStatus, ErrorTypes
)


class TestAirport:
    """Test cases for Airport model."""
    
    def test_airport_creation(self):
        """Test creating an Airport instance."""
        airport = Airport(
            iata_code="JFK",
            name="John F Kennedy International Airport",
            latitude=40.6413,
            longitude=-73.7781
        )
        
        assert airport.iata_code == "JFK"
        assert airport.name == "John F Kennedy International Airport"
        assert airport.latitude == 40.6413
        assert airport.longitude == -73.7781
    
    def test_airport_cache_key(self):
        """Test cache key generation for Airport."""
        airport = Airport(
            iata_code="LAX",
            name="Los Angeles International Airport",
            latitude=33.9425,
            longitude=-118.4081
        )
        
        expected_key = "weather_LAX_33.9425_-118.4081"
        assert airport.cache_key() == expected_key
    
    def test_airport_cache_key_uniqueness(self):
        """Test that different airports generate different cache keys."""
        airport1 = Airport("JFK", "JFK Airport", 40.6413, -73.7781)
        airport2 = Airport("LAX", "LAX Airport", 33.9425, -118.4081)
        
        assert airport1.cache_key() != airport2.cache_key()
    
    def test_airport_cache_key_same_coordinates(self):
        """Test cache key for airports with same coordinates but different codes."""
        airport1 = Airport("ABC", "Airport ABC", 40.0, -73.0)
        airport2 = Airport("XYZ", "Airport XYZ", 40.0, -73.0)
        
        # Should be different because IATA code is included
        assert airport1.cache_key() != airport2.cache_key()


class TestWeatherData:
    """Test cases for WeatherData model."""
    
    def test_weather_data_creation_success(self):
        """Test creating WeatherData with success status."""
        timestamp = datetime.now()
        weather = WeatherData(
            temperature=25.5,
            description="Clear sky",
            humidity=60,
            wind_speed=5.2,
            timestamp=timestamp,
            status=WeatherStatus.SUCCESS
        )
        
        assert weather.temperature == 25.5
        assert weather.description == "Clear sky"
        assert weather.humidity == 60
        assert weather.wind_speed == 5.2
        assert weather.timestamp == timestamp
        assert weather.status == WeatherStatus.SUCCESS
        assert weather.error_message is None
        assert weather.error_type is None
    
    def test_weather_data_creation_with_error(self):
        """Test creating WeatherData with error status."""
        timestamp = datetime.now()
        weather = WeatherData(
            temperature=0.0,
            description="",
            humidity=0,
            wind_speed=0.0,
            timestamp=timestamp,
            status=WeatherStatus.ERROR,
            error_message="API request failed",
            error_type=ErrorTypes.NETWORK_ERROR
        )
        
        assert weather.status == WeatherStatus.ERROR
        assert weather.error_message == "API request failed"
        assert weather.error_type == ErrorTypes.NETWORK_ERROR
    
    def test_weather_data_default_status(self):
        """Test that default status is SUCCESS."""
        weather = WeatherData(
            temperature=20.0,
            description="Cloudy",
            humidity=70,
            wind_speed=3.0,
            timestamp=datetime.now()
        )
        
        assert weather.status == WeatherStatus.SUCCESS


class TestFlightInfo:
    """Test cases for FlightInfo model."""
    
    def test_flight_info_creation(self):
        """Test creating FlightInfo instance."""
        flight = FlightInfo(
            flight_number="AA123",
            origin_airport_code="JFK",
            destination_airport_code="LAX",
            departure_date="2024-01-15",
            ticket_id="TKT001"
        )
        
        assert flight.flight_number == "AA123"
        assert flight.origin_airport_code == "JFK"
        assert flight.destination_airport_code == "LAX"
        assert flight.departure_date == "2024-01-15"
        assert flight.ticket_id == "TKT001"


class TestWeatherResult:
    """Test cases for WeatherResult model."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.airport = Airport("JFK", "JFK Airport", 40.6413, -73.7781)
        self.flight_info = FlightInfo("AA123", "JFK", "LAX", "2024-01-15", "TKT001")
        self.weather_data = WeatherData(
            temperature=25.0,
            description="Clear",
            humidity=60,
            wind_speed=5.0,
            timestamp=datetime.now()
        )
    
    def test_weather_result_creation_complete(self):
        """Test creating WeatherResult with all weather data."""
        result = WeatherResult(
            airport=self.airport,
            origin_weather=self.weather_data,
            destination_weather=self.weather_data,
            flight_info=self.flight_info
        )
        
        assert result.airport == self.airport
        assert result.origin_weather == self.weather_data
        assert result.destination_weather == self.weather_data
        assert result.flight_info == self.flight_info
    
    def test_weather_result_creation_partial(self):
        """Test creating WeatherResult with missing weather data."""
        result = WeatherResult(
            airport=self.airport,
            origin_weather=self.weather_data,
            destination_weather=None,
            flight_info=self.flight_info
        )
        
        assert result.airport == self.airport
        assert result.origin_weather == self.weather_data
        assert result.destination_weather is None
        assert result.flight_info == self.flight_info


class TestWeatherStatus:
    """Test cases for WeatherStatus enum."""
    
    def test_weather_status_values(self):
        """Test WeatherStatus enum values."""
        assert WeatherStatus.SUCCESS.value == "success"
        assert WeatherStatus.ERROR.value == "error"
        assert WeatherStatus.NOT_AVAILABLE.value == "not_available"
        assert WeatherStatus.CACHED.value == "cached"
    
    def test_weather_status_comparison(self):
        """Test WeatherStatus enum comparison."""
        assert WeatherStatus.SUCCESS == WeatherStatus.SUCCESS
        assert WeatherStatus.SUCCESS != WeatherStatus.ERROR


class TestErrorTypes:
    """Test cases for ErrorTypes enum."""
    
    def test_error_types_values(self):
        """Test ErrorTypes enum values."""
        assert ErrorTypes.NETWORK_ERROR.value == "network_error"
        assert ErrorTypes.API_ERROR.value == "api_error"
        assert ErrorTypes.TIMEOUT_ERROR.value == "timeout_error"
        assert ErrorTypes.RATE_LIMIT_ERROR.value == "rate_limit_error"
        assert ErrorTypes.AUTHENTICATION_ERROR.value == "authentication_error"
        assert ErrorTypes.INVALID_COORDINATES.value == "invalid_coordinates"
        assert ErrorTypes.UNKNOWN_ERROR.value == "unknown_error"
    
    def test_error_types_comparison(self):
        """Test ErrorTypes enum comparison."""
        assert ErrorTypes.NETWORK_ERROR == ErrorTypes.NETWORK_ERROR
        assert ErrorTypes.NETWORK_ERROR != ErrorTypes.API_ERROR


class TestModelIntegration:
    """Integration tests for model interactions."""
    
    def test_complete_workflow_models(self):
        """Test complete workflow using all models together."""
        # Create airport
        airport = Airport("JFK", "JFK Airport", 40.6413, -73.7781)
        
        # Create flight info
        flight = FlightInfo("AA123", "JFK", "LAX", "2024-01-15", "TKT001")
        
        # Create weather data
        weather = WeatherData(
            temperature=22.5,
            description="Partly cloudy",
            humidity=65,
            wind_speed=4.2,
            timestamp=datetime.now(),
            status=WeatherStatus.SUCCESS
        )
        
        # Create weather result
        result = WeatherResult(
            airport=airport,
            origin_weather=weather,
            destination_weather=weather,
            flight_info=flight
        )
        
        # Verify all components work together
        assert result.airport.cache_key().startswith("weather_JFK")
        assert result.origin_weather.status == WeatherStatus.SUCCESS
        assert result.flight_info.flight_number == "AA123"
    
    def test_error_scenario_models(self):
        """Test models in error scenarios."""
        airport = Airport("XXX", "Unknown Airport", 0.0, 0.0)
        flight = FlightInfo("XX000", "XXX", "YYY", "2024-01-15", "ERR001")
        
        error_weather = WeatherData(
            temperature=0.0,
            description="",
            humidity=0,
            wind_speed=0.0,
            timestamp=datetime.now(),
            status=WeatherStatus.ERROR,
            error_message="Invalid coordinates",
            error_type=ErrorTypes.INVALID_COORDINATES
        )
        
        result = WeatherResult(
            airport=airport,
            origin_weather=error_weather,
            destination_weather=None,
            flight_info=flight
        )
        
        assert result.origin_weather.status == WeatherStatus.ERROR
        assert result.origin_weather.error_type == ErrorTypes.INVALID_COORDINATES
        assert result.destination_weather is None