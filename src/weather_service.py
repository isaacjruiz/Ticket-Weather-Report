"""
Weather service module for fetching weather data from OpenWeatherMap API.

This module provides the WeatherAPIClient class for making asynchronous HTTP requests
to the OpenWeatherMap API with proper connection pooling, timeouts, and error handling.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    from .models import WeatherData, WeatherStatus, ErrorTypes, Airport
    from .cache_manager import WeatherCache, SQLiteWeatherCache
except ImportError:
    from models import WeatherData, WeatherStatus, ErrorTypes, Airport
    from cache_manager import WeatherCache, SQLiteWeatherCache


logger = logging.getLogger(__name__)


class WeatherAPIClient:
    """
    Asynchronous HTTP client for OpenWeatherMap API.
    
    Provides methods to fetch weather data using coordinates with proper
    connection pooling, timeouts, and error handling.
    """
    
    def __init__(self, api_key: str, timeout: int = 30):
        """
        Initialize the weather API client.
        
        Args:
            api_key: OpenWeatherMap API key
            timeout: Request timeout in seconds (default: 30)
        """
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._create_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
        
    async def _create_session(self):
        """Create aiohttp session with connection pooling and proper configuration."""
        if self._session is None or self._session.closed:
            # Configure connection pooling
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=10,  # Max connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            # Configure timeout
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            # Set appropriate headers
            headers = {
                'User-Agent': 'WeatherReportSystem/1.0',
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate'
            }
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers,
                raise_for_status=False  # We'll handle status codes manually
            )
            
    async def _close_session(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            
    async def fetch_weather(self, lat: float, lon: float) -> Dict:
        """
        Fetch weather data for given coordinates.
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            
        Returns:
            Dict containing weather data from API
            
        Raises:
            aiohttp.ClientError: For HTTP-related errors
            asyncio.TimeoutError: For timeout errors
            ValueError: For invalid coordinates or API responses
        """
        if not (-90 <= lat <= 90):
            raise ValueError(f"Invalid latitude: {lat}. Must be between -90 and 90.")
        if not (-180 <= lon <= 180):
            raise ValueError(f"Invalid longitude: {lon}. Must be between -180 and 180.")
            
        await self._create_session()
        
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'units': 'metric'  # Use Celsius for temperature
        }
        
        logger.debug(f"Fetching weather for coordinates ({lat}, {lon})")
        
        async with self._session.get(self.base_url, params=params) as response:
            # Handle different HTTP status codes
            if response.status == 200:
                data = await response.json()
                logger.debug(f"Successfully fetched weather data for ({lat}, {lon})")
                return data
            elif response.status == 401:
                error_msg = "Invalid API key"
                logger.error(f"Authentication error: {error_msg}")
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=401,
                    message=error_msg
                )
            elif response.status == 429:
                error_msg = "API rate limit exceeded"
                logger.warning(f"Rate limit error: {error_msg}")
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=429,
                    message=error_msg
                )
            elif response.status >= 500:
                error_msg = f"Server error: {response.status}"
                logger.error(f"Server error for ({lat}, {lon}): {error_msg}")
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=error_msg
                )
            else:
                error_msg = f"HTTP {response.status}: {response.reason}"
                logger.error(f"Unexpected HTTP status for ({lat}, {lon}): {error_msg}")
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=error_msg
                )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((
            aiohttp.ClientError,
            asyncio.TimeoutError,
            aiohttp.ServerTimeoutError
        ))
    )
    async def fetch_weather_with_retry(self, lat: float, lon: float) -> WeatherData:
        """
        Fetch weather data with automatic retry logic.
        
        This method wraps fetch_weather with tenacity retry logic to handle
        transient network errors, timeouts, and server errors with exponential backoff.
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            
        Returns:
            WeatherData object with weather information or error details
        """
        try:
            logger.info(f"Attempting to fetch weather for coordinates ({lat}, {lon})")
            raw_data = await self.fetch_weather(lat, lon)
            weather_data = self._parse_weather_response(raw_data)
            logger.info(f"Successfully retrieved weather for ({lat}, {lon})")
            return weather_data
            
        except aiohttp.ClientResponseError as e:
            error_type, should_retry = self._classify_http_error(e.status)
            error_msg = f"HTTP {e.status}: {e.message}"
            
            logger.error(f"HTTP error for ({lat}, {lon}): {error_msg}")
            
            if should_retry:
                logger.warning(f"Retrying request for ({lat}, {lon}) due to {error_type.value}")
                raise  # Let tenacity handle the retry
            else:
                # Don't retry for certain errors (auth, invalid coords, etc.)
                logger.error(f"Non-retryable error for ({lat}, {lon}): {error_msg}")
                return WeatherData(
                    temperature=0.0,
                    description="Clima no disponible",
                    humidity=0,
                    wind_speed=0.0,
                    timestamp=datetime.now(),
                    status=WeatherStatus.NOT_AVAILABLE,
                    error_message=error_msg,
                    error_type=error_type
                )
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            error_msg = f"Network/timeout error: {str(e)}"
            logger.error(f"Network error for ({lat}, {lon}): {error_msg}")
            
            # These errors are retryable
            raise
            
        except ValueError as e:
            error_msg = f"Invalid data: {str(e)}"
            logger.error(f"Data validation error for ({lat}, {lon}): {error_msg}")
            
            # Don't retry validation errors
            return WeatherData(
                temperature=0.0,
                description="Clima no disponible",
                humidity=0,
                wind_speed=0.0,
                timestamp=datetime.now(),
                status=WeatherStatus.NOT_AVAILABLE,
                error_message=error_msg,
                error_type=ErrorTypes.INVALID_COORDINATES
            )
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error for ({lat}, {lon}): {error_msg}")
            
            return WeatherData(
                temperature=0.0,
                description="Clima no disponible",
                humidity=0,
                wind_speed=0.0,
                timestamp=datetime.now(),
                status=WeatherStatus.NOT_AVAILABLE,
                error_message=error_msg,
                error_type=ErrorTypes.UNKNOWN_ERROR
            )
    
    def _classify_http_error(self, status_code: int) -> tuple[ErrorTypes, bool]:
        """
        Classify HTTP errors and determine if they should be retried.
        
        Args:
            status_code: HTTP status code
            
        Returns:
            Tuple of (ErrorType, should_retry)
        """
        if status_code == 401:
            return ErrorTypes.AUTHENTICATION_ERROR, False
        elif status_code == 429:
            return ErrorTypes.RATE_LIMIT_ERROR, True
        elif 500 <= status_code < 600:
            return ErrorTypes.API_ERROR, True
        elif status_code == 400:
            return ErrorTypes.INVALID_COORDINATES, False
        else:
            return ErrorTypes.API_ERROR, True
    
    def _parse_weather_response(self, data: Dict) -> WeatherData:
        """
        Parse OpenWeatherMap API response into WeatherData object.
        
        Args:
            data: Raw API response data
            
        Returns:
            WeatherData object with parsed information
            
        Raises:
            ValueError: If response data is invalid or missing required fields
        """
        try:
            # Validate required fields exist
            if 'main' not in data:
                raise ValueError("Missing 'main' section in API response")
            if 'weather' not in data or not data['weather']:
                raise ValueError("Missing 'weather' section in API response")
            if 'wind' not in data:
                raise ValueError("Missing 'wind' section in API response")
                
            main = data['main']
            weather = data['weather'][0]  # Take first weather condition
            wind = data['wind']
            
            # Extract and validate temperature
            temperature = main.get('temp')
            if temperature is None:
                raise ValueError("Missing temperature in API response")
            
            # Extract weather description
            description = weather.get('description', 'Unknown')
            
            # Extract and validate humidity
            humidity = main.get('humidity')
            if humidity is None:
                raise ValueError("Missing humidity in API response")
            
            # Extract wind speed (may be missing in some responses)
            wind_speed = wind.get('speed', 0.0)
            
            return WeatherData(
                temperature=float(temperature),
                description=description.title(),
                humidity=int(humidity),
                wind_speed=float(wind_speed),
                timestamp=datetime.now(),
                status=WeatherStatus.SUCCESS
            )
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing weather response: {str(e)}")
            logger.debug(f"Raw response data: {data}")
            raise ValueError(f"Invalid API response format: {str(e)}")


class WeatherService:
    """
    Main weather service that orchestrates weather data retrieval for multiple airports.
    
    Provides concurrent processing with caching and rate limiting to efficiently
    fetch weather data for multiple airports while respecting API limits.
    """
    
    def __init__(self, api_key: str, timeout: int = 30, max_concurrency: int = 10, cache_path: Optional[str] = None):
        """
        Initialize the weather service with performance optimizations.
        
        Args:
            api_key: OpenWeatherMap API key
            timeout: Request timeout in seconds (default: 30)
            max_concurrency: Maximum concurrent requests (default: 10)
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_concurrency = max_concurrency
        
        # Initialize cache with optimized settings for large datasets
        cache_size = min(max_concurrency * 100, 10000)  # Scale cache with concurrency
        # If a cache_path is provided, use SQLite-backed cache so it persists between runs
        if cache_path:
            try:
                self.cache = SQLiteWeatherCache(db_path=cache_path, default_ttl=1800, max_size=cache_size)
            except Exception:
                # Fallback to in-memory cache on failure
                self.cache = WeatherCache(max_size=cache_size)
        else:
            self.cache = WeatherCache(max_size=cache_size)
        
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._api_client: Optional[WeatherAPIClient] = None
        
        # Performance monitoring
        self._start_time = None
        self._request_times = []
        
        # Enhanced statistics tracking for graceful error handling
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cached_requests': 0,
            'network_errors': 0,
            'api_errors': 0,
            'timeout_errors': 0,
            'rate_limit_errors': 0,
            'authentication_errors': 0,
            'invalid_coordinate_errors': 0,
            'unknown_errors': 0,
            'airports_processed': 0,
            'airports_with_weather': 0,
            'airports_without_weather': 0
        }
        
    async def __aenter__(self):
        """Async context manager entry.

        If a caller (usually tests) has already injected a mock `_api_client`,
        don't override it. If the injected client provides an async __aenter__,
        call it; otherwise skip initialization.
        """
        # Only create a real API client if one hasn't been injected (useful for tests)
        if not getattr(self, '_api_client', None):
            self._api_client = WeatherAPIClient(self.api_key, self.timeout)
            await self._api_client.__aenter__()
        else:
            # If an injected client provides an async context enter, call it
            maybe_enter = getattr(self._api_client, '__aenter__', None)
            if maybe_enter is not None:
                try:
                    # If it's a coroutine function, await it
                    result = maybe_enter()
                    if hasattr(result, '__await__'):
                        await result
                except TypeError:
                    # Not awaitable, ignore
                    pass

        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._api_client:
            await self._api_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def get_weather_for_airports(self, airports: List[Airport]) -> Dict[str, WeatherData]:
        """
        Get weather data for multiple airports with concurrent processing and caching.
        
        This method implements graceful error handling by continuing to process all airports
        even when some queries fail, marking failed airports as "clima no disponible",
        and maintaining detailed statistics of success/failure rates.
        
        Args:
            airports: List of Airport objects to get weather data for
            
        Returns:
            Dictionary mapping airport IATA codes to WeatherData objects
        """
        if not airports:
            logger.info("No airports provided for weather retrieval")
            return {}
            
        logger.info(f"Starting weather retrieval for {len(airports)} airports with graceful error handling")
        
        # Reset processing statistics for this batch
        self._stats['airports_processed'] = len(airports)
        self._start_time = datetime.now()
        
        # Optimize concurrency based on dataset size
        effective_concurrency = min(self.max_concurrency, len(airports))
        if effective_concurrency != self.max_concurrency:
            logger.info(f"Optimizing concurrency to {effective_concurrency} for {len(airports)} airports")
        
        # Create tasks for concurrent processing - each task is isolated to prevent
        # failures in one airport from affecting others
        tasks = []
        for airport in airports:
            task = asyncio.create_task(
                self._get_weather_for_single_airport_with_graceful_handling(airport),
                name=f"weather_{airport.iata_code}"
            )
            tasks.append((airport.iata_code, task))
        
        # Use asyncio.gather with return_exceptions=True to ensure all tasks complete
        # even if some fail, implementing true graceful error handling
        results = {}
        task_results = await asyncio.gather(
            *[task for _, task in tasks], 
            return_exceptions=True
        )
        
        # Process results and update statistics
        for i, (iata_code, _) in enumerate(tasks):
            result = task_results[i]
            
            if isinstance(result, Exception):
                # Handle unexpected exceptions that weren't caught in the task
                logger.error(f"Unexpected exception processing airport {iata_code}: {str(result)}")
                weather_data = self._create_unavailable_weather_data(
                    f"Processing exception: {str(result)}",
                    ErrorTypes.UNKNOWN_ERROR
                )
                self._update_error_statistics(ErrorTypes.UNKNOWN_ERROR)
            else:
                weather_data = result
                self._update_statistics_for_result(weather_data)
            
            results[iata_code] = weather_data
        
        # Calculate performance metrics
        if self._start_time:
            processing_time = (datetime.now() - self._start_time).total_seconds()
            self._stats['processing_time_seconds'] = processing_time
            self._stats['airports_per_second'] = len(airports) / processing_time if processing_time > 0 else 0
        
        # Log comprehensive statistics
        self._log_processing_statistics()
        
        return results
    
    async def _get_weather_for_single_airport_with_graceful_handling(self, airport: Airport) -> WeatherData:
        """
        Get weather data for a single airport with enhanced graceful error handling.
        
        This method ensures that any failure for one airport doesn't affect processing
        of other airports and properly marks failed airports as "clima no disponible".
        
        Args:
            airport: Airport object to get weather data for
            
        Returns:
            WeatherData object with weather information or "clima no disponible" status
        """
        try:
            return await self._get_weather_for_single_airport(airport)
        except Exception as e:
            # Catch any unexpected exceptions to ensure graceful continuation
            logger.error(f"Unexpected error in graceful handler for {airport.iata_code}: {str(e)}")
            return self._create_unavailable_weather_data(
                f"Unexpected service error: {str(e)}",
                ErrorTypes.UNKNOWN_ERROR
            )
    
    async def _get_weather_for_single_airport(self, airport: Airport) -> WeatherData:
        """
        Get weather data for a single airport with caching and rate limiting.
        
        Args:
            airport: Airport object to get weather data for
            
        Returns:
            WeatherData object with weather information or error details
        """
        self._stats['total_requests'] += 1
        
        # Check cache first
        cache_key = airport.cache_key()
        cached_data = self.cache.get(cache_key)
        
        if cached_data is not None:
            logger.debug(f"Using cached weather data for {airport.iata_code}")
            # Mark as cached but still count as successful weather retrieval
            cached_data.status = WeatherStatus.CACHED
            self._stats['cached_requests'] += 1
            return cached_data
        
        # Use semaphore to limit concurrent requests
        async with self._semaphore:
            logger.debug(f"Fetching weather data for {airport.iata_code} ({airport.latitude}, {airport.longitude})")
            
            # Track request timing for performance monitoring
            request_start = datetime.now()
            
            try:
                # Fetch weather data from API
                weather_data = await self._api_client.fetch_weather_with_retry(
                    airport.latitude, 
                    airport.longitude
                )
                
                # Record request time
                request_time = (datetime.now() - request_start).total_seconds()
                self._request_times.append(request_time)
                
                # Cache successful results
                if weather_data.status == WeatherStatus.SUCCESS:
                    self.cache.set(cache_key, weather_data)
                    logger.debug(f"Cached weather data for {airport.iata_code}")
                    self._stats['successful_requests'] += 1
                else:
                    # Weather data returned with error status - mark as unavailable
                    weather_data.description = "Clima no disponible"
                    self._stats['failed_requests'] += 1
                    self._update_error_statistics(weather_data.error_type)
                
                return weather_data
                
            except Exception as e:
                logger.error(f"Failed to fetch weather for {airport.iata_code}: {str(e)}")
                self._stats['failed_requests'] += 1
                self._stats['unknown_errors'] += 1
                
                return self._create_unavailable_weather_data(
                    f"Service error: {str(e)}",
                    ErrorTypes.UNKNOWN_ERROR
                )
    
    async def get_weather_by_coordinates(self, lat: float, lon: float) -> WeatherData:
        """
        Get weather data for specific coordinates.
        
        This is a convenience method for getting weather data by coordinates
        without needing to create an Airport object.
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            
        Returns:
            WeatherData object with weather information or error details
        """
        # Create a temporary airport object for caching
        temp_airport = Airport(
            iata_code="TEMP",
            name="Temporary",
            latitude=lat,
            longitude=lon
        )
        
        return await self._get_weather_for_single_airport(temp_airport)
    
    def _create_unavailable_weather_data(self, error_message: str, error_type: ErrorTypes) -> WeatherData:
        """
        Create a WeatherData object for unavailable weather with Spanish message.
        
        Args:
            error_message: Detailed error message for logging
            error_type: Type of error that occurred
            
        Returns:
            WeatherData object marked as unavailable
        """
        return WeatherData(
            temperature=0.0,
            description="Clima no disponible",  # Spanish for "Weather not available"
            humidity=0,
            wind_speed=0.0,
            timestamp=datetime.now(),
            status=WeatherStatus.NOT_AVAILABLE,
            error_message=error_message,
            error_type=error_type
        )
    
    def _update_error_statistics(self, error_type: Optional[ErrorTypes]) -> None:
        """
        Update error statistics based on error type.
        
        Args:
            error_type: Type of error that occurred
        """
        if error_type == ErrorTypes.NETWORK_ERROR:
            self._stats['network_errors'] += 1
        elif error_type == ErrorTypes.API_ERROR:
            self._stats['api_errors'] += 1
        elif error_type == ErrorTypes.TIMEOUT_ERROR:
            self._stats['timeout_errors'] += 1
        elif error_type == ErrorTypes.RATE_LIMIT_ERROR:
            self._stats['rate_limit_errors'] += 1
        elif error_type == ErrorTypes.AUTHENTICATION_ERROR:
            self._stats['authentication_errors'] += 1
        elif error_type == ErrorTypes.INVALID_COORDINATES:
            self._stats['invalid_coordinate_errors'] += 1
        else:
            self._stats['unknown_errors'] += 1
    
    def _update_statistics_for_result(self, weather_data: WeatherData) -> None:
        """
        Update statistics based on weather data result.
        
        Args:
            weather_data: WeatherData object to analyze
        """
        if weather_data.status in [WeatherStatus.SUCCESS, WeatherStatus.CACHED]:
            self._stats['airports_with_weather'] += 1
        else:
            self._stats['airports_without_weather'] += 1
            if weather_data.error_type:
                self._update_error_statistics(weather_data.error_type)
    
    def _log_processing_statistics(self) -> None:
        """
        Log comprehensive processing statistics for monitoring and debugging.
        """
        stats = self._stats
        total_airports = stats['airports_processed']
        success_rate = (stats['airports_with_weather'] / total_airports * 100) if total_airports > 0 else 0
        
        logger.info(
            f"Weather processing completed with graceful error handling. "
            f"Total airports: {total_airports}, "
            f"With weather: {stats['airports_with_weather']}, "
            f"Without weather: {stats['airports_without_weather']}, "
            f"Success rate: {success_rate:.1f}%"
        )
        
        # Log detailed error breakdown if there were failures
        if stats['airports_without_weather'] > 0:
            logger.info(
                f"Error breakdown - "
                f"Network: {stats['network_errors']}, "
                f"API: {stats['api_errors']}, "
                f"Timeout: {stats['timeout_errors']}, "
                f"Rate limit: {stats['rate_limit_errors']}, "
                f"Auth: {stats['authentication_errors']}, "
                f"Invalid coords: {stats['invalid_coordinate_errors']}, "
                f"Unknown: {stats['unknown_errors']}"
            )
        
        # Log cache performance
        cache_hit_rate = (stats['cached_requests'] / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
        logger.info(f"Cache performance - Hit rate: {cache_hit_rate:.1f}%")
        
        # Log performance metrics
        if 'processing_time_seconds' in stats:
            logger.info(
                f"Performance metrics - "
                f"Total time: {stats['processing_time_seconds']:.2f}s, "
                f"Rate: {stats['airports_per_second']:.1f} airports/sec"
            )
            
            # Log request timing statistics if available
            if self._request_times:
                avg_request_time = sum(self._request_times) / len(self._request_times)
                max_request_time = max(self._request_times)
                logger.info(
                    f"Request timing - "
                    f"Avg: {avg_request_time:.3f}s, "
                    f"Max: {max_request_time:.3f}s, "
                    f"Total requests: {len(self._request_times)}"
                )

    def get_processing_statistics(self) -> Dict[str, any]:
        """
        Get comprehensive processing statistics including success/failure rates.
        
        Returns:
            Dictionary with detailed processing statistics
        """
        stats = self._stats.copy()
        
        # Calculate derived statistics
        total_airports = stats['airports_processed']
        if total_airports > 0:
            stats['success_rate_percent'] = round((stats['airports_with_weather'] / total_airports) * 100, 2)
            stats['failure_rate_percent'] = round((stats['airports_without_weather'] / total_airports) * 100, 2)
        else:
            stats['success_rate_percent'] = 0.0
            stats['failure_rate_percent'] = 0.0
        
        # Calculate cache hit rate
        if stats['total_requests'] > 0:
            stats['cache_hit_rate_percent'] = round((stats['cached_requests'] / stats['total_requests']) * 100, 2)
        else:
            stats['cache_hit_rate_percent'] = 0.0
        
        return stats

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics including hit rate
        """
        stats = self.cache.get_stats()
        
        # Calculate hit rate if we have data
        total_requests = getattr(self, '_total_requests', 0)
        cache_hits = getattr(self, '_cache_hits', 0)
        
        if total_requests > 0:
            hit_rate = (cache_hits / total_requests) * 100
            stats['hit_rate_percent'] = round(hit_rate, 2)
        else:
            stats['hit_rate_percent'] = 0.0
            
        return stats
    
    def clear_cache(self) -> None:
        """Clear all cached weather data."""
        self.cache.clear()
        logger.info("Weather cache cleared")