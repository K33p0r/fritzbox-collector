# Grafana Dashboard Beispiele

Dieser Ordner enthält Beispiel-Queries für Grafana-Dashboards, die die neuen Features nutzen.

## Weather Data Dashboard

### Panel: Aktuelle Temperatur
```sql
SELECT 
    time,
    temperature_celsius as value,
    'Temperatur' as metric
FROM weather_data
WHERE $__timeFilter(time)
ORDER BY time DESC
```

### Panel: Wetterbedingungen (letzte 24h)
```sql
SELECT 
    time,
    temperature_celsius,
    feels_like_celsius,
    humidity,
    weather_description
FROM weather_data
WHERE time >= NOW() - INTERVAL 24 HOUR
ORDER BY time DESC
```

### Panel: Luftfeuchtigkeit und Druck
```sql
SELECT 
    time,
    humidity as 'Luftfeuchtigkeit (%)',
    pressure as 'Luftdruck (hPa)'
FROM weather_data
WHERE $__timeFilter(time)
ORDER BY time
```

## Stromkosten Dashboard

### Panel: Aktuelle Leistungsaufnahme aller Geräte
```sql
SELECT 
    d.time,
    d.device_name,
    d.multimeter_power / 1000.0 as 'Leistung (W)'
FROM dect200_data d
WHERE $__timeFilter(d.time)
  AND d.multimeter_power IS NOT NULL
ORDER BY d.time
```

### Panel: Stromkosten pro Gerät (aktueller Tag)
```sql
SELECT 
    d.device_name as metric,
    SUM((d.multimeter_power / 1000000.0) * (300 / 3600.0) * p.price_eur_per_kwh) as value
FROM dect200_data d
CROSS JOIN (
    SELECT price_eur_per_kwh 
    FROM electricity_price_config 
    WHERE valid_to IS NULL OR valid_to > NOW()
    ORDER BY valid_from DESC 
    LIMIT 1
) p
WHERE DATE(d.time) = CURDATE()
  AND d.multimeter_power IS NOT NULL
GROUP BY d.device_name
ORDER BY value DESC
```

### Panel: Tägliche Gesamtkosten (letzte 30 Tage)
```sql
SELECT 
    DATE(d.time) as time,
    SUM((d.multimeter_power / 1000000.0) * (300 / 3600.0) * p.price_eur_per_kwh) as 'Kosten (EUR)'
FROM dect200_data d
CROSS JOIN (
    SELECT price_eur_per_kwh 
    FROM electricity_price_config 
    WHERE valid_to IS NULL OR valid_to > NOW()
    ORDER BY valid_from DESC 
    LIMIT 1
) p
WHERE d.time >= NOW() - INTERVAL 30 DAY
  AND d.multimeter_power IS NOT NULL
GROUP BY DATE(d.time)
ORDER BY time
```

### Panel: Hochgerechnete Monatskosten
```sql
SELECT 
    'Hochgerechnete Monatskosten' as metric,
    SUM((d.multimeter_power / 1000000.0) * (300 / 3600.0) * p.price_eur_per_kwh) * (30.0 / DATEDIFF(NOW(), MIN(d.time))) as value
FROM dect200_data d
CROSS JOIN (
    SELECT price_eur_per_kwh 
    FROM electricity_price_config 
    WHERE valid_to IS NULL OR valid_to > NOW()
    ORDER BY valid_from DESC 
    LIMIT 1
) p
WHERE d.time >= NOW() - INTERVAL 7 DAY
  AND d.multimeter_power IS NOT NULL
```

### Panel: Energiekosten pro Gerät (Zeitverlauf)
```sql
SELECT 
    d.time,
    d.device_name,
    (d.multimeter_power / 1000000.0) * (300 / 3600.0) * p.price_eur_per_kwh as 'Kosten (EUR)'
FROM dect200_data d
CROSS JOIN (
    SELECT price_eur_per_kwh 
    FROM electricity_price_config 
    WHERE valid_to IS NULL OR valid_to > NOW()
    ORDER BY valid_from DESC 
    LIMIT 1
) p
WHERE $__timeFilter(d.time)
  AND d.multimeter_power IS NOT NULL
ORDER BY d.time
```

### Panel: Aktueller Strompreis
```sql
SELECT 
    time,
    price_eur_per_kwh as 'Preis (EUR/kWh)',
    description
FROM electricity_price_config
WHERE valid_to IS NULL OR valid_to > NOW()
ORDER BY time DESC
LIMIT 1
```

## Kombiniertes Dashboard: Wetter und Energie

### Panel: Energieverbrauch vs. Temperatur
```sql
SELECT 
    d.time,
    SUM(d.multimeter_power) / 1000.0 as 'Gesamtleistung (W)',
    w.temperature_celsius as 'Temperatur (°C)'
FROM dect200_data d
LEFT JOIN weather_data w ON DATE(d.time) = DATE(w.time) AND HOUR(d.time) = HOUR(w.time)
WHERE $__timeFilter(d.time)
  AND d.multimeter_power IS NOT NULL
GROUP BY d.time, w.temperature_celsius
ORDER BY d.time
```

## Variablen für Dashboard

Fügen Sie folgende Variablen in Grafana hinzu für flexible Dashboards:

### Device Variable
```sql
SELECT DISTINCT device_name 
FROM dect200_data 
WHERE device_name IS NOT NULL 
ORDER BY device_name
```

### Time Range Variable
Standard Grafana Time Range verwenden: `$__timeFilter()`

## Hinweise

- Alle Kosten-Queries gehen von einem 5-Minuten-Intervall (300 Sekunden) aus
- Passen Sie das Intervall an Ihre `COLLECT_INTERVAL` Einstellung an
- Der Strompreis wird aus der `electricity_price_config` Tabelle gelesen
- Wetterdaten werden stündlich aktualisiert (Standard)
