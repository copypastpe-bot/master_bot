import { useState } from 'react';
import { getPromoAdvantages } from '../../../../api/client';

const DEFAULT_ADVANTAGES = [
  { text: '', icon: '' },
  { text: '', icon: '' },
  { text: '', icon: '' },
];

export default function AdvantagesSheet({ data, onChange, onClose }) {
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
        <div className="sheet-section-label">Выберите преимущество</div>
        {loadingTemplates && <p className="sheet-hint">Загрузка...</p>}
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
              {tpl.is_suggested && <span className="adv-suggested-badge">для вас</span>}
            </button>
          ))}
        </div>
        <button type="button" className="sheet-btn" onClick={() => { setTemplates(null); setActiveSlot(null); }}>
          Назад
        </button>
      </div>
    );
  }

  return (
    <div className="sheet-form">
      <div className="sheet-section-label">Преимущества (3 штуки)</div>

      {slots.map((slot, i) => (
        <div key={i} className="adv-slot">
          <div className="adv-slot-row">
            <span className="adv-slot-icon">{slot.icon || '✓'}</span>
            <input
              className="sheet-input adv-slot-input"
              type="text"
              value={slot.text}
              maxLength={60}
              placeholder="Текст преимущества"
              onChange={(e) => updateSlot(i, 'text', e.target.value)}
            />
          </div>
          <button
            type="button"
            className="adv-slot-pick"
            onClick={() => loadTemplates(i)}
          >
            Выбрать из шаблонов
          </button>
        </div>
      ))}

      <button type="button" className="sheet-btn sheet-btn--done" onClick={onClose}>
        Готово
      </button>

      <style>{`
        .adv-slot { display: flex; flex-direction: column; gap: 6px; padding: 10px 0; border-bottom: 1px solid var(--tg-theme-secondary-bg-color, #f4f4f4); }
        .adv-slot-row { display: flex; align-items: center; gap: 10px; }
        .adv-slot-icon { font-size: 20px; min-width: 28px; text-align: center; }
        .adv-slot-input { flex: 1; }
        .adv-slot-pick { background: none; border: none; color: var(--tg-theme-accent-text-color, #2481cc); font-size: 13px; cursor: pointer; text-align: left; padding: 0; }
        .adv-template-list { display: flex; flex-direction: column; gap: 2px; max-height: 50vh; overflow-y: auto; }
        .adv-template-item { display: flex; align-items: center; gap: 10px; background: var(--tg-theme-secondary-bg-color, #f4f4f4); border: none; border-radius: 10px; padding: 10px 12px; cursor: pointer; text-align: left; font-size: 14px; color: var(--tg-theme-text-color, #000); }
        .adv-template-item.is-suggested { border: 1px solid var(--tg-theme-accent-text-color, #2481cc); }
        .adv-template-icon { font-size: 18px; min-width: 26px; }
        .adv-template-text { flex: 1; }
        .adv-suggested-badge { font-size: 11px; color: var(--tg-theme-accent-text-color, #2481cc); white-space: nowrap; }
      `}</style>
    </div>
  );
}
