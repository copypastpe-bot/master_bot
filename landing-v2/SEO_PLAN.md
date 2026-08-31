# SEO-план развития abooking.org

Дата: 2026-05-26
Основа: seo.md (семантическое ядро) + abooking_seo_report.docx (анализ)

---

## Текущее состояние

- 2 страницы: `/` (RU) и `/en/` (EN)
- Базовая SEO-оптимизация выполнена (title, H1, meta, FAQPage JSON-LD, keywords)
- Сайт проиндексирован Google, sitemap.xml подан
- Стек: Vite + чистый HTML/CSS/JS, деплой через `deploy_landing.sh`

---

## Фаза 1 — Нишевые лендинги RU (P0)

Цель: поймать низкочастотный целевой трафик по конкретным профессиям и сценариям.

### Страницы

| URL | Title | Целевой кластер |
|-----|-------|-----------------|
| `/ru/online-booking/` | Онлайн-запись клиентов для частного мастера — Abooking | онлайн запись клиентов, программа для онлайн записи, запись клиентов онлайн бесплатно |
| `/ru/telegram-crm/` | CRM в Telegram для мастеров — запись, клиенты, рассылки | telegram crm для мастеров, crm в telegram, telegram mini app для бизнеса |
| `/ru/manicure/` | CRM и онлайн-запись для мастера маникюра в Telegram | crm для маникюра, crm для мастера маникюра, программа для записи на маникюр |

### Структура каждого лендинга

1. Hero: H1 с ключевой фразой + подзаголовок + CTA
2. Проблема (2-3 боли ниши)
3. Решение (как abooking закрывает боли)
4. Возможности (3-4 фичи, релевантные нише)
5. Скриншот/визуал
6. CTA + FAQ (2-3 вопроса, специфичных для ниши)
7. JSON-LD: FAQPage + BreadcrumbList

### Технические задачи

- [ ] Создать шаблон нишевого лендинга (переиспользуемый HTML/CSS)
- [ ] Добавить маршруты в `vite.config.js` (rollupOptions.input)
- [ ] Добавить BreadcrumbList JSON-LD на все страницы
- [ ] Обновить sitemap.xml при добавлении страниц
- [ ] Добавить навигационные ссылки в footer главной

---

## Фаза 2 — Коммерческие лендинги RU (P1)

| URL | Title | Целевой кластер |
|-----|-------|-----------------|
| `/ru/crm-dlya-mastera/` | CRM для частного мастера — простая программа учёта клиентов | crm для частного мастера, простая crm для одного мастера, программа учета клиентов |
| `/ru/free-crm/` | Бесплатная CRM для мастера в Telegram | бесплатная crm для мастера, crm с бесплатным периодом |
| `/ru/client-reminders/` | Напоминания клиентам о записи в Telegram | напоминания клиентам, автоматические напоминания telegram, сокращение no-show |
| `/ru/client-base/` | База клиентов с историей визитов для мастера | база клиентов с историей, программа лояльности для мастеров |

---

## Фаза 3 — Нишевые лендинги RU (P1-P2)

| URL | Title |
|-----|-------|
| `/ru/beauty-master/` | CRM для бьюти-мастера: клиенты, записи и напоминания в Telegram |
| `/ru/massage/` | Онлайн-запись и база клиентов для массажиста |
| `/ru/tutor/` | CRM и расписание для репетитора в Telegram |
| `/ru/fitness-trainer/` | Онлайн-запись и клиентская база для фитнес-тренера |
| `/ru/cleaner/` | CRM для клинера: заказы, клиенты и напоминания |
| `/ru/lashmaker/` | CRM для лэшмейкера — запись и напоминания в Telegram |
| `/ru/brow-master/` | CRM для бровиста — онлайн-запись клиентов |

---

## Фаза 4 — Страницы сравнений (P1)

| URL | Идея |
|-----|------|
| `/ru/yclients-alternative/` | YCLIENTS для салонов, Abooking — для одного мастера в Telegram. Таблица сравнения. |
| `/ru/dikidi-alternative/` | Dikidi массовый, Abooking легче за счёт Telegram. Без установки приложения. |
| `/ru/altegio-alternative/` | Altegio B2B/салоны, Abooking — быстрый старт частного мастера. |

Принципы:
- Не атаковать конкурента, сравнивать сценарии использования
- Таблица: установка, запись, база, рассылки, бонусы, цена
- Фокус на простоте и Telegram как УТП

---

## Фаза 5 — EN-раздел (P1-P2)

