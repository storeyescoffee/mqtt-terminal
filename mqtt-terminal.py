#!/usr/bin/env python3
"""
MQTT Command Receiver - Python Version
Subscribes to MQTT topic and executes received commands
"""

import paho.mqtt.client as mqtt
import json
import subprocess
import logging
import sys
import time
import signal
import os
from datetime import datetime
from uuid import UUID

# Configuration
MQTT_BROKER = "mqtt.storeyes.io"
MQTT_PORT = 1883
MQTT_TOPIC = "storeyes/request"
MQTT_RESPONSE_TOPIC = "storeyes/response"
MQTT_CLIENT_ID = "command_receiver"
MQTT_USERNAME = "storeyes"
MQTT_PASSWORD = "12345"
LOG_FILE = "mqtt_command_receiver.log"

# Global state
processed_requests = set()  # Track processed requestIds to avoid duplicates
current_working_directory = os.getcwd()  # Track current working directory

# Setup logging with colors for console
class ColoredFormatter(logging.Formatter):
    """Colored log formatter"""
    
    COLORS = {
        'DEBUG': '\033[0;36m',    # Cyan
        'INFO': '\033[0;34m',     # Blue
        'SUCCESS': '\033[0;32m',  # Green
        'WARNING': '\033[1;33m',  # Yellow
        'ERROR': '\033[0;31m',    # Red
        'CRITICAL': '\033[1;31m', # Bold Red
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname_colored = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

# Add SUCCESS level
logging.SUCCESS = 25
logging.addLevelName(logging.SUCCESS, 'SUCCESS')

def success(self, message, *args, **kwargs):
    if self.isEnabledFor(logging.SUCCESS):
        self._log(logging.SUCCESS, message, args, **kwargs)

logging.Logger.success = success

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler with colors
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = ColoredFormatter(
    fmt='[%(asctime)s] [%(levelname_colored)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(console_formatter)

# File handler without colors
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    fmt='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


def validate_uuid(uuid_string):
    """Validate if string is a valid UUID"""
    try:
        UUID(str(uuid_string))
        return True
    except (ValueError, AttributeError):
        return False


def validate_payload(payload):
    """Validate the payload structure"""
    try:
        # Check if payload is a dictionary
        if not isinstance(payload, dict):
            return False, "Payload must be a JSON object (dictionary)"
        
        # Check for requestId field
        if 'requestId' not in payload:
            return False, "Missing 'requestId' field"
        
        # Validate requestId is a valid UUID
        if not validate_uuid(payload['requestId']):
            return False, f"Invalid UUID format for requestId: {payload['requestId']}"
        
        # Check for cmd field
        if 'cmd' not in payload:
            return False, "Missing 'cmd' field"
        
        # Validate cmd is a string
        if not isinstance(payload['cmd'], str):
            return False, f"'cmd' must be a string, got {type(payload['cmd']).__name__}"
        
        # Check if cmd is not empty
        if len(payload['cmd'].strip()) == 0:
            return False, "'cmd' is empty"
        
        return True, "Valid"
    
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def is_duplicate_request(request_id):
    """Check if requestId has already been processed"""
    global processed_requests
    
    if request_id in processed_requests:
        logger.warning(f"[{request_id}] Duplicate request detected - skipping execution")
        return True
    
    # Add to processed requests
    processed_requests.add(request_id)
    logger.debug(f"[{request_id}] Added to processed requests (total: {len(processed_requests)})")
    return False


def execute_command(request_id, command):
    """Execute a single command"""
    global current_working_directory
    
    logger.info(f"[{request_id}] Executing command: {command}")
    logger.debug(f"[{request_id}] Current working directory: {current_working_directory}")
    
    try:
        start_time = time.time()
        
        # Check if it's a cd command
        if command.strip().startswith('cd '):
            # Extract the target directory
            target_dir = command.strip()[3:].strip()
            
            # Expand ~ and environment variables
            target_dir = os.path.expanduser(target_dir)
            target_dir = os.path.expandvars(target_dir)
            
            # Make it absolute if it's relative
            if not os.path.isabs(target_dir):
                target_dir = os.path.join(current_working_directory, target_dir)
            
            # Normalize the path
            target_dir = os.path.normpath(target_dir)
            
            # Check if directory exists
            if not os.path.exists(target_dir):
                duration = time.time() - start_time
                logger.error(f"[{request_id}] Directory does not exist: {target_dir}")
                return {
                    'command': command,
                    'exit_code': 1,
                    'stdout': '',
                    'stderr': f"cd: {target_dir}: No such file or directory",
                    'duration': round(duration, 2),
                    'status': 'failed',
                    'pwd': current_working_directory
                }
            
            if not os.path.isdir(target_dir):
                duration = time.time() - start_time
                logger.error(f"[{request_id}] Not a directory: {target_dir}")
                return {
                    'command': command,
                    'exit_code': 1,
                    'stdout': '',
                    'stderr': f"cd: {target_dir}: Not a directory",
                    'duration': round(duration, 2),
                    'status': 'failed',
                    'pwd': current_working_directory
                }
            
            # Change the working directory
            old_dir = current_working_directory
            current_working_directory = target_dir
            duration = time.time() - start_time
            
            logger.success(f"[{request_id}] Changed directory from {old_dir} to {current_working_directory}")
            
            return {
                'command': command,
                'exit_code': 0,
                'stdout': f"Changed directory to {current_working_directory}",
                'stderr': '',
                'duration': round(duration, 2),
                'status': 'success',
                'pwd': current_working_directory
            }
        
        # Check if it's a pwd command
        elif command.strip() == 'pwd':
            duration = time.time() - start_time
            logger.info(f"[{request_id}] Current directory: {current_working_directory}")
            
            return {
                'command': command,
                'exit_code': 0,
                'stdout': current_working_directory,
                'stderr': '',
                'duration': round(duration, 2),
                'status': 'success',
                'pwd': current_working_directory
            }
        
        # Execute regular command in the current working directory
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=current_working_directory  # Execute in current working directory
        )
        
        duration = time.time() - start_time
        
        execution_result = {
            'command': command,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'duration': round(duration, 2),
            'status': 'success' if result.returncode == 0 else 'failed',
            'pwd': current_working_directory
        }
        
        if result.returncode == 0:
            logger.success(f"[{request_id}] Command completed successfully ({duration:.2f}s)")
            
            # Log output if not empty
            if result.stdout.strip():
                logger.debug(f"[{request_id}] Command output:")
                for line in result.stdout.strip().split('\n')[:10]:  # Limit to first 10 lines in log
                    logger.debug(f"  {line}")
        else:
            logger.warning(f"[{request_id}] Command failed with exit code {result.returncode} ({duration:.2f}s)")
            
            if result.stderr.strip():
                logger.debug(f"[{request_id}] Command error:")
                for line in result.stderr.strip().split('\n')[:10]:  # Limit to first 10 lines in log
                    logger.debug(f"  {line}")
        
        return execution_result
    
    except subprocess.TimeoutExpired:
        logger.error(f"[{request_id}] Command timed out after 300 seconds")
        return {
            'command': command,
            'exit_code': -1,
            'stdout': '',
            'stderr': 'Command timed out after 300 seconds',
            'duration': 300,
            'status': 'timeout',
            'pwd': current_working_directory
        }
    
    except Exception as e:
        logger.error(f"[{request_id}] Error executing command: {str(e)}")
        return {
            'command': command,
            'exit_code': -1,
            'stdout': '',
            'stderr': str(e),
            'duration': 0,
            'status': 'error',
            'pwd': current_working_directory
        }


def publish_response(client, response):
    """Publish execution response to MQTT"""
    try:
        response_json = json.dumps(response, indent=2)
        logger.debug(f"Publishing response to topic: {MQTT_RESPONSE_TOPIC}")
        logger.debug(f"Response: {response_json}")
        
        result = client.publish(
            MQTT_RESPONSE_TOPIC,
            response_json,
            qos=1  # QoS 1 for guaranteed delivery
        )
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.success(f"[{response['requestId']}] Response published successfully with QoS 1")
        else:
            logger.error(f"[{response['requestId']}] Failed to publish response (rc: {result.rc})")
    
    except Exception as e:
        logger.error(f"Error publishing response: {str(e)}", exc_info=True)


def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        logger.success(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        logger.info(f"Subscribing to topic: {MQTT_TOPIC} with QoS 1")
        client.subscribe(MQTT_TOPIC, qos=1)  # QoS 1 subscription
    else:
        error_messages = {
            1: "Connection refused - incorrect protocol version",
            2: "Connection refused - invalid client identifier",
            3: "Connection refused - server unavailable",
            4: "Connection refused - bad username or password",
            5: "Connection refused - not authorized"
        }
        error_msg = error_messages.get(rc, f"Unknown error code: {rc}")
        logger.error(f"Failed to connect to MQTT broker: {error_msg}")
        sys.exit(1)


def on_message(client, userdata, msg):
    """Callback when a message is received"""
    try:
        logger.info(f"Received message on topic: {msg.topic} (QoS: {msg.qos})")
        
        # Decode payload
        payload_str = msg.payload.decode('utf-8')
        logger.debug(f"Raw payload: {payload_str}")
        
        # Parse JSON payload
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON payload: {str(e)}")
            logger.error(f"Payload content: {payload_str}")
            return
        
        logger.debug(f"Parsed payload: {json.dumps(payload, indent=2)}")
        
        # Validate payload
        is_valid, validation_msg = validate_payload(payload)
        if not is_valid:
            logger.error(f"Payload validation failed: {validation_msg}")
            logger.error(f"Received payload: {json.dumps(payload, indent=2)}")
            
            # Send error response
            error_response = {
                "requestId": payload.get('requestId', 'unknown'),
                "status": "validation_failed",
                "error": validation_msg,
                "result": None,
                "pwd": current_working_directory
            }
            publish_response(client, error_response)
            return
        
        request_id = payload['requestId']
        command = payload['cmd']
        
        logger.success(f"Payload validation passed for requestId: {request_id}")
        
        # Check for duplicate requestId
        if is_duplicate_request(request_id):
            # Send duplicate response
            duplicate_response = {
                "requestId": request_id,
                "status": "duplicate",
                "error": "This requestId has already been processed",
                "result": None,
                "pwd": current_working_directory
            }
            publish_response(client, duplicate_response)
            return
        
        # Execute command
        result = execute_command(request_id, command)
        
        # Prepare response
        response = {
            "requestId": request_id,
            "status": "completed",
            "result": result,
            "pwd": current_working_directory
        }
        
        # Publish response to MQTT
        publish_response(client, response)
        
        # Log summary
        logger.info(f"[{request_id}] Completed processing and published response")
    
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        
        # Try to send error response
        try:
            error_response = {
                "requestId": payload.get('requestId', 'unknown') if 'payload' in locals() else 'unknown',
                "status": "error",
                "error": str(e),
                "result": None,
                "pwd": current_working_directory
            }
            publish_response(client, error_response)
        except:
            pass


def on_disconnect(client, userdata, rc):
    """Callback when disconnected from MQTT broker"""
    if rc != 0:
        logger.warning(f"Unexpected disconnection from MQTT broker (code: {rc})")
        logger.info("Will attempt to reconnect...")
    else:
        logger.info("Disconnected from MQTT broker")


def on_subscribe(client, userdata, mid, granted_qos):
    """Callback when subscription is successful"""
    logger.success(f"Successfully subscribed to topic: {MQTT_TOPIC} (QoS: {granted_qos[0]})")


def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal, cleaning up...")
    logger.info(f"Total processed requests: {len(processed_requests)}")
    sys.exit(0)


def main():
    """Main function to run the MQTT command receiver"""
    global current_working_directory
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("MQTT Command Receiver Starting")
    logger.info(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
    logger.info(f"Subscribe Topic: {MQTT_TOPIC}")
    logger.info(f"Response Topic: {MQTT_RESPONSE_TOPIC}")
    logger.info(f"Client ID: {MQTT_CLIENT_ID}")
    logger.info(f"QoS Level: 1")
    logger.info(f"Initial Working Directory: {current_working_directory}")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info("=" * 60)
    
    # Create MQTT client
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe
    
    # Set authentication if configured
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        logger.info(f"Using authentication with username: {MQTT_USERNAME}")
    
    try:
        # Connect to MQTT broker
        logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        
        # Start the loop
        logger.info("Starting MQTT loop - listening for commands...")
        client.loop_forever()
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        logger.info(f"Total processed requests: {len(processed_requests)}")
        client.disconnect()
    except ConnectionRefusedError:
        logger.error(f"Connection refused. Is the MQTT broker running at {MQTT_BROKER}:{MQTT_PORT}?")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
