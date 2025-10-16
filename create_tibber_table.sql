-- Tibber Energy Data Table
-- Stores energy consumption data from Tibber Pulse IR

CREATE TABLE IF NOT EXISTS tibber_energy_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME,
    consumption FLOAT COMMENT 'Energy consumption in kWh',
    accumulated_consumption FLOAT COMMENT 'Total accumulated consumption in kWh',
    accumulated_cost FLOAT COMMENT 'Total accumulated cost',
    currency VARCHAR(8) COMMENT 'Currency code (e.g., EUR, NOK)',
    power INT COMMENT 'Current power in Watts',
    power_production INT COMMENT 'Power production in Watts (if applicable)',
    min_power INT COMMENT 'Minimum power in the period',
    average_power INT COMMENT 'Average power in the period',
    max_power INT COMMENT 'Maximum power in the period',
    voltage1 FLOAT COMMENT 'Voltage on phase L1 in Volts',
    voltage2 FLOAT COMMENT 'Voltage on phase L2 in Volts',
    voltage3 FLOAT COMMENT 'Voltage on phase L3 in Volts',
    current1 FLOAT COMMENT 'Current on phase L1 in Amperes',
    current2 FLOAT COMMENT 'Current on phase L2 in Amperes',
    current3 FLOAT COMMENT 'Current on phase L3 in Amperes',
    power_factor FLOAT COMMENT 'Power factor (0-1)',
    signal_strength INT COMMENT 'Signal strength percentage',
    INDEX idx_timestamp (timestamp),
    INDEX idx_power (power),
    INDEX idx_cost (accumulated_cost)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Tibber Pulse IR energy consumption data';
