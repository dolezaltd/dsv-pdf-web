import React, { useState } from 'react';
import { login } from '../services/auth';

function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const result = await login(username, password, rememberMe);
      onLoginSuccess(result);
    } catch (err) {
      setError(err.message || 'Přihlášení selhalo');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.loginCard}>
        <div style={styles.header}>
          <h1 style={styles.title}>PDF Extractor</h1>
          <p style={styles.subtitle}>Přihlaste se pro přístup k aplikaci</p>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          {error && (
            <div className="error" style={styles.error}>
              {error}
            </div>
          )}

          <div style={styles.inputGroup}>
            <label htmlFor="username" style={styles.label}>
              Uživatelské jméno
            </label>
            <input
              id="username"
              name="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={styles.input}
              placeholder="Zadejte uživatelské jméno"
              required
              disabled={isLoading}
              autoComplete="username"
            />
          </div>

          <div style={styles.inputGroup}>
            <label htmlFor="password" style={styles.label}>
              Heslo
            </label>
            <input
              id="password"
              name="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={styles.input}
              placeholder="Zadejte heslo"
              required
              disabled={isLoading}
              autoComplete="current-password"
            />
          </div>

          <div style={styles.checkboxGroup}>
            <label style={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                style={styles.checkbox}
                disabled={isLoading}
              />
              <span style={styles.checkboxText}>Zapamatovat si mě (30 dní)</span>
            </label>
          </div>

          <button
            type="submit"
            className="button"
            style={styles.submitButton}
            disabled={isLoading}
          >
            {isLoading ? 'Přihlašuji...' : 'Přihlásit se'}
          </button>
        </form>
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f5f5f5',
    padding: '20px',
  },
  loginCard: {
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
    padding: '40px',
    width: '100%',
    maxWidth: '400px',
  },
  header: {
    textAlign: 'center',
    marginBottom: '32px',
  },
  title: {
    fontSize: '28px',
    fontWeight: '700',
    color: '#2c3e50',
    marginBottom: '8px',
  },
  subtitle: {
    fontSize: '14px',
    color: '#7f8c8d',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '14px',
    fontWeight: '500',
    color: '#34495e',
  },
  input: {
    padding: '12px 16px',
    fontSize: '16px',
    border: '2px solid #e0e0e0',
    borderRadius: '8px',
    outline: 'none',
    transition: 'border-color 0.2s',
  },
  checkboxGroup: {
    marginTop: '4px',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
  },
  checkbox: {
    width: '18px',
    height: '18px',
    marginRight: '10px',
    cursor: 'pointer',
  },
  checkboxText: {
    fontSize: '14px',
    color: '#555',
  },
  submitButton: {
    width: '100%',
    marginTop: '8px',
    padding: '14px',
    fontSize: '16px',
    fontWeight: '600',
  },
  error: {
    textAlign: 'center',
  },
};

export default Login;
