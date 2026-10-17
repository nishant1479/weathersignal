# Data Sources Specification

## 1. India Meteorological Department (IMD)

- **Portal**: [https://api.imd.gov.in/public/index.php](https://api.imd.gov.in/public/index.php)
- **Official API Reference**: [https://api.imd.gov.in/public/api_reference.html](https://api.imd.gov.in/public/api_reference.html)
- **Authentication**: Requires registration on `api.imd.gov.in` and an authorized API key passed via the `x-api-key` HTTP header.
- **Endpoints Supported**:
  - `/districtwarning?id={id}`
  - `/districtrainfall?id={id}`
  - `/districtnowcast?id={id}`
  - `/aws_data?id={id}`
- **Fallback / Unconfigured Behavior**:
  - If `IMD_API_KEY` is not provided in environment variables, the system reports `NOT_CONFIGURED`, records the limitation transparently in the investigation, and abstains from manufacturing false IMD data.

## 2. Open-Meteo Weather Observation Archive

- **Portal**: [https://open-meteo.com/en/docs/historical-weather-api](https://open-meteo.com/en/docs/historical-weather-api)
- **Authentication**: None required (Free public open API).
- **Coverage**: Worldwide (including all Indian states, districts, and coordinates) down to hourly resolution.
- **Variables Retrieved**: `rain`, `precipitation`, `temperature_2m`, `windspeed_10m`.
- **Role**: Provides verifiable real-world empirical weather observations for the target coordinates and timestamps.

## 3. OpenStreetMap Nominatim Geocoding

- **Portal**: [https://nominatim.openstreetmap.org/](https://nominatim.openstreetmap.org/)
- **Usage**: Resolves user place names (e.g. "Connaught Place", "Adilabad") into coordinates (`latitude`, `longitude`).
- **Policy**: Sends compliant `User-Agent: WeatherSignal/1.0`.
