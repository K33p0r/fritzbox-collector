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