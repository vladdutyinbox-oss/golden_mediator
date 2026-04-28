
# `model-management-service` — README

## Общее описание

**`model-management-service`** — это центральный сервис управления жизненным циклом моделей в приложении. 

Он выступает как **backend для Model Studio** и является ключевым звеном в цепочке обновления моделей. Основная ответственность — публикация новых версий моделей и распространение информации о них до `rust-inference-service` через событийную архитектуру.

**Ключевое взаимодействие**:  
Публикация версии модели → динамическое обновление конфигурации → применение новой версии в `rust-inference-service` без downtime.

---

## Структура репозитория

```bash
model-management-service/
├── src/
│   ├── main.py                          # Точка входа FastAPI
│   ├── settings.py                      # Конфигурация
│   ├── domain/model/entity.py           # Доменная модель ModelVersion
│   ├── application/model_management/service.py   # Основная бизнес-логика
│   ├── infrastructure/
│   │   ├── kafka/producer.py            # Публикация событий
│   │   └── registry/client.py           # Клиент Model Registry
│   └── tests/
│       ├── unit/                        # Unit-тесты
│       └── integration/                 # Интеграционные тесты
├── k8s/                                 # Kubernetes манифесты
├── Dockerfile
├── docker-compose.yml
├── justfile
├── requirements.txt
├── config.yaml
└── README.md
```

---

## Основные возможности

- Публикация новых версий моделей
- Привязка моделей к AI-личностям
- Управление A/B-тестированием и rollout'ом
- Распространение конфигурации до `rust-inference-service`
- Мониторинг и метрики публикации версий
- Интеграция с Temporal (в будущем — для сложных workflow)

---

## Способы запуска

### 1. Локальная разработка

```bash
# 1. Установка зависимостей
pip install -r requirements.txt

# 2. Запуск в режиме разработки
just dev
```

### 2. Через Docker Compose (рекомендуется)

```bash
# Запуск всех сервисов (включая Redpanda)
just up

# Просмотр логов
just logs

# Проверка здоровья
just health
```

### 3. Через Kubernetes

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/hpa.yaml
```

### 4. Ручная проверка публикации модели

```bash
just publish-test-model
```

---

## Тестирование

### Доступные команды

```bash
just test                    # Все тесты
just test-unit               # Только unit-тесты
just test-integration        # Интеграционные тесты
just test-propagation        # Ключевой тест распространения версии модели
```

### Ключевой тест

Тест `test_model_propagation.py` проверяет:

- Корректность создания `ModelVersion`
- Сохранение в Model Registry
- Публикацию события `inference.router.config.updated`
- Время распространения конфигурации (**propagation latency**)

**Целевые SOTA-показатели**:
- Publication duration: < 1500 мс
- Propagation latency: < 2500 мс
- Успешность публикации: 100%

---

## Отслеживаемые метрики (SOTA 2026)

### Основные показатели ключевого взаимодействия

| Метрика                                | Целевое значение     | Описание |
|----------------------------------------|----------------------|--------|
| `model.version.publication.duration`   | p95 < 1500 мс        | Время публикации версии модели |
| `model.registry.save.duration`         | p95 < 3000 мс        | Время сохранения в registry |
| `kafka.produce.duration`               | p95 < 300 мс         | Время отправки события в Kafka |
| `model.propagation.latency`            | p95 < 2500 мс        | Общее время от публикации до применения в `rust-inference-service` |
| `model.version.consistency.rate`       | ≥ 99.99%             | Процент запросов с корректной версией модели |
| `dynamic.model.load.time`              | p95 < 2500 мс        | Время горячей подгрузки модели |

Все метрики отправляются через **OpenTelemetry** и доступны в Grafana / Jaeger.

---

## Ключевые эндпоинты

| Метод | Путь                            | Описание |
|-------|----------------------------------|--------|
| POST  | `/api/v1/models/publish`        | Опубликовать новую версию модели |
| GET   | `/health`                       | Health check |
| GET   | `/ready`                        | Readiness probe |

---

## Логирование

Сервис использует **structlog** с структурированным выводом.  
Основные уровни логов:

- `info` — важные бизнес-события (публикация версии, успешное сохранение)
- `debug` — детальная информация о преобразованиях
- `error` — ошибки с полным стек-трейсом

---

## Зависимости

- **Redpanda** (Kafka) — событийная шина
- **Model Registry Service** — хранилище артефактов моделей
- **OpenTelemetry Collector** — сбор метрик и трассировок

---

## Рекомендации по разработке

1. Всегда запускайте `just test-propagation` после изменений в ключевом пути.
2. Следите за метрикой `model.propagation.latency` — это один из важнейших показателей качества сервиса.
3. При добавлении новых полей в `ModelVersion` обязательно обновляйте тест `test_model_version_entity.py`.

---

## Следующие шаги

- Подключение Temporal Workflows для сложных процессов rollout
- Добавление gRPC-интерфейса для общения с `rust-inference-service`
- Реализация автоматического отката версий при деградации качества

---

