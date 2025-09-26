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

# TTS Configuration
TTS_PROVIDER = get_env_var("TTS_PROVIDER", "elevenlabs")
TTS_VOICE = get_env_var("TTS_VOICE", "lxYfHSkYm1EzQzGhdbfc")
TTS_LANGUAGE = get_env_var("TTS_LANGUAGE", "en-US")

# Additional configuration
WELCOME_GREETING = os.getenv(
    "WELCOME_GREETING", "Hello! I'm your AI assistant. How can I help you today?"
)
DTMF_MAX_DIGITS = int(os.getenv("DTMF_MAX_DIGITS", 10))
DTMF_TIMEOUT = int(os.getenv("DTMF_TIMEOUT", 3))
IDLE_REMINDER = os.getenv(
    "IDLE_REMINDER", "I'm still here, let me know when you are ready to continue."
)
IDLE_MAX_ATTEMPTS = int(os.getenv("IDLE_MAX_ATTEMPTS", 3))
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT", 20))

# AWS Configuration
AWS_REGION = get_env_var("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = get_env_var("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = get_env_var("AWS_SECRET_ACCESS_KEY")
AWS_PROFILE = get_env_var("AWS_PROFILE", "default")
