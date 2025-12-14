import React, { useState } from 'react';

const ResultsDisplay = ({ extractedData }) => {
  const [copied, setCopied] = useState(false);

  if (!extractedData || extractedData.length === 0) {
    return (
      <div className="card">
        <p style={{ color: '#7f8c8d', textAlign: 'center' }}>
          Žádná data k zobrazení
        </p>
      </div>
    );
  }

  // Získání všech unikátních klíčů ze všech záznamů
  const allKeys = new Set();
  extractedData.forEach(record => {
    Object.keys(record).forEach(key => allKeys.add(key));
  });

  const columns = Array.from(allKeys).sort();

  const copyToClipboard = () => {
    // Hlavička - názvy sloupců (formátované jako v tabulce)
    const header = columns.map(key => 
      key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    ).join('\t');
    
    // Řádky - hodnoty oddělené tabulátory
    const rows = extractedData.map(record => 
      columns.map(key => {
        const value = record[key];
        if (value === null || value === undefined) return '-';
        if (Array.isArray(value)) return value.join(', ');
        return String(value);
      }).join('\t')
    ).join('\n');
    
    // Kopírování do schránky
    navigator.clipboard.writeText(`${header}\n${rows}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="card">
      <h2 style={{ marginBottom: '20px' }}>
        Extrahovaná data ({extractedData.length} záznam{extractedData.length !== 1 ? 'ů' : ''})
      </h2>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ 
          width: '100%', 
          borderCollapse: 'collapse',
          fontSize: '14px'
        }}>
          <thead>
            <tr style={{ backgroundColor: '#34495e', color: 'white' }}>
              {columns.map((key) => (
                <th
                  key={key}
                  style={{
                    padding: '12px',
                    textAlign: 'left',
                    border: '1px solid #2c3e50',
                    fontWeight: 'bold',
                  }}
                >
                  {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {extractedData.map((record, index) => (
              <tr
                key={index}
                style={{
                  backgroundColor: index % 2 === 0 ? '#ffffff' : '#f8f9fa',
                }}
              >
                {columns.map((key) => {
                  const value = record[key];
                  let displayValue = '';
                  
                  if (value === null || value === undefined) {
                    displayValue = '-';
                  } else if (Array.isArray(value)) {
                    displayValue = value.join(', ');
                  } else {
                    displayValue = String(value);
                  }
                  
                  return (
                    <td
                      key={key}
                      style={{
                        padding: '10px 12px',
                        border: '1px solid #e0e0e0',
                        wordBreak: 'break-word',
                        maxWidth: '200px',
                      }}
                    >
                      {displayValue}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: '16px', textAlign: 'right' }}>
        <button className="button" onClick={copyToClipboard}>
          {copied ? '✓ Zkopírováno!' : '📋 Kopírovat tabulku'}
        </button>
      </div>
    </div>
  );
};

export default ResultsDisplay;

