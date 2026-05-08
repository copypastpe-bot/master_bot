import { useI18n } from '../../../../i18n';

export default function PromoSheet({ data, onChange, onClose }) {
  const { tr } = useI18n();

  return (
    <div className="sheet-form">
      <div className="sheet-field sheet-field--toggle">
        <label className="sheet-label">{tr('Показать акцию', 'Show promo')}</label>
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
          <label className="sheet-label">{tr('Текст акции', 'Promo text')}</label>
          <input
            className="sheet-input"
            type="text"
            value={data.promo_text || ''}
            maxLength={60}
            placeholder={tr('Скидка 20% новым клиентам', '20% off for new clients')}
            onChange={(e) => onChange('promo_text', e.target.value)}
          />
        </div>
      )}

      <button type="button" className="sheet-btn sheet-btn--done" onClick={onClose}>
        {tr('Готово', 'Done')}
      </button>
    </div>
  );
}
