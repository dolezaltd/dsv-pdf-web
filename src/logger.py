"""Modul pro logování průběhu vytěžení."""
import json
import logging
import gzip
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Iterable, List
from .config import PROJECT_ROOT
from .logging_setup import (
    RequestContextFilter,
    RedactionFilter,
    create_timed_rotating_jsonl_handler,
    get_default_formatter,
    get_json_formatter,
)


class ExtractionLogger:
    """Třída pro logování průběhu vytěžení PDF souborů."""
    
    def __init__(self, log_file: Optional[Path] = None):
        """
        Inicializace loggeru.
        
        Args:
            log_file: Cesta k logovacímu souboru. Pokud není zadána, použije se extraction_log.jsonl ve složce logs/.
        """
        if log_file is None:
            log_file = PROJECT_ROOT / "logs" / "extraction_log.jsonl"
        
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Unikátní logger per cílový soubor (API/batch mohou logovat do různých JSONL)
        safe_name = self.log_file.stem.replace(".", "_").replace("-", "_")
        self.logger = logging.getLogger(f"dsv.extraction.{safe_name}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        # Filtry: request context + redakce citlivých dat
        if not any(isinstance(f, RequestContextFilter) for f in self.logger.filters):
            self.logger.addFilter(RequestContextFilter())
        if not any(isinstance(f, RedactionFilter) for f in self.logger.filters):
            self.logger.addFilter(RedactionFilter())

        # Formatter: pokud už existuje globálně (setup_logging), použijeme ho.
        formatter = get_default_formatter()
        if formatter is None:
            env = os.getenv("APP_ENV") or os.getenv("ENV") or "dev"
            formatter = get_json_formatter(service="dsv-pdf-web", env=env)

        # Handler: denní rotace, 30 dní retence, gzip pro archivy.
        target = str(self.log_file.resolve())
        for h in self.logger.handlers:
            if getattr(h, "baseFilename", None) == target:
                break
        else:
            handler = create_timed_rotating_jsonl_handler(
                log_file=self.log_file,
                level=logging.INFO,
                formatter=formatter,
                backup_count=30,
                compress=True,
            )
            self.logger.addHandler(handler)
    
    def log_extraction_start(self, pdf_filename: str, pdf_path: Path) -> str:
        """
        Zaloguje začátek vytěžení.
        
        Args:
            pdf_filename: Název PDF souboru
            pdf_path: Cesta k PDF souboru
            
        Returns:
            ID vytěžení (timestamp-based)
        """
        extraction_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        self.logger.info(
            "extraction_start",
            extra={
                "extraction_id": extraction_id,
                "pdf_filename": pdf_filename,
                "pdf_path": str(pdf_path),
                "status": "started",
            },
        )
        
        return extraction_id
    
    def log_extraction_success(
        self,
        extraction_id: str,
        pdf_filename: str,
        usage_info: Dict[str, Any],
        extracted_records_count: int,
        processing_time: float,
        output_files: Dict[str, Optional[str]]
    ):
        """
        Zaloguje úspěšné dokončení vytěžení.
        
        Args:
            extraction_id: ID vytěžení
            pdf_filename: Název PDF souboru
            usage_info: Informace o použití tokenů a nákladech
            extracted_records_count: Počet extrahovaných záznamů
            processing_time: Čas zpracování v sekundách
            output_files: Slovník s cestami k výstupním souborům
        """
        # Převod z USD na CZK
        USD_TO_CZK = 23.5
        total_cost_czk = usage_info.get('total_cost_usd', 0) * USD_TO_CZK

        self.logger.info(
            "extraction_success",
            extra={
                "extraction_id": extraction_id,
                "pdf_filename": pdf_filename,
                "status": "success",
                "processing_time_seconds": round(processing_time, 2),
                "cost": {
                    "usd": round(usage_info.get("total_cost_usd", 0), 6),
                    "czk": round(total_cost_czk, 2),
                },
                "tokens": {
                    "input": usage_info.get("prompt_tokens", 0),
                    "output": usage_info.get("completion_tokens", 0),
                    "total": usage_info.get("total_tokens", 0),
                },
                "model": usage_info.get("model", "unknown"),
                "extracted_records_count": extracted_records_count,
                "output_files": output_files,
            },
        )
    
    def log_extraction_error(
        self,
        extraction_id: str,
        pdf_filename: str,
        error_message: str,
        error_type: Optional[str] = None,
        processing_time: Optional[float] = None
    ):
        """
        Zaloguje chybu při vytěžení.
        
        Args:
            extraction_id: ID vytěžení
            pdf_filename: Název PDF souboru
            error_message: Zpráva o chybě
            error_type: Typ chyby (volitelné)
            processing_time: Čas zpracování před chybou v sekundách (volitelné)
        """
        extra: Dict[str, Any] = {
            "extraction_id": extraction_id,
            "pdf_filename": pdf_filename,
            "status": "error",
            "error": {
                "message": str(error_message),
                "type": error_type or type(error_message).__name__,
            },
        }

        if processing_time is not None:
            extra["processing_time_seconds"] = round(processing_time, 2)

        self.logger.error("extraction_error", extra=extra)
    
    def log_session_summary(
        self,
        total_files: int,
        successful_extractions: int,
        failed_extractions: int,
        total_cost_usd: float,
        total_cost_czk: float,
        total_tokens: int,
        total_processing_time: float
    ):
        """
        Zaloguje shrnutí celé relace zpracování.
        
        Args:
            total_files: Celkový počet souborů
            successful_extractions: Počet úspěšných vytěžení
            failed_extractions: Počet neúspěšných vytěžení
            total_cost_usd: Celkové náklady v USD
            total_cost_czk: Celkové náklady v CZK
            total_tokens: Celkový počet tokenů
            total_processing_time: Celkový čas zpracování v sekundách
        """
        self.logger.info(
            "session_summary",
            extra={
                "status": "completed",
                "summary": {
                    "total_files": total_files,
                    "successful_extractions": successful_extractions,
                    "failed_extractions": failed_extractions,
                    "total_cost_usd": round(total_cost_usd, 6),
                    "total_cost_czk": round(total_cost_czk, 2),
                    "total_tokens": total_tokens,
                    "total_processing_time_seconds": round(total_processing_time, 2),
                },
            },
        )

    def _iter_log_files(self) -> Iterable[Path]:
        """Vrátí aktuální log + rotované soubory (včetně .gz)."""

        pattern = self.log_file.name + ".*"
        rotated = sorted(
            self.log_file.parent.glob(pattern),
            key=lambda p: p.stat().st_mtime,
        )

        for p in rotated:
            yield p
        yield self.log_file
    
    def get_extraction_history(self, limit: Optional[int] = None) -> list:
        """
        Načte historii vytěžení z log souboru.
        
        Args:
            limit: Maximální počet záznamů k načtení (None = všechny)
            
        Returns:
            Seznam slovníků s log záznamy
        """
        from collections import deque

        # Pokud není aktuální soubor, zkusíme aspoň rotované
        has_any = self.log_file.exists() or any(self.log_file.parent.glob(self.log_file.name + ".*"))
        if not has_any:
            return []

        buf: "deque[Dict[str, Any]]" = deque(maxlen=limit or 0)
        entries: List[Dict[str, Any]] = []

        try:
            for path in self._iter_log_files():
                if not path.exists():
                    continue

                opener = gzip.open if path.suffix == ".gz" else open
                with opener(path, "rt", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        if limit:
                            buf.append(obj)
                        else:
                            entries.append(obj)

            return list(buf) if limit else entries
        except Exception as e:
            self.logger.error(
                "failed_to_read_extraction_history",
                extra={"error": {"message": str(e), "type": type(e).__name__}},
            )
            return list(buf) if limit else entries

