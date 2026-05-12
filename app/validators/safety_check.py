# JamieBot/app/validators/safety_check.py
UNSAFE_KEYWORDS = {
    "nude",
    "nudes",
    "sex",
    "onlyfans",
    "explicit",
    "porn",
    "hookup",
}


def validate_safety(text: str) -> bool:
    """
    Checks for unsafe or disallowed language.
    """
    
    lowered = text.lower()
    for keyword in UNSAFE_KEYWORDS:
        if keyword in lowered:
            return False
    
    return True
