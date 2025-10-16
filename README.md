# FritzBox Collector für Unraid & Grafana

Dieses Projekt sammelt regelmäßig Statusdaten von deiner FritzBox und den DECT-Steckdosen, führt Speedtests durch und schreibt alles in eine MariaDB/MySQL. Die Daten können z.B. mit Grafana visualisiert werden.

**Neu:** Unterstützung für Tibber Pulse IR zur Erfassung von Energieverbrauchsdaten!

## Features
- Abfrage FritzBox- und DECT-Daten
- Speedtest mit automatischer Serverwahl
- **Tibber Pulse IR Integration** - Erfassung von Energieverbrauchs- und Kostendaten
- Automatische SQL-Tabellenerstellung beim Start
- Fehlerbehandlung mit Retry & Logging
- Persistente Logs (`/config`)
- Healthcheck für Docker
- Optional: Benachrichtigung bei Fehlern per Discord-Webhook und Telegram

## Start mit Docker (empfohlen in Unraid)

### Option 1: Docker Compose (empfohlen für neue Setups)

```bash
# 1. Passe docker-compose.yml an (Passwörter, FritzBox-Daten, Tibber-Token)
# 2. Starte alle Services
docker-compose up -d

# 3. Logs anschauen
docker-compose logs -f fritzbox-collector

# 4. Grafana öffnen: http://localhost:3000 (admin/change_this_password)
```

### Option 2: Docker Run

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
  -e TIBBER_TOKEN=your_tibber_api_token (optional) \
  -e TIBBER_INTERVAL=3600 (optional, default: 3600) \
  -e LOG_FILE=/config/fritzbox_collector.log \
  -e DISCORD_WEBHOOK=https://discord.com/api/webhooks/... (optional) \
  -e TELEGRAM_TOKEN=xxx (optional) \
  -e TELEGRAM_CHATID=yyy (optional) \
  -v /mnt/user/appdata/fritzbox_collector/:/config \
  fritzbox-collector
```

### Umgebungsvariablen

| Variable | Beschreibung | Standard | Erforderlich |
|----------|--------------|----------|--------------|
| FRITZBOX_HOST | IP-Adresse der FritzBox | 192.168.178.1 | Ja |
| FRITZBOX_USER | FritzBox Benutzername | - | Ja |
| FRITZBOX_PASSWORD | FritzBox Passwort | - | Ja |
| DECT_AINS | Kommaseparierte Liste der DECT AIDs | - | Nein |
| SQL_HOST | MariaDB/MySQL Host | - | Ja |
| SQL_USER | Datenbank Benutzer | - | Ja |
| SQL_PASSWORD | Datenbank Passwort | - | Ja |
| SQL_DB | Datenbank Name | - | Ja |
| COLLECT_INTERVAL | Datensammel-Intervall in Sekunden | 300 | Nein |
| SPEEDTEST_INTERVAL | Speedtest-Intervall in Sekunden | 3600 | Nein |
| **TIBBER_TOKEN** | Tibber API Personal Access Token | - | Nein* |
| **TIBBER_INTERVAL** | Tibber Datensammel-Intervall in Sekunden | 3600 | Nein |
| LOG_FILE | Pfad zur Logdatei | /config/fritzbox_collector.log | Nein |
| DISCORD_WEBHOOK | Discord Webhook URL | - | Nein |
| TELEGRAM_TOKEN | Telegram Bot Token | - | Nein |
| TELEGRAM_CHATID | Telegram Chat ID | - | Nein |

*Nur erforderlich, wenn Tibber-Integration genutzt werden soll.

## Datenbank-Tabellen
Das Skript legt die nötigen Tabellen automatisch an:
- fritzbox_status
- dect200_data
- speedtest_results
- **tibber_energy_data** (wenn TIBBER_TOKEN gesetzt ist)

## Tibber Integration

### Voraussetzungen
1. Tibber Konto mit aktiviertem Pulse IR Gerät
2. Personal Access Token von Tibber ([hier generieren](https://developer.tibber.com/settings/access-token))

### Verbindung testen (Optional aber empfohlen)

Bevor du den Container startest, kannst du deine Tibber-Konfiguration testen:

```bash
# Python-Abhängigkeiten installieren (falls noch nicht installiert)
pip3 install gql[all] aiohttp

# Test-Skript ausführen
python3 test_tibber_connection.py YOUR_TIBBER_TOKEN
```

Das Skript zeigt dir:
- ✅ Ob dein Token gültig ist
- 📊 Deine Tibber-Kontoinformationen
- 🏠 Alle verbundenen Homes
- 📈 Ob historische Daten verfügbar sind

### Einrichtung
1. Generiere einen Personal Access Token in deinem Tibber-Account
2. Setze die Umgebungsvariable `TIBBER_TOKEN` mit deinem Token
3. Optional: Passe `TIBBER_INTERVAL` an (Standard: 3600 Sekunden = 1 Stunde)
4. Starte den Container neu

### Erfasste Daten
Die Tibber-Integration erfasst folgende Daten:
- **Echtzeit-Leistung** (Power in Watt)
- **Energieverbrauch** (Consumption in kWh)
- **Akkumulierte Kosten** (Accumulated Cost)
- **Spannungen** (L1, L2, L3)
- **Ströme** (L1, L2, L3)
- **Leistungsfaktor** (Power Factor)
- **Signalstärke** (Signal Strength)
- Min/Max/Average Power Werte

### Retry-Mechanismus
Die Tibber-Integration implementiert einen exponentiellen Backoff-Algorithmus mit Jitter, wie von Tibber empfohlen:
- Automatische Wiederholungsversuche bei Fehlern
- Exponentielles Backoff (1s, 2s, 4s, 8s, ...)
- Maximale Verzögerung: 60 Sekunden
- Jitter: +/- 10% zur Vermeidung von Thundering Herd

### WebSocket-Verbindung
Die Integration unterstützt auch Echtzeit-Daten über WebSocket-Subscriptions:
- Automatische Wiederverbindung bei Unterbrechungen
- Graceful Handling von Verbindungsabbrüchen
- Exponentieller Backoff für Reconnects (max. 5 Minuten)

## Grafana
- MariaDB als Datenquelle
- Dashboards für Status, DECT und Speedtest
- **Tibber Energy Dashboard** für Energieverbrauch und Kostenanalyse

### Tibber Dashboard Importieren
1. Öffne Grafana
2. Gehe zu Dashboards > Import
3. Lade die Datei `grafana-dashboard-tibber.json` hoch
4. Wähle deine MariaDB-Datenquelle aus
5. Klicke auf Import

Das Dashboard enthält folgende Panels:
- **Echtzeit-Leistungsverbrauch** - Live-Anzeige der aktuellen Leistung in Watt
- **Aktuelle Leistung** - Gauge mit Schwellenwerten
- **Akkumulierter Verbrauch** - Gesamtverbrauch in kWh
- **Stündlicher Energieverbrauch** - Balkendiagramm mit historischen Daten
- **Akkumulierte Energiekosten** - Kostenentwicklung über Zeit
- **Spannungen (L1, L2, L3)** - Dreiphasige Spannungsüberwachung
- **Ströme (L1, L2, L3)** - Dreiphasige Stromüberwachung

## Benachrichtigungen
- Discord: Erstelle einen Webhook in deinem Channel und trage die URL als Umgebungsvariable ein.
- Telegram: Bot erstellen, Token und ChatID als Umgebungsvariablen hinterlegen.

## Healthcheck
Der Healthcheck prüft, ob die Logdatei regelmäßig geschrieben wird.

## Lizenz
MIT