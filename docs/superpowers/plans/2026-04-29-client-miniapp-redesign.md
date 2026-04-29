# Client Mini App Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the existing 4-tab client Mini App shell (home/contact/bonuses/promos) with a redesigned 5-screen app (master select + home/history/news/settings) backed by the already-deployed `/api/client/*` endpoints.

**Architecture:** Variant A — targeted file replacement in `miniapp/src/`. New `ClientApp` shell in `App.jsx` with extended `navigate(pageId, params)`. Sub-screens (booking, question, landing) are overlay-style pages inside the same shell without a navigation stack. Shared `OrderCard`, `ReviewModal`, `ContactSheet` components used across tabs.

**Design doc:** `docs/superpowers/plans/2026-04-29-client-miniapp-redesign-design.md`

**Tech Stack:** React 18, @tanstack/react-query, axios, Vite, Telegram Mini App WebApp API

---

## Pre-flight

Before starting, run:
```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
git status --short
npm --prefix miniapp run build
```
Both must pass cleanly. Working tree may have `miniapp/src/theme.css` and `.claude/` dirty — that is expected per AGENT_STATE.

---

## Task 1: VITE env var for client bot username

**Why:** `MasterLanding` needs to build Telegram share links: `https://t.me/{bot}?start=invite_{token}`. The bot username must come from env config, not be hardcoded.

**Files:**
- Modify: `miniapp/.env.production`
- Modify: `miniapp/.env.development`
- Modify: `miniapp/.env.ru`

**Step 1: Get the client bot username from config**
```bash
grep -i "client_bot\|CLIENT_BOT" /Users/evgenijpastusenko/Projects/Master_bot/src/config.py
```
Note the `CLIENT_BOT_TOKEN` owner username — ask the user if uncertain.

**Step 2: Add VITE_CLIENT_BOT_USERNAME to each env file**

Append to each of the three `.env.*` files (same username in all three):
```
VITE_CLIENT_BOT_USERNAME=<actual_bot_username_without_@>
```

**Step 3: Verify build still passes**
```bash
npm --prefix miniapp run build
```
Expected: BUILD SUCCESS, no errors.

**Step 4: Commit**
```bash
git add miniapp/.env.production miniapp/.env.development miniapp/.env.ru
git commit -m "feat(miniapp): add VITE_CLIENT_BOT_USERNAME env var for share links"
```

---

## Task 2: Add API functions to `api/client.js`

**Files:**
- Modify: `miniapp/src/api/client.js` (append after existing exports)

**Step 1: Append the following block at the end of `api/client.js`**

```js
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

// Public — no X-Init-Data required (backend does not check it)
const publicApi = axios.create({ baseURL: API_URL });
export const getPublicMasterProfile = (inviteToken) =>
  publicApi.get(`/api/public/master/${inviteToken}`).then(r => r.data);
```

**Step 2: Verify build**
```bash
npm --prefix miniapp run build
```
Expected: BUILD SUCCESS.

**Step 3: Commit**
```bash
git add miniapp/src/api/client.js
git commit -m "feat(miniapp): add client app v2 API functions"
```

---

## Task 3: i18n keys for new screens

**Files:**
- Modify: `miniapp/src/i18n/dictionaries/ru.js`
- Modify: `miniapp/src/i18n/dictionaries/en.js`

**Step 1: In `ru.js`, update `nav.client` section** (lines ~25-30):

Replace:
```js
nav: {
  client: {
    home: 'Главная',
    contact: 'Связаться',
    bonuses: 'Бонусы',
    promos: 'Акции',
  },
```
With:
```js
nav: {
  client: {
    home: 'Главная',
    history: 'История',
    news: 'Новости',
    settings: 'Настройки',
  },
```

**Step 2: In `ru.js`, update `masterSelect` section** — replace «мастер» with «специалист»:
```js
masterSelect: {
  title: 'Выберите специалиста',
  subtitle: 'Вы подключены к нескольким специалистам',
  bonus: '💎 {amount} бонусов',
  visits: '📋 {count} визитов',
  lastVisit: 'Последний визит: {date}',
},
```

**Step 3: In `ru.js`, add new sections before the closing `};`**

Add after the `contact:` block:
```js
  clientHome: {
    specialist: 'Ваш специалист',
    detailsLink: 'Подробнее',
    bookBtn: 'Записаться',
    questionBtn: 'Задать вопрос',
    activityTitle: 'Активность',
    allHistory: 'Вся история',
    servicesTitle: 'Услуги',
    newsTitle: 'Новости',
    bookService: 'Записаться',
    noActivity: 'Заказов пока нет',
    noServices: 'Услуги не указаны',
    noNews: 'Публикаций пока нет',
    bonusLabel: 'бонусов',
  },

  orderCard: {
    statusNew: 'Новая запись',
    statusReminder: 'Напоминание',
    statusConfirmed: 'Подтверждён',
    statusDone: 'Выполнен',
    statusCancelled: 'Отменён',
    statusMoved: 'Перенесён',
    reviewLeft: 'Отзыв оставлен',
    btnConfirm: 'Подтвердить',
    btnContact: 'Связаться',
    btnReview: 'Оставить отзыв',
    btnRepeat: 'Повторить',
  },

  reviewModal: {
    title: 'Отзыв о визите',
    placeholder: 'Расскажите о вашем опыте...',
    submit: 'Отправить',
    submitting: 'Отправляем...',
    minLengthError: 'Минимум 10 символов',
    successMsg: 'Спасибо за отзыв!',
  },

  contactSheet: {
    title: 'Связаться со специалистом',
    phone: 'Позвонить',
    telegram: 'Написать в Telegram',
  },

  history: {
    title: 'История',
    balanceLabel: 'Баланс',
    bonusSuffix: 'бонусов',
    noBonusDesc: 'Операция',
    loadMore: 'Загрузить ещё',
    empty: 'Записей пока нет',
  },

  news: {
    title: 'Новости',
    tagPromo: 'Акция',
    tagAnnouncement: 'Объявление',
    tagFreeSlot: 'Свободное окно',
    btnBook: 'Записаться',
    btnWantSame: 'Хочу так же',
    empty: 'Публикаций пока нет',
    loadMore: 'Загрузить ещё',
  },

  settings: {
    title: 'Настройки',
    notificationsGroup: 'Уведомления',
    notifyReminders: 'Напоминания о записи',
    notifyRemindersHint: 'За 24 часа до визита',
    notifyMarketing: 'Новости и акции',
    notifyMarketingHint: 'Публикации специалиста',
    notifyBonuses: 'Бонусы',
    notifyBonusesHint: 'Начисления и списания',
    supportGroup: 'Поддержка',
    supportBtn: 'Написать в поддержку',
    aboutGroup: 'О приложении',
    versionLabel: 'Версия',
    privacyBtn: 'Политика конфиденциальности',
    accountGroup: 'Аккаунт',
    deleteProfile: 'Удалить профиль',
    deleteConfirmTitle: 'Удалить профиль?',
    deleteConfirmText: 'Данные будут удалены безвозвратно.',
    deleteConfirmBtn: 'Да, удалить',
    deleteCancelBtn: 'Отмена',
    deleting: 'Удаляем...',
  },

  masterLanding: {
    reviewsMetric: '{count} отзывов',
    yearsMetric: '{count} лет на платформе',
    yearMetric: '1 год на платформе',
    bookBtn: 'Записаться',
    questionBtn: 'Задать вопрос',
    connectBtn: 'Подключиться к специалисту',
    connecting: 'Подключаемся...',
    aboutTitle: 'О специалисте',
    servicesTitle: 'Услуги',
    contactsTitle: 'Контакты',
    workModeTitle: 'Формат работы',
    reviewsTitle: 'Отзывы',
    shareBtn: 'Поделиться специалистом',
    noReviews: 'Отзывов пока нет',
    noServices: 'Услуги не указаны',
  },

  changeSpecialist: 'Сменить специалиста',
```

**Step 4: Make matching changes in `en.js`** — same keys with English values (translate or copy Russian temporarily).

**Step 5: Verify build**
```bash
npm --prefix miniapp run build
```
Expected: BUILD SUCCESS.

**Step 6: Commit**
```bash
git add miniapp/src/i18n/dictionaries/ru.js miniapp/src/i18n/dictionaries/en.js
git commit -m "feat(miniapp): add i18n keys for client app v2 screens"
```

---

## Task 4: CSS classes in `theme.css`

**Files:**
- Modify: `miniapp/src/theme.css` (append new client-v2 section at end of file)

**Step 1: Append the following section at the end of `theme.css`**

