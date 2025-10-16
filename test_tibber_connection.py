#!/usr/bin/env python3
"""
Tibber Configuration Test Script

This script helps you verify your Tibber API token and connection before
running the full collector.

Usage:
    python3 test_tibber_connection.py YOUR_TIBBER_TOKEN
"""

import sys
import asyncio
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport


async def test_tibber_connection(token):
    """Test connection to Tibber API."""
    print("🔍 Testing Tibber API connection...")
    print(f"Token: {token[:10]}...{token[-4:]}")
    print()
    
    # Test query - fetch basic viewer info
    query = gql("""
    {
      viewer {
        name
        homes {
          id
          address {
            address1
            city
          }
          currentSubscription {
            status
          }
        }
      }
    }
    """)
    
    try:
        transport = AIOHTTPTransport(
            url="https://api.tibber.com/v1-beta/gql",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        async with Client(
            transport=transport,
            fetch_schema_from_transport=False,
        ) as session:
            print("📡 Connecting to Tibber API...")
            result = await session.execute(query)
            
            viewer = result.get("viewer", {})
            if not viewer:
                print("❌ Failed: No viewer data returned")
                return False
            
            print("✅ Connection successful!")
            print()
            print(f"Account Name: {viewer.get('name', 'N/A')}")
            print()
            
            homes = viewer.get("homes", [])
            print(f"Found {len(homes)} home(s):")
            for i, home in enumerate(homes, 1):
                address = home.get("address", {})
                subscription = home.get("currentSubscription", {})
                print(f"  {i}. {address.get('address1', 'N/A')}, {address.get('city', 'N/A')}")
                print(f"     Subscription: {subscription.get('status', 'N/A')}")
                print(f"     Home ID: {home.get('id', 'N/A')}")
            
            print()
            print("✅ Your Tibber token is valid and working!")
            print()
            print("Next steps:")
            print("1. Set TIBBER_TOKEN environment variable in your Docker container")
            print("2. Restart the fritzbox-collector container")
            print("3. Check logs to verify data collection")
            print("4. Import the Grafana dashboard")
            
            return True
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Common issues:")
        print("- Invalid token (generate a new one at https://developer.tibber.com/settings/access-token)")
        print("- Network connectivity issues")
        print("- Firewall blocking connection to api.tibber.com")
        return False


async def test_historical_data(token):
    """Test fetching historical consumption data."""
    print()
    print("🔍 Testing historical data fetch...")
    
    query = gql("""
    {
      viewer {
        homes {
          consumption(resolution: HOURLY, last: 5) {
            nodes {
              from
              to
              consumption
              cost
            }
          }
        }
      }
    }
    """)
    
    try:
        transport = AIOHTTPTransport(
            url="https://api.tibber.com/v1-beta/gql",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        async with Client(
            transport=transport,
            fetch_schema_from_transport=False,
        ) as session:
            result = await session.execute(query)
            
            total_records = 0
            for home in result.get("viewer", {}).get("homes", []):
                nodes = home.get("consumption", {}).get("nodes", [])
                total_records += len(nodes)
                
                if nodes:
                    print(f"✅ Found {len(nodes)} historical records")
                    print()
                    print("Sample data (most recent):")
                    latest = nodes[-1] if nodes else None
                    if latest:
                        print(f"  From: {latest.get('from')}")
                        print(f"  Consumption: {latest.get('consumption')} kWh")
                        print(f"  Cost: {latest.get('cost')}")
            
            if total_records == 0:
                print("⚠️  No historical data found")
                print("This might be normal if:")
                print("- Your Pulse IR was recently installed")
                print("- You haven't had any consumption in the last few hours")
            
            return total_records > 0
            
    except Exception as e:
        print(f"❌ Historical data fetch failed: {e}")
        return False


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python3 test_tibber_connection.py YOUR_TIBBER_TOKEN")
        print()
        print("Get your token from: https://developer.tibber.com/settings/access-token")
        sys.exit(1)
    
    token = sys.argv[1].strip()
    
    if not token or len(token) < 20:
        print("❌ Invalid token format")
        print("Your token should be a long string (40+ characters)")
        sys.exit(1)
    
    print("=" * 70)
    print("Tibber Connection Test")
    print("=" * 70)
    print()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Test basic connection
        success = loop.run_until_complete(test_tibber_connection(token))
        
        if success:
            # Test historical data
            loop.run_until_complete(test_historical_data(token))
        
        print()
        print("=" * 70)
        
        if success:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed - please check the errors above")
            sys.exit(1)
            
    finally:
        loop.close()


if __name__ == "__main__":
    main()
