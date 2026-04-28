# src/tests/integration/test_main_endpoints.py
import pytest
import httpx
import asyncio
from datetime import datetime

@pytest.mark.integration
async def test_publish_model_version_endpoint():
    """Тест основного эндпоинта публикации версии модели"""
    payload = {
        "id": "endpoint-test-v1",
        "name": "Endpoint Test Model",
        "storage_path": "s3://models/test/endpoint-v1",
        "inference_params": {"temperature": 0.8, "top_p": 0.9},
        "persona_bindings": ["persona:test"]
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "http://localhost:8002/api/v1/models/publish",
            json=payload
        )

    assert response.status_code == 201

    data = response.json()
    assert data["status"] == "success"
    assert data["version_id"] == "endpoint-test-v1"
    assert "duration_ms" in data
    assert data["duration_ms"] > 0


@pytest.mark.integration
async def test_health_and_readiness():
    """Тест health и readiness проб"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        health_resp = await client.get("http://localhost:8002/health")
        ready_resp = await client.get("http://localhost:8002/ready")

        assert health_resp.status_code == 200
        assert ready_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"
        assert ready_resp.json()["status"] == "ready"