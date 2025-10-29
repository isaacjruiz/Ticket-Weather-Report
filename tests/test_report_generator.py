"""
Tests for the Weather Report Generator module.

This module contains comprehensive tests for the WeatherReportGenerator class,
including tests for table formatting, statistics calculation, and report generation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from io import StringIO

from src.report_generator import WeatherReportGenerator, ReportStats
from src.models import Airport, WeatherData, WeatherResult, FlightInfo, WeatherStatus, ErrorTypes


class TestWeatherReportGenerator:
    """Test cases for WeatherReportGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.generator = WeatherReportGenerator()
        
        # Create sample airports
        self.airport_mad = Airport(
            iata_code="MAD",
            name="Madrid-Barajas Airport",
            latitude=40.4719,
            longitude=-3.5626
        )
        
        self.airport_bcn = Airport(
            iata_code="BCN", 
            name="Barcelona-El Prat Airport",
            latitude=41.2971,
            longitude=2.0785
        )
        
        self.airport_lhr = Airport(
            iata_code="LHR",
            name="London Heathrow Airport", 
            latitude=51.4700,
            longitude=-0.4543
        )
        
        # Create sample weather data
        self.weather_success = WeatherData(
            temperature=22.5,
            description="clear sky",
            humidity=65,
            wind_speed=3.2,
            timestamp=datetime.now(),
            status=WeatherStatus.SUCCESS
        )
        
        self.weather_cached = WeatherData(
            temperature=18.7,
            description="few clouds",
            humidity=72,
            wind_speed=2.1,
            timestamp=datetime.now() - timedelta(minutes=15),
            status=WeatherStatus.CACHED
        )
        
        self.weather_error = WeatherData(
            temperature=0.0,
            description="",
            humidity=0,
            wind_speed=0.0,
            timestamp=datetime.now(),
            status=WeatherStatus.ERROR,
            error_message="API rate limit exceeded",
            error_type=ErrorTypes.RATE_LIMIT_ERROR
        )
        
        # Create sample flight info
        self.flight_info = FlightInfo(
            flight_number="IB6789",
            origin_airport_code="MAD",
            destination_airport_code="BCN",
            departure_date="2024-03-15",
            ticket_id="TK001"
        )


class TestTableFormatting(TestWeatherReportGenerator):
    """Test cases for table formatting functionality."""
    
    def test_format_weather_table_with_successful_data(self):
        """Test formatting weather table with successful weather data."""
        results = {
            "MAD": self.weather_success,
            "BCN": self.weather_cached
        }
        airports = [self.airport_mad, self.airport_bcn]
        
        table = self.generator._format_weather_table(results, airports)
        
        # Verify table structure
        assert table.title == "Información Meteorológica por Aeropuerto"
        assert len(table.columns) == 7
        assert len(table.rows) == 2
        
        # Verify column headers
        column_headers = [col.header for col in table.columns]
        expected_headers = [
            "Código IATA", "Nombre del Aeropuerto", "Temperatura", 
            "Descripción", "Humedad", "Viento", "Estado"
        ]
        assert column_headers == expected_headers
    
    def test_format_weather_table_with_mixed_data(self):
        """Test formatting weather table with mixed success/error data."""
        results = {
            "MAD": self.weather_success,
            "BCN": self.weather_error,
            "LHR": None  # No data available
        }
        airports = [self.airport_mad, self.airport_bcn, self.airport_lhr]
        
        table = self.generator._format_weather_table(results, airports)
        
        # Verify all airports are included
        assert len(table.rows) == 3
        
        # Check that error cases are handled properly
        # The table should contain appropriate error indicators
        assert table is not None
    
    def test_format_weather_table_empty_data(self):
        """Test formatting weather table with no data."""
        results = {}
        airports = []
        
        table = self.generator._format_weather_table(results, airports)
        
        # Should create empty table with headers
        assert table.title == "Información Meteorológica por Aeropuerto"
        assert len(table.columns) == 7
        assert len(table.rows) == 0
    
    def test_format_weather_table_string_method(self):
        """Test the alternative string-based table formatting method."""
        weather_results = [
            WeatherResult(
                airport=self.airport_mad,
                origin_weather=self.weather_success,
                destination_weather=None,
                flight_info=self.flight_info
            ),
            WeatherResult(
                airport=self.airport_bcn,
                origin_weather=self.weather_error,
                destination_weather=None,
                flight_info=self.flight_info
            )
        ]
        
        table_string = self.generator.format_weather_table(weather_results)
        
        # Verify string contains expected elements
        assert "Código" in table_string
        assert "Aeropuerto" in table_string
        assert "Temperatura" in table_string
        assert "MAD" in table_string
        assert "BCN" in table_string
        assert "22.5°C" in table_string
        assert "Exitoso" in table_string
        assert "Error" in table_string
    
    def test_format_weather_table_string_empty(self):
        """Test string table formatting with empty data."""
        table_string = self.generator.format_weather_table([])
        
        assert table_string == "No hay datos meteorológicos disponibles."
    
    def test_format_statistics_panel(self):
        """Test formatting of statistics panel."""
        stats = ReportStats(
            total_airports=10,
            successful_queries=8,
            failed_queries=2,
            cached_queries=3,
            processing_time=45.67,
            cache_hit_rate=30.0
        )
        
        panel = self.generator._format_statistics_panel(stats)
        
        # Verify panel contains expected statistics
        assert panel is not None
        # The panel content should be a Text object with our statistics
        content = str(panel.renderable)
        assert "10" in content  # total airports
        assert "8" in content   # successful queries
        assert "2" in content   # failed queries
        assert "3" in content   # cached queries
        assert "45.67" in content  # processing time
    
    def test_format_statistics_panel_long_processing_time(self):
        """Test statistics panel formatting with long processing time."""
        stats = ReportStats(
            total_airports=100,
            successful_queries=95,
            failed_queries=5,
            cached_queries=20,
            processing_time=125.5,  # Over 2 minutes
            cache_hit_rate=20.0
        )
        
        panel = self.generator._format_statistics_panel(stats)
        
        # Should format time as minutes and seconds
        content = str(panel.renderable)
        assert "2m" in content and "5.5s" in content


