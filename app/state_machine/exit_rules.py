# JamieBot/app/state_machine/exit_rules.py
import re
import unicodedata

def normalize_text(text: str) -> str:
    if not text:
        return ""
    
    # Normalize unicode (handles smart quotes like ’)
    text = unicodedata.normalize("NFKD", text)
    
    # Lowercase
    text = text.lower()
    
    # Remove punctuation except apostrophes
    text = re.sub(r"[^\w\s']", " ", text)
    
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    
    return text

HELP_SEEKING_PHRASES = {
    "what should i do", "what do i do",
    "what am i supposed to do",
    "how do i fix", "how do i solve", "how do i change this", "how do i get better", "help me",
    "i need help", "i need your help", "i need guidance", "i need advice",
    "guide me",
    "any advice",
    "can you help",
    "can you help me",
    "can you give me advice",
    "what would you do",
    "what should i try",
    "what am i doing wrong",
    "i dont know what to do",
    "i dont know how to fix this",
    "im stuck and need help",
    "i need direction",
}


def seeks_help(text: str) -> bool:
    """
    text is already normalized.
    This detects help-seeking intent, not confusion.
    """
    return any(phrase in text for phrase in HELP_SEEKING_PHRASES)

DATING_KEYWORDS = {
    "date", "dating", "dating life", "love life",
    "girlfriend", "boyfriend", "partner",
    "single", "still single",
    "matches", "no matches",
    "dating apps", "apps", "tinder", "hinge", "bumble", "okcupid",
    "ghosted", "ghosting",
    "relationship", "situationship",
    "women", "men", "girls", "guys", "crush", "attraction",
    "hookups", "talking stage",
}

EMOTION_PHRASES = {
    "feel stuck", "feels stuck", "tired of this",
    "frustrated", "annoyed", "confused", "lost",
    "fed up", "burned out", "discouraged", "hopeless", "drained",
    "emotionally tired", "feels pointless", "ready to give up",
    "giving up",
}


ORIENTATION_PHRASES = {
    "hi", "hello", "hey", "hey there",
    "who are you", "what is this", "what is this about",
    "are you real", "are you a bot", "is this a bot",
    "how does this work",
    "what do you do", "why am i here",
}


ABUSIVE_KEYWORDS = {
    "fuck", "fucking", "fuck off",
    "bitch", "slut", "whore",
    "asshole", "dumbass",
    "retard",
    "nigger",
    "rape",
    "kill", "die", "kys",
    "go die",
}

OFF_TOPIC_KEYWORDS = {
    "physics", "quantum", "math", "algebra",
    "chemistry", "biology",
    "astrology", "horoscope", "zodiac",
    "politics", "election", "government",
    "religion", "god", "allah", "jesus",
    "bitcoin", "crypto", "stocks",
    "coding", "programming",
}


def is_abusive(text: str) -> bool:
    return any(word in text for word in ABUSIVE_KEYWORDS)

def is_off_topic(text: str) -> bool:
    return any(word in text for word in OFF_TOPIC_KEYWORDS)

def has_dating_context(text: str) -> bool:
    return any(word in text for word in DATING_KEYWORDS)

def has_emotional_signal(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in EMOTION_PHRASES)

def is_orientation_only(text: str) -> bool:
    lowered = text.lower().strip()
    return lowered in ORIENTATION_PHRASES

