# Master Mini App Profile Media Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Добавить в Master Mini App управление «О себе», аватаром, портфолио и переключателем «На минисайте» для услуг через file upload, без изменений схемы БД и без бот-хендлеров.

**Architecture:** Фото загружаются multipart-upload в FastAPI, хранятся как статика (`/app/data/avatars/`, `/app/data/portfolio/`), монтируются как `/avatars` и `/portfolio`. Поля `avatar_file_id` / `file_id` в БД хранят либо Telegram file_id (без `/`), либо локальный URL (начинается с `/`). `_photo_url` различает оба формата.

**Tech Stack:** Python 3.11 / FastAPI / aiosqlite / React 18 / @tanstack/react-query / aiogram 3

---

## Task 1: Backend — `_photo_url` handles local paths

**Files:**
- Modify: `src/api/routers/landing.py`
- Modify: `src/api/routers/public.py`

**Step 1: Update `_photo_url` in both files**

В `src/api/routers/landing.py` строка 41:
```python
def _photo_url(file_id: str) -> str:
    if not file_id:
        return None
    if file_id.startswith('/'):
        return file_id  # local static file
    return f"/api/public/photo/{file_id}"
```

В `src/api/routers/public.py` строка 19:
```python
def _photo_url(file_id: str | None) -> str | None:
    if not file_id:
        return None
    if file_id.startswith('/'):
        return file_id  # local static file
    return f"/api/public/photo/{file_id}"
```

**Step 2: Syntax check**

```bash
/opt/homebrew/bin/python3.11 -m py_compile src/api/routers/landing.py src/api/routers/public.py
```
Expected: no output (clean).

**Step 3: Commit**

```bash
git add src/api/routers/landing.py src/api/routers/public.py
git commit -m "fix(landing): _photo_url supports local static paths"
```

---

## Task 2: Backend — mount static dirs + upload endpoints

**Files:**
- Modify: `src/api/app.py`
- Modify: `src/api/routers/master/settings.py`

**Step 1: Mount `/avatars` and `/portfolio` in `src/api/app.py`**

После строки с `BONUS_MEDIA_DIR` (≈ строка 54) добавить:
```python
AVATARS_DIR = Path(os.getenv("AVATARS_DIR", "/app/data/avatars"))
AVATARS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/avatars", StaticFiles(directory=str(AVATARS_DIR)), name="avatars")

PORTFOLIO_DIR = Path(os.getenv("PORTFOLIO_DIR", "/app/data/portfolio"))
PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/portfolio", StaticFiles(directory=str(PORTFOLIO_DIR)), name="portfolio")
```

**Step 2: Add upload endpoints to `src/api/routers/master/settings.py`**

В начале файла убедиться в наличии импортов (добавить если нет):
```python
import uuid
from fastapi import UploadFile, File
```

В конец файла добавить три эндпоинта:

```python
# =============================================================================
# Avatar & Portfolio — file upload
# =============================================================================

_AVATARS_DIR = Path(os.getenv("AVATARS_DIR", "/app/data/avatars"))
_PORTFOLIO_DIR = Path(os.getenv("PORTFOLIO_DIR", "/app/data/portfolio"))
_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


def _safe_ext(filename: str) -> str:
    """Return lowercase extension from filename, default .jpg."""
    ext = Path(filename or "").suffix.lower()
    return ext if ext in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


@router.post("/master/avatar/upload")
async def upload_master_avatar(
    file: UploadFile = File(...),
    master: Master = Depends(get_current_master),
):
    """Upload avatar image for master. Replaces existing."""
    data = await file.read()
    if len(data) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB)")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=415, detail="Only image files are accepted")

    ext = _safe_ext(file.filename or "")
    filename = f"master_{master.id}{ext}"
    _AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    (_AVATARS_DIR / filename).write_bytes(data)

    avatar_url = f"/avatars/{filename}"
    await update_master(master.id, avatar_file_id=avatar_url)
    return {"avatar_url": avatar_url}


@router.delete("/master/avatar")
async def delete_master_avatar(master: Master = Depends(get_current_master)):
    """Remove avatar from master profile."""
    old = master.avatar_file_id or ""
    if old.startswith("/avatars/"):
        path = _AVATARS_DIR / Path(old).name
        if path.exists():
            path.unlink(missing_ok=True)
    await update_master(master.id, avatar_file_id=None)
    return {"ok": True}


@router.post("/master/portfolio/upload", status_code=201)
async def upload_portfolio_photo(
    file: UploadFile = File(...),
    master: Master = Depends(get_current_master),
):
    """Upload a portfolio photo (max 10 total)."""
    data = await file.read()
    if len(data) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB)")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=415, detail="Only image files are accepted")

    ext = _safe_ext(file.filename or "")
    filename = f"master_{master.id}_{uuid.uuid4().hex[:8]}{ext}"
    _PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    (_PORTFOLIO_DIR / filename).write_bytes(data)

    photo_url = f"/portfolio/{filename}"
    photo_id = await add_portfolio_photo(master.id, photo_url)
    if photo_id is None:
        (_PORTFOLIO_DIR / filename).unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="Portfolio limit reached (max 10 photos)")

    return {"id": photo_id, "url": photo_url}
```

