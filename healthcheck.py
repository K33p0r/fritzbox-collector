import os
import time

log_file = os.getenv("LOG_FILE", "/config/fritzbox_collector.log")
try:
    mtime = os.path.getmtime(log_file)
    # Wenn die Logdatei in den letzten 10 Minuten geschrieben wurde, ist alles ok
    if time.time() - mtime > 600:
        exit(1)
except Exception:
    exit(1)