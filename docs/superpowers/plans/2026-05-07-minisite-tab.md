# Minisite Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the master Mini App requests tab with a first-class minisite tab backed by account-level "started creation" state.

**Architecture:** Keep the existing promo page constructor as the editing engine. Add a small server-side `promo_page_started_at` flag on `masters`, expose it through `/api/master/me`, and add an idempotent `/api/promo/page/start` endpoint. On the frontend, route the new `minisite` bottom tab to a wrapper that shows intro before creation starts and delegates all editing/management to `PromoPageBuilder`.

**Tech Stack:** Python/FastAPI/aiosqlite/unittest backend; React/Vite/TanStack Query Mini App; existing CSS in `miniapp/src/theme.css`.

---

## File Structure

- Create `migrations/019_promo_page_started.sql`: adds nullable `promo_page_started_at` to `masters`.
- Modify `src/models.py`: add `promo_page_started_at` to `Master`.
- Modify `src/database.py`: whitelist/parse the new master field and add `mark_promo_page_started()`.
- Modify `src/api/routers/master/dashboard.py`: expose `promo_page_started_at` in `/api/master/me`.
- Modify `src/api/routers/promo_pages.py`: add idempotent `POST /api/promo/page/start`.
- Modify `tests/test_promo_page_database.py`: verify migration/model DB helper behavior.
- Modify `tests/test_promo_page_task2_api.py`: verify start endpoint behavior.
- Modify `miniapp/src/api/client.js`: add `startPromoPage()`.
- Modify `miniapp/src/master/components/MasterNav.jsx`: replace requests tab with minisite tab and planet icon.
- Modify `miniapp/src/master/MasterApp.jsx`: remove visible requests routing/badge fetch and render minisite tab.
- Create `miniapp/src/master/pages/Minisite.jsx`: first-run intro wrapper around `PromoPageBuilder`.
- Modify `miniapp/src/master/pages/Dashboard.jsx`: remove requests CTA.
- Modify `miniapp/src/master/pages/More.jsx`: remove promo page cell from Marketing.
- Modify `miniapp/src/i18n/dictionaries/ru.js` and `miniapp/src/i18n/dictionaries/en.js`: add minisite labels/copy and remove visible promo page menu label usage where obsolete.
- Modify `miniapp/src/theme.css`: style the minisite intro using existing enterprise visual language.

---

### Task 1: Backend Started State

**Files:**
- Create: `migrations/019_promo_page_started.sql`
- Modify: `src/models.py`
- Modify: `src/database.py`
- Test: `tests/test_promo_page_database.py`

- [ ] **Step 1: Add failing database test**

Append this test to `PromoPageDatabaseTest` in `tests/test_promo_page_database.py`:

```python
    async def test_mark_promo_page_started_is_idempotent(self):
        await self._seed_masters()

        first = await db.mark_promo_page_started(1)
        self.assertIsNotNone(first)

        second = await db.mark_promo_page_started(1)
        self.assertEqual(second, first)

        masters = await db.get_masters()
        master = next(item for item in masters if item.id == 1)
        self.assertEqual(master.promo_page_started_at, first)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest tests.test_promo_page_database.PromoPageDatabaseTest.test_mark_promo_page_started_is_idempotent
```

Expected: FAIL with `AttributeError: module 'src.database' has no attribute 'mark_promo_page_started'`.

- [ ] **Step 3: Add migration**

Create `migrations/019_promo_page_started.sql`:

```sql
ALTER TABLE masters ADD COLUMN promo_page_started_at TIMESTAMP;
```

- [ ] **Step 4: Update master model and parser**

In `src/models.py`, add the field near `landing_theme`:

```python
    promo_page_started_at: Optional[datetime] = None
```

In `src/database.py`, add `"promo_page_started_at"` to `ALLOWED_MASTER_FIELDS`.

In `_parse_master_row`, add:

```python
        promo_page_started_at=_parse_db_datetime(row["promo_page_started_at"]) if "promo_page_started_at" in row.keys() else None,
```

- [ ] **Step 5: Add database helper**

Add this helper near promo page database helpers in `src/database.py`:

```python
async def mark_promo_page_started(master_id: int) -> Optional[datetime]:
    """Mark that a master started minisite creation and return the timestamp."""
    conn = await get_connection()
    try:
        await conn.execute(
            """
            UPDATE masters
            SET promo_page_started_at = COALESCE(promo_page_started_at, CURRENT_TIMESTAMP)
            WHERE id = ?
            """,
            (master_id,),
        )
        await conn.commit()
        cursor = await conn.execute(
            "SELECT promo_page_started_at FROM masters WHERE id = ?",
            (master_id,),
        )
        row = await cursor.fetchone()
    finally:
        await conn.close()
    if not row:
        return None
    return _parse_db_datetime(row["promo_page_started_at"])
```

