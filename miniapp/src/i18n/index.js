import { createContext, createElement, useCallback, useContext, useMemo, useState } from 'react';
import ru from './dictionaries/ru';
import en from './dictionaries/en';

const WebApp = window.Telegram?.WebApp;

export const SUPPORTED_LANGS = ['ru', 'en'];
export const DEFAULT_LANG = 'ru';
const STORAGE_KEY = 'miniapp_lang';

const DICTS = { ru, en };

function readPath(obj, path) {
  return path.split('.').reduce((acc, part) => (acc && typeof acc === 'object' ? acc[part] : undefined), obj);
}

function normalizeLang(raw) {
  const value = String(raw || '').toLowerCase();
  if (value.startsWith('en')) return 'en';
  return 'ru';
}

function getStoredLang() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return normalizeLang(raw);
  } catch {
    return null;
  }
}

function getTelegramLang() {
  const code = WebApp?.initDataUnsafe?.user?.language_code;
  if (!code) return null;
  return normalizeLang(code);
}

function interpolate(template, params = {}) {
  if (typeof template !== 'string') return template;
  return template.replace(/\{(\w+)\}/g, (_, key) => String(params[key] ?? ''));
}

function resolveValue(lang, key) {
  const primary = readPath(DICTS[lang], key);
  if (primary !== undefined) return primary;
  return readPath(DICTS.ru, key);
}

function getInitialLang() {
  return getStoredLang() || getTelegramLang() || DEFAULT_LANG;
}

export function getLocaleByLang(lang) {
  return lang === 'en' ? 'en-US' : 'ru-RU';
}

const I18nContext = createContext({
  lang: DEFAULT_LANG,
  setLang: () => {},
  t: (key) => key,
  tr: (ruText, enText) => ruText,
  locale: getLocaleByLang(DEFAULT_LANG),
});

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(getInitialLang);

  const setLang = useCallback((nextLang) => {
    const normalized = normalizeLang(nextLang);
    setLangState(normalized);
    try {
      localStorage.setItem(STORAGE_KEY, normalized);
    } catch {
      // ignore storage errors
    }
  }, []);

  const t = useCallback((key, params) => {
    const value = resolveValue(lang, key);
    if (value === undefined) return key;
    return interpolate(value, params);
  }, [lang]);

  const tr = useCallback((ruText, enText) => (
    lang === 'en' ? enText : ruText
  ), [lang]);

  const contextValue = useMemo(() => ({
    lang,
    setLang,
    t,
    tr,
    locale: getLocaleByLang(lang),
  }), [lang, setLang, t, tr]);

  return createElement(I18nContext.Provider, { value: contextValue }, children);
}

export function useI18n() {
  return useContext(I18nContext);
}
