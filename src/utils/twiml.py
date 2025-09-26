from twilio.twiml.voice_response import VoiceResponse

from src.utils.env import TTS_PROVIDER, TTS_VOICE
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_initial_twiml(
    action_url: str | None, host: str | None, welcome_greeting: str, params: dict
):
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
        voice=TTS_VOICE,
    )

    for param, value in params.items():
        conversation_relay.parameter(name=param, value=value)

    return str(response)


def create_say_hangup_twiml(prompt):
    fallback_response = VoiceResponse()
    fallback_response.say(
        prompt,
        voice="Google.en-US-Chirp3-HD-Aoede",
    )
    fallback_response.hangup()
    return str(fallback_response)


def create_fallback_twiml():
    return create_say_hangup_twiml(
        "I'm sorry, there was an error starting the conversation. Please try again later."
    )


def create_idle_twiml():
    return create_say_hangup_twiml(
        "I'm sorry, I haven't heard you respond in a while. Please try your call again."
    )


def create_error_twiml():
    return create_say_hangup_twiml(
        "I'm sorry, a problem occurred while handling your call. Please try your call again."
    )
