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

// Auth
export const getAuthRole = () => api.get('/api/auth/role').then(r => r.data);

// Master
export const getMasterMe = () => api.get('/api/master/me').then(r => r.data);
export const getMasterDashboard = () => api.get('/api/master/dashboard').then(r => r.data);
export const getMasterOrders = (date) =>
  api.get(`/api/master/orders?date=${date}`).then(r => r.data);
export const getMasterOrderDates = (year, month) =>
  api.get(`/api/master/orders/dates?year=${year}&month=${month}`).then(r => r.data);
export const getMasterOrder = (id) =>
  api.get(`/api/master/orders/${id}`).then(r => r.data);
export const completeMasterOrder = (id, data) =>
  api.put(`/api/master/orders/${id}/complete`, data).then(r => r.data);
export const moveMasterOrder = (id, data) =>
  api.put(`/api/master/orders/${id}/move`, data).then(r => r.data);
export const cancelMasterOrder = (id, data) =>
  api.put(`/api/master/orders/${id}/cancel`, data).then(r => r.data);

export const searchMasterClients = (search, page = 1) =>
  api.get(`/api/master/clients?search=${encodeURIComponent(search)}&page=${page}&per_page=10`).then(r => r.data);
export const getMasterServices = () => api.get('/api/master/services').then(r => r.data);
export const createMasterOrder = (data) => api.post('/api/master/orders', data).then(r => r.data);
export const getLastClientAddress = (clientId) =>
  api.get(`/api/master/clients/${clientId}/last-address`).then(r => r.data);

export const getBroadcastSegments = () =>
  api.get('/api/master/broadcast/segments').then(r => r.data);
export const previewBroadcast = (data) =>
  api.post('/api/master/broadcast/preview', data).then(r => r.data);
export const sendBroadcast = (data) =>
  api.post('/api/master/broadcast/send', data).then(r => r.data);
