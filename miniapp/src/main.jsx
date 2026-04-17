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