class TestStatisticsCalculation(TestWeatherReportGenerator):
    """Test cases for statistics calculation functionality."""
    
    def test_generate_statistics_all_successful(self):
        """Test statistics generation with all successful queries."""
        results = {
            "MAD": self.weather_success,
            "BCN": self.weather_cached,
            "LHR": WeatherData(
                temperature=15.0, description="overcast", humidity=80,
                wind_speed=4.5, timestamp=datetime.now(), status=WeatherStatus.SUCCESS
            )
        }
        
        stats = self.generator.generate_statistics(results, 30.5, cache_hits=1)
        
        assert stats.total_airports == 3
        assert stats.successful_queries == 3  # All successful (including cached)
        assert stats.failed_queries == 0
        assert stats.cached_queries == 1
        assert stats.processing_time == 30.5
        assert stats.cache_hit_rate == pytest.approx(33.33, rel=1e-2)
    
    def test_generate_statistics_mixed_results(self):
        """Test statistics generation with mixed success/failure results."""
        results = {
            "MAD": self.weather_success,
            "BCN": self.weather_error,
            "LHR": None,  # No data
            "CDG": self.weather_cached
        }
        
        stats = self.generator.generate_statistics(results, 60.0)
        
        assert stats.total_airports == 4
        assert stats.successful_queries == 2  # Success + cached
        assert stats.failed_queries == 2     # Error + None
        assert stats.cached_queries == 1
        assert stats.processing_time == 60.0
        assert stats.cache_hit_rate == 25.0
    
    def test_generate_statistics_empty_results(self):
        """Test statistics generation with empty results."""
        results = {}
        
        stats = self.generator.generate_statistics(results, 0.0)
        
        assert stats.total_airports == 0
        assert stats.successful_queries == 0
        assert stats.failed_queries == 0
        assert stats.cached_queries == 0
        assert stats.processing_time == 0.0
        assert stats.cache_hit_rate == 0.0
    
    def test_generate_statistics_all_failed(self):
        """Test statistics generation with all failed queries."""
        results = {
            "MAD": self.weather_error,
            "BCN": None,
            "LHR": WeatherData(
                temperature=0.0, description="", humidity=0,
                wind_speed=0.0, timestamp=datetime.now(), 
                status=WeatherStatus.NOT_AVAILABLE,
                error_message="Service unavailable"
            )
        }
        
        stats = self.generator.generate_statistics(results, 15.0)
        
        assert stats.total_airports == 3
        assert stats.successful_queries == 0
        assert stats.failed_queries == 3
        assert stats.cached_queries == 0
        assert stats.processing_time == 15.0
        assert stats.cache_hit_rate == 0.0
    
    def test_calculate_processing_metrics(self):
        """Test processing time calculation."""
        start_time = datetime(2024, 3, 15, 10, 0, 0)
        end_time = datetime(2024, 3, 15, 10, 2, 30)  # 2 minutes 30 seconds later
        
        processing_time = self.generator.calculate_processing_metrics(start_time, end_time)
        
        assert processing_time == 150.0  # 2.5 minutes = 150 seconds
    
    def test_calculate_processing_metrics_same_time(self):
        """Test processing time calculation with same start and end time."""
        timestamp = datetime(2024, 3, 15, 10, 0, 0)
        
        processing_time = self.generator.calculate_processing_metrics(timestamp, timestamp)
        
        assert processing_time == 0.0


