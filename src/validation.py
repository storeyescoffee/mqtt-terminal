from __future__ import annotations

from uuid import UUID


def validate_uuid(uuid_string) -> bool:
    try:
        UUID(str(uuid_string))
        return True
    except (ValueError, AttributeError):
        return False


def validate_payload(payload):
    try:
        if not isinstance(payload, dict):
            return False, "Payload must be a JSON object (dictionary)"

        if "requestId" not in payload:
            return False, "Missing 'requestId' field"

        if not validate_uuid(payload["requestId"]):
            return False, f"Invalid UUID format for requestId: {payload['requestId']}"

        if "cmd" not in payload:
            return False, "Missing 'cmd' field"

        if not isinstance(payload["cmd"], str):
            return False, f"'cmd' must be a string, got {type(payload['cmd']).__name__}"

        if len(payload["cmd"].strip()) == 0:
            return False, "'cmd' is empty"

        return True, "Valid"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

