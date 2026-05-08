export default function TaglineSheet({ data, onChange, onClose }) {
  const len = (data.tagline || '').length;
  const isWarning = len > 100;

  return (
    <div className="sheet-form">
      <div className="sheet-field">
        <label className="sheet-label">Краткое описание (УТП)</label>
        <textarea
          className="sheet-input sheet-textarea"
          value={data.tagline || ''}
          maxLength={120}
          rows={3}
          placeholder="Коротко опишите свою главную ценность для клиента"
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
        Готово
      </button>
    </div>
  );
}
