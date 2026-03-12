from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AppState:
    processed_requests: set[str] = field(default_factory=set)
    current_working_directory: str = ""


def is_duplicate_request(state: AppState, request_id: str, logger) -> bool:
    if request_id in state.processed_requests:
        logger.warning(f"[{request_id}] Duplicate request detected - skipping execution")
        return True

    state.processed_requests.add(request_id)
    logger.debug(f"[{request_id}] Added to processed requests (total: {len(state.processed_requests)})")
    return False

