# Sistema de Informes Meteorológicos

Un sistema CLI en Python para procesar datasets de vuelos y generar informes meteorológicos completos de aeropuertos de origen y destino.

## 🌟 Características

- **Procesamiento Concurrente**: Consultas paralelas a APIs meteorológicas con límites configurables
- **Caché Inteligente**: Sistema de caché en memoria con TTL de 30 minutos para evitar consultas duplicadas
- **Manejo Robusto de Errores**: Continúa procesando aunque fallen algunas consultas meteorológicas
- **Optimización de Memoria**: Procesamiento eficiente de datasets grandes con gestión de memoria LRU
- **Informes Detallados**: Salida formateada con estadísticas completas de procesamiento

## 📋 Requisitos

- Python 3.8 o superior
- Clave API de OpenWeatherMap (gratuita en [openweathermap.org](https://openweathermap.org/api))

## 🚀 Instalación

### Instalación desde el código fuente

```bash
# Clonar el repositorio
git clone <repository-url>
cd weather_report_system

# Instalar dependencias
pip install -r requirements.txt

# Instalar el paquete
pip install -e .
```

### Verificar la instalación

```bash
weather-report --version
```

## ⚙️ Configuración

### 1. Obtener clave API de OpenWeatherMap

1. Registrarse en [OpenWeatherMap](https://openweathermap.org/api)
2. Crear una cuenta gratuita
3. Generar una clave API en el panel de control
4. La clave puede tardar hasta 2 horas en activarse

### 2. Configurar la clave API

**Opción 1: Variable de entorno (recomendado)**
```bash
export OPENWEATHER_API_KEY="tu_clave_api_aqui"
```

**Opción 2: Archivo .env**
```bash
# Crear archivo .env en el directorio del proyecto
echo "OPENWEATHER_API_KEY=tu_clave_api_aqui" > .env
```

**Opción 3: Parámetro de línea de comandos**
```bash
weather-report dataset.csv --api-key tu_clave_api_aqui
```

## 📊 Uso

### Comando básico

```bash
weather-report flights.csv --api-key TU_CLAVE_API
```

### Opciones avanzadas

```bash
weather-report flights.csv \
  --api-key TU_CLAVE_API \
  --concurrency 15 \
  --timeout 45 \
  --verbose
```

### Parámetros disponibles

- `CSV_FILE`: Archivo CSV con datos de vuelos (requerido)
- `--api-key`: Clave API de OpenWeatherMap (requerido si no está en variable de entorno)
- `--concurrency`: Número máximo de peticiones concurrentes (default: 10, máx: 50)
- `--timeout`: Timeout de peticiones en segundos (default: 30, máx: 300)
- `--verbose`: Habilitar salida detallada con información de progreso
- `--version`: Mostrar versión del programa
- `--help`: Mostrar ayuda completa#
# 📁 Formato del Dataset CSV

El archivo CSV debe contener las siguientes columnas:

```csv
origin_iata_code,origin_name,origin_latitude,origin_longitude,destination_iata_code,destination_name,destination_latitude,destination_longitude,airline,flight_num
JFK,John F Kennedy Intl,40.6413,-73.7781,LAX,Los Angeles Intl,33.9425,-118.4081,AA,AA123
LAX,Los Angeles Intl,33.9425,-118.4081,ORD,Chicago O'Hare Intl,41.9742,-87.9073,UA,UA456
```

### Columnas requeridas:

- `origin_iata_code`: Código IATA del aeropuerto de origen (ej: JFK)
- `origin_name`: Nombre del aeropuerto de origen
- `origin_latitude`: Latitud del aeropuerto de origen (-90 a 90)
- `origin_longitude`: Longitud del aeropuerto de origen (-180 a 180)
- `destination_iata_code`: Código IATA del aeropuerto de destino
- `destination_name`: Nombre del aeropuerto de destino
- `destination_latitude`: Latitud del aeropuerto de destino
- `destination_longitude`: Longitud del aeropuerto de destino
- `airline`: Código de aerolínea (ej: AA, UA, DL)
- `flight_num`: Número de vuelo

## 💡 Ejemplos de Uso

### Ejemplo 1: Uso básico con variable de entorno

```bash
# Configurar clave API
export OPENWEATHER_API_KEY="abcd1234567890"

# Procesar dataset
weather-report flights_data.csv
```

### Ejemplo 2: Procesamiento con alta concurrencia

```bash
weather-report large_dataset.csv \
  --api-key abcd1234567890 \
  --concurrency 20 \
  --verbose
```

### Ejemplo 3: Configuración conservadora para APIs con límites estrictos

```bash
weather-report flights.csv \
  --api-key abcd1234567890 \
  --concurrency 5 \
  --timeout 60
```

### Ejemplo 4: Procesamiento con archivo .env

```bash
# Crear archivo .env
echo "OPENWEATHER_API_KEY=abcd1234567890" > .env

# Ejecutar sin especificar clave
weather-report flights.csv --verbose
```

## 📈 Salida del Programa

### Informe de Terminal

El programa genera un informe tabular con la siguiente información:

```
┌─────────────┬──────────────────────────┬─────────────┬──────────────────┬─────────────┬──────────────┐
│ Aeropuerto  │ Nombre                   │ Temperatura │ Descripción      │ Humedad (%) │ Viento (m/s) │
├─────────────┼──────────────────────────┼─────────────┼──────────────────┼─────────────┼──────────────┤
│ JFK         │ John F Kennedy Intl      │ 22.5°C      │ Partly Cloudy    │ 65          │ 4.2          │
│ LAX         │ Los Angeles Intl         │ 28.1°C      │ Clear Sky        │ 45          │ 2.8          │
│ ORD         │ Chicago O'Hare Intl      │ 15.3°C      │ Light Rain       │ 78          │ 6.1          │
└─────────────┴──────────────────────────┴─────────────┴──────────────────┴─────────────┴──────────────┘
```

### Estadísticas de Procesamiento

```
📊 Estadísticas de Procesamiento:
• Total de aeropuertos procesados: 150
• Aeropuertos con datos meteorológicos: 147 (98.0%)
• Aeropuertos sin datos disponibles: 3 (2.0%)
• Consultas desde caché: 45 (30.0%)
• Tiempo total de procesamiento: 45.2 segundos
• Velocidad de procesamiento: 3.3 aeropuertos/segundo
```

## 🔧 Optimización de Rendimiento

### Configuración Recomendada por Tamaño de Dataset

| Tamaño del Dataset | Concurrencia | Timeout | Memoria Estimada |
|-------------------|--------------|---------|------------------|
| < 500 vuelos      | 10           | 30s     | < 100MB          |
| 500-2000 vuelos   | 15           | 45s     | 100-300MB        |
| 2000-5000 vuelos  | 20           | 60s     | 300-500MB        |
| > 5000 vuelos     | 25           | 90s     | > 500MB          |

### Consejos de Optimización

1. **Usar concurrencia apropiada**: Más concurrencia = más rápido, pero respeta los límites de la API
2. **Aprovechar el caché**: Los aeropuertos duplicados se procesan solo una vez
3. **Monitorear memoria**: Para datasets muy grandes, el sistema optimiza automáticamente el uso de memoria
4. **Configurar timeout adecuado**: Timeouts muy bajos pueden causar fallos innecesarios

## 🚨 Solución de Problemas

### Errores Comunes

**Error: "Invalid API key"**
```bash
# Verificar que la clave API sea correcta y esté activa
curl "https://api.openweathermap.org/data/2.5/weather?q=London&appid=TU_CLAVE_API"
```

**Error: "Rate limit exceeded"**
```bash
# Reducir concurrencia
weather-report dataset.csv --concurrency 5 --timeout 60
```

**Error: "File not found" o "Invalid CSV structure"**
```bash
# Verificar formato del CSV
head -5 tu_dataset.csv
```

**Rendimiento lento**
```bash
# Aumentar concurrencia (si la API lo permite)
weather-report dataset.csv --concurrency 20 --verbose
```

### Logs de Depuración

Para obtener información detallada de depuración:

```bash
weather-report dataset.csv --verbose
```

Esto mostrará:
- Progreso de carga del dataset
- Estadísticas de aeropuertos únicos
- Progreso de consultas meteorológicas
- Estadísticas de caché y rendimiento
- Detalles de errores si ocurren

## 🏗️ Arquitectura del Sistema

### Componentes Principales

1. **CLI Interface** (`cli.py`): Interfaz de línea de comandos con Click
2. **Data Processor** (`data_processor.py`): Carga y procesamiento de CSV
3. **Weather Service** (`weather_service.py`): Orquestación de consultas meteorológicas
4. **Weather API Client** (`weather_api_client.py`): Cliente HTTP asíncrono
5. **Cache Manager** (`cache_manager.py`): Sistema de caché con LRU
6. **Report Generator** (`report_generator.py`): Generación de informes

### Flujo de Procesamiento

```
CSV Dataset → Data Processor → Weather Service → API Client → OpenWeatherMap API
                                     ↓
Cache Manager ← Weather Data ← Response Parser ← HTTP Response
                                     ↓
Report Generator → Terminal Output → Estadísticas
```

## 🧪 Testing

### Ejecutar todas las pruebas

```bash
# Instalar dependencias de testing
pip install pytest pytest-asyncio pytest-mock

# Ejecutar suite completa de pruebas
python -m pytest tests/ -v

# Ejecutar pruebas de rendimiento
python performance_test.py
```

### Pruebas por Componente

```bash
# Pruebas del procesador de datos
python -m pytest tests/test_data_processor.py -v

# Pruebas del servicio meteorológico
python -m pytest tests/test_weather_service.py -v

# Pruebas end-to-end
python -m pytest tests/test_end_to_end.py -v
```

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## 📞 Soporte

Para reportar bugs o solicitar features, por favor crear un issue en el repositorio del proyecto.

---

**Desarrollado con ❤️ para Deal Engine**