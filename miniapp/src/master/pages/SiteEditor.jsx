import { useEffect, useState } from 'react';
import { getPromoStyles, updatePromoPage } from '../../api/client';
import BottomSheet from '../components/site/BottomSheet';
import PromoPreview from '../components/site/PromoPreview';
import SiteControlPanel from '../components/site/SiteControlPanel';
import StyleSwitcher from '../components/site/StyleSwitcher';
import AdvantagesSheet from '../components/site/sheets/AdvantagesSheet';
import CtaSheet from '../components/site/sheets/CtaSheet';
import HeroSheet from '../components/site/sheets/HeroSheet';
import IdentitySheet from '../components/site/sheets/IdentitySheet';
import PromoSheet from '../components/site/sheets/PromoSheet';
import ServiceSheet from '../components/site/sheets/ServiceSheet';
import SettingsSheet from '../components/site/sheets/SettingsSheet';
import TaglineSheet from '../components/site/sheets/TaglineSheet';

const WebApp = window.Telegram?.WebApp;

export default function SiteEditor({ initialData, onUpdate }) {
  const [data, setData] = useState(initialData);
  const [styles, setStyles] = useState([]);
  const [currentStyleIndex, setCurrentStyleIndex] = useState(0);
  const [isDirty, setIsDirty] = useState(false);
  const [activeSheet, setActiveSheet] = useState(null);
  const [saving, setSaving] = useState(false);
  const [photoTs, setPhotoTs] = useState(Date.now());

  useEffect(() => {
    getPromoStyles().then((res) => {
      const list = res?.styles || [];
      setStyles(list);
      const idx = list.findIndex((s) => s.id === initialData?.style_id);
      setCurrentStyleIndex(idx >= 0 ? idx : 0);
    }).catch(() => {});
  }, [initialData?.style_id]);

  function updateField(field, value) {
    setData((prev) => ({ ...prev, [field]: value }));
    setIsDirty(true);
    if (field === 'photo_url') setPhotoTs(Date.now());
  }

  function closeSheet() {
    setActiveSheet(null);
  }

  async function handleSave() {
    setSaving(true);
    try {
      const styleId = styles[currentStyleIndex]?.id ?? data.style_id;
      const saved = await updatePromoPage({ ...data, style_id: styleId });
      setData(saved);
      setIsDirty(false);
      WebApp?.HapticFeedback?.notificationOccurred?.('success');
      onUpdate?.();
    } catch {
      WebApp?.HapticFeedback?.notificationOccurred?.('error');
    } finally {
      setSaving(false);
    }
  }

  const styleConfig = styles[currentStyleIndex]?.config ?? data.style?.config ?? {};

  const SHEETS = {
    hero: <HeroSheet data={data} onChange={updateField} onClose={closeSheet} photoTs={photoTs} />,
    identity: <IdentitySheet data={data} onChange={updateField} onClose={closeSheet} />,
    tagline: <TaglineSheet data={data} onChange={updateField} onClose={closeSheet} />,
    service: <ServiceSheet data={data} onChange={updateField} onClose={closeSheet} />,
    promo: <PromoSheet data={data} onChange={updateField} onClose={closeSheet} />,
    advantages: <AdvantagesSheet data={data} onChange={updateField} onClose={closeSheet} />,
    cta: <CtaSheet data={data} onChange={updateField} onClose={closeSheet} />,
    settings: <SettingsSheet data={data} onChange={updateField} onClose={closeSheet} />,
  };

  return (
    <>
      <link rel="stylesheet" href="/promo-shared.css" />

      <div className="site-editor">
        <PromoPreview
          data={data}
          styleConfig={styleConfig}
          onBlockTap={setActiveSheet}
          photoTs={photoTs}
          heroOverlay={
            <StyleSwitcher
              styles={styles}
              currentIndex={currentStyleIndex}
              onChange={(idx) => { setCurrentStyleIndex(idx); setIsDirty(true); }}
            />
          }
        />

        <SiteControlPanel
          data={data}
          isDirty={isDirty}
          saving={saving}
          onSave={handleSave}
          onSettings={() => setActiveSheet('settings')}
        />

        {activeSheet && SHEETS[activeSheet] && (
          <BottomSheet onClose={closeSheet}>
            {SHEETS[activeSheet]}
          </BottomSheet>
        )}
      </div>

      <style>{`
        .site-editor {
          min-height: 100vh;
          background: var(--master-bg-section);
          position: relative;
        }
        /* Shared sheet form styles */
        .sheet-form { display: flex; flex-direction: column; gap: 12px; }
        .sheet-field { display: flex; flex-direction: column; gap: 6px; }
        .sheet-field--toggle { flex-direction: row; align-items: center; justify-content: space-between; }
        .sheet-label { font-size: 13px; color: var(--master-text-secondary); }
        .sheet-section-label { font-size: 13px; font-weight: 600; color: var(--master-text-primary); }
        .sheet-input {
          background: var(--master-bg-surface);
          border: 1px solid var(--master-border);
          border-radius: 12px;
          padding: 12px 16px;
          font-size: 16px;
          color: var(--master-text-primary);
          outline: none;
          width: 100%;
          transition: border-color 150ms, box-shadow 150ms, background-color 150ms;
        }
        .sheet-input::placeholder { color: var(--master-text-secondary); }
        .sheet-input:focus {
          border-color: var(--master-accent);
          box-shadow: 0 0 0 3px var(--master-accent-14);
        }
        .sheet-textarea { resize: vertical; min-height: 80px; font-family: inherit; }
        .sheet-counter { font-size: 12px; color: var(--master-text-secondary); text-align: right; }
        .sheet-hint { font-size: 13px; color: var(--master-text-secondary); }
        .sheet-error { font-size: 13px; color: var(--master-destructive); }
        .sheet-btn {
          width: 100%;
          padding: 13px;
          border-radius: 12px;
          border: 1px solid var(--master-border);
          background: var(--master-bg-surface);
          font-size: 15px;
          cursor: pointer;
          color: var(--master-text-primary);
          transition: transform 140ms ease, border-color 150ms, background-color 150ms;
        }
        .sheet-btn:active { transform: scale(0.98); }
        .sheet-btn--accent {
          background: var(--master-accent);
          color: var(--master-button-text);
          border-color: transparent;
          box-shadow: 0 10px 24px var(--master-accent-22);
        }
        .sheet-btn--done {
          background: var(--master-accent);
          color: var(--master-button-text);
          border-color: transparent;
          font-weight: 600;
          box-shadow: 0 10px 24px var(--master-accent-22);
        }
        .sheet-btn--danger {
          color: var(--master-destructive);
          border-color: var(--master-destructive);
          background: transparent;
        }
        .sheet-btn:disabled { opacity: 0.5; cursor: default; }
        /* Toggle switch */
        .sheet-toggle { position: relative; display: inline-block; width: 44px; height: 26px; flex-shrink: 0; }
        .sheet-toggle input { opacity: 0; width: 0; height: 0; position: absolute; }
        .sheet-toggle__track {
          position: absolute; inset: 0; border-radius: 13px;
          background: var(--master-border);
          cursor: pointer; transition: background 200ms;
        }
        .sheet-toggle__track::after {
          content: ''; position: absolute; left: 3px; top: 3px;
          width: 20px; height: 20px; border-radius: 50%;
          background: #fff; transition: transform 200ms;
        }
        .sheet-toggle input:checked + .sheet-toggle__track { background: var(--master-accent); }
        .sheet-toggle input:checked + .sheet-toggle__track::after { transform: translateX(18px); }
        /* Hero preview */
        .hero-sheet-preview { display: flex; justify-content: center; padding: 8px 0; }
        .hero-sheet-photo { width: 120px; height: 120px; border-radius: 60px; object-fit: cover; border: 2px solid var(--master-border); }
        /* EditableBlock */
        .editable-block { position: relative; cursor: pointer; transition: outline 200ms ease; border-radius: 8px; }
        .editable-block:active { outline: 1px dashed var(--master-accent); outline-offset: 4px; opacity: 0.85; }
        .editable-block__indicator {
          position: absolute; top: 8px; right: 8px; width: 28px; height: 28px; border-radius: 50%;
          background: var(--master-bg-card); color: var(--master-text-primary);
          border: 1px solid var(--master-border);
          display: flex; align-items: center; justify-content: center; opacity: 0.72; font-size: 14px;
          box-shadow: 0 10px 20px rgba(0,0,0,0.14); pointer-events: none;
        }
      `}</style>
    </>
  );
}
