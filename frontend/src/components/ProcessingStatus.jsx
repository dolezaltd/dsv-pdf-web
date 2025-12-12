import React from 'react';

const ProcessingStatus = ({ status, progress, message }) => {
  if (status === 'idle') {
    return null;
  }

  const getStatusIcon = () => {
    switch (status) {
      case 'uploading':
        return '⬆️';
      case 'processing':
        return '⚙️';
      case 'success':
        return '✅';
      case 'error':
        return '❌';
      default:
        return '⏳';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'uploading':
        return 'Nahrávání souboru...';
      case 'processing':
        return 'Zpracování PDF pomocí AI...';
      case 'success':
        return 'Zpracování dokončeno!';
      case 'error':
        return 'Chyba při zpracování';
      default:
        return 'Čekání...';
    }
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px' }}>
        <span style={{ fontSize: '24px', marginRight: '12px' }}>{getStatusIcon()}</span>
        <h3 style={{ margin: 0 }}>{getStatusText()}</h3>
      </div>
      
      {message && (
        <div style={{ marginTop: '12px', padding: '12px', backgroundColor: '#f8f9fa', borderRadius: '6px' }}>
          {message}
        </div>
      )}
      
      {(status === 'uploading' || status === 'processing') && progress !== null && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ 
            width: '100%', 
            height: '8px', 
            backgroundColor: '#ecf0f1', 
            borderRadius: '4px',
            overflow: 'hidden'
          }}>
            <div
              style={{
                width: `${progress}%`,
                height: '100%',
                backgroundColor: '#3498db',
                transition: 'width 0.3s ease',
              }}
            />
          </div>
          <div style={{ textAlign: 'center', marginTop: '8px', color: '#7f8c8d' }}>
            {progress}%
          </div>
        </div>
      )}
      
      {status === 'processing' && (
        <div style={{ marginTop: '16px', color: '#7f8c8d', fontSize: '14px' }}>
          ⏱️ Zpracování může trvat několik minut v závislosti na velikosti souboru...
        </div>
      )}
    </div>
  );
};

export default ProcessingStatus;

