# JamieBot/app/state_machine/transitions.py
from typing import Dict, Optional
from app.state_machine.states import ConversationState
from app.state_machine.exit_rules import normalize_text, entry_boundary_action, should_exit_entry

def determine_next_state(
    current_state: ConversationState,
    user_message: str,
    extracted_attributes: Optional[Dict[str, any]] = None,
) -> ConversationState:
    
    if extracted_attributes is None: extracted_attributes = {}
    turns = extracted_attributes.get("current_state_turn_count", 0)
    normalized = normalize_text(user_message)

    # --- ENTRY PHASE ---
    if current_state == ConversationState.ENTRY:
        action = entry_boundary_action(normalized, extracted_attributes)
        if action == "HARD_STOP": return ConversationState.END
        if action == "WARN_ABUSE": return ConversationState.ENTRY
        
        if should_exit_entry(normalized): return ConversationState.STAGE_1_PATTERN
        if turns >= 1: return ConversationState.ENTRY_SOCIAL
        return ConversationState.ENTRY

    if current_state == ConversationState.ENTRY_SOCIAL:
        return ConversationState.STAGE_1_PATTERN

    # --- FUNNEL PHASE ---
    if current_state == ConversationState.STAGE_1_PATTERN:
        if turns >= 2: return ConversationState.STAGE_2_TIME_COST
        return ConversationState.STAGE_1_PATTERN

    if current_state == ConversationState.STAGE_2_TIME_COST: return ConversationState.STAGE_3_ADDITIONAL
    if current_state == ConversationState.STAGE_3_ADDITIONAL: return ConversationState.STAGE_4_FAILED_SOLUTIONS
    if current_state == ConversationState.STAGE_4_FAILED_SOLUTIONS: return ConversationState.STAGE_5_GOAL
    if current_state == ConversationState.STAGE_5_GOAL: return ConversationState.STAGE_6_GAP
    if current_state == ConversationState.STAGE_6_GAP: return ConversationState.STAGE_7_REFRAME
    if current_state == ConversationState.STAGE_7_REFRAME: return ConversationState.STAGE_8_INTRO_COACHING
    
    if current_state == ConversationState.STAGE_8_INTRO_COACHING: return ConversationState.STAGE_9_PROGRAM_FRAMING
    if current_state == ConversationState.STAGE_9_PROGRAM_FRAMING: return ConversationState.STAGE_10_QUAL_LOCATION

    # --- QUALIFICATION PHASE ---
    if current_state == ConversationState.STAGE_10_QUAL_LOCATION:
        region = extracted_attributes.get("location_region")
        if region == "OTHER": return ConversationState.ROUTE_LOW_TICKET
        if region in {"US", "CANADA", "EU"}: return ConversationState.STAGE_10_QUAL_AGE
        return ConversationState.STAGE_10_QUAL_LOCATION

    if current_state == ConversationState.STAGE_10_QUAL_AGE:
        return ConversationState.STAGE_10_QUAL_RELATIONSHIP

    if current_state == ConversationState.STAGE_10_QUAL_RELATIONSHIP:
        return ConversationState.STAGE_10_QUAL_FITNESS

    if current_state == ConversationState.STAGE_10_QUAL_FITNESS:
        return ConversationState.STAGE_10_QUAL_FINANCE

    # --- FINAL ROUTING DECISION ---
    if current_state == ConversationState.STAGE_10_QUAL_FINANCE:
        bucket = extracted_attributes.get("financial_bucket")
        region = extracted_attributes.get("location_region")
        raw_age = extracted_attributes.get("age", 0)
        
        # Check Adult
        is_adult = False
        try:
            if int(raw_age) >= 18: is_adult = True
        except: is_adult = False

        # Check Location
        is_valid_loc = region in {"US", "CANADA", "EU"}

        # STRICT RULE: Must be Adult + Valid Loc + High Money
        if bucket == "HIGH" and is_adult and is_valid_loc:
            return ConversationState.ROUTE_HIGH_TICKET
        
        return ConversationState.ROUTE_LOW_TICKET

    # --- POST LINK HANDLING ---
    if current_state == ConversationState.POST_LINK_FLOW:
        return ConversationState.POST_LINK_FLOW

    if current_state in {ConversationState.ROUTE_HIGH_TICKET, ConversationState.ROUTE_LOW_TICKET}:
        return ConversationState.POST_LINK_FLOW

    return ConversationState.END