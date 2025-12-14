"""Service pro zpracování uploadovaných PDF souborů.

Tento modul je adaptér mezi Flask uploadem (Werkzeug `FileStorage`) a core logikou v `src/`.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from src.logger import ExtractionLogger
from src.pdf_processor import PDFProcessor


class PDFService:
    """Wrapper pro zpracování uploadovaných PDF souborů."""

    def __init__(self, log_file: Optional[Path] = None):
        self.logger = ExtractionLogger(log_file=log_file)
        self.processor = PDFProcessor(logger=self.logger)

    def process_uploaded_file(
        self,
        file: FileStorage,
        output_dir: Path,
        extraction_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Zpracuje uploadovaný PDF soubor a uloží výstupy do `output_dir`.

        Poznámka:
        `PDFProcessor.process_pdf()` ukládá výsledky do podsložky `output_dir/{pdf_stem}/...`,
        ale download endpoint v `backend/routes.py` očekává soubory přímo v `output_dir`.
        Proto po zpracování výstupy přesuneme o úroveň výš.
        """

        if not file or not file.filename:
            raise ValueError("Chybí nahraný soubor")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        original_filename = secure_filename(file.filename)

        # Uložíme upload do dočasného souboru (PDFProcessor očekává Path)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            file.save(tmp)

        try:
            result = self.processor.process_pdf(
                pdf_path=tmp_path,
                output_dir=output_dir,
                extraction_id=extraction_id,
            )

            # Přesun výstupů z podsložky `{output_dir}/{pdf_stem}/` přímo do `{output_dir}/`
            output_folder = Path(result.get("output_folder") or "")
            if output_folder.exists() and output_folder.is_dir():
                moved_paths: Dict[str, Optional[str]] = {}
                for p in output_folder.iterdir():
                    if not p.is_file():
                        continue
                    dest = output_dir / p.name
                    # Pokud soubor už existuje, přepíšeme ho deterministicky
                    if dest.exists():
                        dest.unlink()
                    p.rename(dest)
                    if dest.suffix.lower() == ".csv":
                        moved_paths["csv"] = str(dest)
                    elif dest.suffix.lower() == ".pdf" and dest.name.endswith("_MRN.pdf"):
                        moved_paths["mrn_pdf"] = str(dest)

                # Pokus o smazání prázdné podsložky
                try:
                    output_folder.rmdir()
                except OSError:
                    # Pokud není prázdná (nečekané), necháme ji být.
                    pass

                # Aktualizace result struktury tak, aby seděla s download endpointem
                result["output_folder"] = str(output_dir)
                result.setdefault("output_files", {})
                for k in ("csv", "mrn_pdf"):
                    if k in moved_paths:
                        result["output_files"][k] = moved_paths[k]

            # Uložíme i původní filename pro případné budoucí použití
            result.setdefault("input_filename", original_filename)

            return result
        finally:
            tmp_path.unlink(missing_ok=True)

