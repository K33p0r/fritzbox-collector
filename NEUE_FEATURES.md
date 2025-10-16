# Neue Features: Wetter-API und Strompreis

## Übersicht

Dieses Update fügt zwei neue Hauptfunktionen hinzu:
1. **WeatherAPI-Integration**: Automatisches Sammeln von Wetterdaten
2. **Strompreis-Tracking**: Konfigurierbare Stromkosten für Energieberechnungen

## 1. WeatherAPI-Integration

### Beschreibung
Das System ruft stündlich Wetterdaten von OpenWeatherMap ab und speichert sie in der Datenbank.

### Gespeicherte Daten
- Temperatur (°C)
- Gefühlte Temperatur (°C)
- Luftfeuchtigkeit (%)
- Luftdruck (hPa)
- Wetterbedingung (z.B. "Clear", "Rain")
- Wetterbeschreibung (auf Deutsch)
- Windgeschwindigkeit (m/s)
- Bewölkung (%)

### Einrichtung

1. **OpenWeatherMap API-Key erhalten:**
   - Registrierung unter https://openweathermap.org/api
   - Kostenlosen API-Key generieren (Free Plan: 1000 Calls/Tag)

2. **Umgebungsvariablen setzen:**
   ```bash
   WEATHER_API_KEY=dein_api_key_hier
   WEATHER_LOCATION=Berlin,DE
   WEATHER_INTERVAL=3600  # Optional, Standard: 3600 Sekunden (1 Stunde)
   ```

3. **Datenbanktabelle:**
   Die Tabelle `weather_data` wird automatisch beim Start erstellt.

### Beispiel-Abfrage
```sql
SELECT 
    time,
    temperature_celsius,
    humidity,
    weather_description
FROM weather_data
WHERE time >= NOW() - INTERVAL 24 HOUR
ORDER BY time DESC;
```

## 2. Strompreis-Tracking

### Beschreibung
Das System verwendet einen konfigurierbaren Strompreis (Standard: 0,30 EUR/kWh) für Kostenberechnungen.

### Features
- Fester Strompreis von 30 Eurocent pro kWh (konfigurierbar)
- Automatische Berechnung der Energiekosten
- Historische Preisverwaltung möglich
- Integration in DECT-Gerätedaten

### Einrichtung

1. **Umgebungsvariable setzen (optional):**
   ```bash
   ELECTRICITY_PRICE_EUR_PER_KWH=0.30  # Standard: 0,30 EUR/kWh
   ```

2. **Datenbanktabelle:**
   Die Tabelle `electricity_price_config` wird automatisch erstellt und mit dem Standardpreis befüllt.

### Kostenberechnung

Die bereitgestellten Hilfsfunktionen können in Python verwendet werden:

```python
from electricity_price import (
    calculate_energy_cost,
    calculate_power_cost_per_interval,
    get_current_electricity_price
)

# Beispiel: Kosten für 2500 mW (2,5 W) über 5 Minuten
cost = calculate_power_cost_per_interval(2500, 300)
print(f"Kosten: {cost:.6f} EUR")
```

### SQL-Kostenberechnung

Beispiel für tägliche Kosten pro Gerät:
```sql
SELECT 
    DATE(d.time) as tag,
    d.device_name,
    SUM((d.multimeter_power / 1000000.0) * (300 / 3600.0) * p.price_eur_per_kwh) as kosten_eur,
    p.price_eur_per_kwh
FROM dect200_data d
CROSS JOIN (
    SELECT price_eur_per_kwh 
    FROM electricity_price_config 
    WHERE valid_to IS NULL OR valid_to > NOW()
    ORDER BY valid_from DESC 
    LIMIT 1
) p
WHERE d.multimeter_power IS NOT NULL
GROUP BY DATE(d.time), d.device_name, p.price_eur_per_kwh
ORDER BY tag DESC;
```

Weitere Beispiele: siehe `example_cost_queries.sql`

## 3. Grafana-Integration

### Wetter-Dashboard
- Temperaturverlauf
- Luftfeuchtigkeit und Luftdruck
- Aktuelle Wetterbedingungen

### Stromkosten-Dashboard
- Tägliche/monatliche Kosten pro Gerät
- Hochrechnung der Jahreskosten
- Vergleich verschiedener Geräte
- Energieverbrauch vs. Temperatur

