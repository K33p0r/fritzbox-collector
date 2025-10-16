import time
import os
import re
import logging
from fritzconnection import FritzConnection
import mysql.connector
import speedtest
from notify import notify_all
from weather_collector import create_weather_table, collect_weather
from electricity_price import (
    create_electricity_price_table,
    store_electricity_price,
    ELECTRICITY_PRICE_EUR_PER_KWH
)

# Optional: spezifische Exceptions, falls verfügbar
try:
    from fritzconnection.core.exceptions import FritzArrayIndexError
except Exception:  # Fallback, wenn Import nicht möglich
    class FritzArrayIndexError(Exception):
        pass

LOG_FILE = os.getenv("LOG_FILE", "/config/fritzbox_collector.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, mode="a")
    ]
)
logger = logging.getLogger(__name__)

FRITZBOX_HOST = os.getenv("FRITZBOX_HOST", "192.168.178.1")
FRITZBOX_USER = os.getenv("FRITZBOX_USER", "deinuser")
FRITZBOX_PASSWORD = os.getenv("FRITZBOX_PASSWORD", "deinpasswort")

# Optionaler Filter: Wenn leer -> ALLE Geräte speichern
_DECT_AINS_RAW = os.getenv("DECT_AINS", "").strip()
DECT_AINS_FILTER = [a.strip() for a in _DECT_AINS_RAW.split(",") if a.strip()]

SQL_CONFIG = {
    "user": os.getenv("SQL_USER", "sqluser"),
    "password": os.getenv("SQL_PASSWORD", "sqlpass"),
    "host": os.getenv("SQL_HOST", "sqlhost"),
    "database": os.getenv("SQL_DB", "sqldb"),
    "autocommit": True
}

def create_tables():
    logger.info("Prüfe und erstelle ggf. SQL-Tabellen...")
    table_sql = [
        """CREATE TABLE IF NOT EXISTS fritzbox_status (
            id INT AUTO_INCREMENT PRIMARY KEY,
            online VARCHAR(32),
            external_ip VARCHAR(64),
            active_devices INT,
            time DATETIME
        )""",
        """CREATE TABLE IF NOT EXISTS dect200_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ain VARCHAR(32),
            state INT,
            power INT,
            temperature INT,
            product_name VARCHAR(128),
            device_name VARCHAR(128),
            multimeter_power INT,
            temperature_celsius INT,
            switch_state VARCHAR(16),
            hkr_is_temperature INT,
            hkr_set_ventil_status VARCHAR(16),
            hkr_set_temperature INT,
            time DATETIME
        )""",
        """CREATE TABLE IF NOT EXISTS speedtest_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ping_ms FLOAT,
            download_mbps FLOAT,
            upload_mbps FLOAT,
            time DATETIME
        )"""
    ]
    try:
        conn = mysql.connector.connect(**SQL_CONFIG)
        cursor = conn.cursor()
        for sql in table_sql:
            cursor.execute(sql)
        cursor.close()
        conn.close()
        logger.info("Tabellen wurden geprüft/erstellt.")
    except Exception as e:
        logger.error(f"Fehler bei Tabellenprüfung/-erstellung: {e}")
        notify_all(f"SQL Tabellen konnten nicht angelegt werden: {e}")

    # Nachträglich fehlende Spalten ergänzen (Migration)
    try:
        ensure_columns()
    except Exception as e:
        logger.error(f"Fehler beim Ergänzen fehlender Spalten: {e}")
        notify_all(f"SQL Spalten konnten nicht ergänzt werden: {e}")
    
    # Wetter- und Strompreis-Tabellen erstellen
    try:
        create_weather_table()
        create_electricity_price_table()
        store_electricity_price()
        logger.info(f"Strompreis konfiguriert: {ELECTRICITY_PRICE_EUR_PER_KWH} EUR/kWh")
    except Exception as e:
        logger.error(f"Fehler beim Erstellen zusätzlicher Tabellen: {e}")
        notify_all(f"Zusätzliche Tabellen konnten nicht angelegt werden: {e}")

