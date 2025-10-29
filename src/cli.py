"""
CLI interface for the Weather Report System.

This module provides the main command-line interface using Click for processing
flight datasets and generating weather reports with configurable options.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
import pandas as pd
from rich.console import Console
from rich.logging import RichHandler

# Load environment variables from .env if present during normal CLI usage.
# Skip auto-loading during pytest to keep tests deterministic (e.g., missing API key tests).
if 'pytest' not in sys.modules:
    load_dotenv()

# Add the src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from models import Airport, WeatherData, WeatherStatus
from data_processor import FlightDataProcessor
from weather_service import WeatherService
from report_generator import WeatherReportGenerator, ReportStats


# Initialize Rich console for CLI output
console = Console()


def setup_logging(verbose: bool) -> None:
    """
    Configure logging based on verbosity level.
    
    Args:
        verbose: If True, enable debug logging; otherwise use info level
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Configure rich handler for beautiful logging
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )
    
    # Set specific loggers to appropriate levels
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def validate_csv_file(ctx, param, value: str) -> str:
    """
    Validate that the CSV file exists and is readable.
    
    Args:
        ctx: Click context
        param: Click parameter
        value: File path value
        
    Returns:
        Validated file path
        
    Raises:
        click.BadParameter: If file doesn't exist or isn't readable
    """
    if not value:
        raise click.BadParameter("CSV file path is required")
    
    file_path = Path(value)
    
    if not file_path.exists():
        raise click.BadParameter(f"File does not exist: {value}")
    
    if not file_path.is_file():
        raise click.BadParameter(f"Path is not a file: {value}")
    
    if not file_path.suffix.lower() == '.csv':
        raise click.BadParameter(f"File must be a CSV file: {value}")
    
    try:
        # Test if file is readable
        with open(file_path, 'r') as f:
            f.read(1)
    except PermissionError:
        raise click.BadParameter(f"File is not readable: {value}")
    except Exception as e:
        raise click.BadParameter(f"Error accessing file {value}: {str(e)}")
    
    return str(file_path.absolute())


def validate_api_key(ctx, param, value: str) -> str:
    """
    Validate the OpenWeatherMap API key.
    
    Args:
        ctx: Click context
        param: Click parameter
        value: API key value
        
    Returns:
        Validated API key
        
    Raises:
        click.BadParameter: If API key is invalid
    """
    if not value:
        raise click.BadParameter("API key is required")
    
    # Basic validation - OpenWeatherMap API keys are typically 32 characters
    if len(value) < 10:
        raise click.BadParameter("API key appears to be too short")
    
    # Check for common placeholder values
    placeholder_values = ['your_api_key', 'api_key_here', 'replace_me', 'xxx']
    if value.lower() in placeholder_values:
        raise click.BadParameter("Please provide a valid API key, not a placeholder")
    
    return value


def validate_concurrency(ctx, param, value: int) -> int:
    """
    Validate concurrency parameter.
    
    Args:
        ctx: Click context
        param: Click parameter
        value: Concurrency value
        
    Returns:
        Validated concurrency value
        
    Raises:
        click.BadParameter: If concurrency is invalid
    """
    if value < 1:
        raise click.BadParameter("Concurrency must be at least 1")
    
    if value > 50:
        raise click.BadParameter("Concurrency should not exceed 50 to avoid overwhelming APIs")
    
    return value


def validate_timeout(ctx, param, value: int) -> int:
    """
    Validate timeout parameter.
    
    Args:
        ctx: Click context
        param: Click parameter
        value: Timeout value
        
    Returns:
        Validated timeout value
        
    Raises:
        click.BadParameter: If timeout is invalid
    """
    if value < 5:
        raise click.BadParameter("Timeout must be at least 5 seconds")
    
    if value > 300:
        raise click.BadParameter("Timeout should not exceed 300 seconds (5 minutes)")
    
    return value