- [ ] **Step 6: Run database test**

Run:

```bash
python -m unittest tests.test_promo_page_database.PromoPageDatabaseTest.test_mark_promo_page_started_is_idempotent
```

Expected: PASS.

- [ ] **Step 7: Commit backend DB state**

Run:

```bash
git add migrations/019_promo_page_started.sql src/models.py src/database.py tests/test_promo_page_database.py
git commit -m "feat(promo): track minisite creation start"
```

---

### Task 2: Backend API Endpoint

**Files:**
- Modify: `src/api/routers/master/dashboard.py`
- Modify: `src/api/routers/promo_pages.py`
- Test: `tests/test_promo_page_task2_api.py`

- [ ] **Step 1: Add failing API test**

Append this test to `PromoPageTask2ApiTest` in `tests/test_promo_page_task2_api.py`:

```python
    async def test_start_promo_page_is_account_level_and_does_not_create_page(self):
        first = await self.promo_pages.start_promo_page_api(master=self.master)
        self.assertIn("promo_page_started_at", first)
        self.assertIsNotNone(first["promo_page_started_at"])

        self.assertIsNone(await db.get_promo_page_by_master(self.master.id))

        second = await self.promo_pages.start_promo_page_api(master=self.master)
        self.assertEqual(second, first)

        from src.api.routers.master import dashboard

        reloaded_dashboard = importlib.reload(dashboard)
        me = await reloaded_dashboard.get_master_me(master=await db.get_master_by_id(self.master.id))
        self.assertEqual(me["promo_page_started_at"], first["promo_page_started_at"])
```

- [ ] **Step 2: Run API test to verify it fails**

Run:

```bash
python -m unittest tests.test_promo_page_task2_api.PromoPageTask2ApiTest.test_start_promo_page_is_account_level_and_does_not_create_page
```

Expected: FAIL with `AttributeError` for missing `start_promo_page_api`.

- [ ] **Step 3: Expose field in `/api/master/me`**

In `src/api/routers/master/dashboard.py`, add this key to the returned dict:

```python
        "promo_page_started_at": master.promo_page_started_at.isoformat() if master.promo_page_started_at else None,
```

- [ ] **Step 4: Add start endpoint**

In `src/api/routers/promo_pages.py`, import the helper:

```python
    mark_promo_page_started,
```

Add this endpoint near `get_promo_page_api`:

```python
@router.post("/promo/page/start")
async def start_promo_page_api(master: Master = Depends(get_current_master)):
    started_at = await mark_promo_page_started(master.id)
    if not started_at:
        raise HTTPException(status_code=404, detail="Master not found")
    return {"promo_page_started_at": started_at.isoformat()}
```

- [ ] **Step 5: Run API test**

Run:

```bash
python -m unittest tests.test_promo_page_task2_api.PromoPageTask2ApiTest.test_start_promo_page_is_account_level_and_does_not_create_page
```

Expected: PASS.

- [ ] **Step 6: Run promo backend tests**

Run:

```bash
python -m unittest tests.test_promo_page_database tests.test_promo_page_task2_api
```

Expected: PASS.

- [ ] **Step 7: Commit backend API**

Run:

```bash
git add src/api/routers/master/dashboard.py src/api/routers/promo_pages.py tests/test_promo_page_task2_api.py
git commit -m "feat(promo): add minisite start endpoint"
```

---

### Task 3: Frontend API and Navigation

**Files:**
- Modify: `miniapp/src/api/client.js`
- Modify: `miniapp/src/master/components/MasterNav.jsx`
- Modify: `miniapp/src/master/MasterApp.jsx`
- Modify: `miniapp/src/i18n/dictionaries/ru.js`
- Modify: `miniapp/src/i18n/dictionaries/en.js`

- [ ] **Step 1: Add API client helper**

In `miniapp/src/api/client.js`, add near promo page helpers:

```js
export const startPromoPage = () =>
  api.post('/api/promo/page/start').then(r => r.data);
```

- [ ] **Step 2: Add nav labels**

In `miniapp/src/i18n/dictionaries/ru.js`, change `nav.master.requests` to:

```js
      minisite: 'Минисайт',
```

In `miniapp/src/i18n/dictionaries/en.js`, change the same nav key to:

```js
      minisite: 'Minisite',
```

Keep `masterApp.titles.requests` for hidden legacy code. Add:

```js
      minisite: 'Минисайт',
```

