import React from 'react';

const Statistics = ({ usageInfo, processingTime }) => {
  if (!usageInfo) {
    return null;
  }

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '0';
    return new Intl.NumberFormat('cs-CZ').format(num);
  };

  const formatCurrency = (amount) => {
    if (amount === null || amount === undefined) return '0,00';
    return new Intl.NumberFormat('cs-CZ', {
      style: 'currency',
      currency: 'CZK',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatTime = (seconds) => {
    if (!seconds) return '0 s';
    if (seconds < 60) {
      return `${seconds.toFixed(2)} s`;
    }
    const minutes = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(2);
    return `${minutes} min ${secs} s`;
  };

  // Převod USD na CZK (kurz 23.5)
  const USD_TO_CZK = 23.5;
  const costCzk = (usageInfo.total_cost_usd || 0) * USD_TO_CZK;

  return (
    <div className="card">
      <h2 style={{ marginBottom: '20px' }}>Statistiky zpracování</h2>
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px'
      }}>
        <div style={{
          padding: '16px',
          backgroundColor: '#ebf5fb',
          borderRadius: '6px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#2c3e50' }}>
            {formatNumber(usageInfo.total_tokens)}
          </div>
          <div style={{ color: '#7f8c8d', fontSize: '14px', marginTop: '4px' }}>
            Celkem tokenů
          </div>
        </div>
        
        <div style={{
          padding: '16px',
          backgroundColor: '#d5f4e6',
          borderRadius: '6px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#27ae60' }}>
            {formatCurrency(costCzk)}
          </div>
          <div style={{ color: '#7f8c8d', fontSize: '14px', marginTop: '4px' }}>
            Odhadovaná cena
          </div>
        </div>
        
        <div style={{
          padding: '16px',
          backgroundColor: '#fef5e7',
          borderRadius: '6px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#d68910' }}>
            {formatTime(processingTime)}
          </div>
          <div style={{ color: '#7f8c8d', fontSize: '14px', marginTop: '4px' }}>
            Čas zpracování
          </div>
        </div>
        
        <div style={{
          padding: '16px',
          backgroundColor: '#f4ecf7',
          borderRadius: '6px',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#8e44ad' }}>
            {usageInfo.model || 'N/A'}
          </div>
          <div style={{ color: '#7f8c8d', fontSize: '14px', marginTop: '4px' }}>
            Použitý model
          </div>
        </div>
      </div>
      
      <div style={{ marginTop: '20px', padding: '12px', backgroundColor: '#f8f9fa', borderRadius: '6px' }}>
        <div style={{ fontSize: '12px', color: '#7f8c8d' }}>
          <strong>Detailní informace:</strong>
          <div style={{ marginTop: '8px' }}>
            Vstupní tokeny: {formatNumber(usageInfo.prompt_tokens)} | 
            Výstupní tokeny: {formatNumber(usageInfo.completion_tokens)}
          </div>
          {usageInfo.total_cost_usd && (
            <div style={{ marginTop: '4px' }}>
              Cena v USD: ${usageInfo.total_cost_usd.toFixed(6)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Statistics;

