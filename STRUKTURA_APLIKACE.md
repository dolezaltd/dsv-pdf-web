# Struktura a architektura aplikace `dsv-pdf-web`

Tento dokument popisuje aktuální strukturu repozitáře, hlavní běhové části (frontend/backend), sdílenou extrakční logiku a tok dat od nahrání PDF až po stažení výsledků.

> Poznámka ke stavu repozitáře: v `backend/` jsou soubory `app.py` a `pdf_service.py` aktuálně **prázdné (0 bajtů)**. Dokumentace níže proto popisuje jednak to, co v repu reálně existuje (např. `backend/routes.py`, `src/pdf_processor.py`), a jednak **očekávanou roli** chybějících souborů, aby bylo jasné, jak má aplikace držet pohromadě.

---

## Přehled aplikace

- **Účel**: Webová aplikace pro extrakci strukturovaných dat z logistických a celních PDF dokumentů pomocí **Google Gemini** (Vision + File API).
- **Výstupy**:
  - **CSV** s extrahovanými záznamy.
  - **MRN PDF**: samostatný PDF soubor složený z identifikovaných MRN stránek.
  - **Logy**: JSONL (záznamy o extrakcích, tokenech a ceně).
- **Hlavní části**:
  - **Frontend**: React + Vite (`frontend/`)
  - **Backend**: Flask API (`backend/`)
  - **Core extrakční logika**: Python moduly v `src/` (původně CLI/skript, využitelný i pro backend)

---

## Strom projektu (high-level)

```
dsv-pdf-web/
├── backend/                      # Flask API server (web)
│   ├── app.py                    # (aktuálně prázdné) očekávaný entrypoint Flasku
│   ├── routes.py                 # API endpointy: upload, download, results, health
│   ├── pdf_service.py            # (aktuálně prázdné) očekávaný wrapper pro `src/`
│   ├── config.py                 # konfigurace backendu, cesty, env
│   ├── uploads/                  # dočasné/uložené uploady (aktuálně prázdná složka)
│   ├── outputs/                  # výstupy po jobech: {job_id}/... (*.csv, *_MRN.pdf)
│   ├── logs/                     # logy backendu (např. extraction_log.jsonl)
│   └── requirements.txt          # závislosti backendu (Flask, CORS, dotenv)
├── frontend/                     # React aplikace (Vite)
│   ├── vite.config.js            # dev server + proxy na backend
│   ├── package.json              # React 18, Axios, Vite
│   └── src/
│       ├── App.jsx               # hlavní UI a orchestrátor uploadu
│       ├── services/api.js       # Axios klient pro /api
│       └── components/           # FileUpload, ResultsDisplay, DownloadButtons, ...
└── src/                          # core/CLI část (zpracování PDF + Gemini)
    ├── main.py                   # CLI runner: batch zpracování PDF ze složky
    ├── pdf_processor.py          # PDFProcessor: AI extrakce + MRN detekce + CSV/PDF výstupy
    ├── extract_prompt.py         # systémový prompt pro extrakci dat
    ├── logger.py                 # ExtractionLogger: JSONL logy + session summary
    ├── config.py                 # config (GOOGLE_API_KEY, AI_MODEL, INPUT/OUTPUT)
    ├── api_keys.py               # načítání API klíčů z .env / env var
    └── test-files/               # ukázková PDF pro testování
```

---

## Frontend (`frontend/`)

### Jak běží

- **Framework**: React 18 + Vite.
- **API komunikace**: Axios přes `frontend/src/services/api.js`.
- **Dev proxy**: `frontend/vite.config.js` přeposílá `/api` na backend.
  - Aktuální nastavení proxy: `target: http://localhost:5005`
  - Poznámka: README zmiňuje port `5000`, což je v konfliktu s `vite.config.js`. V praxi je důležité sjednotit porty nebo upravit proxy.

### Klíčové soubory

- **`frontend/src/App.jsx`**
  - Drží UI state: `selectedFile`, `status` (idle/uploading/processing/success/error), `progress`, `results`.
  - Po loadu volá **health check** (`healthCheck()`).
  - Upload dělá přes `uploadAndProcessPDF(file, onProgress)` a pak “simuluje” dokončení (timeout 1s) – reálné zpracování probíhá na backendu.

