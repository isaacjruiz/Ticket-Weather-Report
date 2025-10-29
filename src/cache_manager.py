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


class SQLiteWeatherCache:
    """
    Simple SQLite-backed cache for WeatherData.

    Stores serialized WeatherData objects as JSON along with a timestamp so
    entries can be shared between separate runs of the program.
    """

    def __init__(self, db_path: str, default_ttl: int = 1800, max_size: int = 10000):
        import sqlite3
        import json
        self.db_path = db_path
        self.default_ttl = default_ttl
        self.max_size = max_size
        # Use a connection that can be shared across threads/tasks
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # Enable WAL for better concurrency
        try:
            self._conn.execute('PRAGMA journal_mode=WAL;')
        except Exception:
            pass

        # Create table if not exists
        self._conn.execute(
            'CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, ts REAL)'
        )
        self._conn.commit()

    def _serialize(self, data: WeatherData) -> dict:
        return {
            'temperature': data.temperature,
            'description': data.description,
            'humidity': data.humidity,
            'wind_speed': data.wind_speed,
            'timestamp': data.timestamp.isoformat() if data.timestamp is not None else None,
            'status': data.status.value if data.status is not None else None,
            'error_message': data.error_message,
            'error_type': data.error_type.value if data.error_type is not None else None
        }

    def _deserialize(self, obj: dict) -> WeatherData:
        from datetime import datetime
        # Reconstruct WeatherData from the stored dict
        ts = obj.get('timestamp')
        timestamp = datetime.fromisoformat(ts) if ts else datetime.now()

        error_type = None
        try:
            if obj.get('error_type'):
                from models import ErrorTypes
                error_type = ErrorTypes(obj.get('error_type'))
        except Exception:
            error_type = None

        status = None
        try:
            if obj.get('status'):
                from models import WeatherStatus
                status = WeatherStatus(obj.get('status'))
        except Exception:
            status = None

        return WeatherData(
            temperature=float(obj.get('temperature', 0.0)),
            description=obj.get('description', ''),
            humidity=int(obj.get('humidity', 0)),
            wind_speed=float(obj.get('wind_speed', 0.0)),
            timestamp=timestamp,
            status=status or WeatherStatus.CACHED,
            error_message=obj.get('error_message'),
            error_type=error_type
        )

    def get(self, key: str) -> Optional[WeatherData]:
        import json, time
        cur = self._conn.execute('SELECT value, ts FROM cache WHERE key = ?', (key,))
        row = cur.fetchone()
        if not row:
            return None

        value_json, ts = row
        # Check TTL
        if (time.time() - ts) > self.default_ttl:
            # expired
            self._conn.execute('DELETE FROM cache WHERE key = ?', (key,))
            self._conn.commit()
            return None

        try:
            obj = json.loads(value_json)
            weather_data = self._deserialize(obj)
            # Mark as cached
            weather_data.status = WeatherStatus.CACHED
            return weather_data
        except Exception:
            return None

    def set(self, key: str, data: WeatherData, ttl: Optional[int] = None) -> None:
        import json, time
        if ttl is None:
            ttl = self.default_ttl

        value_json = json.dumps(self._serialize(data))
        ts = time.time()
        # Use REPLACE INTO to insert or update
        self._conn.execute('REPLACE INTO cache (key, value, ts) VALUES (?, ?, ?)', (key, value_json, ts))
        self._conn.commit()

        # Optional eviction by max_size: if table grows too large, delete oldest
        cur = self._conn.execute('SELECT COUNT(1) FROM cache')
        total = cur.fetchone()[0]
        if total > self.max_size:
            # delete oldest entries to reduce size to max_size
            to_remove = total - self.max_size
            self._conn.execute(
                'DELETE FROM cache WHERE key IN (SELECT key FROM cache ORDER BY ts ASC LIMIT ?)',
                (to_remove,)
            )
            self._conn.commit()

    def is_expired(self, key: str) -> bool:
        import time
        cur = self._conn.execute('SELECT ts FROM cache WHERE key = ?', (key,))
        row = cur.fetchone()
        if not row:
            return True
        ts = row[0]
        return (time.time() - ts) > self.default_ttl

    def clear(self) -> None:
        self._conn.execute('DELETE FROM cache')
        self._conn.commit()

    def size(self) -> int:
        cur = self._conn.execute('SELECT COUNT(1) FROM cache')
        return int(cur.fetchone()[0])

    def cleanup_expired(self) -> int:
        import time
        threshold = time.time() - self.default_ttl
        cur = self._conn.execute('SELECT COUNT(1) FROM cache WHERE ts < ?', (threshold,))
        removed = int(cur.fetchone()[0])
        self._conn.execute('DELETE FROM cache WHERE ts < ?', (threshold,))
        self._conn.commit()
        return removed

    def get_stats(self) -> Dict[str, int]:
        cur = self._conn.execute('SELECT COUNT(1) FROM cache')
        total = int(cur.fetchone()[0])
        # Count expired
        import time
        threshold = time.time() - self.default_ttl
        cur = self._conn.execute('SELECT COUNT(1) FROM cache WHERE ts < ?', (threshold,))
        expired = int(cur.fetchone()[0])
        valid = total - expired
        return {
            'total_entries': total,
            'valid_entries': valid,
            'expired_entries': expired,
            'max_size': self.max_size,
            'memory_usage_mb': 0.0,
            'access_count': 0
        }