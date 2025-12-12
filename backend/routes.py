"""API routes pro Flask aplikaci."""
import os
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import uuid
import time

from .config import (
    UPLOAD_DIR, 
    OUTPUT_DIR, 
    MAX_FILE_SIZE, 
    ALLOWED_EXTENSIONS,
    GOOGLE_API_KEY
)
from .pdf_service import PDFService

api = Blueprint('api', __name__)

# Inicializace PDF service
pdf_service = None

def init_pdf_service():
    """Inicializuje PDF service."""
    global pdf_service
    if pdf_service is None:
        pdf_service = PDFService()

def allowed_file(filename: str) -> bool:
    """Zkontroluje, zda je soubor povoleného typu."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'google_api_key_configured': GOOGLE_API_KEY is not None
    })

@api.route('/upload', methods=['POST'])
def upload_file():
    """
    Nahrání PDF souboru a jeho zpracování.
    
    Returns:
        JSON s výsledky zpracování nebo chybovou zprávou
    """
    init_pdf_service()
    
    # Kontrola přítomnosti souboru
    if 'file' not in request.files:
        return jsonify({'error': 'Žádný soubor nebyl nahrán'}), 400
    
    file = request.files['file']
    
    # Kontrola, zda byl soubor vybrán
    if file.filename == '':
        return jsonify({'error': 'Žádný soubor nebyl vybrán'}), 400
    
    # Kontrola typu souboru
    if not allowed_file(file.filename):
        return jsonify({
            'error': f'Nepovolený typ souboru. Povolené typy: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400
    
    # Kontrola velikosti souboru
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return jsonify({
            'error': f'Soubor je příliš velký. Maximální velikost: {MAX_FILE_SIZE / 1024 / 1024:.0f} MB'
        }), 400
    
    try:
        # Vytvoření jedinečného ID pro tuto extrakci
        job_id = str(uuid.uuid4())
        extraction_id = f"web_{int(time.time())}_{job_id[:8]}"
        
        # Vytvoření výstupní složky pro tento job
        job_output_dir = OUTPUT_DIR / job_id
        job_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Zpracování souboru
        result = pdf_service.process_uploaded_file(
            file,
            job_output_dir,
            extraction_id=extraction_id
        )
        
        # Příprava odpovědi
        response_data = {
            'job_id': job_id,
            'extraction_id': extraction_id,
            'status': 'success',
            'filename': secure_filename(file.filename),
            'extracted_data': result.get('extracted_data', []),
            'extracted_records_count': len(result.get('extracted_data', [])),
            'page_types': result.get('page_types', {}),
            'output_files': {
                'csv': result.get('output_files', {}).get('csv'),
                'mrn_pdf': result.get('output_files', {}).get('mrn_pdf')
            },
            'usage_info': result.get('usage_info', {}),
            'processing_time': result.get('processing_time', 0)
        }
        
        # Přidání relativních cest pro stažení
        if response_data['output_files']['csv']:
            csv_path = Path(response_data['output_files']['csv'])
            response_data['output_files']['csv_download'] = f'/api/download/csv/{job_id}/{csv_path.name}'
        
        if response_data['output_files']['mrn_pdf']:
            mrn_path = Path(response_data['output_files']['mrn_pdf'])
            response_data['output_files']['mrn_pdf_download'] = f'/api/download/pdf/{job_id}/{mrn_path.name}'
        
        return jsonify(response_data), 200
        
    except ValueError as e:
        return jsonify({'error': f'Chyba konfigurace: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Chyba při zpracování: {str(e)}'}), 500

@api.route('/download/<file_type>/<job_id>/<filename>', methods=['GET'])
def download_file(file_type: str, job_id: str, filename: str):
    """
    Stažení výsledného souboru (CSV nebo PDF).
    
    Args:
        file_type: Typ souboru ('csv' nebo 'pdf')
        job_id: ID jobu
        filename: Název souboru
    """
    # Bezpečnostní kontrola
    filename = secure_filename(filename)
    job_id = secure_filename(job_id)
    
    if file_type not in ['csv', 'pdf']:
        return jsonify({'error': 'Neplatný typ souboru'}), 400
    
    file_path = OUTPUT_DIR / job_id / filename
    
    if not file_path.exists():
        return jsonify({'error': 'Soubor nebyl nalezen'}), 404
    
    # Kontrola, zda soubor patří k danému job_id
    if file_path.parent != OUTPUT_DIR / job_id:
        return jsonify({'error': 'Neplatná cesta k souboru'}), 403
    
    mimetype = 'text/csv' if file_type == 'csv' else 'application/pdf'
    
    return send_file(
        str(file_path),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )

@api.route('/results/<job_id>', methods=['GET'])
def get_results(job_id: str):
    """
    Získání výsledků zpracování podle job_id.
    
    Args:
        job_id: ID jobu
    """
    job_id = secure_filename(job_id)
    job_output_dir = OUTPUT_DIR / job_id
    
    if not job_output_dir.exists():
        return jsonify({'error': 'Job nebyl nalezen'}), 404
    
    # Hledání CSV souboru
    csv_files = list(job_output_dir.glob('*.csv'))
    pdf_files = list(job_output_dir.glob('*_MRN.pdf'))
    
    results = {
        'job_id': job_id,
        'csv_files': [f.name for f in csv_files],
        'pdf_files': [f.name for f in pdf_files],
        'download_links': {}
    }
    
    if csv_files:
        results['download_links']['csv'] = f'/api/download/csv/{job_id}/{csv_files[0].name}'
    
    if pdf_files:
        results['download_links']['mrn_pdf'] = f'/api/download/pdf/{job_id}/{pdf_files[0].name}'
    
    return jsonify(results), 200