- **`frontend/src/services/api.js`**
  - `API_BASE_URL = '/api'`
  - `uploadAndProcessPDF`: `POST /upload` s `multipart/form-data`, `timeout: 300000` (5 minut).
  - `downloadFile`: otevře nové okno na `/api/download/{fileType}/{jobId}/{filename}`.
  - `getResults`: `GET /results/{jobId}`.
  - `healthCheck`: `GET /health`.

- **Komponenty (`frontend/src/components/`)**
  - **`FileUpload.jsx`**: drag&drop + file picker; validační kontrola `file.type === 'application/pdf'`.
  - **`ProcessingStatus.jsx`**: progress bar, texty stavů.
  - **`ResultsDisplay.jsx`**: dynamicky zobrazuje tabulku; sloupce jsou sjednocená množina klíčů ze všech záznamů.
  - **`Statistics.jsx`**: zobrazuje tokeny, cenu a čas; přepočet USD→CZK je fixně `23.5`.
  - **`DownloadButtons.jsx`**: vyrobí filename z cesty a volá `downloadFile(...)`.

---

## Backend (`backend/`)

### Co existuje a co chybí

- **Existuje**:
  - `routes.py`: kompletní definice API endpointů.
  - `config.py`: backend konfigurace (složky, limit, allowed extensions, env).
  - `outputs/`, `uploads/`, `logs/`: pracovní složky a ukázkové výstupy.
- **Chybí implementace**:
  - `backend/app.py` (0 bajtů): očekávaný Flask entrypoint, registrace blueprintu, CORS, port.
  - `backend/pdf_service.py` (0 bajtů): očekávaný wrapper, který:
    - vezme uploadovaný `FileStorage`,
    - uloží/streamuje PDF do dočasné cesty,
    - zavolá core logiku (typicky `src.PDFProcessor.process_pdf(...)`),
    - vrátí strukturu, kterou `routes.py` skládá do JSON response.

### API endpointy (`backend/routes.py`)

- **`GET /api/health`**
  - Vrací `status` a informaci, zda je nakonfigurovaný `GOOGLE_API_KEY`.

- **`POST /api/upload`**
  - Vstup: `multipart/form-data` s polem `file`.
  - Kontroly:
    - přítomnost `file`,
    - neprázdný název,
    - přípona v `ALLOWED_EXTENSIONS` (jen `pdf`),
    - velikost max `MAX_FILE_SIZE` (50 MB).
  - Vytváří:
    - `job_id` (UUID),
    - `extraction_id` ve tvaru `web_{unix_ts}_{uuid8}`.
  - Výstupy ukládá do: `backend/outputs/{job_id}/...`
  - Response obsahuje mimo jiné:
    - `extracted_data` (array záznamů),
    - `page_types` (mapa typu stránek → seznam čísel stránek),
    - `output_files.csv`, `output_files.mrn_pdf`,
    - download linky přes `/api/download/...`,
    - `usage_info` a `processing_time`.

- **`GET /api/download/<file_type>/<job_id>/<filename>`**
  - `file_type`: `csv` nebo `pdf`.
  - Bezpečnost:
    - `secure_filename(...)` pro `job_id` i `filename`,
    - kontrola, že file leží přímo v `backend/outputs/{job_id}/`.
  - Vrací soubor přes `send_file(...)` s `as_attachment=True`.

- **`GET /api/results/<job_id>`**
  - Prohledá `backend/outputs/{job_id}`:
    - CSV: `*.csv`
    - MRN PDF: `*_MRN.pdf`
  - Vrací seznam souborů + linky pro stažení.

### Backend konfigurace (`backend/config.py`)

- **Cesty**:
  - `UPLOAD_DIR = backend/uploads`
  - `OUTPUT_DIR = backend/outputs`
  - `LOGS_DIR = backend/logs`
  - složky se vytváří automaticky (`mkdir(..., exist_ok=True)`).
- **Omezení**:
  - `MAX_FILE_SIZE = 50 MB`
  - `ALLOWED_EXTENSIONS = {'pdf'}`
- **Env**:
  - `GOOGLE_API_KEY`
  - `AI_MODEL` (default `gemini-2.5-flash`)

> Pozor: `backend/config.py` hledá `.env` přes `project_root = Path(__file__).parent.parent.parent`. To typicky vyjde **o jednu úroveň výš** než kořen repozitáře. Pokud `.env` máte přímo v rootu projektu, je možné, že backend klíč nenačte (pokud to není kompenzováno jiným mechanismem).

