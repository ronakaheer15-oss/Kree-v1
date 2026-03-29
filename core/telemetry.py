import json
import logging
import re
import threading
import time
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class TelemetryEvents:
    SESSION_INIT = "session_init"
    CONNECTION_OPEN = "connection_open"
    CONNECTION_ERROR = "connection_error"
    RECONNECT_WAIT = "reconnect_wait"
    USER_TEXT = "user_text"
    INPUT_TRANSCRIPT = "input_transcript"
    OUTPUT_TRANSCRIPT = "output_transcript"
    TOOL_MODEL_REQUEST = "tool_model_request"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_BLOCKED = "tool_blocked"
    MIC_STARTED = "mic_started"
    MIC_ERROR = "mic_error"
    RECEIVE_ERROR = "receive_error"


class TelemetryLogger:
    """Thread-safe event logger with rotating file output."""

    def __init__(self, base_dir: Path, settings: dict[str, Any] | None = None) -> None:
        cfg = settings or {}
        self.enabled = bool(cfg.get("enabled", True))
        self._session_id = uuid.uuid4().hex[:12]
        self._local = threading.local()
        self._lock = threading.Lock()
        self.log_file: Path | None = None

        self._logger = logging.getLogger("kree.telemetry")
        self._logger.propagate = False

        log_file_rel = str(cfg.get("log_file", "logs/kree_events.log"))
        self.log_file = (base_dir / log_file_rel).resolve()
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.enabled:
            self._logger.disabled = True
            return

        self._logger.setLevel(getattr(logging, str(cfg.get("level", "INFO")).upper(), logging.INFO))
        self._logger.handlers.clear()

        max_bytes = int(cfg.get("max_bytes", 1048576) or 1048576)
        backup_count = int(cfg.get("backup_count", 5) or 5)

        handler = RotatingFileHandler(
            filename=str(self.log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        self._logger.addHandler(handler)

    @property
    def session_id(self) -> str:
        return self._session_id

    def set_context(self, **context: Any) -> None:
        self._local.context = dict(context)

    def event(self, event_type: str, message: str = "", **fields: Any) -> None:
        if not self.enabled:
            return

        payload = {
            "ts": round(time.time(), 3),
            "session_id": self._session_id,
            "thread_id": threading.get_ident(),
            "event_type": event_type,
            "message": message,
        }
        payload.update(getattr(self._local, "context", {}))
        payload.update(fields)

        with self._lock:
            self._logger.info(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def load_session_events(log_file: Path, session_id: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    if not log_file.exists():
        return []

    events: list[dict[str, Any]] = []
    try:
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []

    for raw_line in reversed(lines):
        if not raw_line.strip():
            continue

        payload_text = raw_line
        if " | " in raw_line:
            parts = raw_line.split(" | ", 2)
            if len(parts) >= 3:
                payload_text = parts[2].strip()

        try:
            payload = json.loads(payload_text)
        except Exception:
            continue

        if not isinstance(payload, dict):
            continue
        if session_id and str(payload.get("session_id", "")) != session_id:
            continue

        events.append(payload)
        if len(events) >= limit:
            break

    events.reverse()
    return events


def export_session_trace(base_dir: Path, logger: TelemetryLogger, label: str = "session_trace", limit: int = 500) -> Path:
    trace_dir = (base_dir / "logs" / "traces").resolve()
    trace_dir.mkdir(parents=True, exist_ok=True)

    events = load_session_events(logger.log_file or trace_dir / "kree_events.log", logger.session_id, limit)
    summary: dict[str, int] = {}
    for event in events:
        event_type = str(event.get("event_type", "unknown"))
        summary[event_type] = summary.get(event_type, 0) + 1

    safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(label).strip())[:48] or "session_trace"
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    trace_path = trace_dir / f"{safe_label}-{logger.session_id}-{timestamp}.json"

    payload = {
        "label": safe_label,
        "session_id": logger.session_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "event_count": len(events),
        "summary": summary,
        "events": events,
    }

    trace_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return trace_path
