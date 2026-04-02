# Dashboard Empty States, Navigation, Broadcast Empty State — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Добавить empty states для новых мастеров на Dashboard, обновить иконку навигации и добавить empty state для рассылок.

**Architecture:** Расширяем `/api/master/dashboard` двумя новыми полями; добавляем новый эндпоинт `/api/master/broadcast/can-send`; обновляем `PUT /api/master/profile` для записи `onboarding_banner_shown`; обновляем три фронтенд-компонента.

**Tech Stack:** Python/FastAPI (backend), React/React Query (frontend), aiosqlite (DB), inline SVG icons

---

## Task 1: DB — добавить функцию count_done_orders

**Files:**
- Modify: `src/database.py` (после `count_pending_requests`, ~строка 2165)

**Step 1: Добавить функцию в database.py**

Вставить после `count_pending_requests`:

```python
async def count_done_orders(master_id: int) -> int:
    """Count total completed orders for a master."""
    async with get_connection() as db:
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE master_id = ? AND status = 'done'",
            (master_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
```

**Step 2: Запустить приложение и убедиться что нет синтаксических ошибок**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python -c "from src.database import count_done_orders; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add src/database.py
git commit -m "feat(db): add count_done_orders function"
```

---

## Task 2: Backend — расширить /api/master/dashboard

**Files:**
- Modify: `src/api/routers/master/dashboard.py`

**Step 1: Добавить импорт `count_done_orders`**

В строке 12 (в блоке `from src.database import`), добавить `count_done_orders` в список импортов:

```python
from src.database import (
    get_clients_paginated,
    get_orders_by_date,
    get_reports,
    count_pending_requests,
    count_done_orders,
)
```

**Step 2: Вызвать функцию в `get_master_dashboard` и расширить ответ**

В теле `get_master_dashboard` (после строки `pending_requests = await count_pending_requests(master.id)`):

```python
    total_done = await count_done_orders(master.id)
```

Расширить return (добавить два новых поля в конец):

```python
    return {
        "master_name": master.name,
        "today_orders": [_format_order(o) for o in today_orders_raw],
        "tomorrow_orders": [_format_order(o) for o in tomorrow_orders_raw],
        "stats": {
            "week_revenue": week_report.get("revenue", 0),
            "month_revenue": month_report.get("revenue", 0),
            "week_orders": week_report.get("order_count", 0),
            "month_orders": month_report.get("order_count", 0),
            "total_clients": week_report.get("total_clients", 0),
            "pending_requests": pending_requests,
        },
        "total_done_orders": total_done,
        "onboarding_banner": {
            "show": master.onboarding_skipped_first_client and not master.onboarding_banner_shown,
            "skipped_first_client": master.onboarding_skipped_first_client,
            "banner_shown": master.onboarding_banner_shown,
        },
    }
```

**Step 3: Проверить импорты запускаются без ошибок**

```bash
python -c "from src.api.routers.master.dashboard import router; print('OK')"
```

Expected: `OK`

**Step 4: Commit**

```bash
git add src/api/routers/master/dashboard.py
git commit -m "feat(api): add total_done_orders and onboarding_banner to dashboard"
```

---

## Task 3: Backend — добавить PUT /api/master/profile поддержку onboarding_banner_shown

**Files:**
- Modify: `src/api/routers/master/settings.py:42-68`

**Step 1: Расширить `ProfileUpdateBody`**

Добавить поле `onboarding_banner_shown` в класс `ProfileUpdateBody` (после строки `work_hours`):

```python
class ProfileUpdateBody(BaseModel):
    name: Optional[str] = None
    sphere: Optional[str] = None
    contacts: Optional[str] = None
    socials: Optional[str] = None
    work_hours: Optional[str] = None
    onboarding_banner_shown: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError("name cannot be empty")
        if v is not None and len(v) > 100:
            raise ValueError("name max 100 chars")
        return v
