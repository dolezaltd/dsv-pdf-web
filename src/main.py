#!/usr/bin/env python3
"""Hlavní skript pro zpracování PDF souborů."""
import argparse
import sys
import time
from pathlib import Path
import pdfplumber

# Umožní spouštění jak přes `python3 -m src.main`, tak i `python3 src/main.py`
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pdf_processor import PDFProcessor
from src.config import INPUT_DIR, OUTPUT_DIR, PROJECT_ROOT
from src.logger import ExtractionLogger


def main():
    """Hlavní funkce programu."""
    parser = argparse.ArgumentParser(
        description="Extrahuje data z PDF souborů pomocí AI modelu"
    )
    parser.add_argument(
        "-i", "--input-dir",
        type=str,
        default=str(INPUT_DIR),
        help=f"Složka s PDF soubory (výchozí: {INPUT_DIR})"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=str(OUTPUT_DIR),
        help=f"Složka pro výstupní soubory (výchozí: {OUTPUT_DIR})"
    )
    
    args = parser.parse_args()
    
    # Určení vstupní a výstupní složky
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    # Kontrola existence vstupní složky
    if not input_dir.exists():
        print(f"Chyba: Vstupní složka {input_dir} neexistuje!", file=sys.stderr)
        sys.exit(1)
    
    if not input_dir.is_dir():
        print(f"Chyba: {input_dir} není složka!", file=sys.stderr)
        sys.exit(1)
    
    # Vytvoření výstupní složky pokud neexistuje
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Seznam všech PDF souborů ve vstupní složce (podporuje .pdf i .PDF)
    pdf_files = list(input_dir.glob("*.pdf")) + list(input_dir.glob("*.PDF"))
    
    if not pdf_files:
        print(f"Info: Ve složce {input_dir} nejsou žádné PDF soubory k zpracování.")
        sys.exit(0)
    
    # Zpracování souborů
    print(f"Našel jsem {len(pdf_files)} PDF soubor(ů) ke zpracování.\n")
    
    # Inicializace loggeru
    logger = ExtractionLogger(log_file=PROJECT_ROOT / "logs" / "extraction_log.jsonl")
    
    try:
        processor = PDFProcessor(logger=logger)
    except ValueError as e:
        print(f"Chyba inicializace: {e}", file=sys.stderr)
        sys.exit(1)
    
    results = []
    processed_count = 0
    error_count = 0
    total_cost_usd = 0.0
    total_tokens = 0
    session_start_time = time.time()
    
    for pdf_file in pdf_files:
        extraction_id = None
        extraction_start_time = time.time()
        
        try:
            # Logování začátku vytěžení
            extraction_id = logger.log_extraction_start(pdf_file.name, pdf_file)
            
            print(f"\n{'='*60}")
            print(f"Zpracovávám: {pdf_file.name}")
            print(f"{'='*60}")
            
            # Kontrola počtu stránek (max 150)
            with pdfplumber.open(pdf_file) as pdf:
                page_count = len(pdf.pages)
                if page_count > 150:
                    print(f"⚠ Varování: PDF má {page_count} stránek, což překračuje limit 150 stránek.")
                    print(f"  Soubor bude zpracován, ale může dojít k problémům.\n")
            
            result = processor.process_pdf(pdf_file, output_dir, extraction_id=extraction_id)
            results.append(result)
            
            # Aktualizace statistik
            if result.get('usage_info'):
                usage_info = result['usage_info']
                total_cost_usd += usage_info.get('total_cost_usd', 0)
                total_tokens += usage_info.get('total_tokens', 0)
            
            print(f"✓ Hotovo: {pdf_file.name} (soubor zachován pro testování)\n")
            
            processed_count += 1
            
        except Exception as e:
            processing_time = time.time() - extraction_start_time
            logger.log_extraction_error(
                extraction_id=extraction_id or "unknown",
                pdf_filename=pdf_file.name,
                error_message=str(e),
                error_type=type(e).__name__,
                processing_time=processing_time
            )
            print(f"✗ Chyba při zpracování {pdf_file.name}: {e}\n", file=sys.stderr)
            error_count += 1
            continue
    
    # Shrnutí
    total_processing_time = time.time() - session_start_time
    total_cost_czk = total_cost_usd * 23.5  # Převod USD na CZK
    
    print("\n" + "="*60)
    print(f"Zpracováno úspěšně: {processed_count} soubor(ů)")
    if error_count > 0:
        print(f"Chyb: {error_count}")
    print(f"Celková cena: {total_cost_czk:.2f} Kč ({total_cost_usd:.6f} USD)")
    print(f"Celkové tokeny: {total_tokens:,}")
    print(f"Celkový čas zpracování: {total_processing_time:.2f} sekund")
    print(f"Výstupní složka: {output_dir}")
    print("="*60)
    
    # Logování shrnutí relace
    logger.log_session_summary(
        total_files=len(pdf_files),
        successful_extractions=processed_count,
        failed_extractions=error_count,
        total_cost_usd=total_cost_usd,
        total_cost_czk=total_cost_czk,
        total_tokens=total_tokens,
        total_processing_time=total_processing_time
    )


if __name__ == "__main__":
    main()

