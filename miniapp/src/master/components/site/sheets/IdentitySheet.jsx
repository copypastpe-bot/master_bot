import { useI18n } from '../../../../i18n';

export default function IdentitySheet({ data, onChange, onClose }) {
  const { tr } = useI18n();

  return (
    <div className="sheet-form">
      <div className="sheet-field">
        <label className="sheet-label">{tr('Имя / название', 'Name / title')}</label>
        <input
          className="sheet-input"
          type="text"
          value={data.display_name || ''}
          maxLength={60}
          placeholder={tr('Ваше имя', 'Your name')}
          onChange={(e) => onChange('display_name', e.target.value)}
        />
      </div>

      <div className="sheet-field">
        <label className="sheet-label">{tr('Специализация', 'Specialization')}</label>
        <input
          className="sheet-input"
          type="text"
          value={data.specialization || ''}
          maxLength={80}
          placeholder={tr('Например: Частный клинер', 'E.g.: Personal trainer')}
          onChange={(e) => onChange('specialization', e.target.value)}
        />
      </div>

      <button type="button" className="sheet-btn sheet-btn--done" onClick={onClose}>
        {tr('Готово', 'Done')}
      </button>
    </div>
  );
}
