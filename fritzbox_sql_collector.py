import fritzconnection
import mysql.connector
import time

# FritzBox Zugangsdaten
fb = fritzconnection.FritzConnection(address='192.168.178.1', password='dein_passwort')

# SQL Zugangsdaten
sql_config = {
    'user': 'dein_user',
    'password': 'dein_passwort',
    'host': 'dein_db_host',
    'database': 'deine_db'
}

def collect_and_store():
    # Beispiel: Hole aktuelle Verbindungen
    connections = fb.call_action('WANPPPConnection', 'GetStatus')
    status = connections['NewConnectionStatus']
    # Schreibe Status in SQL DB
    conn = mysql.connector.connect(**sql_config)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO fritzbox_status (status, time) VALUES (%s, NOW())", (status,))
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    while True:
        collect_and_store()
        time.sleep(300)  # alle 5 Minuten