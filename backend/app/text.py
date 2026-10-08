"""Nettoyage des textes saisis par les utilisateurs."""

import re
from typing import Annotated

from pydantic import BeforeValidator

# Caractères interdits dans les documents XML (donc dans les exports .xlsx et
# .docx) : caractères de contrôle autres que tabulation et retours à la ligne,
# et les non-caractères U+FFFE/U+FFFF. Un seul d'entre eux dans une saisie
# faisait échouer l'export de tout le projet (erreur 500 pour tout le monde).
_ILLEGAL_XML_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


def strip_control_chars(value: str) -> str:
    return _ILLEGAL_XML_CHARS.sub("", value)


def _clean(value):
    return strip_control_chars(value) if isinstance(value, str) else value


def clean_strings(value):
    """Nettoie récursivement toutes les chaînes d'une structure JSON."""
    if isinstance(value, str):
        return strip_control_chars(value)
    if isinstance(value, list):
        return [clean_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: clean_strings(item) for key, item in value.items()}
    return value


# Type à utiliser pour tout texte libre reçu de l'API.
CleanStr = Annotated[str, BeforeValidator(_clean)]
