import axios from 'axios';
import WebApp from '@twa-dev/sdk';

const API_URL = import.meta.env.VITE_API_URL || 'https://api.crmfit.ru';

const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  // In dev mode send "dev" — backend accepts this when APP_ENV=development
  config.headers['X-Init-Data'] = import.meta.env.DEV ? 'dev' : WebApp.initData;
  return config;
});

export const getMe = () => api.get('/api/me').then(r => r.data);
export const getOrders = () => api.get('/api/orders').then(r => r.data);
export const getBonuses = () => api.get('/api/bonuses').then(r => r.data);
export const getPromos = () => api.get('/api/promos').then(r => r.data);
export const getServices = () => api.get('/api/services').then(r => r.data);
export const createOrderRequest = (data) =>
  api.post('/api/orders/request', data).then(r => r.data);