def ensure_columns():
    # Prüfe vorhandene Spalten und ergänze ggf. via ALTER TABLE
    needed = {
        "product_name": "VARCHAR(128)",
        "device_name": "VARCHAR(128)",
        "multimeter_power": "INT",
        "temperature_celsius": "INT",
        "switch_state": "VARCHAR(16)",
        "hkr_is_temperature": "INT",
        "hkr_set_ventil_status": "VARCHAR(16)",
        "hkr_set_temperature": "INT"
    }
    conn = mysql.connector.connect(**SQL_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'dect200_data'
    """, (SQL_CONFIG["database"],))
    existing = {row[0] for row in cursor.fetchall()}
    for col, coltype in needed.items():
        if col not in existing:
            alter = f"ALTER TABLE dect200_data ADD COLUMN {col} {coltype} NULL"
            cursor.execute(alter)
            logger.info(f"Spalte ergänzt: {col} {coltype}")
    cursor.close()
    conn.close()

def _resolve_homeauto_service(fc: FritzConnection) -> str | None:
    """Service-Namen ermitteln, z. B. 'X_AVM-DE_Homeauto1'."""
    try:
        for name in fc.services.keys():
            if name.startswith("X_AVM-DE_Homeauto"):
                return name
    except Exception as e:
        logger.error(f"Homeauto-Service konnte nicht ermittelt werden: {e}")
    return None

def _is_index_out_of_range_error(err: Exception) -> bool:
    rep = repr(err)
    return ("SpecifiedArrayIndexInvalid" in rep) or ("errorCode: 713" in rep) or isinstance(err, FritzArrayIndexError)

def _enumerate_homeauto_devices(fc: FritzConnection, service_name: str, max_iter: int = 256) -> list[dict]:
    """Liest Geräte über GetGenericDeviceInfos per Index 0..n, bis 713 kommt."""
    devices = []
    for i in range(max_iter):
        try:
            info = fc.call_action(service_name, "GetGenericDeviceInfos", NewIndex=i)
            devices.append(info)
        except Exception as e:
            if _is_index_out_of_range_error(e):
                logger.info(f"Geräte-Auflistung beendet bei Index {i} (713).")
                break
            logger.error(f"GetGenericDeviceInfos Fehler bei Index {i}: {e}")
            notify_all(f"Fehler bei GetGenericDeviceInfos Index {i}: {e}")
            break
    return devices

def _compact_ain(ain: str) -> str:
    return re.sub(r"\s+", "", ain or "").strip()

def _normalize_device_info(info: dict) -> dict:
    """Extrahiert und normalisiert AIN, Zustand, Leistung, Temperatur und weitere Felder."""
    raw_ain = info.get("NewAIN") or ""
    ain = _compact_ain(raw_ain)
    if not ain:
        # Ungültiger Datensatz (z. B. 'unknown' Gerät ohne AIN)
        return {
            "ain": None,
            "state": None,
            "power": None,
            "temperature": None,
            "product_name": None,
            "device_name": None,
            "multimeter_power": None,
            "temperature_celsius": None,
            "switch_state": None,
            "hkr_is_temperature": None,
            "hkr_set_ventil_status": None,
            "hkr_set_temperature": None
        }

    switch_state_str = str(info.get("NewSwitchState") or "").upper()  # OFF/ON/...
    state_map = {"ON": 1, "OFF": 0}
    state = state_map.get(switch_state_str, None)

    multimeter_power = info.get("NewMultimeterPower")
    temperature_celsius = info.get("NewTemperatureCelsius")

    # Integer-Wandlungen mit Fail-Safe
    try:
        multimeter_power = int(multimeter_power) if multimeter_power is not None else None
    except Exception:
        multimeter_power = None
    try:
        temperature_celsius = int(temperature_celsius) if temperature_celsius is not None else None
    except Exception:
        temperature_celsius = None

    # Für Abwärtskompatibilität auch alte Spalten befüllen
    power = multimeter_power
    temperature = temperature_celsius

    return {
        "ain": ain,
        "state": state,  # 0/1/NULL
        "power": power,  # alias zu multimeter_power (mW)
        "temperature": temperature,  # alias zu temperature_celsius (0.1 °C)
        "product_name": info.get("NewProductName"),
        "device_name": info.get("NewDeviceName"),
        "multimeter_power": multimeter_power,
        "temperature_celsius": temperature_celsius,
        "switch_state": info.get("NewSwitchState"),
        "hkr_is_temperature": info.get("NewHkrIsTemperature"),
        "hkr_set_ventil_status": info.get("NewHkrSetVentilStatus"),
        "hkr_set_temperature": info.get("NewHkrSetTemperature"),
    }

def get_fritz_data():
    logger.info("Frage FritzBox-Daten ab...")
    fc = FritzConnection(address=FRITZBOX_HOST, user=FRITZBOX_USER, password=FRITZBOX_PASSWORD)
    data = {}

    # Online-/IP-Infos
    try:
        data["online"] = fc.call_action("WANIPConnection", "GetStatusInfo")["NewConnectionStatus"]
        data["external_ip"] = fc.call_action("WANIPConnection", "GetExternalIPAddress")["NewExternalIPAddress"]
        logger.info(f"Online-Status (Cable): {data['online']}, Externe IP: {data['external_ip']}")
    except Exception as e:
        try:
            data["online"] = fc.call_action("WANPPPConnection", "GetStatus")["NewConnectionStatus"]
            data["external_ip"] = fc.call_action("WANPPPConnection", "GetExternalIPAddress")["NewExternalIPAddress"]
            logger.info(f"Online-Status (DSL): {data['online']}, Externe IP: {data['external_ip']}")
        except Exception as e2:
            logger.error(f"Fehler beim Abfragen FritzBox-Status (beide Methoden): Cable: {e}, DSL: {e2}")
            notify_all(f"Fehler beim Abfragen FritzBox-Status: {e2}")
            data["online"] = None
            data["external_ip"] = None

    # Aktive Geräte (LAN/WLAN)
    try:
        data["active_devices"] = fc.call_action("Hosts", "GetHostNumberOfEntries")["NewHostNumberOfEntries"]
        logger.info(f"Aktive Geräte: {data['active_devices']}")
    except Exception as e:
        logger.error(f"Fehler beim Abfragen der Geräteanzahl: {e}")
        notify_all(f"Fehler beim Abfragen Geräteanzahl: {e}")
        data["active_devices"] = None

    # Smart-Home über Homeauto-TR-064
    data["dect"] = []
    service_name = _resolve_homeauto_service(fc)
    if not service_name:
        logger.error("Kein X_AVM-DE_Homeauto Service gefunden – DECT-Daten werden leer gesetzt.")
        return data

    raw_devices = _enumerate_homeauto_devices(fc, service_name)

    # Normalisieren und optional filtern
    normalized = []
    for info in raw_devices:
        dev = _normalize_device_info(info)
        if not dev["ain"]:
            continue
        if DECT_AINS_FILTER:
            ain_compact = dev["ain"].replace(" ", "")
            if not any(ain_compact == target.replace(" ", "") for target in DECT_AINS_FILTER):
                continue
        normalized.append(dev)

    # Logging
    for d in normalized:
        logger.info(
            f"DECT {d['ain']}: "
            f"State={d['state']}({d['switch_state']}), "
            f"Power(mW)={d['multimeter_power']}, "
            f"Temp(0.1C)={d['temperature_celsius']}, "
            f"Prod='{d['product_name']}', Name='{d['device_name']}'"
        )

    data["dect"] = normalized
    return data

def write_to_sql(data):
    logger.info("Schreibe FritzBox-Daten in die Datenbank...")
    for attempt in range(3):
        try:
            conn = mysql.connector.connect(**SQL_CONFIG)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO fritzbox_status (online, external_ip, active_devices, time)
                VALUES (%s, %s, %s, NOW())
                """,
                (data.get("online"), data.get("external_ip"), data.get("active_devices"))
            )
            for device in data.get("dect", []):
                cursor.execute(
                    """
                    INSERT INTO dect200_data (
                        ain, state, power, temperature,
                        product_name, device_name, multimeter_power, temperature_celsius,
                        switch_state, hkr_is_temperature, hkr_set_ventil_status, hkr_set_temperature, time
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        device["ain"],
                        device["state"],
                        device["power"],
                        device["temperature"],
                        device["product_name"],
                        device["device_name"],
                        device["multimeter_power"],
                        device["temperature_celsius"],
                        device["switch_state"],
                        device["hkr_is_temperature"],
                        device["hkr_set_ventil_status"],
                        device["hkr_set_temperature"],
                    )
                )
            cursor.close()
            conn.close()
            logger.info("FritzBox- und DECT-Daten erfolgreich gespeichert.")
            return
        except Exception as e:
            logger.error(f"Fehler beim Schreiben in die Datenbank (Versuch {attempt+1}): {e}")
            notify_all(f"Fehler beim Schreiben FritzBox-Daten: {e}")
            time.sleep(10)
    logger.error("Daten konnten nach 3 Versuchen nicht geschrieben werden.")

def run_speedtest():
    logger.info("Starte Speedtest...")
    for attempt in range(3):
        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            download = st.download() / 1_000_000
            upload = st.upload() / 1_000_000
            ping = st.results.ping
            logger.info(f"Speedtest: Ping={ping} ms, Download={download:.2f} Mbps, Upload={upload:.2f} Mbps")
            return {"ping_ms": ping, "download_mbps": download, "upload_mbps": upload}
        except Exception as e:
            logger.error(f"Speedtest Fehler (Versuch {attempt+1}): {e}")
            notify_all(f"Fehler beim Speedtest: {e}")
            time.sleep(10)
    return None

def write_speedtest_to_sql(result):
    if result:
        logger.info("Schreibe Speedtest-Ergebnisse in die Datenbank...")
        for attempt in range(3):
            try:
                conn = mysql.connector.connect(**SQL_CONFIG)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO speedtest_results (ping_ms, download_mbps, upload_mbps, time)
                    VALUES (%s, %s, %s, NOW())
                    """,
                    (result["ping_ms"], result["download_mbps"], result["upload_mbps"])
                )
                cursor.close()
                conn.close()
                logger.info("Speedtest-Daten erfolgreich gespeichert.")
                return
            except Exception as e:
                logger.error(f"Fehler beim Schreiben Speedtest in DB (Versuch {attempt+1}): {e}")
                notify_all(f"Fehler beim Schreiben Speedtest-Daten: {e}")
                time.sleep(10)
        logger.error("Speedtest-Daten konnten nach 3 Versuchen nicht geschrieben werden.")

if __name__ == "__main__":
    interval = int(os.getenv("COLLECT_INTERVAL", "300"))
    speedtest_interval = int(os.getenv("SPEEDTEST_INTERVAL", "3600"))
    weather_interval = int(os.getenv("WEATHER_INTERVAL", "3600"))  # Standard: stündlich
    last_speedtest = 0
    last_weather = 0
    create_tables()
    logger.info("Starte FritzBox-Collector...")
    logger.info(f"Strompreis: {ELECTRICITY_PRICE_EUR_PER_KWH} EUR/kWh")
    while True:
        fritz_data = get_fritz_data()
        write_to_sql(fritz_data)
        now = time.time()
        if now - last_speedtest > speedtest_interval:
            speed_result = run_speedtest()
            write_speedtest_to_sql(speed_result)
            last_speedtest = now
        if now - last_weather > weather_interval:
            collect_weather()
            last_weather = now
        time.sleep(interval)