```css
/* ── Client App v2 ─────────────────────────────────────────────────────────── */

/* Profile card (Home screen) */
body.typeui-client-body .client-profile-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  background: var(--tg-theme-secondary-bg-color, #1c2230);
  margin-bottom: 8px;
}
body.typeui-client-body .client-profile-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--tg-theme-button-color, #2481cc);
  color: var(--tg-theme-button-text-color, #fff);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  flex-shrink: 0;
  overflow: hidden;
}
body.typeui-client-body .client-profile-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
body.typeui-client-body .client-profile-info {
  flex: 1;
  min-width: 0;
}
body.typeui-client-body .client-profile-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--tg-theme-text-color, #fff);
  margin: 0 0 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
body.typeui-client-body .client-profile-sphere {
  font-size: 13px;
  color: var(--tg-theme-hint-color, #8e99a4);
  margin: 0 0 6px;
}
body.typeui-client-body .client-profile-bio {
  font-size: 13px;
  color: var(--tg-theme-hint-color, #8e99a4);
  margin: 6px 0 4px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
body.typeui-client-body .client-profile-details-link {
  font-size: 13px;
  color: var(--tg-theme-link-color, #2481cc);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  text-decoration: underline;
}
body.typeui-client-body .client-profile-bonus {
  text-align: right;
  flex-shrink: 0;
}
body.typeui-client-body .client-profile-bonus-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--tg-theme-text-color, #fff);
  line-height: 1.1;
}
body.typeui-client-body .client-profile-bonus-label {
  font-size: 11px;
  color: var(--tg-theme-hint-color, #8e99a4);
}

/* Action buttons row */
body.typeui-client-body .client-action-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 8px;
}
body.typeui-client-body .client-action-btn {
  padding: 13px 8px;
  border-radius: 12px;
  border: none;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}
body.typeui-client-body .client-action-btn:active { opacity: 0.75; }
body.typeui-client-body .client-action-btn.is-primary {
  background: #2481cc;
  color: #fff;
}
body.typeui-client-body .client-action-btn.is-secondary {
  background: var(--tg-theme-secondary-bg-color, #1c2230);
  color: var(--tg-theme-text-color, #fff);
}
body.typeui-client-body .client-action-btn.is-full {
  grid-column: 1 / -1;
  background: #2481cc;
  color: #fff;
}

/* Section header with right link */
body.typeui-client-body .client-section-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 16px 0 8px;
}
body.typeui-client-body .client-section-header-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--tg-theme-text-color, #fff);
}
body.typeui-client-body .client-section-header-link {
  font-size: 13px;
  color: var(--tg-theme-link-color, #2481cc);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
}

/* Order card */
body.typeui-client-body .client-order-card {
  border-radius: 12px;
  background: var(--tg-theme-secondary-bg-color, #1c2230);
  border: 1px solid rgba(255,255,255,0.07);
  padding: 12px 14px;
  margin-bottom: 8px;
}
body.typeui-client-body .client-order-card-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
body.typeui-client-body .client-order-card-date {
  font-size: 12px;
  color: var(--tg-theme-hint-color, #8e99a4);
}
body.typeui-client-body .client-order-card-services {
  font-size: 15px;
  font-weight: 600;
  color: var(--tg-theme-text-color, #fff);
  margin: 0 0 6px;
}
body.typeui-client-body .client-order-card-meta {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 10px;
}
body.typeui-client-body .client-order-card-price {
  color: var(--tg-theme-hint-color, #8e99a4);
}
body.typeui-client-body .client-order-card-bonuses {
  color: #4caf50;
  font-weight: 600;
}
body.typeui-client-body .client-order-card-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
body.typeui-client-body .client-order-card-btn {
  flex: 1;
  min-width: 100px;
  padding: 8px 12px;
  border-radius: 8px;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  text-align: center;
}
body.typeui-client-body .client-order-card-btn:active { opacity: 0.75; }
body.typeui-client-body .client-order-card-btn.is-primary {
  background: #2481cc;
  color: #fff;
}
body.typeui-client-body .client-order-card-btn.is-outline {
  background: transparent;
  border: 1px solid rgba(255,255,255,0.2);
  color: var(--tg-theme-text-color, #fff);
}
body.typeui-client-body .client-order-review-left {
  font-size: 13px;
  color: var(--tg-theme-hint-color, #8e99a4);
  font-style: italic;
}

/* Status badge pills */
body.typeui-client-body .client-status-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
body.typeui-client-body .client-status-badge.is-yellow { background: rgba(255,193,7,0.18); color: #ffc107; }
body.typeui-client-body .client-status-badge.is-blue   { background: rgba(36,129,204,0.18); color: #2481cc; }
body.typeui-client-body .client-status-badge.is-green  { background: rgba(76,175,80,0.18); color: #4caf50; }
body.typeui-client-body .client-status-badge.is-grey   { background: rgba(142,153,164,0.12); color: #8e99a4; }
body.typeui-client-body .client-status-badge.is-red    { background: rgba(244,67,54,0.18); color: #f44336; }

/* Services accordion */
body.typeui-client-body .client-accordion-item {
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
body.typeui-client-body .client-accordion-item:last-child { border-bottom: none; }
body.typeui-client-body .client-accordion-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 13px 0;
  background: none;
  border: none;
  color: var(--tg-theme-text-color, #fff);
  cursor: pointer;
  text-align: left;
}
body.typeui-client-body .client-accordion-trigger-name {
  font-size: 15px;
  font-weight: 500;
}
body.typeui-client-body .client-accordion-trigger-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
body.typeui-client-body .client-accordion-trigger-price {
  font-size: 14px;
  color: #2481cc;
}
body.typeui-client-body .client-accordion-chevron {
  font-size: 12px;
  color: var(--tg-theme-hint-color, #8e99a4);
  transition: transform 0.2s;
}
body.typeui-client-body .client-accordion-chevron.is-open { transform: rotate(90deg); }
body.typeui-client-body .client-accordion-body {
  padding: 0 0 12px;
  font-size: 13px;
  color: var(--tg-theme-hint-color, #8e99a4);
  line-height: 1.5;
}

/* Bonus row (history) */
body.typeui-client-body .client-bonus-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(255,255,255,0.04);
  margin-bottom: 6px;
}
body.typeui-client-body .client-bonus-row-left { flex: 1; min-width: 0; }
body.typeui-client-body .client-bonus-row-desc {
  font-size: 14px;
  color: var(--tg-theme-text-color, #fff);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
body.typeui-client-body .client-bonus-row-date {
  font-size: 12px;
  color: var(--tg-theme-hint-color, #8e99a4);
  margin-top: 2px;
}
body.typeui-client-body .client-bonus-row-amount {
  font-size: 15px;
  font-weight: 700;
  flex-shrink: 0;
  margin-left: 12px;
}
body.typeui-client-body .client-bonus-row-amount.is-positive { color: #4caf50; }
body.typeui-client-body .client-bonus-row-amount.is-negative { color: #f44336; }

/* News card */
body.typeui-client-body .client-news-card {
  border-radius: 12px;
  background: var(--tg-theme-secondary-bg-color, #1c2230);
  margin-bottom: 10px;
  overflow: hidden;
}
body.typeui-client-body .client-news-card-image {
  width: 100%;
  display: block;
  max-height: 200px;
  object-fit: cover;
}
body.typeui-client-body .client-news-card-body { padding: 12px 14px; }
body.typeui-client-body .client-news-card-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
body.typeui-client-body .client-news-card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--tg-theme-text-color, #fff);
  margin: 0 0 4px;
}
body.typeui-client-body .client-news-card-text {
  font-size: 14px;
  color: var(--tg-theme-hint-color, #8e99a4);
  line-height: 1.5;
  margin: 0 0 10px;
}
/* News tag colors */
body.typeui-client-body .client-news-tag { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; }
body.typeui-client-body .client-news-tag.is-promo        { background: rgba(255,87,51,0.18); color: #ff5733; }
body.typeui-client-body .client-news-tag.is-announcement { background: rgba(255,193,7,0.18); color: #ffc107; }
body.typeui-client-body .client-news-tag.is-free_slot    { background: rgba(76,175,80,0.18); color: #4caf50; }

/* Settings groups (iOS-style) */
body.typeui-client-body .client-settings-group {
  margin-bottom: 20px;
}
body.typeui-client-body .client-settings-group-label {
  font-size: 13px;
  color: var(--tg-theme-hint-color, #8e99a4);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 6px;
  padding: 0 4px;
}
body.typeui-client-body .client-settings-list {
  border-radius: 12px;
  background: var(--tg-theme-secondary-bg-color, #1c2230);
  overflow: hidden;
}
body.typeui-client-body .client-settings-row {
  display: flex;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
body.typeui-client-body .client-settings-row:last-child { border-bottom: none; }
body.typeui-client-body .client-settings-row-copy { flex: 1; }
body.typeui-client-body .client-settings-row-title {
  font-size: 15px;
  color: var(--tg-theme-text-color, #fff);
}
body.typeui-client-body .client-settings-row-hint {
  font-size: 12px;
  color: var(--tg-theme-hint-color, #8e99a4);
  margin-top: 2px;
}
body.typeui-client-body .client-settings-row-value {
  font-size: 14px;
  color: var(--tg-theme-hint-color, #8e99a4);
}
body.typeui-client-body .client-settings-row.is-danger .client-settings-row-title {
  color: #f44336;
}
body.typeui-client-body .client-settings-row.is-link {
  cursor: pointer;
}
/* Toggle switch */
body.typeui-client-body .client-toggle {
  position: relative;
  width: 50px;
  height: 28px;
  flex-shrink: 0;
}
body.typeui-client-body .client-toggle input { opacity: 0; width: 0; height: 0; position: absolute; }
body.typeui-client-body .client-toggle-track {
  position: absolute; inset: 0;
  border-radius: 999px;
  background: rgba(255,255,255,0.12);
  transition: background 0.2s;
  cursor: pointer;
}
body.typeui-client-body .client-toggle input:checked + .client-toggle-track {
  background: #4caf50;
}
body.typeui-client-body .client-toggle-thumb {
  position: absolute;
  top: 3px; left: 3px;
  width: 22px; height: 22px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.2s;
  pointer-events: none;
}
body.typeui-client-body .client-toggle input:checked ~ .client-toggle-thumb {
  transform: translateX(22px);
}

/* Bottom sheet */
body.typeui-client-body .client-sheet-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.55);
  z-index: 200;
  display: flex;
  align-items: flex-end;
}
body.typeui-client-body .client-sheet {
  width: 100%;
  background: var(--tg-theme-secondary-bg-color, #1c2230);
  border-radius: 16px 16px 0 0;
  padding: 20px 16px calc(16px + env(safe-area-inset-bottom));
  animation: slideUp 0.25s ease;
}
@keyframes slideUp {
  from { transform: translateY(100%); }
  to   { transform: translateY(0); }
}
body.typeui-client-body .client-sheet-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--tg-theme-text-color, #fff);
  margin-bottom: 14px;
  text-align: center;
}
body.typeui-client-body .client-sheet-btn {
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  border: none;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 10px;
  background: var(--tg-theme-button-color, #2481cc);
  color: var(--tg-theme-button-text-color, #fff);
}
body.typeui-client-body .client-sheet-btn.is-secondary {
  background: rgba(255,255,255,0.08);
  color: var(--tg-theme-text-color, #fff);
}

/* Master landing */
body.typeui-client-body .client-landing-hero {
  text-align: center;
  padding: 24px 16px 16px;
}
body.typeui-client-body .client-landing-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--tg-theme-button-color, #2481cc);
  color: var(--tg-theme-button-text-color, #fff);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  margin: 0 auto 12px;
  overflow: hidden;
}
body.typeui-client-body .client-landing-avatar img { width: 100%; height: 100%; object-fit: cover; }
body.typeui-client-body .client-landing-name {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 4px;
}
body.typeui-client-body .client-landing-sphere {
  font-size: 14px;
  color: var(--tg-theme-hint-color, #8e99a4);
  margin-bottom: 8px;
}
body.typeui-client-body .client-landing-metrics {
  font-size: 13px;
  color: var(--tg-theme-hint-color, #8e99a4);
}

/* Change specialist button in header */
body.typeui-client-body .client-header-specialist-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  color: var(--tg-theme-text-color, #fff);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  max-width: 180px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
body.typeui-client-body .client-header-specialist-btn svg {
  flex-shrink: 0;
  color: var(--tg-theme-hint-color, #8e99a4);
}

/* Confirmation dialog */
body.typeui-client-body .client-confirm-dialog {
  padding: 24px 16px 16px;
  text-align: center;
}
body.typeui-client-body .client-confirm-dialog-title {
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 8px;
}
body.typeui-client-body .client-confirm-dialog-text {
  font-size: 14px;
  color: var(--tg-theme-hint-color, #8e99a4);
  margin-bottom: 20px;
  line-height: 1.5;
}

/* Lazy load trigger */
body.typeui-client-body .client-load-more-trigger {
  height: 1px;
  width: 100%;
}

/* Page header with specialist switcher */
body.typeui-client-body .client-tab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px 8px;
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--tg-theme-bg-color, #0b1622);
}
```

