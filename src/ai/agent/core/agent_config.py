import threading
from typing import Any, Dict, Optional

from src.utils.env import (
    BEDROCK_GUARD_LAST_TURN_ONLY,
    BEDROCK_GUARDRAIL_ID,
    BEDROCK_GUARDRAIL_TRACE,
    BEDROCK_GUARDRAIL_VERSION,
    BEDROCK_KB_ID,
    BEDROCK_MAX_TOKENS,
    BEDROCK_MIN_SCORE_CONFIDENCE,
    BEDROCK_MODEL,
    BEDROCK_REGION,
    BEDROCK_RETRIEVAL_RESULTS,
    BEDROCK_TEMPERATURE,
)


class AgentConfig:
    """Thread-safe singleton configuration for AI agents."""

    _instance: Optional["AgentConfig"] = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls) -> "AgentConfig":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not AgentConfig._initialized:
            with AgentConfig._lock:
                if not AgentConfig._initialized:
                    self._load_config()
                    AgentConfig._initialized = True

    def _load_config(self) -> None:
        """Load configuration from environment variables."""
        self.region_name = BEDROCK_REGION
        self.model_name = BEDROCK_MODEL
        self.temperature = BEDROCK_TEMPERATURE
        self.max_tokens = BEDROCK_MAX_TOKENS

        # Guardrail configuration
        self.guardrail_id = BEDROCK_GUARDRAIL_ID
        self.guardrail_version = BEDROCK_GUARDRAIL_VERSION
        self.guardrail_trace = BEDROCK_GUARDRAIL_TRACE
        self.guard_last_turn_only = BEDROCK_GUARD_LAST_TURN_ONLY

        # Knowledge base and retrieval configuration
        self.knowledge_base_id = BEDROCK_KB_ID
        self.retrieval_config: Dict[str, Any] = {
            "vectorSearchConfiguration": {"numberOfResults": BEDROCK_RETRIEVAL_RESULTS}
        }
        self.min_score_confidence = BEDROCK_MIN_SCORE_CONFIDENCE

    def reload_config(self) -> None:
        """Reload configuration from environment variables."""
        with AgentConfig._lock:
            self._load_config()

    def __repr__(self) -> str:
        return (
            f"AgentConfig(model={self.model_name}, "
            f"region={self.region_name}, "
            f"kb_id={self.knowledge_base_id}, "
            f"temperature={self.temperature}, "
            f"max_tokens={self.max_tokens})"
        )


# Create a module-level singleton instance for easy importing
agent_config = AgentConfig()
