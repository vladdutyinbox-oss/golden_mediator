# src/main.py
"""
ТОЧКА ВХОДА ПРИЛОЖЕНИЯ: main.py

Это главный файл model-management-service.
Здесь происходит:
1. Инициализация приложения FastAPI
2. Настройка lifespan (startup/shutdown)
3. Подключение всех зависимостей (KafkaProducer, ModelRegistryClient и т.д.)
4. Регистрация эндпоинтов
5. Запуск метрик и observability

Этот файл является "дирижёром" ключевого взаимодействия:
от HTTP-запроса из Model Studio до публикации события для rust-inference-service.
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import structlog
from datetime import datetime

from src.settings import settings
from src.application.model_management.service import ModelManagementService
from src.infrastructure.kafka.producer import KafkaProducer
from src.infrastructure.registry.client import ModelRegistryClient

logger = structlog.get_logger(__name__)

# Глобальные зависимости (будут инициализированы в lifespan)
model_service: ModelManagementService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan handler — управляет запуском и остановкой сервиса.
    
    Выполняемые действия при старте:
    - Инициализация Kafka Producer
    - Инициализация клиента Model Registry
    - Создание основного сервиса ModelManagementService
    
    Это критично для ключевого взаимодействия, так как все компоненты 
    должны быть готовы до приёма первого запроса на публикацию модели.
    """
    global model_service

    logger.info("Starting model-management-service", 
               env=settings.app_env,
               version="1.0.0")

    try:
        # Инициализация инфраструктурных компонентов
        kafka_producer = KafkaProducer()
        registry_client = ModelRegistryClient(base_url=settings.model_registry_url)

        # Создание основного сервисного слоя
        model_service = ModelManagementService(
            registry_client=registry_client,
            kafka_producer=kafka_producer
        )

        logger.info("All dependencies initialized successfully")

        yield  # Приложение работает

    except Exception as e:
        logger.error("Failed to initialize model-management-service", error=str(e))
        raise
    finally:
        # Корректное завершение
        logger.info("Shutting down model-management-service")
        if hasattr(registry_client, 'close'):
            await registry_client.close()
        if hasattr(kafka_producer, 'stop'):
            await kafka_producer.stop()


# Создаём FastAPI приложение
app = FastAPI(
    title="Model Management Service",
    description="Сервис управления версиями моделей и их распространения в inference слой",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.post("/api/v1/models/publish", status_code=201)
async def publish_model_version(payload: dict):
    """
    Основной эндпоинт для публикации новой версии модели.
    
    Это стартовая точка ключевого взаимодействия.
    Путь запроса:
    1. HTTP POST из Model Studio
    2. Валидация payload
    3. Вызов ModelManagementService.publish_new_model_version()
    4. Сохранение в registry + публикация события в Kafka
    """
    if not model_service:
        logger.error("ModelManagementService not initialized")
        raise HTTPException(status_code=503, detail="Service not ready")

    start_time = datetime.utcnow()

    try:
        logger.info("Received request to publish model version", 
                   version_id=payload.get("id"),
                   model_name=payload.get("name"))

        # Главный вызов — запускает всю цепочку ключевого взаимодействия
        version = await model_service.publish_new_model_version(payload)

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return {
            "status": "success",
            "message": "Model version published and event propagated",
            "version_id": version.id,
            "duration_ms": round(duration_ms, 2)
        }

    except Exception as e:
        logger.error("Failed to process publish request", 
                    version_id=payload.get("id"),
                    error=str(e),
                    exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """
    Health check эндпоинт для Kubernetes и мониторинга.
    """
    return {
        "status": "healthy",
        "service": "model-management-service",
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": ["kafka", "model-registry"]
    }


@app.get("/ready")
async def readiness_check():
    """
    Readiness probe — проверяет, готов ли сервис обрабатывать трафик.
    """
    if model_service is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.server_host if hasattr(settings, 'server_host') else "0.0.0.0",
        port=settings.server_port if hasattr(settings, 'server_port') else 8002,
        reload=settings.app_env == "development"
    )