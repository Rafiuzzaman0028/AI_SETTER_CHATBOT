# JamieBot/app/state_machine/transitions.py
from typing import Dict, Optional
from app.state_machine.states import ConversationState
from app.state_machine.exit_rules import (
    normalize_text, entry_boundary_action, should_exit_entry
)

def determine_next_state(current_state, user_message, extracted_attributes=None):
    if extracted_attributes is None: extracted_attributes = {}
    turns = extracted_attributes.get("current_state_turn_count", 0)
    normalized = normalize_text(user_message)

    # ENTRY (User said "Hi")
    if current_state == ConversationState.ENTRY:
        action = entry_boundary_action(normalized, extracted_attributes)
        if action == "HARD_STOP": return ConversationState.END
        if action == "WARN_ABUSE": return ConversationState.ENTRY
        
        # EDGE CASE: If user skips pleasantries and immediately talks dating 
        # (e.g., "I need help with a girl"), go straight to business.
        if should_exit_entry(normalized):
            return ConversationState.STAGE_1_PATTERN
        
        # LOGIC FIX:
        # If this is the FIRST message (turn 0), stay in ENTRY so we can ask "How is your day?"
        # If this is the SECOND message (turn >= 1), move to ENTRY_SOCIAL.
        if turns >= 1:
            return ConversationState.ENTRY_SOCIAL
            
        return ConversationState.ENTRY
    
    # -------------------------
    # 2. ENTRY SOCIAL (User said "My day is good/bad")
    # -------------------------
    if current_state == ConversationState.ENTRY_SOCIAL:
        # The user just answered "Good/Bad". 
        # We accept any answer and immediately move to Stage 1 to start the funnel.
        return ConversationState.STAGE_1_PATTERN
    # --- THE LINEAR FUNNEL (SPEED FIX) ---
    # STAGE 1: PATTERN 
    # FIX: Moved from 2 turns to 1 turn. Move immediately if they answer.
    if current_state == ConversationState.STAGE_1_PATTERN:
        if turns >= 2: 
            return ConversationState.STAGE_2_TIME_COST
        return ConversationState.STAGE_1_PATTERN

    # STAGE 2 -> 3
    if current_state == ConversationState.STAGE_2_TIME_COST:
        return ConversationState.STAGE_3_ADDITIONAL

    # STAGE 3 -> 4
    if current_state == ConversationState.STAGE_3_ADDITIONAL:
        return ConversationState.STAGE_4_FAILED_SOLUTIONS

    # STAGE 4 -> 5
    if current_state == ConversationState.STAGE_4_FAILED_SOLUTIONS:
        return ConversationState.STAGE_5_GOAL

    # STAGE 5 -> 6
    if current_state == ConversationState.STAGE_5_GOAL:
        return ConversationState.STAGE_6_GAP

    # STAGE 6 -> 7
    if current_state == ConversationState.STAGE_6_GAP:
        return ConversationState.STAGE_7_REFRAME

    # STAGE 7 -> 8
    if current_state == ConversationState.STAGE_7_REFRAME:
        return ConversationState.STAGE_8_INTRO_COACHING

    # STAGE 8 -> 9 (CRITICAL FIX)
    if current_state == ConversationState.STAGE_8_INTRO_COACHING:
        # We move to Stage 9 regardless of YES or NO.
        # The Stage 9 PROMPT must handle the "No".
        return ConversationState.STAGE_9_PROGRAM_FRAMING

    # STAGE 9 -> 10
    if current_state == ConversationState.STAGE_9_PROGRAM_FRAMING:
        return ConversationState.STAGE_10_QUAL_LOCATION

    # --- QUALIFICATION FILTERS ---
    if current_state == ConversationState.STAGE_10_QUAL_LOCATION:
        region = extracted_attributes.get("location_region")
        if region == "OTHER": return ConversationState.ROUTE_LOW_TICKET
        if region in {"US", "CANADA", "EU"}: return ConversationState.STAGE_10_QUAL_AGE
        # If unknown, ask again (only stay if absolutely necessary)
        return ConversationState.STAGE_10_QUAL_LOCATION

    if current_state == ConversationState.STAGE_10_QUAL_AGE:
        return ConversationState.STAGE_10_QUAL_RELATIONSHIP

    if current_state == ConversationState.STAGE_10_QUAL_RELATIONSHIP:
        return ConversationState.STAGE_10_QUAL_FITNESS

    if current_state == ConversationState.STAGE_10_QUAL_FITNESS:
        return ConversationState.STAGE_10_QUAL_FINANCE

    if current_state == ConversationState.STAGE_10_QUAL_FINANCE:
        bucket = extracted_attributes.get("financial_bucket")
        if bucket == "low": return ConversationState.ROUTE_LOW_TICKET
        if bucket == "high": return ConversationState.ROUTE_HIGH_TICKET
        
        # NEW SAFETY: If the user answered but extraction failed (returned None), 
        # we shouldn't ask again forever.
        # If text length > 5, assume they answered something valid and default to HIGH (assume innocent until proven broke).
        if len(user_message) > 5:
            # Default to High Ticket to be safe, or ask a clarifying question. 
            # For a "dumb script", default to High Ticket.
            return ConversationState.ROUTE_HIGH_TICKET
        
        return ConversationState.STAGE_10_QUAL_FINANCE