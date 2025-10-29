# Ejemplos de Uso - Sistema de Informes Meteorológicos

Este archivo contiene ejemplos prácticos de cómo usar el Sistema de Informes Meteorológicos en diferentes escenarios.

## 🚀 Configuración Inicial

### Obtener y configurar clave API de OpenWeatherMap

```bash
# 1. Registrarse en https://openweathermap.org/api
# 2. Crear cuenta gratuita
# 3. Generar clave API
# 4. Configurar como variable de entorno

export OPENWEATHER_API_KEY="tu_clave_api_de_32_caracteres"
```

### Verificar instalación

```bash
# Verificar que el comando esté disponible
weather-report --version

# Mostrar ayuda completa
weather-report --help
```

## 📊 Ejemplos Básicos

### Ejemplo 1: Procesamiento simple

```bash
# Dataset pequeño con configuración por defecto
weather-report flights_small.csv
```

**Salida esperada:**
```
🌤️  Weather Report System v1.0.0
Processing flight dataset for weather information...

✓ Dataset loaded: 100 flight records
✓ Found 25 unique airports
✓ Weather data retrieved: 24 successful, 1 failed, 8 from cache

┌─────────────┬──────────────────────────┬─────────────┬──────────────────┬─────────────┬──────────────┐
│ Aeropuerto  │ Nombre                   │ Temperatura │ Descripción      │ Humedad (%) │ Viento (m/s) │
├─────────────┼──────────────────────────┼─────────────┼──────────────────┼─────────────┼──────────────┤
│ JFK         │ John F Kennedy Intl      │ 22.5°C      │ Partly Cloudy    │ 65          │ 4.2          │
│ LAX         │ Los Angeles Intl         │ 28.1°C      │ Clear Sky        │ 45          │ 2.8          │
└─────────────┴──────────────────────────┴─────────────┴──────────────────┴─────────────┴──────────────┘

🎉 Processing completed successfully in 12.34 seconds!
```

### Ejemplo 2: Con modo verbose

```bash
# Ver progreso detallado del procesamiento
weather-report flights.csv --verbose
```

**Salida esperada:**
```
🌤️  Weather Report System v1.0.0
Processing flight dataset for weather information...

Configuration:
  • Dataset file: /path/to/flights.csv
  • Concurrency: 10
  • Timeout: 30s
  • API key: ****abc123

📂 Loading and validating dataset...
✓ Dataset loaded: 1000 flight records

🏢 Extracting unique airports...
✓ Found 150 unique airports

🌤️  Fetching weather data (concurrency: 10)...
   • Processing 150 airports...
✓ Weather data retrieved: 147 successful, 3 failed, 45 from cache

📊 Generating weather report...
✓ Report generated successfully

🎉 Processing completed successfully in 45.67 seconds!

Performance metrics:
  • Total processing time: 45.67s
  • Average time per airport: 0.304s
  • Cache hit rate: 30.0%
```

## ⚙️ Configuración Avanzada

### Ejemplo 3: Alta concurrencia para datasets grandes

```bash
# Procesar dataset grande con máxima velocidad
weather-report large_flights.csv \
  --concurrency 25 \
  --timeout 60 \
  --verbose
```

**Cuándo usar:**
- Datasets con más de 2000 vuelos
- API key con límites altos
- Conexión a internet estable

### Ejemplo 4: Configuración conservadora

```bash
# Para APIs con límites estrictos o conexión lenta
weather-report flights.csv \
  --concurrency 3 \
  --timeout 90 \
  --verbose
```

**Cuándo usar:**
- API key gratuita con límites bajos
- Conexión a internet inestable
- Primeras pruebas del sistema

### Ejemplo 5: Usando archivo .env

```bash
# Crear archivo de configuración
cat > .env << EOF
OPENWEATHER_API_KEY=tu_clave_api_aqui
DEFAULT_CONCURRENCY=15
DEFAULT_TIMEOUT=45
EOF

# Ejecutar sin especificar parámetros
weather-report flights.csv --verbose
```

## 🔄 Escenarios de Uso Real

### Escenario 1: Análisis diario de vuelos

```bash
#!/bin/bash
# Script para procesamiento diario automatizado

DATE=$(date +%Y%m%d)
INPUT_FILE="flights_${DATE}.csv"
OUTPUT_LOG="weather_report_${DATE}.log"

echo "Procesando vuelos del día: $DATE"

weather-report "$INPUT_FILE" \
  --concurrency 15 \
  --timeout 45 \
  --verbose > "$OUTPUT_LOG" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Procesamiento completado exitosamente"
    echo "📄 Log guardado en: $OUTPUT_LOG"
else
    echo "❌ Error en el procesamiento"
    echo "📄 Ver detalles en: $OUTPUT_LOG"
fi
```

### Escenario 2: Procesamiento por lotes

```bash
#!/bin/bash
# Procesar múltiples archivos CSV

for file in data/flights_*.csv; do
    echo "Procesando: $file"
    
    weather-report "$file" \
      --concurrency 10 \
      --verbose
    
    echo "Completado: $file"
    echo "---"
done
```

### Escenario 3: Monitoreo de rendimiento

```bash
#!/bin/bash
# Script con monitoreo de tiempo y memoria

echo "Iniciando procesamiento con monitoreo..."

# Medir tiempo de ejecución
time weather-report flights.csv \
  --concurrency 20 \
  --verbose

# Verificar uso de memoria durante ejecución
# (ejecutar en terminal separado)
# watch -n 1 'ps aux | grep weather-report'
```