---

## Core logika (`src/`) – extrakce a generování výstupů

### Hlavní třída: `PDFProcessor` (`src/pdf_processor.py`)

`PDFProcessor` je jádro, které:
- Volá **Google Gemini** (preferuje File API upload PDF → `generate_content([...prompt, uploaded_file])`).
- Fallback při chybě File API: extrahuje text přes `pdfplumber` a volá model na text.
- Čistí odpověď a snaží se robustně vyparsovat JSON array.
- Dělá **detekci typů stránek** v PDF:
  - Consignment Note: obsahuje text `consignment note`
  - MRN: obsahuje `mrn` + heuristika “dlouhý alfanumerický kód” (≥15 znaků)
- Generuje výstupy:
  - CSV z extrahovaných záznamů (`convert_to_csv`)
  - MRN PDF výřez (konkrétní stránky) pomocí `PyPDF2` (`save_extracted_pages`)

### Tok `process_pdf(...)`

1. **AI extrakce** (`extract_data_with_ai`)
2. **Detekce MRN a CN** (`extract_pages_by_type`)
3. **Přiřazení MRN stránek do `extracted_data`**
   - Pokud AI dodala `mrn_pages`, bere prioritu.
   - Jinak se doplní podle pořadí stránek (mezi CN stránkami) nebo fallback “rovnoměrné rozdělení”.
4. **Výstupní složka**: `output_dir/{pdf_stem}/`
5. **CSV**: `output_dir/{pdf_stem}/{pdf_stem}.csv`
6. **MRN PDF**: `output_dir/{pdf_stem}/{pdf_stem}_MRN.pdf` (pokud jsou MRN stránky)
7. **Return struktura**:
   - `extracted_data`, `page_types`, `output_folder`, `output_files`, `usage_info`, `processing_time`

### Prompt (`src/extract_prompt.py`)

Systémový prompt je zaměřený na:
- identifikaci Consignment Note a MRN stránek,
- extrakci CN čísla, Gross Weight, Packages, Volume,
- extrakci HS kódů (8 číslic) z MRN stránek,
- striktní výstup: **jen validní JSON array**.

### Logování (`src/logger.py`)

- `ExtractionLogger` zapisuje:
  - start extrakce (`log_extraction_start`)
  - úspěch (`log_extraction_success`) včetně tokenů a ceny
  - chybu (`log_extraction_error`)
  - shrnutí celé relace (`log_session_summary`)
- Formát: JSON Lines (`.jsonl`)

### Konfigurace core (`src/config.py`)

- `GOOGLE_API_KEY` se čte přes `api_keys.get_api_key("google", fallback_env=True)`.
- `AI_MODEL` default: `gemini-2.5-flash`.
- `INPUT_DIR` / `OUTPUT_DIR`: default `PROJECT_ROOT/input` a `PROJECT_ROOT/output` (odlišné od `backend/outputs`).

---

## Data flow end-to-end (web varianta)

1. Uživatel nahraje PDF ve frontendu (`FileUpload`).
2. Frontend volá `POST /api/upload` (Axios).
3. Backend:
   - validuje soubor (typ, velikost),
   - vytvoří `job_id`,
   - připraví `backend/outputs/{job_id}/`,
   - zavolá `PDFService.process_uploaded_file(...)` (aktuálně chybí implementace).
4. Core logika (očekávaně `src.PDFProcessor`) vygeneruje:
   - `.../{pdf_stem}.csv`
   - `.../{pdf_stem}_MRN.pdf` (pokud jsou MRN stránky)
   - usage/cost info.
5. Backend vrátí JSON s daty a linky pro stažení.
6. Frontend:
   - zobrazí tabulku výsledků,
   - zobrazí statistiky,
   - nabídne stažení CSV/MRN PDF přes `GET /api/download/...`.

---

## Výstupy na disku (backend)

Výstupy jsou organizované per job:

```
backend/outputs/{job_id}/
└── {pdf_stem}/
    ├── {pdf_stem}.csv
    └── {pdf_stem}_MRN.pdf
```