and in English:

```js
      minisite: 'Minisite',
```

- [ ] **Step 3: Replace nav tab and icon**

In `miniapp/src/master/components/MasterNav.jsx`, replace `BellIcon` with:

```jsx
const PlanetIcon = () => (
  <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5" />
    <path d="M3 12c2.5-4 6.5-6 12-6" />
    <path d="M21 12c-2.5 4-6.5 6-12 6" />
    <path d="M4 15c5 3 11 3 16-1" />
  </svg>
);
```

Update `tabs`:

```js
const tabs = [
  { id: 'home', key: 'nav.master.home', Icon: HomeIcon },
  { id: 'calendar', key: 'nav.master.calendar', Icon: CalendarIcon },
  { id: 'minisite', key: 'nav.master.minisite', Icon: PlanetIcon },
  { id: 'more', key: 'nav.master.more', Icon: MoreIcon },
];
```

Simplify component signature and remove badge rendering:

```jsx
export default function MasterNav({ active, onNavigate = () => {} }) {
```

Remove `requestsBadge` usage and `master-nav-badge` rendering block.

- [ ] **Step 4: Update `MasterApp` routing**

In `miniapp/src/master/MasterApp.jsx`:

Remove:

```js
import { getMasterRequestsUnreadCount } from '../api/client';
import Requests from './pages/Requests';
```

Add:

```js
import Minisite from './pages/Minisite';
```

Remove `requestsBadge` state and the `useEffect` that calls `getMasterRequestsUnreadCount`.

Add title:

```js
    minisite:      t('masterApp.titles.minisite'),
```

Remove the nested `if (type === 'requests')` block because no visible master UI should navigate to requests after this change.

In `renderTab`, replace the requests case with:

```jsx
      case 'minisite':
        return <Minisite />;
```

At the bottom, render nav without badge:

```jsx
      <MasterNav active={tab} onNavigate={switchTab} />
```

- [ ] **Step 5: Run frontend lint**

From `miniapp/`, run:

```bash
npm run lint
```

Expected: PASS.

- [ ] **Step 6: Commit navigation/API shell**

Run:

```bash
git add miniapp/src/api/client.js miniapp/src/master/components/MasterNav.jsx miniapp/src/master/MasterApp.jsx miniapp/src/i18n/dictionaries/ru.js miniapp/src/i18n/dictionaries/en.js
git commit -m "feat(miniapp): add minisite navigation tab"
```

---

### Task 4: Minisite Intro Wrapper

**Files:**
- Create: `miniapp/src/master/pages/Minisite.jsx`
- Modify: `miniapp/src/i18n/dictionaries/ru.js`
- Modify: `miniapp/src/i18n/dictionaries/en.js`
- Modify: `miniapp/src/theme.css`

- [ ] **Step 1: Add i18n copy**

In `ru.js`, add a top-level `minisite` section:

```js
  minisite: {
    intro: {
      title: 'Минисайт для клиентов',
      subtitle: 'Соберите публичную страницу с услугами, фото, преимуществами и ссылкой в Telegram.',
      pointServices: 'Покажите услуги и цены',
      pointTrust: 'Добавьте фото и преимущества',
      pointShare: 'Делитесь ссылкой или QR-кодом',
      create: 'Создать минисайт',
      error: 'Не удалось начать создание. Попробуйте ещё раз.',
    },
  },
```

In `en.js`, add:

```js
  minisite: {
    intro: {
      title: 'Client minisite',
      subtitle: 'Build a public page with services, photo, advantages, and a Telegram contact link.',
      pointServices: 'Show services and prices',
      pointTrust: 'Add a photo and advantages',
      pointShare: 'Share a link or QR code',
      create: 'Create minisite',
      error: 'Failed to start creation. Please try again.',
    },
  },
```

- [ ] **Step 2: Create wrapper component**

Create `miniapp/src/master/pages/Minisite.jsx`:

