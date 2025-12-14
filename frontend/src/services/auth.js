import axios from 'axios';

// Načtení URL backendu z environment proměnných nebo fallback na localhost
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Klíče pro localStorage/sessionStorage
const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';
const REMEMBER_KEY = 'auth_remember';

/**
 * Získá storage podle toho, zda je zaškrtnuto "zapamatovat si mě"
 */
const getStorage = () => {
  const remember = localStorage.getItem(REMEMBER_KEY) === 'true';
  return remember ? localStorage : sessionStorage;
};

/**
 * Přihlášení uživatele
 * @param {string} username - Uživatelské jméno
 * @param {string} password - Heslo
 * @param {boolean} rememberMe - Zapamatovat si přihlášení
 * @returns {Promise<{token: string, username: string, expires_at: string}>}
 */
export const login = async (username, password, rememberMe = false) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/auth/login`, {
      username,
      password,
      remember_me: rememberMe
    });

    const { token, username: user, expires_at } = response.data;

    // Uložíme příznak "zapamatovat si mě" do localStorage
    localStorage.setItem(REMEMBER_KEY, rememberMe.toString());

    // Vybereme správné úložiště
    const storage = rememberMe ? localStorage : sessionStorage;
    
    // Uložíme token a uživatele
    storage.setItem(TOKEN_KEY, token);
    storage.setItem(USER_KEY, JSON.stringify({ username: user, expires_at }));

    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.detail || 'Přihlášení selhalo');
    } else if (error.request) {
      throw new Error('Nelze se připojit k serveru');
    } else {
      throw new Error(error.message || 'Nastala neočekávaná chyba');
    }
  }
};

/**
 * Odhlášení uživatele
 */
export const logout = () => {
  // Smažeme z obou úložišť pro jistotu
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(REMEMBER_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
};

/**
 * Získá uložený token
 * @returns {string|null}
 */
export const getToken = () => {
  // Zkusíme localStorage i sessionStorage
  return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
};

/**
 * Získá informace o přihlášeném uživateli
 * @returns {{username: string, expires_at: string}|null}
 */
export const getUser = () => {
  const userStr = localStorage.getItem(USER_KEY) || sessionStorage.getItem(USER_KEY);
  if (!userStr) return null;
  
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
};

/**
 * Zkontroluje, zda je uživatel přihlášen a token není expirovaný
 * @returns {boolean}
 */
export const isAuthenticated = () => {
  const token = getToken();
  if (!token) return false;

  const user = getUser();
  if (!user || !user.expires_at) return false;

  // Kontrola expirace
  const expiresAt = new Date(user.expires_at);
  const now = new Date();
  
  if (now >= expiresAt) {
    // Token expiroval, vyčistíme storage
    logout();
    return false;
  }

  return true;
};

/**
 * Ověří token na serveru
 * @returns {Promise<boolean>}
 */
export const verifyToken = async () => {
  const token = getToken();
  if (!token) return false;

  try {
    const response = await axios.get(`${API_BASE_URL}/auth/verify`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    return response.data.valid === true;
  } catch {
    // Token není platný, vyčistíme storage
    logout();
    return false;
  }
};

export default {
  login,
  logout,
  getToken,
  getUser,
  isAuthenticated,
  verifyToken
};
