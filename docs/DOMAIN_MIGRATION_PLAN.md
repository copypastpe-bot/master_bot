# План миграции Master_bot на новый домен (hard cutover)

Дата: 2026-05-11
Контекст: реальных пользователей нет → переезжаем грубо, без параллельности. Фокус — корректно поднять интеграции с Google, Telegram, nginx/SSL.

> В тексте плана новый домен = `NEWDOMAIN.tld`. Поддоменная схема сохраняется: `app.` (фронт Mini App), `api.` (FastAPI), `masterbot.` (Google OAuth callback), корень (политика конфиденциальности).

---

## 1. Что нужно подготовить заранее (один раз, до старта)

- **Доступы:**
  - регистратор нового домена (для A-записей);
  - SSH к VPS `deploy@75.119.153.118`;
  - [Google Cloud Console](https://console.cloud.google.com/) с правами на проект OAuth-клиента `974446939897-...`;
  - BotFather (есть в Telegram).
- **Имя нового домена** — зафиксировать.
- **Проверить режим OAuth Consent Screen** в Google Cloud → если *Production*, новый домен потребует верификации через Search Console (см. этап 5). Если *Testing* / *Internal* — пропускаем.

---

## 2. Этапы

### Этап 1. DNS

В панели регистратора нового домена завести A-записи на `75.119.153.118`:
- `NEWDOMAIN.tld`
- `app.NEWDOMAIN.tld`
- `api.NEWDOMAIN.tld`
- `masterbot.NEWDOMAIN.tld`

Подождать пропагации, проверить:
```bash
dig +short NEWDOMAIN.tld app.NEWDOMAIN.tld api.NEWDOMAIN.tld masterbot.NEWDOMAIN.tld
```
Все четыре должны вернуть `75.119.153.118`.

### Этап 2. SSL (Let's Encrypt)

На VPS:
```bash
sudo certbot --nginx \
  -d NEWDOMAIN.tld \
  -d app.NEWDOMAIN.tld \
  -d api.NEWDOMAIN.tld \
  -d masterbot.NEWDOMAIN.tld
```
Certbot сам создаст конфиги — но дальше мы их заменим своим. Главное — получить сертификаты в `/etc/letsencrypt/live/*/`.

### Этап 3. Правки в репозитории

Один коммит, всё сразу:

**3.1. `nginx/miniapp.conf`** — глобальная замена `crmfit.ru` → `NEWDOMAIN.tld` в:
- `map $http_origin $cors_origin` (оставить только новый origin, старые `ru.app.crmfit.ru` убрать);
- `server_name` (4 раза);
- пути `ssl_certificate` / `ssl_certificate_key`;
- `root /var/www/app.NEWDOMAIN.tld`.

**3.2. `deploy_miniapp.sh`** — `STATIC_DIR` и echo-строки.

**3.3. `src/config.py:37`**
```python
MINIAPP_URL: str = os.getenv("MINIAPP_URL", "https://app.NEWDOMAIN.tld")
```

**3.4. `src/api/app.py`** — в списке `allow_origins` убрать `https://ru.app.crmfit.ru` (или заменить на новый, если нужен второй вариант). Оставить динамический `MINIAPP_URL`.

**3.5. `src/api/routers/promo_pages.py:61`**
```python
PROMO_PUBLIC_BASE_URL = os.getenv("PROMO_PUBLIC_BASE_URL", "https://api.NEWDOMAIN.tld")
```

**3.6. Захардкоженные ссылки на политику:**
- `src/client_bot.py:320`
- `src/client_bot_legacy.py:374`
- `index.html:414`, `index.html:586`
- `docs/privacy.html:186`, `docs/privacy.html:288`

Везде `https://crmfit.ru/privacy` → `https://NEWDOMAIN.tld/privacy`.

**3.7. Тесты с хостами:**
- `tests/test_landing_profile_task2_api.py`
- `tests/test_promo_page_task2_api.py`
- `tests/test_promo_page_database.py`

Прогнать `pytest -q` локально, убедиться что зелёные.

**3.8. Документация (опционально, но логично в том же коммите):**
- `docs/README.md`
- `prompts/*.md` упоминания crmfit
- `CLAUDE.md` (project file) — если упоминается домен

Коммит → push.

### Этап 4. Прод `.env` на VPS

```env
MINIAPP_URL=https://app.NEWDOMAIN.tld
GOOGLE_REDIRECT_URI=https://masterbot.NEWDOMAIN.tld/auth/google/callback
PROMO_PUBLIC_BASE_URL=https://api.NEWDOMAIN.tld
```

(Остальные переменные не трогаем.)

### Этап 5. Google Cloud Console — OAuth-клиент

APIs & Services → Credentials → ваш OAuth 2.0 Client ID `974446939897-...`:

- **Authorized JavaScript origins:** добавить `https://app.NEWDOMAIN.tld`; старый `https://app.crmfit.ru` удалить.
- **Authorized redirect URIs:** добавить `https://masterbot.NEWDOMAIN.tld/auth/google/callback`; старый удалить.
- Сохранить.

Если приложение в режиме **Production** (а не Testing/Internal) — дополнительно:
- **OAuth consent screen → Authorized domains:** добавить `NEWDOMAIN.tld`, удалить `crmfit.ru`.
- **Application home page / Privacy policy URL:** обновить ссылки на новый домен.
- **Verification:** если требуется подтверждение владения доменом — Google попросит DNS TXT через [Google Search Console](https://search.google.com/search-console). До верификации новый OAuth-флоу для внешних пользователей не запустится. У вас юзеров нет — не блокер для запуска, но сделать сразу, чтобы потом не наткнуться.

### Этап 6. Telegram BotFather

В чате с `@BotFather`:

**Для master_bot:**
- `/mybots` → выбрать master_bot → Bot Settings → Menu Button → Configure Menu Button → URL `https://app.NEWDOMAIN.tld` (или соответствующий путь, посмотреть текущее значение через Menu Button → Current).
- Bot Settings → Domain (для Telegram Login Widget, если используется) → `NEWDOMAIN.tld`.
- Если используется приём платежей — Payments → проверить, что provider не привязан к старому домену.

**Для client_bot** (`handyhomeservice_d_bot`):
- То же самое — Menu Button → `https://app.NEWDOMAIN.tld?app=client` (этот URL формируется в `src/config.py` через `_append_query_param`).

**Privacy Policy:**
- Если бот в BotFather имеет настроенную privacy policy URL — заменить на `https://NEWDOMAIN.tld/privacy`.

### Этап 7. Деплой

На VPS, из чистого worktree:
```bash
cd ~/Master_bot   # или где он лежит
git pull
# Если есть промо-страницы с абсолютными URL в БД — очистить,
# раз реальных пользователей нет:
# sqlite3 db.sqlite3 "DELETE FROM promo_pages;"   # или соответствующий SQL для прод-БД
bash deploy_miniapp.sh
bash restart_bots.sh
```

(Старые server-блоки `*.crmfit.ru` в `nginx/miniapp.conf` уже заменены коммитом этапа 3, при `deploy_miniapp.sh` залит новый конфиг → `nginx -t && reload`. Старый домен перестаёт обслуживаться автоматически.)

### Этап 8. Smoke-test интеграций

Этот этап — главный, ради него весь план.

**8.1. Mini App + API + CORS:**
- Открыть Mini App из master_bot. Должен загрузиться фронт с `app.NEWDOMAIN.tld`, DevTools (Telegram Desktop → Ctrl+Shift+I) — запросы к `api.NEWDOMAIN.tld` зелёные, CORS-ошибок нет.

**8.2. Google Calendar:**
- В Mini App → раздел подключения календаря → жмём «Подключить Google».
- Должен открыться OAuth-консент Google, после согласия — редирект на `https://masterbot.NEWDOMAIN.tld/auth/google/callback?code=...`.
- На бэке (журнал `journalctl -u master_bot -f` или соответствующий) — увидеть успешный обмен code → token.
- Создать тестовое событие в Mini App → проверить, что появилось в Google Calendar.
- Удалить событие в Google Calendar → проверить синк обратно (если он есть).

**8.3. Промо-страница:**
- Создать у тестового мастера промо-страницу со slug `test`.
- Сгенерированная ссылка должна выглядеть как `https://api.NEWDOMAIN.tld/m/test`.
- Открыть в браузере → 200, HTML отдаётся.
- QR-код: если код хранится в БД с абсолютным URL — он указывает уже на новый домен. Старые QR-файлы можно перегенерировать или, проще, удалить и создать заново (юзеров нет — данных не жалко).

**8.4. Telegram Payments (если есть активный flow):**
- Пройти тестовый платёж → убедиться, что `successful_payment` приходит, статус заказа обновляется. Это самое чувствительное место по правилам проекта.

**8.5. Политика конфиденциальности:**
- `https://NEWDOMAIN.tld/privacy` — открывается, отдаёт `docs/privacy.html` (или то, что задеплоено на корневой домен).
- Если корневой домен ничего не отдаёт — нужно отдельно положить static-страницу на nginx (см. этап 9).

### Этап 9. Что может отвалиться и как чинить

| Симптом | Причина | Что делать |
|---|---|---|
| Mini App не загружается, в консоли `CORS error` | В `src/api/app.py` остался старый origin, нового нет | Добавить `https://app.NEWDOMAIN.tld` в `allow_origins`, redeploy |
| OAuth Google: «redirect_uri_mismatch» | В Google Cloud Console не добавлен новый URI или приложение читает старый из `.env` | Проверить точное совпадение URI (https, без trailing slash) в Console и `.env` |
| OAuth Google: «This app isn't verified» / «access blocked» | Production режим OAuth Consent, новый домен не верифицирован | Завершить верификацию домена в Search Console, или временно перевести приложение в Testing и добавить себя в test users |
| `masterbot.NEWDOMAIN.tld` отдаёт 404/502 | В репо нет nginx-конфига для OAuth-сервера (порт 8090), он был только на сервере | Зайти на VPS, посмотреть `/etc/nginx/sites-enabled/`, скопировать старый блок для `masterbot.crmfit.ru`, заменить домен и SSL-пути |
| Telegram Mini App открывает старый URL | BotFather Menu Button не переключён, или у клиента кеш | Перепроверить в BotFather, перезапустить чат с ботом |
| Promo `/m/{slug}` 404 | На прод-БД остались записи с абсолютными старыми URL и/или nginx маршрут на `api.NEWDOMAIN.tld` неполный | Проверить routing в `src/api/app.py`, при необходимости `DELETE FROM promo_pages;` |
| Корневой домен `https://NEWDOMAIN.tld/privacy` → 404 | nginx для корня не настроен | Добавить server-блок для `NEWDOMAIN.tld`, отдавать `/var/www/NEWDOMAIN.tld/privacy.html` (положить туда `docs/privacy.html`) |

### Этап 10. Закрытие сессии

По правилам проекта (`CLAUDE.md`):
1. `git status --short` — пусто;
2. коммиты сделаны малыми логическими порциями;
3. обновить `/Users/evgenijpastusenko/Projects/agent1/project_ai_context/master-bot/AGENT_STATE.md` (≤60 строк);
4. добавить запись в `SESSION_LOG.md` (≤25 строк) — что переехали с crmfit.ru на NEWDOMAIN.tld, deploy SHA.

---

## 3. Что бросается в глаза по интеграциям

**OAuth Consent Screen — основной риск.**
Если приложение опубликовано в Production, отказ Google синхронизировать пока новый домен не верифицирован — самый частый сценарий поломки. Полминуты в Search Console на TXT-запись закрывают вопрос.

**`masterbot.crmfit.ru` отсутствует в репо.**
Файла nginx-конфига для OAuth-сервера в проекте нет — он живёт только на VPS. На этапе 9 это критично: нужно зайти на сервер и руками подготовить аналогичный server-блок для `masterbot.NEWDOMAIN.tld`. Рекомендую заодно положить его в репо (`nginx/oauth.conf`), чтобы в будущем не теряться.

**`docs/privacy.html` тоже нужно куда-то задеплоить.**
В деплой-скрипте сейчас только Mini App едет в `/var/www/app.crmfit.ru`. Корневой домен `crmfit.ru` обслуживается каким-то другим способом (вручную или другим конфигом). На новом домене это нужно повторить — иначе ссылка на политику в Google OAuth Consent Screen будет 404, и Google заверификации не даст.

---

## 4. Что нужно от вас, чтобы стартовать

- Имя нового домена.
- Подтверждение режима OAuth Consent Screen (Production или Testing) — гляньте в Google Cloud Console на странице *OAuth consent screen*, верхний бейдж.
- Доступ-чек: SSH на VPS у вас есть, BotFather и Google Cloud — у вас.

Когда назовёте домен — пройду по этапам конкретно: подготовлю diff для коммита, шаги для VPS и чеклист тестов.
