"""Core logika pro zpracování PDF (balíček).

Poznámka: Historicky byly moduly ve `src/` používány jako „flat“ skripty.
Zabalujeme je do balíčku kvůli jednoznačným importům (aby se nepletly s `backend/config.py`).
"""

from .pdf_processor import PDFProcessor  # noqa: F401
from .logger import ExtractionLogger  # noqa: F401

