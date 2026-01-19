# JamieBot/app/validators/length_check.py
import re

def validate_length(text: str) -> bool:
    """
    Validates that the text contains no more than 2 sentences.
    """
    # Split sentences by punctuation
    sentences = re.split(r'[.!?]+', text)
    # Remove empty strings
    sentences = [s.strip() for s in sentences if s.strip()]
    return len(sentences) <= 2
