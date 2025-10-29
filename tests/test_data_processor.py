"""
Unit tests for FlightDataProcessor.

Tests CSV data validation and unique airport extraction functionality.
Requirements: 1.1, 1.3
"""

import pytest
import pandas as pd
import tempfile
import os
from unittest.mock import patch, MagicMock
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.data_processor import FlightDataProcessor
from src.models import Airport


class TestFlightDataProcessor:
    """Test cases for FlightDataProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = FlightDataProcessor()
        
        # Sample valid CSV data
        self.valid_data = {
            'origin_iata_code': ['JFK', 'LAX', 'ORD'],
            'origin_name': ['John F Kennedy Intl', 'Los Angeles Intl', 'Chicago O\'Hare Intl'],
            'origin_latitude': [40.6413, 33.9425, 41.9742],
            'origin_longitude': [-73.7781, -118.4081, -87.9073],
            'destination_iata_code': ['LAX', 'JFK', 'LAX'],
            'destination_name': ['Los Angeles Intl', 'John F Kennedy Intl', 'Los Angeles Intl'],
            'destination_latitude': [33.9425, 40.6413, 33.9425],
            'destination_longitude': [-118.4081, -73.7781, -118.4081],
            'airline': ['American', 'Delta', 'United'],
            'flight_num': ['AA123', 'DL456', 'UA789']
        }
        
        # Sample data with duplicates for testing unique extraction
        self.duplicate_data = {
            'origin_iata_code': ['JFK', 'JFK', 'LAX'],
            'origin_name': ['John F Kennedy Intl', 'John F Kennedy Intl', 'Los Angeles Intl'],
            'origin_latitude': [40.6413, 40.6413, 33.9425],
            'origin_longitude': [-73.7781, -73.7781, -118.4081],
            'destination_iata_code': ['LAX', 'LAX', 'JFK'],
            'destination_name': ['Los Angeles Intl', 'Los Angeles Intl', 'John F Kennedy Intl'],
            'destination_latitude': [33.9425, 33.9425, 40.6413],
            'destination_longitude': [-118.4081, -118.4081, -73.7781],
            'airline': ['American', 'American', 'United'],
            'flight_num': ['AA123', 'AA124', 'UA789']
        }
    
    def create_temp_csv(self, data):
        """Create a temporary CSV file with given data."""
        df = pd.DataFrame(data)
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()
        return temp_file.name
    
    def test_load_dataset_valid_file(self):
        """Test loading a valid CSV dataset."""
        temp_file = self.create_temp_csv(self.valid_data)
        
        try:
            df = self.processor.load_dataset(temp_file)
            
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 3
            assert all(col in df.columns for col in self.processor.required_columns)
            
        finally:
            os.unlink(temp_file)
    
    def test_load_dataset_file_not_found(self):
        """Test loading a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Dataset file not found"):
            self.processor.load_dataset("non_existent_file.csv")
    
    def test_load_dataset_empty_file(self):
        """Test loading an empty CSV file raises EmptyDataError."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_file.close()
        
        try:
            with pytest.raises(pd.errors.EmptyDataError):
                self.processor.load_dataset(temp_file.name)
        finally:
            os.unlink(temp_file.name)
    
    def test_load_dataset_invalid_structure(self):
        """Test loading CSV with missing required columns raises ValueError."""
        invalid_data = {'col1': [1, 2, 3], 'col2': [4, 5, 6]}
        temp_file = self.create_temp_csv(invalid_data)
        
        try:
            with pytest.raises(ValueError, match="Invalid dataset structure"):
                self.processor.load_dataset(temp_file)
        finally:
            os.unlink(temp_file)
    
    def test_validate_dataset_structure_valid(self):
        """Test validation of valid dataset structure."""
        df = pd.DataFrame(self.valid_data)
        assert self.processor.validate_dataset_structure(df) is True
    
    def test_validate_dataset_structure_empty(self):
        """Test validation of empty dataset returns False."""
        df = pd.DataFrame()
        assert self.processor.validate_dataset_structure(df) is False
    
    def test_validate_dataset_structure_missing_columns(self):
        """Test validation fails when required columns are missing."""
        incomplete_data = {
            'origin_iata_code': ['JFK'],
            'origin_name': ['John F Kennedy Intl']
            # Missing other required columns
        }
        df = pd.DataFrame(incomplete_data)
        assert self.processor.validate_dataset_structure(df) is False
    
    def test_validate_dataset_structure_non_numeric_coordinates(self):
        """Test validation fails when coordinate columns contain non-numeric data."""
        invalid_data = self.valid_data.copy()
        invalid_data['origin_latitude'] = ['invalid', 'data', 'here']
        df = pd.DataFrame(invalid_data)
        assert self.processor.validate_dataset_structure(df) is False
    
    def test_extract_unique_airports_no_duplicates(self):
        """Test extracting unique airports from dataset without duplicates."""
        df = pd.DataFrame(self.valid_data)
        airports = self.processor.extract_unique_airports(df)
        
        # Should have 3 unique airports: JFK, LAX, ORD
        assert len(airports) == 3
        
        # Check that all airports are Airport objects
        assert all(isinstance(airport, Airport) for airport in airports)
        
        # Check specific airports exist
        airport_codes = {airport.iata_code for airport in airports}
        expected_codes = {'JFK', 'LAX', 'ORD'}
        assert airport_codes == expected_codes
    
    def test_extract_unique_airports_with_duplicates(self):
        """Test extracting unique airports removes duplicates correctly."""
        df = pd.DataFrame(self.duplicate_data)
        airports = self.processor.extract_unique_airports(df)
        
        # Should have only 2 unique airports: JFK, LAX (duplicates removed)
        assert len(airports) == 2
        
        airport_codes = {airport.iata_code for airport in airports}
        expected_codes = {'JFK', 'LAX'}
        assert airport_codes == expected_codes
        
        # Verify airport details are correct
        jfk_airport = next(a for a in airports if a.iata_code == 'JFK')
        assert jfk_airport.name == 'John F Kennedy Intl'
        assert jfk_airport.latitude == 40.6413
        assert jfk_airport.longitude == -73.7781
    
    def test_extract_unique_airports_coordinates_conversion(self):
        """Test that coordinates are properly converted to float."""
        df = pd.DataFrame(self.valid_data)
        airports = self.processor.extract_unique_airports(df)
        
        for airport in airports:
            assert isinstance(airport.latitude, float)
            assert isinstance(airport.longitude, float)
    
    def test_clean_dataset_removes_missing_iata_codes(self):
        """Test that rows with missing IATA codes are removed."""
        data_with_missing = self.valid_data.copy()
        data_with_missing['origin_iata_code'][0] = None
        df = pd.DataFrame(data_with_missing)
        
        cleaned_df = self.processor._clean_dataset(df)
        assert len(cleaned_df) == 2  # One row should be removed
    
    def test_clean_dataset_removes_invalid_coordinates(self):
        """Test that rows with invalid coordinates are removed."""
        data_with_invalid_coords = self.valid_data.copy()
        data_with_invalid_coords['origin_latitude'][0] = 'invalid'
        df = pd.DataFrame(data_with_invalid_coords)
        
        cleaned_df = self.processor._clean_dataset(df)
        assert len(cleaned_df) == 2  # One row should be removed
    
    def test_clean_dataset_validates_coordinate_ranges(self):
        """Test that coordinates outside valid ranges are removed."""
        data_with_out_of_range = self.valid_data.copy()
        data_with_out_of_range['origin_latitude'][0] = 95.0  # Invalid latitude > 90
        df = pd.DataFrame(data_with_out_of_range)
        
        cleaned_df = self.processor._clean_dataset(df)
        assert len(cleaned_df) == 2  # One row should be removed
    
    def test_clean_dataset_strips_whitespace(self):
        """Test that whitespace is stripped from string columns."""
        data_with_whitespace = self.valid_data.copy()
        data_with_whitespace['origin_iata_code'][0] = '  JFK  '
        data_with_whitespace['airline'][0] = '  American  '
        df = pd.DataFrame(data_with_whitespace)
        
        cleaned_df = self.processor._clean_dataset(df)
        assert cleaned_df['origin_iata_code'].iloc[0] == 'JFK'
        assert cleaned_df['airline'].iloc[0] == 'American'
    
    def test_required_columns_property(self):
        """Test that required columns are properly defined."""
        expected_columns = {
            'origin_iata_code', 'origin_name', 'origin_latitude', 'origin_longitude',
            'destination_iata_code', 'destination_name', 'destination_latitude', 
            'destination_longitude', 'airline', 'flight_num'
        }
        assert self.processor.required_columns == expected_columns