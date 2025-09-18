import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / '.env')

NODE_ENV = os.getenv('NODE_ENV', 'development')
PORT = int(os.getenv('PORT', 3000))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'info')

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')

# ConversationRelay TTS Configuration
TTS_PROVIDER = os.getenv('TTS_PROVIDER', 'elevenlabs')
TTS_VOICE = os.getenv('TTS_VOICE', 'lxYfHSkYm1EzQzGhdbfc')
WELCOME_GREETING = os.getenv('WELCOME_GREETING', 'Hello! I\'m your AI assistant. How can I help you today?')

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
