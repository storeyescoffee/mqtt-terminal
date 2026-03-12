from __future__ import annotations

from src.device_id import get_pi_serial_id, sanitize_topic_segment

# Core configuration
MQTT_BROKER = "mqtt.storeyes.io"
MQTT_PORT = 1883
MQTT_USERNAME = "storeyes"
MQTT_PASSWORD = "12345"

QOS = 1
KEEPALIVE_SECONDS = 60
COMMAND_TIMEOUT_SECONDS = 300

LOG_FILE = "mqtt_command_receiver.log"

# Device-scoped topics / client id
DEVICE_ID = sanitize_topic_segment(get_pi_serial_id())
MQTT_TOPIC = f"storeyes/{DEVICE_ID}/request"
MQTT_RESPONSE_TOPIC = f"storeyes/{DEVICE_ID}/response"
MQTT_CLIENT_ID = f"command_receiver_{DEVICE_ID}"

