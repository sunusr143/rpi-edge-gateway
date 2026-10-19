FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY gateway ./gateway
# State (the SQLite buffer) must live on a volume so it survives restarts.
RUN useradd --system --create-home gateway && mkdir -p /var/lib/gateway && chown gateway /var/lib/gateway
USER gateway
VOLUME /var/lib/gateway
# Needs --device /dev/ttyUSB0 and the MQTT_* environment variables at run time.
CMD ["python", "-m", "gateway.run"]
