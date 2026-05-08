import { useEffect } from 'react';
import { DEFAULT_THEME_PRESET, getThemePreset } from '../themePresets';

const WebApp = window.Telegram?.WebApp;

const MASTER_THEME_KEYS = [
  '--master-accent',
  '--master-accent-soft',
  '--master-positive',
  '--master-bg-base',
  '--master-bg-card',
  '--master-bg-surface',
  '--master-bg-section',
  '--master-text-primary',
  '--master-text-secondary',
  '--master-border',
  '--master-glow-top',
  '--master-glow-side',
  '--master-destructive',
  '--master-button-text',
  '--master-mode',
  '--master-accent-8',
  '--master-accent-12',
  '--master-accent-14',
  '--master-accent-16',
  '--master-accent-20',
  '--master-accent-22',
  '--master-accent-28',
];

function hexToRgb(hex) {
  const normalized = hex.replace('#', '').trim();
  if (normalized.length !== 6) return null;
  const value = Number.parseInt(normalized, 16);
  if (Number.isNaN(value)) return null;
  return {
    r: (value >> 16) & 255,
    g: (value >> 8) & 255,
    b: value & 255,
  };
}

function withAlpha(hex, alpha) {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;
}

function applyThemePreset(name) {
  const preset = getThemePreset(name || DEFAULT_THEME_PRESET);
  const root = document.documentElement;
  const body = document.body;

  root.style.setProperty('--master-accent', preset.accent);
  root.style.setProperty('--master-accent-soft', preset.accentSoft);
  root.style.setProperty('--master-positive', preset.positive);
  root.style.setProperty('--master-bg-base', preset.bgBase);
  root.style.setProperty('--master-bg-card', preset.bgCard);
  root.style.setProperty('--master-bg-surface', preset.bgSurface);
  root.style.setProperty('--master-bg-section', preset.bgSection);
  root.style.setProperty('--master-text-primary', preset.textPrimary);
  root.style.setProperty('--master-text-secondary', preset.textSecondary);
  root.style.setProperty('--master-border', preset.border);
  root.style.setProperty('--master-glow-top', preset.glowTop);
  root.style.setProperty('--master-glow-side', preset.glowSide);
  root.style.setProperty('--master-destructive', preset.destructive);
  root.style.setProperty('--master-button-text', preset.buttonText || '#ffffff');
  root.style.setProperty('--master-mode', preset.mode);
  root.style.setProperty('--master-accent-8', withAlpha(preset.accent, 0.08));
  root.style.setProperty('--master-accent-12', withAlpha(preset.accent, 0.12));
  root.style.setProperty('--master-accent-14', withAlpha(preset.accent, 0.14));
  root.style.setProperty('--master-accent-16', withAlpha(preset.accent, 0.16));
  root.style.setProperty('--master-accent-20', withAlpha(preset.accent, 0.2));
  root.style.setProperty('--master-accent-22', withAlpha(preset.accent, 0.22));
  root.style.setProperty('--master-accent-28', withAlpha(preset.accent, 0.28));
  root.style.colorScheme = preset.mode;

  if (body?.classList.contains('typeui-enterprise-body')) {
    body.style.background = preset.bgBase;
    body.style.color = preset.textPrimary;
  }
  if (typeof WebApp?.setBackgroundColor === 'function') {
    WebApp.setBackgroundColor(preset.bgBase);
  }
  if (typeof WebApp?.setHeaderColor === 'function') {
    WebApp.setHeaderColor(preset.bgBase);
  }
}

export function useThemePreset(name) {
  useEffect(() => {
    applyThemePreset(name);

    return () => {
      const root = document.documentElement;
      for (const key of MASTER_THEME_KEYS) {
        root.style.removeProperty(key);
      }
    };
  }, [name]);
}
