import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import { I18nProvider } from './i18n';
import './theme.css';
const WebApp = window.Telegram?.WebApp;

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

// Apply safe area CSS variables from JS API (Telegram doesn't set --tg-content-safe-area-inset-* automatically)
const applyInsets = () => {
  const root = document.documentElement;
  const safe = WebApp?.safeAreaInset;
  const content = WebApp?.contentSafeAreaInset;
  if (safe) {
    root.style.setProperty('--tg-safe-area-inset-top', `${safe.top ?? 0}px`);
    root.style.setProperty('--tg-safe-area-inset-bottom', `${safe.bottom ?? 0}px`);
  }
  if (content) {
    root.style.setProperty('--tg-content-safe-area-inset-top', `${content.top ?? 0}px`);
    root.style.setProperty('--tg-content-safe-area-inset-bottom', `${content.bottom ?? 0}px`);
  }
};
applyInsets();
WebApp?.onEvent?.('safeAreaChanged', applyInsets);
WebApp?.onEvent?.('contentSafeAreaChanged', applyInsets);

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
