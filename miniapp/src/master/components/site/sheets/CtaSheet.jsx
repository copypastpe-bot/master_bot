export default function CtaSheet({ data, onChange, onClose }) {
  const len = (data.sub_button_text || '').length;

  return (
    <div className="sheet-form">
      <div className="sheet-field">
        <label className="sheet-label">Текст под кнопкой</label>
        <input
          className="sheet-input"
          type="text"
          value={data.sub_button_text || ''}
          maxLength={60}
          placeholder="Бесплатно · Без спама · Отписка в 1 клик"
          onChange={(e) => onChange('sub_button_text', e.target.value)}
        />
        <span className="sheet-counter">{len}/60</span>
      </div>

      <p className="sheet-hint">Например: «Бесплатно · Без спама · Отписка в 1 клик»</p>

      <button type="button" className="sheet-btn sheet-btn--done" onClick={onClose}>
        Готово
      </button>
    </div>
  );
}
