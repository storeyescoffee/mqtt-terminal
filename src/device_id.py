import os
import re


def sanitize_topic_segment(value: str) -> str:
    """
    MQTT topic segments shouldn't contain '/' and should be predictable.
    Keep only safe characters; collapse others to '-'.
    """
    value = (value or "").strip()
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value)
    value = value.strip("-")
    return value or "unknown"


def get_pi_serial_id() -> str:
    """
    Best-effort Raspberry Pi serial id.
    - Primary: /proc/cpuinfo (common on Pi OS)
    - Secondary: /sys/firmware/devicetree/base/serial-number (some distros)
    - Fallback: env STOREYES_DEVICE_ID or hostname
    """
    env_override = os.getenv("STOREYES_DEVICE_ID")
    if env_override:
        return env_override

    candidates: list[str] = []

    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.lower().startswith("serial"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        candidates.append(parts[1].strip())
    except Exception:
        pass

    try:
        # Often contains a trailing NUL; strip it.
        with open(
            "/sys/firmware/devicetree/base/serial-number",
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as f:
            candidates.append(f.read().replace("\x00", "").strip())
    except Exception:
        pass

    candidates.append(os.uname().nodename if hasattr(os, "uname") else os.getenv("COMPUTERNAME", "unknown"))

    for c in candidates:
        c = (c or "").strip()
        if c:
            return c
    return "unknown"

