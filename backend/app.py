from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import shutil
import os
import sys
from pathlib import Path
import logging
import traceback

# Přidání kořenového adresáře do sys.path, aby šlo importovat ze src
# Předpokládáme, že backend/app.py se spouští z kořenového adresáře projektu
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

try:
    from src.pdf_processor import PDFProcessor
    from src.logger import ExtractionLogger
    from src.config import PROJECT_ROOT, OUTPUT_DIR
except ImportError as e:
    print(f"Chyba importu: {e}")
    # Fallback pro případ, že se spouští jinak
    sys.path.append(str(Path.cwd()))
    try:
        from src.pdf_processor import PDFProcessor
        from src.logger import ExtractionLogger
        from src.config import PROJECT_ROOT, OUTPUT_DIR
    except ImportError:
        print("Nepodařilo se importovat moduly ze src.")
        raise

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

# Nastavení logování
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            
        logger.info(f"File saved to {temp_file_path}")

        # Zpracování PDF
        # Použijeme existující output adresář z configu
        result = processor.process_pdf(temp_file_path, OUTPUT_DIR)
        
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
            "processing_time": result.get("processing_time")
        }
        
        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
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
