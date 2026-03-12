from __future__ import annotations

import os
import subprocess
import sys


def get_machine_id() -> str:
    """
    Best-effort stable machine id across OSes.
    - Linux: /etc/machine-id (or /var/lib/dbus/machine-id)
    - Windows: MachineGuid from registry (via `reg query`)
    - Fallback: env STOREYES_MACHINE_ID
    """
    env_override = os.getenv("STOREYES_MACHINE_ID")
    if env_override:
        return env_override.strip()

    if sys.platform.startswith("linux"):
        for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    value = f.read().strip()
                    if value:
                        return value
            except Exception:
                pass

    if sys.platform.startswith("win"):
        try:
            # Example output line:
            # MachineGuid    REG_SZ    12345678-1234-1234-1234-1234567890ab
            result = subprocess.run(
                [
                    "reg",
                    "query",
                    r"HKLM\SOFTWARE\Microsoft\Cryptography",
                    "/v",
                    "MachineGuid",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            out = (result.stdout or "") + "\n" + (result.stderr or "")
            for line in out.splitlines():
                if "MachineGuid" in line and "REG_" in line:
                    parts = [p for p in line.split() if p]
                    if parts:
                        return parts[-1].strip()
        except Exception:
            pass

    return "unknown"

