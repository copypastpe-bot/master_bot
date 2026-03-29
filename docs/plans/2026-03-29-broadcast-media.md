# Broadcast с медиа — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Добавить шаг загрузки медиа (фото/видео) в рассылки Mini App, перестроив 3 шага в 4: Текст → Медиа → Сегмент → Подтверждение.

**Architecture:** Backend: `POST /broadcast/send` переходит с JSON на `multipart/form-data` (FastAPI `Form()` + `UploadFile`), `POST /broadcast/preview` остаётся JSON с двумя новыми опциональными полями. Frontend: полный рефактор `Broadcast.jsx` — новый шаг `StepMedia`, изменение порядка шагов, `sendBroadcast` в `api/client.js` всегда шлёт FormData.

**Tech Stack:** FastAPI `Form` + `UploadFile` + `File`, aiogram 3 `BufferedInputFile`, React 19 + `@tanstack/react-query` + axios FormData.

---

### Task 1: Backend — обновить `POST /broadcast/preview`

**Files:**
- Modify: `src/api/routers/master/broadcast.py:31-51`

**Step 1: Добавить поля `has_media` и `media_type` в `PreviewRequest`**

```python
# src/api/routers/master/broadcast.py

class PreviewRequest(BaseModel):
    segment: str
    text: str
    has_media: bool = False
    media_type: Optional[str] = None  # "photo" | "video" | None

    @field_validator("segment")
    @classmethod
    def validate_segment(cls, v: str) -> str:
        if v not in VALID_SEGMENTS:
            raise ValueError(f"Unknown segment: {v}")
        return v

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text cannot be empty")
        if len(v) > MAX_TEXT_LENGTH:
            raise ValueError(f"text exceeds {MAX_TEXT_LENGTH} characters")
        return v
```

**Step 2: Обновить хэндлер preview чтобы возвращал `has_media` и `media_type`**

```python
@router.post("/master/broadcast/preview")
async def preview_broadcast(
    body: PreviewRequest,
    master: Master = Depends(get_current_master),
):
    """Preview broadcast — return personalized example and sample recipients."""
    recipients = await get_clients_by_segment(master.id, body.segment)

    preview_text = body.text
    sample_recipients = []

    if recipients:
        first_name = recipients[0].get("name") or "Клиент"
        preview_text = _personalize(body.text, first_name)
        sample_recipients = [
            _abbreviate_name(r["name"]) for r in recipients[:3]
        ]

    return {
        "recipients_count": len(recipients),
        "preview_text": preview_text,
        "sample_recipients": sample_recipients,
        "has_media": body.has_media,
        "media_type": body.media_type,
    }
```

**Step 3: Проверить вручную**

```bash
curl -s -X POST http://localhost:8000/api/master/broadcast/preview \
  -H "Content-Type: application/json" \
  -H "X-Init-Data: dev" \
  -d '{"segment":"all","text":"Привет {name}!","has_media":true,"media_type":"photo"}' | python3 -m json.tool
```

Ожидаемый ответ содержит `"has_media": true, "media_type": "photo"`.

**Step 4: Commit**

```bash
git add src/api/routers/master/broadcast.py
git commit -m "feat(broadcast): preview returns has_media and media_type fields"
```

---

### Task 2: Backend — обновить `POST /broadcast/send` на multipart/form-data

**Files:**
- Modify: `src/api/routers/master/broadcast.py`

**Step 1: Заменить импорты и удалить `SendRequest`**

В начале файла добавить недостающие импорты:

```python
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from aiogram.types import BufferedInputFile
```

Удалить весь класс `SendRequest` (строки 53–73 в текущем файле).

**Step 2: Переписать хэндлер `/broadcast/send`**

