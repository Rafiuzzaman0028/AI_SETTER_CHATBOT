# JamieBot/app/state_machine/exit_rules.py
import re
import unicodedata

# 1. TEXT NORMALIZATION (Still needed for the Orchestrator)
def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.lower()
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# 2. ABUSE DETECTION (Still needed for the ENTRY state)
ABUSIVE_KEYWORDS = {
    "fuck", "fucking", "fuck off",
    "bitch", "slut", "whore",
    "asshole", "dumbass",
    "retard", "nigger", "rape",
    "kill", "die", "kys", "go die",
}

def is_abusive(text: str) -> bool:
    return any(word in text for word in ABUSIVE_KEYWORDS)

def entry_boundary_action(normalized_text: str, extracted_attributes: dict) -> str:
    """
    Checks if the very first message is abusive.
    Returns: "ALLOW", "WARN_ABUSE", or "HARD_STOP"
    """
    abuse_count = extracted_attributes.get("abuse_count", 0)
    
    if is_abusive(normalized_text):
        abuse_count += 1
        extracted_attributes["abuse_count"] = abuse_count
        
        if abuse_count >= 2:
            extracted_attributes["hard_stop_triggered"] = True
            return "HARD_STOP"
        return "WARN_ABUSE"
    
    return "ALLOW"

# 3. ENTRY SKIPPING LOGIC (Still needed for ENTRY state)
# If the user says "Hi, I need help with dating", we skip "How is your day?"
DATING_KEYWORDS = {
    "date", "dating", "love life", "girlfriend", "boyfriend",
    "single", "matches", "tinder", "hinge", "bumble", "ghosted",
    "relationship", "hookups", "talking stage", "help", "advice"
}

ORIENTATION_PHRASES = {
    "hi", "hello", "hey", "hey there",
    "who are you", "what is this", "are you real", "are you a bot"
}

def is_orientation_only(text: str) -> bool:
    return text.strip() in ORIENTATION_PHRASES

def has_dating_context(text: str) -> bool:
    return any(word in text for word in DATING_KEYWORDS)

def should_exit_entry(text: str) -> bool:
    """
    Determines if the user skipped small talk and went straight to business.
    """
    normalized = normalize_text(text)
    if is_orientation_only(normalized):
        return False
    return has_dating_context(normalized)