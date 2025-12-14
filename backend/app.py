from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import shutil
import os
import sys
import time
import uuid
from pathlib import Path
import logging
import traceback
import uvicorn
from starlette.requests import Request

# Přidání kořenového adresáře do sys.path, aby šlo importovat ze src
# Předpokládáme, že backend/app.py se spouští z kořenového adresáře projektu
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

try:
    from src.pdf_processor import PDFProcessor
    from src.logger import ExtractionLogger
    from src.config import PROJECT_ROOT, OUTPUT_DIR
    from src.logging_setup import setup_logging, set_request_context, clear_request_context
except ImportError as e:
    print(f"Chyba importu: {e}")
    # Fallback pro případ, že se spouští jinak
    sys.path.append(str(Path.cwd()))
    try:
        from src.pdf_processor import PDFProcessor
        from src.logger import ExtractionLogger
        from src.config import PROJECT_ROOT, OUTPUT_DIR
        from src.logging_setup import setup_logging, set_request_context, clear_request_context
    except ImportError:
        print("Nepodařilo se importovat moduly ze src.")
        raise

# Nastavení strukturovaného logování (JSONL do logs/ s rotací/retencí)
setup_logging(service="dsv-pdf-web")

app = FastAPI(title="DSV PDF Processor API")

# Konfigurace CORS
# V produkci na Renderu byste měli přidat URL vašeho frontendu
origins = [
    "http://localhost:5173",  # Vite default
    "http://localhost:3000",
    "https://dsv-pdf-web.vercel.app", # Předpokládaná URL na Vercelu (upravte podle skutečnosti)
    "*" # Pro začátek povolíme vše, abychom předešli problémům
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)
access_logger = logging.getLogger("dsv.access")


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Middleware pro request_id korelaci + access log s latencí."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    xff = request.headers.get("x-forwarded-for", "")
    client_ip = (xff.split(",")[0].strip() if xff else "") or (request.client.host if request.client else None)

    http_meta = {"method": request.method, "path": request.url.path}
    client_meta = {"ip": client_ip}

    set_request_context(request_id=request_id, http=http_meta, client=client_meta)
    start = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as e:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        # Aplikační error log s tracebackem
        logger.exception("unhandled_exception")
        # Access log i pro 500 (bez body)
        access_logger.info(
            "http_access",
            extra={
                "request_id": request_id,
                "http": {**http_meta, "status_code": 500, "duration_ms": duration_ms},
                "client": client_meta,
                "error": {"message": str(e), "type": type(e).__name__},
            },
        )
        clear_request_context()
        raise
    else:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        access_logger.info(
            "http_access",
            extra={
                "request_id": request_id,
                "http": {**http_meta, "status_code": response.status_code, "duration_ms": duration_ms},
                "client": client_meta,
            },
        )
        clear_request_context()
        return response

# Inicializace procesoru
try:
    extraction_logger = ExtractionLogger(log_file=PROJECT_ROOT / "logs" / "extraction_log_api.jsonl")
    processor = PDFProcessor(logger=extraction_logger)
except Exception as e:
    logger.error(f"Failed to initialize PDFProcessor: {e}")
    processor = None

@app.get("/")
async def root():
    return {"message": "DSV PDF Processor API is running"}

@app.post("/process-pdf/")
async def process_pdf(file: UploadFile = File(...)):
    if not processor:
        raise HTTPException(status_code=500, detail="PDF Processor not initialized properly")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Korelační ID pro tuto extrakci (důležité pro diagnostiku Gemini)
    extraction_id = f"api_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    try:
        # Vytvoření dočasného souboru
        temp_dir = root_dir / "temp_uploads"
        temp_dir.mkdir(exist_ok=True)
        temp_file_path = temp_dir / file.filename
        
        # Optimalizace: Použití streamu s pevnou velikostí chunků (1MB)
        # To zabrání načtení celého souboru do RAM při ukládání
        with open(temp_file_path, "wb") as buffer:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                buffer.write(content)
            
        logger.info("pdf_saved", extra={"extraction_id": extraction_id, "pdf_filename": file.filename})

        # Zpracování PDF
        # Použijeme existující output adresář z configu
        result = processor.process_pdf(temp_file_path, OUTPUT_DIR, extraction_id=extraction_id)
        
        # Explicitní úklid paměti po zpracování
        import gc
        gc.collect()
        
        # Úklid dočasného souboru (šetří místo na disku)
        try:
            os.remove(temp_file_path)
        except Exception as e:
            logger.warning(f"Could not remove temp file: {e}")
        
        # Obohacení výsledku o cesty ke stažení (relativní URL)
        output_folder_name = temp_file_path.stem
        
        # Konstrukce odpovědi
        response_data = {
            "status": "success",
            "filename": file.filename,
            "job_id": output_folder_name, # Frontend očekává job_id
            "extracted_data": result.get("extracted_data", []),
            "output_files": result.get("output_files", {}),
            "usage_info": result.get("usage_info"),
            "processing_time": result.get("processing_time"),
            "extraction_id": extraction_id,
        }
        
        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(
            "pdf_processing_failed",
            extra={
                "extraction_id": extraction_id,
                "pdf_filename": getattr(file, "filename", None),
                "error": {"message": str(e), "type": type(e).__name__},
            },
        )
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.get("/download/{download_id}/{file_type}")
async def download_result(download_id: str, file_type: str):
    """
    Endpoint pro stažení výsledných souborů.
    file_type: 'csv' nebo 'mrn_pdf'
    """
    target_dir = OUTPUT_DIR / download_id
    
    if not target_dir.exists():
        raise HTTPException(status_code=404, detail="Result not found")
        
    if file_type == 'csv':
        file_path = target_dir / f"{download_id}.csv"
        media_type = "text/csv"
        filename = f"{download_id}.csv"
    elif file_type == 'mrn_pdf':
        file_path = target_dir / f"{download_id}_MRN.pdf"
        media_type = "application/pdf"
        filename = f"{download_id}_MRN.pdf"
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")
        
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
        
    return FileResponse(path=file_path, media_type=media_type, filename=filename)

if __name__ == "__main__":
    # Pro lokální testování
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)

