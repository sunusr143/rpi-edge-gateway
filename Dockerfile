FROM python:3.11-slim
WORKDIR /app
COPY gateway ./gateway
# paho-mqtt is only needed for real MQTT publishing
RUN pip install --no-cache-dir paho-mqtt==1.6.1
USER nobody
CMD ["python", "-m", "gateway", "--cycles", "12"]
