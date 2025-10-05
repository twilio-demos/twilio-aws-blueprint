import os
import threading
from typing import Any, Dict, Optional


class AgentConfig:
    """Singleton configuration class for AI agents."""

    _instance: Optional["AgentConfig"] = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls) -> "AgentConfig":
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super(AgentConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Only initialize once
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._load_config()
                    AgentConfig._initialized = True

    def _load_config(self) -> None:
        """Load configuration from environment variables."""
        self.knowledge_base_id = os.getenv("BEDROCK_KB_ID", "NCWLZCBIRG")
        self.region_name = os.getenv("BEDROCK_REGION", "us-east-1")
        self.retrieval_config: Dict[str, Any] = {
            "vectorSearchConfiguration": {"numberOfResults": 5}
        }
        self.min_score_confidence = 0.0
        self.model_name = os.getenv(
            "BEDROCK_MODEL", "us.anthropic.claude-3-5-haiku-20241022-v1:0"
        )
        self.guardrail_id = os.getenv("BEDROCK_GUARDRAIL_ID", None)
        self.guardrail_version = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")

    def reload_config(self) -> None:
        """Reload configuration from environment variables."""
        with self._lock:
            self._load_config()

    def __repr__(self) -> str:
        return (
            f"AgentConfig(model={self.model_name}, "
            f"region={self.region_name}, "
            f"kb_id={self.knowledge_base_id})"
        )


# Create a module-level singleton instance for easy importing
agent_config = AgentConfig()
