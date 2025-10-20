from typing import Optional

from twilio.twiml.voice_response import VoiceResponse

from src.utils.env import (
    ERROR_PROMPT,
    FALLBACK_TTS,
    IDLE_TIMEOUT_PROMPT,
    INITIAL_HINTS,
    LANGUAGE,
    SPEECH_MODEL,
    SPLIT_CHAR,
    TRANSCRIPTION_PROVIDER,
    TTS_PROVIDER,
    TTS_VOICE,
    WELCOME_ERROR_PROMPT,
    get_for_language,
)
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

    custom_lang = (language or LANGUAGE).split(SPLIT_CHAR)[0]
    custom_hints = get_for_language(hints or INITIAL_HINTS, custom_lang)

    conversation_relay = connect.conversation_relay(
        url=websocket_url,
        dtmf_detection=True,
        interruptible="any",
        welcome_greeting=welcome_greeting or "",
        transcription_language=custom_lang,
        tts_language=custom_lang,
        tts_provider=get_for_language(TTS_PROVIDER, custom_lang),
        voice=get_for_language(TTS_VOICE, custom_lang),
        transcription_provider=get_for_language(TRANSCRIPTION_PROVIDER, custom_lang),
        speech_model=get_for_language(SPEECH_MODEL, custom_lang),
        hints=custom_hints,
    )

    env_languages = LANGUAGE.split(SPLIT_CHAR)
    if len(env_languages) > 1:
        for index in range(len(env_languages)):
            lang = env_languages[index]
            if lang == "multi":
                continue
            conversation_relay.language(
                lang,
                get_for_language(TTS_PROVIDER, lang),
                get_for_language(TTS_VOICE, lang),
                get_for_language(TRANSCRIPTION_PROVIDER, lang),
                get_for_language(SPEECH_MODEL, lang),
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


def create_say_hangup_twiml(prompt, language: Optional[str]):
    fallback_response = VoiceResponse()
    fallback_response.say(
        get_for_language(prompt, language),
        voice=get_for_language(FALLBACK_TTS, language),
    )
    fallback_response.hangup()
    return str(fallback_response)


def create_fallback_twiml(language: Optional[str]):
    return create_say_hangup_twiml(WELCOME_ERROR_PROMPT, language)


def create_idle_twiml(language: Optional[str]):
    return create_say_hangup_twiml(IDLE_TIMEOUT_PROMPT, language)


def create_error_twiml(language: Optional[str]):
    return create_say_hangup_twiml(ERROR_PROMPT, language)
