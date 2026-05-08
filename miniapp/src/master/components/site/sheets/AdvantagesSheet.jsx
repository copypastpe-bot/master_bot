import { useState } from 'react';
import { getPromoAdvantages } from '../../../../api/client';
import { useI18n } from '../../../../i18n';

const DEFAULT_ADVANTAGES = [
  { text: '', icon: '' },
  { text: '', icon: '' },
  { text: '', icon: '' },
];

export default function AdvantagesSheet({ data, onChange, onClose }) {
  const { tr } = useI18n();
  const advantages = data.advantages?.length > 0 ? [...data.advantages] : DEFAULT_ADVANTAGES;
  const [slots, setSlots] = useState(advantages.slice(0, 3).concat(
    DEFAULT_ADVANTAGES.slice(advantages.slice(0, 3).length)
  ));
  const [templates, setTemplates] = useState(null);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [activeSlot, setActiveSlot] = useState(null);

  function updateSlot(i, field, value) {
    const updated = slots.map((s, idx) => idx === i ? { ...s, [field]: value } : s);
    setSlots(updated);
    onChange('advantages', updated);
  }

  function pickTemplate(tpl) {
    if (activeSlot === null) return;
    updateSlot(activeSlot, 'text', tpl.text);
    updateSlot(activeSlot, 'icon', tpl.icon || '✓');
    setActiveSlot(null);
    setTemplates(null);
  }

  async function loadTemplates(slotIdx) {
    setActiveSlot(slotIdx);
    if (templates) return; // already loaded
    setLoadingTemplates(true);
    try {
      const res = await getPromoAdvantages();
      setTemplates(res?.advantages || []);
    } finally {
      setLoadingTemplates(false);
    }
  }

  if (templates !== null) {
    return (
      <div className="sheet-form">
        <div className="sheet-section-label">{tr('Выберите преимущество', 'Select advantage')}</div>
        {loadingTemplates && <p className="sheet-hint">{tr('Загрузка...', 'Loading...')}</p>}
        <div className="adv-template-list">
          {templates.map((tpl, i) => (
            <button
              key={i}
              type="button"
              className={`adv-template-item${tpl.is_suggested ? ' is-suggested' : ''}`}
              onClick={() => pickTemplate(tpl)}
            >
              <span className="adv-template-icon">{tpl.icon || '✓'}</span>
              <span className="adv-template-text">{tpl.text}</span>
              {tpl.is_suggested && <span className="adv-suggested-badge">{tr('для вас', 'for you')}</span>}
            </button>
          ))}
        </div>
        <button type="button" className="sheet-btn" onClick={() => { setTemplates(null); setActiveSlot(null); }}>
          {tr('Назад', 'Back')}
        </button>
      </div>
    );
  }

  return (
    <div className="sheet-form">
      <div className="sheet-section-label">{tr('Преимущества (3 штуки)', 'Advantages (3 items)')}</div>

      {slots.map((slot, i) => (
        <div key={i} className="adv-slot">
          <div className="adv-slot-row">
            <span className="adv-slot-icon">{slot.icon || '✓'}</span>
            <input
              className="sheet-input adv-slot-input"
              type="text"
              value={slot.text}
              maxLength={60}
              placeholder={tr('Текст преимущества', 'Advantage text')}
              onChange={(e) => updateSlot(i, 'text', e.target.value)}
            />
          </div>
          <button
            type="button"
            className="adv-slot-pick"
            onClick={() => loadTemplates(i)}
          >
            {tr('Выбрать из шаблонов', 'Choose from templates')}
          </button>
        </div>
      ))}

      <button type="button" className="sheet-btn sheet-btn--done" onClick={onClose}>
        {tr('Готово', 'Done')}
      </button>

      <style>{`
        .adv-slot { display: flex; flex-direction: column; gap: 6px; padding: 10px 0; border-bottom: 1px solid var(--master-border); }
        .adv-slot-row { display: flex; align-items: center; gap: 10px; }
        .adv-slot-icon { font-size: 20px; min-width: 28px; text-align: center; }
        .adv-slot-input { flex: 1; }
        .adv-slot-pick { background: none; border: none; color: var(--master-accent); font-size: 13px; cursor: pointer; text-align: left; padding: 0; }
        .adv-template-list { display: flex; flex-direction: column; gap: 2px; max-height: 50vh; overflow-y: auto; }
        .adv-template-item { display: flex; align-items: center; gap: 10px; background: var(--master-bg-surface); border: 1px solid transparent; border-radius: 10px; padding: 10px 12px; cursor: pointer; text-align: left; font-size: 14px; color: var(--master-text-primary); }
        .adv-template-item.is-suggested { border: 1px solid var(--master-accent); background: var(--master-accent-8); }
        .adv-template-icon { font-size: 18px; min-width: 26px; }
        .adv-template-text { flex: 1; }
        .adv-suggested-badge { font-size: 11px; color: var(--master-accent); white-space: nowrap; }
      `}</style>
    </div>
  );
}
