import React, { useState } from 'react';
import { downloadFile } from '../services/api';

const DownloadButtons = ({ jobId, outputFiles }) => {
  const [downloading, setDownloading] = useState(null);
  const [error, setError] = useState(null);

  if (!jobId || !outputFiles) {
    return null;
  }

  const handleDownload = async (fileType, filename) => {
    if (filename) {
      setDownloading(fileType);
      setError(null);
      try {
        await downloadFile(fileType, jobId, filename);
      } catch (err) {
        setError(err.message);
      } finally {
        setDownloading(null);
      }
    }
  };

  const getFilenameFromPath = (path) => {
    if (!path) return null;
    return path.split('/').pop();
  };

  const csvFilename = outputFiles.csv_download 
    ? getFilenameFromPath(outputFiles.csv_download)
    : getFilenameFromPath(outputFiles.csv);

  const pdfFilename = outputFiles.mrn_pdf_download
    ? getFilenameFromPath(outputFiles.mrn_pdf_download)
    : getFilenameFromPath(outputFiles.mrn_pdf);

  return (
    <div className="card">
      <h2 style={{ marginBottom: '16px' }}>Stažení výsledků</h2>
      {error && (
        <div className="error" style={{ marginBottom: '12px' }}>
          {error}
        </div>
      )}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        {csvFilename && (
          <button
            className="button button-secondary"
            onClick={() => handleDownload('csv', csvFilename)}
            disabled={downloading !== null}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <span>📊</span>
            <span>{downloading === 'csv' ? 'Stahování...' : 'Stáhnout CSV'}</span>
          </button>
        )}
        
        {pdfFilename && (
          <button
            className="button button-secondary"
            onClick={() => handleDownload('mrn_pdf', pdfFilename)}
            disabled={downloading !== null}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <span>📄</span>
            <span>{downloading === 'mrn_pdf' ? 'Stahování...' : 'Stáhnout MRN PDF'}</span>
          </button>
        )}
        
        {!csvFilename && !pdfFilename && (
          <p style={{ color: '#7f8c8d' }}>
            Žádné soubory ke stažení
          </p>
        )}
      </div>
    </div>
  );
};

export default DownloadButtons;

