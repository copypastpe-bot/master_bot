import { useI18n } from '../../../../i18n';

export default function ServiceSheet({ data, onChange, onClose }) {
  const { tr } = useI18n();

  return (
    <div className="sheet-form">
      <div className="sheet-field">
        <label className="sheet-label">{tr('Популярная услуга', 'Popular service')}</label>
        <input
          className="sheet-input"
          type="text"
          value={data.service_name || ''}
          maxLength={100}
          placeholder={tr('Название услуги', 'Service name')}
          onChange={(e) => onChange('service_name', e.target.value)}
        />
      </div>

      <div className="sheet-field">
        <label className="sheet-label">{tr('Цена', 'Price')}</label>
        <input
          className="sheet-input"
          type="text"
          value={data.service_price || ''}
          maxLength={30}
          placeholder={tr('от 3000 ₽, 500 ₽/час', 'from $50, $100/hr')}
          onChange={(e) => onChange('service_price', e.target.value)}
        />
      </div>

      <button type="button" className="sheet-btn sheet-btn--done" onClick={onClose}>
        {tr('Готово', 'Done')}
      </button>
    </div>
  );
}
