import requests
import time
import mysql.connector

# FritzBox Zugangsdaten und DECT200-IDs
FRITZBOX_URL = "http://192.168.178.1:49000"
USER = "deinuser"
PASSWORD = "deinpasswort"
DECT_IDS = ["12345", "67890"]  # DECT200-AINs

SQL_CONFIG = {
    'user': 'sqluser',
    'password': 'sqlpass',
    'host': 'sqlhost',
    'database': 'sqldb'
}

def aha_request(cmd, ain=None):
    params = {
        'switchcmd': cmd,
        'sid': get_sid()
    }
    if ain:
        params['ain'] = ain
    url = f"http://{FRITZBOX_URL}/webservices/homeautoswitch.lua"
    resp = requests.get(url, params=params, timeout=10)
    return resp.text

def get_sid():
    # Session-ID holen (Login)
    url = f"http://{FRITZBOX_URL}/login_sid.lua"
    requests.get(url, timeout=10)
    # Hier müsste das Challenge-Response-Verfahren implementiert werden!
    # Alternativ, wenn du kein User-Passwort hast, einfach sid auslesen.
    # Für produktives Skript siehe z.B. fritzconnection!
    sid = "0000000000000000"  # Dummy für Beispiel
    return sid

def collect_status():
    # Online-Status
    online_status = aha_request("getWANStatus")
    # DECT200 Daten
    dect_data = []
    for ain in DECT_IDS:
        power = aha_request("getswitchpower", ain)
        state = aha_request("getswitchstate", ain)
        temperature = aha_request("gettemperature", ain)
        dect_data.append({'ain': ain, 'power': power, 'state': state, 'temperature': temperature})

    # Daten in SQL schreiben
    conn = mysql.connector.connect(**SQL_CONFIG)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO fritzbox_status (online_status, time) VALUES (%s, NOW())", (online_status,))
    for data in dect_data:
        cursor.execute("INSERT INTO dect200_data (ain, power, state, temperature, time) VALUES (%s, %s, %s, %s, NOW())",
            (data['ain'], data['power'], data['state'], data['temperature']))
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    while True:
        collect_status()
        time.sleep(300)  # alle 5 Minuten