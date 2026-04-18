# Master UI Unification — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Привести мастер Mini App к единому стилю — убрать inline-стили из Dashboard, переименовать onb-→enterprise- в FeedbackSettings, точечно починить section titles.

**Architecture:** Добавляем новые CSS-классы в конец enterprise-блока в theme.css. Переписываем Dashboard.jsx и FeedbackSettings.jsx. Точечные правки в ClientsList.jsx и PromosList.jsx. Сложные страницы (OrderCreate, OrderDetail, Broadcast) — не трогаем.

**Tech Stack:** React + Vite + plain CSS (CSS-переменные Telegram WebApp)

---

### Task 1: Добавить новые CSS-классы в theme.css

**Files:**
- Modify: `miniapp/src/theme.css` (добавить в конец блока enterprise, перед последними секциями)

**Step 1: Найти правильное место в theme.css**

Открыть `miniapp/src/theme.css`, найти строку:
```
body.typeui-enterprise-body .onb-field-group {
```
Новые классы добавить ПЕРЕД этой строкой (или после последнего `enterprise-` класса, но перед `onb-` секцией).

**Step 2: Добавить классы страниц и типографики**

```css
/* ── Dashboard page layout ── */
body.typeui-enterprise-body .enterprise-page {
  padding: 12px 0 100px;
}

body.typeui-enterprise-body .enterprise-page-inner {
  padding: 0 12px;
}

body.typeui-enterprise-body .enterprise-page-title {
  color: var(--tg-text);
  font-size: 20px;
  font-weight: 700;
  margin: 0;
}

body.typeui-enterprise-body .enterprise-page-subtitle {
  color: var(--tg-hint);
  font-size: 13px;
  margin: 4px 0 0;
}

body.typeui-enterprise-body .enterprise-stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin: 0 12px 24px;
}

body.typeui-enterprise-body .enterprise-info-card {
  margin: 0 12px 16px;
  background: var(--tg-secondary-bg);
  border: 1px solid var(--tg-enterprise-border);
  border-radius: var(--radius-card);
  padding: 14px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

body.typeui-enterprise-body .enterprise-orders-section {
  margin-bottom: 20px;
}

body.typeui-enterprise-body .enterprise-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 16px;
}

body.typeui-enterprise-body .enterprise-section-count {
  color: var(--tg-hint);
  font-size: 13px;
}

body.typeui-enterprise-body .enterprise-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 12px;
}
```

**Step 3: Добавить классы форм и кнопок**

```css
/* ── Enterprise form fields (replaces onb- in app pages) ── */
body.typeui-enterprise-body .enterprise-form-field {
  padding: 0 16px 12px;
}

body.typeui-enterprise-body .enterprise-input {
  width: 100%;
  border-radius: 12px;
  border: 1.5px solid var(--tg-enterprise-border);
  background: var(--tg-section-bg);
  color: var(--tg-text);
  font-size: 16px;
  line-height: 1.2;
  padding: 12px 13px;
  outline: none;
  font-family: inherit;
}

body.typeui-enterprise-body .enterprise-input::placeholder {
  color: var(--tg-hint);
}

body.typeui-enterprise-body .enterprise-input:focus {
  border-color: var(--tg-accent);
}

body.typeui-enterprise-body .enterprise-btn-primary {
  width: 100%;
  border: none;
  border-radius: 12px;
  background: var(--tg-button);
  color: var(--tg-button-text);
  font-size: 15px;
  font-weight: 700;
  padding: 13px 14px;
  cursor: pointer;
  transition: transform 140ms ease, opacity 140ms ease;
  font-family: inherit;
}

body.typeui-enterprise-body .enterprise-btn-primary:disabled {
  opacity: 0.48;
  cursor: default;
}

body.typeui-enterprise-body .enterprise-btn-primary:not(:disabled):active {
  transform: scale(0.99);
}

body.typeui-enterprise-body .enterprise-btn-secondary {
  width: 100%;
  border-radius: 12px;
  border: 1.5px solid var(--tg-enterprise-border);
  background: transparent;
  color: var(--tg-hint);
  font-size: 15px;
  font-weight: 600;
  padding: 12px 14px;
  margin-top: 8px;
  cursor: pointer;
  font-family: inherit;
}

body.typeui-enterprise-body .enterprise-btn-secondary:disabled {
  opacity: 0.5;
  cursor: default;
}
```

**Step 4: Проверить что CSS компилируется**

```bash
cd miniapp && npm run build 2>&1 | tail -5
```

Ожидаем: `✓ built in ...` без ошибок.

