# JamieBot/app/state_machine/transitions.py
from typing import Dict, Optional
from app.state_machine.states import ConversationState
from app.state_machine.exit_rules import (
    normalize_text, should_exit_entry,
    should_exit_rapport,
    entry_boundary_action, is_stall_response, has_concrete_detail,
    is_problem_signal, confirms_pattern, seeks_help, expresses_exhaustion, 
    gives_permission, declines_permission, has_specific_scenario
)

def determine_next_state(
    current_state: ConversationState,
    user_message: str,
    extracted_attributes: Optional[Dict[str, str]] = None,
) -> ConversationState:
    """
    Determines the next conversation state based on
    the current state and extracted user attributes.
    """

    if extracted_attributes is None :
        extracted_attributes = {}
    
    # -------------------------
    # ENTRY STATE
    # -------------------------
    if current_state == ConversationState.ENTRY:
        normalized = normalize_text(user_message)
        
        extracted_attributes["abuse_count"] = int(extracted_attributes.get("abuse_count", 0))
        
        action = entry_boundary_action(normalized, extracted_attributes)
        if action == "HARD_STOP":
            return ConversationState.END
        
        if action == "WARN_ABUSE":
            return ConversationState.ENTRY
        
        if should_exit_entry(normalized):
            return ConversationState.RAPPORT
        
        return ConversationState.ENTRY
    
    # -------------------------
    # RAPPORT STATE 
    # -------------------------
    if current_state == ConversationState.RAPPORT:
        normalized = normalize_text(user_message)
        
        if seeks_help(normalized):
            return ConversationState.PROBLEM_DISCOVERY
        
        stall_count = int(extracted_attributes.get("stall_count", 0))
        
        if is_stall_response(normalized):
            stall_count += 1
            extracted_attributes["stall_count"] = stall_count
        elif has_concrete_detail(normalized):
            extracted_attributes["stall_count"] = 0
        
        if should_exit_rapport(normalized):
            return ConversationState.PROBLEM_DISCOVERY
        
        return ConversationState.RAPPORT
    
    # -------------------------
    # PROBLEM DISCOVERY STATE 
    # -------------------------
    if current_state == ConversationState.PROBLEM_DISCOVERY:
        normalized = normalize_text(user_message)
        
        # 1. NEW: Check for "Stall" or "I don't know"
        # In this state, "I don't know" means "I need your help." -> Exit.
        if is_stall_response(normalized):
            return ConversationState.COACHING_TRANSITION

        # 2. Check for Specific Scenarios
        if has_specific_scenario(normalized):
            return ConversationState.COACHING_TRANSITION

        # Initialize memory
        signal_count = extracted_attributes.get("problem_signal_count", 0)
        confirmed = extracted_attributes.get("problem_confirmed", False)
        
        # Signal detection
        if is_problem_signal(normalized):
            signal_count += 1
            extracted_attributes["problem_signal_count"] = signal_count
        
        # Confirmation
        if confirms_pattern(normalized) or signal_count >= 2:
            extracted_attributes["problem_confirmed"] = True
            confirmed = True
        
        # Exit conditions
        if seeks_help(normalized) or expresses_exhaustion(normalized):
            return ConversationState.COACHING_TRANSITION
        
        #  CONVERGENCE ENFORCEMENT
        if confirmed:
            return ConversationState.PROBLEM_DISCOVERY 
        
        return ConversationState.PROBLEM_DISCOVERY
    
    # -------------------------
    # COACHING TRANSITION STATE 
    # -------------------------
    if current_state == ConversationState.COACHING_TRANSITION:
        normalized = normalize_text(user_message)
        # User gives permission → begin qualification
        if gives_permission(normalized):
            return ConversationState.QUAL_LOCATION
        
        # User declines or hesitates → stay here, do not push
        if declines_permission(normalized):
            return ConversationState.COACHING_TRANSITION
        
        # Default: hold and wait
        return ConversationState.COACHING_TRANSITION
    
    # -------------------------
    # QUAL LOCATION STATE (Updated for Semantic Extraction)
    # -------------------------
    if current_state == ConversationState.QUAL_LOCATION:
        # Check if Orchestrator successfully extracted a region using AI
        region = extracted_attributes.get("location_region")
        
        if region in {"US", "CANADA", "EU"}:
            return ConversationState.QUAL_RELATIONSHIP_GOAL
        
        if region == "OTHER":
            return ConversationState.ROUTE_LOW_TICKET
            
        # If None/Unknown, stay and ask again
        return ConversationState.QUAL_LOCATION
    
    # -------------------------
    # QUAL RELATIONSHIP GOAL (Updated for Semantic Extraction)
    # -------------------------
    if current_state == ConversationState.QUAL_RELATIONSHIP_GOAL:
        goal = extracted_attributes.get("relationship_goal")
        
        # We accept both Serious and Casual to move forward
        if goal in {"SERIOUS", "CASUAL"}:
            return ConversationState.QUAL_FITNESS
            
        return ConversationState.QUAL_RELATIONSHIP_GOAL
    
    # -------------------------
    # QUAL FITNESS (Updated for Semantic Extraction)
    # -------------------------
    if current_state == ConversationState.QUAL_FITNESS:
        fit = extracted_attributes.get("fitness_level")
        
        if fit in {"FIT", "AVERAGE"}:
            return ConversationState.QUAL_FINANCE
            
        # Even if unfit, PDF logic usually says "Respect" -> move to Finance
        if fit == "UNFIT":
            return ConversationState.QUAL_FINANCE 
            
        return ConversationState.QUAL_FITNESS
    
    # -------------------------
    # FINANCIAL ROUTING LOGIC (Updated for Semantic Extraction)
    # -------------------------
    if current_state == ConversationState.QUAL_FINANCE:
        # If already completed in previous turn
        if extracted_attributes.get("finance_completed"):
            bucket = extracted_attributes.get("financial_bucket")
            if bucket == "low":
                return ConversationState.ROUTE_LOW_TICKET
            return ConversationState.ROUTE_HIGH_TICKET

        bucket = extracted_attributes.get("financial_bucket") # "low" or "high"
        
        if bucket == "low":
            extracted_attributes["finance_completed"] = True
            return ConversationState.ROUTE_LOW_TICKET
        
        if bucket == "high":
            extracted_attributes["finance_completed"] = True
            return ConversationState.ROUTE_HIGH_TICKET
            
        return ConversationState.QUAL_FINANCE
    
    # -------------------------
    # TERMINAL STATES
    # -------------------------
    if current_state in {ConversationState.ROUTE_HIGH_TICKET, ConversationState.ROUTE_LOW_TICKET}:
        return ConversationState.END
    
    return ConversationState.END