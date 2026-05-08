import { useI18n } from '../../../i18n';

export default function CtaSheet({ data, onChange, onClose }) {
  const { tr } = useI18n();
  const len = (data.sub_button_text || '').length;

  return (
    <div className="sheet-form">
      <div className="sheet-field">
        <label className="sheet-label">{tr('Текст под кнопкой', 'Text below button')}</label>
        <input
          className="sheet-input"
          type="text"
          value={data.sub_button_text || ''}
          maxLength={60}
          placeholder={tr('Бесплатно · Без спама · Отписка в 1 клик', 'Free · No spam · Unsubscribe anytime')}
          onChange={(e) => onChange('sub_button_text', e.target.value)}
        />
        <span className="sheet-counter">{len}/60</span>
      </div>

      <p className="sheet-hint">{tr('Например: «Бесплатно · Без спама · Отписка в 1 клик»', 'E.g.: «Free · No spam · Unsubscribe anytime»')}</p>

      <button type="button" className="sheet-btn sheet-btn--done" onClick={onClose}>
        {tr('Готово', 'Done')}
      </button>
    </div>
  );
}
