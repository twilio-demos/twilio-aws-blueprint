import os
from typing import List, Optional

import yaml

from src.types.models import Language
from src.utils.env import LANGUAGE
from src.utils.logger import get_logger

logger = get_logger(__name__)
languages_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "languages")
languages: dict[str, Language] = {}


def load_language(language: Optional[str]) -> Language:
    if language is None:
        language = LANGUAGE
    if language in languages:
        return languages[language]
    try:
        path = os.path.join(languages_path, language + ".yaml")
        if os.path.isfile(path):
            with open(path) as file:
                languages[language] = Language.model_validate(yaml.safe_load(file))
                return languages[language]
        logger.error("Lanuage file not found", {"language": language, "path": path})
    except Exception as error:
        logger.error(
            "Error loading language", {"language": language, "error": str(error)}
        )
    return Language()


def list_languages() -> List[str]:
    langs = []
    try:
        langs = [
            os.path.splitext(lang)[0]
            for lang in os.listdir(languages_path)
            if os.path.isfile(os.path.join(languages_path, lang))
        ]
    except Exception as error:
        logger.error(
            "Error listing languages", {"path": languages_path, "error": str(error)}
        )
    return langs
