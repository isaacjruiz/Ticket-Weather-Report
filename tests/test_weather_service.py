"""
Tests for the weather service HTTP client.

This module contains comprehensive tests for the WeatherAPIClient class,
including mocking of API responses and testing various error scenarios.
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aioresponses import aioresponses

from src.weather_service import WeatherAPIClient, WeatherService
from src.models import WeatherData, WeatherStatus, ErrorTypes, Airport


class TestWeatherAPIClient:
    """Test suite for WeatherAPIClient class."""
    
    @pytest.fixture
    def api_client(self):
        """Create a WeatherAPIClient instance for testing."""
        return WeatherAPIClient(api_key="test_api_key", timeout=30)
    
    @pytest.fixture
    def sample_weather_response(self):
        """Sample successful weather API response."""
        return {
            "main": {
                "temp": 22.5,
                "humidity": 65
            },
            "weather": [
                {
                    "description": "clear sky"
                }
            ],
            "wind": {
                "speed": 3.2
            }
        }
    
    @pytest.fixture
    def invalid_weather_response(self):
        """Sample invalid weather API response missing required fields."""
        return {
            "cod": 200,
            "message": "success"
            # Missing main, weather, and wind sections
        }

    @pytest.mark.asyncio
    async def test_successful_weather_fetch(self, api_client, sample_weather_response):
        """Test successful weather data fetching with mocked API response."""
        with aioresponses() as m:
            # Mock successful API response using regex pattern to match any parameters
            import re
            m.get(
                re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*'),
                payload=sample_weather_response,
                status=200
            )
            
            async with api_client:
                result = await api_client.fetch_weather(40.7128, -74.0060)
                
            assert result == sample_weather_response
    
    @pytest.mark.asyncio
    async def test_fetch_weather_with_retry_success(self, api_client, sample_weather_response):
        """Test successful weather fetch with retry wrapper."""
        with aioresponses() as m:
            import re
            m.get(
                re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*'),
                payload=sample_weather_response,
                status=200
            )
            
            async with api_client:
                result = await api_client.fetch_weather_with_retry(40.7128, -74.0060)
                
            assert isinstance(result, WeatherData)
            assert result.status == WeatherStatus.SUCCESS
            assert result.temperature == 22.5
            assert result.description == "Clear Sky"
            assert result.humidity == 65
            assert result.wind_speed == 3.2
    
    @pytest.mark.asyncio
    async def test_invalid_coordinates_validation(self, api_client):
        """Test validation of coordinate ranges."""
        async with api_client:
            # Test invalid latitude (too high)
            with pytest.raises(ValueError, match="Invalid latitude"):
                await api_client.fetch_weather(91.0, 0.0)
            
            # Test invalid latitude (too low)
            with pytest.raises(ValueError, match="Invalid latitude"):
                await api_client.fetch_weather(-91.0, 0.0)
            
            # Test invalid longitude (too high)
            with pytest.raises(ValueError, match="Invalid longitude"):
                await api_client.fetch_weather(0.0, 181.0)
            
            # Test invalid longitude (too low)
            with pytest.raises(ValueError, match="Invalid longitude"):
                await api_client.fetch_weather(0.0, -181.0)
    
    @pytest.mark.asyncio
    async def test_authentication_error_401(self, api_client):
        """Test handling of 401 authentication errors."""
        with aioresponses() as m:
            import re
            m.get(
                re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*'),
                status=401,
                payload={"cod": 401, "message": "Invalid API key"}
            )
            
            async with api_client:
                with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                    await api_client.fetch_weather(40.7128, -74.0060)
                
                assert exc_info.value.status == 401
                assert "Invalid API key" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_429(self, api_client):
        """Test handling of 429 rate limit errors."""
        with aioresponses() as m:
            import re
            m.get(
                re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*'),
                status=429,
                payload={"cod": 429, "message": "Rate limit exceeded"}
            )
            
            async with api_client:
                with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                    await api_client.fetch_weather(40.7128, -74.0060)
                
                assert exc_info.value.status == 429
                assert "API rate limit exceeded" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_server_error_500(self, api_client):
        """Test handling of 500 server errors."""
        with aioresponses() as m:
            import re
            m.get(
                re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*'),
                status=500,
                payload={"cod": 500, "message": "Internal server error"}
            )
            
            async with api_client:
                with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                    await api_client.fetch_weather(40.7128, -74.0060)
                
                assert exc_info.value.status == 500
    
    @pytest.mark.asyncio
    async def test_other_http_errors(self, api_client):
        """Test handling of other HTTP error codes."""
        with aioresponses() as m:
            import re
            m.get(
                re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*'),
                status=404,
                payload={"cod": 404, "message": "Not found"}
            )
            
            async with api_client:
                with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                    await api_client.fetch_weather(40.7128, -74.0060)
                
                assert exc_info.value.status == 404
    
    @pytest.mark.asyncio
    async def test_timeout_error(self, api_client):
        """Test handling of timeout errors."""
        with aioresponses() as m:
            import re
            m.get(
                re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*'),
                exception=asyncio.TimeoutError("Request timeout")
            )
            
            async with api_client:
                with pytest.raises(asyncio.TimeoutError):
                    await api_client.fetch_weather(40.7128, -74.0060)
    
    @pytest.mark.asyncio
    async def test_network_error(self, api_client):
        """Test handling of network connection errors."""
        with aioresponses() as m:
            import re
            m.get(
                re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*'),
                exception=aiohttp.ClientConnectorError(
                    connection_key=None, 
                    os_error=OSError("Network unreachable")
                )
            )
            
            async with api_client:
                with pytest.raises(aiohttp.ClientConnectorError):
                    await api_client.fetch_weather(40.7128, -74.0060)
    
    @pytest.mark.asyncio
    async def test_retry_on_retryable_errors(self, api_client, sample_weather_response):
        """Test that retryable errors trigger retry logic."""
        # For this test, we'll test the retry mechanism by mocking the fetch_weather method directly
        # to avoid the complexity of setting up multiple aioresponses
        with patch.object(api_client, 'fetch_weather') as mock_fetch:
            # First two calls raise server error, third succeeds
            mock_fetch.side_effect = [
                aiohttp.ClientResponseError(None, None, status=500, message="Server error"),
                aiohttp.ClientResponseError(None, None, status=500, message="Server error"),
                sample_weather_response
            ]
            
            async with api_client:
                # Mock the retry mechanism to avoid actual delays
                with patch('src.weather_service.wait_exponential') as mock_wait:
                    mock_wait.return_value = lambda retry_state: 0  # No delay
                    
                    result = await api_client.fetch_weather_with_retry(40.7128, -74.0060)
                    
                assert isinstance(result, WeatherData)
                assert result.status == WeatherStatus.SUCCESS
                assert mock_fetch.call_count == 3  # Verify it retried
    
    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self, api_client):
        """Test that authentication errors don't trigger retries."""
        with aioresponses() as m:
            import re
            m.get(
                re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*'),
                status=401,
                payload={"cod": 401, "message": "Invalid API key"}
            )
            
            async with api_client:
                result = await api_client.fetch_weather_with_retry(40.7128, -74.0060)
                
            assert isinstance(result, WeatherData)
            assert result.status == WeatherStatus.NOT_AVAILABLE
            assert result.error_type == ErrorTypes.AUTHENTICATION_ERROR
            assert "HTTP 401" in result.error_message
    
    @pytest.mark.asyncio
    async def test_invalid_response_parsing(self, api_client, invalid_weather_response):
        """Test handling of invalid API response format."""
        with aioresponses() as m:
            import re
            m.get(
                re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*'),
                payload=invalid_weather_response,
                status=200
            )
            
            async with api_client:
                result = await api_client.fetch_weather_with_retry(40.7128, -74.0060)
                
            assert isinstance(result, WeatherData)
            assert result.status == WeatherStatus.NOT_AVAILABLE
            assert result.error_type == ErrorTypes.INVALID_COORDINATES
            assert "Invalid API response format" in result.error_message
    
    @pytest.mark.asyncio
    async def test_missing_optional_fields(self, api_client):
        """Test parsing response with missing optional fields."""
        response_without_wind_speed = {
            "main": {
                "temp": 20.0,
                "humidity": 70
            },
            "weather": [
                {
                    "description": "cloudy"
                }
            ],
            "wind": {}  # Missing speed field
        }
        
        with aioresponses() as m:
            import re
            m.get(
                re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*'),
                payload=response_without_wind_speed,
                status=200
            )
            
            async with api_client:
                result = await api_client.fetch_weather_with_retry(40.7128, -74.0060)
                
            assert isinstance(result, WeatherData)
            assert result.status == WeatherStatus.SUCCESS
            assert result.wind_speed == 0.0  # Default value for missing wind speed
    
    def test_classify_http_error(self, api_client):
        """Test HTTP error classification logic."""
        # Test authentication error (non-retryable)
        error_type, should_retry = api_client._classify_http_error(401)
        assert error_type == ErrorTypes.AUTHENTICATION_ERROR
        assert should_retry is False
        
        # Test rate limit error (retryable)
        error_type, should_retry = api_client._classify_http_error(429)
        assert error_type == ErrorTypes.RATE_LIMIT_ERROR
        assert should_retry is True
        
        # Test server error (retryable)
        error_type, should_retry = api_client._classify_http_error(500)
        assert error_type == ErrorTypes.API_ERROR
        assert should_retry is True
        
        # Test bad request (non-retryable)
        error_type, should_retry = api_client._classify_http_error(400)
        assert error_type == ErrorTypes.INVALID_COORDINATES
        assert should_retry is False
        
        # Test other error (retryable by default)
        error_type, should_retry = api_client._classify_http_error(418)
        assert error_type == ErrorTypes.API_ERROR
        assert should_retry is True
    
    def test_parse_weather_response_success(self, api_client, sample_weather_response):
        """Test successful parsing of weather response."""
        result = api_client._parse_weather_response(sample_weather_response)
        
        assert isinstance(result, WeatherData)
        assert result.temperature == 22.5
        assert result.description == "Clear Sky"
        assert result.humidity == 65
        assert result.wind_speed == 3.2
        assert result.status == WeatherStatus.SUCCESS
        assert result.error_message is None
    
    def test_parse_weather_response_missing_main(self, api_client):
        """Test parsing response with missing main section."""
        invalid_response = {
            "weather": [{"description": "sunny"}],
            "wind": {"speed": 5.0}
        }
        
        with pytest.raises(ValueError, match="Missing 'main' section"):
            api_client._parse_weather_response(invalid_response)
    
    def test_parse_weather_response_missing_weather(self, api_client):
        """Test parsing response with missing weather section."""
        invalid_response = {
            "main": {"temp": 20.0, "humidity": 60},
            "wind": {"speed": 5.0}
        }
        
        with pytest.raises(ValueError, match="Missing 'weather' section"):
            api_client._parse_weather_response(invalid_response)
    
    def test_parse_weather_response_missing_wind(self, api_client):
        """Test parsing response with missing wind section."""
        invalid_response = {
            "main": {"temp": 20.0, "humidity": 60},
            "weather": [{"description": "sunny"}]
        }
        
        with pytest.raises(ValueError, match="Missing 'wind' section"):
            api_client._parse_weather_response(invalid_response)
    
    def test_parse_weather_response_missing_temperature(self, api_client):
        """Test parsing response with missing temperature."""
        invalid_response = {
            "main": {"humidity": 60},
            "weather": [{"description": "sunny"}],
            "wind": {"speed": 5.0}
        }
        
        with pytest.raises(ValueError, match="Missing temperature"):
            api_client._parse_weather_response(invalid_response)
    
    @pytest.mark.asyncio
    async def test_session_management(self, api_client):
        """Test proper session creation and cleanup."""
        # Session should be None initially
        assert api_client._session is None
        
        async with api_client:
            # Session should be created
            assert api_client._session is not None
            assert not api_client._session.closed
        
        # Session should be closed after context exit
        assert api_client._session.closed
    
    @pytest.mark.asyncio
    async def test_session_reuse(self, api_client):
        """Test that session is reused across multiple requests."""
        with aioresponses() as m:
            import re
            m.get(
                re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*'),
                payload={"main": {"temp": 20}, "weather": [{"description": "test"}], "wind": {"speed": 1}},
                status=200,
                repeat=True
            )
            
            async with api_client:
                session1 = api_client._session
                await api_client.fetch_weather(40.0, -74.0)
                
                session2 = api_client._session
                await api_client.fetch_weather(41.0, -75.0)
                
                # Same session should be reused
                assert session1 is session2
    
    @pytest.mark.asyncio
    async def test_request_parameters(self, api_client):
        """Test that correct parameters are sent in API requests."""
        with aioresponses() as m:
            import re
            url_pattern = re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*')
            m.get(
                url_pattern,
                payload={"main": {"temp": 20}, "weather": [{"description": "test"}], "wind": {"speed": 1}},
                status=200
            )
            
            async with api_client:
                await api_client.fetch_weather(40.7128, -74.0060)
            
            # Verify the request was made with correct parameters
            assert len(m.requests) == 1
            # Get the first (and only) request made
            request_key = list(m.requests.keys())[0]
            request = m.requests[request_key][0]
            
            # Check query parameters in the request
            assert 'lat=40.7128' in str(request.kwargs.get('params', {})) or 'lat=40.7128' in str(request_key[1])
            assert 'lon=-74.006' in str(request.kwargs.get('params', {})) or 'lon=-74.006' in str(request_key[1])
            assert 'appid=test_api_key' in str(request.kwargs.get('params', {})) or 'appid=test_api_key' in str(request_key[1])
            assert 'units=metric' in str(request.kwargs.get('params', {})) or 'units=metric' in str(request_key[1])


