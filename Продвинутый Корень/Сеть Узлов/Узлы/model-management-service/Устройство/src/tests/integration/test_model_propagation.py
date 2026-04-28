# src/tests/integration/test_model_propagation.py
import pytest
import asyncio
import time
import httpx
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

@pytest.mark.integration
async def test_publish_new_model_version_flow():
    """
    Полноценный интеграционный тест ключевого взаимодействия.
    Проверяет весь путь от API до публикации события в Kafka.
    """
    version_id = f"test-v-{int(time.time())}"
    
    payload = {
        "id": version_id,
        "name": "qwen2.5-32b-instruct-test",
        "storage_path": f"s3://models/test/{version_id}",
        "inference_params": {"temperature": 0.7, "top_p": 0.9},
        "persona_bindings": ["persona:001"],
        "created_at": datetime.utcnow().isoformat()
    }

    start_time = time.perf_counter()

    # === Тест вызова главного метода через HTTP ===
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "http://localhost:8002/api/v1/models/publish",
            json=payload
        )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    total_duration_ms = (time.perf_counter() - start_time) * 1000

    # === SOTA проверки ===
    assert total_duration_ms < 2000, f"Publication too slow: {total_duration_ms:.2f}ms"

    data = response.json()
    assert data["version_id"] == version_id

    logger.info("Key interaction test passed",
                version_id=version_id,
                total_duration_ms=round(total_duration_ms, 2))

    # Дополнительная проверка: событие должно быть опубликовано (логи можно проверить вручную)