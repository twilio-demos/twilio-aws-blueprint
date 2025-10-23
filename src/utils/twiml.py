from typing import Optional

from twilio.twiml.voice_response import VoiceResponse

from src.utils.env import LANGUAGE
from src.utils.language import list_languages, load_language
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_initial_twiml(
    action_url: Optional[str],
    host: Optional[str],
    language: Optional[str],
    welcome_greeting: Optional[str],
    hints: Optional[str],
    params: Optional[dict],
):
    # Create TwiML response using Twilio SDK
    response = VoiceResponse()

    # Build WebSocket URL dynamically based on request
    websocket_url = f"wss://{host}/ws/"

    # Connect to ConversationRelay
    connect_action_url = action_url or f"https://{host}/call/action"
    connect = response.connect(action=connect_action_url)

    custom_lang = language or LANGUAGE
    lang_settings = load_language(custom_lang)
    custom_hints = hints or lang_settings.settings.initial_hints

    conversation_relay = connect.conversation_relay(
        url=websocket_url,
        dtmf_detection=True,
        interruptible="any",
        welcome_greeting=welcome_greeting or "",
        transcription_language=custom_lang,
        tts_language=custom_lang,
        tts_provider=lang_settings.settings.tts_provider,
        voice=lang_settings.settings.tts_voice,
        transcription_provider=lang_settings.settings.transcription_provider,
        speech_model=lang_settings.settings.speech_model,
        hints=custom_hints,
        debug="speaker-events",  # This is used for idle detection
    )

    languages = list_languages()
    for lang_name in languages:
        if lang_name == "multi":
            continue
        settings = load_language(lang_name).settings
        conversation_relay.language(
            lang_name,
            settings.tts_provider,
            settings.tts_voice,
            settings.transcription_provider,
            settings.speech_model,
        )

    # Store initial settings as parameters so that we can receive them in the setup message
    conversation_relay.parameter(
        name="initial_hints",
        value=custom_hints,
    )
    conversation_relay.parameter(name="initial_language", value=custom_lang)
    conversation_relay.parameter(name="initial_greeting", value=welcome_greeting or "")

    if params is not None:
        for param, value in params.items():
            conversation_relay.parameter(name=param, value=value)

    return str(response)


def create_say_hangup_twiml(prompt: str, voice: str):
    fallback_response = VoiceResponse()
    fallback_response.say(
        prompt,
        voice=voice,
    )
    fallback_response.hangup()
    return str(fallback_response)


def create_fallback_twiml(language: Optional[str]):
    lang_settings = load_language(language)
    return create_say_hangup_twiml(
        lang_settings.prompts.welcome_error, lang_settings.settings.fallback_tts
    )


def create_idle_twiml(language: Optional[str]):
    lang_settings = load_language(language)
    return create_say_hangup_twiml(
        lang_settings.prompts.idle_timeout, lang_settings.settings.fallback_tts
    )


def create_error_twiml(language: Optional[str]):
    lang_settings = load_language(language)
    return create_say_hangup_twiml(
        lang_settings.prompts.error, lang_settings.settings.fallback_tts
    )
