FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fritzbox_collector.py .
COPY weather_collector.py .
COPY electricity_price.py .
COPY notify.py .
COPY healthcheck.py .

# Healthcheck prüft, ob das Skript läuft und die Logdatei aktualisiert wurde
HEALTHCHECK --interval=5m --timeout=30s --retries=3 CMD python3 healthcheck.py || exit 1

CMD ["python", "fritzbox_collector.py"]