**Step 2: Verify build**
```bash
npm --prefix miniapp run build
```
Expected: BUILD SUCCESS.

**Step 3: Commit**
```bash
git add miniapp/src/theme.css
git commit -m "feat(miniapp): add client app v2 CSS classes to theme.css"
```

---

## Task 5: Create `components/OrderCard.jsx`

**Files:**
- Create: `miniapp/src/components/OrderCard.jsx`

**Step 1: Create the file**

```jsx
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;
function haptic(t = 'light') {
  WebApp?.HapticFeedback?.impactOccurred(t);
}

function formatDate(dateStr, locale) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d)) return '';
  return d.toLocaleString(locale, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' });
}

const STATUS_BADGE = {
  new:       { label: 'orderCard.statusNew',       cls: 'is-yellow' },
  reminder:  { label: 'orderCard.statusReminder',  cls: 'is-yellow' },
  confirmed: { label: 'orderCard.statusConfirmed', cls: 'is-blue'   },
  done:      { label: 'orderCard.statusDone',      cls: 'is-green'  },
  cancelled: { label: 'orderCard.statusCancelled', cls: 'is-red'    },
  moved:     { label: 'orderCard.statusMoved',     cls: 'is-grey'   },
};

export default function OrderCard({ order, onConfirm, onReview, onRepeat, onContact }) {
  const { t, locale } = useI18n();
  const ds = order.display_status || 'new';
  const badge = STATUS_BADGE[ds] || STATUS_BADGE.new;

  const buttons = [];

  if (ds === 'reminder') {
    buttons.push(
      <button key="confirm" className="client-order-card-btn is-primary"
        onClick={() => { haptic(); onConfirm?.(order.id); }}>
        {t('orderCard.btnConfirm')}
      </button>
    );
  }

  if (ds === 'done') {
    if (!order.has_review) {
      buttons.push(
        <button key="review" className="client-order-card-btn is-primary"
          onClick={() => { haptic(); onReview?.(order); }}>
          {t('orderCard.btnReview')}
        </button>
      );
      buttons.push(
        <button key="repeat" className="client-order-card-btn is-outline"
          onClick={() => { haptic(); onRepeat?.(order); }}>
          {t('orderCard.btnRepeat')}
        </button>
      );
    }
  }

  const showContact = ['new', 'reminder', 'confirmed'].includes(ds);
  if (showContact) {
    buttons.push(
      <button key="contact" className="client-order-card-btn is-outline"
        onClick={() => { haptic(); onContact?.(order); }}>
        {t('orderCard.btnContact')}
      </button>
    );
  }

  const currency = order.currency || '₽';
  const price = order.price != null ? `${order.price} ${currency}` : null;
  const bonuses = order.bonuses_earned ? `+${order.bonuses_earned}` : null;

  return (
    <div className="client-order-card">
      <div className="client-order-card-topline">
        <span className={`client-status-badge ${badge.cls}`}>{t(badge.label)}</span>
        <span className="client-order-card-date">
          {formatDate(order.scheduled_at, locale)}
        </span>
      </div>

      <p className="client-order-card-services">
        {order.services || order.service_name || '—'}
      </p>

      {(price || bonuses) && (
        <div className="client-order-card-meta">
          <span className="client-order-card-price">{price}</span>
          {bonuses && <span className="client-order-card-bonuses">{bonuses}</span>}
        </div>
      )}

      {ds === 'done' && order.has_review && (
        <p className="client-order-review-left">{t('orderCard.reviewLeft')}</p>
      )}

      {buttons.length > 0 && (
        <div className="client-order-card-actions">{buttons}</div>
      )}
    </div>
  );
}
```

**Step 2: Verify build**
```bash
npm --prefix miniapp run build
```
Expected: BUILD SUCCESS.

**Step 3: Commit**
```bash
git add miniapp/src/components/OrderCard.jsx
git commit -m "feat(miniapp): add OrderCard component for client app v2"
```

---

## Task 6: Create `components/ReviewModal.jsx`

**Files:**
- Create: `miniapp/src/components/ReviewModal.jsx`

**Step 1: Create the file**

```jsx
import { useState } from 'react';
import { createClientOrderReview } from '../api/client';
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;

function formatDate(dateStr, locale) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d)) return '';
  return d.toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' });
}

export default function ReviewModal({ order, onClose, onSuccess }) {
  const { t, locale } = useI18n();
  const [text, setText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (text.trim().length < 10) {
      setError(t('reviewModal.minLengthError'));
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      await createClientOrderReview(order.id, { text: text.trim() });
      WebApp?.HapticFeedback?.notificationOccurred('success');
      onSuccess?.(order.id);
      onClose?.();
    } catch {
      setError(t('reviewModal.minLengthError'));
      WebApp?.HapticFeedback?.notificationOccurred('error');
    } finally {
      setSubmitting(false);
    }
  };

  const subtitle = [order.services || order.service_name, formatDate(order.scheduled_at, locale)]
    .filter(Boolean).join(' · ');

  return (
    <div className="client-sheet-overlay" onClick={onClose}>
      <div className="client-sheet" onClick={e => e.stopPropagation()}>
        <p className="client-sheet-title">{t('reviewModal.title')}</p>
        {subtitle && (
          <p style={{ fontSize: 13, color: 'var(--tg-theme-hint-color)', marginBottom: 12, textAlign: 'center' }}>
            {subtitle}
          </p>
        )}
        <textarea
          value={text}
          onChange={e => { setText(e.target.value); setError(''); }}
          placeholder={t('reviewModal.placeholder')}
          rows={4}
          style={{
            width: '100%', background: 'rgba(255,255,255,0.06)', border: 'none',
            borderRadius: 12, padding: '12px 14px', color: 'var(--tg-theme-text-color)',
            fontSize: 15, resize: 'none', fontFamily: 'inherit', outline: 'none',
            boxSizing: 'border-box', marginBottom: error ? 6 : 12,
          }}
        />
        {error && (
          <p style={{ fontSize: 13, color: '#f44336', marginBottom: 10 }}>{error}</p>
        )}
        <button
          className="client-sheet-btn"
          onClick={handleSubmit}
          disabled={submitting}
          style={{ opacity: submitting ? 0.7 : 1 }}
        >
          {submitting ? t('reviewModal.submitting') : t('reviewModal.submit')}
        </button>
        <button className="client-sheet-btn is-secondary" onClick={onClose}>
          {t('common.cancel')}
        </button>
      </div>
    </div>
  );
}
```

