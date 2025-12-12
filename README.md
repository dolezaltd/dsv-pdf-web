# PDF Extractor - Webová aplikace

Webová aplikace pro extrakci dat z PDF dokumentů pomocí AI modelu Google Gemini. Aplikace převádí funkcionalitu původního PDF extractoru do moderního webového prostředí.

## Struktura projektu

```
web-app/
├── backend/              # Flask API server
│   ├── app.py           # Hlavní Flask aplikace
│   ├── routes.py        # API endpointy
│   ├── pdf_service.py   # Wrapper pro PDFProcessor
│   ├── config.py        # Konfigurace backendu
│   └── requirements.txt # Python závislosti
├── frontend/            # React aplikace
│   ├── src/
│   │   ├── components/  # React komponenty
│   │   ├── services/    # API služby
│   │   └── App.jsx      # Hlavní komponenta
│   ├── package.json
│   └── vite.config.js
└── README.md            # Tento soubor
```

## Požadavky

- Python 3.8 nebo novější
- Node.js 16 nebo novější
- Google API klíč pro Gemini (stejný jako v původním projektu)
- Všechny závislosti z původního projektu (viz `requirements.txt` v kořenové složce)

## Instalace

### Backend

1. Přejděte do složky backend:
```bash
cd web-app/backend
```

2. Vytvořte virtuální prostředí (doporučeno):
```bash
python -m venv venv
source venv/bin/activate  # Na Windows: venv\Scripts\activate
```

3. Nainstalujte závislosti:
```bash
pip install -r requirements.txt
```

4. Ujistěte se, že máte nastavený `GOOGLE_API_KEY` v `.env` souboru v kořenové složce projektu (stejný jako pro původní skript).

### Frontend

1. Přejděte do složky frontend:
```bash
cd web-app/frontend
```

2. Nainstalujte závislosti:
```bash
npm install
```

## Spuštění

### Backend

1. Aktivujte virtuální prostředí (pokud používáte):
```bash
cd web-app/backend
source venv/bin/activate  # Na Windows: venv\Scripts\activate
```

2. Spusťte Flask server:
```bash
python app.py
```

Backend poběží na `http://localhost:5000`

### Frontend

1. V novém terminálu přejděte do složky frontend:
```bash
cd web-app/frontend
```

2. Spusťte vývojový server:
```bash
npm run dev
```

Frontend poběží na `http://localhost:3000`

## Použití

1. Otevřete prohlížeč a přejděte na `http://localhost:3000`
2. Nahrajte PDF soubor pomocí drag & drop nebo kliknutím na oblast pro nahrávání
3. Počkejte na dokončení zpracování (může trvat několik minut pro velké soubory)
4. Prohlédněte si extrahovaná data v tabulce
5. Stáhněte výsledky (CSV soubor s daty a/nebo MRN PDF stránky)

## API Endpointy

### `POST /api/upload`
Nahrání a zpracování PDF souboru.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (PDF soubor)

**Response:**
```json
{
  "job_id": "uuid",
  "extraction_id": "web_timestamp_uuid",
  "status": "success",
  "filename": "document.pdf",
  "extracted_data": [...],
  "extracted_records_count": 5,
  "page_types": {...},
  "output_files": {
    "csv": "/path/to/file.csv",
    "mrn_pdf": "/path/to/file_MRN.pdf",
    "csv_download": "/api/download/csv/job_id/filename.csv",
    "mrn_pdf_download": "/api/download/pdf/job_id/filename_MRN.pdf"
  },
  "usage_info": {...},
  "processing_time": 45.2
}
```

### `GET /api/download/<file_type>/<job_id>/<filename>`
Stažení výsledného souboru.

- `file_type`: `csv` nebo `pdf`
- `job_id`: ID jobu z upload odpovědi
- `filename`: Název souboru

### `GET /api/results/<job_id>`
Získání informací o výsledcích zpracování.

### `GET /api/health`
Health check endpoint pro kontrolu stavu API.

## Funkce

- ✅ Drag & drop nahrávání PDF souborů
- ✅ Real-time zobrazení průběhu zpracování
- ✅ Extrakce dat pomocí Google Gemini AI
- ✅ Identifikace typů stránek (Consignment Note, MRN)
- ✅ Zobrazení extrahovaných dat v tabulce
- ✅ Stažení CSV souboru s daty
- ✅ Stažení extrahovaných MRN PDF stránek
- ✅ Zobrazení statistik (náklady, tokeny, čas zpracování)
- ✅ Responzivní design pro mobilní zařízení

## Technologie

- **Backend:** Flask, Flask-CORS
- **Frontend:** React, Vite, Axios
- **AI:** Google Gemini (stejný jako v původním projektu)

## Bezpečnost

- Validace nahraných souborů (pouze PDF)
- Omezení velikosti souboru (50 MB)
- Sanitizace názvů souborů
- CORS konfigurace pro produkci

## Řešení problémů

### Backend se nespustí
- Zkontrolujte, zda máte nainstalované všechny závislosti z `requirements.txt`
- Ujistěte se, že máte nastavený `GOOGLE_API_KEY` v `.env` souboru
- Zkontrolujte, zda port 5000 není obsazený jinou aplikací

### Frontend se nepřipojí k backendu
- Ujistěte se, že backend běží na `http://localhost:5000`
- Zkontrolujte CORS konfiguraci v `backend/app.py`
- Zkontrolujte proxy konfiguraci v `frontend/vite.config.js`

### Chyba při zpracování PDF
- Zkontrolujte, zda máte platný Google API klíč
- Ověřte, že PDF soubor není poškozený
- Zkontrolujte logy v `backend/logs/`

## Poznámky

- Aplikace používá stejnou logiku zpracování jako původní skript
- Výstupní soubory jsou ukládány do `backend/outputs/`
- Logy jsou ukládány do `backend/logs/`
- Pro produkční nasazení je doporučeno použít WSGI server (např. Gunicorn) a upravit CORS konfiguraci

