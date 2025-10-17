"""
WeatherAPI Collector Module

Sammelt Wetterdaten von OpenWeatherMap API und schreibt sie in die Datenbank.
"""
import os
import logging
import requests
import mysql.connector
from notify import notify_all

logger = logging.getLogger(__name__)

# Konstanten für Wetter-API
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
WEATHER_LOCATION = os.getenv("WEATHER_LOCATION", "Berlin,DE")
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"

# SQL-Konfiguration (wird von fritzbox_collector.py übernommen)
SQL_CONFIG = {
    "user": os.getenv("SQL_USER", "sqluser"),
    "password": os.getenv("SQL_PASSWORD", "sqlpass"),
    "host": os.getenv("SQL_HOST", "sqlhost"),
    "database": os.getenv("SQL_DB", "sqldb"),
    "autocommit": True
}


def create_weather_table():
    """Erstellt die Tabelle für Wetterdaten, falls sie nicht existiert."""
    logger.info("Prüfe und erstelle ggf. weather_data Tabelle...")
    table_sql = """CREATE TABLE IF NOT EXISTS weather_data (
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
    )"""
    
    try:
        conn = mysql.connector.connect(**SQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(table_sql)
        cursor.close()
        conn.close()
        logger.info("weather_data Tabelle wurde geprüft/erstellt.")
    except Exception as e:
        logger.error("Fehler bei weather_data Tabellenprüfung/-erstellung: %s", e)
        notify_all(f"Weather-Tabelle konnte nicht angelegt werden: {e}")
        raise


def fetch_weather_data():
    """
    Ruft Wetterdaten von der OpenWeatherMap API ab.
    
    Returns:
        dict: Wetterdaten oder None bei Fehler
    """
    if not WEATHER_API_KEY:
        logger.warning("WEATHER_API_KEY ist nicht gesetzt - überspringe Wetterabfrage")
        return None
    
    logger.info("Frage Wetterdaten ab für: %s", WEATHER_LOCATION)
    
    try:
        params = {
            "q": WEATHER_LOCATION,
            "appid": WEATHER_API_KEY,
            "units": "metric",  # Celsius statt Kelvin
            "lang": "de"
        }
        
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        weather_data = {
            "location": WEATHER_LOCATION,
            "temperature_celsius": data["main"]["temp"],
            "feels_like_celsius": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "weather_condition": data["weather"][0]["main"] if data.get("weather") else None,
            "weather_description": data["weather"][0]["description"] if data.get("weather") else None,
            "wind_speed": data["wind"]["speed"],
            "clouds": data["clouds"]["all"]
        }
        
        logger.info(
            "Wetterdaten abgerufen: Temp=%s°C, Luftfeuchtigkeit=%s%%, Wetter=%s",
            weather_data['temperature_celsius'],
            weather_data['humidity'],
            weather_data['weather_description']
        )
        
        return weather_data
        
    except requests.exceptions.RequestException as e:
        logger.error("Fehler beim Abrufen der Wetterdaten: %s", e)
        notify_all(f"Fehler beim Abrufen der Wetterdaten: {e}")
        return None
    except KeyError as e:
        logger.error("Fehler beim Parsen der Wetterdaten: %s", e)
        notify_all(f"Fehler beim Parsen der Wetterdaten: {e}")
        return None


def write_weather_to_sql(weather_data):
    """
    Schreibt Wetterdaten in die Datenbank.
    
    Args:
        weather_data (dict): Wetterdaten zum Speichern
    """
    if not weather_data:
        logger.warning("Keine Wetterdaten zum Speichern vorhanden")
        return
    
    logger.info("Schreibe Wetterdaten in die Datenbank...")
    
    for attempt in range(3):
        try:
            conn = mysql.connector.connect(**SQL_CONFIG)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO weather_data (
                    location, temperature_celsius, feels_like_celsius, humidity,
                    pressure, weather_condition, weather_description, wind_speed, clouds, time
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    weather_data["location"],
                    weather_data["temperature_celsius"],
                    weather_data["feels_like_celsius"],
                    weather_data["humidity"],
                    weather_data["pressure"],
                    weather_data["weather_condition"],
                    weather_data["weather_description"],
                    weather_data["wind_speed"],
                    weather_data["clouds"]
                )
            )
            cursor.close()
            conn.close()
            logger.info("Wetterdaten erfolgreich gespeichert.")
            return
        except Exception as e:
            logger.error("Fehler beim Schreiben der Wetterdaten in DB (Versuch %s): %s", attempt+1, e)
            notify_all(f"Fehler beim Schreiben der Wetterdaten: {e}")
            import time
            time.sleep(10)
    
    logger.error("Wetterdaten konnten nach 3 Versuchen nicht geschrieben werden.")


def collect_weather():
    """Hauptfunktion zum Sammeln und Speichern von Wetterdaten."""
    weather_data = fetch_weather_data()
    if weather_data:
        write_weather_to_sql(weather_data)
