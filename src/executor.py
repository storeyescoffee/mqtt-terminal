from __future__ import annotations

import os
import subprocess
import time

from src.config import COMMAND_TIMEOUT_SECONDS
from src.state import AppState


def execute_command(state: AppState, request_id: str, command: str, logger):
    logger.info(f"[{request_id}] Executing command: {command}")
    logger.debug(f"[{request_id}] Current working directory: {state.current_working_directory}")

    try:
        start_time = time.time()

        if command.strip().startswith("cd "):
            target_dir = command.strip()[3:].strip()
            target_dir = os.path.expanduser(target_dir)
            target_dir = os.path.expandvars(target_dir)
            if not os.path.isabs(target_dir):
                target_dir = os.path.join(state.current_working_directory, target_dir)
            target_dir = os.path.normpath(target_dir)

            if not os.path.exists(target_dir):
                duration = time.time() - start_time
                logger.error(f"[{request_id}] Directory does not exist: {target_dir}")
                return {
                    "command": command,
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": f"cd: {target_dir}: No such file or directory",
                    "duration": round(duration, 2),
                    "status": "failed",
                    "pwd": state.current_working_directory,
                }

            if not os.path.isdir(target_dir):
                duration = time.time() - start_time
                logger.error(f"[{request_id}] Not a directory: {target_dir}")
                return {
                    "command": command,
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": f"cd: {target_dir}: Not a directory",
                    "duration": round(duration, 2),
                    "status": "failed",
                    "pwd": state.current_working_directory,
                }

            old_dir = state.current_working_directory
            state.current_working_directory = target_dir
            duration = time.time() - start_time
            logger.success(f"[{request_id}] Changed directory from {old_dir} to {state.current_working_directory}")
            return {
                "command": command,
                "exit_code": 0,
                "stdout": f"Changed directory to {state.current_working_directory}",
                "stderr": "",
                "duration": round(duration, 2),
                "status": "success",
                "pwd": state.current_working_directory,
            }

        if command.strip() == "pwd":
            duration = time.time() - start_time
            logger.info(f"[{request_id}] Current directory: {state.current_working_directory}")
            return {
                "command": command,
                "exit_code": 0,
                "stdout": state.current_working_directory,
                "stderr": "",
                "duration": round(duration, 2),
                "status": "success",
                "pwd": state.current_working_directory,
            }

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            cwd=state.current_working_directory,
        )

        duration = time.time() - start_time
        execution_result = {
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration": round(duration, 2),
            "status": "success" if result.returncode == 0 else "failed",
            "pwd": state.current_working_directory,
        }

        if result.returncode == 0:
            logger.success(f"[{request_id}] Command completed successfully ({duration:.2f}s)")
            if result.stdout.strip():
                logger.debug(f"[{request_id}] Command output:")
                for line in result.stdout.strip().split("\n")[:10]:
                    logger.debug(f"  {line}")
        else:
            logger.warning(f"[{request_id}] Command failed with exit code {result.returncode} ({duration:.2f}s)")
            if result.stderr.strip():
                logger.debug(f"[{request_id}] Command error:")
                for line in result.stderr.strip().split("\n")[:10]:
                    logger.debug(f"  {line}")

        return execution_result

    except subprocess.TimeoutExpired:
        logger.error(f"[{request_id}] Command timed out after {COMMAND_TIMEOUT_SECONDS} seconds")
        return {
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {COMMAND_TIMEOUT_SECONDS} seconds",
            "duration": COMMAND_TIMEOUT_SECONDS,
            "status": "timeout",
            "pwd": state.current_working_directory,
        }
    except Exception as e:
        logger.error(f"[{request_id}] Error executing command: {str(e)}")
        return {
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "duration": 0,
            "status": "error",
            "pwd": state.current_working_directory,
        }

