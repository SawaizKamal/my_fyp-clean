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
    // #region agent log
    if (process.env.NODE_ENV === 'development' && config.url && config.url.includes('transcribe/status')) {
      fetch('http://127.0.0.1:7243/ingest/437f7cb7-d9e7-437e-82fe-e00f0e39dcc2',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api/config.js:22',message:'Request interceptor - adding token',data:{url:config.url,has_token:!!token,token_length:token?.length||0,has_auth_header:!!config.headers.Authorization},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'AUTH'})}).catch(()=>{});
    }
    // #endregion
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
      // #region agent log
      if (process.env.NODE_ENV === 'development') {
        const tokenBeforeRemoval = localStorage.getItem('token');
        fetch('http://127.0.0.1:7243/ingest/437f7cb7-d9e7-437e-82fe-e00f0e39dcc2',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api/config.js:42',message:'Response interceptor - 401 error',data:{url:error.config?.url,has_token_before_removal:!!tokenBeforeRemoval,response_status:error.response?.status,response_data:error.response?.data},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'AUTH'})}).catch(()=>{});
      }
      // #endregion
      // Token expired or invalid, remove it
      localStorage.removeItem('token');
      // Redirect to login will be handled by ProtectedRoute
    }
    return Promise.reject(error);
  }
);

export default api;

