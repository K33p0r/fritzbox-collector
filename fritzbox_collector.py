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

def get_fritz_data():
    logger.info("Frage FritzBox-Daten ab...")
    fc = FritzConnection(address=FRITZBOX_HOST, user=FRITZBOX_USER, password=FRITZBOX_PASSWORD)
    data = {}
    try:
        data['online'] = fc.call_action('WANPPPConnection', 'GetStatus')['NewConnectionStatus']
        data['external_ip'] = fc.call_action('WANPPPConnection', 'GetExternalIPAddress')['NewExternalIPAddress']
        logger.info(f"Online-Status: {data['online']}, Externe IP: {data['external_ip']}")
    except Exception as e:
        logger.error(f"Fehler beim Abfragen FritzBox-Status: {e}")
        notify_all(f"Fehler beim Abfragen FritzBox-Status: {e}")
        data['online'] = None
        data['external_ip'] = None
    try:
        data['active_devices'] = fc.call_action('Hosts', 'GetHostNumberOfEntries')['NewHostNumberOfEntries']
        logger.info(f"Aktive Geräte: {data['active_devices']}")
    except Exception as e:
        logger.error(f"Fehler beim Abfragen der Geräteanzahl: {e}")
        notify_all(f"Fehler beim Abfragen Geräteanzahl: {e}")
        data['active_devices'] = None
    data['dect'] = []
    for ain in DECT_AINS:
        try:
            switch_state = fc.call_action('X_AVM-DE_Homeauto', 'GetSwitchState', NewAIN=ain.strip())['NewSwitchState']
            power = fc.call_action('X_AVM-DE_Homeauto', 'GetSwitchPower', NewAIN=ain.strip())['NewSwitchPower']
            temp = fc.call_action('X_AVM-DE_Homeauto', 'GetTemperature', NewAIN=ain.strip())['NewTemperature']
            data['dect'].append({'ain': ain, 'state': switch_state, 'power': power, 'temperature': temp})
            logger.info(f"DECT {ain}: State={switch_state}, Power={power}, Temp={temp}")
        except Exception as e:
            logger.error(f"Fehler beim Abfragen DECT {ain}: {e}")
            notify_all(f"Fehler beim Abfragen DECT {ain}: {e}")
            data['dect'].append({'ain': ain, 'state': None, 'power': None, 'temperature': None})
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