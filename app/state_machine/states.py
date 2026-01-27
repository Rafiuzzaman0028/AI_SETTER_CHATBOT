# JamieBot/app/state_machine/states.py
from enum import Enum

class ConversationState(str, Enum):
    """
    The 11-Stage Sales Funnel (Linear Path).
    """
    ENTRY = "ENTRY"
    ENTRY_SOCIAL = "ENTRY_SOCIAL"  # <--- NEW STATE
    
    # The Core Funnel (Rapport Replacement)
    STAGE_1_PATTERN = "STAGE_1_PATTERN"             # Validate & dig into pattern (Max 2 turns)
    STAGE_2_TIME_COST = "STAGE_2_TIME_COST"         # "How long has this been going on?"
    STAGE_3_ADDITIONAL = "STAGE_3_ADDITIONAL"       # "Any other challenges?"
    STAGE_4_FAILED_SOLUTIONS = "STAGE_4_FAILED_SOLUTIONS" # "What have you tried?"
    STAGE_5_GOAL = "STAGE_5_GOAL"                   # "What is your goal?"
    STAGE_6_GAP = "STAGE_6_GAP"                     # "What needs to change?"
    STAGE_7_REFRAME = "STAGE_7_REFRAME"             # The teaching moment
    STAGE_8_INTRO_COACHING = "STAGE_8_INTRO_COACHING" # "Have you considered coaching?"
    
    # Qualification (The Filters)
    STAGE_9_PROGRAM_FRAMING = "STAGE_9_PROGRAM_FRAMING"
    STAGE_10_QUAL_LOCATION = "STAGE_10_QUAL_LOCATION"
    STAGE_10_QUAL_AGE = "STAGE_10_QUAL_AGE"         # NEW: Added per PDF
    STAGE_10_QUAL_RELATIONSHIP = "STAGE_10_QUAL_RELATIONSHIP"
    STAGE_10_QUAL_FITNESS = "STAGE_10_QUAL_FITNESS"
    STAGE_10_QUAL_FINANCE = "STAGE_10_QUAL_FINANCE"
    
    # Routing
    ROUTE_HIGH_TICKET = "ROUTE_HIGH_TICKET"
    ROUTE_LOW_TICKET = "ROUTE_LOW_TICKET"
    
    END = "END"