**Step 2: Verify build**
```bash
npm --prefix miniapp run build
```

**Step 3: Commit**
```bash
git add miniapp/src/components/ReviewModal.jsx
git commit -m "feat(miniapp): add ReviewModal component"
```

---

## Task 7: Create `components/ContactSheet.jsx`

**Files:**
- Create: `miniapp/src/components/ContactSheet.jsx`

**Step 1: Create the file**

```jsx
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;

export default function ContactSheet({ master, onClose }) {
  const { t } = useI18n();
  const phone = master?.phone || master?.contacts;
  const telegram = master?.telegram;

  const handlePhone = () => {
    WebApp?.HapticFeedback?.impactOccurred('light');
    if (phone) window.open(`tel:${phone.replace(/\s/g, '')}`, '_blank');
  };

  const handleTelegram = () => {
    WebApp?.HapticFeedback?.impactOccurred('light');
    if (telegram) {
      const username = telegram.replace(/^@/, '');
      window.open(`tg://resolve?domain=${username}`, '_blank');
    }
  };

  return (
    <div className="client-sheet-overlay" onClick={onClose}>
      <div className="client-sheet" onClick={e => e.stopPropagation()}>
        <p className="client-sheet-title">{t('contactSheet.title')}</p>
        {phone && (
          <button className="client-sheet-btn" onClick={handlePhone}>
            📞 {t('contactSheet.phone')}
          </button>
        )}
        {telegram && (
          <button className="client-sheet-btn is-secondary" onClick={handleTelegram}>
            ✈️ {t('contactSheet.telegram')}
          </button>
        )}
        <button className="client-sheet-btn is-secondary" onClick={onClose}>
          {t('common.cancel')}
        </button>
      </div>
    </div>
  );
}
```

**Step 2: Verify build + commit**
```bash
npm --prefix miniapp run build
git add miniapp/src/components/ContactSheet.jsx
git commit -m "feat(miniapp): add ContactSheet component"
```

---

## Task 8: Rewrite `pages/Home.jsx`

**Files:**
- Modify (full rewrite): `miniapp/src/pages/Home.jsx`

**Step 1: Replace the entire file with:**

```jsx
import { useState } from 'react';
import { useQueries, useQueryClient } from '@tanstack/react-query';
import {
  getClientMasterProfile,
  getClientMasterActivity,
  getClientMasterServices,
  getClientMasterNews,
  confirmClientOrder,
} from '../api/client';
import { Skeleton } from '../components/Skeleton';
import OrderCard from '../components/OrderCard';
import ReviewModal from '../components/ReviewModal';
import ContactSheet from '../components/ContactSheet';
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;
function haptic(t = 'light') { WebApp?.HapticFeedback?.impactOccurred(t); }

