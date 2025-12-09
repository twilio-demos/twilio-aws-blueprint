from langchain_core.tools import tool

from src.utils.logger import get_logger

logger = get_logger(__name__)

"""
UpdateLanguage tool for changing the conversation language. Use this when the user asks to switch to a supported language, or if the user begins prompting in a different supported language than the one currently used.
"""


@tool
def update_language_tool(language: str) -> str:
    """
    Tool function to update the language used for speech recognition and text-to-speech. Use this when the user asks to switch to a supported language, or if the user begins prompting in a different supported language than the one currently used.

    Args:
        language: The language code to use going forward in the conversation.

    Examples:
        update_language_tool("pt-BR")
    """

    logger.info("UpdateLanguage tool invoked:", {"language": language})

    return language
