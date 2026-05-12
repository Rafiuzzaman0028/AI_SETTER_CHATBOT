# JamieBot/app/state_machine/transitions.py
from typing import Dict, Optional
from app.state_machine.states import ConversationState
from app.state_machine.exit_rules import (
    normalize_text, entry_boundary_action, should_exit_entry, has_buying_intent
)

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
    # Fast-forward to qualification if buying intent is detected during the funnel
    funnel_states = {
        ConversationState.STAGE_1_PATTERN, ConversationState.STAGE_2_TIME_COST,
        ConversationState.STAGE_3_ADDITIONAL, ConversationState.STAGE_4_FAILED_SOLUTIONS,
        ConversationState.STAGE_5_GOAL, ConversationState.STAGE_6_GAP,
        ConversationState.STAGE_7_REFRAME, ConversationState.STAGE_8_INTRO_COACHING,
        ConversationState.STAGE_9_PROGRAM_FRAMING
    }
    if current_state in funnel_states:
        # Fast-exit if core discovery is complete
        if all(extracted_attributes.get(k) for k in ["primary_problem", "tried_solutions", "desired_outcome"]):
            return ConversationState.STAGE_10_QUAL_LOCATION

        if has_buying_intent(user_message):
            return ConversationState.STAGE_10_QUAL_LOCATION

    if current_state == ConversationState.STAGE_1_PATTERN:
        if turns >= 0: return ConversationState.STAGE_2_TIME_COST # Speed Fix
        return ConversationState.STAGE_1_PATTERN

    if current_state == ConversationState.STAGE_2_TIME_COST:
        if extracted_attributes.get("primary_problem") and str(extracted_attributes.get("primary_problem")) != "GENERAL":
            return ConversationState.STAGE_4_FAILED_SOLUTIONS
        return ConversationState.STAGE_3_ADDITIONAL
    if current_state == ConversationState.STAGE_3_ADDITIONAL: return ConversationState.STAGE_4_FAILED_SOLUTIONS
    if current_state == ConversationState.STAGE_4_FAILED_SOLUTIONS: return ConversationState.STAGE_5_GOAL
    if current_state == ConversationState.STAGE_5_GOAL: return ConversationState.STAGE_6_GAP
    if current_state == ConversationState.STAGE_6_GAP: return ConversationState.STAGE_7_REFRAME
    if current_state == ConversationState.STAGE_7_REFRAME: return ConversationState.STAGE_8_INTRO_COACHING
    
    if current_state == ConversationState.STAGE_8_INTRO_COACHING: return ConversationState.STAGE_9_PROGRAM_FRAMING
    if current_state == ConversationState.STAGE_9_PROGRAM_FRAMING: return ConversationState.STAGE_10_QUAL_LOCATION

    # --- QUALIFICATION PHASE ---
    if current_state == ConversationState.STAGE_10_QUAL_LOCATION:
        if extracted_attributes.get("location_region"):
            return ConversationState.STAGE_10_QUAL_AGE
        return ConversationState.STAGE_10_QUAL_AGE

    if current_state == ConversationState.STAGE_10_QUAL_AGE:
        # Check to skip age if already extracted
        if extracted_attributes.get("age"):
            # Check relationship skip too
            if extracted_attributes.get("relationship_goal") or any(w in normalized for w in ["marriage", "wife", "husband", "long term", "serious relationship"]):
                return ConversationState.STAGE_10_QUAL_FITNESS
            return ConversationState.STAGE_10_QUAL_RELATIONSHIP
        
        if any(w in normalized for w in ["marriage", "wife", "husband", "long term", "serious relationship"]):
            extracted_attributes["relationship_goal"] = "SERIOUS"
            return ConversationState.STAGE_10_QUAL_FITNESS
        return ConversationState.STAGE_10_QUAL_RELATIONSHIP

    if current_state == ConversationState.STAGE_10_QUAL_RELATIONSHIP:
        if extracted_attributes.get("relationship_goal"):
            return ConversationState.STAGE_10_QUAL_FITNESS
        return ConversationState.STAGE_10_QUAL_FITNESS

    if current_state == ConversationState.STAGE_10_QUAL_FITNESS:
        if extracted_attributes.get("fitness_level"):
            return ConversationState.STAGE_10_QUAL_FINANCE
        return ConversationState.STAGE_10_QUAL_FINANCE

    # --- FINAL ROUTING DECISION (The 3 Buckets) ---
    if current_state == ConversationState.STAGE_10_QUAL_FINANCE:
        bucket = extracted_attributes.get("financial_bucket")
        # If we already have finance, we can proceed to final decision logic below
        pass
        region = extracted_attributes.get("location_region")
        raw_age = extracted_attributes.get("age", 0)
        problem_tag = str(extracted_attributes.get("primary_problem", "GENERAL")) # Get problem
        
        # 1. Check Qualifications
        is_adult = False
        try:
            if int(raw_age) >= 18: is_adult = True
        except: is_adult = False

        is_valid_loc = region in {"US", "CANADA", "EU"}
        is_high_finance = (bucket == "HIGH")

        # 2. Logic Tree
        
        # BUCKET 1: DISCOVERY CALL (Qualified)
        if is_adult and is_valid_loc and is_high_finance:
            return ConversationState.ROUTE_DISCOVERY_CALL
        
        # BUCKET 2: COURSE SPECIFIC (Unqualified + Specific Problem)
        if problem_tag != "GENERAL":
            return ConversationState.ROUTE_COURSE_SPECIFIC
            
        # BUCKET 3: FREE GUIDE (Unqualified + Vague Problem)
        return ConversationState.ROUTE_FREE_GUIDE

    # --- POST LINK HANDLING ---
    if current_state == ConversationState.POST_LINK_FLOW:
        return ConversationState.POST_LINK_FLOW

    if current_state in {
        ConversationState.ROUTE_DISCOVERY_CALL, 
        ConversationState.ROUTE_COURSE_SPECIFIC, 
        ConversationState.ROUTE_FREE_GUIDE
    }:
        return ConversationState.POST_LINK_FLOW

    return ConversationState.END