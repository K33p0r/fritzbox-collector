# Tibber Integration - Setup and Troubleshooting Guide

## Overview
The Tibber integration allows you to collect energy consumption data from your Tibber Pulse IR device every 5 minutes and store it in your MariaDB/MySQL database for visualization in Grafana.

## Setup

### 1. Get Your Tibber API Token

1. Go to https://developer.tibber.com/
2. Log in with your Tibber account
3. Navigate to "Settings" → "API Access Tokens"
4. Click "Create Token"
5. Give it a descriptive name (e.g., "FritzBox Collector")
6. Copy the generated token (you won't be able to see it again!)

### 2. Configure Environment Variables

Add the following environment variable to your Docker container:

```bash
-e TIBBER_API_TOKEN=your_token_here
```

Optional configuration:
```bash
-e TIBBER_INTERVAL=300  # Collection interval in seconds (default: 300 = 5 minutes)
```

### 3. Verify Installation

Check the Docker logs to confirm Tibber integration is working:

```bash
docker logs fritzbox-collector
```

You should see messages like:
- "Tibber-Datensammlung geplant alle 300 Sekunden."
- "Querying Tibber API for live consumption data..."
- "Tibber data: consumption=X.X kWh, cost=X.X, current_price=X.X"
- "Tibber-Daten erfolgreich gespeichert."

## Database Schema

The Tibber data is stored in the `tibber_consumption` table with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Auto-incrementing primary key |
| consumption_kwh | FLOAT | Energy consumption in kWh |
| cost | FLOAT | Cost for the consumption period |
| unit_price | FLOAT | Price per unit (kWh) |
| from_time | DATETIME | Start of measurement period |
| to_time | DATETIME | End of measurement period |
| current_price_total | FLOAT | Current total electricity price |
| current_price_energy | FLOAT | Current energy component of price |
| current_price_tax | FLOAT | Current tax component of price |
| price_starts_at | DATETIME | When current price started |
| real_time_enabled | BOOLEAN | Whether real-time monitoring is enabled |
| time | DATETIME | Timestamp when data was collected |

## Grafana Integration

### Sample Query for Energy Consumption Over Time

```sql
SELECT 
    time as time_sec,
    consumption_kwh as value,
    'Consumption' as metric
FROM tibber_consumption
WHERE $__timeFilter(time)
ORDER BY time
```

### Sample Query for Energy Costs

```sql
SELECT 
    time as time_sec,
    cost as value,
    'Cost' as metric
FROM tibber_consumption
WHERE $__timeFilter(time)
ORDER BY time
```

### Sample Query for Current Price

```sql
SELECT 
    time as time_sec,
    current_price_total as value,
    'Price' as metric
FROM tibber_consumption
WHERE $__timeFilter(time)
ORDER BY time
```

## Troubleshooting

### Issue: "TIBBER_API_TOKEN not set"

**Symptom:** Log shows "TIBBER_API_TOKEN not set, skipping Tibber data collection."

**Solution:** 
- Verify that the environment variable is set correctly in your Docker run command
- Restart the container after adding the variable
- Check for typos in the variable name

### Issue: "Tibber API returned errors"

**Symptom:** Log shows "Tibber API returned errors: [...]"

**Possible causes and solutions:**

1. **Invalid token:**
   - Verify your API token is correct
   - Generate a new token at https://developer.tibber.com/
   - Update the environment variable and restart the container

2. **Token expired:**
   - Tibber tokens don't expire, but if your account is closed, the token becomes invalid
   - Generate a new token

3. **API rate limiting:**
   - The default 5-minute interval should be well within Tibber's rate limits
   - If you're experiencing rate limiting, increase `TIBBER_INTERVAL`

### Issue: Connection Timeouts

**Symptom:** Log shows "Tibber API timeout"

**Solution:**
- Check your internet connection
- Verify DNS resolution is working
- Check if firewall is blocking outbound HTTPS connections
- The collector will automatically retry 3 times with exponential backoff

### Issue: Database Connection Errors

**Symptom:** Log shows "Fehler beim Schreiben Tibber-Daten in DB"

**Solution:**
- Verify database credentials are correct
- Check that the database server is running and accessible
- Ensure the `tibber_consumption` table exists (it should be created automatically)
- Check database user permissions

### Issue: No Data in Database

**Symptom:** Table is empty or no recent data

**Checklist:**
1. Check Docker logs for errors
2. Verify `TIBBER_API_TOKEN` is set
3. Confirm you have an active Tibber subscription with consumption data
4. Check that the Tibber API is returning data (enable DEBUG logging)
5. Verify database connection is working

### Issue: Missing Pulse Data

**Symptom:** `real_time_enabled` is False

**Explanation:** 
- The Tibber Pulse IR device provides real-time data
- If you don't have a Pulse device, you'll only get hourly consumption data
- The integration works with or without Pulse, but Pulse provides more detailed data

## Performance Considerations

### Data Collection Interval

- **Default:** 300 seconds (5 minutes)
- **Minimum recommended:** 60 seconds (1 minute)
- **Maximum:** Any value in seconds

**Note:** Tibber's consumption data is typically updated hourly, so collecting more frequently than every 5 minutes won't provide significantly more data points, but will show price changes more frequently.

### Database Storage

Each data point is approximately 200 bytes. At 5-minute intervals:
- Per hour: 12 records (~2.4 KB)
- Per day: 288 records (~58 KB)
- Per month: ~8,640 records (~1.7 MB)
- Per year: ~105,120 records (~20 MB)

Storage requirements are minimal.

## API Rate Limits

Tibber's API has rate limits, but they are generous:
- The collector uses exponential backoff on failures
- Default 5-minute interval is well within limits
- Each request fetches multiple data points efficiently

## Error Handling

The integration includes robust error handling:

1. **Retry Logic:** 3 attempts with exponential backoff (1s, 2s, 4s)
2. **Timeout Protection:** 30-second timeout on API requests
3. **Database Retries:** 3 attempts with 10-second delays
4. **Graceful Degradation:** Other collectors continue if Tibber fails
5. **Notifications:** Errors are sent via Discord/Telegram if configured

## Support

For issues specific to:
- **Tibber API:** Contact Tibber support or check https://developer.tibber.com/
- **This Integration:** Open an issue on the GitHub repository
- **Database Issues:** Check MariaDB/MySQL documentation
- **Docker Issues:** Verify Docker configuration and logs

## Additional Resources

- Tibber API Documentation: https://developer.tibber.com/docs/overview
- Tibber GraphQL Explorer: https://developer.tibber.com/explorer
- FritzBox Collector Repository: https://github.com/K33p0r/fritzbox-collector
