CREATE TABLE IF NOT EXISTS tibber_consumption (
    id INT AUTO_INCREMENT PRIMARY KEY,
    consumption_kwh FLOAT,
    cost FLOAT,
    unit_price FLOAT,
    from_time DATETIME,
    to_time DATETIME,
    current_price_total FLOAT,
    current_price_energy FLOAT,
    current_price_tax FLOAT,
    price_starts_at DATETIME,
    real_time_enabled BOOLEAN,
    time DATETIME
);