Убедиться что `Path` и `os` уже импортированы в файле (они есть через `from pathlib import Path` и `import os`). Если нет — добавить.

**Step 3: Syntax check**

```bash
/opt/homebrew/bin/python3.11 -m py_compile src/api/app.py src/api/routers/master/settings.py
```
Expected: no output.

**Step 4: Commit**

```bash
git add src/api/app.py src/api/routers/master/settings.py
git commit -m "feat(api): avatar/portfolio file upload endpoints + static mounts"
```

---

## Task 3: Frontend — API client functions

**Files:**
- Modify: `miniapp/src/api/client.js`

**Step 1: Add five functions at the end of the file**

```js
// ── Landing profile media ──────────────────────────────────────────
export const uploadMasterAvatar = (formData) =>
  api.post('/api/master/avatar/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);

export const deleteMasterAvatar = () =>
  api.delete('/api/master/avatar').then(r => r.data);

export const getMasterPortfolio = () =>
  api.get('/api/master/portfolio').then(r => r.data);

export const uploadPortfolioPhoto = (formData) =>
  api.post('/api/master/portfolio/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);

export const deletePortfolioPhoto = (id) =>
  api.delete(`/api/master/portfolio/${id}`).then(r => r.data);
```

**Step 2: ESLint check**

```bash
cd miniapp && npm exec eslint -- src/api/client.js
```
Expected: no errors.

**Step 3: Commit**

```bash
git add miniapp/src/api/client.js
git commit -m "feat(miniapp): add avatar/portfolio API client functions"
```

---

## Task 4: Frontend — Profile.jsx: «О себе» + секция «Минисайт»

**Files:**
- Modify: `miniapp/src/master/pages/Profile.jsx`

**Step 1: Add imports at top of file**

В блок импортов из `../../api/client` добавить:
```js
import {
  ...existing...,
  uploadMasterAvatar,
  deleteMasterAvatar,
  getMasterPortfolio,
  uploadPortfolioPhoto,
  deletePortfolioPhoto,
} from '../../api/client';
```

В блок React-импортов добавить `useRef`:
```js
import { useState, useRef } from 'react';
```

**Step 2: Add SVG icons**

После существующих иконок (перед `function SectionTitle`) добавить:
```jsx
const TextIcon = () => (
  <svg {...iconProps}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <path d="M14 2v6h6" />
    <path d="M16 13H8" /><path d="M16 17H8" /><path d="M10 9H8" />
  </svg>
);

const ImageIcon = () => (
  <svg {...iconProps}>
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <circle cx="8.5" cy="8.5" r="1.5" />
    <path d="m21 15-5-5L5 21" />
  </svg>
);

const TrashIcon = () => (
  <svg {...iconProps} width={14} height={14} stroke="currentColor">
    <path d="M3 6h18" /><path d="M19 6l-1 14H6L5 6" />
    <path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2" />
  </svg>
);
```

**Step 3: Add portfolio query + mutations inside Profile() component**

Сразу после `const qc = useQueryClient();` добавить:
```jsx
const avatarInputRef = useRef(null);
const portfolioInputRef = useRef(null);

const { data: portfolioItems = [] } = useQuery({
  queryKey: ['master-portfolio'],
  queryFn: getMasterPortfolio,
  staleTime: 30_000,
});

const avatarUploadMutation = useMutation({
  mutationFn: uploadMasterAvatar,
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ['master-me'] });
    showSuccess('Аватар обновлён');
  },
  onError: () => hapticNotify('error'),
});

const avatarDeleteMutation = useMutation({
  mutationFn: deleteMasterAvatar,
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ['master-me'] });
    showSuccess('Аватар удалён');
  },
  onError: () => hapticNotify('error'),
});

const portfolioUploadMutation = useMutation({
  mutationFn: uploadPortfolioPhoto,
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ['master-portfolio'] });
    showSuccess('Фото добавлено');
  },
  onError: (err) => {
    hapticNotify('error');
    const detail = err?.response?.data?.detail || 'Ошибка загрузки';
    if (typeof WebApp?.showAlert === 'function') WebApp.showAlert(detail);
  },
});

const portfolioDeleteMutation = useMutation({
  mutationFn: deletePortfolioPhoto,
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ['master-portfolio'] });
    showSuccess('Фото удалено');
  },
  onError: () => hapticNotify('error'),
});

const handleAvatarFileChange = (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  haptic('medium');
  const fd = new FormData();
  fd.append('file', file);
  avatarUploadMutation.mutate(fd);
  e.target.value = '';
};

const handlePortfolioFileChange = (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  haptic('medium');
  const fd = new FormData();
  fd.append('file', file);
  portfolioUploadMutation.mutate(fd);
  e.target.value = '';
};
```

