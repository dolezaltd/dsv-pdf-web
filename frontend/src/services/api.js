import axios from 'axios';

// Načtení URL backendu z environment proměnných nebo fallback na localhost
// V Vite se environment proměnné musí jmenovat VITE_...
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

console.log('Using API Base URL:', API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minut pro zpracování velkých souborů
});

/**
 * Nahrání a zpracování PDF souboru
 * @param {File} file - PDF soubor k nahrání
 * @param {Function} onProgress - Callback pro sledování průběhu nahrávání
 * @returns {Promise} Promise s výsledky zpracování
 */
export const uploadAndProcessPDF = async (file, onProgress = null) => {
  const formData = new FormData();
  formData.append('file', file);

  const config = {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        onProgress(percentCompleted);
      }
    },
  };

  try {
    // Endpoint v backend/app.py je definován jako /process-pdf/
    const response = await api.post('/process-pdf/', formData, config);
    return response.data;
  } catch (error) {
    console.error('Upload error:', error);
    if (error.response) {
      throw new Error(error.response.data.detail || error.response.data.error || 'Chyba při nahrávání souboru');
    } else if (error.request) {
      throw new Error('Nelze se připojit k serveru. Zkontrolujte, zda běží backend na ' + API_BASE_URL);
    } else {
      throw new Error(error.message || 'Nastala neočekávaná chyba');
    }
  }
};

/**
 * Stažení výsledného souboru
 * @param {string} fileType - Typ souboru ('csv' nebo 'mrn_pdf')
 * @param {string} jobId - ID pro stažení (získané z response.job_id)
 * @param {string} filename - Původní název souboru (nepoužívá se pro konstrukci URL, ale může být užitečný)
 */
export const downloadFile = (fileType, jobId, filename) => {
  // Konstrukce URL pro přímé stažení
  // Endpoint: /download/{download_id}/{file_type}
  // V app.py je endpoint definován jako /download/{download_id}/{file_type}
  // Zde používáme jobId jako download_id
  const url = `${API_BASE_URL}/download/${jobId}/${fileType}`;
  window.open(url, '_blank');
};

/**
 * Health check endpoint
 * @returns {Promise} Promise s informacemi o stavu API
 */
export const healthCheck = async () => {
  try {
    const response = await api.get('/');
    return response.data;
  } catch (error) {
    throw new Error('Backend není dostupný');
  }
};
