import { useI18n } from '../../../../i18n';

export default function TaglineSheet({ data, onChange, onClose }) {
  const { tr } = useI18n();
  const len = (data.tagline || '').length;
  const isWarning = len > 100;

  return (
    <div className="sheet-form">
      <div className="sheet-field">
        <label className="sheet-label">{tr('Краткое описание (УТП)', 'Short description (USP)')}</label>
        <textarea
          className="sheet-input sheet-textarea"
          value={data.tagline || ''}
          maxLength={120}
          rows={3}
          placeholder={tr('Коротко опишите свою главную ценность для клиента', 'Briefly describe your main value for clients')}
          onChange={(e) => onChange('tagline', e.target.value)}
        />
        <span
          className="sheet-counter"
          style={{ color: isWarning ? 'var(--tg-theme-destructive-text-color, #e53935)' : undefined }}
        >
          {len}/120
        </span>
      </div>

      <button type="button" className="sheet-btn sheet-btn--done" onClick={onClose}>
        {tr('Готово', 'Done')}
      </button>
    </div>
  );
}
