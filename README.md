# FritzBox Collector für Unraid & Grafana

Dieses Projekt sammelt regelmäßig Statusdaten von deiner FritzBox und den DECT-Steckdosen, führt Speedtests durch und schreibt alles in eine MariaDB/MySQL. Die Daten können z.B. mit Grafana visualisiert werden.

## Features
- Abfrage FritzBox- und DECT-Daten
- Speedtest mit automatischer Serverwahl
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

## Grafana
- MariaDB als Datenquelle
- Dashboards für Status, DECT und Speedtest

## Benachrichtigungen
- Discord: Erstelle einen Webhook in deinem Channel und trage die URL als Umgebungsvariable ein.
- Telegram: Bot erstellen, Token und ChatID als Umgebungsvariablen hinterlegen.

## Healthcheck
Der Healthcheck prüft, ob die Logdatei regelmäßig geschrieben wird.

## Lizenz
MIT