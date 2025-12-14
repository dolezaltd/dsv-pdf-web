import axios from 'axios';
import { getToken, logout } from './auth';

// Načtení URL backendu z environment proměnných nebo fallback na localhost
// V Vite se environment proměnné musí jmenovat VITE_...
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

console.log('Using API Base URL:', API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minut pro zpracování velkých souborů
});

// Interceptor pro přidání Authorization headeru ke všem požadavkům
api.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor pro zachycení 401 odpovědí (neautorizovaný přístup)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Token je neplatný nebo expirovaný
      logout();
      // Přesměrování na login (reload stránky)
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

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
 * @param {string} filename - Původní název souboru
 */
export const downloadFile = async (fileType, jobId, filename) => {
  try {
    // Použijeme axios s auth headerem pro stažení
    const response = await api.get(`/download/${jobId}/${fileType}`, {
      responseType: 'blob'
    });
    
    // Vytvoření URL pro blob a stažení
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    
    // Nastavení názvu souboru
    const downloadFilename = fileType === 'csv' 
      ? `${jobId}.csv` 
      : `${jobId}_MRN.pdf`;
    link.setAttribute('download', downloadFilename);
    
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Download error:', error);
    throw new Error('Chyba při stahování souboru');
  }
};

/**
 * Health check endpoint
 * @returns {Promise} Promise s informacemi o stavu API
 */
export const healthCheck = async () => {
  try {
    const response = await api.get('/');
    // Pokud backend vrátí validní odpověď (i když jen message), považujeme to za OK
    return { 
      status: 'ok', 
      message: response.data.message || 'Backend běží' 
    };
  } catch (error) {
    throw new Error('Backend není dostupný');
  }
};
