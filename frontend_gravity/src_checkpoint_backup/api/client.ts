import axios from 'axios';

// Base API instance
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to inject auth headers from localized storage or store
api.interceptors.request.use((config) => {
  // We'll read from localStorage to avoid circular dependencies with Zustand
  const auth = localStorage.getItem('industrix-auth');
  if (auth) {
    try {
      const parsed = JSON.parse(auth);
      if (parsed.state && parsed.state.teamId && parsed.state.pin) {
        config.headers['X-Team-Id'] = parsed.state.teamId;
        config.headers['X-Team-Pin'] = parsed.state.pin;
      }
    } catch (e) {
      console.error("Failed to parse auth", e);
    }
  }
  return config;
});

export default api;
