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

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401 || status === 403) {
      const WebApp = window.Telegram?.WebApp;
      if (typeof WebApp?.showAlert === 'function') {
        WebApp.showAlert('Сессия истекла, перезапустите приложение');
      }
    }
    return Promise.reject(error);
  }
);

// Active master (module-level — localStorage unavailable in TG Mini App)
let _activeMasterId = null;
export const setActiveMasterId = (id) => { _activeMasterId = id; };

const masterParams = () => (_activeMasterId != null ? { master_id: _activeMasterId } : {});

export const getMe = () => api.get('/api/me', { params: masterParams() }).then(r => r.data);
export const getOrders = () => api.get('/api/orders', { params: masterParams() }).then(r => r.data);
export const getBonuses = () => api.get('/api/bonuses', { params: masterParams() }).then(r => r.data);
export const getPromos = () => api.get('/api/promos', { params: masterParams() }).then(r => r.data);
export const getServices = () => api.get('/api/services', { params: masterParams() }).then(r => r.data);
export const createOrderRequest = (data) =>
  api.post('/api/orders/request', data).then(r => r.data);

// Multi-master
export const getClientMasters = () => api.get('/api/client/masters').then(r => r.data);
export const linkToMaster = (token) => api.post('/api/client/link', { invite_token: token }).then(r => r.data);

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
export const sendBroadcast = (formData) =>
  api.post('/api/master/broadcast/send', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  }).then(r => r.data);
export const getBroadcastCanSend = () =>
  api.get('/api/master/broadcast/can-send').then(r => r.data);

export const getMasterInviteLink = () =>
  api.get('/api/master/invite-link').then(r => r.data);

// V2 — Clients (extended)
export const getMasterClients = (search = '', page = 1) =>
  api.get('/api/master/clients', { params: { search, page, per_page: 20 } }).then(r => r.data);
export const getMasterClient = (id) =>
  api.get(`/api/master/clients/${id}`).then(r => r.data);
export const updateMasterClient = (id, data) =>
  api.put(`/api/master/clients/${id}`, data).then(r => r.data);
export const updateMasterClientNote = (id, note) =>
  api.put(`/api/master/clients/${id}/note`, { note }).then(r => r.data);
export const masterClientBonus = (id, amount, comment) =>
  api.post(`/api/master/clients/${id}/bonus`, { amount, comment }).then(r => r.data);

// V2 — Profile / Settings
export const updateMasterProfile = (data) =>
  api.put('/api/master/profile', data).then(r => r.data);
export const updateMasterTimezone = (timezone) =>
  api.put('/api/master/timezone', { timezone }).then(r => r.data);
export const updateMasterCurrency = (currency) =>
  api.put('/api/master/currency', { currency }).then(r => r.data);
export const getMasterInvite = () =>
  api.get('/api/master/invite').then(r => r.data);

// V2 — Bonus settings
export const getMasterBonusSettings = () =>
  api.get('/api/master/bonus-settings').then(r => r.data);
export const updateMasterBonusSettings = (data) =>
  api.put('/api/master/bonus-settings', data).then(r => r.data);

// V2 — Services (full CRUD — backward compat: getMasterServices still works)
export const getMasterServicesAll = () =>
  api.get('/api/master/services').then(r => r.data);
export const createMasterService = (data) =>
  api.post('/api/master/services', data).then(r => r.data);
export const updateMasterService = (id, data) =>
  api.put(`/api/master/services/${id}`, data).then(r => r.data);
export const archiveMasterService = (id) =>
  api.put(`/api/master/services/${id}/archive`).then(r => r.data);
export const restoreMasterService = (id) =>
  api.put(`/api/master/services/${id}/restore`).then(r => r.data);

// V2 — Promos
export const getMasterPromos = () =>
  api.get('/api/master/promos').then(r => r.data);
export const createMasterPromo = (data) =>
  api.post('/api/master/promos', data).then(r => r.data);
export const deactivateMasterPromo = (id) =>
  api.put(`/api/master/promos/${id}/deactivate`).then(r => r.data);
export const getPromoRecipientsCount = () =>
  api.get('/api/master/promos/recipients-count').then(r => r.data);

// Reports
// params: { period: 'week'|'month'|'today' } or { date_from: 'YYYY-MM-DD', date_to: 'YYYY-MM-DD' }
export const getMasterReports = (params) =>
  api.get('/api/master/reports', { params }).then(r => r.data);

// Client creation
export const createMasterClient = (data) =>
  api.post('/api/master/clients', data).then(r => r.data);
// data: { name: string, phone: string, birthday?: string }

export const restoreArchivedClient = (clientId) =>
  api.post(`/api/master/clients/${clientId}/restore`).then(r => r.data);

// Master registration (onboarding)
export const registerMaster = (data) =>
  api.post('/api/master/register', data).then(r => r.data);
