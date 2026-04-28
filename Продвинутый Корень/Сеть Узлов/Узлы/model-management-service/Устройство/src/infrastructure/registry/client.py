# src/infrastructure/registry/client.py
"""
ИНФРАСТРУКТУРНЫЙ КЛИЕНТ: ModelRegistryClient

Отвечает за сохранение метаданных версии модели в централизованном хранилище 
(model-registry-service).

Это важный шаг в ключевом взаимодействии:
ModelVersion → HTTP POST в Model Registry → подтверждение сохранения → 
далее публикация события в Kafka.

Ключевые ответственности:
- Надёжное сохранение артефакта модели
- Валидация ответа от registry
- Детальное логирование и измерение времени выполнения
- Обработка ошибок с понятными сообщениями
"""

import httpx
import structlog
from datetime import datetime
from domain.model.entity import ModelVersion

logger = structlog.get_logger(__name__)

class ModelRegistryClient:
    """
    Клиент для общения с Model Registry Service.
    Использует HTTP (можно заменить на gRPC в будущем для большей производительности).
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        # Создаём клиент с таймаутом и повторными попытками
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            follow_redirects=True
        )
        logger.info("ModelRegistryClient initialized", base_url=self.base_url)

    async def save(self, version: ModelVersion) -> dict:
        """
        Сохраняет версию модели в Model Registry.

        Преобразования:
        1. ModelVersion (доменная сущность) → JSON dict
        2. Отправка через HTTP POST
        3. Обработка ответа и проверка статуса

        Это критический шаг перед публикацией события в Kafka.
        Если сохранение не удалось — событие публиковать нельзя.
        """
        start_time = datetime.utcnow()

        url = f"{self.base_url}/api/v1/models"

        logger.info("Saving model version to registry", 
                   version_id=version.id,
                   model_name=version.name,
                   url=url)

        try:
            # === Преобразование: ModelVersion → JSON для HTTP ===
            payload = version.model_dump(mode='json')

            response = await self.client.post(
                url=url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            response.raise_for_status()  # Выбросит исключение при 4xx/5xx

            result = response.json()

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info("Model version successfully saved to registry",
                       version_id=version.id,
                       registry_response_status=response.status_code,
                       duration_ms=round(duration_ms, 2),
                       registry_id=result.get("id"))

            # SOTA метрика: время сохранения в registry
            self._record_registry_metric(version.id, duration_ms)

            return result

        except httpx.HTTPStatusError as e:
            logger.error("HTTP error while saving model to registry",
                        version_id=version.id,
                        status_code=e.response.status_code,
                        response_text=e.response.text[:500])
            raise
        except httpx.RequestError as e:
            logger.error("Network error while connecting to model registry",
                        version_id=version.id,
                        error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error during model registry save",
                        version_id=version.id,
                        error=str(e),
                        exc_info=True)
            raise

    def _record_registry_metric(self, version_id: str, duration_ms: float):
        """Запись метрики сохранения в registry"""
        logger.info("Model registry save metric",
                   metric="model.registry.save.duration",
                   version_id=version_id,
                   duration_ms=round(duration_ms, 2),
                   target_max_ms=3000)   # SOTA цель — до 3 секунд

    async def close(self):
        """Закрытие HTTP клиента"""
        await self.client.aclose()
        logger.info("ModelRegistryClient closed")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()