```

Примечание: `update_master` принимает `**kwargs`, а фильтр `if v is not None` корректно работает с bool (False — это не None).

**Step 2: Проверить**

```bash
python -c "from src.api.routers.master.settings import router; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add src/api/routers/master/settings.py
git commit -m "feat(api): allow updating onboarding_banner_shown via PUT /master/profile"
```

---

## Task 4: Backend — добавить GET /api/master/broadcast/can-send

**Files:**
- Modify: `src/api/routers/master/broadcast.py`

**Step 1: Добавить импорты**

В строке 13 (в блоке `from src.database import`), добавить `get_broadcast_recipients_count`:

```python
from src.database import get_clients_by_segment, save_campaign, get_broadcast_recipients_count
```

Добавить импорт `CLIENT_BOT_USERNAME`:

```python
from src.config import CLIENT_BOT_USERNAME
```

**Step 2: Добавить эндпоинт (вставить перед `get_broadcast_segments`)**

```python
@router.get("/master/broadcast/can-send")
async def get_broadcast_can_send(
    master: Master = Depends(get_current_master),
):
    """Check if master can send broadcasts (has clients with Telegram)."""
    count = await get_broadcast_recipients_count(master.id, "all")
    bot_username = CLIENT_BOT_USERNAME or "client_bot"
    invite_link = f"https://t.me/{bot_username}?start=invite_{master.invite_token}"
    return {
        "can_send": count > 0,
        "clients_with_telegram": count,
        "invite_link": invite_link,
    }
```

**Step 3: Проверить**

```bash
python -c "from src.api.routers.master.broadcast import router; print('OK')"
```

Expected: `OK`

**Step 4: Commit**

```bash
git add src/api/routers/master/broadcast.py
git commit -m "feat(api): add GET /master/broadcast/can-send endpoint"
```

---

## Task 5: Frontend API client — добавить новые функции

**Files:**
- Modify: `miniapp/src/api/client.js`

**Step 1: Добавить `getBroadcastCanSend` после `sendBroadcast` (~строка 82)**

```js
export const getBroadcastCanSend = () =>
  api.get('/api/master/broadcast/can-send').then(r => r.data);