class TestWeatherService:
    """Test suite for WeatherService class."""
    
    @pytest.fixture
    def weather_service(self):
        """Create a WeatherService instance for testing."""
        return WeatherService(api_key="test_api_key", timeout=30, max_concurrency=5)
    
    @pytest.fixture
    def sample_airports(self):
        """Sample airports for testing."""
        return [
            Airport(iata_code="JFK", name="John F. Kennedy International Airport", 
                   latitude=40.6413, longitude=-73.7781),
            Airport(iata_code="LAX", name="Los Angeles International Airport", 
                   latitude=33.9425, longitude=-118.4081),
            Airport(iata_code="ORD", name="O'Hare International Airport", 
                   latitude=41.9742, longitude=-87.9073),
        ]
    
    @pytest.fixture
    def sample_weather_data(self):
        """Sample weather data for testing."""
        return WeatherData(
            temperature=22.5,
            description="Clear Sky",
            humidity=65,
            wind_speed=3.2,
            timestamp=datetime.now(),
            status=WeatherStatus.SUCCESS
        )

    @pytest.mark.asyncio
    async def test_get_weather_for_airports_success(self, weather_service, sample_airports, sample_weather_data):
        """Test successful weather retrieval for multiple airports."""
        # Mock the _get_weather_for_single_airport method to return sample data
        with patch.object(weather_service, '_get_weather_for_single_airport') as mock_get_weather:
            mock_get_weather.return_value = sample_weather_data
            
            async with weather_service:
                results = await weather_service.get_weather_for_airports(sample_airports)
            
            # Verify results
            assert len(results) == 3
            assert "JFK" in results
            assert "LAX" in results
            assert "ORD" in results
            
            # Verify all results are successful
            for airport_code, weather_data in results.items():
                assert isinstance(weather_data, WeatherData)
                assert weather_data.status == WeatherStatus.SUCCESS
                assert weather_data.temperature == 22.5
            
            # Verify the method was called for each airport
            assert mock_get_weather.call_count == 3

    @pytest.mark.asyncio
    async def test_get_weather_for_airports_empty_list(self, weather_service):
        """Test weather retrieval with empty airport list."""
        async with weather_service:
            results = await weather_service.get_weather_for_airports([])
        
        assert results == {}

    @pytest.mark.asyncio
    async def test_get_weather_for_airports_with_errors(self, weather_service, sample_airports):
        """Test weather retrieval when some airports fail."""
        error_weather_data = WeatherData(
            temperature=0.0,
            description="Clima no disponible",
            humidity=0,
            wind_speed=0.0,
            timestamp=datetime.now(),
            status=WeatherStatus.NOT_AVAILABLE,
            error_message="API error",
            error_type=ErrorTypes.API_ERROR
        )
        
        success_weather_data = WeatherData(
            temperature=20.0,
            description="Sunny",
            humidity=50,
            wind_speed=2.0,
            timestamp=datetime.now(),
            status=WeatherStatus.SUCCESS
        )
        
        # Mock to return success for first airport, error for others
        with patch.object(weather_service, '_get_weather_for_single_airport') as mock_get_weather:
            mock_get_weather.side_effect = [success_weather_data, error_weather_data, error_weather_data]
            
            async with weather_service:
                results = await weather_service.get_weather_for_airports(sample_airports)
            
            # Verify all airports are in results
            assert len(results) == 3
            
            # Verify first airport succeeded
            assert results["JFK"].status == WeatherStatus.SUCCESS
            assert results["JFK"].temperature == 20.0
            
            # Verify other airports failed
            assert results["LAX"].status == WeatherStatus.NOT_AVAILABLE
            assert results["ORD"].status == WeatherStatus.NOT_AVAILABLE

    @pytest.mark.asyncio
    async def test_get_weather_for_single_airport_with_cache_hit(self, weather_service, sample_airports, sample_weather_data):
        """Test that cached data is returned when available."""
        airport = sample_airports[0]
        
        # Pre-populate cache
        cache_key = airport.cache_key()
        weather_service.cache.set(cache_key, sample_weather_data)
        
        async with weather_service:
            result = await weather_service._get_weather_for_single_airport(airport)
        
        # Should return cached data (same data, just verify key fields)
        assert result.temperature == sample_weather_data.temperature
        assert result.description == sample_weather_data.description
        assert result.humidity == sample_weather_data.humidity
        assert result.wind_speed == sample_weather_data.wind_speed

    @pytest.mark.asyncio
    async def test_get_weather_for_single_airport_cache_miss(self, weather_service, sample_airports, sample_weather_data):
        """Test weather retrieval when cache is empty."""
        airport = sample_airports[0]
        
        # Mock the WeatherAPIClient class entirely
        with patch('src.weather_service.WeatherAPIClient') as mock_client_class:
            # Create a mock instance
            mock_client_instance = AsyncMock()
            mock_client_instance.fetch_weather_with_retry = AsyncMock(return_value=sample_weather_data)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            
            # Make the class constructor return our mock instance
            mock_client_class.return_value = mock_client_instance
            
            async with weather_service:
                result = await weather_service._get_weather_for_single_airport(airport)
            
            # Verify API was called
            mock_client_instance.fetch_weather_with_retry.assert_called_once_with(
                airport.latitude, airport.longitude
            )
            
            # Verify result has correct data
            assert result.temperature == sample_weather_data.temperature
            assert result.description == sample_weather_data.description
            assert result.status == WeatherStatus.SUCCESS
            
            # Verify data was cached
            cached_data = weather_service.cache.get(airport.cache_key())
            assert cached_data is not None
            assert cached_data.temperature == sample_weather_data.temperature

    @pytest.mark.asyncio
    async def test_get_weather_by_coordinates(self, weather_service, sample_weather_data):
        """Test weather retrieval by coordinates."""
        lat, lon = 40.7128, -74.0060
        
        # Mock the _get_weather_for_single_airport method instead
        with patch.object(weather_service, '_get_weather_for_single_airport') as mock_get_weather:
            mock_get_weather.return_value = sample_weather_data
            
            async with weather_service:
                result = await weather_service.get_weather_by_coordinates(lat, lon)
            
            # Verify the method was called
            mock_get_weather.assert_called_once()
            
            # Verify result
            assert result == sample_weather_data

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, sample_airports):
        """Test that concurrency is properly limited by semaphore."""
        # Create service with low concurrency limit for testing
        weather_service = WeatherService(api_key="test_key", max_concurrency=2)
        
        # Track concurrent calls
        concurrent_calls = 0
        max_concurrent_calls = 0
        
        async def mock_api_call(*args, **kwargs):
            nonlocal concurrent_calls, max_concurrent_calls
            concurrent_calls += 1
            max_concurrent_calls = max(max_concurrent_calls, concurrent_calls)
            
            # Simulate some processing time
            await asyncio.sleep(0.1)
            
            concurrent_calls -= 1
            return WeatherData(
                temperature=20.0,
                description="Test",
                humidity=50,
                wind_speed=1.0,
                timestamp=datetime.now(),
                status=WeatherStatus.SUCCESS
            )
        
        # Mock the API client method
        with patch.object(weather_service, '_api_client') as mock_client:
            mock_client.fetch_weather_with_retry = mock_api_call
            
            async with weather_service:
                # Use more airports than concurrency limit
                airports = sample_airports * 3  # 9 airports total
                await weather_service.get_weather_for_airports(airports)
        
        # Verify concurrency was limited
        assert max_concurrent_calls <= 2

    @pytest.mark.asyncio
    async def test_exception_handling_in_concurrent_processing(self, weather_service, sample_airports):
        """Test that exceptions in individual airport processing are handled gracefully."""
        # Mock to raise exception for one airport
        with patch.object(weather_service, '_get_weather_for_single_airport') as mock_get_weather:
            def side_effect(airport):
                if airport.iata_code == "LAX":
                    raise Exception("Unexpected error")
                return WeatherData(
                    temperature=20.0,
                    description="Success",
                    humidity=50,
                    wind_speed=1.0,
                    timestamp=datetime.now(),
                    status=WeatherStatus.SUCCESS
                )
            
            mock_get_weather.side_effect = side_effect
            
            async with weather_service:
                results = await weather_service.get_weather_for_airports(sample_airports)
            
            # Verify all airports are in results
            assert len(results) == 3
            
            # Verify successful airports
            assert results["JFK"].status == WeatherStatus.SUCCESS
            assert results["ORD"].status == WeatherStatus.SUCCESS
            
            # Verify failed airport has error status
            assert results["LAX"].status == WeatherStatus.NOT_AVAILABLE
            assert "Unexpected service error" in results["LAX"].error_message

    def test_get_cache_stats(self, weather_service):
        """Test cache statistics retrieval."""
        stats = weather_service.get_cache_stats()
        
        # Should return a dictionary with statistics
        assert isinstance(stats, dict)
        assert 'hit_rate_percent' in stats

    def test_clear_cache(self, weather_service, sample_airports, sample_weather_data):
        """Test cache clearing functionality."""
        # Add some data to cache
        airport = sample_airports[0]
        cache_key = airport.cache_key()
        weather_service.cache.set(cache_key, sample_weather_data)
        
        # Verify data is in cache
        assert weather_service.cache.get(cache_key) is not None
        
        # Clear cache
        weather_service.clear_cache()
        
        # Verify cache is empty
        assert weather_service.cache.get(cache_key) is None

    @pytest.mark.asyncio
    async def test_graceful_error_handling_with_mixed_results(self, weather_service, sample_airports):
        """Test graceful error handling with mixed success and failure results."""
        success_data = WeatherData(
            temperature=22.0,
            description="Sunny",
            humidity=60,
            wind_speed=2.5,
            timestamp=datetime.now(),
            status=WeatherStatus.SUCCESS
        )
        
        error_data = WeatherData(
            temperature=0.0,
            description="Clima no disponible",
            humidity=0,
            wind_speed=0.0,
            timestamp=datetime.now(),
            status=WeatherStatus.NOT_AVAILABLE,
            error_message="API error",
            error_type=ErrorTypes.API_ERROR
        )
        
        # Mock to return mixed results
        with patch.object(weather_service, '_get_weather_for_single_airport_with_graceful_handling') as mock_graceful:
            mock_graceful.side_effect = [success_data, error_data, success_data]
            
            async with weather_service:
                results = await weather_service.get_weather_for_airports(sample_airports)
            
            # Verify all airports processed
            assert len(results) == 3
            
            # Verify statistics tracking
            stats = weather_service.get_processing_statistics()
            assert stats['airports_processed'] == 3
            assert stats['airports_with_weather'] == 2
            assert stats['airports_without_weather'] == 1
            assert stats['success_rate_percent'] == 66.67
            assert stats['failure_rate_percent'] == 33.33

    def test_create_unavailable_weather_data(self, weather_service):
        """Test creation of unavailable weather data with Spanish message."""
        error_msg = "Test error message"
        error_type = ErrorTypes.NETWORK_ERROR
        
        result = weather_service._create_unavailable_weather_data(error_msg, error_type)
        
        assert isinstance(result, WeatherData)
        assert result.temperature == 0.0
        assert result.description == "Clima no disponible"
        assert result.humidity == 0
        assert result.wind_speed == 0.0
        assert result.status == WeatherStatus.NOT_AVAILABLE
        assert result.error_message == error_msg
        assert result.error_type == error_type

    def test_update_error_statistics(self, weather_service):
        """Test error statistics tracking for different error types."""
        # Test network error
        weather_service._update_error_statistics(ErrorTypes.NETWORK_ERROR)
        assert weather_service._stats['network_errors'] == 1
        
        # Test API error
        weather_service._update_error_statistics(ErrorTypes.API_ERROR)
        assert weather_service._stats['api_errors'] == 1
        
        # Test timeout error
        weather_service._update_error_statistics(ErrorTypes.TIMEOUT_ERROR)
        assert weather_service._stats['timeout_errors'] == 1
        
        # Test rate limit error
        weather_service._update_error_statistics(ErrorTypes.RATE_LIMIT_ERROR)
        assert weather_service._stats['rate_limit_errors'] == 1
        
        # Test authentication error
        weather_service._update_error_statistics(ErrorTypes.AUTHENTICATION_ERROR)
        assert weather_service._stats['authentication_errors'] == 1
        
        # Test invalid coordinates error
        weather_service._update_error_statistics(ErrorTypes.INVALID_COORDINATES)
        assert weather_service._stats['invalid_coordinate_errors'] == 1
        
        # Test unknown error
        weather_service._update_error_statistics(ErrorTypes.UNKNOWN_ERROR)
        assert weather_service._stats['unknown_errors'] == 1
        
        # Test None error type (should count as unknown)
        weather_service._update_error_statistics(None)
        assert weather_service._stats['unknown_errors'] == 2

    def test_update_statistics_for_result(self, weather_service):
        """Test statistics update based on weather data results."""
        # Test successful result
        success_data = WeatherData(
            temperature=20.0,
            description="Sunny",
            humidity=50,
            wind_speed=1.0,
            timestamp=datetime.now(),
            status=WeatherStatus.SUCCESS
        )
        
        weather_service._update_statistics_for_result(success_data)
        assert weather_service._stats['airports_with_weather'] == 1
        assert weather_service._stats['airports_without_weather'] == 0
        
        # Test cached result
        cached_data = WeatherData(
            temperature=25.0,
            description="Cloudy",
            humidity=70,
            wind_speed=2.0,
            timestamp=datetime.now(),
            status=WeatherStatus.CACHED
        )
        
        weather_service._update_statistics_for_result(cached_data)
        assert weather_service._stats['airports_with_weather'] == 2
        assert weather_service._stats['airports_without_weather'] == 0
        
        # Test error result
        error_data = WeatherData(
            temperature=0.0,
            description="Clima no disponible",
            humidity=0,
            wind_speed=0.0,
            timestamp=datetime.now(),
            status=WeatherStatus.NOT_AVAILABLE,
            error_message="Test error",
            error_type=ErrorTypes.API_ERROR
        )
        
        weather_service._update_statistics_for_result(error_data)
        assert weather_service._stats['airports_with_weather'] == 2
        assert weather_service._stats['airports_without_weather'] == 1
        assert weather_service._stats['api_errors'] == 1

    def test_get_processing_statistics(self, weather_service):
        """Test comprehensive processing statistics retrieval."""
        # Set up some test statistics
        weather_service._stats.update({
            'airports_processed': 10,
            'airports_with_weather': 8,
            'airports_without_weather': 2,
            'total_requests': 15,
            'cached_requests': 5,
            'successful_requests': 8,
            'failed_requests': 2
        })
        
        stats = weather_service.get_processing_statistics()
        
        # Verify basic statistics
        assert stats['airports_processed'] == 10
        assert stats['airports_with_weather'] == 8
        assert stats['airports_without_weather'] == 2
        
        # Verify calculated percentages
        assert stats['success_rate_percent'] == 80.0
        assert stats['failure_rate_percent'] == 20.0
        assert stats['cache_hit_rate_percent'] == 33.33

    @pytest.mark.asyncio
    async def test_graceful_handling_with_exception(self, weather_service, sample_airports):
        """Test graceful error handling when unexpected exceptions occur."""
        airport = sample_airports[0]
        
        # Mock to raise an unexpected exception
        with patch.object(weather_service, '_get_weather_for_single_airport') as mock_get_weather:
            mock_get_weather.side_effect = Exception("Unexpected error")
            
            result = await weather_service._get_weather_for_single_airport_with_graceful_handling(airport)
            
            # Should return unavailable weather data instead of raising exception
            assert isinstance(result, WeatherData)
            assert result.status == WeatherStatus.NOT_AVAILABLE
            assert result.description == "Clima no disponible"
            assert "Unexpected service error" in result.error_message
            assert result.error_type == ErrorTypes.UNKNOWN_ERROR

    @pytest.mark.asyncio
    async def test_spanish_error_messages_in_api_client(self):
        """Test that API client returns Spanish error messages for unavailable weather."""
        api_client = WeatherAPIClient(api_key="test_key")
        
        # Test authentication error
        with aioresponses() as m:
            import re
            m.get(
                re.compile(r'https://api\.openweathermap\.org/data/2\.5/weather.*'),
                status=401,
                payload={"cod": 401, "message": "Invalid API key"}
            )
            
            async with api_client:
                result = await api_client.fetch_weather_with_retry(40.0, -74.0)
                
            assert result.description == "Clima no disponible"
            assert result.status == WeatherStatus.NOT_AVAILABLE
            assert result.error_type == ErrorTypes.AUTHENTICATION_ERROR

    @pytest.mark.asyncio
    async def test_context_manager_functionality(self, weather_service):
        """Test that WeatherService works properly as async context manager."""
        # Test entering and exiting context
        async with weather_service as service:
            assert service is weather_service
            assert service._api_client is not None
        
        # After exiting, the API client should be cleaned up
        # (We can't easily test this without accessing private methods)

    @pytest.mark.asyncio
    async def test_api_client_error_handling(self, weather_service, sample_airports):
        """Test handling of API client errors during weather retrieval."""
        airport = sample_airports[0]
        
        # Mock API client to raise an exception
        with patch.object(weather_service, '_api_client') as mock_client:
            mock_client.fetch_weather_with_retry.side_effect = Exception("API client error")
            
            async with weather_service:
                result = await weather_service._get_weather_for_single_airport(airport)
            
            # Should return error weather data
            assert result.status == WeatherStatus.NOT_AVAILABLE
            assert "Service error" in result.error_message
            assert result.error_type == ErrorTypes.UNKNOWN_ERROR