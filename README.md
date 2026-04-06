# payment-gateway-faststream

Упрощенный платежный шлюз на FastAPI с интеграцией провайдера.

## Быстрый старт

```bash
git clone <gitgub.com/PSKonch/payment-gateway-faststream>
cd payment-gateway-faststream
docker compose up --build
```

Swagger:
- http://127.0.0.1:8000/docs

## Запуск тестов

1. Подготовьте окружение:

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

2. Подготовьте конфиг для тестового запуска:

```bash
cp .env.test .env
```

3. Запустите тесты:

```bash
pytest -q
```

Примечание:
- `.env.example` содержит рабочие дефолты для запуска проекта.
- `.env.test` содержит отдельные дефолты для тестового запуска.

## Аутентификация (текущее поведение)

Защищенные merchant-ручки требуют:
- `X-API-Key`

`X-Signature` обязателен только для strict-режима.

Формат `X-API-Key`:

```text
<key_id>:<secret>
```

Пример:

```text
testm001:test-secret-merchant-1
```

Для strict-режима подпись считается по canonical request:

```text
canonical_request = <METHOD>\n<PATH>\n<BODY_SHA256_HEX>
X-Signature = HMAC-SHA256(canonical_request, secret)
```

Где:
- `METHOD` - HTTP-метод в верхнем регистре
- `PATH` - путь без query string (например, `/api/v1/payments`)
- `BODY_SHA256_HEX` - SHA256 от raw body bytes
- для `GET` без тела используется SHA256 от пустой строки

## DEV bypass по умолчанию

По умолчанию включен dev-bypass для выделенного пользователя.

Значения по умолчанию:

```text
AUTH_DEV_BYPASS_ENABLED=true
AUTH_DEV_BYPASS_KEY_IDS=devbypass001
AUTH_DEV_BYPASS_MERCHANT_NAME=Dev Bypass Merchant
AUTH_DEV_BYPASS_API_KEY_ID=devbypass001
AUTH_DEV_BYPASS_SECRET=dev-bypass-secret
AUTH_DEV_BYPASS_BALANCE=100000
```

Пример bypass ключа:

```text
devbypass001:dev-bypass-secret
```

Для Swagger UI также поддержан формат только `key_id`:

```text
devbypass001
```

Bypass работает только для `key_id`, перечисленных в `AUTH_DEV_BYPASS_KEY_IDS`.

## Проверка flow через curl

1. Проверка health:

```bash
curl -s http://127.0.0.1:8000/health
```

2. Проверка профиля bypass-мерчанта (без подписи):

```bash
curl -s http://127.0.0.1:8000/api/v1/me \
	-H 'X-API-Key: devbypass001:dev-bypass-secret'
```

3. Создание платежа (без подписи):

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/payments \
	-H 'Content-Type: application/json' \
	-H 'X-API-Key: devbypass001:dev-bypass-secret' \
	-d '{"merchant_order_id":"order-1001","amount":10000}'
```

4. Подождать 1-3 секунды и повторить `GET /api/v1/me`.

## Strict-режим (опционально)

Если нужен полноценный strict-путь с проверкой подписи:

1. Установите `AUTH_DEV_BYPASS_ENABLED=false` в `.env`.
2. Перезапустите проект: `docker compose up --build`.
3. Генерируйте подпись helper-скриптом `scripts/sign_request.py`.

## Последовательность проверки (коротко)

1. `GET /health`
2. `GET /api/v1/me`
3. `POST /api/v1/payments`
4. Подождать 1-3 секунды (асинхронный этап outbox -> broker -> consumer -> provider)
5. Снова `GET /api/v1/me` и проверить итоговый баланс

## Подробная инструкция

Полный пошаговый гайд по запуску и e2e проверке:
- `docs/run_guide.md`

## API для проверки

- `GET /health`
- `GET /api/v1/me`
- `POST /api/v1/payments`

## Fake provider

Provider работает как отдельное приложение и отдельный контейнер в `docker-compose`.

Provider принимает создание платежа и отвечает строго по ТЗ:

```text
{ "id": "string", "external_invoice_id": "string", "amount": int, "callback_url": "string", "status": "Created" }
```

После этого provider делает `POST {callback_url}` с телом вебхука:

```text
{ "id": "string", "external_invoice_id": "string", "status": "Created|Completed|Canceled" }
```

## Полезные файлы

- `app/api/dependencies.py` - проверка merchant-подписей
- `app/services/signature_service.py` - canonical signing
- `scripts/sign_request.py` - локальный helper для подписи
- `scripts/seed_data.py` - idempotent seed мерчантов и (опционально) dev-bypass мерчанта
- `docs/run_guide.md` - детальная инструкция запуска и ручной проверки
- `docs/test_assignment_flow.md` - подробный флоу проверки тестового задания (от старта до финального статуса)