**Step 4: Add «О себе» Cell in the Profile section JSX**

Найти блок с ячейкой `sphere` (≈ строка 340 в текущем файле) и сразу после него добавить:
```jsx
<Cell
  icon={<TextIcon />}
  label="О себе"
  value={master?.about ? master.about.slice(0, 40) + (master.about.length > 40 ? '…' : '') : null}
  fallbackValue={t('common.notSpecified')}
  onClick={() => setEditor({
    field: 'about',
    title: 'О себе',
    value: master?.about || '',
    placeholder: 'Расскажите о себе и своём опыте…',
    multiline: true,
  })}
/>
```

**Step 5: Add «Минисайт» section before invite section JSX**

Найти `<SectionTitle>{t('profile.sections.invite')}</SectionTitle>` и перед ним вставить:

```jsx
<SectionTitle>Минисайт</SectionTitle>

{/* Avatar */}
<div className="enterprise-cell-group">
  <div className="enterprise-cell" style={{ alignItems: 'center', gap: 12 }}>
    <div style={{
      width: 52, height: 52, borderRadius: '50%', overflow: 'hidden', flexShrink: 0,
      background: 'var(--tg-accent, #6c47ff)', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      color: '#fff', fontWeight: 700, fontSize: 20,
    }}>
      {master?.avatar_file_id
        ? <img src={master.avatar_file_id.startsWith('/') ? master.avatar_file_id : `/api/public/photo/${master.avatar_file_id}`}
            alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        : (master?.name || '?')[0].toUpperCase()
      }
    </div>
    <span className="enterprise-cell-label">Аватар</span>
    <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
      <button
        type="button"
        className="enterprise-sheet-btn secondary"
        style={{ padding: '6px 12px', fontSize: 13 }}
        disabled={avatarUploadMutation.isPending}
        onClick={() => { haptic(); avatarInputRef.current?.click(); }}
      >
        {avatarUploadMutation.isPending ? '…' : 'Загрузить'}
      </button>
      {master?.avatar_file_id && (
        <button
          type="button"
          className="enterprise-sheet-btn destructive"
          style={{ padding: '6px 12px', fontSize: 13 }}
          disabled={avatarDeleteMutation.isPending}
          onClick={() => { haptic(); avatarDeleteMutation.mutate(); }}
        >
          Удалить
        </button>
      )}
    </div>
  </div>
</div>
<input
  ref={avatarInputRef}
  type="file"
  accept="image/*"
  style={{ display: 'none' }}
  onChange={handleAvatarFileChange}
/>

{/* Portfolio */}
<div style={{ marginTop: 16 }}>
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 0 8px' }}>
    <span className="enterprise-section-title" style={{ margin: 0 }}>Портфолио</span>
    <span style={{ fontSize: 13, color: 'var(--tg-hint)' }}>{portfolioItems.length}/10</span>
  </div>
  {portfolioItems.length > 0 && (
    <div style={{
      display: 'flex', gap: 10, overflowX: 'auto', paddingBottom: 4,
      scrollSnapType: 'x mandatory', WebkitOverflowScrolling: 'touch',
    }}>
      {portfolioItems.map(photo => (
        <div key={photo.id} style={{ position: 'relative', flexShrink: 0, scrollSnapAlign: 'start' }}>
          <img
            src={photo.url}
            alt="portfolio"
            style={{ width: 100, height: 100, objectFit: 'cover', borderRadius: 10, display: 'block' }}
          />
          <button
            type="button"
            onClick={() => { haptic(); portfolioDeleteMutation.mutate(photo.id); }}
            disabled={portfolioDeleteMutation.isPending}
            style={{
              position: 'absolute', top: 4, right: 4,
              background: 'rgba(0,0,0,0.55)', border: 'none', borderRadius: '50%',
              width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: '#fff', padding: 0,
            }}
          >
            <TrashIcon />
          </button>
        </div>
      ))}
    </div>
  )}
  {portfolioItems.length < 10 && (
    <button
      type="button"
      className="enterprise-services-add-btn"
      style={{ marginTop: 8, width: '100%' }}
      disabled={portfolioUploadMutation.isPending}
      onClick={() => { haptic(); portfolioInputRef.current?.click(); }}
    >
      <ImageIcon />
      <span>{portfolioUploadMutation.isPending ? 'Загрузка…' : 'Добавить фото'}</span>
    </button>
  )}
  <input
    ref={portfolioInputRef}
    type="file"
    accept="image/*"
    style={{ display: 'none' }}
    onChange={handlePortfolioFileChange}
  />
</div>
```