**Step 5: Commit**

```bash
git add miniapp/src/theme.css
git commit -m "style(master): add enterprise page/form/button CSS classes for unification"
```

---

### Task 2: Переписать Dashboard.jsx на CSS классы

**Files:**
- Modify: `miniapp/src/master/pages/Dashboard.jsx`

**Step 1: Прочитать текущий файл полностью**

Открыть `miniapp/src/master/pages/Dashboard.jsx` и изучить структуру компонентов: `DashboardSkeleton`, `OrdersSection`, `DashboardContent`.

**Step 2: Переписать OrdersSection**

Заменить компонент `OrdersSection` (строки ~28–81):

```jsx
function OrdersSection({ title, orders, onNavigate, emptyContent, tr }) {
  return (
    <div className="enterprise-orders-section">
      <div className="enterprise-section-header">
        <div className="enterprise-section-title">{title}</div>
        {orders.length > 0 && (
          <span className="enterprise-section-count">
            {tr(`${orders.length} зап.`, `${orders.length} bookings`)}
          </span>
        )}
      </div>

      {orders.length === 0 ? (
        <div className="enterprise-cell-group" style={{ margin: '0 12px' }}>
          <div style={{ padding: '14px 16px', color: 'var(--tg-hint)', fontSize: 14, textAlign: 'center' }}>
            {emptyContent ?? tr('Свободный день! 🎉', 'Free day! 🎉')}
          </div>
        </div>
      ) : (
        <div className="enterprise-cell-group" style={{ margin: '0 12px' }}>
          {orders.map((order, idx) => (
            <OrderCard
              key={order.id}
              order={order}
              onClick={() => onNavigate('order', { id: order.id })}
              style={idx === orders.length - 1 ? { borderBottom: 'none' } : {}}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 3: Переписать DashboardSkeleton**

```jsx
function DashboardSkeleton() {
  return (
    <div className="enterprise-page">
      <div className="enterprise-page-inner" style={{ marginBottom: 20 }}>
        <Skeleton height={24} style={{ width: '55%', marginBottom: 6 }} />
        <Skeleton height={14} style={{ width: '35%' }} />
      </div>
      <div className="enterprise-stat-grid">
        <Skeleton height={80} />
        <Skeleton height={80} />
        <Skeleton height={80} />
        <Skeleton height={80} />
      </div>
      <div className="enterprise-section-title" style={{ visibility: 'hidden' }}>—</div>
      <div className="enterprise-cell-group" style={{ margin: '0 12px', marginBottom: 20 }}>
        <Skeleton height={64} />
      </div>
      <div className="enterprise-section-title" style={{ visibility: 'hidden' }}>—</div>
      <div className="enterprise-cell-group" style={{ margin: '0 12px' }}>
        <Skeleton height={64} />
      </div>
    </div>
  );
}
```

**Step 4: Переписать DashboardContent**

Заменить JSX внутри `DashboardContent` (return внутри компонента, строки ~251–478):

```jsx
return (
  <div className="enterprise-page">
    {/* Onboarding banner */}
    {showBanner && (
      <div className="enterprise-info-card" style={{ alignItems: 'center', gap: 10 }}>
        <p style={{ flex: 1, color: 'var(--tg-text)', fontSize: 13, margin: 0, lineHeight: 1.4 }}>
          {tr('Добавь первого клиента, чтобы увидеть как работают напоминания', 'Add your first client to see how reminders work')}
        </p>
        <button
          onClick={handleBannerAdd}
          style={{ background: 'var(--tg-button)', color: 'var(--tg-button-text)', border: 'none', borderRadius: 8, padding: '7px 12px', fontSize: 13, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap' }}
        >
          {tr('Добавить →', 'Add ->')}
        </button>
        <button
          onClick={handleBannerDismiss}
          style={{ background: 'none', border: 'none', color: 'var(--tg-hint)', fontSize: 18, cursor: 'pointer', padding: '0 2px', lineHeight: 1 }}
        >
          ×
        </button>
      </div>
    )}

    {/* Greeting */}
    <div className="enterprise-page-inner" style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <h2 className="enterprise-page-title">
          {tr('Привет', 'Hello')}, {data?.master_name || ''}!
        </h2>
        <span style={{ color: isSubscriptionActive ? '#2f74d2' : '#888888', fontSize: 24, lineHeight: 1 }}>★</span>
      </div>
      <p className="enterprise-page-subtitle">{formatDate(today, locale)}</p>
    </div>

    {/* Stats */}
    {totalDoneOrders > 0 ? (
      <div className="enterprise-stat-grid">
        <StatCard icon="💰" value={formatCurrency(stats.week_revenue || 0, locale)} label={tr('Выручка за неделю', 'Revenue this week')} onClick={handleReportsWeek} />
        <StatCard icon="📅" value={formatCurrency(stats.month_revenue || 0, locale)} label={tr('Выручка за месяц', 'Revenue this month')} onClick={handleReportsMonth} />
        <StatCard icon="✅" value={stats.week_orders || 0} label={tr('Заказов за неделю', 'Orders this week')} />
        <StatCard icon="👥" value={stats.total_clients || 0} label={tr('Всего клиентов', 'Total clients')} onClick={handleClients} />
      </div>
    ) : (
      <div className="enterprise-info-card">
        <span style={{ fontSize: 24, lineHeight: 1 }}>📊</span>
        <p style={{ color: 'var(--tg-hint)', fontSize: 14, margin: 0, lineHeight: 1.4 }}>
          {tr('Выполни первый заказ и увидишь показатели своей работы в цифрах', 'Complete your first order to see your performance in numbers')}
        </p>
      </div>
    )}

    {/* Today's orders */}
    <OrdersSection
      title={tr('Сегодня', 'Today')}
      orders={todayOrders}
      onNavigate={onNavigate}
      tr={tr}
      emptyContent={
        totalDoneOrders === 0 && todayOrders.length === 0 && tomorrowOrders.length === 0
          ? (
            <div>
              <p style={{ margin: '0 0 10px', color: 'var(--tg-hint)' }}>
                {tr('Пока записей нет', 'No bookings yet')}
              </p>
              <button
                onClick={handleNewOrder}
                style={{ background: isSubscriptionActive ? 'var(--tg-button)' : 'var(--tg-secondary-bg)', color: isSubscriptionActive ? 'var(--tg-button-text)' : 'var(--tg-hint)', border: isSubscriptionActive ? 'none' : '1px solid var(--tg-enterprise-border)', borderRadius: 8, padding: '8px 16px', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}
              >
                {tr('+ Добавить первую запись', '+ Add first booking')}
              </button>
            </div>
          )
          : todayOrders.length === 0
            ? tr('Записей на сегодня нет', 'No bookings for today')
            : null
      }
    />

    {/* Tomorrow's orders */}
    <OrdersSection
      title={tr('Завтра', 'Tomorrow')}
      orders={tomorrowOrders}
      onNavigate={onNavigate}
      tr={tr}
      emptyContent={tr('Записей на завтра нет', 'No bookings for tomorrow')}
    />

    {/* Actions */}
    <div className="enterprise-actions">
      <button
        onClick={handleNewOrder}
        className="enterprise-btn-primary"
        style={!isSubscriptionActive ? { background: 'var(--tg-secondary-bg)', color: 'var(--tg-hint)' } : {}}
      >
        {tr('+ Новый заказ', '+ New order')}
      </button>

      {(stats.pending_requests || 0) > 0 && (
        <button
          onClick={handleRequests}
          style={{ background: 'var(--tg-surface)', color: 'var(--tg-button)', border: '1.5px solid var(--tg-button)', borderRadius: 12, padding: '14px', fontSize: 15, fontWeight: 600, cursor: 'pointer', width: '100%' }}
        >
          {tr(`Новые заявки (${stats.pending_requests})`, `New requests (${stats.pending_requests})`)}
        </button>
      )}
    </div>

    <SubscriptionPaywallSheet
      open={paywallOpen}
      onClose={() => setPaywallOpen(false)}
      onPay={handlePaywallPay}
      onInvite={handlePaywallInvite}
    />
  </div>
);
```

**Step 5: Также переписать error-state в Dashboard**

Найти блок error-state (строки ~123–150) и заменить:

```jsx
if (isError) {
  return (
    <div className="enterprise-page enterprise-page-inner" style={{ textAlign: 'center', paddingTop: 48 }}>
      <p style={{ color: 'var(--tg-text)', marginBottom: 8 }}>
        {tr('Не удалось загрузить данные', 'Failed to load data')}
      </p>
      <button className="enterprise-btn-primary" onClick={() => { WebApp?.HapticFeedback?.impactOccurred?.('light'); refetch(); }}>
        {tr('Повторить', 'Retry')}
      </button>
    </div>
  );
}
```

**Step 6: Проверить build**

```bash
cd miniapp && npm run build 2>&1 | tail -5
```

Ожидаем: `✓ built in ...` без ошибок.

**Step 7: Commit**

```bash
git add miniapp/src/master/pages/Dashboard.jsx
git commit -m "style(master): rewrite Dashboard.jsx inline styles to CSS classes"
```

---

### Task 3: Переписать FeedbackSettings.jsx

**Files:**
- Modify: `miniapp/src/master/pages/FeedbackSettings.jsx`

**Step 1: Прочитать файл**

Открыть `miniapp/src/master/pages/FeedbackSettings.jsx`. Запомнить структуру: `enterprise-profile-page` → секции с `enterprise-cell-group` → поля с `onb-*` классами → кнопка сохранить.

**Step 2: Заменить onb- классы на enterprise-**

Произвести следующие замены во всём файле:

| Было | Стало |
|---|---|
| `className="onb-field-group"` | `className="enterprise-form-field"` |
| `className="onb-label"` | убрать label-элемент полностью (описание секции уже даёт `enterprise-section-title`) |
| `className="onb-input"` | `className="enterprise-input"` |
| `className="enterprise-sheet-input"` | `className="enterprise-input"` |
| `className="onb-btn-primary"` | `className="enterprise-btn-primary"` |
| `className="onb-btn-secondary"` | `className="enterprise-btn-secondary"` |

Обёртку кнопки сохранить (`div style={{ padding: '16px' }}`) — оставить как есть (это spacing, не стиль).

Для секции `onb-field-group` с `style={{ padding: '0 16px 12px' }}` — класс `enterprise-form-field` уже содержит этот padding, поэтому inline style удалить.

**Step 3: Убрать onb-label внутри cell-group**

В текущем FeedbackSettings.jsx каждый `enterprise-cell-group` содержит `onb-field-group` с `onb-label` (описание поля). После замены на `enterprise-form-field` label можно убрать — описание уже даёт `enterprise-section-title` над блоком. Если label несёт уникальную информацию (например, для кнопок с индексом), оставить `<label>` без класса, с inline `style={{ display: 'block', marginBottom: 6, color: 'var(--tg-hint)', fontSize: 12, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}`.

**Step 4: Проверить build**

```bash
cd miniapp && npm run build 2>&1 | tail -5
```

Ожидаем: без ошибок.

**Step 5: Commit**

```bash
git add miniapp/src/master/pages/FeedbackSettings.jsx
git commit -m "style(master): replace onb- classes with enterprise- in FeedbackSettings"
```

---

### Task 4: Точечные правки ClientsList.jsx и PromosList.jsx

**Files:**
- Modify: `miniapp/src/master/pages/ClientsList.jsx`
- Modify: `miniapp/src/master/pages/PromosList.jsx`

**Step 1: ClientsList.jsx — заменить inline section title**

Найти строку ~104:
```jsx
<div style={{ fontSize: 12, color: 'var(--tg-hint)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '8px 16px' }}>
```

Заменить на:
```jsx
<div className="enterprise-section-title">
```

**Step 2: PromosList.jsx — проверить section titles**

Открыть `miniapp/src/master/pages/PromosList.jsx`. Найти все `style={{ ... textTransform: 'uppercase'...}}` или подобные inline section headers. Заменить на `enterprise-section-title`.

Для card-контейнеров акций — если есть `div` с `background: var(--tg-section-bg), borderRadius, padding` — заменить на `enterprise-cell-group`.

**Step 3: Проверить build**

```bash
cd miniapp && npm run build 2>&1 | tail -5
```

**Step 4: Commit**

```bash
git add miniapp/src/master/pages/ClientsList.jsx miniapp/src/master/pages/PromosList.jsx
git commit -m "style(master): use enterprise-section-title in ClientsList and PromosList"
```

---

### Task 5: Deploy и визуальная проверка

**Step 1: Итоговый git status**

```bash
git status --short
```

Ожидаем: чистый worktree (всё закоммичено).

**Step 2: Push и deploy фронта**

```bash
git push && bash deploy_miniapp.sh
```

**Step 3: Визуальная проверка в Telegram**

Открыть мастер Mini App и проверить:
- [ ] Dashboard: section titles "СЕГОДНЯ" / "ЗАВТРА" в uppercase hint-цвете
- [ ] Dashboard: stat-карточки в 2-колоночной grid-сетке
- [ ] Dashboard: кнопка "+ Новый заказ" в едином стиле
- [ ] FeedbackSettings: поля ввода в enterprise-стиле, кнопка сохранить выглядит как основная кнопка
- [ ] ClientsList: алфавитный разделитель в uppercase hint-стиле
- [ ] Все изменения работают в тёмном и светлом режиме
