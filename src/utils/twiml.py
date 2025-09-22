from twilio.twiml.voice_response import VoiceResponse
from src.utils.env import TTS_PROVIDER, TTS_VOICE, WELCOME_GREETING
from src.utils.logger import get_logger

logger = get_logger(__name__)

def create_initial_twiml(action_url: str, host: str, welcome_greeting: str, params: dict):
    # Create TwiML response using Twilio SDK
    response = VoiceResponse()
    
    # Build WebSocket URL dynamically based on request
    websocket_url = f"wss://{host}/ws/"
    
    # Connect to ConversationRelay
    connect_action_url = action_url or f"https://{host}/call/action"
    connect = response.connect(action=connect_action_url)
    
    conversation_relay = connect.conversation_relay(
        url=websocket_url,
        dtmf_detection=True,
        interruptible="any",
        welcome_greeting=welcome_greeting,
        tts_provider=TTS_PROVIDER,
        voice=TTS_VOICE
    )
    
    for param, value in params.items():
        conversation_relay.parameter(name=param, value=value)
    
    return str(response)

def create_fallback_twiml():
    fallback_response = VoiceResponse()
    fallback_response.say("I'm sorry, there was an error starting the conversation. Please try again later.")
    fallback_response.hangup()
    return str(fallback_response)