Backend endpoint pro download ale očekává soubor přímo v `backend/outputs/{job_id}/filename`. V praxi proto typicky backend vrací `output_files` jako absolutní cesty (z core) a současně přidává `csv_download`/`mrn_pdf_download` s cestou, která obsahuje pouze `filename` (bez podadresáře). To je detail, který je potřeba při implementaci `PDFService` sladit (buď ukládat výsledné soubory přímo pod `job_id`, nebo upravit download endpointy na podporu podadresáře).

---

## Známé nesrovnalosti / technické dluhy v aktuálním stavu

- **`backend/app.py` a `backend/pdf_service.py` jsou prázdné** → backend dle README nelze spustit bez doplnění.
- **Port mismatch**:
  - `frontend/vite.config.js` proxy cílí na `http://localhost:5005`
  - README zmiňuje backend na `http://localhost:5000`
- **Backend `.env` path**:
  - `backend/config.py` hledá `.env` nejspíš o úroveň výš než root repozitáře.
- **Závislosti backendu**:
  - `backend/requirements.txt` obsahuje jen Flask stack; pro reálné zpracování PDF bude potřeba také `google-generativeai`, `pdfplumber`, `PyPDF2` atd. (aktuálně jsou v `src/requirements.txt`).

---

## Doporučené “single source of truth” pro budoucí úpravy

- **Core extrakce**: držet v `src/` (např. `PDFProcessor` + `ExtractionLogger`).
- **Backend wrapper** (`backend/pdf_service.py`): jen adaptér mezi HTTP uploadem a core logikou:
  - file I/O (uložení PDF, validace, cleanup),
  - volání `PDFProcessor.process_pdf(...)`,
  - sjednocení výstupních cest pro download.
- **Frontend**: držet co nejjednodušší – pouze upload, polling (pokud se přidá async job queue), zobrazení.

---

## 🔴 IDENTIFIKOVANÉ KRITICKÉ PROBLÉMY (Prosinec 2024)

Při pokusu o spuštění aplikace byly zjištěny následující problémy:

### 1. KRITICKÝ: Prázdné implementace backendu

| Soubor | Stav | Dopad |
|--------|------|-------|
| `backend/app.py` | **Prázdný (0 bajtů)** | Backend nelze spustit |
| `backend/pdf_service.py` | **Prázdný (0 bajtů)** | Import v `routes.py` selže |

**Chyba při spuštění:**
```
ImportError: cannot import name 'PDFService' from 'pdf_service'
```

### 2. Chybějící závislosti v backend/requirements.txt

Backend `requirements.txt` obsahuje pouze:
- Flask, flask-cors, Werkzeug, python-dotenv

**Chybí** (jsou v `src/requirements.txt`):
- `google-generativeai>=0.3.0`
- `PyPDF2>=3.0.0`
- `pdfplumber>=0.10.0`

### 3. Port mismatch (nesoulad portů)

| Místo | Port |
|-------|------|
| `frontend/vite.config.js` proxy | **5005** |
| README.md dokumentace | **5000** |

### 4. Nesprávná cesta k `.env` souboru

V `backend/config.py`:
```python
project_root = Path(__file__).parent.parent.parent  # = ../../.. od backend/config.py
```
Výsledek: hledá `.env` **o jednu úroveň výš než root repozitáře**.

### 5. Nesoulad cest pro výstupní soubory

`PDFProcessor.process_pdf()` ukládá soubory do:
```
output_dir/{pdf_stem}/{pdf_stem}.csv
output_dir/{pdf_stem}/{pdf_stem}_MRN.pdf
```

Ale `routes.py` download endpoint očekává soubory v:
```
backend/outputs/{job_id}/filename
```

---

## 📋 NÁVRH REFAKTORINGU

### Fáze 1: Oprava kritických chyb (Priorita: VYSOKÁ)

#### 1.1 Implementace `backend/app.py`

Vytvořit Flask entrypoint:

```python
"""Flask aplikace pro PDF Extractor."""
from flask import Flask
from flask_cors import CORS
from routes import api

app = Flask(__name__)
CORS(app)

# Registrace API blueprintu
app.register_blueprint(api, url_prefix='/api')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)
```

#### 1.2 Implementace `backend/pdf_service.py`

Vytvořit wrapper nad `src/pdf_processor.py`:

