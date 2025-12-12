import React from 'react';
import { downloadFile } from '../services/api';

const DownloadButtons = ({ jobId, outputFiles }) => {
  if (!jobId || !outputFiles) {
    return null;
  }

  const handleDownload = (fileType, filename) => {
    if (filename) {
      downloadFile(fileType, jobId, filename);
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
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        {csvFilename && (
          <button
            className="button button-secondary"
            onClick={() => handleDownload('csv', csvFilename)}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <span>📊</span>
            <span>Stáhnout CSV</span>
          </button>
        )}
        
        {pdfFilename && (
          <button
            className="button button-secondary"
            onClick={() => handleDownload('mrn_pdf', pdfFilename)}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <span>📄</span>
            <span>Stáhnout MRN PDF</span>
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

