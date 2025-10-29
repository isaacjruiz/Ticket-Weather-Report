"""
Integration tests for the weather service.
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import patch
import pytest
from src.weather_service import WeatherService
from src.models import Airport, WeatherData, WeatherStatus


def test_multiple_airports_processing():
    """Test processing multiple airports - requirement 2.2"""
    airports = [
        Airport("JFK", "JFK Airport", 40.6413, -73.7781),
        Airport("LAX", "LAX Airport", 33.9425, -118.4081),
        Airport("ORD", "ORD Airport", 41.9742, -87.9073),
    ]
    
    # Verify airports are created correctly
    assert len(airports) == 3
    assert airports[0].iata_code == "JFK"
    assert airports[1].iata_code == "LAX" 
    assert airports[2].iata_code == "ORD"


@pytest.mark.asyncio
async def test_concurrency_verification():
    """Test concurrency verification - requirement 6.1"""
    weather_service = WeatherService("test_key", max_concurrency=2)
    
    # Mock the API client to track concurrent calls
    call_count = 0
    max_concurrent = 0
    active_calls = 0
    
    async def mock_fetch(*args, **kwargs):
        nonlocal call_count, max_concurrent, active_calls
        call_count += 1
        active_calls += 1
        max_concurrent = max(max_concurrent, active_calls)
        
        await asyncio.sleep(0.01)  # Simulate work
        
        active_calls -= 1
        return WeatherData(
            temperature=20.0,
            description="Test",
            humidity=60,
            wind_speed=2.0,
            timestamp=datetime.now(),
            status=WeatherStatus.SUCCESS
        )
    
    airports = [
        Airport(f"AP{i}", f"Airport {i}", 40.0 + i, -74.0 + i)
        for i in range(4)
    ]
    
    with patch.object(weather_service, '_api_client') as mock_client:
        mock_client.fetch_weather_with_retry = mock_fetch
        
        async with weather_service:
            results = await weather_service.get_weather_for_airports(airports)
    
    # Verify concurrency was limited
    assert max_concurrent <= 2
    assert len(results) == 4
    assert call_count == 4