import axios from 'axios';

// Simplification: Always use /api.
// In Development: Vite Proxy forwards this to http://localhost:8000
// In Production: It serves relative to the domain (same origin)
// VERSION 2025-12-23-FIX-01
const API_BASE_URL = '/api';

console.log('DEBUG: Auth Config Loaded. VERSION: 2025-12-23-FIX-01');
console.log('DEBUG: Using API_BASE_URL:', API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Request interceptor to add JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // For FormData requests, remove Content-Type header to let browser set it with boundary
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid, remove it
      localStorage.removeItem('token');
      // Redirect to login will be handled by ProtectedRoute
    }
    return Promise.reject(error);
  }
);

export default api;

