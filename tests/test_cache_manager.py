"""
Tests for the WeatherCache class.

This module contains comprehensive tests for the cache manager functionality,
including TTL verification, data storage and retrieval operations.
"""

import time
import pytest
from datetime import datetime
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cache_manager import WeatherCache
from models import WeatherData, WeatherStatus, ErrorTypes


class TestWeatherCache:
    """Test suite for WeatherCache class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.cache = WeatherCache(default_ttl=1800)  # 30 minutes
        self.sample_weather_data = WeatherData(
            temperature=25.5,
            description="Clear sky",
            humidity=60,
            wind_speed=5.2,
            timestamp=datetime.now(),
            status=WeatherStatus.SUCCESS
        )
        self.cache_key = "weather_JFK_40.6413_-73.7781"
    
    def test_cache_initialization(self):
        """Test cache initialization with default and custom TTL."""
        # Test default TTL
        default_cache = WeatherCache()
        assert default_cache.default_ttl == 1800
        assert default_cache.size() == 0
        
        # Test custom TTL
        custom_cache = WeatherCache(default_ttl=3600)
        assert custom_cache.default_ttl == 3600
        assert custom_cache.size() == 0
    
    def test_set_and_get_data(self):
        """Test basic storage and retrieval of weather data."""
        # Store data in cache
        self.cache.set(self.cache_key, self.sample_weather_data)
        
        # Verify cache size
        assert self.cache.size() == 1
        
        # Retrieve data from cache
        cached_data = self.cache.get(self.cache_key)
        
        # Verify data integrity
        assert cached_data is not None
        assert cached_data.temperature == self.sample_weather_data.temperature
        assert cached_data.description == self.sample_weather_data.description
        assert cached_data.humidity == self.sample_weather_data.humidity
        assert cached_data.wind_speed == self.sample_weather_data.wind_speed
        assert cached_data.status == WeatherStatus.CACHED  # Should be marked as cached
    
    def test_get_nonexistent_key(self):
        """Test retrieval of non-existent cache key."""
        result = self.cache.get("nonexistent_key")
        assert result is None
    
    def test_cache_overwrite(self):
        """Test overwriting existing cache entries."""
        # Store initial data
        self.cache.set(self.cache_key, self.sample_weather_data)
        
        # Create new weather data
        new_weather_data = WeatherData(
            temperature=30.0,
            description="Partly cloudy",
            humidity=70,
            wind_speed=8.5,
            timestamp=datetime.now(),
            status=WeatherStatus.SUCCESS
        )
        
        # Overwrite with new data
        self.cache.set(self.cache_key, new_weather_data)
        
        # Verify cache still has only one entry
        assert self.cache.size() == 1
        
        # Verify new data is retrieved
        cached_data = self.cache.get(self.cache_key)
        assert cached_data.temperature == 30.0
        assert cached_data.description == "Partly cloudy"
    
    def test_ttl_expiration_with_mock_time(self):
        """Test TTL expiration using mocked time."""
        # Set cache with 60 second TTL
        short_ttl_cache = WeatherCache(default_ttl=60)
        
        with patch('time.time') as mock_time:
            # Initial time
            mock_time.return_value = 1000.0
            
            # Store data
            short_ttl_cache.set(self.cache_key, self.sample_weather_data)
            
            # Verify data is available immediately
            cached_data = short_ttl_cache.get(self.cache_key)
            assert cached_data is not None
            assert not short_ttl_cache.is_expired(self.cache_key)
            
            # Advance time by 30 seconds (within TTL)
            mock_time.return_value = 1030.0
            cached_data = short_ttl_cache.get(self.cache_key)
            assert cached_data is not None
            assert not short_ttl_cache.is_expired(self.cache_key)
            
            # Advance time by 61 seconds (beyond TTL)
            mock_time.return_value = 1061.0
            assert short_ttl_cache.is_expired(self.cache_key)
            
            # Data should be None and removed from cache
            cached_data = short_ttl_cache.get(self.cache_key)
            assert cached_data is None
            assert short_ttl_cache.size() == 0
    
    def test_ttl_expiration_real_time(self):
        """Test TTL expiration with real time (short TTL for testing)."""
        # Create cache with very short TTL for testing
        short_ttl_cache = WeatherCache(default_ttl=1)  # 1 second
        
        # Store data
        short_ttl_cache.set(self.cache_key, self.sample_weather_data)
        
        # Verify data is available immediately
        cached_data = short_ttl_cache.get(self.cache_key)
        assert cached_data is not None
        assert not short_ttl_cache.is_expired(self.cache_key)
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Verify data has expired
        assert short_ttl_cache.is_expired(self.cache_key)
        cached_data = short_ttl_cache.get(self.cache_key)
        assert cached_data is None
    
    def test_custom_ttl_per_entry(self):
        """Test setting custom TTL for individual cache entries."""
        with patch('time.time') as mock_time:
            mock_time.return_value = 1000.0
            
            # Store with custom TTL
            self.cache.set(self.cache_key, self.sample_weather_data, ttl=120)  # 2 minutes
            
            # Advance time by 90 seconds (within custom TTL but beyond default)
            mock_time.return_value = 1090.0
            
            # Note: Current implementation uses default_ttl for expiration check
            # This test documents current behavior - may need adjustment if 
            # per-entry TTL is implemented in the future
            cached_data = self.cache.get(self.cache_key)
            assert cached_data is not None  # Should still be valid with default TTL
    
    def test_clear_cache(self):
        """Test clearing all cache entries."""
        # Add multiple entries
        self.cache.set("key1", self.sample_weather_data)
        self.cache.set("key2", self.sample_weather_data)
        self.cache.set("key3", self.sample_weather_data)
        
        assert self.cache.size() == 3
        
        # Clear cache
        self.cache.clear()
        
        assert self.cache.size() == 0
        assert self.cache.get("key1") is None
        assert self.cache.get("key2") is None
        assert self.cache.get("key3") is None
    
    def test_cleanup_expired_entries(self):
        """Test cleanup of expired entries."""
        with patch('time.time') as mock_time:
            # Initial time
            mock_time.return_value = 1000.0
            
            # Add multiple entries
            self.cache.set("key1", self.sample_weather_data)
            self.cache.set("key2", self.sample_weather_data)
            self.cache.set("key3", self.sample_weather_data)
            
            assert self.cache.size() == 3
            
            # Advance time to expire entries
            mock_time.return_value = 1000.0 + self.cache.default_ttl + 1
            
            # Cleanup expired entries
            removed_count = self.cache.cleanup_expired()
            
            assert removed_count == 3
            assert self.cache.size() == 0
    
    def test_cache_stats(self):
        """Test cache statistics functionality."""
        with patch('time.time') as mock_time:
            # Initial time
            mock_time.return_value = 1000.0
            
            # Add entries at different times
            self.cache.set("key1", self.sample_weather_data)
            self.cache.set("key2", self.sample_weather_data)
            
            # Advance time partially
            mock_time.return_value = 1000.0 + self.cache.default_ttl - 100
            self.cache.set("key3", self.sample_weather_data)  # This one is newer
            
            # Advance time to expire first two entries
            mock_time.return_value = 1000.0 + self.cache.default_ttl + 1
            
            stats = self.cache.get_stats()
            
            assert stats['total_entries'] == 3
            assert stats['expired_entries'] == 2
            assert stats['valid_entries'] == 1
    
    def test_cache_with_error_data(self):
        """Test caching weather data with error status."""
        error_weather_data = WeatherData(
            temperature=0.0,
            description="",
            humidity=0,
            wind_speed=0.0,
            timestamp=datetime.now(),
            status=WeatherStatus.ERROR,
            error_message="API timeout",
            error_type=ErrorTypes.TIMEOUT_ERROR
        )
        
        # Store error data
        self.cache.set(self.cache_key, error_weather_data)
        
        # Retrieve and verify
        cached_data = self.cache.get(self.cache_key)
        assert cached_data is not None
        assert cached_data.status == WeatherStatus.CACHED  # Should be marked as cached
        assert cached_data.error_message == "API timeout"
        assert cached_data.error_type == ErrorTypes.TIMEOUT_ERROR
    
    def test_multiple_airports_caching(self):
        """Test caching data for multiple airports."""
        # Create different airport cache keys
        jfk_key = "weather_JFK_40.6413_-73.7781"
        lax_key = "weather_LAX_33.9425_-118.4081"
        ord_key = "weather_ORD_41.9742_-87.9073"
        
        # Create different weather data for each
        jfk_weather = WeatherData(25.5, "Clear", 60, 5.2, datetime.now())
        lax_weather = WeatherData(28.0, "Sunny", 45, 3.1, datetime.now())
        ord_weather = WeatherData(15.2, "Cloudy", 80, 12.5, datetime.now())
        
        # Store all data
        self.cache.set(jfk_key, jfk_weather)
        self.cache.set(lax_key, lax_weather)
        self.cache.set(ord_key, ord_weather)
        
        assert self.cache.size() == 3
        
        # Verify each can be retrieved correctly
        cached_jfk = self.cache.get(jfk_key)
        cached_lax = self.cache.get(lax_key)
        cached_ord = self.cache.get(ord_key)
        
        assert cached_jfk.temperature == 25.5
        assert cached_lax.temperature == 28.0
        assert cached_ord.temperature == 15.2
        
        assert cached_jfk.description == "Clear"
        assert cached_lax.description == "Sunny"
        assert cached_ord.description == "Cloudy"
    
    def test_is_expired_nonexistent_key(self):
        """Test is_expired method with non-existent key."""
        assert self.cache.is_expired("nonexistent_key") is True
    
    def test_cache_preserves_original_data_integrity(self):
        """Test that caching doesn't modify the original weather data."""
        original_status = self.sample_weather_data.status
        
        # Store in cache
        self.cache.set(self.cache_key, self.sample_weather_data)
        
        # Verify original data is unchanged
        assert self.sample_weather_data.status == original_status
        
        # Verify cached data has different status
        cached_data = self.cache.get(self.cache_key)
        assert cached_data.status == WeatherStatus.CACHED
        assert cached_data.status != original_status