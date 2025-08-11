CREATE TABLE speedtest_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ping_ms FLOAT,
    download_mbps FLOAT,
    upload_mbps FLOAT,
    time DATETIME
);