import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'https://api.crmfit.ru';

const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  // Read initData fresh each request from Telegram's injected script
  config.headers['X-Init-Data'] = import.meta.env.DEV
    ? 'dev'
    : (window.Telegram?.WebApp?.initData || '');
  return config;
});

export const getMe = () => api.get('/api/me').then(r => r.data);
export const getOrders = () => api.get('/api/orders').then(r => r.data);
export const getBonuses = () => api.get('/api/bonuses').then(r => r.data);
export const getPromos = () => api.get('/api/promos').then(r => r.data);
export const getServices = () => api.get('/api/services').then(r => r.data);
export const createOrderRequest = (data) =>
  api.post('/api/orders/request', data).then(r => r.data);
