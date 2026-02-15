# TG Flowers Bot

Telegram-бот — цветочный магазин с микросервисной архитектурой.

## Архитектура

Проект состоит из следующих микросервисов:

| Сервис | Порт | Описание |
|--------|------|----------|
| **catalog-service** | 8001 | Управление каталогом товаров, категориями, магазинами |
| **order-service** | 8002 | Корзина и оформление заказов |
| **analytics-service** | 8003 | Аналитика и метрики (просмотры, популярные товары) |
| **main-bot** | — | Telegram-бот для покупателей |
| **admin-bot** | — | Telegram-бот для администраторов |
| **nginx** | 80 | Прокси для API + раздача веб-приложений |
| **PostgreSQL** | 5432 | База данных |
| **Kafka + Zookeeper** | 9092 | Очередь сообщений между сервисами |

### Технологии

- **Python 3.11** — FastAPI, python-telegram-bot, SQLAlchemy (async), aiokafka
- **PostgreSQL 15** — хранение данных
- **Apache Kafka** — межсервисное взаимодействие (события просмотров, заказов)
- **Docker / Docker Compose** — контейнеризация и оркестрация
- **Nginx** — API-шлюз и раздача статики

## Функциональность

### Бот для покупателей (main-bot)
- Отправка местоположения или выбор адреса на карте
- Просмотр каталога через Telegram Web App (категории, товары, цены)
- Просмотр деталей товара (изображение, цена, описание, наличие в магазинах)
- Корзина товаров (добавление, изменение количества, удаление)
- Оформление заказа: самовывоз (выбор магазина и времени) или доставка (подтверждение адреса)
- Просмотр истории заказов

### Бот для администраторов (admin-bot)
- Управление каталогом (добавление, редактирование, удаление товаров и категорий)
- Управление наличием товаров по магазинам
- Просмотр и управление заказами (изменение статуса)
- Дашборд метрик:
  - Количество заказов, выручка, средний чек
  - Популярные товары по просмотрам и по заказам

## Запуск

### 1. Создание Telegram-ботов

