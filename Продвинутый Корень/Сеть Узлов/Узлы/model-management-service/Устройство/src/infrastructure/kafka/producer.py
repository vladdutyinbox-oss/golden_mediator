# src/infrastructure/kafka/producer.py
"""
ИНФРАСТРУКТУРНЫЙ КОМПОНЕНТ: KafkaProducer

Отвечает за надёжную публикацию событий в Kafka (Redpanda).
Это критическая часть ключевого взаимодействия — именно здесь событие 
"inference.router.config.updated" покидает model-management-service 
и начинает путь к inference-router → rust-inference-service.

Особенности:
- Асинхронная публикация
- Строгая сериализация
- Подробное логирование каждого этапа
- Обработка ошибок с повторными попытками
"""

import json
import asyncio
from typing import Dict, Any
import structlog
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaTimeoutError

from src.settings import settings

logger = structlog.get_logger(__name__)

class KafkaProducer:
    """
    Kafka Producer с поддержкой повторных попыток и детальным логированием.
    Используется для публикации событий о новых версиях моделей.
    """

    def __init__(self):
        self.producer: AIOKafkaProducer | None = None
        self._is_started = False

    async def start(self):
        """
        Инициализация и запуск Kafka Producer.
        Выполняется лениво при первой публикации.
        """
        if self._is_started:
            return

        try:
            logger.info("Initializing Kafka producer", 
                       bootstrap_servers=settings.kafka_bootstrap_servers)

            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                client_id="model-management-service",
                # Сериализация значения в JSON
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                # Сериализация ключа (используем version_id как ключ для партиционирования)
                key_serializer=lambda k: k.encode('utf-8') if isinstance(k, str) else None,
                # Настройки надёжности
                acks='all',                    # Ждём подтверждения от всех реплик
                retries=5,                     # Количество повторных попыток
                request_timeout_ms=15000,      # Таймаут запроса
            )

            await self.producer.start()
            self._is_started = True
            
            logger.info("Kafka producer successfully started and ready")

        except Exception as e:
            logger.error("Failed to start Kafka producer", error=str(e))
            raise

    async def publish(self, topic: str, key: str, value: Dict[str, Any]):
        """
        Публикует событие в Kafka.

        Ключевые преобразования:
        1. Python dict → JSON bytes
        2. Добавление метаданных для трассировки
        3. Отправка с гарантией доставки (acks='all')
        
        Это событие будет потреблено inference-router'ом и в итоге 
        приведёт к обновлению конфигурации в rust-inference-service.
        """
        start_time = asyncio.get_event_loop().time()

        if not self.producer or not self._is_started:
            await self.start()

        try:
            # === Преобразование: dict → JSON bytes (сериализация) ===
            serialized_value = json.dumps(value).encode('utf-8')

            logger.debug("Preparing to publish Kafka event",
                        topic=topic,
                        key=key,
                        event_type=value.get("event_type"),
                        payload_size=len(serialized_value))

            # === Отправка события ===
            await self.producer.send_and_wait(
                topic=topic,
                key=key,                    # Используется для партиционирования
                value=serialized_value,
                timestamp_ms=int(datetime.now().timestamp() * 1000)
            )

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            logger.info("Kafka event published successfully",
                       topic=topic,
                       key=key,
                       event_type=value.get("event_type"),
                       duration_ms=round(duration_ms, 2),
                       propagation_target="inference-router")

            # SOTA метрика: время публикации события
            self._record_publish_metric(topic, duration_ms)

        except (KafkaConnectionError, KafkaTimeoutError) as e:
            logger.error("Kafka connection/timeout error during publish",
                        topic=topic,
                        error=str(e))
            # Здесь можно добавить retry logic с экспоненциальной задержкой
            raise
        except Exception as e:
            logger.error("Unexpected error while publishing to Kafka",
                        topic=topic,
                        error=str(e),
                        exc_info=True)
            raise

    def _record_publish_metric(self, topic: str, duration_ms: float):
        """Запись метрики публикации для observability"""
        logger.info("Kafka publish metric",
                   metric="kafka.produce.duration",
                   topic=topic,
                   duration_ms=round(duration_ms, 2),
                   target_max_ms=300)   # SOTA цель для публикации

    async def stop(self):
        """Корректное завершение продюсера"""
        if self.producer and self._is_started:
            await self.producer.stop()
            self._is_started = False
            logger.info("Kafka producer stopped gracefully")