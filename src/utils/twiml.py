from typing import Optional

from twilio.twiml.voice_response import VoiceResponse

from src.utils.env import (
    INITIAL_HINTS,
    LANGUAGE,
    SPEECH_MODEL,
    SPLIT_CHAR,
    TRANSCRIPTION_PROVIDER,
    TTS_PROVIDER,
    TTS_VOICE,
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

    languages = (language or LANGUAGE).split(SPLIT_CHAR)
    env_languages = LANGUAGE.split(SPLIT_CHAR)
    hints_list = (hints or INITIAL_HINTS).split(SPLIT_CHAR)
    tts_providers = TTS_PROVIDER.split(SPLIT_CHAR)
    transcription_providers = TRANSCRIPTION_PROVIDER.split(SPLIT_CHAR)
    speech_models = SPEECH_MODEL.split(SPLIT_CHAR)
    voices = TTS_VOICE.split(SPLIT_CHAR)

    custom_language = False
    custom_language_index = 0

    if len(languages) == 1 and len(env_languages) > 1 and languages[0] in env_languages:
        # If a specific language was passed to this function, we want to use that language's configuration for TTS and STT parameters.
        custom_language = True
        custom_language_index = env_languages.index(languages[0])

    tts_provider = tts_providers[0]
    voice = voices[0]
    transcription_provider = transcription_providers[0]
    speech_model = speech_models[0]
    custom_hints = hints_list[0]

    if custom_language:
        # Use setting per language if defined
        if len(tts_providers) > custom_language_index:
            tts_provider = tts_providers[custom_language_index]
        if len(voices) > custom_language_index:
            voice = voices[custom_language_index]
        if len(transcription_providers) > custom_language_index:
            transcription_provider = transcription_providers[custom_language_index]
        if len(speech_models) > custom_language_index:
            speech_model = speech_models[custom_language_index]
        if len(hints_list) > custom_language_index:
            custom_hints = hints_list[custom_language_index]

    conversation_relay = connect.conversation_relay(
        url=websocket_url,
        dtmf_detection=True,
        interruptible="any",
        welcome_greeting=welcome_greeting or "",
        transcription_language=languages[0],
        tts_language=languages[0],
        tts_provider=tts_provider,
        voice=voice,
        transcription_provider=transcription_provider,
        speech_model=speech_model,
        hints=custom_hints,
    )

    if len(env_languages) > 1:
        for index in range(len(env_languages)):
            if env_languages[index] == "multi":
                continue
            conversation_relay.language(
                env_languages[index],
                tts_providers[index],
                voices[index],
                transcription_providers[index],
                speech_models[index],
            )

    # Store initial settings as parameters so that we can receive them in the setup message
    conversation_relay.parameter(
        name="initial_hints",
        value=custom_hints,
    )
    conversation_relay.parameter(name="initial_language", value=languages[0])
    conversation_relay.parameter(name="initial_greeting", value=welcome_greeting or "")

    if params is not None:
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
