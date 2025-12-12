"""Modul pro logování průběhu vytěžení."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from .config import PROJECT_ROOT


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
        
        # Nastavení Python logging pro strukturované logy
        self.logger = logging.getLogger("extraction_logger")
        self.logger.setLevel(logging.INFO)
        
        # Přidání file handleru pokud ještě není přidán
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file, encoding='utf-8')
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
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
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "extraction_id": extraction_id,
            "event": "extraction_start",
            "pdf_filename": pdf_filename,
            "pdf_path": str(pdf_path),
            "status": "started"
        }
        
        self._write_jsonl_entry(log_entry)
        self.logger.info(f"Začátek vytěžení: {pdf_filename} (ID: {extraction_id})")
        
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
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "extraction_id": extraction_id,
            "event": "extraction_success",
            "pdf_filename": pdf_filename,
            "status": "success",
            "processing_time_seconds": round(processing_time, 2),
            "cost": {
                "usd": round(usage_info.get('total_cost_usd', 0), 6),
                "czk": round(total_cost_czk, 2)
            },
            "tokens": {
                "input": usage_info.get('prompt_tokens', 0),
                "output": usage_info.get('completion_tokens', 0),
                "total": usage_info.get('total_tokens', 0)
            },
            "model": usage_info.get('model', 'unknown'),
            "extracted_records_count": extracted_records_count,
            "output_files": output_files
        }
        
        self._write_jsonl_entry(log_entry)
        self.logger.info(
            f"Úspěšné vytěžení: {pdf_filename} | "
            f"Tokeny: {usage_info.get('total_tokens', 0):,} | "
            f"Cena: {total_cost_czk:.2f} Kč | "
            f"Záznamů: {extracted_records_count}"
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
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "extraction_id": extraction_id,
            "event": "extraction_error",
            "pdf_filename": pdf_filename,
            "status": "error",
            "error": {
                "message": str(error_message),
                "type": error_type or type(error_message).__name__
            }
        }
        
        if processing_time is not None:
            log_entry["processing_time_seconds"] = round(processing_time, 2)
        
        self._write_jsonl_entry(log_entry)
        self.logger.error(f"Chyba při vytěžení: {pdf_filename} | {error_message}")
    
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
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "session_summary",
            "status": "completed",
            "summary": {
                "total_files": total_files,
                "successful_extractions": successful_extractions,
                "failed_extractions": failed_extractions,
                "total_cost_usd": round(total_cost_usd, 6),
                "total_cost_czk": round(total_cost_czk, 2),
                "total_tokens": total_tokens,
                "total_processing_time_seconds": round(total_processing_time, 2)
            }
        }
        
        self._write_jsonl_entry(log_entry)
        self.logger.info(
            f"Shrnutí relace: {successful_extractions}/{total_files} úspěšných | "
            f"Celková cena: {total_cost_czk:.2f} Kč | "
            f"Celkové tokeny: {total_tokens:,}"
        )
    
    def _write_jsonl_entry(self, entry: Dict[str, Any]):
        """
        Zapíše záznam do JSONL souboru (JSON Lines format).
        
        Args:
            entry: Slovník s daty k zapsání
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            # Fallback na standardní Python logging pokud selže zápis
            self.logger.error(f"Nepodařilo se zapsat log entry: {e}")
    
    def get_extraction_history(self, limit: Optional[int] = None) -> list:
        """
        Načte historii vytěžení z log souboru.
        
        Args:
            limit: Maximální počet záznamů k načtení (None = všechny)
            
        Returns:
            Seznam slovníků s log záznamy
        """
        if not self.log_file.exists():
            return []
        
        entries = []
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if limit:
                    lines = lines[-limit:]
                
                for line in lines:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            self.logger.error(f"Nepodařilo se načíst historii: {e}")
        
        return entries