Beispiele: siehe `GRAFANA_EXAMPLES.md`

## 4. Vollständige Docker-Konfiguration

```bash
docker run -d --restart=unless-stopped \
  --name fritzbox-collector \
  -e FRITZBOX_HOST=192.168.178.1 \
  -e FRITZBOX_USER=deinuser \
  -e FRITZBOX_PASSWORD=deinpasswort \
  -e DECT_AINS=12345,67890 \
  -e SQL_HOST=192.168.178.xx \
  -e SQL_USER=sqluser \
  -e SQL_PASSWORD=sqlpass \
  -e SQL_DB=fritzbox \
  -e COLLECT_INTERVAL=300 \
  -e SPEEDTEST_INTERVAL=3600 \
  -e WEATHER_INTERVAL=3600 \
  -e WEATHER_API_KEY=dein_openweathermap_api_key \
  -e WEATHER_LOCATION="Berlin,DE" \
  -e ELECTRICITY_PRICE_EUR_PER_KWH=0.30 \
  -e LOG_FILE=/config/fritzbox_collector.log \
  -v /mnt/user/appdata/fritzbox_collector/:/config \
  fritzbox-collector
```

## 5. Datenbanktabellen

Das System erstellt automatisch folgende neue Tabellen:

### weather_data
```sql
CREATE TABLE weather_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    location VARCHAR(128),
    temperature_celsius FLOAT,
    feels_like_celsius FLOAT,
    humidity INT,
    pressure INT,
    weather_condition VARCHAR(64),
    weather_description VARCHAR(128),
    wind_speed FLOAT,
    clouds INT,
    time DATETIME
);
```

### electricity_price_config
```sql
CREATE TABLE electricity_price_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    price_eur_per_kwh FLOAT NOT NULL,
    valid_from DATETIME NOT NULL,
    valid_to DATETIME NULL,
    description VARCHAR(255),
    time DATETIME
);
```

## 6. Testen der Installation

Nach dem Start des Containers:

1. **Logs prüfen:**
   ```bash
   docker logs fritzbox-collector
   ```
   
   Erwartete Ausgaben:
   - "Strompreis konfiguriert: 0.3 EUR/kWh"
   - "Frage Wetterdaten ab für: Berlin,DE" (falls API-Key gesetzt)
   - "weather_data Tabelle wurde geprüft/erstellt"

2. **Datenbank prüfen:**
   ```sql
   -- Wetterdaten prüfen
   SELECT * FROM weather_data ORDER BY time DESC LIMIT 5;
   
   -- Strompreis prüfen
   SELECT * FROM electricity_price_config;
   ```

3. **Test-Script ausführen:**
   ```bash
   docker exec fritzbox-collector python3 test_modules.py
   ```

## 7. Fehlerbehebung

### Keine Wetterdaten
- Prüfen Sie, ob `WEATHER_API_KEY` gesetzt ist
- Überprüfen Sie die Logs auf API-Fehler
- Validieren Sie Ihren API-Key bei OpenWeatherMap

### Strompreis wird nicht angezeigt
- Prüfen Sie, ob die Tabelle `electricity_price_config` existiert
- Standard-Fallback ist immer 0,30 EUR/kWh

### Kostenberechnungen fehlerhaft
- Stellen Sie sicher, dass `multimeter_power` nicht NULL ist
- Überprüfen Sie das `COLLECT_INTERVAL` (Standard: 300 Sekunden)
- Passen Sie SQL-Queries an Ihr Intervall an

## 8. Weiterführende Informationen

- **OpenWeatherMap Dokumentation:** https://openweathermap.org/api
- **SQL-Beispiele:** `example_cost_queries.sql`
- **Grafana-Beispiele:** `GRAFANA_EXAMPLES.md`
- **Test-Script:** `test_modules.py`

## 9. Änderungen an bestehenden Features

**Keine Breaking Changes** - Alle bestehenden Features funktionieren weiterhin wie gewohnt:
- FritzBox-Datensammlung
- DECT-Gerätedaten
- Speedtest-Funktionalität
- Benachrichtigungen

Die neuen Features sind optional und können durch Nicht-Setzen der entsprechenden Umgebungsvariablen deaktiviert werden.
