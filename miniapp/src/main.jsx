import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
const WebApp = window.Telegram?.WebApp;
import App from './App';
import './theme.css';

// Initialize Telegram WebApp
if (typeof WebApp?.ready === 'function') {
  WebApp.ready();
}
if (typeof WebApp?.expand === 'function') {
  WebApp.expand();
}

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
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
);
