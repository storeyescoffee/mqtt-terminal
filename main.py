from __future__ import annotations

import argparse
import json
import os
import signal
import sys

import paho.mqtt.client as mqtt

from src import config
from src.machine_id import get_machine_id
from src.logging_setup import setup_logger
from src.mqtt_handlers import on_connect, on_disconnect, on_message, on_subscribe
from src.pi_kind import get_pi_kind
from src.state import AppState


def _signal_handler(logger, state: AppState):
    def handler(sig, frame):
        logger.info("Received shutdown signal, cleaning up...")
        logger.info(f"Total processed requests: {len(state.processed_requests)}")
        sys.exit(0)

    return handler


def _publish_link(logger) -> int:
    """
    Publish a one-shot link payload to `storeyes/link` and exit.
    """
    payload = {
        "deviceId": config.DEVICE_ID,
        "machineId": get_machine_id(),
        "piKind": get_pi_kind(),  # 4/5/0
    }

    client = mqtt.Client(client_id=f"{config.MQTT_CLIENT_ID}_link")

    if config.MQTT_USERNAME and config.MQTT_PASSWORD:
        client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)

    try:
        logger.info(f"Connecting to MQTT broker at {config.MQTT_BROKER}:{config.MQTT_PORT}...")
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=config.KEEPALIVE_SECONDS)
        client.loop_start()

        topic = "storeyes/link"
        payload_json = json.dumps(payload, separators=(",", ":"))
        logger.info(f"Publishing link payload to topic: {topic}")
        logger.info(f"Link payload: {payload_json}")

        info = client.publish(topic, payload_json, qos=config.QOS)
        info.wait_for_publish(timeout=10)

        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.success(f"Link payload published successfully with QoS {config.QOS}")
            return 0

        logger.error(f"Failed to publish link payload (rc: {info.rc})")
        return 2
    except Exception as e:
        logger.error(f"Failed to publish link payload: {str(e)}", exc_info=True)
        return 2
    finally:
        try:
            client.loop_stop()
        except Exception:
            pass
        try:
            client.disconnect()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(prog="mqtt-terminal")
    parser.add_argument(
        "--link",
        action="store_true",
        help="Send device-id, machine-id, and pi kind (4/5/0) to storeyes/link then exit.",
    )
    args = parser.parse_args()

    logger = setup_logger(config.LOG_FILE)

    # Start in the user's home directory so that `pwd` and all commands
    # initially run from there instead of the script location.
    home_dir = os.path.expanduser("~")
    try:
        os.chdir(home_dir)
        initial_cwd = home_dir
    except Exception:
        # Fallback: keep current process directory if we can't change it
        initial_cwd = os.getcwd()

    state = AppState(current_working_directory=initial_cwd)

    signal.signal(signal.SIGINT, _signal_handler(logger, state))
    signal.signal(signal.SIGTERM, _signal_handler(logger, state))

    if args.link:
        sys.exit(_publish_link(logger))

    logger.info("=" * 60)
    logger.info("MQTT Command Receiver Starting")
    logger.info(f"Device ID: {config.DEVICE_ID}")
    logger.info(f"Broker: {config.MQTT_BROKER}:{config.MQTT_PORT}")
    logger.info(f"Subscribe Topic: {config.MQTT_TOPIC}")
    logger.info(f"Response Topic: {config.MQTT_RESPONSE_TOPIC}")
    logger.info(f"Client ID: {config.MQTT_CLIENT_ID}")
    logger.info(f"QoS Level: {config.QOS}")
    logger.info(f"Initial Working Directory: {state.current_working_directory}")
    logger.info(f"Log file: {config.LOG_FILE}")
    logger.info("=" * 60)

    client = mqtt.Client(client_id=config.MQTT_CLIENT_ID)

    # Provide shared context to callbacks via userdata
    client.user_data_set(
        {
            "logger": logger,
            "state": state,
            "subscribe_topic": config.MQTT_TOPIC,
            "response_topic": config.MQTT_RESPONSE_TOPIC,
        }
    )

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe

    if config.MQTT_USERNAME and config.MQTT_PASSWORD:
        client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
        logger.info(f"Using authentication with username: {config.MQTT_USERNAME}")

    try:
        logger.info(f"Connecting to MQTT broker at {config.MQTT_BROKER}:{config.MQTT_PORT}...")
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=config.KEEPALIVE_SECONDS)

        logger.info("Starting MQTT loop - listening for commands...")
        client.loop_forever()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        logger.info(f"Total processed requests: {len(state.processed_requests)}")
        client.disconnect()
    except ConnectionRefusedError:
        logger.error(
            f"Connection refused. Is the MQTT broker running at {config.MQTT_BROKER}:{config.MQTT_PORT}?"
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

