import { useMemo } from 'react';
import { useI18n } from '../../i18n';

export default function CategoryPicker({
  categories = [],
  selectedCategoryIds = [],
  customNames = {},
  maxCount = 3,
  onChange,
  onSave,
  onCancel,
  loading = false,
  showActions = false,
  saveLabel,
}) {
  const { tr } = useI18n();
  const otherCategory = useMemo(() => categories.find((category) => category.slug === 'other'), [categories]);
  const otherSelected = Boolean(otherCategory && selectedCategoryIds.includes(otherCategory.id));

  const emitChange = (nextIds, nextCustomNames = customNames) => {
    onChange?.({
      category_ids: nextIds,
      custom_names: nextCustomNames,
    });
  };

  const toggleCategory = (category) => {
    if (loading) return;
    const isSelected = selectedCategoryIds.includes(category.id);
    if (isSelected) {
      const nextIds = selectedCategoryIds.filter((id) => id !== category.id);
      const nextCustomNames = { ...customNames };
      delete nextCustomNames[category.id];
      emitChange(nextIds, nextCustomNames);
      return;
    }
    if (selectedCategoryIds.length >= maxCount) return;
    emitChange([...selectedCategoryIds, category.id]);
  };

  const handleCustomName = (value) => {
    if (!otherCategory) return;
    emitChange(selectedCategoryIds, {
      ...customNames,
      [otherCategory.id]: value,
    });
  };

  return (
    <div className="master-category-picker">
      <div className="master-category-picker-grid">
        {categories.map((category) => {
          const isSelected = selectedCategoryIds.includes(category.id);
          const isDisabled = loading || (!isSelected && selectedCategoryIds.length >= maxCount);
          return (
            <button
              key={category.id}
              type="button"
              className={`master-category-chip${isSelected ? ' is-selected' : ''}`}
              disabled={isDisabled}
              onClick={() => toggleCategory(category)}
            >
              <span className="master-category-chip-icon">{category.icon || '•'}</span>
              <span>{category.name}</span>
            </button>
          );
        })}
      </div>

      {otherSelected && (
        <label className="master-category-custom">
          <span>{tr('Своя ниша', 'Your niche')}</span>
          <input
            value={customNames[otherCategory.id] || ''}
            maxLength={100}
            onChange={(event) => handleCustomName(event.target.value)}
            placeholder={tr('Напишите вашу нишу', 'Write your niche')}
            disabled={loading}
          />
        </label>
      )}

      {showActions && (
        <div className="enterprise-sheet-actions">
          <button type="button" className="enterprise-sheet-btn secondary" onClick={onCancel} disabled={loading}>
            {tr('Отмена', 'Cancel')}
          </button>
          <button type="button" className="enterprise-sheet-btn primary" onClick={onSave} disabled={loading}>
            {loading ? tr('Сохраняем...', 'Saving...') : (saveLabel || tr('Сохранить', 'Save'))}
          </button>
        </div>
      )}
    </div>
  );
}