def entry_boundary_action(normalized_text: str, extracted_attributes: dict,) -> str:
    """
    Returns one of:
    - "ALLOW"
    - "WARN_ABUSE"
    - "HARD_STOP"
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

def should_exit_entry(text: str) -> bool:
    """
    ENTRY → RAPPORT gate.
    """
    normalized = normalize_text(text)
    
    if is_orientation_only(normalized):
        return False
    
    return has_dating_context(normalized) or has_emotional_signal(normalized)

#RAPPORT EXIT RULES 

RECURRENCE_MARKERS = {
    "always",
    "every time",
    "keeps happening",
    "keeps doing this",
    "again and again",
    "over and over",
    "constantly",
    "never changes",
    "same thing",
}


OBSTACLE_PHRASES = {
    "can't figure out",
    "cant figure out",
    "dont know why",
    "don't know why",
    "the problem is",
    "what's wrong",
    "something is wrong",
    "i mess it up",
    "i screw it up",
    "i dont get it",
}

UNDERSTANDING_INTENT = {
    "i want to understand",
    "i need to understand",
    "help me understand",
    "why does this happen",
    "why does this keep happening",
    "why am i like this",
    "what am i missing",
}

STALL_PHRASES = {
    "i don't know",
    "i dont know",
    "not sure",
    "i'm not sure",
    "im not sure",
    "can't explain",
    "cant explain",
    "hard to explain",
    "dating sucks",
    "this sucks",
    "it just sucks",
    "everything",
    "idk",
    "clueless",
    "i am just nervous", "just nervous",
    "no idea",
}

# ADD NEW KEYWORDS FOR SPECIFIC SCENARIOS
SPECIFIC_SCENARIO_KEYWORDS = {
    "tomorrow", "tonight", "this weekend", "next week",
    "dress", "outfit", "wear", "clothes", "shirt",
    "movie", "dinner", "coffee", "lunch",
    "class", "work", "gym", "office", "colleague", "coworker",
    "first date", "second date",
    "asking her out", "ask her out", "asking him out", "ask him out",
    "approach", "approaching", "make a move",
}

def is_stall_response(text: str) -> bool:
    return (
        len(text.split()) <= 4
        or any(phrase in text for phrase in STALL_PHRASES)
    )


def has_concrete_detail(text: str) -> bool:
    """
    Concrete = mentions a specific situation, behavior, or pattern
    """
    SIGNAL_WORDS = {
        "messages",
        "texts",
        "dates",
        "matches",
        "ghost",
        "replies",
        "apps",
        "conversation",
        "meet",
        "talking",
        "after",
        "before",
    }
    return any(word in text for word in SIGNAL_WORDS)


def has_specific_scenario(text: str) -> bool:
    """
    Detects if the user is talking about a specific upcoming event or detail.
    If they are, we don't need to dig deeper.
    """
    return any(word in text for word in SPECIFIC_SCENARIO_KEYWORDS)

def has_specific_pattern(text: str) -> bool:
    lowered = text.lower()
    return any(p in lowered for p in RECURRENCE_MARKERS)


def names_clear_obstacle(text: str) -> bool:
    lowered = text.lower()
    return any(p in lowered for p in OBSTACLE_PHRASES)


def seeks_understanding(text: str) -> bool:
    lowered = text.lower()
    return any(p in lowered for p in UNDERSTANDING_INTENT)


def should_exit_rapport(text: str) -> bool:
    """
    RAPPORT → PROBLEM_DISCOVERY gate (working version).
    """
    normalized = normalize_text(text)
    return (
        has_specific_pattern(normalized)
        or names_clear_obstacle(normalized)
        or seeks_understanding(normalized)
        or has_specific_scenario(normalized) # <--- ADD THIS
    )

# PROBLEM DISCOVERY EXIT RULES 

EXHAUSTION_PHRASES = {
    "tried everything",
    "nothing works",
    "out of ideas",
    "at a loss"
}

# --- PROBLEM DISCOVERY HELPERS ---
PROBLEM_SIGNAL_WORDS = {
    "message", "messages",
    "text", "texts", "texting",
    "ghost", "ghosted",
    "reply", "replies",
    "match", "matches",
    "date", "dates",
    "conversation", "talking",
    "after", "before",
    "first", "few",
    "left on read",
    "stopped replying",
}


def is_problem_signal(text: str) -> bool:
    """
    Detects concrete, repeatable dating behavior
    """
    return any(word in text for word in PROBLEM_SIGNAL_WORDS)


def confirms_pattern(text: str) -> bool:
    """
    Detects repetition / absolutes that confirm a pattern
    """
    CONFIRM_WORDS = {
        "always", "every time", "keeps", "never",
        "usually", "most of the time",
    }
    return any(word in text for word in CONFIRM_WORDS)

def expresses_exhaustion(text: str) -> bool:
    lowered = text.lower()
    return any(p in lowered for p in EXHAUSTION_PHRASES)


def should_exit_problem_discovery(text: str) -> bool:
    """
    PROBLEM_DISCOVERY → COACHING_TRANSITION gate.
    If they mention a specific scenario, we have enough info to transition.
    """
    normalized = normalize_text(text)
    return (
        seeks_help(normalized) 
        or expresses_exhaustion(normalized)
        or has_specific_scenario(normalized) # <--- ADD THIS
    )

#COACHING TRANSITION EXIT RULES 

AFFIRMATIVE_PHRASES = {
    "yes", "yeah", "yep", "yup",
    "sure", "okay", "ok",
    "i think so",
    "probably",
    "i want help",
    "i do",
    "sounds good",
    "im open",
    "im open to it",
    "i am open",
    "lets do it",
    "lets try",
    "im willing",
}


NEGATIVE_PHRASES = {
    "no", "nah",
    "not really",
    "not sure",
    "i dont think so",
    "i'm not ready",
    "dont want",
    "not interested",
    "maybe later",
    "forget it",
    "no thanks",
    "pass",
}



def gives_permission(text: str) -> bool:
    return any(phrase in text for phrase in AFFIRMATIVE_PHRASES)

def declines_permission(text: str) -> bool:
    return any(phrase in text for phrase in NEGATIVE_PHRASES)

def is_affirmative(text: str) -> bool:
    return any(p in text for p in AFFIRMATIVE_PHRASES)


def is_negative(text: str) -> bool:
    return any(p in text for p in NEGATIVE_PHRASES)

def should_exit_coaching_transition(text: str) -> bool:
    """
    COACHING_TRANSITION → QUAL_LOCATION gate (working version).
    """
    normalized = normalize_text(text)
    
    if is_negative(normalized):
        return False
    
    if is_affirmative(normalized):
        return True
    
    # Default: gentle forward motion (working version)
    return True


# LOCATION QUAL RULES 

US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california",
    "colorado", "connecticut", "delaware", "florida", "georgia",
    "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas",
    "kentucky", "louisiana", "maine", "maryland", "massachusetts",
    "michigan", "minnesota", "mississippi", "missouri", "montana",
    "nebraska", "nevada", "new hampshire", "new jersey", "new mexico",
    "new york", "north carolina", "north dakota", "ohio", "oklahoma",
    "oregon", "pennsylvania", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont",
    "virginia", "washington", "west virginia", "wisconsin", "wyoming",
}

CANADA_PROVINCES = {
    "ontario", "quebec", "british columbia", "alberta",
    "manitoba", "saskatchewan", "nova scotia",
    "new brunswick", "newfoundland", "prince edward island",
}

EU_COUNTRIES = {
    "germany", "france", "italy", "spain", "netherlands",
    "belgium", "sweden", "norway", "denmark", "finland",
    "poland", "austria", "switzerland", "ireland",
    "portugal", "czech republic", "greece", "hungary",
}

US_COUNTRIES = {
    "us", "usa", "united states", "america"
}

CANADA_COUNTRIES = {
    "canada"
}


def extract_location_detail(text: str) -> dict | None:
    """
    Returns structured location info if detected.
    Does NOT decide eligibility.
    """
    # US states
    for state in US_STATES:
        if state in text:
            return {"region": "US", "detail": state}
        
    # Canada provinces
    for province in CANADA_PROVINCES:
        if province in text:
            return {"region": "CANADA", "detail": province}
    
    # EU countries
    for country in EU_COUNTRIES:
        if country in text:
            return {"region": "EU", "detail": country}
    
    # Region mentions
    if "eu" in text or "europe" in text:
        return {"region": "EU", "detail": None}
    
    if any(c in text for c in US_COUNTRIES):
        return {"region": "US", "detail": None}
    
    if any(c in text for c in CANADA_COUNTRIES):
        return {"region": "CANADA", "detail": None}
    
    return None

def is_location_eligible(text: str) -> bool:
    return extract_location_detail(text) is not None

# RELATIONSHIP GOAL QUAL RULES 

CASUAL_PHRASES = {
    "casual", "dating",
    "seeing whats out there",
    "just dating", "fun"
}

SERIOUS_PHRASES = {
    "serious", "long term",
    "relationship", "girlfriend", "wife", "marriage"
}

def classify_relationship_goal(text: str) -> str | None:
    """
    Returns: 'supported', 'unsupported', or None
    """
    if any(p in text for p in SERIOUS_PHRASES):
        return "supported"
    
    if any(p in text for p in CASUAL_PHRASES):
        return "unsupported"
    
    return None

# FITNESS QUAL RULES 

LOW_CAPACITY_PHRASES = {
    "burned out", "exhausted", "overwhelmed",
    "no energy", "cant focus", "can't focus",
    "falling apart", "barely functioning",
}

def has_sufficient_capacity(text: str) -> bool:
    """
    Returns False only in clear low-capacity cases.
    Default is True (pass).
    """
    if any(p in text for p in LOW_CAPACITY_PHRASES):
        return False
    
    return True

# FINANCE QUAL RULES 

LOW_BUDGET_PHRASES = {
    "paycheck to paycheck",
    "broke",
    "struggling",
    "tight",
    "no money",
    "cant afford",
    "can't afford",
    "low on money",
    "barely scraping by",
}


MID_BUDGET_PHRASES = {
    "some savings",
    "a little saved",
    "okay financially",
    "doing alright",
    "not struggling",
    "managing fine",
}


HIGH_BUDGET_PHRASES = {
    "doing well",
    "pretty well",
    "pretty good",
    "comfortable",
    "good income",
    "financially stable",
    "well off",
    "money is not an issue",
}


def get_financial_bucket(text: str) -> str | None:
    """
    Returns: 'low', 'mid', 'high', or None
    """
    if any(p in text for p in LOW_BUDGET_PHRASES):
        return "low"
    
    if any(p in text for p in MID_BUDGET_PHRASES):
        return "mid"
    
    if any(p in text for p in HIGH_BUDGET_PHRASES):
        return "high"
    
    return None

INVESTMENT_INTENT_PHRASES = {
    "invest in myself",
    "i invest",
    "i usually invest",
    "i get help",
    "i pay for help",
    "i hire",
    "i buy courses",
    "i buy programs",
    "i pay for coaching",
    "i invest in growth",
}


def expresses_investment_mindset(text: str) -> bool:
    """
    Detects willingness to invest without mentioning money explicitly.
    """
    return any(p in text for p in INVESTMENT_INTENT_PHRASES)

OUT_OF_SHAPE_PHRASES = {"out of shape", "overweight", "fat", "unfit", "skinny fat", "no gym"}
AVERAGE_PHRASES = {"average", "okay shape", "normal", "not bad", "decent", "dad bod"}
FIT_PHRASES = {"fit", "muscular", "athletic", "gym", "in shape", "strong", "shredded"}

def has_fitness_level(text: str) -> bool:
    """Used by transitions.py to check valid fitness answer"""
    return (
        any(p in text for p in OUT_OF_SHAPE_PHRASES) or
        any(p in text for p in AVERAGE_PHRASES) or
        any(p in text for p in FIT_PHRASES)
    )

# 2. Function Aliases (Map old names to new logic)
def extract_location(text: str):
    data = extract_location_detail(text)
    if data:
        return data['detail'] or data['region']
    return None

def has_relationship_goal(text: str) -> bool:
    return classify_relationship_goal(text) is not None