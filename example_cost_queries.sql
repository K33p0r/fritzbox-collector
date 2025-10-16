-- SQL-Abfragen für Stromkosten-Berechnungen
-- Diese Beispiele zeigen, wie man den Strompreis für Auswertungen verwendet

-- 1. Aktuellen Strompreis abrufen
SELECT price_eur_per_kwh, valid_from, description
FROM electricity_price_config
WHERE valid_to IS NULL OR valid_to > NOW()
ORDER BY valid_from DESC
LIMIT 1;

-- 2. Stromkosten für DECT-Geräte berechnen (pro Messung)
-- Formel: (power_mw / 1.000.000) * (Intervall_in_Sekunden / 3600) * Preis_EUR_pro_kWh
SELECT 
    d.ain,
    d.device_name,
    d.multimeter_power as power_mw,
    d.time,
    (d.multimeter_power / 1000000.0) * (300 / 3600.0) * p.price_eur_per_kwh as cost_eur_per_interval,
    p.price_eur_per_kwh
FROM dect200_data d
CROSS JOIN (
    SELECT price_eur_per_kwh 
    FROM electricity_price_config 
    WHERE valid_to IS NULL OR valid_to > NOW()
    ORDER BY valid_from DESC 
    LIMIT 1
) p
WHERE d.multimeter_power IS NOT NULL
ORDER BY d.time DESC
LIMIT 100;

-- 3. Tägliche Stromkosten pro DECT-Gerät
SELECT 
    DATE(d.time) as tag,
    d.ain,
    d.device_name,
    COUNT(*) as anzahl_messungen,
    AVG(d.multimeter_power) as durchschnitt_mw,
    SUM((d.multimeter_power / 1000000.0) * (300 / 3600.0) * p.price_eur_per_kwh) as kosten_eur_pro_tag,
    p.price_eur_per_kwh
FROM dect200_data d
CROSS JOIN (
    SELECT price_eur_per_kwh 
    FROM electricity_price_config 
    WHERE valid_to IS NULL OR valid_to > NOW()
    ORDER BY valid_from DESC 
    LIMIT 1
) p
WHERE d.multimeter_power IS NOT NULL
GROUP BY DATE(d.time), d.ain, d.device_name, p.price_eur_per_kwh
ORDER BY tag DESC, d.ain
LIMIT 30;

-- 4. Monatliche Gesamtkosten aller DECT-Geräte
SELECT 
    DATE_FORMAT(d.time, '%Y-%m') as monat,
    COUNT(DISTINCT d.ain) as anzahl_geraete,
    COUNT(*) as anzahl_messungen,
    SUM((d.multimeter_power / 1000000.0) * (300 / 3600.0) * p.price_eur_per_kwh) as gesamtkosten_eur,
    p.price_eur_per_kwh
FROM dect200_data d
CROSS JOIN (
    SELECT price_eur_per_kwh 
    FROM electricity_price_config 
    WHERE valid_to IS NULL OR valid_to > NOW()
    ORDER BY valid_from DESC 
    LIMIT 1
) p
WHERE d.multimeter_power IS NOT NULL
GROUP BY DATE_FORMAT(d.time, '%Y-%m'), p.price_eur_per_kwh
ORDER BY monat DESC;

-- 5. Gerät mit höchsten Stromkosten (letzte 7 Tage)
SELECT 
    d.ain,
    d.device_name,
    COUNT(*) as anzahl_messungen,
    AVG(d.multimeter_power) as durchschnitt_mw,
    MAX(d.multimeter_power) as max_mw,
    SUM((d.multimeter_power / 1000000.0) * (300 / 3600.0) * p.price_eur_per_kwh) as kosten_eur_7_tage,
    p.price_eur_per_kwh
FROM dect200_data d
CROSS JOIN (
    SELECT price_eur_per_kwh 
    FROM electricity_price_config 
    WHERE valid_to IS NULL OR valid_to > NOW()
    ORDER BY valid_from DESC 
    LIMIT 1
) p
WHERE d.multimeter_power IS NOT NULL
  AND d.time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY d.ain, d.device_name, p.price_eur_per_kwh
ORDER BY kosten_eur_7_tage DESC;

-- 6. Stromverbrauch und Kosten für ein spezifisches Gerät (letzte 24 Stunden)
-- AIN ersetzen mit tatsächlicher Geräte-AIN
SELECT 
    d.time,
    d.ain,
    d.device_name,
    d.multimeter_power as power_mw,
    (d.multimeter_power / 1000.0) as power_w,
    (d.multimeter_power / 1000000.0) * (300 / 3600.0) as energy_kwh_per_interval,
    (d.multimeter_power / 1000000.0) * (300 / 3600.0) * p.price_eur_per_kwh as cost_eur_per_interval,
    p.price_eur_per_kwh
FROM dect200_data d
CROSS JOIN (
    SELECT price_eur_per_kwh 
    FROM electricity_price_config 
    WHERE valid_to IS NULL OR valid_to > NOW()
    ORDER BY valid_from DESC 
    LIMIT 1
) p
WHERE d.ain = 'DEINE_GERAETE_AIN_HIER'  -- Ersetzen!
  AND d.time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
ORDER BY d.time DESC;

-- 7. Hochrechnung: Jahreskosten basierend auf letzten 30 Tagen
SELECT 
    d.ain,
    d.device_name,
    COUNT(*) as messungen_30_tage,
    AVG(d.multimeter_power) as durchschnitt_mw,
    SUM((d.multimeter_power / 1000000.0) * (300 / 3600.0) * p.price_eur_per_kwh) as kosten_30_tage_eur,
    SUM((d.multimeter_power / 1000000.0) * (300 / 3600.0) * p.price_eur_per_kwh) * (365.0 / 30.0) as hochgerechnete_jahreskosten_eur,
    p.price_eur_per_kwh
FROM dect200_data d
CROSS JOIN (
    SELECT price_eur_per_kwh 
    FROM electricity_price_config 
    WHERE valid_to IS NULL OR valid_to > NOW()
    ORDER BY valid_from DESC 
    LIMIT 1
) p
WHERE d.multimeter_power IS NOT NULL
  AND d.time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY d.ain, d.device_name, p.price_eur_per_kwh
ORDER BY hochgerechnete_jahreskosten_eur DESC;
