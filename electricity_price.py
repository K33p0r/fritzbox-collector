"""
Electricity Price Configuration Module

Verwaltet den Strompreis für Berechnungen und Auswertungen.
"""
import os
import logging
import mysql.connector
from notify import notify_all

logger = logging.getLogger(__name__)

# Strompreis-Konstante: 30 Eurocent pro kWh = 0.30 EUR/kWh
ELECTRICITY_PRICE_EUR_PER_KWH = float(os.getenv("ELECTRICITY_PRICE_EUR_PER_KWH", "0.30"))

# SQL-Konfiguration (wird von fritzbox_collector.py übernommen)
SQL_CONFIG = {
    "user": os.getenv("SQL_USER", "sqluser"),
    "password": os.getenv("SQL_PASSWORD", "sqlpass"),
    "host": os.getenv("SQL_HOST", "sqlhost"),
    "database": os.getenv("SQL_DB", "sqldb"),
    "autocommit": True
}


def create_electricity_price_table():
    """Erstellt die Tabelle für Strompreis-Konfiguration, falls sie nicht existiert."""
    logger.info("Prüfe und erstelle ggf. electricity_price_config Tabelle...")
    table_sql = """CREATE TABLE IF NOT EXISTS electricity_price_config (
        id INT AUTO_INCREMENT PRIMARY KEY,
        price_eur_per_kwh FLOAT NOT NULL,
        valid_from DATETIME NOT NULL,
        valid_to DATETIME NULL,
        description VARCHAR(255),
        time DATETIME
    )"""
    
    try:
        conn = mysql.connector.connect(**SQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(table_sql)
        cursor.close()
        conn.close()
        logger.info("electricity_price_config Tabelle wurde geprüft/erstellt.")
    except Exception as e:
        logger.error(f"Fehler bei electricity_price_config Tabellenprüfung/-erstellung: {e}")
        notify_all(f"Strompreis-Tabelle konnte nicht angelegt werden: {e}")
        raise


def store_electricity_price():
    """
    Speichert den aktuellen Strompreis in der Datenbank, falls noch kein aktiver Eintrag existiert.
    """
    logger.info(f"Prüfe Strompreis-Konfiguration (aktuell: {ELECTRICITY_PRICE_EUR_PER_KWH} EUR/kWh)...")
    
    try:
        conn = mysql.connector.connect(**SQL_CONFIG)
        cursor = conn.cursor()
        
        # Prüfe, ob bereits ein aktiver Strompreis existiert
        cursor.execute("""
            SELECT COUNT(*) FROM electricity_price_config 
            WHERE valid_to IS NULL OR valid_to > NOW()
        """)
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Kein aktiver Eintrag vorhanden - erstelle einen
            cursor.execute(
                """
                INSERT INTO electricity_price_config 
                (price_eur_per_kwh, valid_from, valid_to, description, time)
                VALUES (%s, NOW(), NULL, %s, NOW())
                """,
                (ELECTRICITY_PRICE_EUR_PER_KWH, "Statischer Strompreis (Standardkonfiguration)")
            )
            logger.info(f"Strompreis {ELECTRICITY_PRICE_EUR_PER_KWH} EUR/kWh in Datenbank gespeichert.")
        else:
            logger.info("Aktiver Strompreis-Eintrag bereits vorhanden.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Strompreises: {e}")
        notify_all(f"Fehler beim Speichern des Strompreises: {e}")


def get_current_electricity_price():
    """
    Liest den aktuell gültigen Strompreis aus der Datenbank.
    
    Returns:
        float: Strompreis in EUR/kWh oder Konstante als Fallback
    """
    try:
        conn = mysql.connector.connect(**SQL_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT price_eur_per_kwh 
            FROM electricity_price_config 
            WHERE valid_to IS NULL OR valid_to > NOW()
            ORDER BY valid_from DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            price = result[0]
            logger.debug(f"Strompreis aus Datenbank gelesen: {price} EUR/kWh")
            return price
        else:
            logger.debug(f"Kein Strompreis in DB - verwende Konstante: {ELECTRICITY_PRICE_EUR_PER_KWH} EUR/kWh")
            return ELECTRICITY_PRICE_EUR_PER_KWH
            
    except Exception as e:
        logger.warning(f"Fehler beim Lesen des Strompreises aus DB: {e} - verwende Konstante")
        return ELECTRICITY_PRICE_EUR_PER_KWH


def calculate_energy_cost(power_mw, duration_seconds):
    """
    Berechnet die Energiekosten basierend auf Leistung und Dauer.
    
    Args:
        power_mw (int): Leistung in Milliwatt (mW)
        duration_seconds (int): Dauer in Sekunden
    
    Returns:
        float: Kosten in EUR
    """
    if power_mw is None or duration_seconds is None:
        return 0.0
    
    # Umrechnung: mW -> kW und Sekunden -> Stunden
    power_kw = power_mw / 1_000_000
    duration_hours = duration_seconds / 3600
    
    energy_kwh = power_kw * duration_hours
    price = get_current_electricity_price()
    cost_eur = energy_kwh * price
    
    return cost_eur


def calculate_power_cost_per_interval(power_mw, interval_seconds=300):
    """
    Berechnet die Kosten für ein Standard-Messintervall (z.B. 5 Minuten).
    
    Args:
        power_mw (int): Leistung in Milliwatt (mW)
        interval_seconds (int): Intervall in Sekunden (Standard: 300 = 5 Minuten)
    
    Returns:
        float: Kosten in EUR für das Intervall
    """
    return calculate_energy_cost(power_mw, interval_seconds)
