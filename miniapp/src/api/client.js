import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'https://api.crmfit.ru';

const api = axios.create({ baseURL: API_URL });
const LANG_STORAGE_KEY = 'miniapp_lang';

function getLang() {
  try {
    const stored = (localStorage.getItem(LANG_STORAGE_KEY) || '').toLowerCase();
    if (stored.startsWith('en')) return 'en';
  } catch {
    // ignore storage errors
  }
  const tgLang = (window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code || '').toLowerCase();
  return tgLang.startsWith('en') ? 'en' : 'ru';
}

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
    const payload = error?.response?.data;
    const isSubscriptionRequired =
      payload?.error === 'subscription_required' ||
      payload?.detail?.error === 'subscription_required';
    if (status === 401 || status === 403) {
      if (!isSubscriptionRequired) {
        const WebApp = window.Telegram?.WebApp;
        if (typeof WebApp?.showAlert === 'function') {
          const msg = getLang() === 'en'
            ? 'Session expired, please restart the app'
            : 'Сессия истекла, перезапустите приложение';
          WebApp.showAlert(msg);
        }
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
export async function createOrderRequest({ service_name, comment, desired_date, desired_time, files, file, media_type }) {
  const fd = new FormData();
  fd.append('service_name', service_name);
  if (comment) fd.append('comment', comment);
  if (desired_date) fd.append('desired_date', desired_date);
  if (desired_time) fd.append('desired_time', desired_time);
  const mediaFiles = Array.isArray(files) ? files : (file ? [file] : []);
  for (const mediaFile of mediaFiles) {
    fd.append('media', mediaFile, mediaFile.name);
  }
  if (media_type) {
    fd.append('media_type', media_type);
  }
  return api.post('/api/orders/request', fd, {
    params: masterParams(),
  }).then(r => r.data);
}

export async function createQuestion({ text, files, file, media_type }) {
  const fd = new FormData();
  fd.append('text', text);
  const mediaFiles = Array.isArray(files) ? files : (file ? [file] : []);
  for (const mediaFile of mediaFiles) {
    fd.append('media', mediaFile, mediaFile.name);
  }
  if (media_type) {
    fd.append('media_type', media_type);
  }
  return api.post('/api/requests/question', fd, {
    params: masterParams(),
  }).then(r => r.data);
}

// Multi-master
export const getClientMasters = () => api.get('/api/client/masters').then(r => r.data);
export const linkToMaster = (token) => api.post('/api/client/link', { invite_token: token }).then(r => r.data);

// Auth
export const getAuthRole = () => api.get('/api/auth/role').then(r => r.data);

// Master
export const getMasterMe = () => api.get('/api/master/me').then((r) => {
  const data = r.data || {};
  const phone = data.phone || data.contacts || '';
  const socials = data.socials || [data.telegram, data.instagram, data.website].filter(Boolean).join(' · ');
  return {
    ...data,
    phone,
    contacts: data.contacts ?? phone,
    socials,
  };
});
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
export const getMasterClientAddresses = (clientId) =>
  api.get(`/api/master/clients/${clientId}/addresses`).then(r => r.data);
export const createMasterClientAddress = (clientId, data) =>
  api.post(`/api/master/clients/${clientId}/addresses`, data).then(r => r.data);

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
export const getMasterSubscription = () =>
  api.get('/api/master/subscription').then(r => r.data);
export const createMasterSubscriptionInvoiceLink = (data) =>
  api.post('/api/master/subscription/invoice-link', data).then(r => r.data);
export const trackMasterReferralLinkCopied = (source = 'unknown') =>
  api.post('/api/master/subscription/referral-link-copied', { source }).then(r => r.data);

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
export const updateMasterProfile = (data) => {
  const payload = { ...data };
  if (Object.prototype.hasOwnProperty.call(payload, 'contacts') && !Object.prototype.hasOwnProperty.call(payload, 'phone')) {
    payload.phone = payload.contacts;
  }
  return api.put('/api/master/profile', payload).then(r => r.data);
};
export const updateMasterTimezone = (timezone) =>
  api.put('/api/master/timezone', { timezone }).then(r => r.data);
export const updateMasterCurrency = (currency) =>
  api.put('/api/master/currency', { currency }).then(r => r.data);
export const getMasterInvite = () =>
  api.get('/api/master/invite').then(r => r.data);
export const getMasterGoogleCalendar = () =>
  api.get('/api/master/google-calendar').then(r => r.data);
export const getMasterGoogleCalendarConnectUrl = () =>
  api.post('/api/master/google-calendar/connect').then(r => r.data);
export const disconnectMasterGoogleCalendar = () =>
  api.post('/api/master/google-calendar/disconnect').then(r => r.data);

// V2 — Bonus settings
export const getMasterBonusSettings = () =>
  api.get('/api/master/bonus-settings').then(r => r.data);
export const updateMasterBonusSettings = (data) =>
  api.put('/api/master/bonus-settings', data).then(r => r.data);
export const uploadMasterBonusPhoto = (bonusType, file) => {
  const fd = new FormData();
  fd.append('photo', file, file.name || 'image.jpg');
  return api.post(`/api/master/bonus-settings/${bonusType}/photo`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
};
export const deleteMasterBonusPhoto = (bonusType) =>
  api.delete(`/api/master/bonus-settings/${bonusType}/photo`).then(r => r.data);

// V2 — Feedback settings
export const getMasterFeedbackSettings = () =>
  api.get('/api/master/settings/feedback').then(r => r.data);
export const updateMasterFeedbackSettings = (data) =>
  api.put('/api/master/settings/feedback', data).then(r => r.data);

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

// Requests
export const getMasterRequests = (status) =>
  api.get('/api/master/requests', { params: status && status !== 'all' ? { status } : {} }).then(r => r.data);
export const getMasterRequestMedia = (id) =>
  api.get(`/api/master/requests/${id}/media`).then(r => r.data);
export const getMasterRequestMediaUrl = (id) =>
  api.get(`/api/master/requests/${id}/media-url`).then(r => r.data);
export const getMasterRequestsUnreadCount = () =>
  api.get('/api/master/requests/unread_count').then(r => r.data);
export const closeMasterRequest = (id) =>
  api.post(`/api/master/requests/${id}/close`).then(r => r.data);

// ── Client App v2 ────────────────────────────────────────────────────────────

export const getClientMasterProfile = (masterId) =>
  api.get(`/api/client/master/${masterId}/profile`).then(r => r.data);

export const getClientMasterActivity = (masterId, limit = 3) =>
  api.get(`/api/client/master/${masterId}/activity`, { params: { limit } }).then(r => r.data);

export const getClientMasterServices = (masterId) =>
  api.get(`/api/client/master/${masterId}/services`).then(r => r.data);

export const getClientMasterNews = (masterId) =>
  api.get(`/api/client/master/${masterId}/news`, { params: { limit: 1 } }).then(r => r.data);

export const getClientMasterHistory = (masterId, limit = 20, offset = 0) =>
  api.get(`/api/client/master/${masterId}/history`, { params: { limit, offset } }).then(r => r.data);

export const getClientMasterPublications = (masterId, limit = 20, offset = 0) =>
  api.get(`/api/client/master/${masterId}/publications`, { params: { limit, offset } }).then(r => r.data);

export const getClientMasterSettings = (masterId) =>
  api.get(`/api/client/master/${masterId}/settings`).then(r => r.data);

export const patchClientMasterSettings = (masterId, patch) =>
  api.patch(`/api/client/master/${masterId}/settings`, patch).then(r => r.data);

export const getClientMasterReviews = (masterId, limit = 20, offset = 0) =>
  api.get(`/api/client/master/${masterId}/reviews`, { params: { limit, offset } }).then(r => r.data);

export const confirmClientOrder = (orderId) =>
  api.post(`/api/client/orders/${orderId}/confirm`).then(r => r.data);

export const createClientOrderReview = (orderId, body) =>
  api.post(`/api/client/orders/${orderId}/review`, body).then(r => r.data);

export const deleteClientProfile = () =>
  api.delete('/api/client/profile').then(r => r.data);

// V2 — Avatar upload/delete
export const uploadMasterAvatar = (formData) =>
  api.post('/api/master/avatar/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
export const deleteMasterAvatar = () =>
  api.delete('/api/master/avatar').then(r => r.data);

// V2 — Portfolio upload/list/delete
export const uploadPortfolioPhoto = (formData) =>
  api.post('/api/master/portfolio/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
export const getMasterPortfolio = () =>
  api.get('/api/master/portfolio').then(r => r.data);
export const deletePortfolioPhoto = (id) =>
  api.delete(`/api/master/portfolio/${id}`).then(r => r.data);

// Public — no X-Init-Data required (backend does not check it)
const publicApi = axios.create({ baseURL: API_URL });
export const getPublicMasterProfile = (inviteToken) =>
  publicApi.get(`/api/public/master/${inviteToken}`).then(r => r.data);
