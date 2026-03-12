from __future__ import annotations

import json
import sys

import paho.mqtt.client as mqtt

from src.config import MQTT_BROKER, MQTT_PORT, QOS
from src.executor import execute_command
from src.state import AppState, is_duplicate_request
from src.validation import validate_payload


def publish_response(client, response_topic: str, response: dict, logger):
    try:
        response_json = json.dumps(response, indent=2)
        logger.debug(f"Publishing response to topic: {response_topic}")
        logger.debug(f"Response: {response_json}")

        result = client.publish(response_topic, response_json, qos=QOS)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.success(f"[{response.get('requestId', 'unknown')}] Response published successfully with QoS {QOS}")
        else:
            logger.error(
                f"[{response.get('requestId', 'unknown')}] Failed to publish response (rc: {result.rc})"
            )
    except Exception as e:
        logger.error(f"Error publishing response: {str(e)}", exc_info=True)


def on_connect(client, userdata, flags, rc):
    logger = userdata["logger"]
    subscribe_topic = userdata["subscribe_topic"]

    if rc == 0:
        logger.success(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        logger.info(f"Subscribing to topic: {subscribe_topic} with QoS {QOS}")
        client.subscribe(subscribe_topic, qos=QOS)
        return

    error_messages = {
        1: "Connection refused - incorrect protocol version",
        2: "Connection refused - invalid client identifier",
        3: "Connection refused - server unavailable",
        4: "Connection refused - bad username or password",
        5: "Connection refused - not authorized",
    }
    error_msg = error_messages.get(rc, f"Unknown error code: {rc}")
    logger.error(f"Failed to connect to MQTT broker: {error_msg}")
    sys.exit(1)


def on_message(client, userdata, msg):
    logger = userdata["logger"]
    state: AppState = userdata["state"]
    response_topic = userdata["response_topic"]

    try:
        logger.info(f"Received message on topic: {msg.topic} (QoS: {msg.qos})")

        payload_str = msg.payload.decode("utf-8")
        logger.debug(f"Raw payload: {payload_str}")

        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON payload: {str(e)}")
            logger.error(f"Payload content: {payload_str}")
            return

        logger.debug(f"Parsed payload: {json.dumps(payload, indent=2)}")

        is_valid, validation_msg = validate_payload(payload)
        if not is_valid:
            logger.error(f"Payload validation failed: {validation_msg}")
            logger.error(f"Received payload: {json.dumps(payload, indent=2)}")

            error_response = {
                "requestId": payload.get("requestId", "unknown"),
                "status": "validation_failed",
                "error": validation_msg,
                "result": None,
                "pwd": state.current_working_directory,
            }
            publish_response(client, response_topic, error_response, logger)
            return

        request_id = payload["requestId"]
        command = payload["cmd"]
        logger.success(f"Payload validation passed for requestId: {request_id}")

        if is_duplicate_request(state, request_id, logger):
            duplicate_response = {
                "requestId": request_id,
                "status": "duplicate",
                "error": "This requestId has already been processed",
                "result": None,
                "pwd": state.current_working_directory,
            }
            publish_response(client, response_topic, duplicate_response, logger)
            return

        result = execute_command(state, request_id, command, logger)

        response = {
            "requestId": request_id,
            "status": "completed",
            "result": result,
            "pwd": state.current_working_directory,
        }
        publish_response(client, response_topic, response, logger)
        logger.info(f"[{request_id}] Completed processing and published response")

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)

        try:
            error_response = {
                "requestId": payload.get("requestId", "unknown") if "payload" in locals() else "unknown",
                "status": "error",
                "error": str(e),
                "result": None,
                "pwd": state.current_working_directory,
            }
            publish_response(client, response_topic, error_response, logger)
        except Exception:
            pass


def on_disconnect(client, userdata, rc):
    logger = userdata["logger"]
    if rc != 0:
        logger.warning(f"Unexpected disconnection from MQTT broker (code: {rc})")
        logger.info("Will attempt to reconnect...")
    else:
        logger.info("Disconnected from MQTT broker")


def on_subscribe(client, userdata, mid, granted_qos):
    logger = userdata["logger"]
    subscribe_topic = userdata["subscribe_topic"]
    logger.success(f"Successfully subscribed to topic: {subscribe_topic} (QoS: {granted_qos[0]})")

