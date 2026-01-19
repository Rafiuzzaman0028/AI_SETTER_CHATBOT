# JamieBot/app/validators/question_check.py
def validate_question_count(text: str) -> bool:
    """
    Validates that the text contains at most one question mark.
    """
    return text.count("?") <= 1
