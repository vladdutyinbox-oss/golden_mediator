# src/domain/model/entity.py
"""
ДОМЕННАЯ СУЩНОСТЬ: ModelVersion

Это核心 (ядро) доменной модели.
Здесь определяется структура данных версии модели и правила её валидации.

Все преобразования в model-management-service начинаются именно с этого файла:
dict (из API) → ModelVersion (строго типизированная сущность)
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

class ModelVersion(BaseModel):
    """
    Доменная сущность версии модели.
    
    Используется как каноническая форма данных о модели во всём сервисе.
    Обеспечивает строгую типизацию и валидацию перед публикацией события.
    """

    id: str = Field(..., description="Уникальный идентификатор версии модели")
    name: str = Field(..., description="Человекочитаемое имя модели (например: qwen2.5-32b-instruct-v4)")
    storage_path: str = Field(..., description="Путь к весам модели в хранилище (S3/MinIO)")
    
    inference_params: Dict = Field(
        default_factory=dict,
        description="Параметры инференса: temperature, top_p, max_tokens и т.д."
    )
    
    persona_bindings: List[str] = Field(
        default_factory=list,
        description="Список ID личностей, к которым привязана эта версия модели"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="published", pattern="^(published|deprecated|archived)$")
    
    # Метаданные для отладки и observability
    source_service: str = Field(default="model-management-service")
    published_by: Optional[str] = Field(default=None, description="Кто опубликовал версию")

    @field_validator("id")
    @classmethod
    def validate_version_id(cls, v: str) -> str:
        if not v or len(v.strip()) < 3:
            raise ValueError("Model version id must be at least 3 characters long")
        return v.strip()

    @field_validator("storage_path")
    @classmethod
    def validate_storage_path(cls, v: str) -> str:
        if not v.startswith(("s3://", "gs://", "file://", "http")):
            logger.warning("Unusual storage path format", storage_path=v)
        return v

    @field_validator("inference_params")
    @classmethod
    def validate_inference_params(cls, v: Dict) -> Dict:
        """Проверяем наличие критически важных параметров инференса"""
        required_keys = {"temperature", "top_p"}
        missing = required_keys - v.keys()
        if missing:
            logger.warning("Missing recommended inference parameters", missing_keys=missing)
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        extra = "forbid"   # Запрещаем лишние поля для безопасности

    @classmethod
    def from_dict(cls, data: dict) -> "ModelVersion":
        """
        Фабричный метод преобразования сырого dict (из API) в доменную сущность.
        
        Это критическое преобразование в ключевом взаимодействии:
        dict → ModelVersion (с валидацией)
        """
        try:
            instance = cls(**data)
            logger.debug("Successfully converted dict to ModelVersion entity",
                        version_id=instance.id,
                        name=instance.name)
            return instance
        except Exception as e:
            logger.error("Failed to create ModelVersion from dict", 
                        error=str(e),
                        input_data_keys=list(data.keys()))
            raise

    def to_event_payload(self) -> dict:
        """
        Преобразует сущность в формат события для Kafka.
        Это событие будет прочитано inference-router → rust-inference-service.
        """
        payload = {
            "event_type": "model_version_published",
            "model_version_id": self.id,
            "model_name": self.name,
            "storage_path": self.storage_path,
            "inference_params": self.inference_params,
            "target_personas": self.persona_bindings,
            "timestamp": self.created_at.isoformat(),
            "status": self.status,
            "source_service": self.source_service
        }
        logger.debug("ModelVersion converted to Kafka event payload", 
                    version_id=self.id,
                    event_size=len(str(payload)))
        return payload