```jsx
import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getMasterMe, getPromoPage, startPromoPage } from '../../api/client';
import { useI18n } from '../../i18n';
import PromoPageBuilder from './PromoPageBuilder';

const WebApp = window.Telegram?.WebApp;

function IntroPoint({ children }) {
  return (
    <li className="minisite-intro-point">
      <span>✓</span>
      <b>{children}</b>
    </li>
  );
}

export default function Minisite() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [error, setError] = useState('');

  const masterQuery = useQuery({
    queryKey: ['master-me'],
    queryFn: getMasterMe,
    staleTime: 30_000,
  });

  const pageQuery = useQuery({
    queryKey: ['promo-page'],
    queryFn: () => getPromoPage().catch((err) => {
      if (err?.response?.status === 404) return null;
      throw err;
    }),
    staleTime: 20_000,
  });

  const shouldShowIntro = useMemo(() => {
    if (pageQuery.data) return false;
    return !masterQuery.data?.promo_page_started_at;
  }, [masterQuery.data?.promo_page_started_at, pageQuery.data]);

  const startMutation = useMutation({
    mutationFn: startPromoPage,
    onSuccess: (data) => {
      WebApp?.HapticFeedback?.notificationOccurred?.('success');
      qc.setQueryData(['master-me'], (old) => ({
        ...(old || {}),
        promo_page_started_at: data?.promo_page_started_at || new Date().toISOString(),
      }));
      setError('');
    },
    onError: () => {
      WebApp?.HapticFeedback?.notificationOccurred?.('error');
      setError(t('minisite.intro.error'));
    },
  });

  if (pageQuery.isLoading || (masterQuery.isLoading && !pageQuery.data)) {
    return <div className="promo-builder-state">{t('common.loading')}</div>;
  }

  if (pageQuery.isError) {
    return (
      <div className="promo-builder-state">
        <p>{t('minisite.intro.error')}</p>
        <button type="button" onClick={() => pageQuery.refetch()}>{t('common.retry')}</button>
      </div>
    );
  }

  if (!shouldShowIntro) {
    return <PromoPageBuilder />;
  }

  return (
    <div className="minisite-intro-page">
      <section className="minisite-intro-hero">
        <span className="minisite-intro-orbit" aria-hidden="true">◎</span>
        <h2>{t('minisite.intro.title')}</h2>
        <p>{t('minisite.intro.subtitle')}</p>
      </section>

      <ul className="minisite-intro-list">
        <IntroPoint>{t('minisite.intro.pointServices')}</IntroPoint>
        <IntroPoint>{t('minisite.intro.pointTrust')}</IntroPoint>
        <IntroPoint>{t('minisite.intro.pointShare')}</IntroPoint>
      </ul>

      {error && <div className="promo-builder-error is-global">{error}</div>}

      <button
        type="button"
        className="promo-builder-btn minisite-intro-cta"
        onClick={() => startMutation.mutate()}
        disabled={startMutation.isPending}
      >
        {startMutation.isPending ? t('common.saving') : t('minisite.intro.create')}
      </button>
    </div>
  );
}
```

- [ ] **Step 3: Add intro styles**

Append near promo builder styles in `miniapp/src/theme.css`:

```css
body.typeui-enterprise-body .minisite-intro-page {
  padding: 18px 16px calc(92px + var(--safe-bottom));
  display: grid;
  gap: 14px;
}

body.typeui-enterprise-body .minisite-intro-hero {
  border: 1px solid var(--tg-enterprise-border);
  border-radius: 8px;
  background: var(--tg-card-bg);
  padding: 18px;
}

body.typeui-enterprise-body .minisite-intro-orbit {
  display: inline-flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #2f74d2;
  background: rgba(47, 116, 210, 0.1);
  font-size: 24px;
  line-height: 1;
  margin-bottom: 14px;
}

body.typeui-enterprise-body .minisite-intro-hero h2 {
  margin: 0 0 8px;
  font-size: 22px;
  line-height: 1.15;
  color: var(--tg-text);
  letter-spacing: 0;
}

body.typeui-enterprise-body .minisite-intro-hero p {
  margin: 0;
  color: var(--tg-hint);
  font-size: 14px;
  line-height: 1.45;
}

body.typeui-enterprise-body .minisite-intro-list {
  list-style: none;
  display: grid;
  gap: 8px;
  padding: 0;
  margin: 0;
}

body.typeui-enterprise-body .minisite-intro-point {
  display: grid;
  grid-template-columns: 28px 1fr;
  align-items: center;
  gap: 10px;
  min-height: 48px;
  border: 1px solid var(--tg-enterprise-border);
  border-radius: 8px;
  background: var(--tg-card-bg);
  padding: 10px 12px;
  color: var(--tg-text);
}

body.typeui-enterprise-body .minisite-intro-point span {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(47, 116, 210, 0.1);
  color: #2f74d2;
  font-weight: 700;
}

body.typeui-enterprise-body .minisite-intro-point b {
  font-size: 14px;
  line-height: 1.25;
  font-weight: 600;
}

body.typeui-enterprise-body .minisite-intro-cta {
  width: 100%;
}
```

- [ ] **Step 4: Run frontend lint/build**

Run:

From `miniapp/`, run:

```bash
npm run lint
npm run build
```

Expected: both PASS.

