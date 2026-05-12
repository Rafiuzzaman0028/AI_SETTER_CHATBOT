# JamieBot/app/orchestrator.py
from typing import Dict, Optional, List
import re
from app.state_machine.states import ConversationState
from app.state_machine.transitions import determine_next_state
from app.services.llm_service import LLMService
from app.validators.safety_check import validate_safety
from app.state_machine.exit_rules import normalize_text
from app.routing.problem_inference import infer_problem_tag, ProblemTag
from app.routing.product_catalog import get_product_for_problem
from app.scoring import calculate_score

class Orchestrator:
    def __init__(self):
        self.llm_service = LLMService()

    def _load_prompt(self, filename: str) -> str:
        try:
            with open(f"app/prompts/{filename}", "r", encoding="utf-8") as file:
                return file.read().strip()
        except FileNotFoundError:
            return "You are Jamie. Keep the conversation moving."

    def process_message(
        self,
        user_message: str,
        current_state: ConversationState,
        extracted_attributes: Optional[Dict[str, any]] = None,
        history: List[Dict] = [] 
    ) -> Dict[str, any]:
        
        if extracted_attributes is None: extracted_attributes = {}
        
        # 1. SAFETY & OFF-TOPIC
        if not validate_safety(user_message):
            return {"reply": "I’m not the right person for this...", "next_state": current_state.value, "extracted_attributes": extracted_attributes, "progress_score": calculate_score(current_state)}

        off_topic_response = self.llm_service.check_off_topic(user_message)
        if off_topic_response:
            return {"reply": off_topic_response + " anyway... back to what we were saying.", "next_state": current_state.value, "extracted_attributes": extracted_attributes, "progress_score": calculate_score(current_state)}

        # 2. EXTRACTION
        if current_state == ConversationState.STAGE_10_QUAL_LOCATION:
            loc = self.llm_service.extract_attribute(user_message, "location")
            if loc: extracted_attributes["location_region"] = loc
        elif current_state == ConversationState.STAGE_10_QUAL_FINANCE:
            fin = self.llm_service.extract_attribute(user_message, "finance")
            if fin: extracted_attributes["financial_bucket"] = fin
        elif current_state == ConversationState.STAGE_10_QUAL_AGE:
            age_raw = self.llm_service.extract_attribute(user_message, "age")
            try:
                age_num = re.search(r'\d+', str(age_raw))
                if age_num: extracted_attributes["age"] = int(age_num.group())
            except: extracted_attributes["age"] = 0
        elif current_state == ConversationState.STAGE_10_QUAL_RELATIONSHIP:
            goal = self.llm_service.extract_attribute(user_message, "relationship_goal")
            if goal: extracted_attributes["relationship_goal"] = goal
        elif current_state == ConversationState.STAGE_10_QUAL_FITNESS:
            fit = self.llm_service.extract_attribute(user_message, "fitness")
            if fit: extracted_attributes["fitness_level"] = fit

        if "primary_problem" not in extracted_attributes:
            normalized = normalize_text(user_message)
            inferred_problem = infer_problem_tag(normalized)
            if inferred_problem != ProblemTag.GENERAL: extracted_attributes["primary_problem"] = inferred_problem

        if "tried_solutions" not in extracted_attributes:
            tried = self.llm_service.extract_attribute(user_message, "tried_solutions")
            if tried: extracted_attributes["tried_solutions"] = tried

        if "desired_outcome" not in extracted_attributes:
            outcome = self.llm_service.extract_attribute(user_message, "desired_outcome")
            if outcome: extracted_attributes["desired_outcome"] = outcome

        # 3. TRANSITION
        next_state = determine_next_state(current_state, user_message, extracted_attributes)
        
        state_turn_count = extracted_attributes.get("current_state_turn_count", 0)
        if next_state != current_state: extracted_attributes["current_state_turn_count"] = 0
        else: extracted_attributes["current_state_turn_count"] = state_turn_count + 1

        # --- 4. ROUTING LOGIC (THE 3 OUTCOMES) ---
        
        # OUTCOME 1: DISCOVERY CALL (Qualified)
        if next_state == ConversationState.ROUTE_DISCOVERY_CALL:
            system_prompt = self._load_prompt("system.txt")
            state_prompt = self._load_prompt("route_discovery_call.txt")
            response_text = self.llm_service.generate_response(system_prompt, state_prompt, user_message, history)
            return {"reply": response_text, "next_state": ConversationState.POST_LINK_FLOW.value, "extracted_attributes": extracted_attributes, "progress_score": 100}

        # OUTCOME 2: SPECIFIC COURSE (Unqualified + Specific Problem)
        if next_state == ConversationState.ROUTE_COURSE_SPECIFIC:
            # Resolve Product
            raw_tag = extracted_attributes.get("primary_problem", "GENERAL")
            if isinstance(raw_tag, str): 
                try: problem_tag = ProblemTag(raw_tag)
                except: problem_tag = ProblemTag.GENERAL
            else: problem_tag = raw_tag
            
            product = get_product_for_problem(problem_tag)
            
            system_prompt = self._load_prompt("system.txt")
            state_prompt = self._load_prompt("route_course_specific.txt")
            # Inject product info into state prompt
            state_prompt = state_prompt.replace("{product_name}", product.name).replace("{product_link}", product.link)
            
            response_text = self.llm_service.generate_response(system_prompt, state_prompt, user_message, history)
            return {"reply": response_text, "next_state": ConversationState.POST_LINK_FLOW.value, "extracted_attributes": extracted_attributes, "progress_score": 100}

        # OUTCOME 3: FREE GUIDE / GENERAL (Unqualified + Vague)
        if next_state == ConversationState.ROUTE_FREE_GUIDE:
            system_prompt = self._load_prompt("system.txt")
            state_prompt = self._load_prompt("route_free_guide.txt") # I should create this too
            response_text = self.llm_service.generate_response(system_prompt, state_prompt, user_message, history)
            return {"reply": response_text, "next_state": ConversationState.POST_LINK_FLOW.value, "extracted_attributes": extracted_attributes, "progress_score": 100}

        # 5. POST LINK HANDLING
        if current_state == ConversationState.POST_LINK_FLOW:
            intent = self.llm_service.classify_post_link_intent(user_message)
            prompt_file = "post_link_off_topic.txt"
            if intent == "BOUGHT": prompt_file = "post_link_bought.txt"
            elif intent == "QUESTION": prompt_file = "post_link_question.txt"
            elif intent == "HESITATION": prompt_file = "post_link_hesitation.txt"
            elif intent == "TECH_ISSUE": prompt_file = "post_link_tech.txt"
            elif intent == "NEGOTIATION": prompt_file = "post_link_negotiation.txt"
            
            system_prompt = self._load_prompt("system.txt")
            state_prompt = self._load_prompt(prompt_file)
            response_text = self.llm_service.generate_response(system_prompt, state_prompt, user_message, history)
            return {"reply": response_text, "next_state": ConversationState.POST_LINK_FLOW.value, "extracted_attributes": extracted_attributes, "progress_score": 100}

        # 6. NORMAL GENERATION
        if next_state == ConversationState.END:
            return {"reply": "Got it. I’ll leave things there for now.", "next_state": next_state.value, "progress_score": 100}

        system_prompt = self._load_prompt("system.txt")
        state_prompt = self._load_prompt(f"{next_state.value.lower()}.txt")
        response_text = self.llm_service.generate_response(system_prompt, state_prompt, user_message, history)
        
        return {"reply": response_text, "next_state": next_state.value, "extracted_attributes": extracted_attributes, "progress_score": calculate_score(next_state)}