import React, { useRef, useState } from 'react';

const FileUpload = ({ onFileSelect, disabled }) => {
  const fileInputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = (files) => {
    const validFiles = Array.from(files).filter(file => file.type === 'application/pdf');
    
    if (validFiles.length > 0) {
      onFileSelect(validFiles);
    } else if (files.length > 0) {
      alert('Prosím, vyberte pouze PDF soubory.');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const handleClick = () => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  };

  return (
    <div
      className={`file-upload-area ${isDragging ? 'dragging' : ''} ${disabled ? 'disabled' : ''}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={handleClick}
      style={{
        border: `2px dashed ${isDragging ? '#3498db' : '#bdc3c7'}`,
        borderRadius: '8px',
        padding: '40px',
        textAlign: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        backgroundColor: isDragging ? '#ebf5fb' : '#f8f9fa',
        transition: 'all 0.3s ease',
        opacity: disabled ? 0.6 : 1,
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        multiple
        onChange={handleInputChange}
        style={{ display: 'none' }}
        disabled={disabled}
      />
      <div style={{ fontSize: '48px', marginBottom: '16px' }}>📄</div>
      <div style={{ fontSize: '18px', marginBottom: '8px', fontWeight: 'bold' }}>
        {isDragging ? 'Pusťte soubory zde' : 'Přetáhněte PDF soubory sem'}
      </div>
      <div style={{ color: '#7f8c8d', marginBottom: '16px' }}>
        nebo klikněte pro výběr souborů
      </div>
      <div style={{ fontSize: '14px', color: '#95a5a6' }}>
        Podporované formáty: PDF (max. 50 MB)
      </div>
    </div>
  );
};

export default FileUpload;
