import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")


def get_env_var(key: str, default=None, required=False):
    """Get environment variable with optional default and required check."""
    value = os.getenv(key, default)
    if required and value is None:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


# Application settings
ENVIRONMENT = get_env_var("ENVIRONMENT", "development")
PORT = int(os.getenv("PORT", 8000))
LOG_LEVEL = get_env_var("LOG_LEVEL", "INFO")

# External URL configuration (for ngrok, load balancers, etc.)
EXTERNAL_URL = get_env_var("EXTERNAL_URL")  # Optional: set to ngrok URL for development

# Twilio configuration
TWILIO_ACCOUNT_SID = get_env_var("TWILIO_ACCOUNT_SID", required=True)
TWILIO_AUTH_TOKEN = get_env_var("TWILIO_AUTH_TOKEN", required=True)
FORCE_VALIDATION = os.getenv("FORCE_VALIDATION", "false").lower() == "true"

# Twilio Conversational Intelligence
TWILIO_CONVERSATIONAL_INTELLIGENCE = get_env_var("TWILIO_CONVERSATIONAL_INTELLIGENCE")

# Idle configuration
IDLE_MAX_ATTEMPTS = int(os.getenv("IDLE_MAX_ATTEMPTS", 3))
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT", 20))

# Additional configuration
LANGUAGE = os.getenv("LANGUAGE", "en-US")
DTMF_MAX_DIGITS = int(os.getenv("DTMF_MAX_DIGITS", 10))
DTMF_TIMEOUT = int(os.getenv("DTMF_TIMEOUT", 3))
ERROR_MAX_ATTEMPTS = int(os.getenv("ERROR_MAX_ATTEMPTS", 5))

# AWS Configuration
AWS_REGION = get_env_var("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = get_env_var("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = get_env_var("AWS_SECRET_ACCESS_KEY")
AWS_PROFILE = get_env_var("AWS_PROFILE", "default")

# AWS Bedrock Configuration
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-east-2")
BEDROCK_MODEL = os.getenv(
    "BEDROCK_MODEL", "us.anthropic.claude-3-5-haiku-20241022-v1:0"
)
BEDROCK_TEMPERATURE = float(os.getenv("BEDROCK_TEMPERATURE", "0"))
BEDROCK_MAX_TOKENS = int(os.getenv("BEDROCK_MAX_TOKENS", "4000"))

# AWS Bedrock Guardrail Configuration
BEDROCK_GUARDRAIL_ID = os.getenv("BEDROCK_GUARDRAIL_ID")
BEDROCK_GUARDRAIL_VERSION = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
BEDROCK_GUARDRAIL_TRACE = os.getenv("BEDROCK_GUARDRAIL_TRACE", "enabled")
BEDROCK_GUARD_LAST_TURN_ONLY = (
    os.getenv("BEDROCK_GUARD_LAST_TURN_ONLY", "true").lower() == "true"
)

# AWS Bedrock Knowledge Base Configuration
BEDROCK_KB_ID = os.getenv("BEDROCK_KB_ID")
BEDROCK_RETRIEVAL_RESULTS = int(os.getenv("BEDROCK_RETRIEVAL_RESULTS", "5"))
BEDROCK_MIN_SCORE_CONFIDENCE = float(os.getenv("BEDROCK_MIN_SCORE_CONFIDENCE", "0.0"))
