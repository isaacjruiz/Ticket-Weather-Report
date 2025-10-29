"""
Cache manager for weather data.

This module provides in-memory caching functionality for weather data
to avoid duplicate API calls and improve performance.
"""

import time
import gc
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

try:
    from .models import WeatherData, WeatherStatus
except ImportError:
    from models import WeatherData, WeatherStatus


class WeatherCache:
    """
    In-memory cache for weather data with TTL (Time To Live) functionality and LRU eviction.
    
    Stores weather data with timestamps to avoid duplicate API calls
    within the configured TTL period (default 30 minutes). Implements LRU eviction
    and memory limits for large datasets.
    """
    
    def __init__(self, default_ttl: int = 1800, max_size: int = 10000):
        """
        Initialize the weather cache with LRU eviction and memory limits.
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 1800 = 30 minutes)
            max_size: Maximum number of entries in cache (default: 10000)
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        # Use OrderedDict for LRU functionality
        self._cache: OrderedDict[str, Tuple[WeatherData, float]] = OrderedDict()
        self._access_count = 0
        self._cleanup_threshold = 100  # Cleanup every 100 accesses
    
    def get(self, key: str) -> Optional[WeatherData]:
        """
        Retrieve weather data from cache if it exists and hasn't expired.
        Implements LRU by moving accessed items to end.
        
        Args:
            key: Cache key (typically generated from airport coordinates)
            
        Returns:
            WeatherData if found and not expired, None otherwise
        """
        self._access_count += 1
        
        # Periodic cleanup to manage memory
        if self._access_count % self._cleanup_threshold == 0:
            self._periodic_cleanup()
        
        if key not in self._cache:
            return None
            
        weather_data, timestamp = self._cache[key]
        
        if self.is_expired(key):
            # Remove expired entry
            del self._cache[key]
            return None
        
        # Move to end for LRU (most recently used)
        self._cache.move_to_end(key)
            
        # Mark as cached data
        cached_data = WeatherData(
            temperature=weather_data.temperature,
            description=weather_data.description,
            humidity=weather_data.humidity,
            wind_speed=weather_data.wind_speed,
            timestamp=weather_data.timestamp,
            status=WeatherStatus.CACHED,
            error_message=weather_data.error_message,
            error_type=weather_data.error_type
        )
        
        return cached_data
    
    def set(self, key: str, data: WeatherData, ttl: Optional[int] = None) -> None:
        """
        Store weather data in cache with timestamp and LRU eviction.
        
        Args:
            key: Cache key (typically generated from airport coordinates)
            data: WeatherData to store
            ttl: Time-to-live in seconds (uses default_ttl if None)
        """
        if ttl is None:
            ttl = self.default_ttl
            
        # Store with current timestamp
        current_time = time.time()
        
        # If key exists, update and move to end
        if key in self._cache:
            self._cache[key] = (data, current_time)
            self._cache.move_to_end(key)
        else:
            # Check if we need to evict old entries
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            self._cache[key] = (data, current_time)
    
    def is_expired(self, key: str) -> bool:
        """
        Check if a cache entry has expired.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if expired or doesn't exist, False otherwise
        """
        if key not in self._cache:
            return True
            
        _, timestamp = self._cache[key]
        current_time = time.time()
        
        return (current_time - timestamp) > self.default_ttl
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
    
    def size(self) -> int:
        """Get the number of entries in cache."""
        return len(self._cache)
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        expired_keys = [key for key in self._cache.keys() if self.is_expired(key)]
        
        for key in expired_keys:
            del self._cache[key]
            
        return len(expired_keys)
    
    def _evict_lru(self) -> None:
        """
        Evict least recently used entries to make room for new ones.
        Removes 10% of cache size to avoid frequent evictions.
        """
        evict_count = max(1, self.max_size // 10)  # Remove 10% or at least 1
        
        for _ in range(evict_count):
            if self._cache:
                # Remove from beginning (least recently used)
                self._cache.popitem(last=False)
    
    def _periodic_cleanup(self) -> None:
        """
        Periodic cleanup of expired entries and memory optimization.
        """
        # Remove expired entries
        expired_count = self.cleanup_expired()
        
        # Force garbage collection if we removed many items
        if expired_count > 50:
            gc.collect()
    
    def get_memory_usage_estimate(self) -> Dict[str, int]:
        """
        Estimate memory usage of the cache.
        
        Returns:
            Dictionary with memory usage estimates in bytes
        """
        # Rough estimate: each WeatherData object ~200 bytes + key ~50 bytes
        estimated_per_entry = 250
        total_entries = len(self._cache)
        
        return {
            'estimated_total_bytes': total_entries * estimated_per_entry,
            'estimated_mb': round((total_entries * estimated_per_entry) / (1024 * 1024), 2),
            'entries_count': total_entries,
            'max_entries': self.max_size
        }

    def get_stats(self) -> Dict[str, int]:
        """
        Get comprehensive cache statistics including memory usage.
        
        Returns:
            Dictionary with cache statistics
        """
        total_entries = len(self._cache)
        expired_entries = sum(1 for key in self._cache.keys() if self.is_expired(key))
        valid_entries = total_entries - expired_entries
        memory_stats = self.get_memory_usage_estimate()
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'max_size': self.max_size,
            'memory_usage_mb': memory_stats['estimated_mb'],
            'access_count': self._access_count
        }