```python
PHOTO_MAX_BYTES = 10 * 1024 * 1024   # 10 MB
VIDEO_MAX_BYTES = 50 * 1024 * 1024   # 50 MB


@router.post("/master/broadcast/send")
async def send_broadcast(
    request: Request,
    segment: str = Form(...),
    text: str = Form(...),
    media_type: Optional[str] = Form(None),
    media: Optional[UploadFile] = File(None),
    master: Master = Depends(get_current_master),
):
    """Send broadcast to selected segment via client_bot."""
    # Validate segment
    if segment not in VALID_SEGMENTS:
        raise HTTPException(status_code=422, detail="Unknown segment")

    # Validate text
    text = text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text cannot be empty")
    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=422, detail=f"text exceeds {MAX_TEXT_LENGTH} characters")

    # Read and validate media
    media_bytes: Optional[bytes] = None
    if media is not None and media_type in ("photo", "video"):
        media_bytes = await media.read()
        limit = PHOTO_MAX_BYTES if media_type == "photo" else VIDEO_MAX_BYTES
        if len(media_bytes) > limit:
            limit_mb = limit // (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"{media_type} exceeds {limit_mb} MB limit",
            )

    recipients = await get_clients_by_segment(master.id, segment)

    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients in this segment")

    client_bot = getattr(request.app.state, "client_bot", None)
    if not client_bot:
        raise HTTPException(status_code=503, detail="client_bot not available")

    sent = 0
    failed = 0

    for client in recipients:
        tg_id = client.get("tg_id")
        if not tg_id:
            failed += 1
            continue
        try:
            personalized = _personalize(text, client.get("name") or "")
            if media_bytes and media_type == "photo":
                file_obj = BufferedInputFile(media_bytes, filename="photo.jpg")
                await client_bot.send_photo(chat_id=tg_id, photo=file_obj, caption=personalized)
            elif media_bytes and media_type == "video":
                file_obj = BufferedInputFile(media_bytes, filename="video.mp4")
                await client_bot.send_video(chat_id=tg_id, video=file_obj, caption=personalized)
            else:
                await client_bot.send_message(chat_id=tg_id, text=personalized)
            sent += 1
            await asyncio.sleep(0.05)
        except TelegramForbiddenError:
            logger.warning(f"Broadcast: client {tg_id} blocked the bot")
            failed += 1
        except Exception as e:
            logger.error(f"Broadcast: failed to send to {tg_id}: {e}")
            failed += 1

    await save_campaign(
        master_id=master.id,
        campaign_type="broadcast",
        title=None,
        text=text,
        active_from=None,
        active_to=None,
        sent_count=sent,
        segment=segment,
    )

    return {"sent_count": sent, "failed_count": failed}
```

**Step 3: Проверить что сервер запускается без ошибок**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python3 -c "from src.api.routers.master.broadcast import router; print('OK')"
```

Ожидаемый вывод: `OK`

**Step 4: Commit**

```bash
git add src/api/routers/master/broadcast.py
git commit -m "feat(broadcast): send endpoint accepts multipart/form-data with optional media"
```

---

### Task 3: Frontend — обновить `sendBroadcast` в `api/client.js`

**Files:**
- Modify: `miniapp/src/api/client.js:67-68`

**Step 1: Заменить функцию `sendBroadcast`**

Найти строки:
```js
export const sendBroadcast = (data) =>
  api.post('/api/master/broadcast/send', data).then(r => r.data);
```

Заменить на:
```js
export const sendBroadcast = (formData) =>
  api.post('/api/master/broadcast/send', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  }).then(r => r.data);
