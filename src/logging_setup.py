"""Centralizované nastavení logování pro backend.

Cíle:
- strukturované JSONL logy do souborů (bez DB)
- denní rotace + retence
- request correlation pomocí contextvars (request_id + http metadata)
- redakce citlivých údajů
"""

from __future__ import annotations

import contextvars
import gzip
import logging
import os
import shutil
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from pythonjsonlogger.json import JsonFormatter

from .config import PROJECT_ROOT


# -------- Request-scoped context (FastAPI middleware plní, log filter čte) --------
_request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)
_http_var: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "http", default=None
)
_client_var: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "client", default=None
)


def set_request_context(
    *,
    request_id: Optional[str],
    http: Optional[Dict[str, Any]] = None,
    client: Optional[Dict[str, Any]] = None,
) -> None:
    """Naváže request metadata do contextvars (platí pro aktuální task/request)."""

    _request_id_var.set(request_id)
    _http_var.set(http)
    _client_var.set(client)


def clear_request_context() -> None:
    """Vyčistí request metadata z contextvars."""

    _request_id_var.set(None)
    _http_var.set(None)
    _client_var.set(None)


class RequestContextFilter(logging.Filter):
    """Doplňuje request kontext do každého LogRecordu."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = _request_id_var.get()
        if not hasattr(record, "http"):
            record.http = _http_var.get()
        if not hasattr(record, "client"):
            record.client = _client_var.get()
        return True


# -------- Redakce citlivých dat --------
_SENSITIVE_KEYS = {
    "api_key",
    "openai_api_key",
    "anthropic_api_key",
    "google_api_key",
    "authorization",
    "token",
    "access_token",
    "refresh_token",
    "password",
    "secret",
    "x-api-key",
}

_PATH_KEYS = {
    "pdf_path",
    "file_path",
}


def _redact_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if k_lower in _SENSITIVE_KEYS:
                out[k] = "[REDACTED]"
                continue
            if k_lower in _PATH_KEYS and isinstance(v, (str, Path)):
                out[k] = Path(v).name
                continue
            out[k] = _redact_obj(v)
        return out
    if isinstance(obj, list):
        return [_redact_obj(x) for x in obj]
    if isinstance(obj, tuple):
        return tuple(_redact_obj(x) for x in obj)
    return obj


class RedactionFilter(logging.Filter):
    """Maskuje citlivé hodnoty v extra polích a ve zprávě pokud je dict."""

    def filter(self, record: logging.LogRecord) -> bool:
        # 1) Pokud někdo loguje dict jako msg, umíme ho zredigovat
        if isinstance(record.msg, dict):
            record.msg = _redact_obj(record.msg)

        # 2) Redakce extra atributů v record.__dict__
        for k, v in list(record.__dict__.items()):
            k_lower = str(k).lower()
            if k_lower in _SENSITIVE_KEYS:
                record.__dict__[k] = "[REDACTED]"
            elif k_lower in _PATH_KEYS and isinstance(v, (str, Path)):
                record.__dict__[k] = Path(v).name
            elif isinstance(v, (dict, list, tuple)):
                record.__dict__[k] = _redact_obj(v)

        return True


# -------- Handlery a formattery --------
_DEFAULT_FORMATTER: Optional[JsonFormatter] = None


def get_json_formatter(
    *,
    service: str,
    env: str,
    version: Optional[str] = None,
) -> JsonFormatter:
    """Vytvoří JsonFormatter s jednotným schématem."""

    static_fields = {
        "service": service,
        "env": env,
    }
    if version:
        static_fields["version"] = version

    # Pozn.: rename_fields mapuje standardní LogRecord pole do našeho schématu.
    return JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
            "message": "event",
        },
        static_fields=static_fields,
        defaults={
            "request_id": None,
            "http": None,
            "client": None,
        },
        json_ensure_ascii=False,
    )


def _gzip_namer(default_name: str) -> str:
    return default_name + ".gz"


def _gzip_rotator(source: str, dest: str) -> None:
    with open(source, "rb") as sf, gzip.open(dest, "wb") as df:
        shutil.copyfileobj(sf, df)
    try:
        os.remove(source)
    except OSError:
        pass


def create_timed_rotating_jsonl_handler(
    *,
    log_file: Path,
    level: int,
    formatter: JsonFormatter,
    when: str = "midnight",
    backup_count: int = 30,
    utc: bool = True,
    compress: bool = True,
) -> TimedRotatingFileHandler:
    """Vytvoří handler pro JSONL log do souboru s denní rotací."""

    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when=when,
        backupCount=backup_count,
        utc=utc,
        encoding="utf-8",
        delay=True,
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)

    if compress:
        handler.namer = _gzip_namer
        handler.rotator = _gzip_rotator

    return handler


def setup_logging(
    *,
    service: str = "dsv-pdf-web",
    env: Optional[str] = None,
    version: Optional[str] = None,
    log_dir: Optional[Path] = None,
    backup_days: int = 30,
) -> None:
    """Nastaví logování pro celý proces (root + dsv.access).

    Poznámka: pro `ExtractionLogger` se handler váže přímo v `src/logger.py`,
    protože umí logovat do různých souborů (api/batch).
    """

    global _DEFAULT_FORMATTER

    resolved_env = env or os.getenv("APP_ENV") or os.getenv("ENV") or "dev"
    resolved_log_dir = Path(log_dir) if log_dir else (PROJECT_ROOT / "logs")
    resolved_log_dir.mkdir(parents=True, exist_ok=True)

    formatter = get_json_formatter(service=service, env=resolved_env, version=version)
    _DEFAULT_FORMATTER = formatter

    context_filter = RequestContextFilter()
    redaction_filter = RedactionFilter()

    # Root logger: aplikační + error log
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Odstraníme existující handlery (typicky uvicorn/basicConfig), ať neděláme duplicitní výstupy
    for h in list(root.handlers):
        root.removeHandler(h)

    for f in list(root.filters):
        root.removeFilter(f)

    root.addFilter(context_filter)
    root.addFilter(redaction_filter)

    app_handler = create_timed_rotating_jsonl_handler(
        log_file=resolved_log_dir / "app.jsonl",
        level=logging.INFO,
        formatter=formatter,
        backup_count=backup_days,
    )
    error_handler = create_timed_rotating_jsonl_handler(
        log_file=resolved_log_dir / "error.jsonl",
        level=logging.ERROR,
        formatter=formatter,
        backup_count=backup_days,
    )

    # Konzole necháme pro lokální debugging (stderr), v produkci ji můžete vypnout přes env.
    console_level = os.getenv("CONSOLE_LOG_LEVEL", "INFO").upper()
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, console_level, logging.INFO))
    console_handler.setFormatter(formatter)

    root.addHandler(app_handler)
    root.addHandler(error_handler)

    if os.getenv("ENABLE_CONSOLE_LOGS", "1") not in {"0", "false", "False"}:
        root.addHandler(console_handler)

    # Access logger: oddělený soubor, nepropaguje do root
    access_logger = logging.getLogger("dsv.access")
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False

    for h in list(access_logger.handlers):
        access_logger.removeHandler(h)
    for f in list(access_logger.filters):
        access_logger.removeFilter(f)

    access_logger.addFilter(context_filter)
    access_logger.addFilter(redaction_filter)

    access_handler = create_timed_rotating_jsonl_handler(
        log_file=resolved_log_dir / "access.jsonl",
        level=logging.INFO,
        formatter=formatter,
        backup_count=backup_days,
    )
    access_logger.addHandler(access_handler)

    # Uvicorn access logy typicky nechceme duplicitně (máme vlastní access schema s request_id).
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_default_formatter() -> Optional[JsonFormatter]:
    return _DEFAULT_FORMATTER
