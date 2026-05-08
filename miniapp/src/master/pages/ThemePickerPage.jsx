import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getMasterMe, updateMasterThemePreset } from '../../api/client';
import { useI18n } from '../../i18n';
import {
  DEFAULT_THEME_PRESET,
  getThemePreset,
  THEME_PRESET_GROUPS,
  THEME_PRESETS,
} from '../themePresets';

const WebApp = window.Telegram?.WebApp;

function haptic() {
  if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
    WebApp.HapticFeedback.impactOccurred('light');
  }
}

function ThemePreview({ preset, selected }) {
  return (
    <div
      style={{
        borderRadius: 18,
        border: `1.5px solid ${selected ? preset.accent : preset.border}`,
        background: preset.bgCard,
        boxShadow: selected ? `0 0 0 2px ${preset.accent}` : 'var(--tg-enterprise-shadow-soft)',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <div
        style={{
          minHeight: 118,
          padding: 12,
          background: `radial-gradient(circle at top, ${preset.glowTop}, transparent 34%), radial-gradient(circle at 85% 12%, ${preset.glowSide}, transparent 24%), ${preset.bgBase}`,
          display: 'grid',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ width: 54, height: 10, borderRadius: 999, background: preset.accentSoft }} />
          <div style={{ width: 18, height: 18, borderRadius: 999, background: preset.accent }} />
        </div>
        <div style={{ display: 'grid', gap: 6 }}>
          <div style={{ height: 12, width: '72%', borderRadius: 999, background: preset.textPrimary }} />
          <div style={{ height: 8, width: '48%', borderRadius: 999, background: preset.textSecondary }} />
        </div>
        <div
          style={{
            marginTop: 'auto',
            borderRadius: 14,
            background: preset.bgSurface,
            border: `1px solid ${preset.border}`,
            padding: 10,
            display: 'grid',
            gap: 8,
          }}
        >
          <div style={{ width: '100%', height: 8, borderRadius: 999, background: preset.textSecondary }} />
          <div
            style={{
              width: '60%',
              height: 28,
              borderRadius: 10,
              background: preset.accent,
              color: preset.buttonText || '#ffffff',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 11,
              fontWeight: 700,
            }}
          >
            CTA
          </div>
        </div>
      </div>
      {selected ? (
        <div
          style={{
            position: 'absolute',
            top: 8,
            right: 8,
            width: 24,
            height: 24,
            borderRadius: 999,
            background: preset.accent,
            color: preset.buttonText || '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 14,
            fontWeight: 800,
            boxShadow: 'var(--tg-enterprise-shadow-soft)',
          }}
        >
          ✓
        </div>
      ) : null}
    </div>
  );
}

export default function ThemePickerPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [pendingPreset, setPendingPreset] = useState(null);

  const { data: masterData } = useQuery({
    queryKey: ['master-me'],
    queryFn: getMasterMe,
    staleTime: 30_000,
  });

  const currentPreset = masterData?.theme_preset || DEFAULT_THEME_PRESET;

  const mutation = useMutation({
    mutationFn: updateMasterThemePreset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['master-me'] });
      queryClient.invalidateQueries({ queryKey: ['master-dashboard'] });
    },
    onSettled: () => {
      setPendingPreset(null);
    },
  });

  const sections = useMemo(() => THEME_PRESET_GROUPS.map((group) => ({
    ...group,
    title: group.id === 'dark' ? t('themePicker.dark') : t('themePicker.light'),
    items: group.keys.map((key) => ({ key, preset: THEME_PRESETS[key] })),
  })), [t]);

  const applyOptimisticPreset = (presetName) => {
    queryClient.setQueryData(['master-me'], (old) => (old ? { ...old, theme_preset: presetName } : old));
    queryClient.setQueryData(['master-dashboard'], (old) => (old ? { ...old, theme_preset: presetName } : old));
  };

  const handleSelect = async (presetName) => {
    if (mutation.isPending || presetName === currentPreset) return;

    haptic();
    setPendingPreset(presetName);

    const previousMe = queryClient.getQueryData(['master-me']);
    const previousDashboard = queryClient.getQueryData(['master-dashboard']);
    applyOptimisticPreset(presetName);

    try {
      await mutation.mutateAsync(presetName);
    } catch (_) {
      queryClient.setQueryData(['master-me'], previousMe);
      queryClient.setQueryData(['master-dashboard'], previousDashboard);
      if (typeof WebApp?.showAlert === 'function') {
        WebApp.showAlert(t('themePicker.savingFailed'));
      }
    }
  };

  return (
    <div className="enterprise-page">
      <div className="enterprise-page-inner" style={{ paddingBottom: 108 }}>
        {sections.map((section) => (
          <section key={section.id} style={{ marginBottom: 22 }}>
            <div className="enterprise-section-title" style={{ paddingLeft: 0, paddingRight: 0 }}>
              {section.title}
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
                gap: 10,
              }}
            >
              {section.items.map(({ key, preset }) => {
                const resolved = getThemePreset(key);
                const selected = currentPreset === key;
                const isPending = pendingPreset === key;

                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => handleSelect(key)}
                    disabled={mutation.isPending && !selected}
                    style={{
                      border: 'none',
                      background: 'transparent',
                      padding: 0,
                      textAlign: 'left',
                      cursor: 'pointer',
                      opacity: mutation.isPending && !selected ? 0.72 : 1,
                    }}
                  >
                    <ThemePreview preset={resolved} selected={selected} />
                    <div
                      style={{
                        marginTop: 8,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: 8,
                        color: 'var(--tg-text)',
                        fontSize: 14,
                        fontWeight: 700,
                      }}
                    >
                      <span>{preset.label}</span>
                      {isPending ? (
                        <span style={{ color: 'var(--tg-hint)', fontSize: 12 }}>
                          {t('common.saving')}
                        </span>
                      ) : null}
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
