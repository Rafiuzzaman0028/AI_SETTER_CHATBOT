# JamieBot/app/scoring.py
from app.state_machine.states import ConversationState

# Map every state to a percentage (0 to 100)
SCORE_MAP = {
    ConversationState.ENTRY: 0,
    ConversationState.ENTRY_SOCIAL: 10,
    ConversationState.STAGE_1_PATTERN: 15,
    ConversationState.STAGE_2_TIME_COST: 25,
    ConversationState.STAGE_3_ADDITIONAL: 35,
    ConversationState.STAGE_4_FAILED_SOLUTIONS: 45,
    ConversationState.STAGE_5_GOAL: 55,
    ConversationState.STAGE_6_GAP: 65,
    ConversationState.STAGE_7_REFRAME: 70,
    ConversationState.STAGE_8_INTRO_COACHING: 75,
    ConversationState.STAGE_9_PROGRAM_FRAMING: 80,
    ConversationState.STAGE_10_QUAL_LOCATION: 85,
    ConversationState.STAGE_10_QUAL_AGE: 88,
    ConversationState.STAGE_10_QUAL_RELATIONSHIP: 90,
    ConversationState.STAGE_10_QUAL_FITNESS: 92,
    ConversationState.STAGE_10_QUAL_FINANCE: 95,
    ConversationState.ROUTE_HIGH_TICKET: 100,
    ConversationState.ROUTE_LOW_TICKET: 100,
    ConversationState.POST_LINK_FLOW: 100,
    ConversationState.END: 100
}

def calculate_score(state: ConversationState) -> int:
    return SCORE_MAP.get(state, 0)