"""
Weather Report Generator for the Weather Report System.

This module provides functionality to generate formatted terminal reports
showing weather information for airports and flight statistics.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

try:
    from .models import Airport, WeatherData, WeatherResult, WeatherStatus
except ImportError:
    from models import Airport, WeatherData, WeatherResult, WeatherStatus


@dataclass
class ReportStats:
    """Statistics for the weather report generation."""
    total_airports: int
    successful_queries: int
    failed_queries: int
    cached_queries: int
    processing_time: float
    cache_hit_rate: float


class WeatherReportGenerator:
    """Generates formatted weather reports for terminal display."""
    
    def __init__(self):
        """Initialize the report generator with a Rich console."""
        self.console = Console()
    
    def generate_terminal_report(self, results: Dict[str, WeatherData], 
                               airports: List[Airport],
                               stats: Optional[ReportStats] = None,
                               flight_dataset=None) -> None:
        """
        Generate and display a complete weather report in the terminal.
        
        Args:
            results: Dictionary mapping airport codes to weather data
            airports: List of airports that were processed
            stats: Optional statistics about the processing
            flight_dataset: Optional pandas DataFrame with flight data
        """
        self.console.print("\n")
        self.console.print(Panel.fit(
            "[bold blue]🌤️  Informe Meteorológico de Aeropuertos[/bold blue]",
            box=box.DOUBLE
        ))
        
        # Generate the main weather table
        weather_table = self._format_weather_table(results, airports)
        self.console.print(weather_table)
        
        # Generate flight information if dataset provided
        if flight_dataset is not None:
            flight_summary = self._format_flight_summary(flight_dataset, results)
            self.console.print(flight_summary)
        
        # Generate statistics if provided
        if stats:
            stats_panel = self._format_statistics_panel(stats)
            self.console.print(stats_panel)
        
        self.console.print("\n")
    
    def _format_weather_table(self, results: Dict[str, WeatherData], 
                             airports: List[Airport]) -> Table:
        """
        Format weather data into a Rich table.
        
        Args:
            results: Dictionary mapping airport codes to weather data
            airports: List of airports that were processed
            
        Returns:
            Rich Table object with formatted weather data
        """
        table = Table(
            title="Información Meteorológica por Aeropuerto",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        # Add columns
        table.add_column("Código IATA", style="cyan", no_wrap=True)
        table.add_column("Nombre del Aeropuerto", style="white")
        table.add_column("Temperatura", style="yellow", justify="center")
        table.add_column("Descripción", style="green")
        table.add_column("Humedad", style="blue", justify="center")
        table.add_column("Viento", style="blue", justify="center")
        table.add_column("Estado", style="bold", justify="center")
        
        # Add rows for each airport
        for airport in airports:
            weather = results.get(airport.iata_code)
            
            if weather and weather.status == WeatherStatus.SUCCESS:
                # Successful weather data
                temp_text = f"{weather.temperature:.1f}°C"
                humidity_text = f"{weather.humidity}%"
                wind_text = f"{weather.wind_speed:.1f} m/s"
                status_text = "[green]✓ Exitoso[/green]"
                
                table.add_row(
                    airport.iata_code,
                    airport.name,
                    temp_text,
                    weather.description.title(),
                    humidity_text,
                    wind_text,
                    status_text
                )
            
            elif weather and weather.status == WeatherStatus.CACHED:
                # Cached weather data
                temp_text = f"{weather.temperature:.1f}°C"
                humidity_text = f"{weather.humidity}%"
                wind_text = f"{weather.wind_speed:.1f} m/s"
                status_text = "[blue]📋 Cache[/blue]"
                
                table.add_row(
                    airport.iata_code,
                    airport.name,
                    temp_text,
                    weather.description.title(),
                    humidity_text,
                    wind_text,
                    status_text
                )
            
            else:
                # Failed or unavailable weather data
                error_msg = "No disponible"
                if weather and weather.error_message:
                    error_msg = weather.error_message[:30] + "..." if len(weather.error_message) > 30 else weather.error_message
                
                status_text = "[red]✗ Error[/red]"
                
                table.add_row(
                    airport.iata_code,
                    airport.name,
                    "[dim]N/A[/dim]",
                    f"[dim]{error_msg}[/dim]",
                    "[dim]N/A[/dim]",
                    "[dim]N/A[/dim]",
                    status_text
                )
        
        return table
    
    def _format_statistics_panel(self, stats: ReportStats) -> Panel:
        """
        Format processing statistics into a Rich panel.
        
        Args:
            stats: Statistics about the processing
            
        Returns:
            Rich Panel object with formatted statistics
        """
        # Format processing time
        time_str = f"{stats.processing_time:.2f} segundos"
        if stats.processing_time > 60:
            minutes = int(stats.processing_time // 60)
            seconds = stats.processing_time % 60
            time_str = f"{minutes}m {seconds:.1f}s"
        
        # Create statistics text
        stats_text = Text()
        stats_text.append("📊 Estadísticas de Procesamiento\n\n", style="bold blue")
        
        stats_text.append(f"• Total de aeropuertos procesados: ", style="white")
        stats_text.append(f"{stats.total_airports}\n", style="bold cyan")
        
        stats_text.append(f"• Consultas exitosas: ", style="white")
        stats_text.append(f"{stats.successful_queries}", style="bold green")
        stats_text.append(f" ({stats.successful_queries/stats.total_airports*100:.1f}%)\n", style="green")
        
        stats_text.append(f"• Consultas fallidas: ", style="white")
        stats_text.append(f"{stats.failed_queries}", style="bold red")
        stats_text.append(f" ({stats.failed_queries/stats.total_airports*100:.1f}%)\n", style="red")
        
        stats_text.append(f"• Consultas desde caché: ", style="white")
        stats_text.append(f"{stats.cached_queries}", style="bold blue")
        stats_text.append(f" ({stats.cache_hit_rate:.1f}%)\n", style="blue")
        
        stats_text.append(f"• Tiempo total de procesamiento: ", style="white")
        stats_text.append(f"{time_str}", style="bold yellow")
        
        return Panel(
            stats_text,
            box=box.ROUNDED,
            padding=(1, 2)
        )
    
    def format_weather_table(self, data: List[WeatherResult]) -> str:
        """
        Format weather results into a string table (alternative method).
        
        Args:
            data: List of weather results to format
            
        Returns:
            Formatted string representation of the weather data
        """
        if not data:
            return "No hay datos meteorológicos disponibles."
        
        # Create a simple text table
        lines = []
        lines.append("=" * 100)
        lines.append(f"{'Código':<8} {'Aeropuerto':<25} {'Temperatura':<12} {'Descripción':<20} {'Estado':<15}")
        lines.append("=" * 100)
        
        for result in data:
            airport = result.airport
            
            # Use origin weather if available, otherwise destination weather
            weather = result.origin_weather or result.destination_weather
            
            if weather and weather.status == WeatherStatus.SUCCESS:
                temp = f"{weather.temperature:.1f}°C"
                desc = weather.description.title()[:18]
                status = "Exitoso"
            else:
                temp = "N/A"
                desc = "No disponible"
                status = "Error"
            
            lines.append(f"{airport.iata_code:<8} {airport.name[:23]:<25} {temp:<12} {desc:<20} {status:<15}")
        
        lines.append("=" * 100)
        return "\n".join(lines)
    
    def generate_statistics(self, results: Dict[str, WeatherData], 
                          processing_time: float,
                          cache_hits: int = 0) -> ReportStats:
        """
        Generate comprehensive statistics from weather results.
        
        This method calculates:
        - Total airports processed
        - Successful vs failed queries
        - Cache hit rate and cached queries
        - Processing time metrics
        
        Args:
            results: Dictionary mapping airport codes to weather data
            processing_time: Total time taken for processing in seconds
            cache_hits: Number of cache hits during processing (optional)
            
        Returns:
            ReportStats object with calculated statistics
        """
        total_airports = len(results)
        
        # Count successful queries (both fresh and cached)
        successful_queries = sum(1 for weather in results.values() 
                               if weather and weather.status in [WeatherStatus.SUCCESS, WeatherStatus.CACHED])
        
        # Count failed queries
        failed_queries = sum(1 for weather in results.values() 
                           if not weather or weather.status in [WeatherStatus.ERROR, WeatherStatus.NOT_AVAILABLE])
        
        # Count cached queries specifically
        cached_queries = sum(1 for weather in results.values() 
                           if weather and weather.status == WeatherStatus.CACHED)
        
        # Calculate cache hit rate as percentage
        cache_hit_rate = (cached_queries / total_airports * 100) if total_airports > 0 else 0.0
        
        return ReportStats(
            total_airports=total_airports,
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            cached_queries=cached_queries,
            processing_time=processing_time,
            cache_hit_rate=cache_hit_rate
        )
    
    def calculate_processing_metrics(self, start_time: datetime, end_time: datetime) -> float:
        """
        Calculate processing time metrics.
        
        Args:
            start_time: When processing started
            end_time: When processing ended
            
        Returns:
            Processing time in seconds
        """
        processing_duration = end_time - start_time
        return processing_duration.total_seconds()
    
    def display_processing_summary(self, stats: ReportStats) -> None:
        """
        Display a summary of processing statistics to the console.
        
        Args:
            stats: Statistics to display
        """
        self.console.print("\n")
        self.console.print("[bold green]✅ Procesamiento completado[/bold green]")
        
        # Create a summary text
        summary = Text()
        summary.append(f"Se procesaron {stats.total_airports} aeropuertos en {stats.processing_time:.2f} segundos\n")
        summary.append(f"Exitosos: {stats.successful_queries} | ", style="green")
        summary.append(f"Fallidos: {stats.failed_queries} | ", style="red")
        summary.append(f"Cache: {stats.cached_queries} ({stats.cache_hit_rate:.1f}%)", style="blue")
        
        self.console.print(summary)
        self.console.print("\n")
    
    def _format_flight_summary(self, flight_dataset, weather_results: Dict[str, WeatherData]) -> Panel:
        """
        Format flight summary information into a Rich panel.
        
        Args:
            flight_dataset: Pandas DataFrame with flight data
            weather_results: Dictionary mapping airport codes to weather data
            
        Returns:
            Rich Panel object with flight summary
        """
        total_flights = len(flight_dataset)
        
        # Count flights with complete weather data (both origin and destination)
        complete_flights = 0
        partial_flights = 0
        failed_flights = 0
        
        # Sample some flights for display
        sample_flights = []
        for idx, row in flight_dataset.head(10).iterrows():  # Show first 10 flights
            flight_code = f"{row['airline']}{row['flight_num']}"
            origin_code = row['origin_iata_code']
            dest_code = row['destination_iata_code']
            
            origin_weather = weather_results.get(origin_code)
            dest_weather = weather_results.get(dest_code)
            
            # Format weather info
            origin_temp = f"{origin_weather.temperature:.1f}°C" if origin_weather and origin_weather.status.name == 'SUCCESS' else "N/A"
            dest_temp = f"{dest_weather.temperature:.1f}°C" if dest_weather and dest_weather.status.name == 'SUCCESS' else "N/A"
            
            sample_flights.append(f"  {flight_code}: {origin_code} ({origin_temp}) → {dest_code} ({dest_temp})")
        
        # Count all flights by weather availability
        for _, row in flight_dataset.iterrows():
            origin_code = row['origin_iata_code']
            dest_code = row['destination_iata_code']
            
            origin_weather = weather_results.get(origin_code)
            dest_weather = weather_results.get(dest_code)
            
            origin_success = origin_weather and origin_weather.status.name == 'SUCCESS'
            dest_success = dest_weather and dest_weather.status.name == 'SUCCESS'
            
            if origin_success and dest_success:
                complete_flights += 1
            elif origin_success or dest_success:
                partial_flights += 1
            else:
                failed_flights += 1
        
        # Create flight summary text
        flight_text = Text()
        flight_text.append("✈️ Resumen de Vuelos\n\n", style="bold blue")
        
        flight_text.append(f"• Total de vuelos procesados: ", style="white")
        flight_text.append(f"{total_flights:,}\n", style="bold cyan")
        
        flight_text.append(f"• Vuelos con clima completo: ", style="white")
        flight_text.append(f"{complete_flights:,}", style="bold green")
        flight_text.append(f" ({complete_flights/total_flights*100:.1f}%)\n", style="green")
        
        flight_text.append(f"• Vuelos con clima parcial: ", style="white")
        flight_text.append(f"{partial_flights:,}", style="bold yellow")
        flight_text.append(f" ({partial_flights/total_flights*100:.1f}%)\n", style="yellow")
        
        flight_text.append(f"• Vuelos sin clima: ", style="white")
        flight_text.append(f"{failed_flights:,}", style="bold red")
        flight_text.append(f" ({failed_flights/total_flights*100:.1f}%)\n\n", style="red")
        
        # Add sample flights
        flight_text.append("📋 Muestra de vuelos (primeros 10):\n", style="bold white")
        for flight_info in sample_flights:
            flight_text.append(f"{flight_info}\n", style="dim white")
        
        if total_flights > 10:
            flight_text.append(f"... y {total_flights - 10:,} vuelos más\n", style="dim cyan")
        
        # Unique airports info
        unique_origins = flight_dataset['origin_iata_code'].nunique()
        unique_destinations = flight_dataset['destination_iata_code'].nunique()
        total_unique = len(set(flight_dataset['origin_iata_code'].unique()) | set(flight_dataset['destination_iata_code'].unique()))
        
        flight_text.append(f"\n🏢 Aeropuertos únicos:\n", style="bold white")
        flight_text.append(f"• Aeropuertos de origen: ", style="white")
        flight_text.append(f"{unique_origins}\n", style="bold cyan")
        
        flight_text.append(f"• Aeropuertos de destino: ", style="white")
        flight_text.append(f"{unique_destinations}\n", style="bold cyan")
        
        flight_text.append(f"• Total aeropuertos únicos: ", style="white")
        flight_text.append(f"{total_unique}", style="bold cyan")
        
        return Panel(
            flight_text,
            box=box.ROUNDED,
            padding=(1, 2)
        )