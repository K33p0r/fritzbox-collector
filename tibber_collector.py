import time
import os
import logging
import json
import asyncio
from datetime import datetime, timedelta
import mysql.connector
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.websockets import WebsocketsTransport
from notify import notify_all

logger = logging.getLogger(__name__)

# Tibber API Configuration
TIBBER_API_URL = "https://api.tibber.com/v1-beta/gql"
TIBBER_WS_URL = "wss://websocket-api.tibber.com/v1-beta/gql"


def get_tibber_token():
    """Get Tibber token from environment."""
    return os.getenv("TIBBER_TOKEN", "")

SQL_CONFIG = {
    "user": os.getenv("SQL_USER", "sqluser"),
    "password": os.getenv("SQL_PASSWORD", "sqlpass"),
    "host": os.getenv("SQL_HOST", "sqlhost"),
    "database": os.getenv("SQL_DB", "sqldb"),
    "autocommit": True
}


def create_tibber_table():
    """Create the Tibber energy data table if it doesn't exist."""
    logger.info("Creating Tibber energy data table if not exists...")
    table_sql = """
        CREATE TABLE IF NOT EXISTS tibber_energy_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME,
            consumption FLOAT,
            accumulated_consumption FLOAT,
            accumulated_cost FLOAT,
            currency VARCHAR(8),
            power INT,
            power_production INT,
            min_power INT,
            average_power INT,
            max_power INT,
            voltage1 FLOAT,
            voltage2 FLOAT,
            voltage3 FLOAT,
            current1 FLOAT,
            current2 FLOAT,
            current3 FLOAT,
            power_factor FLOAT,
            signal_strength INT,
            INDEX idx_timestamp (timestamp)
        )
    """
    try:
        conn = mysql.connector.connect(**SQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(table_sql)
        cursor.close()
        conn.close()
        logger.info("Tibber energy data table created/verified.")
    except Exception as e:
        logger.error(f"Error creating Tibber table: {e}")
        notify_all(f"Tibber table creation failed: {e}")


def exponential_backoff_retry(func, max_retries=5, initial_delay=1, max_delay=60):
    """
    Retry a function with exponential backoff and jitter.
    Implements Tibber's recommended retry strategy.
    """
    import random
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed after {max_retries} attempts: {e}")
                raise
            
            # Calculate delay with exponential backoff and jitter
            delay = min(initial_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.1)  # Add up to 10% jitter
            total_delay = delay + jitter
            
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {total_delay:.2f}s...")
            time.sleep(total_delay)


def get_tibber_client():
    """Create and return a Tibber GraphQL client."""
    tibber_token = get_tibber_token()
    if not tibber_token:
        logger.error("TIBBER_TOKEN environment variable is not set")
        return None
    
    transport = AIOHTTPTransport(
        url=TIBBER_API_URL,
        headers={"Authorization": f"Bearer {tibber_token}"}
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)
    return client


async def fetch_historical_consumption(hours=24):
    """
    Fetch historical energy consumption data from Tibber.
    
    Args:
        hours: Number of hours of historical data to fetch (default: 24)
    
    Returns:
        List of consumption data points
    """
    tibber_token = get_tibber_token()
    if not tibber_token:
        logger.error("Cannot fetch Tibber data: TIBBER_TOKEN not set")
        return []
    
    query = gql("""
    {
      viewer {
        homes {
          consumption(resolution: HOURLY, last: %d) {
            nodes {
              from
              to
              cost
              unitPrice
              unitPriceVAT
              consumption
              consumptionUnit
            }
          }
          currentSubscription {
            priceInfo {
              current {
                total
                energy
                tax
                startsAt
              }
            }
          }
        }
      }
    }
    """ % hours)
    
    try:
        transport = AIOHTTPTransport(
            url=TIBBER_API_URL,
            headers={"Authorization": f"Bearer {tibber_token}"}
        )
        
        async with Client(
            transport=transport,
            fetch_schema_from_transport=False,
        ) as session:
            result = await session.execute(query)
            
            consumption_data = []
            for home in result.get("viewer", {}).get("homes", []):
                for node in home.get("consumption", {}).get("nodes", []):
                    consumption_data.append(node)
            
            logger.info(f"Fetched {len(consumption_data)} historical consumption records")
            return consumption_data
    
    except Exception as e:
        logger.error(f"Error fetching historical Tibber data: {e}")
        notify_all(f"Tibber historical data fetch failed: {e}")
        return []


async def subscribe_to_live_measurements(callback):
    """
    Subscribe to real-time energy measurements via WebSocket.
    
    Args:
        callback: Function to call with each new measurement
    """
    tibber_token = get_tibber_token()
    if not tibber_token:
        logger.error("Cannot subscribe to Tibber: TIBBER_TOKEN not set")
        return
    
    subscription = gql("""
    subscription {
      liveMeasurement(homeId: "") {
        timestamp
        power
        powerProduction
        accumulatedConsumption
        accumulatedCost
        currency
        minPower
        averagePower
        maxPower
        voltage1
        voltage2
        voltage3
        current1
        current2
        current3
        powerFactor
        signalStrength
      }
    }
    """)
    
    retry_delay = 1
    max_retry_delay = 300  # 5 minutes
    
    while True:
        try:
            transport = WebsocketsTransport(
                url=TIBBER_WS_URL,
                headers={"Authorization": f"Bearer {tibber_token}"}
            )
            
            async with Client(
                transport=transport,
                fetch_schema_from_transport=False,
            ) as session:
                logger.info("Connected to Tibber WebSocket")
                retry_delay = 1  # Reset retry delay on successful connection
                
                async for result in session.subscribe(subscription):
                    measurement = result.get("liveMeasurement", {})
                    if measurement:
                        await callback(measurement)
        
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            logger.info(f"Reconnecting in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
            
            # Exponential backoff with max limit
            retry_delay = min(retry_delay * 2, max_retry_delay)


def write_tibber_data_to_sql(measurement):
    """
    Write a Tibber measurement to the database.
    
    Args:
        measurement: Dictionary containing the measurement data
    """
    logger.info("Writing Tibber measurement to database...")
    
    try:
        conn = mysql.connector.connect(**SQL_CONFIG)
        cursor = conn.cursor()
        
        # Parse timestamp
        timestamp_str = measurement.get("timestamp")
        if timestamp_str:
            # Convert ISO format timestamp to MySQL datetime
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            timestamp = datetime.now()
        
        cursor.execute(
            """
            INSERT INTO tibber_energy_data (
                timestamp, consumption, accumulated_consumption, accumulated_cost,
                currency, power, power_production, min_power, average_power, max_power,
                voltage1, voltage2, voltage3, current1, current2, current3,
                power_factor, signal_strength
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                timestamp,
                measurement.get("consumption"),
                measurement.get("accumulatedConsumption"),
                measurement.get("accumulatedCost"),
                measurement.get("currency"),
                measurement.get("power"),
                measurement.get("powerProduction"),
                measurement.get("minPower"),
                measurement.get("averagePower"),
                measurement.get("maxPower"),
                measurement.get("voltage1"),
                measurement.get("voltage2"),
                measurement.get("voltage3"),
                measurement.get("current1"),
                measurement.get("current2"),
                measurement.get("current3"),
                measurement.get("powerFactor"),
                measurement.get("signalStrength"),
            )
        )
        
        cursor.close()
        conn.close()
        logger.info("Tibber measurement saved successfully")
        
    except Exception as e:
        logger.error(f"Error writing Tibber data to database: {e}")
        notify_all(f"Tibber data write failed: {e}")


def write_historical_data_to_sql(consumption_data):
    """
    Write historical consumption data to the database.
    
    Args:
        consumption_data: List of consumption records
    """
    if not consumption_data:
        logger.info("No historical data to write")
        return
    
    logger.info(f"Writing {len(consumption_data)} historical records to database...")
    
    try:
        conn = mysql.connector.connect(**SQL_CONFIG)
        cursor = conn.cursor()
        
        for record in consumption_data:
            # Parse timestamp from 'from' field
            timestamp_str = record.get("from")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                continue
            
            # Check if record already exists
            cursor.execute(
                "SELECT id FROM tibber_energy_data WHERE timestamp = %s",
                (timestamp,)
            )
            if cursor.fetchone():
                continue  # Skip duplicate
            
            consumption = record.get("consumption", 0)
            cost = record.get("cost", 0)
            
            cursor.execute(
                """
                INSERT INTO tibber_energy_data (
                    timestamp, consumption, accumulated_cost, currency
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    timestamp,
                    consumption,
                    cost,
                    record.get("consumptionUnit", "kWh"),
                )
            )
        
        cursor.close()
        conn.close()
        logger.info("Historical Tibber data saved successfully")
        
    except Exception as e:
        logger.error(f"Error writing historical Tibber data: {e}")
        notify_all(f"Historical Tibber data write failed: {e}")


async def run_tibber_collector_once():
    """Run one iteration of Tibber data collection (historical only)."""
    logger.info("Running Tibber historical data collection...")
    
    try:
        # Fetch last 24 hours of historical data
        historical_data = await fetch_historical_consumption(hours=24)
        if historical_data:
            write_historical_data_to_sql(historical_data)
    except Exception as e:
        logger.error(f"Error in Tibber collection: {e}")
        notify_all(f"Tibber collection error: {e}")


async def run_tibber_live_collector():
    """Run the live Tibber data collector with WebSocket subscription."""
    logger.info("Starting Tibber live data collector...")
    
    async def handle_measurement(measurement):
        """Callback to handle incoming measurements."""
        logger.info(f"Received live measurement: Power={measurement.get('power')}W")
        write_tibber_data_to_sql(measurement)
    
    await subscribe_to_live_measurements(handle_measurement)


def sync_run_historical_collection():
    """Synchronous wrapper for historical data collection."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_tibber_collector_once())
    finally:
        loop.close()
