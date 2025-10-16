"""
Simple test to verify Tibber collector module functionality.
This is a basic validation script, not a full test suite.
"""
import os
import sys
from unittest.mock import patch, MagicMock

# Set dummy environment variables for testing
os.environ['TIBBER_API_TOKEN'] = 'test_token_12345'
os.environ['SQL_HOST'] = 'localhost'
os.environ['SQL_USER'] = 'test'
os.environ['SQL_PASSWORD'] = 'test'
os.environ['SQL_DB'] = 'test'

# Import the module
import tibber_collector

def test_tibber_collector_no_token():
    """Test that collector handles missing API token gracefully."""
    print("Testing Tibber collector without API token...")
    original_token = os.environ.get('TIBBER_API_TOKEN')
    os.environ['TIBBER_API_TOKEN'] = ''
    
    result = tibber_collector.get_tibber_consumption_data()
    
    if result is None:
        print("✓ Correctly returns None when no API token is set")
    else:
        print("✗ Should return None when no API token is set")
        sys.exit(1)
    
    # Restore token
    if original_token:
        os.environ['TIBBER_API_TOKEN'] = original_token

def test_tibber_api_error_response():
    """Test that collector handles API errors gracefully."""
    print("Testing Tibber collector with API error response...")
    
    # Mock the requests.post to return an error response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "errors": [{"message": "Invalid token"}]
    }
    mock_response.raise_for_status.return_value = None
    
    with patch('tibber_collector.requests.post', return_value=mock_response):
        result = tibber_collector.get_tibber_consumption_data()
        
        if result is None:
            print("✓ Correctly handles API error response")
        else:
            print("✗ Should return None on API error")
            sys.exit(1)

def test_tibber_api_success_response():
    """Test that collector correctly parses successful API response."""
    print("Testing Tibber collector with successful API response...")
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "viewer": {
                "homes": [{
                    "features": {
                        "realTimeConsumptionEnabled": True
                    },
                    "consumption": {
                        "nodes": [{
                            "from": "2025-10-16T10:00:00Z",
                            "to": "2025-10-16T11:00:00Z",
                            "cost": 1.25,
                            "unitPrice": 0.25,
                            "unitPriceVAT": 0.05,
                            "consumption": 5.0,
                            "consumptionUnit": "kWh"
                        }]
                    },
                    "currentSubscription": {
                        "priceInfo": {
                            "current": {
                                "total": 0.30,
                                "energy": 0.25,
                                "tax": 0.05,
                                "startsAt": "2025-10-16T10:00:00Z"
                            }
                        }
                    }
                }]
            }
        }
    }
    mock_response.raise_for_status.return_value = None
    
    with patch('tibber_collector.requests.post', return_value=mock_response):
        result = tibber_collector.get_tibber_consumption_data()
        
        if result is None:
            print("✗ Should return data on successful API call")
            sys.exit(1)
        
        # Verify data structure
        assert result['real_time_enabled'] == True, "real_time_enabled should be True"
        assert result['consumption_kwh'] == 5.0, "consumption_kwh should be 5.0"
        assert result['cost'] == 1.25, "cost should be 1.25"
        assert result['unit_price'] == 0.25, "unit_price should be 0.25"
        assert result['current_price_total'] == 0.30, "current_price_total should be 0.30"
        
        print("✓ Correctly parses successful API response")
        print(f"  - Consumption: {result['consumption_kwh']} kWh")
        print(f"  - Cost: {result['cost']}")
        print(f"  - Current price: {result['current_price_total']}")

def test_tibber_api_timeout():
    """Test that collector handles timeouts with retry logic."""
    print("Testing Tibber collector timeout handling...")
    
    import requests
    with patch('tibber_collector.requests.post', side_effect=requests.exceptions.Timeout("Connection timeout")):
        with patch('tibber_collector.time.sleep'):  # Skip actual sleep
            result = tibber_collector.get_tibber_consumption_data()
            
            if result is None:
                print("✓ Correctly handles timeout errors")
            else:
                print("✗ Should return None on timeout")
                sys.exit(1)

def test_tibber_api_empty_homes():
    """Test that collector handles empty homes response."""
    print("Testing Tibber collector with empty homes...")
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "viewer": {
                "homes": []
            }
        }
    }
    mock_response.raise_for_status.return_value = None
    
    with patch('tibber_collector.requests.post', return_value=mock_response):
        result = tibber_collector.get_tibber_consumption_data()
        
        if result is None:
            print("✓ Correctly handles empty homes response")
        else:
            print("✗ Should return None when no homes found")
            sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("Running Tibber Collector Tests")
    print("=" * 60)
    
    try:
        test_tibber_collector_no_token()
        test_tibber_api_error_response()
        test_tibber_api_success_response()
        test_tibber_api_timeout()
        test_tibber_api_empty_homes()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
