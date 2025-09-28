import time
import os
import logging
from fritzconnection import FritzConnection
import mysql.connector
import speedtest
from notify import notify_all

LOG_FILE = os.getenv("LOG_FILE", "/config/fritzbox_collector.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, mode='a')
    ]
)
logger = logging.getLogger(__name__)

FRITZBOX_HOST = os.getenv("FRITZBOX_HOST", "192.168.178.1")
FRITZBOX_USER = os.getenv("FRITZBOX_USER", "deinuser")
FRITZBOX_PASSWORD = os.getenv("FRITZBOX_PASSWORD", "deinpasswort")
DECT_AINS = os.getenv("DECT_AINS", "12345,67890").split(',')

SQL_CONFIG = {
    'user': os.getenv("SQL_USER", "sqluser"),
    'password': os.getenv("SQL_PASSWORD", "sqlpass"),
    'host': os.getenv("SQL_HOST", "sqlhost"),
    'database': os.getenv("SQL_DB", "sqldb"),
    'autocommit': True
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

def _resolve_homeauto_service(fc: FritzConnection) -> tuple[str, set]:
    """Ermittle den konkreten Homeauto-Service-Namen und gebe die verfügbaren Actions zurück."""
    try:
        services = list(fc.services.values())
        candidates = [s for s in services if s.service.startswith("X_AVM-DE_Homeauto")]
        if not candidates:
            logger.error("Kein X_AVM-DE_Homeauto Service gefunden.")
            return "", set()
        # Bevorzuge explizit die Version 1, falls vorhanden
        svc = next((s for s in candidates if s.service.startswith("X_AVM-DE_Homeauto1")), candidates[0])
        actions = set(svc.actions.keys())
        logger.info(f"Nutze Homeauto-Service: {svc.service} mit Actions: {sorted(actions)}")
        return svc.service, actions
    except Exception as e:
        logger.error(f"Konnte Homeauto-Service nicht auflösen: {e}")
        return "", set()

def _read_dect_via_homeauto(fc: FritzConnection, service_name: str, available_actions: set, ain: str) -> dict:
    """Lese DECT-Werte robust: zuerst gezielte Actions, bei 401/Unbekannt -> GetSpecificDeviceInfos-Fallback."""
    ain = ain.strip()
    # 1) bevorzugte, gezielte Actions (wenn vorhanden)
    try:
        if {"GetSwitchState", "GetTemperature"}.issubset(available_actions):
            state = fc.call_action(service_name, "GetSwitchState", NewAIN=ain)["NewSwitchState"]
            temp = fc.call_action(service_name, "GetTemperature", NewAIN=ain)["NewTemperature"]
        else:
            raise RuntimeError("Gezielte State/Temp-Actions nicht verfügbar")
        # Power: je nach Firmware GetSwitchPower oder GetPower
        power = None
        if "GetSwitchPower" in available_actions:
            power = fc.call_action(service_name, "GetSwitchPower", NewAIN=ain).get("NewSwitchPower")
        elif "GetPower" in available_actions:
            power = fc.call_action(service_name, "GetPower", NewAIN=ain).get("NewPower")
        else:
            logger.warning("Weder GetSwitchPower noch GetPower verfügbar – nutze Fallback.")
            raise RuntimeError("Power-Actions nicht verfügbar")
        return {"ain": ain, "state": state, "power": power, "temperature": temp}
    except Exception as e:
        logger.warning(f"Abruf über gezielte Actions fehlgeschlagen ({ain}): {e} – versuche GetSpecificDeviceInfos")

    # 2) Fallback: GetSpecificDeviceInfos (sehr kompatibel)
    try:
        info = fc.call_action(service_name, "GetSpecificDeviceInfos", NewAIN=ain)
        state = info.get("NewSwitchState")
        power = info.get("NewPower") or info.get("NewSwitchPower")
        temp = info.get("NewTemperature")
        if state is None and power is None and temp is None:
            raise RuntimeError(f"Unerwartete Antwort von GetSpecificDeviceInfos: {info}")
        return {"ain": ain, "state": state, "power": power, "temperature": temp}
    except Exception as e:
        logger.error(f"Fallback GetSpecificDeviceInfos fehlgeschlagen ({ain}): {e}")
        return {"ain": ain, "state": None, "power": None, "temperature": None}

def get_fritz_data():
    logger.info("Frage FritzBox-Daten ab...")
    fc = FritzConnection(address=FRITZBOX_HOST, user=FRITZBOX_USER, password=FRITZBOX_PASSWORD)
    data = {}
    try:
        # Versuche zuerst WANIPConnection für Cable Router
        data['online'] = fc.call_action('WANIPConnection', 'GetStatusInfo')['NewConnectionStatus']
        data['external_ip'] = fc.call_action('WANIPConnection', 'GetExternalIPAddress')['NewExternalIPAddress']
        logger.info(f"Online-Status (Cable): {data['online']}, Externe IP: {data['external_ip']}")
    except Exception as e:
        try:
            # Fallback auf WANPPPConnection für DSL Router
            data['online'] = fc.call_action('WANPPPConnection', 'GetStatus')['NewConnectionStatus']
            data['external_ip'] = fc.call_action('WANPPPConnection', 'GetExternalIPAddress')['NewExternalIPAddress']
            logger.info(f"Online-Status (DSL): {data['online']}, Externe IP: {data['external_ip']}")
        except Exception as e2:
            logger.error(f"Fehler beim Abfragen FritzBox-Status (beide Methoden): Cable: {e}, DSL: {e2}")
            notify_all(f"Fehler beim Abfragen FritzBox-Status: {e2}")
            data['online'] = None
            data['external_ip'] = None
    try:
        data['active_devices'] = fc.call_action('Hosts', 'GetHostNumberOfEntries')['NewHostNumberOfEntries']
        logger.info(f"Aktive Geräte: {data['active_devices']}")
    except Exception as e:
        logger.error(f"Fehler beim Abfragen der Geräteanzahl: {e}")
        notify_all(f"Fehler beim Abfragen Geräteanzahl: {e}")
        data['active_devices'] = None

    # Homeauto-Service auflösen und DECT lesen
    data['dect'] = []
    service_name, actions = _resolve_homeauto_service(fc)
    if not service_name:
        logger.error("Kein Homeauto-Service gefunden – DECT-Daten werden mit None befüllt.")
        for ain in DECT_AINS:
            data['dect'].append({'ain': ain.strip(), 'state': None, 'power': None, 'temperature': None})
        return data

    for ain in DECT_AINS:
        device = _read_dect_via_homeauto(fc, service_name, actions, ain)
        if device['state'] is None and device['power'] is None and device['temperature'] is None:
            notify_all(f"Fehler beim Abfragen DECT {ain} – siehe Log (Action-Mapping/Firmware)")
            logger.error(f"Fehler beim Abfragen DECT {ain}")
        else:
            logger.info(f"DECT {ain}: State={device['state']}, Power={device['power']}, Temp={device['temperature']}")
        data['dect'].append(device)
    return data

def write_to_sql(data):
    logger.info("Schreibe FritzBox-Daten in die Datenbank...")
    for attempt in range(3):
        try:
            conn = mysql.connector.connect(**SQL_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fritzbox_status (online, external_ip, active_devices, time)
                VALUES (%s, %s, %s, NOW())
            """, (data['online'], data['external_ip'], data['active_devices']))
            for device in data['dect']:
                cursor.execute("""
                    INSERT INTO dect200_data (ain, state, power, temperature, time)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (device['ain'], device['state'], device['power'], device['temperature']))
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
            return {'ping_ms': ping, 'download_mbps': download, 'upload_mbps': upload}
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
                cursor.execute("""
                    INSERT INTO speedtest_results (ping_ms, download_mbps, upload_mbps, time)
                    VALUES (%s, %s, %s, NOW())
                """, (result['ping_ms'], result['download_mbps'], result['upload_mbps']))
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
    last_speedtest = 0
    create_tables()
    logger.info("Starte FritzBox-Collector...")
    while True:
        fritz_data = get_fritz_data()
        write_to_sql(fritz_data)
        now = time.time()
        if now - last_speedtest > speedtest_interval:
            speed_result = run_speedtest()
            write_speedtest_to_sql(speed_result)
            last_speedtest = now
        time.sleep(interval)