# src/tests/unit/test_kafka_producer.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from src.infrastructure.kafka.producer import KafkaProducer

@pytest.mark.asyncio
async def test_kafka_publish_success():
    """Тест успешной публикации события"""
    producer = KafkaProducer()
    
    # Мокаем реальный продюсер
    with patch.object(producer, 'producer', AsyncMock()) as mock_producer:
        mock_producer.send_and_wait = AsyncMock()
        
        test_event = {
            "event_type": "model_version_published",
            "model_version_id": "test-v-123",
            "timestamp": "2026-04-28T10:00:00Z"
        }

        await producer.publish(
            topic="inference.router.config.updated",
            key="test-v-123",
            value=test_event
        )

        # Проверяем, что send_and_wait был вызван
        mock_producer.send_and_wait.assert_called_once()

        # Проверяем правильность параметров
        call_args = mock_producer.send_and_wait.call_args
        assert call_args.kwargs["topic"] == "inference.router.config.updated"
        assert call_args.kwargs["key"] == "test-v-123"


@pytest.mark.asyncio
async def test_kafka_publish_logs_properly():
    """Тест корректного логирования при публикации"""
    producer = KafkaProducer()
    
    with patch('structlog.get_logger') as mock_logger:
        logger_instance = mock_logger.return_value
        logger_instance.info = AsyncMock()
        
        test_event = {"event_type": "test_event"}
        
        await producer.publish("test-topic", "test-key", test_event)
        
        # Проверяем, что были важные логи
        logger_instance.info.assert_any_call(
            "Kafka event published successfully",
            topic="test-topic",
            key="test-key",
            event_type="test_event",
            # ... остальные поля
        )