**Step 6: ESLint**

```bash
cd miniapp && npm exec eslint -- src/master/pages/Profile.jsx
```
Expected: no errors.

**Step 7: Commit**

```bash
git add miniapp/src/master/pages/Profile.jsx
git commit -m "feat(miniapp): profile — about field + avatar/portfolio upload"
```

---

## Task 5: Frontend — Services.jsx: show_on_landing toggle

**Files:**
- Modify: `miniapp/src/master/pages/Services.jsx`

**Step 1: Add `showOnLanding` state inside `ServiceSheet`**

В компонент `ServiceSheet` (≈ строка 70) после существующих `useState` добавить:
```jsx
const [showOnLanding, setShowOnLanding] = useState(
  initial?.show_on_landing !== undefined ? initial.show_on_landing : true
);
```

**Step 2: Include `show_on_landing` in `handleSave` payload**

В функцию `handleSave` внутри `ServiceSheet` изменить `onSave(...)`:
```js
onSave({
  name: name.trim(),
  price: parsedPrice,
  description: description.trim() || null,
  show_on_landing: showOnLanding,
});
```

**Step 3: Add toggle UI in ServiceSheet JSX**

После блока `description` (перед `<div className="enterprise-sheet-actions">`) добавить:
```jsx
<div style={{
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  padding: '12px 0', borderTop: '1px solid var(--tg-secondary-bg, #eee)',
  marginTop: 8,
}}>
  <div>
    <div style={{ fontSize: 15, fontWeight: 500 }}>На минисайте</div>
    <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginTop: 2 }}>
      Услуга отображается на вашем публичном лендинге
    </div>
  </div>
  <button
    type="button"
    role="switch"
    aria-checked={showOnLanding}
    onClick={() => { haptic(); setShowOnLanding(v => !v); }}
    style={{
      width: 44, height: 26, borderRadius: 13, border: 'none', cursor: 'pointer',
      background: showOnLanding ? 'var(--tg-accent, #6c47ff)' : 'var(--tg-hint, #aaa)',
      position: 'relative', transition: 'background 0.2s', flexShrink: 0,
    }}
  >
    <span style={{
      position: 'absolute', top: 3,
      left: showOnLanding ? 21 : 3,
      width: 20, height: 20, borderRadius: '50%',
      background: '#fff', transition: 'left 0.2s',
    }} />
  </button>
</div>
```

**Step 4: ESLint**

```bash
cd miniapp && npm exec eslint -- src/master/pages/Services.jsx
```
Expected: no errors.

**Step 5: Commit**

```bash
git add miniapp/src/master/pages/Services.jsx
git commit -m "feat(miniapp): services — show_on_landing toggle"
```

---

## Task 6: Build, verify, deploy

**Step 1: Full build**

```bash
npm --prefix miniapp run build
```
Expected: build completes, existing Vite chunk-size warning is OK, no new errors.

**Step 2: Python compile check**

```bash
/opt/homebrew/bin/python3.11 -m py_compile \
  src/api/app.py \
  src/api/routers/master/settings.py \
  src/api/routers/landing.py \
  src/api/routers/public.py
```
Expected: no output.

**Step 3: Run existing tests**

```bash
/opt/homebrew/bin/python3.11 -m unittest \
  tests.test_client_bot_notifications.ClientBotNotificationFormattingTest
```
Expected: 4 tests passed.

**Step 4: Deploy backend**

```bash
git push origin main
ssh deploy@75.119.153.118 "cd /opt/master_bot && git pull origin main --ff-only && docker compose up -d --build"
```
Expected: containers recreated and Up, `curl https://api.crmfit.ru/health` → `{"status":"ok"}`.

**Step 5: Deploy miniapp**

```bash
bash deploy_miniapp.sh
```
Expected: build + upload completes, nginx reloaded.

**Step 6: Smoke test новых эндпоинтов**

```bash
# Проверить что эндпоинты зарегистрированы
curl -s https://api.crmfit.ru/openapi.json | python3 -c \
  "import sys,json; paths=json.load(sys.stdin)['paths']; \
   print('\n'.join(k for k in paths if 'avatar' in k or 'portfolio/upload' in k))"
```
Expected: видим `/api/master/avatar/upload`, `/api/master/avatar`, `/api/master/portfolio/upload`.

**Step 7: Final commit of session state**

После успешного деплоя обновить:
- `/Users/evgenijpastusenko/Projects/agent1/project_ai_context/master-bot/AGENT_STATE.md`
- `/Users/evgenijpastusenko/Projects/agent1/project_ai_context/master-bot/SESSION_LOG.md`
