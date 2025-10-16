# FritzBox Collector für Unraid & Grafana

Dieses Projekt sammelt regelmäßig Statusdaten von deiner FritzBox und den DECT-Steckdosen, führt Speedtests durch und schreibt alles in eine MariaDB/MySQL. Die Daten können z.B. mit Grafana visualisiert werden.

## Features
- Abfrage FritzBox- und DECT-Daten
- Speedtest mit automatischer Serverwahl
- **WeatherAPI-Integration**: Abrufen von Wetterdaten (z.B. von OpenWeatherMap)
- **Strompreis-Tracking**: Fester Strompreis (30 Eurocent/kWh) für Kostenberechnungen
- Automatische SQL-Tabellenerstellung beim Start
- Fehlerbehandlung mit Retry & Logging
- Persistente Logs (`/config`)
- Healthcheck für Docker
- Optional: Benachrichtigung bei Fehlern per Discord-Webhook und Telegram

## Start mit Docker (empfohlen in Unraid)
```bash
docker build -t fritzbox-collector .
docker run -d --restart=unless-stopped \
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
  -e DISCORD_WEBHOOK=https://discord.com/api/webhooks/... (optional) \
  -e TELEGRAM_TOKEN=xxx (optional) \
  -e TELEGRAM_CHATID=yyy (optional) \
  -v /mnt/user/appdata/fritzbox_collector/:/config \
  fritzbox-collector
```

## Datenbank-Tabellen
Das Skript legt die nötigen Tabellen automatisch an:
- fritzbox_status
- dect200_data
- speedtest_results
- **weather_data**: Wetterdaten (Temperatur, Luftfeuchtigkeit, Wetterbedingungen, etc.)
- **electricity_price_config**: Strompreis-Konfiguration für Kostenberechnungen

## Grafana
- MariaDB als Datenquelle
- Dashboards für Status, DECT und Speedtest

## Konfiguration

### Umgebungsvariablen

#### FritzBox-Konfiguration
- `FRITZBOX_HOST`: IP-Adresse der FritzBox (Standard: 192.168.178.1)
- `FRITZBOX_USER`: Benutzername für FritzBox-Zugriff
- `FRITZBOX_PASSWORD`: Passwort für FritzBox-Zugriff
- `DECT_AINS`: Kommaseparierte Liste der DECT-AIDs (optional, leer = alle Geräte)

#### Datenbank-Konfiguration
- `SQL_HOST`: Hostname/IP der MariaDB/MySQL-Datenbank
- `SQL_USER`: Datenbank-Benutzername
- `SQL_PASSWORD`: Datenbank-Passwort
- `SQL_DB`: Datenbankname

#### Intervall-Konfiguration
- `COLLECT_INTERVAL`: Intervall für FritzBox-Datensammlung in Sekunden (Standard: 300 = 5 Minuten)
- `SPEEDTEST_INTERVAL`: Intervall für Speedtests in Sekunden (Standard: 3600 = 1 Stunde)
- `WEATHER_INTERVAL`: Intervall für Wetterabfragen in Sekunden (Standard: 3600 = 1 Stunde)

#### Wetter-API-Konfiguration
- `WEATHER_API_KEY`: API-Key für OpenWeatherMap (erforderlich für Wetterdaten)
- `WEATHER_LOCATION`: Standort für Wetterabfrage (Format: "Stadt,Ländercode", z.B. "Berlin,DE")

Wetter-API-Key erhalten:
1. Registrierung bei [OpenWeatherMap](https://openweathermap.org/api)
2. Kostenlosen API-Key generieren
3. Key als Umgebungsvariable `WEATHER_API_KEY` setzen

#### Strompreis-Konfiguration
- `ELECTRICITY_PRICE_EUR_PER_KWH`: Strompreis in EUR pro kWh (Standard: 0.30 = 30 Eurocent/kWh)

Der Strompreis wird für Kostenberechnungen verwendet und in der Datenbank gespeichert. 
Der Wert kann über die Datenbanktabelle `electricity_price_config` angepasst werden.

#### Logging & Benachrichtigungen
- `LOG_FILE`: Pfad zur Logdatei (Standard: /config/fritzbox_collector.log)
- `DISCORD_WEBHOOK`: Discord Webhook-URL für Fehlerbenachrichtigungen (optional)
- `TELEGRAM_TOKEN`: Telegram Bot Token für Benachrichtigungen (optional)
- `TELEGRAM_CHATID`: Telegram Chat-ID für Benachrichtigungen (optional)

## Benachrichtigungen
- Discord: Erstelle einen Webhook in deinem Channel und trage die URL als Umgebungsvariable ein.
- Telegram: Bot erstellen, Token und ChatID als Umgebungsvariablen hinterlegen.

## Healthcheck
Der Healthcheck prüft, ob die Logdatei regelmäßig geschrieben wird.

## Lizenz
MIT