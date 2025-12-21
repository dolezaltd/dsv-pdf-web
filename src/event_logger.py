"""Strukturované logování událostí pro Render.com konzoli.

Modul poskytuje centralizovanou třídu EventLogger pro logování
důležitých událostí v aplikaci s jednotným schématem.

Typy událostí:
- lifecycle: startup, shutdown, wake_up
- auth: login_success, login_failed, token_verified, token_invalid
- pdf: uploaded, processing_start, processing_success, processing_error, downloaded
- error: unhandled_exception
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

from .logging_setup import get_json_formatter


# Práh pro detekci wake-up po uspání (Render.com free tier uspí po 15 min)
WAKE_UP_THRESHOLD_SECONDS = 15 * 60  # 15 minut


class EventLogger:
    """Strukturované logování událostí pro Render.com konzoli.
    
    Všechny události jsou logovány do stdout ve formátu JSONL,
    což umožňuje snadné filtrování v Render.com dashboardu.
    """
    
    def __init__(self, service: str = "dsv-pdf-web"):
        """Inicializace EventLoggeru.
        
        Args:
            service: Název služby pro identifikaci v logech.
        """
        self.service = service
        self.logger = logging.getLogger("dsv.events")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        
        # Sledování času posledního requestu pro detekci wake-up
        self._last_request_time: Optional[float] = None
        self._startup_time: Optional[float] = None
        
        # Handler pouze pro konzoli (stdout)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            
            env = os.getenv("APP_ENV") or os.getenv("ENV") or "dev"
            formatter = get_json_formatter(service=service, env=env)
            handler.setFormatter(formatter)
            
            self.logger.addHandler(handler)
    
    def _log_event(
        self,
        level: int,
        event_type: str,
        event: str,
        **data: Any
    ) -> None:
        """Interní metoda pro logování události s jednotným schématem.
        
        Args:
            level: Úroveň logu (logging.INFO, logging.WARNING, logging.ERROR).
            event_type: Kategorie události (lifecycle, auth, pdf, error).
            event: Název konkrétní události.
            **data: Dodatečná data specifická pro událost.
        """
        extra: Dict[str, Any] = {
            "event_type": event_type,
            "data": data if data else None,
        }
        
        self.logger.log(level, event, extra=extra)
    
    # ========================================
    # LIFECYCLE EVENTS
    # ========================================
    
    def log_startup(self) -> None:
        """Zaloguje start serveru."""
        self._startup_time = time.time()
        self._last_request_time = self._startup_time
        
        self._log_event(
            logging.INFO,
            "lifecycle",
            "startup",
            timestamp=datetime.utcnow().isoformat() + "Z",
            message="Server started successfully",
        )
    
    def log_shutdown(self, reason: str = "normal") -> None:
        """Zaloguje vypnutí serveru.
        
        Args:
            reason: Důvod vypnutí (normal, error, signal).
        """
        uptime_seconds = None
        if self._startup_time:
            uptime_seconds = round(time.time() - self._startup_time, 2)
        
        self._log_event(
            logging.INFO,
            "lifecycle",
            "shutdown",
            reason=reason,
            uptime_seconds=uptime_seconds,
            message=f"Server shutting down: {reason}",
        )
    
    def check_and_log_wake_up(self) -> bool:
        """Zkontroluje, zda se server probudil po uspání, a případně zaloguje.
        
        Volat na začátku každého requestu.
        
        Returns:
            True pokud byl detekován wake-up, False jinak.
        """
        current_time = time.time()
        
        if self._last_request_time is None:
            self._last_request_time = current_time
            return False
        
        time_since_last_request = current_time - self._last_request_time
        self._last_request_time = current_time
        
        if time_since_last_request >= WAKE_UP_THRESHOLD_SECONDS:
            self._log_event(
                logging.INFO,
                "lifecycle",
                "wake_up",
                sleep_duration_seconds=round(time_since_last_request, 2),
                sleep_duration_minutes=round(time_since_last_request / 60, 1),
                message=f"Server woke up after {round(time_since_last_request / 60, 1)} minutes of inactivity",
            )
            return True
        
        return False
    
    # ========================================
    # AUTH EVENTS
    # ========================================
    
    def log_login_success(self, username: str, remember_me: bool = False) -> None:
        """Zaloguje úspěšné přihlášení.
        
        Args:
            username: Přihlášený uživatel.
            remember_me: Zda bylo použito "zapamatovat si mě".
        """
        self._log_event(
            logging.INFO,
            "auth",
            "login_success",
            username=username,
            remember_me=remember_me,
            message=f"User '{username}' logged in successfully",
        )
    
    def log_login_failed(self, username: str, reason: str) -> None:
        """Zaloguje neúspěšný pokus o přihlášení.
        
        Args:
            username: Uživatelské jméno z pokusu.
            reason: Důvod selhání (invalid_username, invalid_password, config_error).
        """
        self._log_event(
            logging.WARNING,
            "auth",
            "login_failed",
            username=username,
            reason=reason,
            message=f"Login failed for '{username}': {reason}",
        )
    
    def log_token_verified(self, username: str) -> None:
        """Zaloguje úspěšné ověření tokenu.
        
        Args:
            username: Uživatel z tokenu.
        """
        self._log_event(
            logging.INFO,
            "auth",
            "token_verified",
            username=username,
            message=f"Token verified for user '{username}'",
        )
    
    def log_token_invalid(self, reason: str) -> None:
        """Zaloguje neplatný nebo expirovaný token.
        
        Args:
            reason: Důvod neplatnosti (expired, invalid, missing).
        """
        self._log_event(
            logging.WARNING,
            "auth",
            "token_invalid",
            reason=reason,
            message=f"Invalid token: {reason}",
        )
    
    # ========================================
    # PDF EVENTS
    # ========================================
    
    def log_pdf_uploaded(
        self,
        filename: str,
        size_bytes: int,
        username: str,
    ) -> None:
        """Zaloguje nahrání PDF souboru.
        
        Args:
            filename: Název souboru.
            size_bytes: Velikost souboru v bajtech.
            username: Uživatel, který soubor nahrál.
        """
        size_mb = round(size_bytes / (1024 * 1024), 2)
        
        self._log_event(
            logging.INFO,
            "pdf",
            "uploaded",
            filename=filename,
            size_bytes=size_bytes,
            size_mb=size_mb,
            username=username,
            message=f"PDF '{filename}' uploaded ({size_mb} MB)",
        )
    
    def log_pdf_processing_start(
        self,
        extraction_id: str,
        filename: str,
        username: str,
    ) -> None:
        """Zaloguje začátek zpracování PDF.
        
        Args:
            extraction_id: Unikátní ID extrakce.
            filename: Název souboru.
            username: Uživatel, který spustil zpracování.
        """
        self._log_event(
            logging.INFO,
            "pdf",
            "processing_start",
            extraction_id=extraction_id,
            filename=filename,
            username=username,
            message=f"Started processing '{filename}'",
        )
    
    def log_pdf_processing_success(
        self,
        extraction_id: str,
        filename: str,
        processing_time_seconds: float,
        records_count: int,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None,
    ) -> None:
        """Zaloguje úspěšné dokončení zpracování PDF.
        
        Args:
            extraction_id: Unikátní ID extrakce.
            filename: Název souboru.
            processing_time_seconds: Doba zpracování v sekundách.
            records_count: Počet extrahovaných záznamů.
            tokens_used: Počet použitých tokenů (volitelné).
            cost_usd: Náklady v USD (volitelné).
        """
        data: Dict[str, Any] = {
            "extraction_id": extraction_id,
            "filename": filename,
            "processing_time_seconds": round(processing_time_seconds, 2),
            "records_count": records_count,
            "message": f"Successfully processed '{filename}' ({records_count} records, {round(processing_time_seconds, 1)}s)",
        }
        
        if tokens_used is not None:
            data["tokens_used"] = tokens_used
        if cost_usd is not None:
            data["cost_usd"] = round(cost_usd, 6)
        
        self._log_event(logging.INFO, "pdf", "processing_success", **data)
    
    def log_pdf_processing_error(
        self,
        extraction_id: str,
        filename: str,
        error: str,
        error_type: Optional[str] = None,
        processing_time_seconds: Optional[float] = None,
    ) -> None:
        """Zaloguje chybu při zpracování PDF.
        
        Args:
            extraction_id: Unikátní ID extrakce.
            filename: Název souboru.
            error: Popis chyby.
            error_type: Typ chyby (volitelné).
            processing_time_seconds: Doba do selhání (volitelné).
        """
        data: Dict[str, Any] = {
            "extraction_id": extraction_id,
            "filename": filename,
            "error": error,
            "message": f"Failed to process '{filename}': {error}",
        }
        
        if error_type:
            data["error_type"] = error_type
        if processing_time_seconds is not None:
            data["processing_time_seconds"] = round(processing_time_seconds, 2)
        
        self._log_event(logging.ERROR, "pdf", "processing_error", **data)
    
    def log_pdf_downloaded(
        self,
        download_id: str,
        file_type: str,
        username: str,
    ) -> None:
        """Zaloguje stažení výsledného souboru.
        
        Args:
            download_id: ID pro stažení.
            file_type: Typ souboru (csv, mrn_pdf).
            username: Uživatel, který stahuje.
        """
        self._log_event(
            logging.INFO,
            "pdf",
            "downloaded",
            download_id=download_id,
            file_type=file_type,
            username=username,
            message=f"File downloaded: {download_id}/{file_type}",
        )
    
    # ========================================
    # ERROR EVENTS
    # ========================================
    
    def log_unhandled_exception(
        self,
        error: str,
        error_type: str,
        path: Optional[str] = None,
        method: Optional[str] = None,
    ) -> None:
        """Zaloguje neošetřenou výjimku.
        
        Args:
            error: Popis chyby.
            error_type: Typ výjimky.
            path: HTTP cesta (volitelné).
            method: HTTP metoda (volitelné).
        """
        data: Dict[str, Any] = {
            "error": error,
            "error_type": error_type,
            "message": f"Unhandled exception: {error_type}: {error}",
        }
        
        if path:
            data["path"] = path
        if method:
            data["method"] = method
        
        self._log_event(logging.ERROR, "error", "unhandled_exception", **data)


# Globální instance pro použití v celé aplikaci
event_logger = EventLogger()