```python
"""Service pro zpracování PDF souborů."""
import sys
import tempfile
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

# Přidání src do path pro import PDFProcessor
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from pdf_processor import PDFProcessor
from logger import ExtractionLogger

class PDFService:
    """Wrapper pro zpracování uploadovaných PDF souborů."""
    
    def __init__(self):
        self.logger = ExtractionLogger()
        self.processor = PDFProcessor(logger=self.logger)
    
    def process_uploaded_file(
        self, 
        file: FileStorage, 
        output_dir: Path, 
        extraction_id: str = None
    ) -> dict:
        """
        Zpracuje uploadovaný PDF soubor.
        
        Args:
            file: Werkzeug FileStorage objekt
            output_dir: Výstupní složka pro soubory
            extraction_id: ID extrakce pro logování
            
        Returns:
            Dict s výsledky zpracování
        """
        # Uložení uploadovaného souboru do dočasného adresáře
        filename = secure_filename(file.filename)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            file.save(tmp)
            tmp_path = Path(tmp.name)
        
        try:
            # Zpracování PDF pomocí core logiky
            result = self.processor.process_pdf(
                pdf_path=tmp_path,
                output_dir=output_dir,
                extraction_id=extraction_id
            )
            
            # Přesun výstupních souborů z podsložky přímo do output_dir
            # (pro kompatibilitu s download endpointem)
            output_folder = Path(result.get('output_folder', ''))
            if output_folder.exists() and output_folder != output_dir:
                for file_path in output_folder.iterdir():
                    dest = output_dir / file_path.name
                    file_path.rename(dest)
                    # Aktualizace cest v result
                    if 'csv' in str(file_path):
                        result['output_files']['csv'] = str(dest)
                    elif 'MRN' in str(file_path):
                        result['output_files']['mrn_pdf'] = str(dest)
                # Smazat prázdnou podsložku
                output_folder.rmdir()
            
            return result
            
        finally:
            # Vyčištění dočasného souboru
            tmp_path.unlink(missing_ok=True)
```

#### 1.3 Aktualizace `backend/requirements.txt`

Sjednotit závislosti:

```
Flask>=2.3.0
flask-cors>=4.0.0
Werkzeug>=2.3.0
python-dotenv>=1.0.0
google-generativeai>=0.3.0
PyPDF2>=3.0.0
pdfplumber>=0.10.0
```

#### 1.4 Oprava cesty k `.env` v `backend/config.py`

Změnit:
```python
project_root = Path(__file__).parent.parent.parent
```

Na:
```python
project_root = Path(__file__).parent.parent  # = kořen repozitáře
```

### Fáze 2: Sjednocení konfigurace (Priorita: STŘEDNÍ)

#### 2.1 Sjednocení portů

Rozhodnout se pro jeden port (doporučuji 5005) a aktualizovat:
- [x] `frontend/vite.config.js` → `target: 'http://localhost:5005'` ✓ (už je)
- [ ] `README.md` → změnit port z 5000 na 5005

#### 2.2 Centralizace konfigurace

Zvážit vytvoření jednoho konfiguračního modulu v rootu projektu, který načítají jak `src/` tak `backend/`.

### Fáze 3: Optimalizace (Priorita: NÍZKÁ)

#### 3.1 Asynchronní zpracování

Pro větší PDF soubory zvážit:
- Implementaci job queue (Celery/Redis nebo jednodušší SQLite-based)
- Polling endpoint pro frontend místo synchronního čekání

#### 3.2 Správa souborů

- Implementovat automatický cleanup starých jobů (např. po 24h)
- Zvážit limit na celkový prostor v `outputs/`

#### 3.3 Error handling

- Přidat retry logiku pro Gemini API volání
- Implementovat strukturované chybové odpovědi pro frontend

---

## 🚀 RYCHLÝ START PO REFAKTORINGU

Po implementaci oprav by mělo fungovat:

```bash
# 1. Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
python app.py

# 2. Frontend (nový terminál)
cd frontend
npm install
npm run dev

# 3. Otevřít http://localhost:3000
```

---

## CHECKLIST PRO OPRAVU

- [ ] Implementovat `backend/app.py`
- [ ] Implementovat `backend/pdf_service.py`
- [ ] Aktualizovat `backend/requirements.txt`
- [ ] Opravit cestu k `.env` v `backend/config.py`
- [ ] Aktualizovat port v `README.md`
- [ ] Vytvořit `.env` v rootu projektu s `GOOGLE_API_KEY`
- [ ] Otestovat end-to-end flow

