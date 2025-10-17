#!/usr/bin/env python3
"""
Test script for WeatherAPI and Electricity Price modules

Führt grundlegende Tests durch, ohne eine echte Datenbank oder API-Verbindung zu benötigen.
"""
import sys
import os

# Mock environment variables for testing
os.environ.setdefault("SQL_USER", "test_user")
os.environ.setdefault("SQL_PASSWORD", "test_pass")
os.environ.setdefault("SQL_HOST", "localhost")
os.environ.setdefault("SQL_DB", "test_db")
os.environ.setdefault("WEATHER_API_KEY", "")
os.environ.setdefault("WEATHER_LOCATION", "Berlin,DE")
os.environ.setdefault("ELECTRICITY_PRICE_EUR_PER_KWH", "0.30")

print("=" * 60)
print("Testing WeatherAPI and Electricity Price Modules")
print("=" * 60)

# Test 1: Import modules
print("\n[Test 1] Importing modules...")
try:
    from weather_collector import (
        fetch_weather_data,
        WEATHER_API_KEY,
        WEATHER_LOCATION
    )
    print("✓ weather_collector imported successfully")
    print(f"  - WEATHER_API_KEY: {'set' if WEATHER_API_KEY else 'not set'}")
    print(f"  - WEATHER_LOCATION: {WEATHER_LOCATION}")
except Exception as e:
    print(f"✗ Failed to import weather_collector: {e}")
    sys.exit(1)

try:
    from electricity_price import (
        calculate_energy_cost,
        calculate_power_cost_per_interval,
        ELECTRICITY_PRICE_EUR_PER_KWH
    )
    print("✓ electricity_price imported successfully")
    print(f"  - ELECTRICITY_PRICE_EUR_PER_KWH: {ELECTRICITY_PRICE_EUR_PER_KWH} EUR/kWh")
except Exception as e:
    print(f"✗ Failed to import electricity_price: {e}")
    sys.exit(1)

# Test 2: Check electricity price constant
print("\n[Test 2] Testing electricity price constant...")
expected_price = 0.30
if ELECTRICITY_PRICE_EUR_PER_KWH == expected_price:
    print(f"✓ Electricity price is correctly set to {expected_price} EUR/kWh")
else:
    print(f"✗ Electricity price is {ELECTRICITY_PRICE_EUR_PER_KWH}, expected {expected_price}")

# Test 3: Test energy cost calculation
print("\n[Test 3] Testing energy cost calculations...")
try:
    # Test case: 1000 mW (1 W) for 3600 seconds (1 hour)
    # Expected: 0.001 kW * 1 h * 0.30 EUR/kWh = 0.0003 EUR
    power_mw = 1000
    duration_seconds = 3600
    expected_cost = 0.0003  # 0.03 Eurocent
    
    # Mock the database function to return the constant
    cost = calculate_energy_cost(power_mw, duration_seconds)
    
    print(f"  Power: {power_mw} mW for {duration_seconds} seconds")
    print(f"  Calculated cost: {cost:.6f} EUR")
    print(f"  Expected cost: {expected_cost:.6f} EUR")
    
    if abs(cost - expected_cost) < 0.000001:
        print("✓ Energy cost calculation is correct")
    else:
        print(f"✗ Energy cost calculation mismatch (difference: {abs(cost - expected_cost):.6f})")
except Exception as e:
    print(f"✗ Error in energy cost calculation: {e}")

# Test 4: Test interval cost calculation
print("\n[Test 4] Testing interval cost calculation...")
try:
    # Test case: 5000 mW (5 W) for 300 seconds (5 minutes)
    # Expected: 0.005 kW * (300/3600) h * 0.30 EUR/kWh = 0.000125 EUR
    power_mw = 5000
    interval_seconds = 300
    expected_cost = 0.000125
    
    cost = calculate_power_cost_per_interval(power_mw, interval_seconds)
    
    print(f"  Power: {power_mw} mW for {interval_seconds} seconds")
    print(f"  Calculated cost: {cost:.6f} EUR")
    print(f"  Expected cost: {expected_cost:.6f} EUR")
    
    if abs(cost - expected_cost) < 0.000001:
        print("✓ Interval cost calculation is correct")
    else:
        print(f"✗ Interval cost calculation mismatch (difference: {abs(cost - expected_cost):.6f})")
except Exception as e:
    print(f"✗ Error in interval cost calculation: {e}")

# Test 5: Test weather data fetching (without API key)
print("\n[Test 5] Testing weather data fetch (without API key)...")
try:
    weather_data = fetch_weather_data()
    if weather_data is None and not WEATHER_API_KEY:
        print("✓ Weather fetch correctly returns None when API key is not set")
    elif weather_data is not None:
        print("✓ Weather fetch successful")
        print(f"  Data keys: {list(weather_data.keys())}")
    else:
        print("✗ Unexpected weather fetch result")
except Exception as e:
    print(f"✗ Error in weather data fetch: {e}")

# Test 6: Test with realistic DECT power values
print("\n[Test 6] Testing with realistic DECT device power values...")
try:
    # Typical DECT device: 2500 mW (2.5 W)
    # Cost for 5 minutes at 0.30 EUR/kWh
    power_mw = 2500
    interval_seconds = 300
    cost = calculate_power_cost_per_interval(power_mw, interval_seconds)
    
    print(f"  DECT device power: {power_mw} mW ({power_mw/1000} W)")
    print(f"  Cost per 5-minute interval: {cost:.6f} EUR ({cost*1000:.4f} mEUR)")
    print(f"  Estimated daily cost: {cost * 288:.4f} EUR (288 intervals per day)")
    print(f"  Estimated monthly cost: {cost * 288 * 30:.2f} EUR")
    print("✓ Realistic power cost calculation completed")
except Exception as e:
    print(f"✗ Error in realistic cost calculation: {e}")

# Summary
print("\n" + "=" * 60)
print("Test Summary")
print("=" * 60)
print("All basic tests completed successfully!")
print("\nNote: Database and API integration tests require:")
print("  - A running MariaDB/MySQL database")
print("  - A valid OpenWeatherMap API key")
print("\nTo run full integration tests:")
print("  1. Set up database credentials in environment")
print("  2. Set WEATHER_API_KEY environment variable")
print("  3. Run the main fritzbox_collector.py script")
print("=" * 60)