@click.command()
@click.argument(
    'dataset_file', 
    type=click.Path(exists=True),
    callback=validate_csv_file,
    metavar='CSV_FILE'
)
@click.option(
    '--api-key', 
    required=True,
    callback=validate_api_key,
    help='OpenWeatherMap API key for weather data retrieval',
    envvar='OPENWEATHER_API_KEY'
)
@click.option(
    '--concurrency', 
    default=10,
    callback=validate_concurrency,
    help='Maximum number of concurrent API requests (default: 10)',
    show_default=True,
    envvar='WEATHER_CONCURRENCY'
)
@click.option(
    '--timeout', 
    default=30,
    callback=validate_timeout,
    help='Request timeout in seconds (default: 30)',
    show_default=True,
    envvar='WEATHER_TIMEOUT'
)
@click.option(
    '--verbose', 
    is_flag=True,
    help='Enable verbose output with detailed progress information',
    envvar='WEATHER_VERBOSE'
)

@click.option(
    '--cache-path',
    default=None,
    help='Path to SQLite cache file to persist weather cache between runs',
    envvar='WEATHER_CACHE_PATH'
)
@click.option(
    '--clear-cache',
    is_flag=True,
    help='Clear the weather cache before processing (uses --cache-path when provided)',
    envvar='WEATHER_CLEAR_CACHE'
)