- [ ] **Step 5: Commit intro wrapper**

Run:

```bash
git add miniapp/src/master/pages/Minisite.jsx miniapp/src/i18n/dictionaries/ru.js miniapp/src/i18n/dictionaries/en.js miniapp/src/theme.css
git commit -m "feat(miniapp): add minisite intro"
```

---

### Task 5: Remove Old Visible Entry Points

**Files:**
- Modify: `miniapp/src/master/pages/Dashboard.jsx`
- Modify: `miniapp/src/master/pages/More.jsx`
- Modify: `miniapp/src/master/MasterApp.jsx`
- Modify: `miniapp/src/i18n/dictionaries/ru.js`
- Modify: `miniapp/src/i18n/dictionaries/en.js`

- [ ] **Step 1: Remove dashboard requests CTA**

In `miniapp/src/master/pages/Dashboard.jsx`, remove `handleRequests`:

```js
  const handleRequests = () => {
    if (typeof WebApp?.HapticFeedback?.impactOccurred === 'function') {
      WebApp.HapticFeedback.impactOccurred('light');
    }
    onNavigate('requests');
  };
```

Remove this JSX block:

```jsx
        {(stats.pending_requests || 0) > 0 && (
          <button
            onClick={handleRequests}
            className="enterprise-btn-outline"
          >
            {tr(`Новые заявки (${stats.pending_requests})`, `New requests (${stats.pending_requests})`)}
          </button>
        )}
```

If `stats` is only used for other dashboard cards, keep it.

- [ ] **Step 2: Remove promo page from More Marketing**

In `miniapp/src/master/pages/More.jsx`, remove the `Cell` that uses:

```jsx
          label={t('more.cells.promoPage')}
          onClick={isSubscriptionActive ? () => onNavigate('promo_page') : handleLockedTap}
```

Keep `LinkIcon` because it is still used by the invite-client cell. Keep the `broadcast` and `promos` cells.

- [ ] **Step 3: Remove direct promo_page nested route**

In `miniapp/src/master/MasterApp.jsx`, remove:

```js
import PromoPageBuilder from './pages/PromoPageBuilder';
```

Remove title map entry:

```js
    promo_page:    t('masterApp.titles.promoPage'),
```

Remove nested route block:

```jsx
    if (type === 'promo_page') {
      return (
        <div className="master-shell">
          <AppHeader title={currentTitle} />
          <PromoPageBuilder />
        </div>
      );
    }
```

Keep `PromoPageBuilder` imported inside `Minisite.jsx`.

- [ ] **Step 4: Clean obsolete visible i18n keys if unused**

Run:

```bash
rg -n "promoPage|promo_page|nav\\.master\\.requests|masterApp\\.titles\\.requests" miniapp/src
```

Expected: no `promoPage` usage in `More.jsx`; no `promo_page` route block in `MasterApp.jsx`; no `nav.master.requests` usage.

- [ ] **Step 5: Run frontend validation**

Run:

From `miniapp/`, run:

```bash
npm run lint
npm run build
```

Expected: both PASS.

- [ ] **Step 6: Commit old entry-point removal**

Run:

```bash
git add miniapp/src/master/pages/Dashboard.jsx miniapp/src/master/pages/More.jsx miniapp/src/master/MasterApp.jsx miniapp/src/i18n/dictionaries/ru.js miniapp/src/i18n/dictionaries/en.js
git commit -m "refactor(miniapp): detach requests and old promo entry"
```

---

### Task 6: Final Verification

**Files:**
- No planned source changes unless verification finds defects.

- [ ] **Step 1: Run backend promo tests**

Run:

```bash
python -m unittest tests.test_promo_page_database tests.test_promo_page_task2_api
```

Expected: PASS.

- [ ] **Step 2: Run wider backend tests**

Run:

```bash
python -m unittest discover tests
```

Expected: PASS. If local dependency gaps block this, record the exact missing dependency and continue with targeted passing tests.

- [ ] **Step 3: Run Mini App checks**

Run:

From `miniapp/`, run:

```bash
npm run lint
npm run build
```

Expected: PASS.

- [ ] **Step 4: Inspect visible strings**

Run:

```bash
rg -n "Заявки|Новые заявки|Requests|New requests|Промо-страница|Promo page" miniapp/src/master miniapp/src/i18n/dictionaries
```

Expected: no visible bottom nav, dashboard, or More Marketing entry for requests or promo page. Hidden `Requests.jsx` and legacy title strings may remain.

- [ ] **Step 5: Review git status**

Run:

```bash
git status --short
```

Expected: clean after commits, or only deliberate uncommitted verification notes if the user requested no commits.