```

**Step 2: Проверить что файл сохранился корректно**

```bash
grep -n "sendBroadcast" /Users/evgenijpastusenko/Projects/Master_bot/miniapp/src/api/client.js
```

Ожидаемый вывод: строки с `formData` и `timeout: 120000`.

**Step 3: Commit**

```bash
git add miniapp/src/api/client.js
git commit -m "feat(broadcast): sendBroadcast always uses FormData with 120s timeout"
```

---

### Task 4: Frontend — новый `StepMedia` и рефактор `Broadcast.jsx`

**Files:**
- Modify: `miniapp/src/master/pages/Broadcast.jsx`

Это самая большая задача. Делаем полный рефактор файла.

**Step 1: Обновить `ProgressBar` на 4 шага**

Найти:
```jsx
function ProgressBar({ step }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      padding: '12px 16px',
    }}>
      {[1, 2, 3].map((s) => (
```

Заменить `[1, 2, 3]` на `[1, 2, 3, 4]`:
```jsx
      {[1, 2, 3, 4].map((s) => (
```

**Step 2: Добавить новый компонент `StepMedia` после `StepText` (примерно после строки 204)**

```jsx
// ─── Step 2: Media upload ─────────────────────────────────────────────────────

const PHOTO_MAX_MB = 10;
const VIDEO_MAX_MB = 50;

function StepMedia({ mediaFile, mediaType, onFileChange, onRemove, onSkip, onNext }) {
  const inputRef = useRef(null);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const isPhoto = file.type.startsWith('image/');
    const isVideo = file.type === 'video/mp4';

    if (!isPhoto && !isVideo) {
      alert('Поддерживаются только JPEG, PNG и MP4');
      return;
    }

    const maxBytes = isPhoto ? PHOTO_MAX_MB * 1024 * 1024 : VIDEO_MAX_MB * 1024 * 1024;
    if (file.size > maxBytes) {
      const limit = isPhoto ? PHOTO_MAX_MB : VIDEO_MAX_MB;
      alert(`Файл превышает ${limit} МБ`);
      e.target.value = '';
      return;
    }

    onFileChange(file, isPhoto ? 'photo' : 'video');
    haptic();
  };

  const previewUrl = mediaFile && mediaType === 'photo'
    ? URL.createObjectURL(mediaFile)
    : null;

  // Cleanup object URL on unmount / file change
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const fileSizeMb = mediaFile ? (mediaFile.size / (1024 * 1024)).toFixed(1) : null;

  return (
    <div style={{ padding: '0 16px 80px' }}>
      <p style={{ color: 'var(--tg-hint)', fontSize: 13, margin: '0 0 16px' }}>
        Добавьте фото или видео к сообщению (необязательно)
      </p>

      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,video/mp4"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />

      {!mediaFile ? (
        /* Upload area */
        <button
          onClick={() => { haptic(); inputRef.current?.click(); }}
          style={{
            width: '100%',
            padding: '32px 16px',
            background: 'var(--tg-secondary-bg)',
            border: '1.5px dashed var(--tg-hint)',
            borderRadius: 14,
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span style={{ fontSize: 36 }}>📎</span>
          <span style={{ color: 'var(--tg-button)', fontSize: 15, fontWeight: 600 }}>
            Выбрать фото или видео
          </span>
          <span style={{ color: 'var(--tg-hint)', fontSize: 12 }}>
            JPEG, PNG до {PHOTO_MAX_MB} МБ · MP4 до {VIDEO_MAX_MB} МБ
          </span>
        </button>
      ) : (
        /* Preview area */
        <div style={{
          background: 'var(--tg-secondary-bg)',
          borderRadius: 14,
          overflow: 'hidden',
        }}>
          {mediaType === 'photo' && previewUrl ? (
            <img
              src={previewUrl}
              alt="preview"
              style={{
                width: '100%',
                maxHeight: 240,
                objectFit: 'cover',
                display: 'block',
              }}
            />
          ) : (
            <div style={{
              padding: '20px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}>
              <span style={{ fontSize: 32 }}>🎥</span>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--tg-text)' }}>
                  {mediaFile.name}
                </div>
                <div style={{ fontSize: 12, color: 'var(--tg-hint)', marginTop: 2 }}>
                  {fileSizeMb} МБ
                </div>
              </div>
            </div>
          )}

          <button
            onClick={() => { haptic(); onRemove(); }}
            style={{
              width: '100%',
              padding: '10px',
              background: 'none',
              border: 'none',
              borderTop: '1px solid var(--tg-hint)',
              color: '#e74c3c',
              fontSize: 14,
              cursor: 'pointer',
            }}
          >
            Удалить
          </button>
        </div>
      )}

      {/* Bottom buttons */}
      <div style={{
        position: 'fixed',
        bottom: 0, left: 0, right: 0,
        padding: '12px 16px',
        background: 'var(--tg-bg)',
        display: 'flex',
        gap: 8,
      }}>
        {!mediaFile && (
          <button
            onClick={() => { haptic(); onSkip(); }}
            style={{
              flex: 1,
              padding: '14px',
              background: 'var(--tg-secondary-bg)',
              color: 'var(--tg-text)',
              border: 'none',
              borderRadius: 12,
              fontSize: 15,
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Пропустить
          </button>
        )}
        <button
          onClick={() => { haptic(); onNext(); }}
          style={{
            flex: mediaFile ? 1 : undefined,
            flexGrow: 1,
            padding: '14px',
            background: 'var(--tg-button)',
            color: 'var(--tg-button-text)',
            border: 'none',
            borderRadius: 12,
            fontSize: 16,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Далее
        </button>
      </div>
    </div>
  );
}
```

**Step 3: Обновить `StepSegment` — убрать фиксированную кнопку "Далее" (у неё уже всё правильно)**

Кнопку "Далее" у `StepText` нужно обновить — сейчас она говорит "Предпросмотр", теперь должна говорить "Далее":

Найти в `StepText`:
```jsx
          Предпросмотр
```

Заменить на:
```jsx
          Далее
```

**Step 4: Обновить `StepPreview` — добавить отображение медиа-индикатора**

В `StepPreview` (функция и её параметры), добавить `has_media` и `media_type`:

Найти:
```jsx
function StepPreview({ segment, text, previewData, isLoading, onSend, isSending }) {
```

Заменить на:
```jsx
function StepPreview({ segment, text, mediaFile, mediaType, previewData, isLoading, onSend, isSending }) {
```

После блока `{/* Recipient count */}` (примерно после строки 267), добавить медиа-индикатор перед блоком "Пример сообщения":

```jsx
      {/* Media indicator */}
      {mediaFile && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '12px 14px',
          background: 'var(--tg-secondary-bg)',
          borderRadius: 12,
          marginBottom: 12,
        }}>
          <span style={{ fontSize: 22 }}>{mediaType === 'photo' ? '🖼️' : '🎥'}</span>
          <div style={{ fontSize: 14, color: 'var(--tg-text)' }}>
            {mediaType === 'photo' ? 'Фото приложено' : 'Видео приложено'}
          </div>
        </div>
      )}
```

**Step 5: Обновить главный компонент `Broadcast`**

Полностью заменить всё от `export default function Broadcast()` до конца файла:

```jsx
export default function Broadcast() {
  const [step, setStep] = useState(1);
  const [text, setText] = useState('');
  const [mediaFile, setMediaFile] = useState(null);
  const [mediaType, setMediaType] = useState(null);
  const [selectedSegment, setSelectedSegment] = useState(null);
  const [sendResult, setSendResult] = useState(null);

  // Back button: show on steps 2–4, hide on success
  const handleBack = useCallback(() => {
    if (step > 1) setStep(s => s - 1);
  }, [step]);
  useBackButton(handleBack, step > 1 && !sendResult);

  // Load segments on mount
  const {
    data: segmentsData,
    isLoading: segmentsLoading,
    isError: segmentsError,
  } = useQuery({
    queryKey: ['broadcast-segments'],
    queryFn: getBroadcastSegments,
    staleTime: 60 * 1000,
  });

  const segments = segmentsData?.segments || [];

  // Preview query — runs when entering step 4
  const {
    data: previewData,
    isLoading: previewLoading,
  } = useQuery({
    queryKey: ['broadcast-preview', selectedSegment, text, !!mediaFile, mediaType],
    queryFn: () => previewBroadcast({
      segment: selectedSegment,
      text,
      has_media: !!mediaFile,
      media_type: mediaFile ? mediaType : null,
    }),
    enabled: step === 4 && !!selectedSegment && text.trim().length > 0,
    staleTime: 0,
  });

  // Send mutation
  const sendMutation = useMutation({
    mutationFn: sendBroadcast,
    onSuccess: (data) => {
      setSendResult(data);
      if (typeof WebApp?.MainButton?.hideProgress === 'function') {
        WebApp.MainButton.hideProgress();
      }
      if (typeof WebApp?.MainButton?.hide === 'function') {
        WebApp.MainButton.hide();
      }
    },
    onError: (err) => {
      if (typeof WebApp?.MainButton?.hideProgress === 'function') {
        WebApp.MainButton.hideProgress();
      }
      const msg = err?.response?.data?.detail || 'Ошибка отправки';
      alert(msg);
    },
  });

  // Hide MainButton when not on step 4
  useEffect(() => {
    if (step !== 4 && !sendResult) {
      if (typeof WebApp?.MainButton?.hide === 'function') {
        WebApp.MainButton.hide();
      }
    }
  }, [step, sendResult]);

  const handleSend = useCallback(() => {
    haptic();
    if (!selectedSegment || !text.trim()) return;

    const fd = new FormData();
    fd.append('segment', selectedSegment);
    fd.append('text', text.trim());
    if (mediaFile && mediaType) {
      fd.append('media_type', mediaType);
      fd.append('media', mediaFile);
    }
    sendMutation.mutate(fd);
  }, [selectedSegment, text, mediaFile, mediaType, sendMutation]);

  const handleReset = () => {
    setStep(1);
    setText('');
    setMediaFile(null);
    setMediaType(null);
    setSelectedSegment(null);
    setSendResult(null);
  };

  if (sendResult) {
    return <SuccessScreen result={sendResult} onReset={handleReset} />;
  }

  const stepTitles = ['', 'Текст', 'Медиа', 'Аудитория', 'Предпросмотр'];

  return (
    <div>
      {/* Header */}
      <div style={{ padding: '12px 16px 0' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 4,
        }}>
          {step > 1 ? (
            <BackBtn onClick={handleBack} />
          ) : (
            <div style={{ width: 60 }} />
          )}
          <h2 style={{
            margin: 0,
            fontSize: 17,
            fontWeight: 700,
            color: 'var(--tg-text)',
            textAlign: 'center',
            flex: 1,
          }}>
            {stepTitles[step]}
          </h2>
          <div style={{ width: 60 }} />
        </div>

        <ProgressBar step={step} />
      </div>

      {/* Step content */}
      {step === 1 && (
        <StepText
          text={text}
          onTextChange={setText}
          onNext={() => setStep(2)}
        />
      )}

      {step === 2 && (
        <StepMedia
          mediaFile={mediaFile}
          mediaType={mediaType}
          onFileChange={(file, type) => { setMediaFile(file); setMediaType(type); }}
          onRemove={() => { setMediaFile(null); setMediaType(null); }}
          onSkip={() => setStep(3)}
          onNext={() => setStep(3)}
        />
      )}

      {step === 3 && (
        segmentsLoading ? (
          <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
            Загрузка...
          </div>
        ) : segmentsError ? (
          <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--tg-hint)' }}>
            Ошибка загрузки сегментов
          </div>
        ) : (
          <StepSegment
            segments={segments}
            selected={selectedSegment}
            onSelect={setSelectedSegment}
            onNext={() => setStep(4)}
          />
        )
      )}

      {step === 4 && (
        <StepPreview
          segment={selectedSegment}
          text={text}
          mediaFile={mediaFile}
          mediaType={mediaType}
          previewData={previewData}
          isLoading={previewLoading}
          onSend={handleSend}
          isSending={sendMutation.isPending}
        />
      )}
    </div>
  );
}
```

**Step 6: Добавить `useRef` к импортам**

В самом верху файла найти:
```jsx
import { useState, useEffect, useCallback } from 'react';
```

Заменить на:
```jsx
import { useState, useEffect, useCallback, useRef } from 'react';
```

**Step 7: Проверить сборку**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot/miniapp
npm run build 2>&1 | tail -20
```

Ожидаемый вывод: `✓ built in` без ошибок.

**Step 8: Commit**

```bash
git add miniapp/src/master/pages/Broadcast.jsx
git commit -m "feat(broadcast): 4-step flow with media upload step (StepMedia)"
```

---

### Task 5: Финальная проверка

**Step 1: Проверить что backend запускается**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot
python3 -c "
from src.api.routers.master.broadcast import router
routes = [r.path for r in router.routes]
print(routes)
"
```

Ожидаемый вывод: список с `/master/broadcast/segments`, `/master/broadcast/preview`, `/master/broadcast/send`.

**Step 2: Проверить что `send_broadcast` принимает Form-параметры**

```bash
python3 -c "
import inspect
from src.api.routers.master.broadcast import send_broadcast
sig = inspect.signature(send_broadcast)
print(list(sig.parameters.keys()))
"
```

Ожидаемый вывод: `['request', 'segment', 'text', 'media_type', 'media', 'master']`

**Step 3: Проверить frontend build ещё раз**

```bash
cd /Users/evgenijpastusenko/Projects/Master_bot/miniapp
npm run build 2>&1 | grep -E "(error|warning|built)"
```

Ожидаемый вывод: строка `✓ built in` без `error`.

**Step 4: Финальный commit (если нужны правки)**

```bash
git add -p
git commit -m "fix(broadcast): address review feedback"
```
