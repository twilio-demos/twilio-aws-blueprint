from typing import Any

from langchain_core.tools import tool

from src.utils.logger import get_logger

logger = get_logger(__name__)

"""
UpdateHints tool for updating hints provided to speech recognition. Use this when prompting the user for information from a bounded list containing things such as proper nouns which may be difficult for speech recognition to otherwise detect. You should then use this to clear the list of hints after the desired information has been recognized.
"""


@tool
def update_hints_tool(hints: list[str], prompt: str) -> dict[str, Any]:
    """
    Tool function to update hints provided to speech recognition. Use this when prompting the user for information from a bounded list containing things such as proper nouns which may be difficult for speech recognition to otherwise detect. You should then use this to clear the list of hints after the desired information has been recognized.

    Args:
        hints: The list of hints to use for speech recognition. Pass an empty list for no hints.
        prompt: The prompt to speak to the user asking for input once the hints are updated.

    Examples:
        update_hints_tool(["Aspirin", "Acetaminophen"], "Which prescription are you refilling?")
        update_hints_tool([], "Is there anything else I can help you with?")
    """

    logger.info("UpdateHints tool invoked:", {"hints": hints, "prompt": prompt})

    return {
        "result": "hint",
        "hints": ",".join(hints) if len(hints) > 0 else "",
        "message": prompt,
    }
