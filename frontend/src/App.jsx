import React, { useState, useEffect, useCallback } from 'react';
import FileUpload from './components/FileUpload';
import ProcessingStatus from './components/ProcessingStatus';
import ResultsDisplay from './components/ResultsDisplay';
import Statistics from './components/Statistics';
import DownloadButtons from './components/DownloadButtons';
import Login from './components/Login';
import { uploadAndProcessPDF, healthCheck } from './services/api';
import { isAuthenticated, logout, getUser } from './services/auth';
import './App.css';

function App() {
  // Auth state
  const [isLoggedIn, setIsLoggedIn] = useState(() => isAuthenticated());
  const [currentUser, setCurrentUser] = useState(() => getUser());

  // App state
  const [queue, setQueue] = useState([]);
  const [processedFiles, setProcessedFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentFileIndex, setCurrentFileIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  
  const [selectedResultIndex, setSelectedResultIndex] = useState(0);
  
  const [backendStatus, setBackendStatus] = useState(null);

  // Handler pro úspěšné přihlášení
  const handleLoginSuccess = (result) => {
    setIsLoggedIn(true);
    setCurrentUser({ username: result.username });
  };

  // Handler pro odhlášení
  const handleLogout = () => {
    logout();
    setIsLoggedIn(false);
    setCurrentUser(null);
    // Reset app state
    setQueue([]);
    setProcessedFiles([]);
    setIsProcessing(false);
    setCurrentFileIndex(0);
    setProgress(0);
    setMessage('');
    setSelectedResultIndex(0);
  };

  // Kontrola stavu backendu při načtení
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const health = await healthCheck();
        setBackendStatus(health);
      } catch (err) {
        setBackendStatus({ status: 'error', message: err.message });
      }
    };
    checkBackend();
  }, []);

  const processNextFile = useCallback(async (file, index) => {
    setProgress(0);
    setMessage(`Nahrávám soubor: ${file.name}`);

    try {
      const result = await uploadAndProcessPDF(file, (uploadProgress) => {
        // Upload progress (0-50%)
        setProgress(Math.round(uploadProgress / 2));
      });

      setMessage(`Extrahuji data z: ${file.name}`);
      setProgress(75);

      // Add to processed files
      setProcessedFiles(prev => {
        const newFiles = [...prev];
        // Check if file already exists in list (retry logic?) - simple append for now
        newFiles.push({
          file: file,
          status: 'success',
          result: result,
          error: null
        });
        return newFiles;
      });
      
      // Select the newly processed file
      setSelectedResultIndex(index);

    } catch (err) {
      setProcessedFiles(prev => [...prev, {
        file: file,
        status: 'error',
        result: null,
        error: err.message || 'Chyba při zpracování'
      }]);
      setSelectedResultIndex(index);
    } finally {
      setProgress(0);
    }
  }, []);

  useEffect(() => {
    const processQueue = async () => {
      if (isProcessing && currentFileIndex < queue.length) {
        const file = queue[currentFileIndex];
        await processNextFile(file, currentFileIndex);
        setCurrentFileIndex(prev => prev + 1);
      } else if (isProcessing && currentFileIndex >= queue.length) {
        setIsProcessing(false);
        setMessage('Všechny soubory zpracovány.');
      }
    };

    if (isProcessing) {
      processQueue();
    }
  }, [isProcessing, currentFileIndex, queue, processNextFile]);

  const handleFileSelect = (files) => {
    const newFiles = Array.isArray(files) ? files : [files];
    setQueue(prev => [...prev, ...newFiles]);
    if (!isProcessing) {
      setIsProcessing(true);
    }
  };

  const handleReset = () => {
    setQueue([]);
    setProcessedFiles([]);
    setIsProcessing(false);
    setCurrentFileIndex(0);
    setProgress(0);
    setMessage('');
    setSelectedResultIndex(0);
  };

  const activeResult = processedFiles[selectedResultIndex];

  // Zobrazení login obrazovky, pokud uživatel není přihlášen
  if (!isLoggedIn) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="App">
      <div className="header">
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          maxWidth: '1200px',
          margin: '0 auto',
          padding: '0 20px'
        }}>
          <h1 style={{ margin: 0 }}>PDF Extractor - Webová aplikace</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {currentUser && (
              <span style={{ fontSize: '14px', opacity: 0.9 }}>
                {currentUser.username}
              </span>
            )}
            <button
              onClick={handleLogout}
              style={{
                background: 'rgba(255,255,255,0.2)',
                border: '1px solid rgba(255,255,255,0.3)',
                color: 'white',
                padding: '8px 16px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px',
                transition: 'background 0.2s'
              }}
              onMouseOver={(e) => e.target.style.background = 'rgba(255,255,255,0.3)'}
              onMouseOut={(e) => e.target.style.background = 'rgba(255,255,255,0.2)'}
            >
              Odhlásit
            </button>
          </div>
        </div>
        {backendStatus && (
          <div style={{ 
            textAlign: 'center', 
            marginTop: '10px',
            fontSize: '14px',
            color: backendStatus.status === 'ok' ? '#2ecc71' : '#e74c3c'
          }}>
            {backendStatus.status === 'ok' 
              ? '✅ Backend připojen' 
              : `❌ Backend nedostupný: ${backendStatus.message || 'Zkontrolujte připojení'}`}
          </div>
        )}
      </div>

      <div className="container">
        {/* Upload sekce - vždy viditelná, ale disabled pokud se zpracovává */}
        <div className="card">
           <h2 style={{ marginBottom: '20px', textAlign: 'center' }}>
             {queue.length === 0 ? 'Nahrajte PDF soubory' : 'Přidat další soubory'}
           </h2>
           <FileUpload onFileSelect={handleFileSelect} disabled={isProcessing} />
        </div>

        {/* Status a Progress */}
        {(isProcessing || queue.length > 0) && (
          <div className="card" style={{ marginTop: '20px' }}>
            <h3>Stav zpracování</h3>
            <div style={{ marginBottom: '10px', color: '#7f8c8d' }}>
              Zpracováno {currentFileIndex} z {queue.length} souborů
            </div>
            
            {isProcessing && (
              <ProcessingStatus 
                status="processing" 
                progress={progress} 
                message={message}
              />
            )}

            {!isProcessing && queue.length > 0 && (
              <div className="success">
                ✅ Dávka dokončena
              </div>
            )}
          </div>
        )}

        {/* Seznam zpracovaných souborů (Sidebar/List) */}
        {processedFiles.length > 0 && (
          <div className="processed-files-list card" style={{ marginTop: '20px' }}>
            <h3>Zpracované soubory</h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '10px' }}>
              {processedFiles.map((item, index) => (
                <button
                  key={index}
                  onClick={() => setSelectedResultIndex(index)}
                  style={{
                    padding: '8px 12px',
                    backgroundColor: selectedResultIndex === index ? '#3498db' : (item.status === 'success' ? '#eafaf1' : '#fdedec'),
                    color: selectedResultIndex === index ? 'white' : (item.status === 'success' ? '#2ecc71' : '#e74c3c'),
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: selectedResultIndex === index ? 'bold' : 'normal'
                  }}
                >
                  {item.file.name} {item.status === 'success' ? '✅' : '❌'}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Detail vybraného výsledku */}
        {activeResult && activeResult.status === 'success' && activeResult.result && (
          <div style={{ marginTop: '20px' }}>
            <h2>Výsledky pro: {activeResult.file.name}</h2>
            
            <Statistics 
              usageInfo={activeResult.result.usage_info} 
              processingTime={activeResult.result.processing_time}
            />

            <DownloadButtons 
              jobId={activeResult.result.job_id}
              outputFiles={activeResult.result.output_files}
            />

            <ResultsDisplay extractedData={activeResult.result.extracted_data} />
          </div>
        )}

        {activeResult && activeResult.status === 'error' && (
           <div className="error" style={{ marginTop: '20px' }}>
              <strong>Chyba při zpracování {activeResult.file.name}:</strong> {activeResult.error}
           </div>
        )}

        {processedFiles.length > 0 && !isProcessing && (
           <div style={{ textAlign: 'center', marginTop: '40px' }}>
              <button className="button" onClick={handleReset}>
                Resetovat vše
              </button>
           </div>
        )}
      </div>
    </div>
  );
}

export default App;
