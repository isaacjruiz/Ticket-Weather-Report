"""
End-to-end tests for the Weather Report System CLI.

These tests verify the complete workflow from CLI invocation to report generation
using a small test dataset and various CLI options.
"""

import asyncio
import os
import tempfile
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from click.testing import CliRunner
import pandas as pd
from datetime import datetime

# Import CLI and related modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from cli import main, process_weather_report
from models import WeatherData, WeatherStatus, Airport, ErrorTypes


class TestEndToEnd:
    """End-to-end tests for the complete weather report system."""
    
    @pytest.fixture
    def test_dataset_csv(self):
        """Create a small test dataset CSV file."""
        test_data = {
            'origin_iata_code': ['JFK', 'LAX', 'ORD', 'JFK', 'LAX'],
            'origin_name': ['John F Kennedy Intl', 'Los Angeles Intl', 'Chicago O\'Hare Intl', 
                           'John F Kennedy Intl', 'Los Angeles Intl'],
            'origin_latitude': [40.6413, 33.9425, 41.9742, 40.6413, 33.9425],
            'origin_longitude': [-73.7781, -118.4081, -87.9073, -73.7781, -118.4081],
            'destination_iata_code': ['LAX', 'JFK', 'LAX', 'ORD', 'ORD'],
            'destination_name': ['Los Angeles Intl', 'John F Kennedy Intl', 'Los Angeles Intl',
                               'Chicago O\'Hare Intl', 'Chicago O\'Hare Intl'],
            'destination_latitude': [33.9425, 40.6413, 33.9425, 41.9742, 41.9742],
            'destination_longitude': [-118.4081, -73.7781, -118.4081, -87.9073, -87.9073],
            'airline': ['AA', 'UA', 'DL', 'AA', 'UA'],
            'flight_num': ['AA100', 'UA200', 'DL300', 'AA101', 'UA201']
        }
        
        df = pd.DataFrame(test_data)
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()
        
        yield temp_file.name
        
        # Cleanup
        os.unlink(temp_file.name)
    
    @pytest.fixture
    def mock_weather_data(self):
        """Mock weather data for testing."""
        return WeatherData(
            temperature=22.5,
            description="Clear sky",
            humidity=65,
            wind_speed=3.2,
            timestamp=datetime.now(),
            status=WeatherStatus.SUCCESS
        )
    
    def test_cli_basic_execution(self, test_dataset_csv, mock_weather_data):
        """Test basic CLI execution with minimal parameters - requirement 7.1"""
        runner = CliRunner()
        
        # Mock the weather service to avoid real API calls
        with patch('cli.WeatherService') as mock_service_class:
            # Create a proper async context manager mock
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock the async context manager methods
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            
            # Mock weather results for 3 unique airports (JFK, LAX, ORD)
            mock_service.get_weather_for_airports.return_value = {
                'JFK': mock_weather_data,
                'LAX': mock_weather_data,
                'ORD': mock_weather_data
            }
            
            # Mock get_processing_statistics as a regular method (not async)
            mock_service.get_processing_statistics = MagicMock(return_value={
                'airports_with_weather': 3,
                'airports_without_weather': 0,
                'cached_requests': 0,
                'success_rate_percent': 100.0,
                'cache_hit_rate_percent': 0.0
            })
            
            # Execute CLI command
            result = runner.invoke(main, [
                test_dataset_csv,
                '--api-key', 'test_api_key_12345'
            ])
            
            # Verify successful execution
            assert result.exit_code == 0
            assert "Weather Report System" in result.output
            assert "Processing completed successfully" in result.output
    
    def test_cli_with_all_options(self, test_dataset_csv, mock_weather_data):
        """Test CLI with all available options - requirement 7.2"""
        runner = CliRunner()
        
        with patch('cli.WeatherService') as mock_service_class:
            # Create a proper async context manager mock
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock the async context manager methods
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            
            mock_service.get_weather_for_airports.return_value = {
                'JFK': mock_weather_data,
                'LAX': mock_weather_data,
                'ORD': mock_weather_data
            }
            
            # Mock get_processing_statistics as a regular method (not async)
            mock_service.get_processing_statistics = MagicMock(return_value={
                'airports_with_weather': 3,
                'airports_without_weather': 0,
                'cached_requests': 1,
                'success_rate_percent': 100.0,
                'cache_hit_rate_percent': 33.3
            })
            
            # Execute CLI with all options
            result = runner.invoke(main, [
                test_dataset_csv,
                '--api-key', 'test_api_key_12345',
                '--concurrency', '5',
                '--timeout', '45',
                '--verbose'
            ])
            
            # Verify successful execution
            assert result.exit_code == 0
            assert "Weather Report System" in result.output
            assert "Configuration:" in result.output  # Verbose output
            assert "Concurrency: 5" in result.output
            assert "Timeout: 45s" in result.output
            assert "Processing completed successfully" in result.output
    
    def test_cli_with_environment_variable(self, test_dataset_csv, mock_weather_data):
        """Test CLI using environment variable for API key - requirement 7.2"""
        runner = CliRunner()
        
        with patch('cli.WeatherService') as mock_service_class:
            # Create a proper async context manager mock
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock the async context manager methods
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            
            mock_service.get_weather_for_airports.return_value = {
                'JFK': mock_weather_data,
                'LAX': mock_weather_data,
                'ORD': mock_weather_data
            }
            
            # Mock get_processing_statistics as a regular method (not async)
            mock_service.get_processing_statistics = MagicMock(return_value={
                'airports_with_weather': 3,
                'airports_without_weather': 0,
                'cached_requests': 0,
                'success_rate_percent': 100.0,
                'cache_hit_rate_percent': 0.0
            })
            
            # Execute CLI with environment variable
            result = runner.invoke(main, [test_dataset_csv], 
                                 env={'OPENWEATHER_API_KEY': 'env_test_key_12345'})
            
            # Verify successful execution
            assert result.exit_code == 0
            assert "Processing completed successfully" in result.output
    
    def test_cli_invalid_csv_file(self):
        """Test CLI with invalid CSV file - requirement 7.1"""
        runner = CliRunner()
        
        # Test with non-existent file
        result = runner.invoke(main, [
            'non_existent_file.csv',
            '--api-key', 'test_api_key_12345'
        ])
        
        assert result.exit_code != 0
        assert "does not exist" in result.output
    
    def test_cli_invalid_api_key(self, test_dataset_csv):
        """Test CLI with invalid API key - requirement 7.1"""
        runner = CliRunner()
        
        # Test with placeholder API key
        result = runner.invoke(main, [
            test_dataset_csv,
            '--api-key', 'your_api_key'
        ])
        
        assert result.exit_code != 0
        assert "Please provide a valid API key" in result.output
    
    def test_cli_invalid_concurrency(self, test_dataset_csv):
        """Test CLI with invalid concurrency values - requirement 7.2"""
        runner = CliRunner()
        
        # Test with concurrency too low
        result = runner.invoke(main, [
            test_dataset_csv,
            '--api-key', 'test_api_key_12345',
            '--concurrency', '0'
        ])
        
        assert result.exit_code != 0
        assert "Concurrency must be at least 1" in result.output
        
        # Test with concurrency too high
        result = runner.invoke(main, [
            test_dataset_csv,
            '--api-key', 'test_api_key_12345',
            '--concurrency', '100'
        ])
        
        assert result.exit_code != 0
        assert "Concurrency should not exceed 50" in result.output
    
    def test_cli_invalid_timeout(self, test_dataset_csv):
        """Test CLI with invalid timeout values - requirement 7.2"""
        runner = CliRunner()
        
        # Test with timeout too low
        result = runner.invoke(main, [
            test_dataset_csv,
            '--api-key', 'test_api_key_12345',
            '--timeout', '2'
        ])
        
        assert result.exit_code != 0
        assert "Timeout must be at least 5 seconds" in result.output
        
        # Test with timeout too high
        result = runner.invoke(main, [
            test_dataset_csv,
            '--api-key', 'test_api_key_12345',
            '--timeout', '400'
        ])
        
        assert result.exit_code != 0
        assert "Timeout should not exceed 300 seconds" in result.output
    
    def test_cli_with_partial_weather_failures(self, test_dataset_csv):
        """Test CLI handling partial weather API failures - requirement 7.2"""
        runner = CliRunner()
        
        with patch('cli.WeatherService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock the async context manager methods
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            
            # Mock partial failures - only JFK and LAX succeed, ORD fails
            mock_service.get_weather_for_airports.return_value = {
                'JFK': WeatherData(
                    temperature=22.5,
                    description="Clear sky",
                    humidity=65,
                    wind_speed=3.2,
                    timestamp=datetime.now(),
                    status=WeatherStatus.SUCCESS
                ),
                'LAX': WeatherData(
                    temperature=25.0,
                    description="Partly cloudy",
                    humidity=70,
                    wind_speed=2.8,
                    timestamp=datetime.now(),
                    status=WeatherStatus.SUCCESS
                ),
                'ORD': WeatherData(
                    temperature=0.0,
                    description="",
                    humidity=0,
                    wind_speed=0.0,
                    timestamp=datetime.now(),
                    status=WeatherStatus.ERROR,
                    error_message="API rate limit exceeded",
                    error_type=ErrorTypes.RATE_LIMIT_ERROR
                )
            }
            
            # Mock get_processing_statistics as a regular method (not async)
            mock_service.get_processing_statistics = MagicMock(return_value={
                'airports_with_weather': 2,
                'airports_without_weather': 1,
                'cached_requests': 0,
                'success_rate_percent': 66.7,
                'cache_hit_rate_percent': 0.0
            })
            
            # Execute CLI command
            result = runner.invoke(main, [
                test_dataset_csv,
                '--api-key', 'test_api_key_12345',
                '--verbose'
            ])
            
            # Verify execution completes despite partial failures
            assert result.exit_code == 0
            assert "Processing completed successfully" in result.output
            assert "Weather data retrieved: 2 successful, 1 failed" in result.output
    
    @pytest.mark.asyncio
    async def test_process_weather_report_function(self, test_dataset_csv, mock_weather_data):
        """Test the main async processing function directly - requirement 7.1, 7.2"""
        
        with patch('cli.WeatherService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock the async context manager methods
            mock_service.__aenter__.return_value = mock_service
            mock_service.__aexit__.return_value = None
            
            mock_service.get_weather_for_airports.return_value = {
                'JFK': mock_weather_data,
                'LAX': mock_weather_data,
                'ORD': mock_weather_data
            }
            
            # Mock get_processing_statistics as a regular method (not async)
            mock_service.get_processing_statistics = MagicMock(return_value={
                'airports_with_weather': 3,
                'airports_without_weather': 0,
                'cached_requests': 0,
                'success_rate_percent': 100.0,
                'cache_hit_rate_percent': 0.0
            })
            
            # Mock the report generator to avoid console output during tests
            with patch('cli.WeatherReportGenerator') as mock_report_gen:
                mock_report_instance = mock_report_gen.return_value
                mock_report_instance.generate_statistics.return_value = MagicMock(
                    total_airports=3,
                    successful_requests=3,
                    failed_requests=0,
                    cache_hits=0,
                    processing_time=1.5
                )
                
                # Test the async function directly
                await process_weather_report(
                    dataset_file=test_dataset_csv,
                    api_key='test_api_key_12345',
                    concurrency=10,
                    timeout=30,
                    verbose=True
                )
                
                # Verify the weather service was called correctly
                mock_service.get_weather_for_airports.assert_called_once()
                mock_report_instance.generate_terminal_report.assert_called_once()
    
    def test_cli_keyboard_interrupt(self, test_dataset_csv):
        """Test CLI handling of keyboard interrupt - requirement 7.2"""
        runner = CliRunner()
        
        with patch('cli.process_weather_report') as mock_process:
            mock_process.side_effect = KeyboardInterrupt()
            
            result = runner.invoke(main, [
                test_dataset_csv,
                '--api-key', 'test_api_key_12345'
            ])
            
            assert result.exit_code == 1
            assert "Processing interrupted by user" in result.output
    
    def test_cli_version_option(self):
        """Test CLI version option - requirement 7.2"""
        runner = CliRunner()
        
        result = runner.invoke(main, ['--version'])
        
        assert result.exit_code == 0
        assert "Weather Report System" in result.output
        assert "1.0.0" in result.output
    
    def test_cli_help_option(self):
        """Test CLI help option - requirement 7.2"""
        runner = CliRunner()
        
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert "Process flight dataset and generate weather reports" in result.output
        assert "--api-key" in result.output
        assert "--concurrency" in result.output
        assert "--timeout" in result.output
        assert "--verbose" in result.output
    
    def test_empty_csv_file(self):
        """Test CLI with empty CSV file - requirement 7.1"""
        runner = CliRunner()
        
        # Create empty CSV file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_file.close()
        
        try:
            result = runner.invoke(main, [
                temp_file.name,
                '--api-key', 'test_api_key_12345'
            ])
            
            # Should fail due to empty dataset
            assert result.exit_code != 0 or "Error loading dataset" in result.output
            
        finally:
            os.unlink(temp_file.name)
    
    def test_malformed_csv_file(self):
        """Test CLI with malformed CSV file - requirement 7.1"""
        runner = CliRunner()
        
        # Create malformed CSV file (missing required columns)
        malformed_data = {
            'wrong_column1': ['A', 'B'],
            'wrong_column2': ['C', 'D']
        }
        
        df = pd.DataFrame(malformed_data)
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()
        
        try:
            result = runner.invoke(main, [
                temp_file.name,
                '--api-key', 'test_api_key_12345'
            ])
            
            # Should fail due to invalid dataset structure
            assert result.exit_code != 0 or "Error loading dataset" in result.output
            
        finally:
            os.unlink(temp_file.name)
    
    def test_cli_non_csv_file(self):
        """Test CLI with non-CSV file - requirement 7.1"""
        runner = CliRunner()
        
        # Create a text file instead of CSV
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        temp_file.write("This is not a CSV file")
        temp_file.close()
        
        try:
            result = runner.invoke(main, [
                temp_file.name,
                '--api-key', 'test_api_key_12345'
            ])
            
            assert result.exit_code != 0
            assert "File must be a CSV file" in result.output
            
        finally:
            os.unlink(temp_file.name)
    
    def test_cli_missing_api_key(self, test_dataset_csv):
        """Test CLI without API key - requirement 7.1"""
        runner = CliRunner()
        
        result = runner.invoke(main, [test_dataset_csv])
        
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()


if __name__ == '__main__':
    pytest.main([__file__])