@click.version_option(version='1.0.0', prog_name='Weather Report System')
def main(dataset_file: str, api_key: str, concurrency: int, timeout: int, verbose: bool, cache_path: Optional[str], clear_cache: bool) -> None:
    """
    Process flight dataset and generate weather reports.
    
    This tool processes a CSV file containing flight data to generate comprehensive
    weather reports for origin and destination airports. It fetches current weather
    data from OpenWeatherMap API with intelligent caching and concurrent processing.
    
    CSV_FILE: Path to the flight dataset CSV file to process
    
    Example usage:
    
        weather-report flights.csv --api-key YOUR_API_KEY
        
        weather-report flights.csv --api-key YOUR_API_KEY --concurrency 15 --verbose
        
        OPENWEATHER_API_KEY=your_key weather-report flights.csv
    """
    # Setup logging based on verbosity
    setup_logging(verbose)
    
    # Display startup banner
    console.print("\n[bold blue]🌤️  Weather Report System v1.0.0[/bold blue]")
    console.print("[dim]Processing flight dataset for weather information...[/dim]\n")
    
    if verbose:
        console.print(f"[dim]Configuration:[/dim]")
        console.print(f"[dim]  • Dataset file: {dataset_file}[/dim]")
        console.print(f"[dim]  • Concurrency: {concurrency}[/dim]")
        console.print(f"[dim]  • Timeout: {timeout}s[/dim]")
        console.print(f"[dim]  • API key: {'*' * (len(api_key) - 4) + api_key[-4:]}[/dim]\n")
        if cache_path:
            console.print(f"[dim]  • Cache path: {cache_path}[/dim]")
        if clear_cache:
            console.print(f"[dim]  • Clear cache: enabled[/dim]")
    
    try:
        # Optionally clear cache before processing
        if clear_cache:
            try:
                ws = WeatherService(
                    api_key=api_key,
                    timeout=timeout,
                    max_concurrency=concurrency,
                    cache_path=cache_path
                )
                ws.clear_cache()
                console.print("[blue]🧹 Cache cleared[/blue]" + (f" at {cache_path}" if cache_path else " (in-memory)"))
            except Exception as e:
                console.print(f"[yellow]⚠️  Failed to clear cache: {str(e)}[/yellow]")

        # Run the async main function
        asyncio.run(process_weather_report(
            dataset_file=dataset_file,
            api_key=api_key,
            concurrency=concurrency,
            timeout=timeout,
            verbose=verbose,
            cache_path=cache_path
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Processing interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {str(e)}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


async def process_weather_report(dataset_file: str, api_key: str, 
                               concurrency: int, timeout: int, verbose: bool,
                               cache_path: Optional[str] = None) -> None:
    """
    Main async function that orchestrates the weather report processing.
    
    Integrates all components to provide the complete workflow:
    1. Load and process CSV dataset
    2. Extract unique airports
    3. Fetch weather data concurrently with caching
    4. Generate and display comprehensive report
    
    Args:
        dataset_file: Path to the CSV dataset file
        api_key: OpenWeatherMap API key
        concurrency: Maximum concurrent requests
        timeout: Request timeout in seconds
        verbose: Enable verbose logging
    """
    logger = logging.getLogger(__name__)
    start_time = datetime.now()
    
    try:
        # Step 1: Initialize data processor and load dataset
        if verbose:
            console.print("[dim]📂 Loading and validating dataset...[/dim]")
        
        data_processor = FlightDataProcessor()
        
        try:
            df = data_processor.load_dataset(dataset_file)
            logger.info(f"Successfully loaded dataset with {len(df)} flight records")
            
            if verbose:
                console.print(f"[green]✓[/green] Dataset loaded: {len(df)} flight records")
                
        except Exception as e:
            console.print(f"[red]❌ Error loading dataset: {str(e)}[/red]")
            return
        
        # Step 2: Extract unique airports to avoid duplicate API calls
        if verbose:
            console.print("[dim]🏢 Extracting unique airports...[/dim]")
            
        try:
            airports = data_processor.extract_unique_airports(df)
            logger.info(f"Extracted {len(airports)} unique airports from dataset")
            
            if verbose:
                console.print(f"[green]✓[/green] Found {len(airports)} unique airports")
                
        except Exception as e:
            console.print(f"[red]❌ Error extracting airports: {str(e)}[/red]")
            return
        
        # Step 3: Initialize weather service and fetch weather data
        if verbose:
            console.print(f"[dim]🌤️  Fetching weather data (concurrency: {concurrency})...[/dim]")
        
        weather_results = {}
        
        try:
            async with WeatherService(
                api_key=api_key, 
                timeout=timeout, 
                max_concurrency=concurrency,
                cache_path=cache_path
            ) as weather_service:
                
                # Show progress for verbose mode
                if verbose:
                    console.print(f"[dim]   • Processing {len(airports)} airports...[/dim]")
                
                # Fetch weather data for all airports concurrently
                weather_results = await weather_service.get_weather_for_airports(airports)
                
                # Get processing statistics
                processing_stats = weather_service.get_processing_statistics()
                
                logger.info(f"Weather processing completed. Success rate: {processing_stats.get('success_rate_percent', 0):.1f}%")
                
                # Get detailed cache statistics
                cache_stats = weather_service.get_cache_stats()
                
                if verbose:
                    successful = processing_stats.get('airports_with_weather', 0)
                    failed = processing_stats.get('airports_without_weather', 0)
                    cached = processing_stats.get('cached_requests', 0)
                    console.print(f"[green]✓[/green] Weather data retrieved: {successful} successful, {failed} failed, {cached} from cache")
                
        except Exception as e:
            console.print(f"[red]❌ Error fetching weather data: {str(e)}[/red]")
            if verbose:
                logger.exception("Detailed error information:")
            return
        
        # Step 4: Generate and display comprehensive report
        if verbose:
            console.print("[dim]📊 Generating weather report...[/dim]")
        
        try:
            # Calculate processing time
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Initialize report generator
            report_generator = WeatherReportGenerator()
            
            # Generate statistics
            stats = report_generator.generate_statistics(
                results=weather_results,
                processing_time=processing_time,
                cache_hits=processing_stats.get('cached_requests', 0)
            )
            
            # Display the weather report with flight information
            report_generator.generate_terminal_report(
                results=weather_results,
                airports=airports,
                stats=stats,
                flight_dataset=df  # Pass the flight dataset
            )
            
            logger.info(f"Report generation completed in {processing_time:.2f} seconds")
            
            if verbose:
                console.print(f"[green]✓[/green] Report generated successfully")
                
        except Exception as e:
            console.print(f"[red]❌ Error generating report: {str(e)}[/red]")
            if verbose:
                logger.exception("Detailed error information:")
            return
        
        # Step 5: Display final summary
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        console.print(f"\n[bold green]🎉 Processing completed successfully in {total_time:.2f} seconds![/bold green]")
        
        if verbose:
            # Show detailed performance metrics
            console.print(f"[dim]Performance metrics:[/dim]")
            console.print(f"[dim]  • Total processing time: {total_time:.2f}s[/dim]")
            console.print(f"[dim]  • Average time per airport: {total_time/len(airports):.3f}s[/dim]")
            console.print(f"[dim]  • Cache hit rate: {processing_stats.get('cache_hit_rate_percent', 0):.1f}%[/dim]")
        
    except KeyboardInterrupt:
        console.print(f"\n[yellow]⚠️  Processing interrupted by user[/yellow]")
        raise
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error during processing: {str(e)}[/red]")
        if verbose:
            logger.exception("Detailed error information:")
        raise


if __name__ == '__main__':
    main()