Перед запуском необходимо создать двух ботов в Telegram:

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания **основного бота** (для покупателей)
4. Скопируйте полученный токен (формат: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Повторите шаги 2-4 для создания **бота администратора**

### 2. Настройка окружения

Скопируйте файл `.env.example` в `.env` и настройте переменные:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```
# Токены ботов (получите от @BotFather)
MAIN_BOT_TOKEN=ваш_токен_основного_бота
ADMIN_BOT_TOKEN=ваш_токен_бота_админки

# URL веб-приложений (ОБЯЗАТЕЛЬНО HTTPS!)
MAIN_WEBAPP_URL=https://ваш-домен.com/customer
ADMIN_WEBAPP_URL=https://ваш-домен.com/admin
```

**Важно:**
- Токены в `.env.example` являются примерами и не будут работать!
- **WEBAPP_URL должен быть HTTPS!** Telegram требует HTTPS для Mini App
- Все остальные переменные окружения (DATABASE_URL, KAFKA_BOOTSTRAP_SERVERS и т.д.) **автоматически настраиваются** в docker-compose.yml

**Что нужно в `.env`:**
- `MAIN_BOT_TOKEN` и `ADMIN_BOT_TOKEN` — токены ботов
- `MAIN_WEBAPP_URL` и `ADMIN_WEBAPP_URL` — публичные HTTPS URL веб-приложений

### 3. Запуск всех сервисов

```bash
docker compose up --build
```

### 4. Проверка работы ботов

После запуска откройте своих ботов в Telegram и отправьте команду `/start`. Бот должен ответить приветственным сообщением.

### 5. Остановка

```bash
docker compose down
```

## Устранение неполадок

### Боты не отвечают (молчат)

Если боты запущены, но не отвечают на сообщения:

1. **Проверьте токены ботов**
   - Убедитесь, что файл `.env` существует и содержит реальные токены от @BotFather
   - Токены должны быть в формате: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

2. **Проверьте логи ботов**
   ```bash
   docker compose logs main-bot
   docker compose logs admin-bot
   ```

   Ищите сообщения об ошибках:
   - `TELEGRAM_BOT_TOKEN environment variable is not set` — токен не установлен
   - `Unauthorized` или `401` — неверный токен
   - `ModuleNotFoundError` — отсутствует зависимость

3. **Пересоберите образы после изменений**
   ```bash
   docker compose down
   docker compose up --build
   ```

4. **Проверьте состояние контейнеров**
   ```bash
   docker compose ps
   ```
   Все сервисы должны быть в статусе `Up`

### Ошибки при запуске сервисов

Если какой-либо сервис не запускается:

1. Проверьте доступность портов (5432, 8001, 8002, 8003, 80)
2. Убедитесь, что Docker и Docker Compose установлены корректно
3. Проверьте логи конкретного сервиса: `docker compose logs <имя-сервиса>`

### Настройка WEBAPP_URL (HTTPS для Telegram Mini App)

Telegram требует **HTTPS** для веб-приложений (Mini App). Внутренний URL `http://nginx/customer` не подойдёт по двум причинам:
1. Используется HTTP вместо HTTPS
2. Telegram не имеет доступа к внутренней сети Docker

**Варианты решения:**

#### Для локальной разработки (ngrok)

1. Установите [ngrok](https://ngrok.com/):
   ```bash
   # macOS
   brew install ngrok

   # Или скачайте с https://ngrok.com/download
   ```

2. Запустите ngrok для проброса порта 80:
   ```bash
   ngrok http 80
   ```

3. Скопируйте полученный HTTPS URL (например: `https://abc123.ngrok.io`)

4. Укажите в `.env`:
   ```
   MAIN_WEBAPP_URL=https://abc123.ngrok.io/customer
   ADMIN_WEBAPP_URL=https://abc123.ngrok.io/admin
   ```

#### Для продакшена

Используйте ваш домен с SSL-сертификатом:
```
MAIN_WEBAPP_URL=https://yourdomain.com/customer
ADMIN_WEBAPP_URL=https://yourdomain.com/admin
```

**В `.env` нужны переменные:**
```
MAIN_BOT_TOKEN=ваш_токен_основного_бота
ADMIN_BOT_TOKEN=ваш_токен_бота_админки
MAIN_WEBAPP_URL=https://ваш-публичный-домен/customer
ADMIN_WEBAPP_URL=https://ваш-публичный-домен/admin
```

Все остальные переменные окружения (DATABASE_URL, KAFKA_BOOTSTRAP_SERVERS и т.д.) уже правильно настроены в `docker-compose.yml` и не требуют изменений

## API

Все API доступны через nginx на порту 80:

- `GET /api/catalog/categories/` — список категорий
- `GET /api/catalog/products/` — список товаров
- `GET /api/catalog/products/{id}/` — детали товара
- `GET /api/catalog/products/{id}/availability/` — наличие товара
- `GET /api/catalog/stores/` — список магазинов
- `GET /api/catalog/stores/nearby?lat=...&lon=...` — ближайшие магазины
- `GET /api/orders/cart/{user_id}/` — корзина пользователя
- `POST /api/orders/cart/{user_id}/items/` — добавить в корзину
- `POST /api/orders/orders/` — создать заказ
- `GET /api/orders/orders/` — список заказов
- `GET /api/analytics/analytics/dashboard` — дашборд метрик

## Структура проекта

```
├── docker-compose.yml
├── nginx/
│   └── nginx.conf
├── services/
│   ├── catalog-service/    # FastAPI: каталог товаров
│   ├── order-service/      # FastAPI: корзина и заказы
│   ├── analytics-service/  # FastAPI: аналитика
│   ├── main-bot/           # Telegram-бот покупателя
│   └── admin-bot/          # Telegram-бот администратора
└── webapp/
    ├── customer/           # Web App для покупателей
    └── admin/              # Web App для администраторов
```
