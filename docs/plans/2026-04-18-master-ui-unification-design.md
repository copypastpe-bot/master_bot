# Master UI Unification — Design Document

## Goal

Привести мастер-часть Mini App к единому визуальному стилю: убрать inline-стили из Dashboard, перевести FeedbackSettings с onb- классов на enterprise- классы, точечно исправить section titles в нескольких страницах.

## Принципы

- Не переключаем тему и не переписываем сложные страницы (OrderCreate, OrderDetail, Broadcast, ClientCard)
- Используем существующую enterprise-CSS-систему, добавляем только то, чего не хватает
- Каждое изменение должно работать в тёмном и светлом режиме Telegram (CSS-переменные, не хардкод)

## Затронутые файлы

### theme.css — новые классы (добавляем в конец enterprise-блока)
- `enterprise-page` — wrapper страницы без горизонтального padding (`padding: 12px 0 100px`)
- `enterprise-page-inner` — inner-блок с горизонтальным padding (`padding: 0 12px`)
- `enterprise-page-title` — 20px, 700, `var(--tg-text)`
- `enterprise-page-subtitle` — 13px, `var(--tg-hint)`, margin-top 4px
- `enterprise-stat-grid` — CSS Grid 2 колонки, gap 8px, margin-bottom 24px
- `enterprise-info-card` — карточка-баннер (`var(--tg-secondary-bg)`, border, radius-card, padding 14px)
- `enterprise-orders-section` — section wrapper, margin-bottom 20px
- `enterprise-section-count` — span с count "(1 зап.)", 13px hint color
- `enterprise-input` — text input (те же стили что `onb-input` — перенесём под enterprise-имя)
- `enterprise-form-field` — field wrapper с padding `0 16px 12px` (аналог `onb-field-group`)
- `enterprise-btn-primary` — primary button (аналог `onb-btn-primary`)
- `enterprise-btn-secondary` — secondary button (аналог `onb-btn-secondary`)

### Dashboard.jsx
- Весь JSX переводится на CSS классы
- `OrdersSection` компонент: h3 → `enterprise-section-title`, orders div → `enterprise-cell-group`
- `DashboardSkeleton` обновляется под новую структуру

### FeedbackSettings.jsx
- `onb-field-group` → `enterprise-form-field`
- `onb-label` убираем (описание секции уже даёт `enterprise-section-title`)
- `onb-input` → `enterprise-input`
- `enterprise-sheet-input` (textarea) → `enterprise-input`
- `onb-btn-primary` → `enterprise-btn-primary`
- `onb-btn-secondary` → `enterprise-btn-secondary`

### ClientsList.jsx
- Строка 104: inline section title div → `enterprise-section-title`

### PromosList.jsx
- Список акций рендерится в карточках: обернуть в `enterprise-cell-group` где необходимо

## Что НЕ меняем
- `MasterOnboarding.jsx` — сохраняет `onb-*` (это его родной контекст)
- `OrderCreate.jsx`, `OrderDetail.jsx`, `Broadcast.jsx`, `ClientCard.jsx`, `Reports.jsx` — слишком сложные, риск > польза
- Существующие `enterprise-subscription-card`, `enterprise-cell`, `enterprise-cell-group` — не трогаем
