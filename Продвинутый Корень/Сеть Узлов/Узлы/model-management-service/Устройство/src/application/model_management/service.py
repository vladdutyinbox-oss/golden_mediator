# src/application/model_management/service.py
"""
МОДУЛЬ: ModelManagementService
Ключевой файл, отвечающий за публикацию новой версии модели и запуск цепочки 
распространения конфигурации до rust-inference-service.

Это центральная точка ключевого взаимодействия.
"""

import structlog
from datetime import datetime
from domain.model.entity import ModelVersion
from infrastructure.kafka.producer import KafkaProducer
from infrastructure.registry.client import ModelRegistryClient

logger = structlog.get_logger(__name__)

class ModelManagementService:
    """
    Сервис управления моделями.
    Отвечает за сохранение версии модели и уведомление всей системы 
    (в первую очередь rust-inference-service) о появлении новой версии.
    """

    def __init__(self, registry_client: ModelRegistryClient, kafka_producer: KafkaProducer):
        self.registry = registry_client
        self.kafka = kafka_producer

    async def publish_new_model_version(self, version_data: dict):
        """
        Основной метод публикации новой версии модели.
        
        Преобразования и этапы:
        1. dict → ModelVersion (валидация и типизация)
        2. Сохранение в Model Registry
        3. Формирование события для Kafka
        4. Публикация события "inference.router.config.updated"
        5. Логирование метрик для SOTA-мониторинга
        """
        start_time = datetime.utcnow()
        version_id = version_data.get("id")

        logger.info("Starting model version publication", 
                   version_id=version_id,
                   model_name=version_data.get("name"))

        try:
            # === Преобразование 1: dict → доменная сущность ModelVersion ===
            # Здесь происходит валидация данных, преобразование типов и 
            # приведение к строгой доменной модели
            version: ModelVersion = ModelVersion.from_dict(version_data)
            
            logger.debug("ModelVersion entity created", 
                        version_id=version.id,
                        storage_path=version.storage_path)

            # === Преобразование 2: Сохранение в Model Registry ===
            # Отправляем артефакт модели в централизованное хранилище
            await self.registry.save(version)
            
            logger.info("Model version successfully saved to registry", 
                       version_id=version.id)

            # === Преобразование 3: Подготовка события для Kafka ===
            # Формируем событие, которое будет прочитано inference-router'ом 
            # и в конечном итоге дойдёт до rust-inference-service
            event_payload = {
                "event_type": "model_version_published",
                "model_version_id": version.id,
                "model_name": version.name,
                "storage_path": version.storage_path,
                "inference_params": version.inference_params,
                "target_personas": version.persona_bindings,
                "timestamp": datetime.utcnow().isoformat(),
                "propagation_required": True,
                "source_service": "model-management-service"
            }

            logger.debug("Kafka event payload prepared", 
                        event_type=event_payload["event_type"],
                        topic="inference.router.config.updated")

            # === Преобразование 4: Публикация события ===
            # Отправляем событие в event-bus. Это ключевое взаимодействие.
            await self.kafka.publish(
                topic="inference.router.config.updated",
                key=version.id,
                value=event_payload
            )

            # === Преобразование 5: Расчёт и логирование метрик ===
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info("Model version publication completed successfully",
                       version_id=version.id,
                       duration_ms=round(duration_ms, 2),
                       event_published=True)

            # SOTA метрика: время публикации версии
            self._record_publication_metric(version.id, duration_ms)

            return version

        except Exception as e:
            logger.error("Failed to publish model version",
                        version_id=version_id,
                        error=str(e),
                        exc_info=True)
            raise

    def _record_publication_metric(self, version_id: str, duration_ms: float):
        """Запись метрики для observability (будет отправлено в OpenTelemetry)"""
        logger.info("Model publication metric recorded",
                   metric_name="model.version.publication.duration",
                   version_id=version_id,
                   duration_ms=round(duration_ms, 2),
                   target_max_ms=1500)  # SOTA цель