import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import { I18nProvider } from './i18n';
import './theme.css';
const WebApp = window.Telegram?.WebApp;
const FORCED_THEME = {
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

// Initialize Telegram WebApp
if (typeof WebApp?.ready === 'function') {
  WebApp.ready();
}
if (typeof WebApp?.expand === 'function') {
  WebApp.expand();
}
if (typeof WebApp?.requestFullscreen === 'function') {
  WebApp.requestFullscreen();
}

const applyForcedTheme = () => {
  const root = document.documentElement;
  root.style.setProperty('--tg-theme-bg-color', FORCED_THEME.bg);
  root.style.setProperty('--tg-theme-secondary-bg-color', FORCED_THEME.secondaryBg);
  root.style.setProperty('--tg-theme-section-bg-color', FORCED_THEME.sectionBg);
  root.style.setProperty('--tg-theme-text-color', FORCED_THEME.text);
  root.style.setProperty('--tg-theme-hint-color', FORCED_THEME.hint);
  root.style.setProperty('--tg-theme-link-color', FORCED_THEME.link);
  root.style.setProperty('--tg-theme-button-color', FORCED_THEME.button);
  root.style.setProperty('--tg-theme-button-text-color', FORCED_THEME.buttonText);
  root.style.setProperty('--tg-theme-accent-text-color', FORCED_THEME.accent);
  root.style.setProperty('--tg-theme-destructive-text-color', FORCED_THEME.destructive);
  root.style.colorScheme = 'dark';
  if (document.body) {
    document.body.style.color = FORCED_THEME.text;
    document.body.style.background = FORCED_THEME.bg;
  }
  if (typeof WebApp?.setBackgroundColor === 'function') WebApp.setBackgroundColor(FORCED_THEME.bg);
  if (typeof WebApp?.setHeaderColor === 'function') WebApp.setHeaderColor(FORCED_THEME.bg);
};
applyForcedTheme();

// Apply safe area CSS variables from JS API.
// Only set when value > 0 to avoid overriding CSS env() fallbacks with 0px.
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
WebApp?.onEvent?.('themeChanged', applyForcedTheme);
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    applyForcedTheme();
    applyInsets();
  }
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <I18nProvider>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </I18nProvider>
);
