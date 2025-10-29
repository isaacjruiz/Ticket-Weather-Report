# 🚀 Guía de Inicio Rápido

Empezar a usar el Sistema de Informes Meteorológicos en menos de 5 minutos.

## ⚡ Instalación Rápida

```bash
# 1. Clonar e instalar
git clone <repository-url>
cd weather_report_system
pip install -r requirements.txt
pip install -e .

# 2. Verificar instalación
weather-report --version
```

## 🔑 Configurar API Key

### Opción 1: Variable de entorno (más fácil)
```bash
export OPENWEATHER_API_KEY="tu_clave_api_de_openweathermap"
```

### Opción 2: Archivo .env
```bash
cp .env.example .env
# Editar .env y reemplazar "your_api_key_here" con tu clave real
```

**¿No tienes clave API?** → [Obtener gratis en OpenWeatherMap](https://openweathermap.org/api)

## 📊 Primer Uso

```bash
# Comando básico
weather-report tu_archivo.csv

# Con información detallada
weather-report tu_archivo.csv --verbose
```

## 📁 Formato del CSV

Tu archivo CSV debe tener estas columnas:
```csv
origin_iata_code,origin_name,origin_latitude,origin_longitude,destination_iata_code,destination_name,destination_latitude,destination_longitude,airline,flight_num
JFK,John F Kennedy Intl,40.6413,-73.7781,LAX,Los Angeles Intl,33.9425,-118.4081,AA,AA123
```

## 🎯 Ejemplos Rápidos

```bash
# Dataset pequeño
weather-report flights.csv

# Dataset grande con más velocidad
weather-report large_flights.csv --concurrency 20 --verbose

# Configuración conservadora
weather-report flights.csv --concurrency 5 --timeout 60
```

## 🆘 ¿Problemas?

- **"Invalid API key"** → Verificar que la clave esté correcta y activa
- **"Rate limit exceeded"** → Usar `--concurrency 5`
- **Muy lento** → Usar `--concurrency 20 --verbose`
- **Errores de CSV** → Verificar que tenga todas las columnas requeridas

## 📚 Más Información

- **Documentación completa**: `README.md`
- **Ejemplos detallados**: `examples.md`
- **Ayuda del comando**: `weather-report --help`

---
¡Listo para procesar datos meteorológicos! 🌤️