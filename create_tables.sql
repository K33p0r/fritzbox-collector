CREATE TABLE fritzbox_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    online VARCHAR(32),
    external_ip VARCHAR(64),
    active_devices INT,
    time DATETIME
);

CREATE TABLE dect200_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ain VARCHAR(32),
    state INT,
    power INT,
    temperature INT,
    time DATETIME
);

CREATE TABLE speedtest_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ping_ms FLOAT,
    download_mbps FLOAT,
    upload_mbps FLOAT,
    time DATETIME
);

CREATE TABLE weather_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    location VARCHAR(128),
    temperature_celsius FLOAT,
    feels_like_celsius FLOAT,
    humidity INT,
    pressure INT,
    weather_condition VARCHAR(64),
    weather_description VARCHAR(128),
    wind_speed FLOAT,
    clouds INT,
    time DATETIME
);

CREATE TABLE electricity_price_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    price_eur_per_kwh FLOAT NOT NULL,
    valid_from DATETIME NOT NULL,
    valid_to DATETIME NULL,
    description VARCHAR(255),
    time DATETIME
);