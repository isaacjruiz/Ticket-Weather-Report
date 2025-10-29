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
# Opción 1: Archivo .env (recomendado)
cp .env.example .env
# Edita .env y añade tu API key

# Opción 2: Variable de entorno
export OPENWEATHER_API_KEY="tu_clave_api_aqui"

# Opción 3: Pasar como parámetro
weather-report flights.csv --api-key tu_clave_api_aqui
```

### 3. Usar el sistema
```bash
# Comando básico (lee configuración desde .env)
weather-report challenge_dataset.csv

# Con caché persistente para mejorar velocidad
weather-report challenge_dataset.csv --cache-path .weather_cache.sqlite

# Con información detallada
weather-report challenge_dataset.csv --verbose

# Limpiar caché antes de procesar
weather-report challenge_dataset.csv --cache-path .weather_cache.sqlite --clear-cache
## 📁 Formato del CSV

Tu archivo CSV debe tener estas columnas:

```csv
origin_iata_code,origin_name,origin_latitude,origin_longitude,destination_iata_code,destination_name,destination_latitude,destination_longitude,airline,flight_num
JFK,John F Kennedy Intl,40.6413,-73.7781,LAX,Los Angeles Intl,33.9425,-118.4081,AA,AA123
LAX,Los Angeles Intl,33.9425,-118.4081,ORD,Chicago O'Hare Intl,41.9742,-87.9073,UA,UA456
```

## ⚙️ Configuración con .env

El sistema carga automáticamente la configuración desde un archivo `.env` en la raíz del proyecto:

```bash
# Copiar plantilla
cp .env.example .env
```

**Variables de entorno soportadas:**

| Variable | Descripción | Default |
|----------|-------------|---------|
| `OPENWEATHER_API_KEY` | API key de OpenWeatherMap (requerida) | - |
| `WEATHER_CACHE_PATH` | Ruta al archivo SQLite para caché persistente | ninguno |
| `WEATHER_CONCURRENCY` | Máximo de peticiones concurrentes | 10 |
| `WEATHER_TIMEOUT` | Timeout por petición en segundos | 30 |
| `WEATHER_VERBOSE` | Activar logs detallados (`1`, `true`, `yes`) | false |
| `WEATHER_CLEAR_CACHE` | Limpiar caché al inicio (`1`, `true`, `yes`) | false |

**Ejemplo de `.env`:**
```bash
OPENWEATHER_API_KEY=tu_clave_api_aqui
WEATHER_CACHE_PATH=.weather_cache.sqlite
WEATHER_CONCURRENCY=20
WEATHER_TIMEOUT=45
WEATHER_VERBOSE=1
```

Con este archivo, simplemente ejecuta:
```bash
weather-report challenge_dataset.csv
```

> **Nota:** Los flags de CLI tienen prioridad sobre las variables de entorno.

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

**Argumentos:**
- `CSV_FILE`: Archivo CSV con datos de vuelos (requerido)

**Opciones:**
- `--api-key TEXT`: Clave API de OpenWeatherMap (también via `OPENWEATHER_API_KEY`)
- `--concurrency INTEGER`: Peticiones concurrentes (default: 10, máx: 50, también via `WEATHER_CONCURRENCY`)
- `--timeout INTEGER`: Timeout en segundos (default: 30, máx: 300, también via `WEATHER_TIMEOUT`)
- `--verbose`: Mostrar información detallada (también via `WEATHER_VERBOSE=1`)
- `--cache-path PATH`: Ruta a SQLite para caché persistente (también via `WEATHER_CACHE_PATH`)
- `--clear-cache`: Limpia la caché antes de procesar (también via `WEATHER_CLEAR_CACHE=1`)
- `--version`: Mostrar versión del programa
- `--help`: Mostrar ayuda completa

> **Tip:** Usa un archivo `.env` para no tener que pasar parámetros cada vez

## 🔧 Configuración Recomendada

| Tamaño del Dataset | Concurrencia | Timeout | Comando |
|-------------------|--------------|---------|---------|
| < 500 vuelos      | 10           | 30s     | `weather-report flights.csv` |
| 500-2000 vuelos   | 15           | 45s     | `weather-report flights.csv --concurrency 15 --timeout 45` |
| 2000-5000 vuelos  | 20           | 60s     | `weather-report flights.csv --concurrency 20 --timeout 60` |
| > 5000 vuelos     | 25           | 90s     | `weather-report flights.csv --concurrency 25 --timeout 90` |

## 💡 Ejemplos de Uso

### Uso básico con .env
```bash
# Configurar .env una vez
cp .env.example .env
# Editar .env con tu API key

# Usar sin parámetros
weather-report challenge_dataset.csv
```

### Con caché persistente (recomendado para datasets grandes)
```bash
# Primera ejecución: llena la caché
weather-report challenge_dataset.csv --cache-path .weather_cache.sqlite

# Segunda ejecución: usa caché (más rápido, sin API calls)
weather-report challenge_dataset.csv --cache-path .weather_cache.sqlite
# Resultado: 100% cache hit, ~0.12s vs ~1.2s

# Limpiar caché y volver a procesar
weather-report challenge_dataset.csv --cache-path .weather_cache.sqlite --clear-cache
```

### Dataset grande con alta velocidad
```bash
weather-report large_flights.csv --concurrency 20 --verbose
```

### Configuración conservadora (API con límites)
```bash
weather-report flights.csv --concurrency 5 --timeout 60
```

## 🚨 Solución de Problemas

### Errores Comunes

**"Invalid API key" o "Missing option '--api-key'"**
```bash
# Verificar que .env existe y tiene la API key
cat .env | grep OPENWEATHER_API_KEY

# O configurarla manualmente
export OPENWEATHER_API_KEY="tu_clave_api"

# Verificar que la clave funciona
curl "https://api.openweathermap.org/data/2.5/weather?q=London&appid=TU_CLAVE_API"
```

**Limpiar caché**
```bash
# Opción 1: Usar el flag
weather-report dataset.csv --cache-path .weather_cache.sqlite --clear-cache

# Opción 2: Borrar el archivo
rm .weather_cache.sqlite
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