```

**Step 2: Commit**

```bash
git add miniapp/src/api/client.js
git commit -m "feat(api-client): add getBroadcastCanSend function"
```

---

## Task 6: Frontend — обновить Dashboard (empty states + баннер)

**Files:**
- Modify: `miniapp/src/master/pages/Dashboard.jsx`

**Step 1: Обновить `OrdersSection` — добавить проп `emptyContent`**

Изменить сигнатуру функции и рендер пустого состояния:

```jsx
function OrdersSection({ title, orders, onNavigate, emptyContent }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 8,
      }}>
        <h3 style={{
          color: 'var(--tg-text)',
          fontSize: 16,
          fontWeight: 600,
          margin: 0,
        }}>
          {title}
        </h3>
        <span style={{
          color: 'var(--tg-hint)',
          fontSize: 13,
        }}>
          {orders.length > 0 ? `${orders.length} зап.` : ''}
        </span>
      </div>

      {orders.length === 0 ? (
        <div style={{
          background: 'var(--tg-surface)',
          borderRadius: 'var(--radius-card)',
          padding: '14px 16px',
          color: 'var(--tg-hint)',
          fontSize: 14,
          textAlign: 'center',
        }}>
          {emptyContent ?? 'Свободный день! 🎉'}
        </div>
      ) : (
        <div style={{
          background: 'var(--tg-surface)',
          borderRadius: 'var(--radius-card)',
          padding: '0 16px',
        }}>
          {orders.map((order, idx) => (
            <OrderCard
              key={order.id}
              order={order}
              onClick={() => onNavigate('order', order.id)}
              style={idx === orders.length - 1 ? { borderBottom: 'none' } : {}}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Добавить import `useState` в начало файла**

```jsx
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMasterDashboard, updateMasterProfile } from '../../api/client';
```

**Step 3: В компоненте `Dashboard` — добавить состояние баннера и логику**

В теле `Dashboard` после строки `const stats = data?.stats || {};`:

```jsx
  const queryClient = useQueryClient();
  const [bannerDismissed, setBannerDismissed] = useState(false);

  const dismissBannerMutation = useMutation({
    mutationFn: () => updateMasterProfile({ onboarding_banner_shown: true }),
    onSuccess: () => {
      setBannerDismissed(true);
      queryClient.invalidateQueries({ queryKey: ['master-dashboard'] });
    },
  });

  const totalDoneOrders = data?.total_done_orders ?? 0;
  const todayOrders = data?.today_orders || [];
  const tomorrowOrders = data?.tomorrow_orders || [];
  const showBanner = !bannerDismissed && (data?.onboarding_banner?.show === true);

  const handleBannerDismiss = () => {
    dismissBannerMutation.mutate();
  };

  const handleBannerAdd = () => {
    handleNewOrder();
    dismissBannerMutation.mutate();
  };
```

**Step 4: Добавить мотивационный блок (заменить KPI-секцию)**

Заменить весь блок `{/* Block 2: Stats 2x2 grid */}` (строки 207-237):

```jsx
      {/* Block 2: KPI or motivational block */}
      {totalDoneOrders > 0 ? (
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 8,
          marginBottom: 24,
        }}>
          <StatCard
            icon="💰"
            value={formatCurrency(stats.week_revenue || 0)}
            label="Выручка за неделю"
            onClick={handleReportsWeek}
          />
          <StatCard
            icon="📅"
            value={formatCurrency(stats.month_revenue || 0)}
            label="Выручка за месяц"
            onClick={handleReportsMonth}
          />
          <StatCard
            icon="✅"
            value={stats.week_orders || 0}
            label="Заказов за неделю"
          />
          <StatCard
            icon="👥"
            value={stats.total_clients || 0}
            label="Всего клиентов"
            onClick={handleClients}
          />
        </div>
      ) : (
        <div style={{
          background: 'var(--tg-secondary-bg-color, var(--tg-surface))',
          borderRadius: 'var(--radius-card)',
          padding: '16px',
          marginBottom: 24,
          display: 'flex',
          alignItems: 'flex-start',
          gap: 12,
        }}>
          <span style={{ fontSize: 24, lineHeight: 1 }}>📊</span>
          <p style={{
            color: 'var(--tg-hint)',
            fontSize: 14,
            margin: 0,
            lineHeight: 1.4,
          }}>
            Выполни первый заказ и увидишь показатели своей работы в цифрах
          </p>
        </div>
      )}
```

**Step 5: Обновить рендер секций "Сегодня" и "Завтра"**

Заменить блоки `{/* Block 3 */}` и `{/* Block 4 */}` (строки 239-251):

```jsx
      {/* Block 3: Today's orders */}
      <OrdersSection
        title="Сегодня"
        orders={todayOrders}
        onNavigate={onNavigate}
        emptyContent={
          totalDoneOrders === 0 && todayOrders.length === 0 && tomorrowOrders.length === 0
            ? (
              <div>
                <p style={{ margin: '0 0 10px', color: 'var(--tg-hint)' }}>
                  Пока записей нет
                </p>
                <button
                  onClick={handleNewOrder}
                  style={{
                    background: 'var(--tg-button)',
                    color: 'var(--tg-button-text)',
                    border: 'none',
                    borderRadius: 8,
                    padding: '8px 16px',
                    fontSize: 14,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  + Добавить первую запись
                </button>
              </div>
            )
            : todayOrders.length === 0
              ? 'Записей на сегодня нет'
              : null
        }
      />

      {/* Block 4: Tomorrow's orders */}
      <OrdersSection
        title="Завтра"
        orders={tomorrowOrders}
        onNavigate={onNavigate}
        emptyContent="Записей на завтра нет"
      />
```

**Step 6: Добавить онбординг-баннер над приветствием**

Вставить в начало `return` (первым элементом, перед `{/* Block 1: Greeting */}`):

```jsx
      {/* Onboarding banner */}
      {showBanner && (
        <div style={{
          background: 'var(--tg-secondary-bg-color, var(--tg-surface))',
          borderRadius: 'var(--radius-card)',
          padding: '12px 14px',
          marginBottom: 16,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}>
          <p style={{
            flex: 1,
            color: 'var(--tg-text)',
            fontSize: 13,
            margin: 0,
            lineHeight: 1.4,
          }}>
            Добавь первого клиента, чтобы увидеть как работают напоминания
          </p>
          <button
            onClick={handleBannerAdd}
            style={{
              background: 'var(--tg-button)',
              color: 'var(--tg-button-text)',
              border: 'none',
              borderRadius: 8,
              padding: '7px 12px',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            Добавить →
          </button>
          <button
            onClick={handleBannerDismiss}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--tg-hint)',
              fontSize: 18,
              cursor: 'pointer',
              padding: '0 2px',
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>
      )}
```

**Step 7: Build check**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot/miniapp
npm run build 2>&1 | tail -20
```

Expected: нет ошибок (только warnings допустимы)

**Step 8: Commit**

```bash
git add miniapp/src/master/pages/Dashboard.jsx
git commit -m "feat(dashboard): add empty states for new masters and onboarding banner"
```

---

## Task 7: Frontend — обновить иконку в MasterNav

**Files:**
- Modify: `miniapp/src/master/components/MasterNav.jsx:19-23`

**Step 1: Заменить `MegaphoneIcon` на `MailIcon`**

Заменить компонент `MegaphoneIcon` (строки 19-23):

```jsx
const MailIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="4" width="20" height="16" rx="2"/>
    <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
  </svg>
);
```

В массиве `tabs` заменить `Icon: MegaphoneIcon` на `Icon: MailIcon`:

```jsx
  { id: 'marketing', label: 'Рассылки', Icon: MailIcon },
```

**Step 2: Build check**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot/miniapp
npm run build 2>&1 | tail -10
```

**Step 3: Commit**

```bash
git add miniapp/src/master/components/MasterNav.jsx
git commit -m "feat(nav): replace megaphone icon with mail icon for broadcasts tab"
```

---

## Task 8: Frontend — Broadcast empty state

**Files:**
- Modify: `miniapp/src/master/pages/Broadcast.jsx`

**Step 1: Добавить импорты в начало файла**

В блок импортов добавить `getBroadcastCanSend`:

```jsx
import { getBroadcastCanSend, getBroadcastSegments, previewBroadcast, sendBroadcast } from '../../api/client';
```

**Step 2: Добавить `useQuery` для can-send в начало компонента `Broadcast`**

В компоненте `Broadcast` (или как называется главный экспортируемый компонент) добавить запрос в самом начале хуков:

```jsx
  const {
    data: canSendData,
    isLoading: canSendLoading,
  } = useQuery({
    queryKey: ['broadcast-can-send'],
    queryFn: getBroadcastCanSend,
    staleTime: 60_000,
  });
```

**Step 3: Добавить условный рендер перед основным wizard**

В начале `return` (до основного контента), добавить проверку:

```jsx
  // Loading state for can-send check
  if (canSendLoading) {
    return (
      <div style={{ padding: '16px 16px 100px' }}>
        <Skeleton height={200} style={{ marginBottom: 16 }} />
      </div>
    );
  }

  // Empty state — no clients with Telegram
  if (canSendData?.can_send === false) {
    return (
      <div style={{
        padding: '48px 24px 100px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 56, marginBottom: 16 }}>✉️</div>
        <h2 style={{
          color: 'var(--tg-text)',
          fontSize: 20,
          fontWeight: 700,
          margin: '0 0 8px',
        }}>
          Массовые рассылки
        </h2>
        <p style={{
          color: 'var(--tg-hint)',
          fontSize: 14,
          margin: '0 0 24px',
          lineHeight: 1.5,
        }}>
          Добавьте клиентов, чтобы делать массовые рассылки
        </p>

        <div style={{
          width: '100%',
          height: 1,
          background: 'var(--tg-hint)',
          opacity: 0.2,
          marginBottom: 24,
        }} />

        <div style={{
          width: '100%',
          background: 'var(--tg-surface)',
          borderRadius: 'var(--radius-card)',
          padding: '16px',
          textAlign: 'left',
        }}>
          <p style={{
            color: 'var(--tg-text)',
            fontSize: 14,
            fontWeight: 600,
            margin: '0 0 4px',
          }}>
            Ссылка-приглашение для клиентов
          </p>
          <p style={{
            color: 'var(--tg-hint)',
            fontSize: 13,
            margin: '0 0 12px',
          }}>
            Отправьте ссылку, чтобы пригласить клиента
          </p>
          <div style={{
            background: 'var(--tg-bg)',
            borderRadius: 8,
            padding: '10px 12px',
            marginBottom: 10,
            wordBreak: 'break-all',
            fontSize: 13,
            color: 'var(--tg-hint)',
          }}>
            {canSendData?.invite_link || ''}
          </div>
          <button
            onClick={() => {
              navigator.clipboard.writeText(canSendData?.invite_link || '');
              const WebApp = window.Telegram?.WebApp;
              if (typeof WebApp?.HapticFeedback?.notificationOccurred === 'function') {
                WebApp.HapticFeedback.notificationOccurred('success');
              }
            }}
            style={{
              width: '100%',
              background: 'var(--tg-button)',
              color: 'var(--tg-button-text)',
              border: 'none',
              borderRadius: 10,
              padding: '12px',
              fontSize: 15,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Копировать ссылку
          </button>
        </div>
      </div>
    );
  }
```

**Step 4: Убедиться что `Skeleton` импортирован**

В импортах файла должно быть:
```jsx
import { Skeleton } from '../../components/Skeleton';
```

Если нет — добавить.

**Step 5: Build check**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot/miniapp
npm run build 2>&1 | tail -20
```

Expected: нет ошибок

**Step 6: Commit**

```bash
git add miniapp/src/master/pages/Broadcast.jsx
git commit -m "feat(broadcast): add empty state for masters without Telegram clients"
```

---

## Task 9: Final verification

**Step 1: Полная сборка фронтенда**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot/miniapp
npm run build 2>&1
```

Expected: `✓ built in X.Xs` без ошибок

**Step 2: Проверить Python-модули**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python -c "
from src.database import count_done_orders
from src.api.routers.master.dashboard import router as dash
from src.api.routers.master.broadcast import router as bcast
from src.api.routers.master.settings import router as sett
print('All modules OK')
"
```

Expected: `All modules OK`

**Step 3: Финальный commit (если есть несохранённые изменения)**

```bash
git status
```

---

## Checklist критериев приёмки

- [ ] Новый мастер (0 done-заказов) → KPI скрыты, мотивационный блок 📊 видён
- [ ] "Пока записей нет" + кнопка "Добавить первую запись" → ведёт на OrderCreate
- [ ] Баннер онбординга виден если `onboarding_banner.show == true`
- [ ] Баннер скрывается при нажатии "Добавить →" или "×", сохраняется в БД
- [ ] Мастер с 1+ done-заказом → KPI показываются, баннер скрыт
- [ ] "Записей на сегодня нет" — нейтральный текст (без 🎉)
- [ ] Навигация: вкладка "Рассылки" с иконкой конверта (MailIcon)
- [ ] 0 клиентов с TG → empty state рассылок с инвайт-ссылкой
- [ ] 1+ клиент с TG → обычный wizard рассылок
- [ ] "Копировать ссылку" — работает через Clipboard API
- [ ] `npm run build` без ошибок
