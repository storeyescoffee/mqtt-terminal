from __future__ import annotations

import os
import sys


def _read_first_existing(paths: tuple[str, ...]) -> str | None:
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            pass
    return None


def get_pi_kind() -> int:
    """
    Return Raspberry Pi generation kind:
    - 5 for Raspberry Pi 5
    - 4 for Raspberry Pi 4
    - 0 otherwise/unknown

    Override with env STOREYES_PI_KIND (accepted: 0/4/5).
    """
    env_override = (os.getenv("STOREYES_PI_KIND") or "").strip()
    if env_override in {"0", "4", "5"}:
        return int(env_override)

    if not sys.platform.startswith("linux"):
        return 0

    model = _read_first_existing(
        (
            "/proc/device-tree/model",
            "/sys/firmware/devicetree/base/model",
        )
    )
    if not model:
        return 0

    model_l = model.lower()
    if "raspberry pi 5" in model_l:
        return 5
    if "raspberry pi 4" in model_l:
        return 4
    return 0

