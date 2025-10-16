import os
import time
import logging
import requests
from notify import notify_all

logger = logging.getLogger(__name__)

# Tibber API configuration
TIBBER_API_TOKEN = os.getenv("TIBBER_API_TOKEN", "")
TIBBER_API_URL = "https://api.tibber.com/v1-beta/gql"

def get_tibber_consumption_data():
    """
    Query Tibber GraphQL API to fetch live energy consumption data.
    Returns a dict with consumption, power, timestamp, cost, and other metadata.
    """
    if not TIBBER_API_TOKEN:
        logger.warning("TIBBER_API_TOKEN not set, skipping Tibber data collection.")
        return None
    
    logger.info("Querying Tibber API for live consumption data...")
    
    # GraphQL query to fetch live measurements
    query = """
    {
        viewer {
            homes {
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
                features {
                    realTimeConsumptionEnabled
                }
                consumption(resolution: HOURLY, last: 1) {
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
            }
        }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {TIBBER_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    for attempt in range(3):
        try:
            response = requests.post(
                TIBBER_API_URL,
                json={"query": query},
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error(f"Tibber API returned errors: {data['errors']}")
                notify_all(f"Tibber API Error: {data['errors']}")
                return None
            
            # Extract relevant data from response
            homes = data.get("data", {}).get("viewer", {}).get("homes", [])
            if not homes:
                logger.warning("No homes found in Tibber API response.")
                return None
            
            home = homes[0]  # Use first home
            result = {
                "real_time_enabled": home.get("features", {}).get("realTimeConsumptionEnabled", False),
                "consumption_kwh": None,
                "cost": None,
                "unit_price": None,
                "from_time": None,
                "to_time": None,
                "current_price_total": None,
                "current_price_energy": None,
                "current_price_tax": None,
                "price_starts_at": None
            }
            
            # Get consumption data
            consumption_nodes = home.get("consumption", {}).get("nodes", [])
            if consumption_nodes:
                latest = consumption_nodes[-1]
                result["consumption_kwh"] = latest.get("consumption")
                result["cost"] = latest.get("cost")
                result["unit_price"] = latest.get("unitPrice")
                result["from_time"] = latest.get("from")
                result["to_time"] = latest.get("to")
            
            # Get current price info
            current_price = home.get("currentSubscription", {}).get("priceInfo", {}).get("current", {})
            if current_price:
                result["current_price_total"] = current_price.get("total")
                result["current_price_energy"] = current_price.get("energy")
                result["current_price_tax"] = current_price.get("tax")
                result["price_starts_at"] = current_price.get("startsAt")
            
            logger.info(
                f"Tibber data: consumption={result['consumption_kwh']} kWh, "
                f"cost={result['cost']}, current_price={result['current_price_total']}"
            )
            
            return result
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Tibber API timeout (attempt {attempt+1}/3): {e}")
            if attempt < 2:
                sleep_time = 2 ** attempt  # Exponential backoff: 1s, 2s
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
        except requests.exceptions.RequestException as e:
            logger.error(f"Tibber API request error (attempt {attempt+1}/3): {e}")
            notify_all(f"Tibber API Error: {e}")
            if attempt < 2:
                sleep_time = 2 ** attempt
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
        except Exception as e:
            logger.error(f"Unexpected error querying Tibber API (attempt {attempt+1}/3): {e}")
            notify_all(f"Tibber API Unexpected Error: {e}")
            if attempt < 2:
                sleep_time = 2 ** attempt
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
    
    logger.error("Failed to get Tibber data after 3 attempts.")
    return None


def get_tibber_live_measurement():
    """
    Alternative query for live/real-time measurements if Pulse is available.
    This requires a WebSocket subscription, which is more complex.
    For now, we use the REST API above for periodic polling.
    """
    # This would require WebSocket implementation for true real-time data
    # For periodic 5-minute polling, the REST API above is sufficient
    pass
