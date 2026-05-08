export default function PromoSheet({ data, onChange, onClose }) {
  return (
    <div className="sheet-form">
      <div className="sheet-field sheet-field--toggle">
        <label className="sheet-label">Показать акцию</label>
        <label className="sheet-toggle">
          <input
            type="checkbox"
            checked={!!data.promo_enabled}
            onChange={(e) => onChange('promo_enabled', e.target.checked)}
          />
          <span className="sheet-toggle__track" />
        </label>
      </div>

      {data.promo_enabled && (
        <div className="sheet-field">
          <label className="sheet-label">Текст акции</label>
          <input
            className="sheet-input"
            type="text"
            value={data.promo_text || ''}
            maxLength={60}
            placeholder="Скидка 20% новым клиентам"
            onChange={(e) => onChange('promo_text', e.target.value)}
          />
        </div>
      )}

      <button type="button" className="sheet-btn sheet-btn--done" onClick={onClose}>
        Готово
      </button>
    </div>
  );
}
