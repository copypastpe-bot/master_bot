export default function IdentitySheet({ data, onChange, onClose }) {
  return (
    <div className="sheet-form">
      <div className="sheet-field">
        <label className="sheet-label">Имя / название</label>
        <input
          className="sheet-input"
          type="text"
          value={data.display_name || ''}
          maxLength={60}
          placeholder="Ваше имя"
          onChange={(e) => onChange('display_name', e.target.value)}
        />
      </div>

      <div className="sheet-field">
        <label className="sheet-label">Специализация</label>
        <input
          className="sheet-input"
          type="text"
          value={data.specialization || ''}
          maxLength={80}
          placeholder="Например: Частный клинер"
          onChange={(e) => onChange('specialization', e.target.value)}
        />
      </div>

      <button type="button" className="sheet-btn sheet-btn--done" onClick={onClose}>
        Готово
      </button>
    </div>
  );
}
