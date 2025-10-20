import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env file
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")


def get_env_var(key: str, default=None, required=False):
    """Get environment variable with optional default and required check."""
    value = os.getenv(key, default)
    if required and value is None:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


def get_for_language(env_var: str, language: Optional[str]):
    """Get corresponding environment variable value for the specified language."""
    languages = LANGUAGE.split(SPLIT_CHAR)
    split_vars = env_var.split(SPLIT_CHAR)

    use_value = split_vars[0]
    if (
        language is not None
        and len(split_vars) >= len(languages)
        and language in languages
    ):
        # If a specific language was passed to this function, we want to use that language's configuration for the var.
        use_value = split_vars[languages.index(language)]

    return use_value


SPLIT_CHAR = "|"

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

# TTS configuration
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "ElevenLabs")
TTS_VOICE = os.getenv("TTS_VOICE", "lxYfHSkYm1EzQzGhdbfc")
FALLBACK_TTS = os.getenv("FALLBACK_TTS", "Google.en-US-Chirp3-HD-Aoede")

# STT configuration
TRANSCRIPTION_PROVIDER = os.getenv("TRANSCRIPTION_PROVIDER", "Deepgram")
SPEECH_MODEL = os.getenv("SPEECH_MODEL", "nova-3-general")

# Prompts
WELCOME_GREETING = os.getenv(
    "WELCOME_GREETING", "Hello! I'm your AI assistant. How can I help you today?"
)
WELCOME_ERROR_PROMPT = os.getenv(
    "WELCOME_ERROR_PROMPT",
    "I'm sorry, there was an error starting the conversation. Please try again later.",
)
ERROR_PROMPT = os.getenv(
    "ERROR_PROMPT",
    "I'm sorry, a problem occurred while handling your call. Please try your call again.",
)

# Idle configuration
IDLE_REMINDER = os.getenv(
    "IDLE_REMINDER", "I'm still here, let me know when you are ready to continue."
)
IDLE_TIMEOUT_PROMPT = os.getenv(
    "IDLE_TIMEOUT_PROMPT",
    "I'm sorry, I haven't heard you respond in a while. Please try your call again.",
)
IDLE_MAX_ATTEMPTS = int(os.getenv("IDLE_MAX_ATTEMPTS", 3))
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT", 20))

# Additional configuration
LANGUAGE = os.getenv("LANGUAGE", "en-US")
INITIAL_HINTS = os.getenv("INITIAL_HINTS", "")
DTMF_MAX_DIGITS = int(os.getenv("DTMF_MAX_DIGITS", 10))
DTMF_TIMEOUT = int(os.getenv("DTMF_TIMEOUT", 3))
ERROR_MAX_ATTEMPTS = int(os.getenv("ERROR_MAX_ATTEMPTS", 5))

# AWS Configuration
AWS_REGION = get_env_var("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = get_env_var("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = get_env_var("AWS_SECRET_ACCESS_KEY")
AWS_PROFILE = get_env_var("AWS_PROFILE", "default")
