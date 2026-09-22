import json
import sys
import traceback as tb_module
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

_current_context: dict = {}
_log_path: Path | None = None


def _get_log_path() -> Path:
    global _log_path
    if _log_path is None:
        _log_path = settings.data_path / "errors.jsonl"
        _log_path.parent.mkdir(parents=True, exist_ok=True)
    return _log_path


def set_context(**kwargs) -> None:
    _current_context.update(kwargs)


def clear_context() -> None:
    _current_context.clear()


def get_context() -> dict:
    return dict(_current_context)


def _get_traceback() -> str | None:
    exc = sys.exc_info()
    if exc and exc[1]:
        return "".join(tb_module.format_exception(*exc))
    return None


def log_error(
    error_type: str,
    error_message: str,
    context: str | None = None,
    project_id: str | None = None,
    page_url: str | None = None,
    **extra,
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_type": error_type,
        "error_message": error_message,
        "context": context,
        "project_id": project_id,
        "page_url": page_url,
        "traceback": _get_traceback(),
        "bot_context": _current_context.copy(),
    }
    entry.update(extra)

    path = _get_log_path()
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def read_errors(limit: int = 50) -> list[dict]:
    path = _get_log_path()
    if not path.exists():
        return []
    errors = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        errors.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass
    return errors[-limit:]
