import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import { I18nProvider } from './i18n';
import { applyThemePreset, getStoredThemePreset } from './master/hooks/useThemePreset';
import './theme.css';

const WebApp = window.Telegram?.WebApp;

// Initialize Telegram WebApp
WebApp?.ready?.();
WebApp?.expand?.();
WebApp?.requestFullscreen?.();

// ─── Boot theme ────────────────────────────────────────────────────────────
// Pick the initial body bg/colors BEFORE React mounts so masters don't see
// the dark→light flash. Read the last known role from localStorage:
//   - master  → apply stored master theme preset (light bg, brand accent)
//   - client  → apply the forced dark Telegram-style theme
//   - first visit (no localStorage) → keep dark forced theme as neutral default

const LAST_ROLE_KEY = 'last_role';
let lastRole = null;
try { lastRole = localStorage.getItem(LAST_ROLE_KEY); } catch {}

const FORCED_CLIENT_THEME = {
  bg: '#0f1923',
  secondaryBg: '#162030',
  sectionBg: '#0f1923',
  text: '#ffffff',
  hint: '#8b9bb4',
  link: '#4f9cf9',
  button: '#4f9cf9',
  buttonText: '#ffffff',
  accent: '#4f9cf9',
  destructive: '#e53935',
};

function applyForcedClientTheme() {
  const root = document.documentElement;
  root.style.setProperty('--tg-theme-bg-color', FORCED_CLIENT_THEME.bg);
  root.style.setProperty('--tg-theme-secondary-bg-color', FORCED_CLIENT_THEME.secondaryBg);
  root.style.setProperty('--tg-theme-section-bg-color', FORCED_CLIENT_THEME.sectionBg);
  root.style.setProperty('--tg-theme-text-color', FORCED_CLIENT_THEME.text);
  root.style.setProperty('--tg-theme-hint-color', FORCED_CLIENT_THEME.hint);
  root.style.setProperty('--tg-theme-link-color', FORCED_CLIENT_THEME.link);
  root.style.setProperty('--tg-theme-button-color', FORCED_CLIENT_THEME.button);
  root.style.setProperty('--tg-theme-button-text-color', FORCED_CLIENT_THEME.buttonText);
  root.style.setProperty('--tg-theme-accent-text-color', FORCED_CLIENT_THEME.accent);
  root.style.setProperty('--tg-theme-destructive-text-color', FORCED_CLIENT_THEME.destructive);
  root.style.colorScheme = 'dark';
  if (document.body) {
    document.body.style.color = FORCED_CLIENT_THEME.text;
    document.body.style.background = FORCED_CLIENT_THEME.bg;
  }
  WebApp?.setBackgroundColor?.(FORCED_CLIENT_THEME.bg);
  WebApp?.setHeaderColor?.(FORCED_CLIENT_THEME.bg);
}

function applyEarlyMasterTheme() {
  // applyThemePreset writes body bg only if typeui-enterprise-body class is
  // present — add it now so the boot paint matches the final master state.
  document.body.classList.add('typeui-enterprise-body');
  applyThemePreset(getStoredThemePreset());
}

function applyBootTheme() {
  if (lastRole === 'master') applyEarlyMasterTheme();
  else applyForcedClientTheme();
}

applyBootTheme();

// ─── Safe area insets ──────────────────────────────────────────────────────
const applyInsets = () => {
  const root = document.documentElement;
  const safeTop = WebApp?.safeAreaInset?.top ?? 0;
  const contentTop = WebApp?.contentSafeAreaInset?.top ?? 0;
  const safeBottom = WebApp?.safeAreaInset?.bottom ?? 0;
  if (safeTop > 0) root.style.setProperty('--tg-safe-area-inset-top', `${safeTop}px`);
  if (contentTop > 0) root.style.setProperty('--tg-content-safe-area-inset-top', `${contentTop}px`);
  if (safeBottom > 0) root.style.setProperty('--tg-safe-area-inset-bottom', `${safeBottom}px`);
};
applyInsets();
WebApp?.onEvent?.('safeAreaChanged', applyInsets);
WebApp?.onEvent?.('contentSafeAreaChanged', applyInsets);
WebApp?.onEvent?.('fullscreen_changed', applyInsets);
WebApp?.onEvent?.('themeChanged', applyBootTheme);
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    applyBootTheme();
    applyInsets();
  }
});

// ─── React Query with localStorage persistence ─────────────────────────────
// Cached data shows instantly on next open; queries refetch in background.
// Inline persister (no new deps) — sufficient for our cache shape.

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

const RQ_CACHE_KEY = 'rq-cache-v1';
const RQ_MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24h

// Hydrate cache from localStorage
try {
  const raw = localStorage.getItem(RQ_CACHE_KEY);
  if (raw) {
    const parsed = JSON.parse(raw);
    if (parsed && Array.isArray(parsed.queries) && Date.now() - parsed.ts < RQ_MAX_AGE_MS) {
      for (const entry of parsed.queries) {
        if (entry?.key && entry.data !== undefined) {
          queryClient.setQueryData(entry.key, entry.data);
        }
      }
    }
  }
} catch {
  // ignore parse / quota errors
}

// Persist successful queries (debounced)
let rqSaveTimer = null;
queryClient.getQueryCache().subscribe(() => {
  if (rqSaveTimer) clearTimeout(rqSaveTimer);
  rqSaveTimer = setTimeout(() => {
    try {
      const queries = queryClient.getQueryCache().getAll()
        .filter((q) => q.state.status === 'success' && q.state.data !== undefined)
        .map((q) => ({ key: q.queryKey, data: q.state.data }));
      localStorage.setItem(RQ_CACHE_KEY, JSON.stringify({ ts: Date.now(), queries }));
    } catch {
      // localStorage quota or serialize failure — non-fatal
    }
  }, 600);
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <I18nProvider>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </I18nProvider>
);
