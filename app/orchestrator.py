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
            return "You are Jamie. Keep it brief."

    def process_message(
        self, user_message: str, current_state: ConversationState,
        extracted_attributes: Optional[Dict[str, any]] = None, history: List[Dict] = [] 
    ) -> Dict[str, any]:
        
        if extracted_attributes is None: extracted_attributes = {}
        
        # 1. SAFETY & OFF-TOPIC
        if not validate_safety(user_message):
            return {"reply": "I’m not the right person for this...", "next_state": current_state.value, "extracted_attributes": extracted_attributes, "progress_score": calculate_score(current_state)}

        off_topic_response = self.llm_service.check_off_topic(user_message)
        if off_topic_response:
            return {"reply": off_topic_response + " anyway... back to what we were saying.", "next_state": current_state.value, "extracted_attributes": extracted_attributes, "progress_score": calculate_score(current_state)}

        # 2. SEMANTIC EXTRACTION
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

        if "primary_problem" not in extracted_attributes:
            normalized = normalize_text(user_message)
            inferred_problem = infer_problem_tag(normalized)
            if inferred_problem != ProblemTag.GENERAL: extracted_attributes["primary_problem"] = inferred_problem

        # 3. NEXT STATE
        next_state = determine_next_state(current_state, user_message, extracted_attributes)
        
        state_turn_count = extracted_attributes.get("current_state_turn_count", 0)
        if next_state != current_state: extracted_attributes["current_state_turn_count"] = 0
        else: extracted_attributes["current_state_turn_count"] = state_turn_count + 1

        # 4. ROUTING LOGIC
        if next_state == ConversationState.ROUTE_HIGH_TICKET:
            raw_tag = extracted_attributes.get("primary_problem", "GENERAL")
            if isinstance(raw_tag, str): 
                try: problem_tag = ProblemTag(raw_tag) 
                except: problem_tag = ProblemTag.GENERAL
            else: problem_tag = raw_tag
            
            product = get_product_for_problem(problem_tag)
            
            response_text = (
                "Perfect. Based on what you told me, you’re a great fit for this specific program.\n\n"
                f"It’s called **{product.name}**, and it fixes exactly what we talked about.\n\n"
                f"You can grab it here (and use code JDate10 for 10% off):\n{product.link}"
            )
            return {"reply": response_text, "next_state": ConversationState.POST_LINK_FLOW.value, "extracted_attributes": extracted_attributes, "progress_score": 100}

        if next_state == ConversationState.ROUTE_LOW_TICKET:
            response_text = (
                "Got it. Based on where you're at, I want to make sure you have the right resources without overcommitting.\n\n"
                "I have a full library of self-guided courses here. Take a look and see which one feels right for you:\n"
                "https://www.jamiedatecoaching.com/courses\n\n"
                "(You can use code JDate10 for 10% off too!)"
            )
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
        system_prompt = self._load_prompt("system.txt")
        state_prompt = self._load_prompt(f"{next_state.value.lower()}.txt")
        response_text = self.llm_service.generate_response(system_prompt, state_prompt, user_message, history)
        
        return {"reply": response_text, "next_state": next_state.value, "extracted_attributes": extracted_attributes, "progress_score": calculate_score(next_state)}