function Accordion({ services, onBook }) {
  const { t } = useI18n();
  const [openId, setOpenId] = useState(null);
  if (!services.length) return <p style={{ color: 'var(--tg-theme-hint-color)', fontSize: 14 }}>{t('clientHome.noServices')}</p>;
  return (
    <div className="client-card" style={{ padding: '0 14px' }}>
      {services.map(s => (
        <div key={s.id} className="client-accordion-item">
          <button className="client-accordion-trigger" onClick={() => { haptic(); setOpenId(openId === s.id ? null : s.id); }}>
            <span className="client-accordion-trigger-name">{s.name}</span>
            <span className="client-accordion-trigger-right">
              {s.price != null && <span className="client-accordion-trigger-price">{s.price} ₽</span>}
              <span className={`client-accordion-chevron${openId === s.id ? ' is-open' : ''}`}>▸</span>
            </span>
          </button>
          {openId === s.id && (
            <div className="client-accordion-body">
              {s.description && <p style={{ marginBottom: 8 }}>{s.description}</p>}
              <button className="client-order-card-btn is-primary" onClick={() => { haptic(); onBook(s); }}>
                {t('clientHome.bookService')}
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function Home({ activeMasterId, navigate, masterName }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [reviewOrder, setReviewOrder] = useState(null);
  const [contactOrder, setContactOrder] = useState(null);
  const [profile, setProfile] = useState(null);

  const results = useQueries({
    queries: [
      { queryKey: ['client-profile', activeMasterId], queryFn: () => getClientMasterProfile(activeMasterId), enabled: !!activeMasterId },
      { queryKey: ['client-activity', activeMasterId], queryFn: () => getClientMasterActivity(activeMasterId, 3), enabled: !!activeMasterId },
      { queryKey: ['client-services', activeMasterId], queryFn: () => getClientMasterServices(activeMasterId), enabled: !!activeMasterId },
      { queryKey: ['client-news', activeMasterId], queryFn: () => getClientMasterNews(activeMasterId), enabled: !!activeMasterId },
    ],
  });

  const [profRes, actRes, svcRes, newsRes] = results;
  const prof = profRes.data;
  const activity = actRes.data?.items || [];
  const services = svcRes.data?.services || [];
  const news = newsRes.data?.publications?.[0] || null;

  // keep profile for ContactSheet
  if (prof && prof !== profile) setProfile(prof);

  const handleConfirm = async (orderId) => {
    try {
      await confirmClientOrder(orderId);
      qc.invalidateQueries({ queryKey: ['client-activity', activeMasterId] });
      WebApp?.HapticFeedback?.notificationOccurred('success');
    } catch { WebApp?.HapticFeedback?.notificationOccurred('error'); }
  };

  const handleRepeat = (order) => {
    const service = order.services ? { name: order.services } : null;
    navigate('create_order', service ? { service } : {});
  };

  const avatarContent = prof?.photo_url
    ? <img src={prof.photo_url} alt="" />
    : (prof?.name || masterName || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();

  return (
    <div className="client-page" style={{ padding: '0 16px 120px' }}>
      {/* Specialist header */}
      <div className="client-profile-card" style={{ marginTop: 12 }}>
        <div className="client-profile-avatar">{avatarContent}</div>
        <div className="client-profile-info">
          {profRes.isLoading ? <Skeleton width={140} height={20} /> : (
            <p className="client-profile-name">{prof?.name || masterName || '—'}</p>
          )}
          {prof?.sphere && <p className="client-profile-sphere">{prof.sphere}</p>}
          {prof?.bio && <p className="client-profile-bio">{prof.bio}</p>}
          <button className="client-profile-details-link"
            onClick={() => { haptic(); navigate('landing', { masterId: activeMasterId }); }}>
            {t('clientHome.detailsLink')}
          </button>
        </div>
        <div className="client-profile-bonus">
          {profRes.isLoading ? <Skeleton width={40} height={24} /> : (
            <>
              <div className="client-profile-bonus-value">{prof?.bonus_balance ?? 0}</div>
              <div className="client-profile-bonus-label">{t('clientHome.bonusLabel')}</div>
            </>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="client-action-grid">
        <button className="client-action-btn is-primary" onClick={() => { haptic(); navigate('create_order'); }}>
          {t('clientHome.bookBtn')}
        </button>
        <button className="client-action-btn is-secondary" onClick={() => { haptic(); navigate('ask_question'); }}>
          {t('clientHome.questionBtn')}
        </button>
      </div>

      {/* Activity */}
      <div className="client-section-header">
        <span className="client-section-header-title">{t('clientHome.activityTitle')}</span>
        <button className="client-section-header-link" onClick={() => { haptic(); navigate('history'); }}>
          {t('clientHome.allHistory')}
        </button>
      </div>
      {actRes.isLoading ? (
        <><Skeleton height={80} style={{ marginBottom: 8 }} /><Skeleton height={80} /></>
      ) : activity.length === 0 ? (
        <p style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)' }}>{t('clientHome.noActivity')}</p>
      ) : activity.map(order => (
        <OrderCard key={order.id} order={order}
          onConfirm={handleConfirm}
          onReview={o => setReviewOrder(o)}
          onRepeat={handleRepeat}
          onContact={o => setContactOrder(o)}
        />
      ))}

      {/* Services */}
      <div className="client-section-header" style={{ marginTop: 8 }}>
        <span className="client-section-header-title">{t('clientHome.servicesTitle')}</span>
      </div>
      {svcRes.isLoading ? <Skeleton height={50} /> : (
        <Accordion services={services} onBook={s => navigate('create_order', { service: s })} />
      )}

      {/* News preview */}
      {(newsRes.isLoading || news) && (
        <>
          <div className="client-section-header" style={{ marginTop: 8 }}>
            <span className="client-section-header-title">{t('clientHome.newsTitle')}</span>
          </div>
          {newsRes.isLoading ? <Skeleton height={60} /> : news && (
            <div className="client-card" style={{ padding: 14, cursor: 'pointer' }}
              onClick={() => { haptic(); navigate('news'); }}>
              <p style={{ fontSize: 12, color: 'var(--tg-theme-hint-color)', marginBottom: 4 }}>
                {new Date(news.created_at).toLocaleDateString('ru', { day: 'numeric', month: 'long' })}
              </p>
              <p style={{ fontSize: 14, color: 'var(--tg-theme-text-color)', lineHeight: 1.4 }}>
                {news.text?.slice(0, 120)}{news.text?.length > 120 ? '…' : ''}
              </p>
            </div>
          )}
        </>
      )}

      {reviewOrder && (
        <ReviewModal
          order={reviewOrder}
          onClose={() => setReviewOrder(null)}
          onSuccess={() => {
            qc.invalidateQueries({ queryKey: ['client-activity', activeMasterId] });
            setReviewOrder(null);
          }}
        />
      )}
      {contactOrder && (
        <ContactSheet master={profile} onClose={() => setContactOrder(null)} />
      )}
    </div>
  );
}
```

**Step 2: Verify build**
```bash
npm --prefix miniapp run build
```
Expected: BUILD SUCCESS.

**Step 3: Commit**
```bash
git add miniapp/src/pages/Home.jsx
git commit -m "feat(miniapp): rewrite client Home screen for v2 design"
```

---

## Task 9: Create `pages/History.jsx`

**Files:**
- Create: `miniapp/src/pages/History.jsx`

**Step 1: Create the file**

```jsx
import { useState, useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getClientMasterHistory, confirmClientOrder } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import OrderCard from '../components/OrderCard';
import ReviewModal from '../components/ReviewModal';
import ContactSheet from '../components/ContactSheet';
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;
const PAGE = 20;

export default function History({ activeMasterId, navigate, masterProfile }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [items, setItems] = useState([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [bonusBalance, setBonusBalance] = useState(null);
  const [reviewOrder, setReviewOrder] = useState(null);
  const [contactMaster, setContactMaster] = useState(null);
  const triggerRef = useRef(null);

  const loadPage = useCallback(async (off) => {
    if (!activeMasterId) return;
    setLoading(true);
    try {
      const data = await getClientMasterHistory(activeMasterId, PAGE, off);
      if (off === 0) setBonusBalance(data.bonus_balance ?? null);
      setItems(prev => off === 0 ? (data.items || []) : [...prev, ...(data.items || [])]);
      setHasMore((data.items || []).length >= PAGE);
    } finally {
      setLoading(false);
    }
  }, [activeMasterId]);

  useEffect(() => { setOffset(0); loadPage(0); }, [loadPage]);

  // Intersection observer for lazy load
  useEffect(() => {
    if (!triggerRef.current || !hasMore || loading) return;
    const obs = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) {
        setOffset(prev => { const next = prev + PAGE; loadPage(next); return next; });
      }
    }, { threshold: 0.1 });
    obs.observe(triggerRef.current);
    return () => obs.disconnect();
  }, [hasMore, loading, loadPage]);

  const handleConfirm = async (orderId) => {
    try {
      await confirmClientOrder(orderId);
      qc.invalidateQueries({ queryKey: ['client-activity', activeMasterId] });
      setItems(prev => prev.map(item =>
        item.id === orderId && item.type === 'order'
          ? { ...item, display_status: 'confirmed', client_confirmed: true }
          : item
      ));
      WebApp?.HapticFeedback?.notificationOccurred('success');
    } catch { WebApp?.HapticFeedback?.notificationOccurred('error'); }
  };

  const handleRepeat = (order) => {
    const service = order.services ? { name: order.services } : null;
    navigate('create_order', service ? { service } : {});
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('ru', { day: 'numeric', month: 'long' });
  };

  return (
    <div className="client-page" style={{ padding: '0 16px 120px' }}>
      <div className="client-tab-header">
        <span className="client-page-title">{t('history.title')}</span>
        {bonusBalance !== null && (
          <span style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)' }}>
            {t('history.balanceLabel')}: <strong style={{ color: 'var(--tg-theme-text-color)' }}>{bonusBalance}</strong> {t('history.bonusSuffix')}
          </span>
        )}
      </div>

      {loading && items.length === 0 ? (
        <><Skeleton height={90} style={{ marginBottom: 8 }} /><Skeleton height={90} /></>
      ) : items.length === 0 ? (
        <p style={{ textAlign: 'center', color: 'var(--tg-theme-hint-color)', marginTop: 40 }}>{t('history.empty')}</p>
      ) : (
        <>
          {items.map((item, i) => item.type === 'order' ? (
            <OrderCard key={`${item.type}-${item.id}-${i}`} order={item}
              onConfirm={handleConfirm}
              onReview={o => setReviewOrder(o)}
              onRepeat={handleRepeat}
              onContact={() => setContactMaster(masterProfile)}
            />
          ) : (
            <div key={`bonus-${item.id}-${i}`} className="client-bonus-row">
              <div className="client-bonus-row-left">
                <div className="client-bonus-row-desc">{item.comment || t('history.noBonusDesc')}</div>
                <div className="client-bonus-row-date">{formatDate(item.created_at)}</div>
              </div>
              <div className={`client-bonus-row-amount ${item.amount > 0 ? 'is-positive' : 'is-negative'}`}>
                {item.amount > 0 ? '+' : ''}{item.amount}
              </div>
            </div>
          ))}
          {loading && <Skeleton height={60} style={{ marginTop: 8 }} />}
          <div ref={triggerRef} className="client-load-more-trigger" />
        </>
      )}

      {reviewOrder && (
        <ReviewModal order={reviewOrder} onClose={() => setReviewOrder(null)}
          onSuccess={(orderId) => {
            setItems(prev => prev.map(item =>
              item.id === orderId && item.type === 'order' ? { ...item, has_review: true } : item
            ));
            setReviewOrder(null);
          }}
        />
      )}
      {contactMaster && (
        <ContactSheet master={contactMaster} onClose={() => setContactMaster(null)} />
      )}
    </div>
  );
}
```

**Step 2: Verify build + commit**
```bash
npm --prefix miniapp run build
git add miniapp/src/pages/History.jsx
git commit -m "feat(miniapp): add History tab screen"
```

---

## Task 10: Create `pages/News.jsx`

**Files:**
- Create: `miniapp/src/pages/News.jsx`

**Step 1: Create the file**

```jsx
import { useState, useEffect, useRef, useCallback } from 'react';
import { getClientMasterPublications } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;
function haptic() { WebApp?.HapticFeedback?.impactOccurred('light'); }
const PAGE = 20;

const TAG_CONFIG = {
  promo:        { key: 'news.tagPromo',        cls: 'is-promo' },
  announcement: { key: 'news.tagAnnouncement', cls: 'is-announcement' },
  free_slot:    { key: 'news.tagFreeSlot',     cls: 'is-free_slot' },
};

export default function News({ activeMasterId, navigate }) {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const triggerRef = useRef(null);

  const loadPage = useCallback(async (off) => {
    if (!activeMasterId) return;
    setLoading(true);
    try {
      const data = await getClientMasterPublications(activeMasterId, PAGE, off);
      const pubs = data.publications || [];
      setItems(prev => off === 0 ? pubs : [...prev, ...pubs]);
      setHasMore(pubs.length >= PAGE);
    } finally {
      setLoading(false);
    }
  }, [activeMasterId]);

  useEffect(() => { setOffset(0); loadPage(0); }, [loadPage]);

  useEffect(() => {
    if (!triggerRef.current || !hasMore || loading) return;
    const obs = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) {
        setOffset(prev => { const next = prev + PAGE; loadPage(next); return next; });
      }
    }, { threshold: 0.1 });
    obs.observe(triggerRef.current);
    return () => obs.disconnect();
  }, [hasMore, loading, loadPage]);

  const renderButton = (pub) => {
    if (pub.type === 'promo' || pub.type === 'free_slot') {
      return (
        <button className="client-order-card-btn is-primary" style={{ marginTop: 8 }}
          onClick={() => { haptic(); navigate('create_order'); }}>
          {t('news.btnBook')}
        </button>
      );
    }
    if (pub.type === 'portfolio') {
      return (
        <button className="client-order-card-btn is-outline" style={{ marginTop: 8 }}
          onClick={() => { haptic(); navigate('create_order'); }}>
          {t('news.btnWantSame')}
        </button>
      );
    }
    return null;
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('ru', { day: 'numeric', month: 'long', year: 'numeric' });
  };

  return (
    <div className="client-page" style={{ padding: '0 16px 120px' }}>
      <div className="client-tab-header">
        <span className="client-page-title">{t('news.title')}</span>
      </div>

      {loading && items.length === 0 ? (
        <><Skeleton height={100} style={{ marginBottom: 10 }} /><Skeleton height={100} /></>
      ) : items.length === 0 ? (
        <p style={{ textAlign: 'center', color: 'var(--tg-theme-hint-color)', marginTop: 40 }}>{t('news.empty')}</p>
      ) : (
        <>
          {items.map((pub, i) => {
            const tag = TAG_CONFIG[pub.type];
            return (
              <div key={`${pub.id}-${i}`} className="client-news-card">
                {pub.image_url && <img className="client-news-card-image" src={pub.image_url} alt="" />}
                <div className="client-news-card-body">
                  <div className="client-news-card-topline">
                    {tag && <span className={`client-news-tag ${tag.cls}`}>{t(tag.key)}</span>}
                    <span style={{ fontSize: 12, color: 'var(--tg-theme-hint-color)' }}>{formatDate(pub.created_at)}</span>
                  </div>
                  {pub.title && <p className="client-news-card-title">{pub.title}</p>}
                  {pub.text && <p className="client-news-card-text">{pub.text}</p>}
                  {renderButton(pub)}
                </div>
              </div>
            );
          })}
          {loading && <Skeleton height={60} style={{ marginTop: 8 }} />}
          <div ref={triggerRef} className="client-load-more-trigger" />
        </>
      )}
    </div>
  );
}
```

**Step 2: Verify build + commit**
```bash
npm --prefix miniapp run build
git add miniapp/src/pages/News.jsx
git commit -m "feat(miniapp): add News tab screen"
```

---

## Task 11: Create `pages/Settings.jsx`

**Files:**
- Create: `miniapp/src/pages/Settings.jsx`

**Step 1: Create the file**

```jsx
import { useState, useEffect } from 'react';
import { getClientMasterSettings, patchClientMasterSettings, deleteClientProfile } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;
const APP_VERSION = import.meta.env.VITE_APP_VERSION || '1.0.0';
const SUPPORT_TG = import.meta.env.VITE_SUPPORT_TG || 'crmfit_support';
const PRIVACY_URL = import.meta.env.VITE_PRIVACY_URL || 'https://crmfit.ru/privacy';

function Toggle({ checked, onChange, disabled }) {
  return (
    <label className="client-toggle">
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} disabled={disabled} />
      <span className="client-toggle-track" />
      <span className="client-toggle-thumb" />
    </label>
  );
}

export default function Settings({ activeMasterId, onProfileDeleted }) {
  const { t } = useI18n();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(null); // key of field being saved
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!activeMasterId) return;
    getClientMasterSettings(activeMasterId)
      .then(data => setSettings(data))
      .finally(() => setLoading(false));
  }, [activeMasterId]);

  const handleToggle = async (key, value) => {
    WebApp?.HapticFeedback?.impactOccurred('light');
    setSettings(prev => ({ ...prev, [key]: value }));
    setSaving(key);
    try {
      await patchClientMasterSettings(activeMasterId, { [key]: value });
    } catch {
      // Revert on error
      setSettings(prev => ({ ...prev, [key]: !value }));
      WebApp?.HapticFeedback?.notificationOccurred('error');
    } finally {
      setSaving(null);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteClientProfile();
      WebApp?.HapticFeedback?.notificationOccurred('success');
      onProfileDeleted?.();
    } catch {
      WebApp?.HapticFeedback?.notificationOccurred('error');
    } finally {
      setDeleting(false);
    }
  };

  if (confirmDelete) {
    return (
      <div className="client-page" style={{ padding: '0 16px 120px' }}>
        <div className="client-tab-header">
          <span className="client-page-title">{t('settings.title')}</span>
        </div>
        <div className="client-confirm-dialog">
          <p className="client-confirm-dialog-title">{t('settings.deleteConfirmTitle')}</p>
          <p className="client-confirm-dialog-text">{t('settings.deleteConfirmText')}</p>
          <button className="client-action-btn is-primary" style={{ width: '100%', marginBottom: 10, background: '#f44336' }}
            onClick={handleDelete} disabled={deleting}>
            {deleting ? t('settings.deleting') : t('settings.deleteConfirmBtn')}
          </button>
          <button className="client-action-btn is-secondary" style={{ width: '100%' }}
            onClick={() => setConfirmDelete(false)}>
            {t('settings.deleteCancelBtn')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="client-page" style={{ padding: '0 16px 120px' }}>
      <div className="client-tab-header">
        <span className="client-page-title">{t('settings.title')}</span>
      </div>

      {loading ? (
        <><Skeleton height={140} style={{ marginBottom: 16, borderRadius: 12 }} /></>
      ) : (
        <>
          {/* Notifications */}
          <div className="client-settings-group">
            <p className="client-settings-group-label">{t('settings.notificationsGroup')}</p>
            <div className="client-settings-list">
              {[
                { key: 'notify_reminders', titleKey: 'settings.notifyReminders', hintKey: 'settings.notifyRemindersHint' },
                { key: 'notify_marketing', titleKey: 'settings.notifyMarketing', hintKey: 'settings.notifyMarketingHint' },
                { key: 'notify_bonuses',   titleKey: 'settings.notifyBonuses',   hintKey: 'settings.notifyBonusesHint' },
              ].map(({ key, titleKey, hintKey }) => (
                <div key={key} className="client-settings-row">
                  <div className="client-settings-row-copy">
                    <div className="client-settings-row-title">{t(titleKey)}</div>
                    <div className="client-settings-row-hint">{t(hintKey)}</div>
                  </div>
                  <Toggle
                    checked={!!settings?.[key]}
                    onChange={v => handleToggle(key, v)}
                    disabled={saving === key}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Support */}
          <div className="client-settings-group">
            <p className="client-settings-group-label">{t('settings.supportGroup')}</p>
            <div className="client-settings-list">
              <button className="client-settings-row is-link" style={{ width: '100%', textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer' }}
                onClick={() => window.open(`tg://resolve?domain=${SUPPORT_TG}`, '_blank')}>
                <div className="client-settings-row-copy">
                  <div className="client-settings-row-title">{t('settings.supportBtn')}</div>
                </div>
                <span style={{ color: 'var(--tg-theme-hint-color)' }}>›</span>
              </button>
            </div>
          </div>

          {/* About */}
          <div className="client-settings-group">
            <p className="client-settings-group-label">{t('settings.aboutGroup')}</p>
            <div className="client-settings-list">
              <div className="client-settings-row">
                <div className="client-settings-row-copy">
                  <div className="client-settings-row-title">{t('settings.versionLabel')}</div>
                </div>
                <span className="client-settings-row-value">{APP_VERSION}</span>
              </div>
              <button className="client-settings-row is-link" style={{ width: '100%', textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer' }}
                onClick={() => window.open(PRIVACY_URL, '_blank')}>
                <div className="client-settings-row-copy">
                  <div className="client-settings-row-title">{t('settings.privacyBtn')}</div>
                </div>
                <span style={{ color: 'var(--tg-theme-hint-color)' }}>›</span>
              </button>
            </div>
          </div>

          {/* Account */}
          <div className="client-settings-group">
            <p className="client-settings-group-label">{t('settings.accountGroup')}</p>
            <div className="client-settings-list">
              <button className="client-settings-row is-danger is-link" style={{ width: '100%', textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer' }}
                onClick={() => setConfirmDelete(true)}>
                <div className="client-settings-row-copy">
                  <div className="client-settings-row-title">{t('settings.deleteProfile')}</div>
                </div>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
```

**Step 2: Verify build + commit**
```bash
npm --prefix miniapp run build
git add miniapp/src/pages/Settings.jsx
git commit -m "feat(miniapp): add Settings tab screen"
```

---

## Task 12: Create `pages/MasterLanding.jsx`

**Files:**
- Create: `miniapp/src/pages/MasterLanding.jsx`

**Step 1: Create the file**

```jsx
import { useState, useEffect } from 'react';
import {
  getClientMasterProfile,
  getClientMasterReviews,
  getPublicMasterProfile,
  linkToMaster,
} from '../api/client';
import { Skeleton } from '../components/Skeleton';
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;
function haptic() { WebApp?.HapticFeedback?.impactOccurred('light'); }

const CLIENT_BOT = import.meta.env.VITE_CLIENT_BOT_USERNAME || '';

export default function MasterLanding({ mode, masterId, inviteToken, navigate, onLinked }) {
  const { t } = useI18n();
  const [profile, setProfile] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        if (mode === 'public' && inviteToken) {
          const data = await getPublicMasterProfile(inviteToken);
          setProfile(data);
          setReviews(data.reviews || []);
        } else if (mode === 'private' && masterId) {
          const [prof, rev] = await Promise.all([
            getClientMasterProfile(masterId),
            getClientMasterReviews(masterId, 10, 0),
          ]);
          setProfile(prof);
          setReviews(rev.reviews || []);
        }
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [mode, masterId, inviteToken]);

  const handleConnect = async () => {
    haptic();
    setLinking(true);
    try {
      await linkToMaster(inviteToken);
    } catch (e) {
      if (e?.response?.status !== 409) {
        WebApp?.HapticFeedback?.notificationOccurred('error');
        setLinking(false);
        return;
      }
    }
    WebApp?.HapticFeedback?.notificationOccurred('success');
    onLinked?.();
  };

  const handleShare = () => {
    haptic();
    const token = profile?.invite_token || inviteToken;
    if (!token || !CLIENT_BOT) return;
    const url = `https://t.me/${CLIENT_BOT}?start=invite_${token}`;
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(profile?.name || '')}`;
    window.open(shareUrl, '_blank');
  };

  const formatReviewName = (name) => {
    if (!name) return 'Клиент';
    const parts = name.trim().split(' ');
    if (parts.length < 2) return name;
    return `${parts[0]} ${parts[1][0]}.`;
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('ru', { day: 'numeric', month: 'long', year: 'numeric' });
  };

  const avatarContent = profile?.photo_url
    ? <img src={profile.photo_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
    : (profile?.name || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();

  const metrics = [
    profile?.review_count > 0 && t('masterLanding.reviewsMetric', { count: profile.review_count }),
    profile?.years_on_platform > 1 && t('masterLanding.yearsMetric', { count: profile.years_on_platform }),
    profile?.years_on_platform === 1 && t('masterLanding.yearMetric'),
  ].filter(Boolean).join(' · ');

  if (loading) {
    return (
      <div className="client-page" style={{ padding: '0 16px 120px' }}>
        <Skeleton height={80} style={{ borderRadius: '50%', width: 80, margin: '24px auto 12px' }} />
        <Skeleton height={24} style={{ width: 200, margin: '0 auto 8px' }} />
        <Skeleton height={16} style={{ width: 160, margin: '0 auto' }} />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="client-page" style={{ padding: '24px 16px', textAlign: 'center' }}>
        <p style={{ color: 'var(--tg-theme-hint-color)' }}>Специалист не найден</p>
      </div>
    );
  }

  return (
    <div className="client-page" style={{ paddingBottom: 120 }}>
      {/* Hero */}
      <div className="client-landing-hero">
        <div className="client-landing-avatar">{avatarContent}</div>
        <p className="client-landing-name">{profile.name}</p>
        {profile.sphere && <p className="client-landing-sphere">{profile.sphere}</p>}
        {metrics && <p className="client-landing-metrics">{metrics}</p>}
      </div>

      <div style={{ padding: '0 16px' }}>
        {/* Actions */}
        <div className="client-action-grid" style={{ marginBottom: 16 }}>
          {mode === 'public' ? (
            <button className="client-action-btn is-full" onClick={handleConnect} disabled={linking}>
              {linking ? t('masterLanding.connecting') : t('masterLanding.connectBtn')}
            </button>
          ) : (
            <>
              <button className="client-action-btn is-primary" onClick={() => { haptic(); navigate('create_order'); }}>
                {t('masterLanding.bookBtn')}
              </button>
              <button className="client-action-btn is-secondary" onClick={() => { haptic(); navigate('ask_question'); }}>
                {t('masterLanding.questionBtn')}
              </button>
            </>
          )}
        </div>

        {/* About */}
        {profile.bio && (
          <section style={{ marginBottom: 20 }}>
            <p className="client-section-title" style={{ marginBottom: 8 }}>{t('masterLanding.aboutTitle')}</p>
            <p style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)', lineHeight: 1.6 }}>{profile.bio}</p>
          </section>
        )}

        {/* Services */}
        {profile.services?.length > 0 && (
          <section style={{ marginBottom: 20 }}>
            <p className="client-section-title" style={{ marginBottom: 8 }}>{t('masterLanding.servicesTitle')}</p>
            <div className="client-card" style={{ padding: '0 14px' }}>
              {profile.services.map((s, i) => (
                <div key={s.id ?? i} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '12px 0',
                  borderBottom: i < profile.services.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
                }}>
                  <span style={{ fontSize: 15 }}>{s.name}</span>
                  {s.price != null && <span style={{ fontSize: 14, color: '#2481cc' }}>{s.price} ₽</span>}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Contacts */}
        {(profile.phone || profile.telegram || profile.instagram || profile.website || profile.contact_address) && (
          <section style={{ marginBottom: 20 }}>
            <p className="client-section-title" style={{ marginBottom: 8 }}>{t('masterLanding.contactsTitle')}</p>
            <div className="client-card" style={{ padding: '0 14px' }}>
              {[
                profile.phone && { label: profile.phone, href: `tel:${profile.phone}` },
                profile.telegram && { label: `@${profile.telegram.replace('@','')}`, href: `tg://resolve?domain=${profile.telegram.replace('@','')}` },
                profile.instagram && { label: `@${profile.instagram.replace('@','')}`, href: `https://instagram.com/${profile.instagram.replace('@','')}` },
                profile.website && { label: profile.website, href: profile.website.startsWith('http') ? profile.website : `https://${profile.website}` },
                profile.contact_address && { label: profile.contact_address, href: null },
              ].filter(Boolean).map((c, i, arr) => (
                <div key={i} style={{
                  padding: '12px 0',
                  borderBottom: i < arr.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
                }}>
                  {c.href ? (
                    <a href={c.href} style={{ color: 'var(--tg-theme-link-color, #2481cc)', fontSize: 14, textDecoration: 'none' }}>
                      {c.label}
                    </a>
                  ) : (
                    <span style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)' }}>{c.label}</span>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Work mode */}
        {profile.work_mode && (
          <section style={{ marginBottom: 20 }}>
            <p className="client-section-title" style={{ marginBottom: 8 }}>{t('masterLanding.workModeTitle')}</p>
            <p style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)' }}>{profile.work_mode}</p>
          </section>
        )}

        {/* Reviews */}
        <section style={{ marginBottom: 20 }}>
          <p className="client-section-title" style={{ marginBottom: 8 }}>{t('masterLanding.reviewsTitle')}</p>
          {reviews.length === 0 ? (
            <p style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)' }}>{t('masterLanding.noReviews')}</p>
          ) : reviews.map((r, i) => (
            <div key={r.id ?? i} className="client-card" style={{ padding: '12px 14px', marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{formatReviewName(r.client_name)}</span>
                <span style={{ fontSize: 12, color: 'var(--tg-theme-hint-color)' }}>{formatDate(r.created_at)}</span>
              </div>
              <p style={{ fontSize: 14, color: 'var(--tg-theme-hint-color)', lineHeight: 1.5, margin: 0 }}>{r.text}</p>
            </div>
          ))}
        </section>

        {/* Share */}
        {CLIENT_BOT && (
          <button className="client-action-btn is-secondary" style={{ width: '100%', marginBottom: 8 }} onClick={handleShare}>
            {t('masterLanding.shareBtn')}
          </button>
        )}
      </div>
    </div>
  );
}
```

**Step 2: Verify build + commit**
```bash
npm --prefix miniapp run build
git add miniapp/src/pages/MasterLanding.jsx
git commit -m "feat(miniapp): add MasterLanding screen (private + public modes)"
```

---

## Task 13: Update `Contact.jsx` — add `preselectedService` prop

**Files:**
- Modify: `miniapp/src/pages/Contact.jsx` (BookingForm component only)

**Step 1: Add `preselectedService` prop to `BookingForm`**

Find `function BookingForm({ onSuccess, keyboardOpen })` (around line 153) and change to:
```js
function BookingForm({ onSuccess, keyboardOpen, preselectedService }) {
```

Find the `useState` for `selectedService` (around line 156):
```js
const [selectedService, setSelectedService] = useState(null);
```
Change to:
```js
const [selectedService, setSelectedService] = useState(preselectedService || null);
```

**Step 2: Pass prop through from parent `Contact`**

Find the `BookingForm` usage in `Contact` (around line 381):
```jsx
<BookingForm onSuccess={() => setDone(true)} keyboardOpen={keyboardOpen} />
```
Change to:
```jsx
<BookingForm onSuccess={() => setDone(true)} keyboardOpen={keyboardOpen} preselectedService={preselectedService} />
```

Find `export default function Contact({ onNavigate, keyboardOpen })` and change to:
```js
export default function Contact({ onNavigate, keyboardOpen, preselectedService }) {
```

**Step 3: Verify build + commit**
```bash
npm --prefix miniapp run build
git add miniapp/src/pages/Contact.jsx
git commit -m "feat(miniapp): add preselectedService prop to Contact BookingForm"
```

---

## Task 14: Update `BottomNav.jsx`

**Files:**
- Modify (full rewrite): `miniapp/src/components/BottomNav.jsx`

**Step 1: Replace the entire file:**

```jsx
import { useI18n } from '../i18n';

const WebApp = window.Telegram?.WebApp;

const HomeIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
);

const ClockIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12 6 12 12 16 14"/>
  </svg>
);

const BellIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
    <path d="M13.73 21a2 2 0 01-3.46 0"/>
  </svg>
);

const GearIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
  </svg>
);

const tabs = [
  { id: 'home',     key: 'nav.client.home',     Icon: HomeIcon  },
  { id: 'history',  key: 'nav.client.history',  Icon: ClockIcon },
  { id: 'news',     key: 'nav.client.news',     Icon: BellIcon  },
  { id: 'settings', key: 'nav.client.settings', Icon: GearIcon  },
];

export default function BottomNav({ active, onNavigate = () => {} }) {
  const { t } = useI18n();

  const handleTab = (id) => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onNavigate(id);
  };

  return (
    <nav className="client-nav">
      {tabs.map(({ id, key, Icon }) => {
        const isActive = active === id;
        return (
          <button
            key={id}
            onClick={() => handleTab(id)}
            className={`client-nav-button${isActive ? ' is-active' : ''}`}
            aria-current={isActive ? 'page' : undefined}
          >
            <Icon />
            <span>{t(key)}</span>
          </button>
        );
      })}
    </nav>
  );
}
```

**Step 2: Verify build + commit**
```bash
npm --prefix miniapp run build
git add miniapp/src/components/BottomNav.jsx
git commit -m "feat(miniapp): update BottomNav to 4 new client tabs"
```

---

## Task 15: Update `App.jsx` — new ClientApp + invite flow

**Files:**
- Modify: `miniapp/src/App.jsx`

This is the most critical task — read the existing `App.jsx` carefully before editing.

**Step 1: Replace the `ClientApp` function** (lines ~20-81) with the new implementation:

```jsx
const SUB_SCREENS = new Set(['create_order', 'ask_question', 'landing']);

function ClientApp({ masters, activeMasterId, onMasterChange, initialInviteToken }) {
  const [tab, setTab] = useState('home');
  const [page, setPage] = useState(initialInviteToken ? 'landing' : 'home');
  const [pageParams, setPageParams] = useState(initialInviteToken ? { inviteToken: initialInviteToken, mode: 'public' } : {});
  const [keyboardOpen, setKeyboardOpen] = useState(false);
  const [masterProfile, setMasterProfile] = useState(null);
  const qc = useQueryClient();

  // Import useQueryClient at top of App.jsx: import { useQueryClient } from '@tanstack/react-query';

  useEffect(() => {
    document.body.classList.add('typeui-client-body');
    return () => document.body.classList.remove('typeui-client-body');
  }, []);

  // Telegram BackButton
  useEffect(() => {
    if (!WebApp?.BackButton) return;
    const isSubScreen = SUB_SCREENS.has(page) || page === 'master_select';
    if (isSubScreen) {
      WebApp.BackButton.show();
      const handler = () => navigate(tab);
      WebApp.BackButton.onClick(handler);
      return () => WebApp.BackButton.offClick(handler);
    } else {
      WebApp.BackButton.hide();
    }
  }, [page, tab]);

  // Hide BottomNav when keyboard open
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const handler = () => setKeyboardOpen(window.innerHeight - vv.height > 150);
    vv.addEventListener('resize', handler);
    return () => vv.removeEventListener('resize', handler);
  }, []);

  const navigate = (pageId, params = {}) => {
    if (pageId === 'home' || pageId === 'history' || pageId === 'news' || pageId === 'settings') {
      setTab(pageId);
      setPage(pageId);
      setPageParams({});
    } else {
      setPage(pageId);
      setPageParams(params);
    }
  };

  const handleTabNav = (tabId) => {
    if (tabId === tab && !SUB_SCREENS.has(page) && page !== 'master_select') {
      // Already on this tab — scroll to top
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      navigate(tabId);
    }
  };

  const handleMasterSelectDone = (masterId) => {
    onMasterChange(masterId);
    qc.invalidateQueries();
    navigate(tab);
  };

  const handleLinked = () => {
    // After connecting from public landing — reload masters
    window.location.reload();
  };

  const isSubScreen = SUB_SCREENS.has(page) || page === 'master_select';
  const activeMaster = masters.find(m => m.master_id === activeMasterId);

  const renderContent = () => {
    if (!activeMasterId && page !== 'landing') {
      return <MasterSelectScreen masters={masters} onSelect={handleMasterSelectDone} />;
    }

    if (page === 'master_select') {
      return <MasterSelectScreen masters={masters} onSelect={handleMasterSelectDone} />;
    }

    if (page === 'landing') {
      return (
        <MasterLanding
          mode={pageParams.mode || 'private'}
          masterId={pageParams.masterId || activeMasterId}
          inviteToken={pageParams.inviteToken}
          navigate={navigate}
          onLinked={handleLinked}
        />
      );
    }

    if (page === 'create_order') {
      return (
        <Contact
          onNavigate={(p) => navigate(p)}
          keyboardOpen={keyboardOpen}
          preselectedService={pageParams.service}
          initialMode="booking"
        />
      );
    }

    if (page === 'ask_question') {
      return (
        <Contact
          onNavigate={(p) => navigate(p)}
          keyboardOpen={keyboardOpen}
          initialMode="question"
        />
      );
    }

    if (tab === 'home') return (
      <Home
        activeMasterId={activeMasterId}
        navigate={navigate}
        masterName={activeMaster?.master_name}
        onProfileLoaded={setMasterProfile}
      />
    );
    if (tab === 'history') return (
      <History
        activeMasterId={activeMasterId}
        navigate={navigate}
        masterProfile={masterProfile}
      />
    );
    if (tab === 'news') return (
      <News activeMasterId={activeMasterId} navigate={navigate} />
    );
    if (tab === 'settings') return (
      <Settings
        activeMasterId={activeMasterId}
        onProfileDeleted={() => window.location.reload()}
      />
    );

    return null;
  };

  return (
    <div className="client-shell">
      <div className="client-shell-content">
        {/* Specialist switcher header — shown on all tab screens */}
        {!isSubScreen && activeMasterId && masters.length > 1 && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '8px 16px 0' }}>
            <button className="client-header-specialist-btn" onClick={() => navigate('master_select')}>
              <span>{activeMaster?.master_name}</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </button>
          </div>
        )}
        {renderContent()}
      </div>
      {!isSubScreen && activeMasterId && !keyboardOpen && (
        <BottomNav active={tab} onNavigate={handleTabNav} />
      )}
    </div>
  );
}
```

**Step 2: Update imports at the top of `App.jsx`**

Add new imports alongside existing ones:
```jsx
import { useQueryClient } from '@tanstack/react-query';
import Home from './pages/Home';
import History from './pages/History';
import News from './pages/News';
import Settings from './pages/Settings';
import MasterLanding from './pages/MasterLanding';
import Contact from './pages/Contact';
```

Remove unused imports: `Bonuses`, `Promos`.

Keep existing imports: `BottomNav`, `Skeleton`, `getAuthRole`, `getClientMasters`, `linkToMaster`, `setActiveMasterId`, `MasterOnboarding`, `MasterSelectScreen`, `MasterTypeUIProvider`, `useI18n`, `MasterApp`.

**Step 3: Update the invite flow in the `App` function**

Find the `useEffect` that calls `load()` for role === 'client' (around line 145). Change the `load` function inside to:

```js
const load = async () => {
  const data = await getClientMasters();
  setMasters(data.masters || []);
  // Do NOT call linkToMaster here — invite is handled by showing MasterLanding
};
load().catch(() => setMasters([]));
```

Remove the `token`/`linkToMaster` logic from this effect. The token is passed to `ClientApp` as `initialInviteToken`.

**Step 4: Pass `initialInviteToken` to `ClientApp`**

In the `App` return for role === 'client':
```jsx
return (
  <ClientApp
    masters={masters}
    activeMasterId={activeMasterId}
    onMasterChange={handleMasterChange}
    initialInviteToken={token || null}
  />
);
```

Where `token` is extracted from `start_param` as before:
```js
const startParam = WebApp?.initDataUnsafe?.start_param;
const token = startParam?.startsWith('invite_') ? startParam.slice(7) : null;
```

Move this extraction to component level (outside the effect).

**Step 5: Add `initialMode` prop to `Contact` component**

In `Contact.jsx`, update the export signature and add logic to start in a specific mode:
```js
export default function Contact({ onNavigate, keyboardOpen, preselectedService, initialMode }) {
  const [mode, setMode] = useState(initialMode || null);
```

**Step 6: Verify build**
```bash
npm --prefix miniapp run build
```
Expected: BUILD SUCCESS. Fix any import errors before committing.

**Step 7: Commit**
```bash
git add miniapp/src/App.jsx miniapp/src/pages/Contact.jsx
git commit -m "feat(miniapp): wire new ClientApp shell with 4-tab navigation and invite flow"
```

---

## Task 16: Delete old files

**Files to delete:**
- `miniapp/src/pages/Bonuses.jsx`
- `miniapp/src/pages/Promos.jsx`
- `miniapp/src/pages/Booking.jsx`

**Step 1: Delete and verify**
```bash
rm miniapp/src/pages/Bonuses.jsx
rm miniapp/src/pages/Promos.jsx
rm miniapp/src/pages/Booking.jsx
npm --prefix miniapp run build
```
Expected: BUILD SUCCESS (no remaining imports of deleted files — verify with `grep -r "Bonuses\|from.*Promos\|from.*Booking" miniapp/src/`).

**Step 2: Commit**
```bash
git add -A miniapp/src/pages/Bonuses.jsx miniapp/src/pages/Promos.jsx miniapp/src/pages/Booking.jsx
git commit -m "chore(miniapp): remove old client screens (Bonuses, Promos, Booking)"
```

---

## Task 17: Final verification

**Step 1: Full build**
```bash
npm --prefix miniapp run build
```
Expected: BUILD SUCCESS, no warnings about missing modules.

**Step 2: Verify no «мастер» in client UI strings**
```bash
grep -rn "мастер\|мастера\|мастеру" miniapp/src/i18n/dictionaries/ru.js | grep -v "master\|Master"
```
Any hits: fix them (replace with «специалист»).

**Step 3: Verify no dead imports**
```bash
grep -rn "from.*Bonuses\|from.*Promos\|from.*Booking" miniapp/src/
```
Expected: 0 matches.

**Step 4: Smoke-test checklist (manual, in Telegram)**

- [ ] Specialist select screen loads and shows list
- [ ] Tap specialist → Home tab loads profile, activity, services, news preview
- [ ] «Записаться» opens booking form
- [ ] «Задать вопрос» opens question form
- [ ] Service accordion opens/closes; «Записаться» pre-fills service
- [ ] History tab loads and shows orders + bonus rows
- [ ] News tab loads publications with correct tags
- [ ] Settings tab toggles work (network request fires on toggle)
- [ ] «Подробнее» → landing → shows reviews
- [ ] «Поделиться» → share dialog opens
- [ ] Multi-master: specialist switcher visible in header → returns to select screen
- [ ] BackButton shown on sub-screens (booking, landing), hidden on tabs
- [ ] Invite link flow: open with `?start=invite_TOKEN` → shows landing → «Подключиться» links and reloads

**Step 5: Commit any final fixes, then deploy**
```bash
git status --short
# commit remaining fixes if any
bash deploy_miniapp.sh
```

---

## Notes

- `VITE_SUPPORT_TG` and `VITE_PRIVACY_URL` env vars used in `Settings.jsx` — add if needed, or hardcode for now with obvious placeholder
- `APP_VERSION` can be added as `VITE_APP_VERSION=1.x.x` in env files or sourced from `package.json`
- If `Contact.jsx`'s `initialMode` prop causes `mode` to stay null on re-render (e.g. when navigating back), reset it with a `useEffect` on `initialMode` prop
- All new API functions use the existing `axios` instance with `X-Init-Data` header — no auth changes needed
- The `getPublicMasterProfile` uses a separate `publicApi` instance (no `X-Init-Data`) — backend `/api/public/master/{token}` does not validate headers
