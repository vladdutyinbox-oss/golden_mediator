# src/tests/unit/test_model_version_entity.py
import pytest
from src.domain.model.entity import ModelVersion
from datetime import datetime

def test_model_version_creation_from_dict():
    """Тест преобразования dict → ModelVersion"""
    data = {
        "id": "qwen2.5-32b-v42",
        "name": "Qwen2.5 32B Instruct v4.2",
        "storage_path": "s3://models/qwen2.5-32b/v42",
        "inference_params": {
            "temperature": 0.75,
            "top_p": 0.92,
            "max_tokens": 8192
        },
        "persona_bindings": ["persona:default", "persona:creative"],
        "published_by": "admin"
    }

    version = ModelVersion.from_dict(data)

    assert version.id == "qwen2.5-32b-v42"
    assert version.name == "Qwen2.5 32B Instruct v4.2"
    assert version.storage_path.startswith("s3://")
    assert version.inference_params["temperature"] == 0.75
    assert len(version.persona_bindings) == 2
    assert version.status == "published"


def test_model_version_to_event_payload():
    """Тест преобразования сущности в событие для Kafka"""
    version = ModelVersion(
        id="test-v-001",
        name="Test Model",
        storage_path="s3://test/model",
        inference_params={"temperature": 0.7},
        persona_bindings=["p1"]
    )

    payload = version.to_event_payload()

    assert payload["event_type"] == "model_version_published"
    assert payload["model_version_id"] == "test-v-001"
    assert payload["target_personas"] == ["p1"]
    assert "timestamp" in payload
    assert payload["source_service"] == "model-management-service"


def test_invalid_model_version_raises_error():
    """Тест валидации: некорректные данные должны вызывать ошибку"""
    invalid_data = {
        "id": "",                    # слишком короткий id
        "name": "Invalid Model",
        "storage_path": "invalid-path"  # неправильный формат
    }

    with pytest.raises(ValueError):
        ModelVersion.from_dict(invalid_data)