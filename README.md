# Sistema de Informes Meteorológicos

Un sistema CLI en Python para procesar datasets de vuelos y generar informes meteorológicos de aeropuertos de origen y destino.

## 🚀 Inicio Rápido

### 1. Instalación
```bash
# Instalar dependencias
pip install -r requirements.txt
pip install -e .

# Verificar instalación
weather-report --version
```

### 2. Configurar API Key
Obtén una clave gratuita en [OpenWeatherMap](https://openweathermap.org/api):

```bash
# Opción 1: Variable de entorno (recomendado)
export OPENWEATHER_API_KEY="tu_clave_api_aqui"

# Opción 2: Archivo .env
echo "OPENWEATHER_API_KEY=tu_clave_api_aqui" > .env
```

### 3. Usar el sistema
```bash
# Comando básico
weather-report flights.csv

# Con información detallada
weather-report flights.csv --verbose

# Con configuración personalizada
weather-report flights.csv --concurrency 15 --timeout 45 --verbose

```csv
origin_iata_code,origin_name,origin_latitude,origin_longitude,destination_iata_code,destination_name,destination_latitude,destination_longitude,airline,flight_num
JFK,John F Kennedy Intl,40.6413,-73.7781,LAX,Los Angeles Intl,33.9425,-118.4081,AA,AA123
LAX,Los Angeles Intl,33.9425,-118.4081,ORD,Chicago O'Hare Intl,41.9742,-87.9073,UA,UA456
```

## 🌟 Características

- **Procesamiento Concurrente**: Consultas paralelas con límites configurables
- **Caché Inteligente**: Evita consultas duplicadas (TTL 30 min)
- **Manejo de Errores**: Continúa procesando aunque fallen algunas consultas
- **Optimización de Memoria**: Procesamiento eficiente de datasets grandes
- **Informes Detallados**: Salida formateada con estadísticas completas

## 📊 Salida del Programa

### Informe de Aeropuertos
```
┌─────────────┬──────────────────────────┬─────────────┬──────────────────┬─────────────┬──────────────┐
│ Aeropuerto  │ Nombre                   │ Temperatura │ Descripción      │ Humedad (%) │ Viento (m/s) │
├─────────────┼──────────────────────────┼─────────────┼──────────────────┼─────────────┼──────────────┤
│ JFK         │ John F Kennedy Intl      │ 22.5°C      │ Partly Cloudy    │ 65          │ 4.2          │
│ LAX         │ Los Angeles Intl         │ 28.1°C      │ Clear Sky        │ 45          │ 2.8          │
└─────────────┴──────────────────────────┴─────────────┴──────────────────┴─────────────┴──────────────┘
• Tiempo total de procesamiento: 45.2 segundos
```

## ⚙️ Parámetros del Comando

- `CSV_FILE`: Archivo CSV con datos de vuelos (requerido)
- `--api-key`: Clave API de OpenWeatherMap (opcional si está en variable de entorno)
- `--concurrency`: Peticiones concurrentes (default: 10, máx: 50)
- `--timeout`: Timeout en segundos (default: 30, máx: 300)
- `--verbose`: Mostrar información detallada de progreso
- `--cache-path`: Ruta a un archivo SQLite para persistir la caché entre ejecuciones (también via env `WEATHER_CACHE_PATH`).
- `--clear-cache`: Limpia la caché antes de procesar (si se usa con `--cache-path`, borra el contenido del archivo SQLite; sin ruta, limpia la caché en memoria).
- `--version`: Mostrar versión del programa
- `--help`: Mostrar ayuda completa

## 🔧 Configuración Recomendada

| Tamaño del Dataset | Concurrencia | Timeout | Comando |
|-------------------|--------------|---------|---------|
| < 500 vuelos      | 10           | 30s     | `weather-report flights.csv` |
| 500-2000 vuelos   | 15           | 45s     | `weather-report flights.csv --concurrency 15 --timeout 45` |
| 2000-5000 vuelos  | 20           | 60s     | `weather-report flights.csv --concurrency 20 --timeout 60` |
| > 5000 vuelos     | 25           | 90s     | `weather-report flights.csv --concurrency 25 --timeout 90` |

## 💡 Ejemplos de Uso

### Dataset pequeño
```bash
export OPENWEATHER_API_KEY="tu_clave_api"
weather-report flights_small.csv
```

### Dataset grande con alta velocidad
```bash
weather-report large_flights.csv --concurrency 20 --verbose
```

### Configuración conservadora (API con límites)
```bash
weather-report flights.csv --concurrency 5 --timeout 60
```

### Caché persistente (recomendado)
```bash
# 1) Primera ejecución: llena la caché en .weather_cache.sqlite
weather-report challenge_dataset.csv --api-key YOUR_API_KEY --cache-path .weather_cache.sqlite --verbose

# 2) Segunda ejecución: reutiliza la caché (más rápido y sin golpear la API)
weather-report challenge_dataset.csv --api-key YOUR_API_KEY --cache-path .weather_cache.sqlite --verbose

# Limpia la caché antes de procesar
weather-report challenge_dataset.csv --api-key YOUR_API_KEY --cache-path .weather_cache.sqlite --clear-cache --verbose
```

### Procesamiento con archivo .env
```bash
echo "OPENWEATHER_API_KEY=tu_clave_api" > .env
weather-report flights.csv --verbose
```

### Variables de entorno soportadas (.env)

Además de `OPENWEATHER_API_KEY`, el CLI soporta estas variables para establecer valores por defecto sin pasar flags:

- `WEATHER_CACHE_PATH`: Ruta a un archivo SQLite para la caché persistente.
- `WEATHER_CONCURRENCY`: Número máximo de peticiones concurrentes (por defecto 10).
- `WEATHER_TIMEOUT`: Timeout por petición en segundos (por defecto 30).
- `WEATHER_VERBOSE`: Activa salida detallada si se establece a `1`, `true` o `yes`.
- `WEATHER_CLEAR_CACHE`: Limpia la caché al inicio si se establece a `1`, `true` o `yes`.

Ejemplo de `.env` completo:

```
OPENWEATHER_API_KEY=tu_clave_api
WEATHER_CACHE_PATH=.weather_cache.sqlite
WEATHER_CONCURRENCY=20
WEATHER_TIMEOUT=45
WEATHER_VERBOSE=1
# Opcional: limpiar caché antes de cada ejecución
# WEATHER_CLEAR_CACHE=1
```

Con este archivo `.env`, basta ejecutar:

```
weather-report challenge_dataset.csv
```

Los flags en la línea de comandos siempre tienen prioridad sobre las variables de entorno.

## 🚨 Solución de Problemas

### Errores Comunes

**"Invalid API key"**
```bash
# Verificar clave API
curl "https://api.openweathermap.org/data/2.5/weather?q=London&appid=TU_CLAVE_API"
```

**"Rate limit exceeded"**
```bash
# Reducir concurrencia
weather-report dataset.csv --concurrency 5
```

**"File not found" o "Invalid CSV"**
```bash
# Verificar formato del CSV
head -5 tu_dataset.csv
```

**Rendimiento lento**
```bash
# Aumentar concurrencia
weather-report dataset.csv --concurrency 20 --verbose
```

### Debugging
```bash
# Ver información detallada
weather-report dataset.csv --verbose

# Guardar logs para análisis
weather-report dataset.csv --verbose > debug.log 2>&1
```

## 🧪 Testing

```bash
# Instalar dependencias de testing
pip install pytest pytest-asyncio pytest-mock

# Ejecutar todas las pruebas
python -m pytest tests/ -v

# Pruebas específicas
python -m pytest tests/test_data_processor.py -v
python -m pytest tests/test_weather_service.py -v
python -m pytest tests/test_end_to_end.py -v
```

## 🏗️ Arquitectura

### Componentes Principales
1. **CLI Interface** (`cli.py`): Interfaz de línea de comandos
2. **Data Processor** (`data_processor.py`): Carga y procesamiento de CSV
3. **Weather Service** (`weather_service.py`): Orquestación de consultas meteorológicas
### Flujo de Procesamiento
CSV → Data Processor → Weather Service → OpenWeatherMap API
                           ↓
Cache Manager ← Weather Data ← HTTP Response
                           ↓
Report Generator → Terminal Output
```

## 📋 Requisitos

- Python 3.8 o superior
- Clave API de OpenWeatherMap (gratuita)
- Dependencias: `requests`, `click`, `tabulate`, `python-dotenv`

---

**Desarrollado para Deal Engine** 🌤️