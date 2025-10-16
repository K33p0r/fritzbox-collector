# Grafana SQL Queries Reference

This document contains useful SQL queries for creating custom Grafana panels with Tibber energy data.

## Basic Queries

### Current Power Consumption

```sql
SELECT 
    timestamp as time,
    power as "Power (W)"
FROM tibber_energy_data
WHERE $__timeFilter(timestamp)
    AND power IS NOT NULL
ORDER BY timestamp
```

### Hourly Energy Consumption

```sql
SELECT 
    timestamp as time,
    consumption as "Consumption (kWh)"
FROM tibber_energy_data
WHERE $__timeFilter(timestamp)
    AND consumption IS NOT NULL
ORDER BY timestamp
```

### Accumulated Cost

```sql
SELECT 
    timestamp as time,
    accumulated_cost as "Cost"
FROM tibber_energy_data
WHERE $__timeFilter(timestamp)
    AND accumulated_cost IS NOT NULL
ORDER BY timestamp
```

## Advanced Queries

### Daily Energy Consumption Summary

```sql
SELECT 
    DATE(timestamp) as time,
    SUM(consumption) as "Total Consumption (kWh)",
    AVG(power) as "Avg Power (W)",
    MAX(power) as "Peak Power (W)"
FROM tibber_energy_data
WHERE $__timeFilter(timestamp)
GROUP BY DATE(timestamp)
ORDER BY time
```

### Energy Cost per Day

```sql
SELECT 
    DATE(timestamp) as time,
    MAX(accumulated_cost) - MIN(accumulated_cost) as "Daily Cost"
FROM tibber_energy_data
WHERE $__timeFilter(timestamp)
    AND accumulated_cost IS NOT NULL
GROUP BY DATE(timestamp)
ORDER BY time
```

### Three-Phase Voltage Monitoring

```sql
SELECT 
    timestamp as time,
    voltage1 as "L1 (V)",
    voltage2 as "L2 (V)",
    voltage3 as "L3 (V)"
FROM tibber_energy_data
WHERE $__timeFilter(timestamp)
    AND (voltage1 IS NOT NULL OR voltage2 IS NOT NULL OR voltage3 IS NOT NULL)
ORDER BY timestamp
```

### Three-Phase Current Monitoring

```sql
SELECT 
    timestamp as time,
    current1 as "L1 (A)",
    current2 as "L2 (A)",
    current3 as "L3 (A)"
FROM tibber_energy_data
WHERE $__timeFilter(timestamp)
    AND (current1 IS NOT NULL OR current2 IS NOT NULL OR current3 IS NOT NULL)
ORDER BY timestamp
```

### Power Factor Monitoring

```sql
SELECT 
    timestamp as time,
    power_factor as "Power Factor"
FROM tibber_energy_data
WHERE $__timeFilter(timestamp)
    AND power_factor IS NOT NULL
ORDER BY timestamp
```

## Stat Panels (Single Value)

### Latest Power Reading

```sql
SELECT power as "Current Power (W)"
FROM tibber_energy_data
WHERE power IS NOT NULL
ORDER BY timestamp DESC
LIMIT 1
```

### Total Energy Today

```sql
SELECT 
    MAX(accumulated_consumption) - MIN(accumulated_consumption) as "Today's Consumption (kWh)"
FROM tibber_energy_data
WHERE DATE(timestamp) = CURDATE()
    AND accumulated_consumption IS NOT NULL
```

### Total Cost Today

```sql
SELECT 
    MAX(accumulated_cost) - MIN(accumulated_cost) as "Today's Cost"
FROM tibber_energy_data
WHERE DATE(timestamp) = CURDATE()
    AND accumulated_cost IS NOT NULL
```

### Average Power Last Hour

```sql
SELECT AVG(power) as "Avg Power (W)"
FROM tibber_energy_data
WHERE timestamp >= NOW() - INTERVAL 1 HOUR
    AND power IS NOT NULL
```

## Table Panels

### Recent Measurements (Last 10)

```sql
SELECT 
    timestamp as "Time",
    power as "Power (W)",
    consumption as "Consumption (kWh)",
    accumulated_cost as "Cost",
    voltage1 as "V1",
    current1 as "I1"
FROM tibber_energy_data
WHERE power IS NOT NULL
ORDER BY timestamp DESC
LIMIT 10
```

### Hourly Summary for Today

```sql
SELECT 
    DATE_FORMAT(timestamp, '%H:00') as "Hour",
    AVG(power) as "Avg Power (W)",
    SUM(consumption) as "Consumption (kWh)",
    MAX(power) as "Peak Power (W)"
FROM tibber_energy_data
WHERE DATE(timestamp) = CURDATE()
GROUP BY HOUR(timestamp)
ORDER BY timestamp
```

## Alerting Queries

### High Power Consumption Alert

```sql
SELECT 
    timestamp as time,
    power
FROM tibber_energy_data
WHERE $__timeFilter(timestamp)
    AND power > 3000  -- Adjust threshold as needed
ORDER BY timestamp DESC
```

### Voltage Deviation Alert

```sql
SELECT 
    timestamp as time,
    voltage1,
    voltage2,
    voltage3
FROM tibber_energy_data
WHERE $__timeFilter(timestamp)
    AND (
        voltage1 < 210 OR voltage1 > 250 OR
        voltage2 < 210 OR voltage2 > 250 OR
        voltage3 < 210 OR voltage3 > 250
    )
ORDER BY timestamp DESC
```

### Low Power Factor Alert

```sql
SELECT 
    timestamp as time,
    power_factor
FROM tibber_energy_data
WHERE $__timeFilter(timestamp)
    AND power_factor < 0.85  -- Adjust threshold as needed
ORDER BY timestamp DESC
```

## Tips for Grafana

1. **Time Macros**: Always use `$__timeFilter(timestamp)` for time-based filtering
2. **Aliases**: Use `as "Display Name"` to set column names for better visualization
3. **NULL Handling**: Filter out NULL values with `IS NOT NULL` for cleaner graphs
4. **Aggregations**: Use `GROUP BY` with time intervals for summary views
5. **Units**: Set appropriate units in Grafana panel settings (W, kWh, V, A, etc.)

## Creating Custom Panels

1. Add a new panel in Grafana
2. Select your MariaDB data source
3. Switch to "Query Editor" mode (toggle from Query Builder)
4. Paste one of the queries above
5. Adjust the query as needed
6. Configure visualization type (Time series, Stat, Gauge, etc.)
7. Set units and thresholds in panel settings
8. Save the panel

## Performance Optimization

For large datasets, consider:

```sql
-- Add time constraints
WHERE timestamp >= NOW() - INTERVAL 7 DAY

-- Use appropriate aggregations
GROUP BY DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00')

-- Limit results
LIMIT 1000
```
