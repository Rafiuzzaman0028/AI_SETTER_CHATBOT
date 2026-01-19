# JamieBot/app/routing/problem_inference.py
from enum import Enum

class ProblemTag(str, Enum):
    TEXTING = "TEXTING"
    MATCHES = "MATCHES"
    APPROACH = "APPROACH"
    SPARK = "SPARK"
    ESCALATION = "ESCALATION"
    CONFIDENCE = "CONFIDENCE"
    GENERAL = "GENERAL"

# Keyword Signals

TEXTING_KEYWORDS = {
    "texting",
    "text",
    "messages",
    "messaging",
    "what to say",
    "conversation fizzle",
    "reply",
}

MATCHES_KEYWORDS = {
    "matches",
    "no matches",
    "dating apps",
    "tinder",
    "hinge",
    "bumble",
    "profile",
    "bio",
}

APPROACH_KEYWORDS = {
    "approach",
    "approaching",
    "in person",
    "real life",
    "cold approach",
    "social anxiety",
    "nervous",
}

SPARK_KEYWORDS = {
    "no spark",
    "friend zone",
    "friends",
    "chemistry",
    "attraction",
    "too nice",
}

ESCALATION_KEYWORDS = {
    "escalate",
    "physical",
    "kiss",
    "touch",
    "sexual",
    "make a move",
}

CONFIDENCE_KEYWORDS = {
    "confidence",
    "self doubt",
    "feel stuck",
    "insecure",
    "not good enough",
    "lost",
}

# Inference Function
def infer_problem_tag(text: str) -> ProblemTag:
    """
    Infers the primary dating problem from normalized user text.
    Returns exactly ONE ProblemTag.
    """
    
    if any(k in text for k in TEXTING_KEYWORDS):
        return ProblemTag.TEXTING
    
    if any(k in text for k in MATCHES_KEYWORDS):
        return ProblemTag.MATCHES
    
    if any(k in text for k in APPROACH_KEYWORDS):
        return ProblemTag.APPROACH
    
    if any(k in text for k in SPARK_KEYWORDS):
        return ProblemTag.SPARK
    
    if any(k in text for k in ESCALATION_KEYWORDS):
        return ProblemTag.ESCALATION
    
    if any(k in text for k in CONFIDENCE_KEYWORDS):
        return ProblemTag.CONFIDENCE
    
    return ProblemTag.GENERAL
