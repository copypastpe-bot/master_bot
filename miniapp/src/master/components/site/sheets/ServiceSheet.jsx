export default function ServiceSheet({ data, onChange, onClose }) {
  return (
    <div className="sheet-form">
      <div className="sheet-field">
        <label className="sheet-label">Популярная услуга</label>
        <input
          className="sheet-input"
          type="text"
          value={data.service_name || ''}
          maxLength={100}
          placeholder="Название услуги"
          onChange={(e) => onChange('service_name', e.target.value)}
        />
      </div>

      <div className="sheet-field">
        <label className="sheet-label">Цена</label>
        <input
          className="sheet-input"
          type="text"
          value={data.service_price || ''}
          maxLength={30}
          placeholder="от 3000 ₽, 500 ₽/час"
          onChange={(e) => onChange('service_price', e.target.value)}
        />
      </div>

      <button type="button" className="sheet-btn sheet-btn--done" onClick={onClose}>
        Готово
      </button>
    </div>
  );
}
