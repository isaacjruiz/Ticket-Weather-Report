"""
Data models for the Weather Report System.

This module contains all the dataclasses and enums used throughout the system
for representing airports, weather data, flight information, and results.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class WeatherStatus(Enum):
    """Status of weather data retrieval."""
    SUCCESS = "success"
    ERROR = "error"
    NOT_AVAILABLE = "not_available"
    CACHED = "cached"


class ErrorTypes(Enum):
    """Types of errors that can occur during weather data retrieval."""
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    AUTHENTICATION_ERROR = "authentication_error"
    INVALID_COORDINATES = "invalid_coordinates"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class Airport:
    """Represents an airport with its location information."""
    iata_code: str
    name: str
    latitude: float
    longitude: float
    
    def cache_key(self) -> str:
        """Generate a unique cache key for this airport's weather data."""
        return f"weather_{self.iata_code}_{self.latitude}_{self.longitude}"


@dataclass
class WeatherData:
    """Represents weather information for a specific location."""
    temperature: float
    description: str
    humidity: int
    wind_speed: float
    timestamp: datetime
    status: WeatherStatus = WeatherStatus.SUCCESS
    error_message: Optional[str] = None
    error_type: Optional[ErrorTypes] = None


@dataclass
class FlightInfo:
    """Represents flight information from the dataset."""
    flight_number: str
    origin_airport_code: str
    destination_airport_code: str
    departure_date: str
    ticket_id: str


@dataclass
class WeatherResult:
    """Represents the complete weather result for a flight route."""
    airport: Airport
    origin_weather: Optional[WeatherData]
    destination_weather: Optional[WeatherData]
    flight_info: FlightInfo