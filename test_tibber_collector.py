import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import sys
import asyncio
from datetime import datetime

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tibber_collector


class TestTibberCollector(unittest.TestCase):
    """Unit tests for Tibber Collector module."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Set up test environment variables
        os.environ["TIBBER_TOKEN"] = "test_token_12345"
        os.environ["SQL_HOST"] = "localhost"
        os.environ["SQL_USER"] = "testuser"
        os.environ["SQL_PASSWORD"] = "testpass"
        os.environ["SQL_DB"] = "testdb"
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove test environment variables
        if "TIBBER_TOKEN" in os.environ:
            del os.environ["TIBBER_TOKEN"]
    
    def test_exponential_backoff_success(self):
        """Test exponential backoff with successful function."""
        mock_func = MagicMock(return_value="success")
        result = tibber_collector.exponential_backoff_retry(mock_func, max_retries=3)
        
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 1)
    
    def test_exponential_backoff_retry(self):
        """Test exponential backoff with retries."""
        mock_func = MagicMock(side_effect=[Exception("Error 1"), Exception("Error 2"), "success"])
        result = tibber_collector.exponential_backoff_retry(mock_func, max_retries=5, initial_delay=0.01)
        
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 3)
    
    def test_exponential_backoff_max_retries(self):
        """Test exponential backoff reaches max retries."""
        mock_func = MagicMock(side_effect=Exception("Persistent error"))
        
        with self.assertRaises(Exception):
            tibber_collector.exponential_backoff_retry(mock_func, max_retries=3, initial_delay=0.01)
        
        self.assertEqual(mock_func.call_count, 3)
    
    @patch('tibber_collector.mysql.connector.connect')
    def test_create_tibber_table_success(self, mock_connect):
        """Test successful table creation."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        tibber_collector.create_tibber_table()
        
        # Verify connection was made
        mock_connect.assert_called_once()
        
        # Verify cursor operations
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('tibber_collector.mysql.connector.connect')
    def test_create_tibber_table_error(self, mock_connect):
        """Test table creation with database error."""
        mock_connect.side_effect = Exception("Database connection failed")
        
        # Should not raise exception, just log error
        tibber_collector.create_tibber_table()
    
    def test_get_tibber_client_with_token(self):
        """Test getting Tibber client with valid token."""
        with patch('tibber_collector.get_tibber_token', return_value="test_token_12345"):
            client = tibber_collector.get_tibber_client()
            self.assertIsNotNone(client)
    
    def test_get_tibber_client_without_token(self):
        """Test getting Tibber client without token."""
        with patch('tibber_collector.get_tibber_token', return_value=""):
            client = tibber_collector.get_tibber_client()
            self.assertIsNone(client)
    
    @patch('tibber_collector.mysql.connector.connect')
    def test_write_tibber_data_to_sql(self, mock_connect):
        """Test writing measurement data to SQL."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        measurement = {
            "timestamp": "2025-10-16T12:00:00Z",
            "power": 1500,
            "consumption": 0.5,
            "accumulatedConsumption": 150.5,
            "accumulatedCost": 45.25,
            "currency": "EUR",
            "powerProduction": 0,
            "minPower": 1000,
            "averagePower": 1250,
            "maxPower": 1500,
            "voltage1": 230.5,
            "voltage2": 231.0,
            "voltage3": 229.5,
            "current1": 6.5,
            "current2": 6.3,
            "current3": 6.6,
            "powerFactor": 0.98,
            "signalStrength": 85
        }
        
        tibber_collector.write_tibber_data_to_sql(measurement)
        
        # Verify database interaction
        mock_connect.assert_called_once()
        mock_cursor.execute.assert_called_once()
        
        # Verify the SQL contains the expected fields
        sql_call = mock_cursor.execute.call_args[0][0]
        self.assertIn("INSERT INTO tibber_energy_data", sql_call)
        self.assertIn("timestamp", sql_call)
        self.assertIn("power", sql_call)
        self.assertIn("consumption", sql_call)
    
    @patch('tibber_collector.mysql.connector.connect')
    def test_write_historical_data_to_sql(self, mock_connect):
        """Test writing historical consumption data to SQL."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock fetchone to return None (no existing records)
        mock_cursor.fetchone.return_value = None
        
        consumption_data = [
            {
                "from": "2025-10-16T10:00:00Z",
                "to": "2025-10-16T11:00:00Z",
                "consumption": 1.5,
                "cost": 0.45,
                "consumptionUnit": "kWh"
            },
            {
                "from": "2025-10-16T11:00:00Z",
                "to": "2025-10-16T12:00:00Z",
                "consumption": 1.3,
                "cost": 0.39,
                "consumptionUnit": "kWh"
            }
        ]
        
        tibber_collector.write_historical_data_to_sql(consumption_data)
        
        # Verify database interaction
        mock_connect.assert_called_once()
        
        # Should have 2 execute calls for SELECT and 2 for INSERT
        self.assertEqual(mock_cursor.execute.call_count, 4)
    
    @patch('tibber_collector.mysql.connector.connect')
    def test_write_historical_data_skips_duplicates(self, mock_connect):
        """Test that duplicate records are skipped."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock fetchone to return existing record
        mock_cursor.fetchone.return_value = (1,)
        
        consumption_data = [
            {
                "from": "2025-10-16T10:00:00Z",
                "to": "2025-10-16T11:00:00Z",
                "consumption": 1.5,
                "cost": 0.45,
                "consumptionUnit": "kWh"
            }
        ]
        
        tibber_collector.write_historical_data_to_sql(consumption_data)
        
        # Should only have SELECT call, no INSERT for duplicate
        self.assertEqual(mock_cursor.execute.call_count, 1)
    
    def test_sync_run_historical_collection(self):
        """Test synchronous wrapper for historical collection."""
        with patch('tibber_collector.run_tibber_collector_once', new_callable=AsyncMock) as mock_run:
            tibber_collector.sync_run_historical_collection()
            
            # Verify async function was called
            mock_run.assert_called_once()


class TestAsyncTibberFunctions(unittest.TestCase):
    """Test async functions in Tibber collector."""
    
    def setUp(self):
        """Set up test fixtures."""
        os.environ["TIBBER_TOKEN"] = "test_token_12345"
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()
        if "TIBBER_TOKEN" in os.environ:
            del os.environ["TIBBER_TOKEN"]
    
    @patch('tibber_collector.Client')
    def test_fetch_historical_consumption(self, mock_client_class):
        """Test fetching historical consumption data."""
        with patch('tibber_collector.get_tibber_token', return_value="test_token_12345"):
            mock_session = MagicMock()
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client
            
            mock_result = {
                "viewer": {
                    "homes": [
                        {
                            "consumption": {
                                "nodes": [
                                    {
                                        "from": "2025-10-16T10:00:00Z",
                                        "to": "2025-10-16T11:00:00Z",
                                        "consumption": 1.5,
                                        "cost": 0.45
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            result = self.loop.run_until_complete(
                tibber_collector.fetch_historical_consumption(hours=24)
            )
            
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["consumption"], 1.5)
    
    @patch('tibber_collector.Client')
    def test_fetch_historical_consumption_no_token(self, mock_client_class):
        """Test fetching data without token."""
        with patch('tibber_collector.get_tibber_token', return_value=""):
            result = self.loop.run_until_complete(
                tibber_collector.fetch_historical_consumption(hours=24)
            )
            
            self.assertEqual(result, [])
            mock_client_class.assert_not_called()
    
    @patch('tibber_collector.Client')
    def test_fetch_historical_consumption_error(self, mock_client_class):
        """Test handling of errors during data fetch."""
        mock_client_class.side_effect = Exception("API Error")
        
        result = self.loop.run_until_complete(
            tibber_collector.fetch_historical_consumption(hours=24)
        )
        
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
