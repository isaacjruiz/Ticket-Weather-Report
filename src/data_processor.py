"""
Flight Data Processor for Weather Report System.

This module handles loading and processing of flight dataset CSV files,
extracting unique airports and validating data structure.
"""

import pandas as pd
from typing import List, Set
try:
    from .models import Airport, FlightInfo
except ImportError:
    from models import Airport, FlightInfo


class FlightDataProcessor:
    """Processes flight dataset CSV files and extracts airport information."""
    
    def __init__(self):
        """Initialize the FlightDataProcessor."""
        self.required_columns = {
            'origin_iata_code', 'origin_name', 'origin_latitude', 'origin_longitude',
            'destination_iata_code', 'destination_name', 'destination_latitude', 
            'destination_longitude', 'airline', 'flight_num'
        }
    
    def load_dataset(self, file_path: str, chunk_size: int = 10000) -> pd.DataFrame:
        """
        Load flight dataset from CSV file with memory optimization for large files.
        
        Args:
            file_path: Path to the CSV file
            chunk_size: Size of chunks for processing large files (default: 10000)
            
        Returns:
            DataFrame containing the flight data
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            pd.errors.EmptyDataError: If the file is empty
            ValueError: If the dataset structure is invalid
        """
        try:
            # First, read a small sample to validate structure
            sample_df = pd.read_csv(file_path, nrows=100)
            
            # Validate dataset structure with sample
            if not self.validate_dataset_structure(sample_df):
                raise ValueError("Invalid dataset structure: missing required columns")
            
            # Determine optimal data types for memory efficiency
            dtypes = self._get_optimized_dtypes()
            
            # For large files, use chunked reading
            file_size = self._get_file_size(file_path)
            
            if file_size > 50 * 1024 * 1024:  # 50MB threshold
                # Process in chunks for large files
                df = self._load_large_dataset_chunked(file_path, chunk_size, dtypes)
            else:
                # Load normally for smaller files
                df = pd.read_csv(file_path, dtype=dtypes)
            
            # Clean and validate data
            df = self._clean_dataset(df)
            
            return df
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Dataset file not found: {file_path}")
        except pd.errors.EmptyDataError:
            raise pd.errors.EmptyDataError(f"Dataset file is empty: {file_path}")
        except Exception as e:
            raise ValueError(f"Error loading dataset: {str(e)}")
    
    def validate_dataset_structure(self, df: pd.DataFrame) -> bool:
        """
        Validate that the dataset has the required column structure.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if structure is valid, False otherwise
        """
        if df.empty:
            return False
            
        # Check if all required columns are present
        missing_columns = self.required_columns - set(df.columns)
        if missing_columns:
            print(f"Missing required columns: {missing_columns}")
            return False
            
        # Check if coordinate columns contain numeric data
        coordinate_columns = [
            'origin_latitude', 'origin_longitude', 
            'destination_latitude', 'destination_longitude'
        ]
        
        for col in coordinate_columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                try:
                    pd.to_numeric(df[col], errors='raise')
                except (ValueError, TypeError):
                    print(f"Column {col} contains non-numeric data")
                    return False
        
        return True
    
    def extract_unique_airports(self, df: pd.DataFrame) -> List[Airport]:
        """
        Extract unique airports from the dataset to avoid duplicates.
        
        Args:
            df: DataFrame containing flight data
            
        Returns:
            List of unique Airport objects
        """
        unique_airports = {}
        
        # Extract origin airports
        for _, row in df.iterrows():
            origin_code = row['origin_iata_code']
            if origin_code not in unique_airports:
                unique_airports[origin_code] = Airport(
                    iata_code=origin_code,
                    name=row['origin_name'],
                    latitude=float(row['origin_latitude']),
                    longitude=float(row['origin_longitude'])
                )
            
            # Extract destination airports
            dest_code = row['destination_iata_code']
            if dest_code not in unique_airports:
                unique_airports[dest_code] = Airport(
                    iata_code=dest_code,
                    name=row['destination_name'],
                    latitude=float(row['destination_latitude']),
                    longitude=float(row['destination_longitude'])
                )
        
        return list(unique_airports.values())
    
    def _clean_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean the dataset by removing invalid rows and converting data types.
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        # Remove rows with missing critical data
        df = df.dropna(subset=['origin_iata_code', 'destination_iata_code'])
        
        # Convert coordinate columns to numeric, coercing errors to NaN
        coordinate_columns = [
            'origin_latitude', 'origin_longitude', 
            'destination_latitude', 'destination_longitude'
        ]
        
        for col in coordinate_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove rows with invalid coordinates
        df = df.dropna(subset=coordinate_columns)
        
        # Validate coordinate ranges
        df = df[
            (df['origin_latitude'].between(-90, 90)) &
            (df['origin_longitude'].between(-180, 180)) &
            (df['destination_latitude'].between(-90, 90)) &
            (df['destination_longitude'].between(-180, 180))
        ]
        
        # Strip whitespace from string columns
        string_columns = ['origin_iata_code', 'origin_name', 'destination_iata_code', 
                         'destination_name', 'airline', 'flight_num']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        
        return df
    
    def _get_file_size(self, file_path: str) -> int:
        """
        Get file size in bytes.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File size in bytes
        """
        import os
        return os.path.getsize(file_path)
    
    def _get_optimized_dtypes(self) -> dict:
        """
        Get optimized data types for memory efficiency.
        
        Returns:
            Dictionary mapping column names to optimal data types
        """
        return {
            'origin_iata_code': 'category',
            'origin_name': 'string',
            'origin_latitude': 'float32',
            'origin_longitude': 'float32',
            'destination_iata_code': 'category',
            'destination_name': 'string',
            'destination_latitude': 'float32',
            'destination_longitude': 'float32',
            'airline': 'category',
            'flight_num': 'string'
        }
    
    def _load_large_dataset_chunked(self, file_path: str, chunk_size: int, dtypes: dict) -> pd.DataFrame:
        """
        Load large dataset in chunks to optimize memory usage.
        
        Args:
            file_path: Path to the CSV file
            chunk_size: Size of each chunk
            dtypes: Data types for columns
            
        Returns:
            Combined DataFrame
        """
        chunks = []
        
        # Read file in chunks
        for chunk in pd.read_csv(file_path, chunksize=chunk_size, dtype=dtypes):
            # Clean each chunk individually to save memory
            cleaned_chunk = self._clean_dataset(chunk)
            if not cleaned_chunk.empty:
                chunks.append(cleaned_chunk)
        
        # Combine all chunks
        if chunks:
            df = pd.concat(chunks, ignore_index=True)
            # Optimize memory usage after concatenation
            df = self._optimize_dataframe_memory(df)
            return df
        else:
            return pd.DataFrame()
    
    def _optimize_dataframe_memory(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Optimize DataFrame memory usage by downcasting numeric types.
        
        Args:
            df: DataFrame to optimize
            
        Returns:
            Memory-optimized DataFrame
        """
        # Downcast float columns
        float_cols = df.select_dtypes(include=['float']).columns
        for col in float_cols:
            df[col] = pd.to_numeric(df[col], downcast='float')
        
        # Downcast integer columns if any
        int_cols = df.select_dtypes(include=['int']).columns
        for col in int_cols:
            df[col] = pd.to_numeric(df[col], downcast='integer')
        
        return df