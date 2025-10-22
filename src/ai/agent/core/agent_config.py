import os
import threading
from typing import Any, Dict, Optional


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
        self.region_name = os.getenv("BEDROCK_REGION", "us-east-2")
        self.model_name = os.getenv(
            "BEDROCK_MODEL", "us.anthropic.claude-3-5-haiku-20241022-v1:0"
        )
        self.temperature = float(os.getenv("BEDROCK_TEMPERATURE", "0"))
        self.max_tokens = int(os.getenv("BEDROCK_MAX_TOKENS", "4000"))

        # Guardrail configuration
        self.guardrail_id = os.getenv("BEDROCK_GUARDRAIL_ID")
        self.guardrail_version = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
        self.guardrail_trace = os.getenv("BEDROCK_GUARDRAIL_TRACE", "enabled")
        self.guard_last_turn_only = (
            os.getenv("BEDROCK_GUARD_LAST_TURN_ONLY", "true").lower() == "true"
        )

        # Knowledge base and retrieval configuration
        self.knowledge_base_id = os.getenv("BEDROCK_KB_ID")
        retrieval_results = int(os.getenv("BEDROCK_RETRIEVAL_RESULTS", "5"))
        self.retrieval_config: Dict[str, Any] = {
            "vectorSearchConfiguration": {"numberOfResults": retrieval_results}
        }
        self.min_score_confidence = float(
            os.getenv("BEDROCK_MIN_SCORE_CONFIDENCE", "0.0")
        )

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