| URL | Title | Целевой кластер |
|-----|-------|-----------------|
| `/en/appointment-booking-app/` | Free Appointment Booking App in Telegram — Abooking | appointment booking app, online appointment booking |
| `/en/telegram-booking-bot/` | Telegram Booking Bot for Solo Professionals | telegram booking bot, telegram appointment bot |
| `/en/booking-app-for-freelancers/` | Booking App for Freelancers — Manage Clients in Telegram | booking app for freelancers, client management app |
| `/en/free-appointment-booking-app/` | Free Appointment Booking App — No Download Required | free appointment booking app |
| `/en/nail-appointment-booking-app/` | Nail Appointment Booking App in Telegram | nail appointment booking app |
| `/en/barber-appointment-booking-app/` | Barber Appointment Booking App — Free in Telegram | barber appointment booking app |
| `/en/salon-booking-app/` | Salon Booking App in Telegram — Abooking | salon booking app |

EN-сравнения (после базовых):
| `/en/fresha-alternative/` | Fresha Alternative for Solo Professionals |
| `/en/calendly-alternative/` | Calendly Alternative for Service Providers |

---

## Фаза 6 — Контент-маркетинг (блог)

Формат: статьи под информационные long-tail запросы с перелинковкой на лендинги.

### RU-статьи

| Тема | Целевые запросы |
|------|-----------------|
| Как сделать онлайн-запись клиентов бесплатно | как сделать онлайн запись клиентов, онлайн запись бесплатно |
| Как вернуть клиентов мастеру: 5 способов | как вернуть клиентов мастеру, повторные продажи для мастеров |
| Переход с блокнота на CRM: опыт мастера маникюра | переход с блокнота на crm, опыт использования telegram crm |
| Как работает CRM в Telegram: полный гайд | как работает crm в telegram, преимущества telegram mini app |
| Программа лояльности для мастеров: зачем и как | программа лояльности для мастеров, бонусы для клиентов |
| Сравнение CRM для частных мастеров 2026 | лучшая crm для частных специалистов, отзывы crm для мастеров |

### EN-статьи

| Тема | Целевые запросы |
|------|-----------------|
| How to set up online appointment booking for free | free appointment booking, easy scheduling app |
| Telegram Mini App for business: complete guide | telegram mini app for business, telegram based booking system |
| Best booking app for independent contractors 2026 | best booking app for independent contractors |

### Технические задачи для блога

- [ ] Выбрать формат: статичные HTML или генерация (markdown → HTML)
- [ ] Создать шаблон статьи с sidebar, breadcrumbs, related posts
- [ ] Настроить URL-структуру: `/ru/blog/{slug}/` и `/en/blog/{slug}/`
- [ ] Добавить Article JSON-LD schema

---

## Техническое SEO — сквозные задачи

### Сейчас

- [x] Title, H1, meta description с ключевыми фразами
- [x] FAQPage JSON-LD
- [x] theme-color meta
- [x] hreflang RU/EN/x-default
- [x] canonical URLs
- [x] robots.txt + sitemap.xml
- [x] OG + Twitter Cards

### Ближайшее

- [ ] Подать сайт в Google Search Console
- [ ] Подать сайт в Yandex Webmaster
- [ ] Подать сайт в Bing Webmaster (BingSiteAuth.xml уже есть)
- [ ] Добавить BreadcrumbList JSON-LD на все страницы
- [ ] Preload шрифт Inter (критический ресурс для LCP)
- [ ] Оптимизировать изображения: WebP + srcset + explicit width/height
- [ ] Добавить `<link rel="preload">` для hero-картинки (LCP)
- [ ] Проверить Core Web Vitals через PageSpeed Insights
- [ ] Настроить 301 редиректы если будут менять URL

### Перелинковка

- [ ] Footer: ссылки на ключевые лендинги (online-booking, telegram-crm, manicure)
- [ ] Каждый нишевый лендинг ссылается на главную и на 2-3 смежных
- [ ] Статьи блога ссылаются на лендинги как CTA
- [ ] Страницы сравнений ссылаются на функциональные лендинги

---

## Внешнее SEO

- [ ] Добавить ссылку на сайт в описание Telegram-бота (BotFather)
- [ ] Профили на ProductHunt, AlternativeTo, G2 (backlinks)
- [ ] Ответы на Quora/Reddit/VC.ru с упоминанием abooking
- [ ] Гостевые посты на тематических ресурсах (beauty/freelance блоги)
- [ ] Каталоги Telegram-ботов и Mini Apps

---

## Приоритеты и порядок

```
Фаза 1 (неделя 1-2)  →  3 нишевых лендинга RU + шаблон
Фаза 4 (неделя 2-3)  →  2 страницы сравнений RU
Фаза 2 (неделя 3-4)  →  4 коммерческих лендинга RU
Фаза 5 (неделя 4-5)  →  3-4 EN-лендинга
Фаза 3 (неделя 5-6)  →  5-7 доп. нишевых RU
Фаза 6 (неделя 6+)   →  блог, первые 3-4 статьи
```

---

## Метрики успеха

- Google Search Console: impressions, clicks, avg position по целевым запросам
- Количество проиндексированных страниц
- Позиции по 10 главным ключам (ручная проверка или Ubersuggest)
- CTR в SERP (цель: >5% для branded, >3% для non-branded)
- Органический трафик → конверсия в переход на бота