## 🚨 Manejo de Errores

### Ejemplo 6: Recuperación de errores de API

```bash
# Si hay errores de rate limiting, reducir concurrencia
weather-report flights.csv --concurrency 5 --timeout 120

# Si hay timeouts, aumentar timeout
weather-report flights.csv --timeout 90 --verbose

# Para debugging completo
weather-report flights.csv --verbose 2>&1 | tee debug.log
```

### Ejemplo 7: Validación de dataset

```bash
# Verificar estructura del CSV antes del procesamiento
head -5 flights.csv

# Verificar columnas requeridas
python -c "
import pandas as pd
df = pd.read_csv('flights.csv')
required = {'origin_iata_code', 'origin_name', 'origin_latitude', 'origin_longitude',
           'destination_iata_code', 'destination_name', 'destination_latitude', 
           'destination_longitude', 'airline', 'flight_num'}
missing = required - set(df.columns)
if missing:
    print(f'❌ Columnas faltantes: {missing}')
else:
    print('✅ Estructura del CSV válida')
    print(f'📊 Total de vuelos: {len(df)}')
"
```

## 📈 Optimización de Rendimiento

### Ejemplo 8: Configuración por tamaño de dataset

```bash
# Dataset pequeño (< 500 vuelos)
weather-report small_flights.csv --concurrency 8

# Dataset mediano (500-2000 vuelos)  
weather-report medium_flights.csv --concurrency 15 --timeout 45

# Dataset grande (2000-5000 vuelos)
weather-report large_flights.csv --concurrency 20 --timeout 60

# Dataset muy grande (> 5000 vuelos)
weather-report huge_flights.csv --concurrency 25 --timeout 90 --verbose
```

### Ejemplo 9: Prueba de rendimiento

```bash
# Ejecutar prueba de rendimiento del sistema
python performance_test.py

# Verificar que cumple requisitos de tiempo (< 5 minutos)
time weather-report test_3000_flights.csv --concurrency 20 --verbose
```

## 🔍 Debugging y Troubleshooting

### Ejemplo 10: Debugging completo

```bash
# Habilitar logging detallado
export PYTHONPATH="./src:$PYTHONPATH"

# Ejecutar con máximo detalle
weather-report flights.csv \
  --verbose \
  --concurrency 5 \
  --timeout 120 \
  2>&1 | tee full_debug.log

# Analizar logs
grep "ERROR" full_debug.log
grep "Cache" full_debug.log  
grep "Performance" full_debug.log
```

### Ejemplo 11: Verificación de conectividad API

```bash
# Probar conectividad con OpenWeatherMap
curl -s "https://api.openweathermap.org/data/2.5/weather?q=London&appid=$OPENWEATHER_API_KEY" | jq .

# Si falla, verificar clave API
echo "API Key: $OPENWEATHER_API_KEY"

# Probar con coordenadas específicas
curl -s "https://api.openweathermap.org/data/2.5/weather?lat=40.6413&lon=-73.7781&appid=$OPENWEATHER_API_KEY" | jq .
```

## 📊 Análisis de Resultados

### Ejemplo 12: Procesamiento de salida

```bash
# Guardar salida en archivo
weather-report flights.csv --verbose > report_output.txt 2>&1

# Extraer solo estadísticas
grep -A 10 "Estadísticas de Procesamiento" report_output.txt

# Extraer solo errores
grep "❌\|ERROR\|Failed" report_output.txt

# Contar aeropuertos procesados
grep "aeropuertos procesados" report_output.txt
```

## 🔄 Integración con Otros Sistemas

### Ejemplo 13: Pipeline de datos

```bash
#!/bin/bash
# Pipeline completo de procesamiento de datos

# 1. Descargar datos
wget -O flights_today.csv "https://api.example.com/flights/today"

# 2. Procesar con weather report
weather-report flights_today.csv \
  --concurrency 15 \
  --verbose > weather_results.log

# 3. Extraer métricas para dashboard
python extract_metrics.py weather_results.log > metrics.json

# 4. Enviar a sistema de monitoreo
curl -X POST -H "Content-Type: application/json" \
  -d @metrics.json \
  https://monitoring.example.com/api/metrics
```

### Ejemplo 14: Automatización con cron

```bash
# Agregar a crontab para ejecución diaria
# crontab -e

# Ejecutar todos los días a las 6:00 AM
0 6 * * * /path/to/process_daily_flights.sh

# Script: process_daily_flights.sh
#!/bin/bash
cd /path/to/weather_report_system
source venv/bin/activate
export OPENWEATHER_API_KEY="tu_clave_api"

weather-report /data/flights_$(date +\%Y\%m\%d).csv \
  --concurrency 15 \
  --verbose >> /logs/weather_report_$(date +\%Y\%m\%d).log 2>&1
```

---

## 💡 Consejos Adicionales

1. **Monitorear límites de API**: Las cuentas gratuitas tienen límites de 1000 llamadas/día
2. **Usar caché efectivamente**: Los aeropuertos duplicados se procesan solo una vez
3. **Ajustar concurrencia**: Empezar con valores bajos y aumentar gradualmente
4. **Guardar logs**: Usar `--verbose` y redirigir salida para análisis posterior
5. **Validar datos**: Verificar estructura del CSV antes del procesamiento masivo

Para más información, consultar el archivo `README.md` principal.