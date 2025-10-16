# Tibber Pulse IR Integration - Setup Guide

This guide will help you set up the Tibber Pulse IR integration for the FritzBox Collector.

## Prerequisites

1. **Tibber Account**: You need an active Tibber account
2. **Tibber Pulse IR**: You need to have a Tibber Pulse IR device installed and connected
3. **Personal Access Token**: You need to generate a Personal Access Token from Tibber

## Step 1: Generate Tibber Personal Access Token

1. Go to [Tibber Developer Settings](https://developer.tibber.com/settings/access-token)
2. Log in with your Tibber account
3. Create a new Personal Access Token
4. **Important**: Save the token securely - you won't be able to see it again!

## Step 2: Configure the Docker Container

Add the following environment variables to your Docker run command or docker-compose.yml:

```bash
-e TIBBER_TOKEN=your_personal_access_token_here
-e TIBBER_INTERVAL=3600  # Optional: collect data every hour (default)
```

### Full Docker Run Example

```bash
docker run -d --restart=unless-stopped \
  -e FRITZBOX_HOST=192.168.178.1 \
  -e FRITZBOX_USER=your_user \
  -e FRITZBOX_PASSWORD=your_password \
  -e SQL_HOST=192.168.178.xx \
  -e SQL_USER=sqluser \
  -e SQL_PASSWORD=sqlpass \
  -e SQL_DB=fritzbox \
  -e TIBBER_TOKEN=your_tibber_token_here \
  -e TIBBER_INTERVAL=3600 \
  -v /mnt/user/appdata/fritzbox_collector/:/config \
  fritzbox-collector
```

### Docker Compose Example

```yaml
version: '3'
services:
  fritzbox-collector:
    build: .
    restart: unless-stopped
    environment:
      - FRITZBOX_HOST=192.168.178.1
      - FRITZBOX_USER=your_user
      - FRITZBOX_PASSWORD=your_password
      - SQL_HOST=mariadb
      - SQL_USER=collector
      - SQL_PASSWORD=secure_password
      - SQL_DB=fritzbox
      - TIBBER_TOKEN=your_tibber_token_here
      - TIBBER_INTERVAL=3600
      - COLLECT_INTERVAL=300
      - SPEEDTEST_INTERVAL=3600
    volumes:
      - ./config:/config
    depends_on:
      - mariadb
```

## Step 3: Verify Integration

1. **Check Logs**: Monitor the container logs to ensure Tibber data is being collected:
   ```bash
   docker logs -f fritzbox-collector
   ```

2. **Look for these log messages**:
   - `Tibber integration enabled`
   - `Running Tibber historical data collection...`
   - `Fetched X historical consumption records`

3. **Check Database**: Verify the `tibber_energy_data` table exists and contains data:
   ```sql
   SELECT * FROM tibber_energy_data ORDER BY timestamp DESC LIMIT 10;
   ```

## Step 4: Import Grafana Dashboard

1. Open Grafana in your browser
2. Navigate to **Dashboards** → **Import**
3. Click **Upload JSON file**
4. Select the `grafana-dashboard-tibber.json` file from this repository
5. Choose your MariaDB data source
6. Click **Import**

The dashboard will display:
- Real-time power consumption
- Current power gauge
- Accumulated energy consumption
- Hourly energy consumption (bar chart)
- Accumulated energy costs
- Voltage levels (L1, L2, L3)
- Current levels (L1, L2, L3)

## Step 5: Configure Data Collection Interval

The `TIBBER_INTERVAL` variable controls how often historical data is fetched:

- **3600** (default): Fetch data every hour (recommended for most users)
- **1800**: Fetch every 30 minutes (more frequent updates)
- **7200**: Fetch every 2 hours (less frequent, reduces API calls)

**Note**: The Tibber API has rate limits. We recommend keeping the interval at 1 hour or higher.

## Troubleshooting

### Issue: "Cannot fetch Tibber data: TIBBER_TOKEN not set"

**Solution**: Make sure you've set the `TIBBER_TOKEN` environment variable correctly.

### Issue: "Error fetching historical Tibber data: Unauthorized"

**Solution**: Your token might be invalid or expired. Generate a new token from the Tibber Developer Portal.

### Issue: No data in tibber_energy_data table

**Possible causes**:
1. Check that your Tibber Pulse IR is online and connected
2. Verify you have an active Tibber subscription
3. Check the container logs for error messages
4. Ensure the database connection is working

### Issue: WebSocket connection keeps failing

**Solution**: This is usually a network connectivity issue. Check:
1. Firewall settings
2. Network connectivity to `websocket-api.tibber.com`
3. Container's network configuration

## API Rate Limits

Tibber has rate limits on their API. The integration implements:

- **Exponential backoff** with jitter for retries
- **Automatic reconnection** for WebSocket subscriptions
- **Graceful error handling** with notifications

If you're hitting rate limits:
1. Increase `TIBBER_INTERVAL` to a higher value
2. Check logs for excessive retry attempts
3. Ensure only one instance of the collector is running

## Data Privacy

- All data is stored locally in your MariaDB database
- No data is sent to third parties (except Tibber API queries)
- Your Tibber token is only used for API authentication
- Consider encrypting your database backups

## Advanced Configuration

### Real-time WebSocket Data (Future Enhancement)

The collector includes support for real-time WebSocket data collection. This feature can be enabled in future versions to get live power measurements every few seconds instead of hourly aggregates.

### Historical Data Backfill

To backfill historical data, you can adjust the `hours` parameter in the code:

```python
# In tibber_collector.py, line ~377
historical_data = await fetch_historical_consumption(hours=168)  # Last 7 days
```

**Note**: Tibber API limits historical queries, so large backfills may not be possible.

## Support

For issues specific to the Tibber integration:
1. Check the [Tibber API Documentation](https://developer.tibber.com/docs/overview)
2. Review the container logs
3. Open an issue in this repository

For Tibber account or Pulse IR device issues:
- Contact [Tibber Support](https://tibber.com/support)