class TestReportGeneration(TestWeatherReportGenerator):
    """Test cases for complete report generation functionality."""
    
    @patch('src.report_generator.Console')
    def test_generate_terminal_report_complete(self, mock_console_class):
        """Test complete terminal report generation."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        
        # Create new generator to use mocked console
        generator = WeatherReportGenerator()
        
        results = {
            "MAD": self.weather_success,
            "BCN": self.weather_cached
        }
        airports = [self.airport_mad, self.airport_bcn]
        stats = ReportStats(
            total_airports=2,
            successful_queries=2,
            failed_queries=0,
            cached_queries=1,
            processing_time=25.0,
            cache_hit_rate=50.0
        )
        
        generator.generate_terminal_report(results, airports, stats)
        
        # Verify console.print was called multiple times
        assert mock_console.print.call_count >= 3  # Header, table, stats
    
    @patch('src.report_generator.Console')
    def test_generate_terminal_report_no_stats(self, mock_console_class):
        """Test terminal report generation without statistics."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        
        generator = WeatherReportGenerator()
        
        results = {"MAD": self.weather_success}
        airports = [self.airport_mad]
        
        generator.generate_terminal_report(results, airports, stats=None)
        
        # Should still print header and table, but no stats
        assert mock_console.print.call_count >= 2
    
    @patch('src.report_generator.Console')
    def test_display_processing_summary(self, mock_console_class):
        """Test processing summary display."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        
        generator = WeatherReportGenerator()
        
        stats = ReportStats(
            total_airports=5,
            successful_queries=4,
            failed_queries=1,
            cached_queries=2,
            processing_time=42.5,
            cache_hit_rate=40.0
        )
        
        generator.display_processing_summary(stats)
        
        # Verify console.print was called for summary
        assert mock_console.print.call_count >= 2


class TestReportStatsDataclass:
    """Test cases for ReportStats dataclass."""
    
    def test_report_stats_creation(self):
        """Test ReportStats dataclass creation and attributes."""
        stats = ReportStats(
            total_airports=10,
            successful_queries=8,
            failed_queries=2,
            cached_queries=3,
            processing_time=45.67,
            cache_hit_rate=30.0
        )
        
        assert stats.total_airports == 10
        assert stats.successful_queries == 8
        assert stats.failed_queries == 2
        assert stats.cached_queries == 3
        assert stats.processing_time == 45.67
        assert stats.cache_hit_rate == 30.0
    
    def test_report_stats_equality(self):
        """Test ReportStats equality comparison."""
        stats1 = ReportStats(
            total_airports=5,
            successful_queries=4,
            failed_queries=1,
            cached_queries=2,
            processing_time=30.0,
            cache_hit_rate=40.0
        )
        
        stats2 = ReportStats(
            total_airports=5,
            successful_queries=4,
            failed_queries=1,
            cached_queries=2,
            processing_time=30.0,
            cache_hit_rate=40.0
        )
        
        assert stats1 == stats2


class TestEdgeCases(TestWeatherReportGenerator):
    """Test cases for edge cases and error conditions."""
    
    def test_format_table_with_very_long_airport_name(self):
        """Test table formatting with very long airport name."""
        long_name_airport = Airport(
            iata_code="TST",
            name="This Is A Very Long Airport Name That Should Be Truncated Properly",
            latitude=0.0,
            longitude=0.0
        )
        
        results = {"TST": self.weather_success}
        airports = [long_name_airport]
        
        table = self.generator._format_weather_table(results, airports)
        
        # Should handle long names gracefully
        assert len(table.rows) == 1
    
    def test_format_table_with_very_long_error_message(self):
        """Test table formatting with very long error message."""
        long_error_weather = WeatherData(
            temperature=0.0,
            description="",
            humidity=0,
            wind_speed=0.0,
            timestamp=datetime.now(),
            status=WeatherStatus.ERROR,
            error_message="This is a very long error message that should be truncated to fit in the table properly without breaking the layout"
        )
        
        results = {"MAD": long_error_weather}
        airports = [self.airport_mad]
        
        table = self.generator._format_weather_table(results, airports)
        
        # Should handle long error messages gracefully
        assert len(table.rows) == 1
    
    def test_statistics_with_zero_division_protection(self):
        """Test statistics calculation protects against zero division."""
        # Empty results should not cause division by zero
        results = {}
        
        stats = self.generator.generate_statistics(results, 0.0)
        
        assert stats.cache_hit_rate == 0.0  # Should not raise ZeroDivisionError
    
    def test_format_weather_table_with_none_weather_data(self):
        """Test table formatting when weather data is None."""
        results = {
            "MAD": None,
            "BCN": self.weather_success
        }
        airports = [self.airport_mad, self.airport_bcn]
        
        table = self.generator._format_weather_table(results, airports)
        
        # Should handle None weather data gracefully
        assert len(table.rows) == 2
    
    def test_string_table_with_missing_weather_data(self):
        """Test string table formatting with missing weather data."""
        weather_results = [
            WeatherResult(
                airport=self.airport_mad,
                origin_weather=None,
                destination_weather=None,
                flight_info=self.flight_info
            )
        ]
        
        table_string = self.generator.format_weather_table(weather_results)
        
        # Should handle missing weather data
        assert "N/A" in table_string
        assert "No disponible" in table_string
        assert "Error" in table_string


if __name__ == "__main__":
    pytest.main([__file__])