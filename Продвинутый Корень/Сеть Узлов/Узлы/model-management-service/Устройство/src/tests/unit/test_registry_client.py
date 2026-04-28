# src/tests/unit/test_registry_client.py
import pytest
import httpx
from unittest.mock import patch, AsyncMock
from src.infrastructure.registry.client import ModelRegistryClient
from src.domain.model.entity import ModelVersion

@pytest.mark.asyncio
async def test_save_model_version_success():
    """Тест успешного сохранения версии модели в registry"""
    version = ModelVersion(
        id="test-v-789",
        name="Test Model v2",
        storage_path="s3://models/test/v789",
        inference_params={"temperature": 0.7},
        persona_bindings=["persona:default"]
    )

    mock_response = AsyncMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "test-v-789", "status": "stored"}

    with patch('httpx.AsyncClient.post', return_value=mock_response):
        client = ModelRegistryClient(base_url="http://test-registry:8003")
        
        result = await client.save(version)

        assert result["id"] == "test-v-789"
        assert result["status"] == "stored"


@pytest.mark.asyncio
async def test_registry_client_logs_and_metrics():
    """Тест корректного логирования и записи метрик"""
    version = ModelVersion(
        id="test-v-001",
        name="Logging Test Model",
        storage_path="s3://test/path",
        inference_params={},
        persona_bindings=[]
    )

    mock_response = AsyncMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "test-v-001"}

    with patch('httpx.AsyncClient.post', return_value=mock_response):
        with patch('structlog.get_logger') as mock_logger:
            logger_instance = mock_logger.return_value
            logger_instance.info = AsyncMock()

            client = ModelRegistryClient("http://fake-registry")
            await client.save(version)

            # Проверяем наличие важных логов
            logger_instance.info.assert_any_call(
                "Saving model version to registry",
                version_id="test-v-001",
                model_name="Logging Test Model"
            )

            logger_instance.info.assert_any_call(
                "Model version successfully saved to registry",
                version_id="test-v-001"
            )