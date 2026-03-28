from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_files() -> tuple[Path, ...]:
    """
    Raíz del repo: src/asistente/config.py -> parents[2].
    Así el .env se carga aunque uvicorn se ejecute desde otro cwd.
    """
    root = Path(__file__).resolve().parents[2]
    return (root / ".env", Path(".env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    default_city: str = Field(default="Madrid", validation_alias="DEFAULT_CITY")

    api_host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(default=8000, validation_alias="API_PORT")

    # Memoria de sesión (en RAM; se pierde al reiniciar el servidor)
    session_ttl_seconds: int = Field(default=2700, validation_alias="SESSION_TTL_SECONDS")
    session_max_turn_pairs: int = Field(default=12, validation_alias="SESSION_MAX_TURN_PAIRS")

    # Memoria larga (Chroma en disco)
    memory_dir: str = Field(default="./data/memory", validation_alias="MEMORY_DIR")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="EMBEDDING_MODEL",
    )
    rag_top_k: int = Field(default=8, validation_alias="RAG_TOP_K")

    # MQTT (domótica); si falta el host, no se publica
    mqtt_broker_host: str | None = Field(default=None, validation_alias="MQTT_BROKER_HOST")
    mqtt_broker_port: int = Field(default=1883, validation_alias="MQTT_BROKER_PORT")
    mqtt_topic_prefix: str = Field(default="casa", validation_alias="MQTT_TOPIC_PREFIX")
    mqtt_username: str | None = Field(default=None, validation_alias="MQTT_USERNAME")
    mqtt_password: str | None = Field(default=None, validation_alias="MQTT_PASSWORD")
    mqtt_client_id: str = Field(default="asistente-personal", validation_alias="MQTT_CLIENT_ID")
    # Coma: comedor,dormitorio,cocina,salon — vacío = cualquier zona (sin restricción)
    mqtt_home_zones: str = Field(default="", validation_alias="MQTT_HOME_ZONES")


@lru_cache
def get_settings() -> Settings:
    return Settings()
