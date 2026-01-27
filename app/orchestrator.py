# JamieBot/app/orchestrator.py
# JamieBot/app/orchestrator.py
from typing import Dict, Optional, List
from app.state_machine.states import ConversationState
from app.state_machine.transitions import determine_next_state
from app.services.llm_service import LLMService
from app.validators.safety_check import validate_safety
from app.state_machine.exit_rules import normalize_text
from app.routing.problem_inference import infer_problem_tag, ProblemTag
from app.routing.product_catalog import get_product_for_problem

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
        self,
        user_message: str,
        current_state: ConversationState,
        extracted_attributes: Optional[Dict[str, any]] = None,
        history: List[Dict] = []  # <--- NEW ARGUMENT
    ) -> Dict[str, any]:
        
        if not validate_safety(user_message):
            return {
                "reply": "I’m not the right person for this. You can try OnlyFans for that 😂. Now..if you want help with a real dating strategy, I’m happy to help.",
                "next_state": current_state.value,
                "extracted_attributes": extracted_attributes
            }

        if extracted_attributes is None: extracted_attributes = {}

        # --- LOGIC & EXTRACTION (Same as before) ---
        state_turn_count = extracted_attributes.get("current_state_turn_count", 0)

        if current_state == ConversationState.STAGE_10_QUAL_LOCATION:
            loc = self.llm_service.extract_attribute(user_message, "location")
            if loc: extracted_attributes["location_region"] = loc
        elif current_state == ConversationState.STAGE_10_QUAL_FINANCE:
            fin = self.llm_service.extract_attribute(user_message, "finance")
            if fin: extracted_attributes["financial_bucket"] = fin.lower()
        elif current_state == ConversationState.STAGE_10_QUAL_AGE:
             extracted_attributes["age"] = user_message 

        if "primary_problem" not in extracted_attributes:
            normalized = normalize_text(user_message)
            inferred_problem = infer_problem_tag(normalized)
            if inferred_problem != ProblemTag.GENERAL:
                extracted_attributes["primary_problem"] = inferred_problem

        next_state = determine_next_state(
            current_state=current_state,
            user_message=user_message,
            extracted_attributes=extracted_attributes,
        )

        if next_state != current_state:
            extracted_attributes["current_state_turn_count"] = 0
        else:
            extracted_attributes["current_state_turn_count"] = state_turn_count + 1

        # --- ROUTING (Same as before) ---
        if next_state == ConversationState.ROUTE_HIGH_TICKET:
            response_text = "Perfect. Based on what you told me, you’re a good fit for private coaching.\n\nHere’s the link to book a time:\nhttps://www.jamiedatecoaching.com/privatecoaching"
            return {"reply": response_text, "next_state": ConversationState.END.value, "extracted_attributes": extracted_attributes}

        if next_state == ConversationState.ROUTE_LOW_TICKET:
            raw_tag = extracted_attributes.get("primary_problem")
            if isinstance(raw_tag, str):
                try: problem_tag = ProblemTag(raw_tag)
                except ValueError: problem_tag = ProblemTag.GENERAL
            elif raw_tag: problem_tag = raw_tag
            else: problem_tag = ProblemTag.GENERAL
            product = get_product_for_problem(problem_tag)
            response_text = f"Private coaching might be out of budget, but I don’t want you leaving empty-handed.\n\nCheck out this self-guided option ({product.name}):\n{product.link}"
            return {"reply": response_text, "next_state": ConversationState.END.value, "extracted_attributes": extracted_attributes}

        if next_state == ConversationState.END:
            return {"reply": "Got it. I’ll leave things there for now.", "next_state": next_state.value}

        # --- LLM GENERATION WITH HISTORY ---
        system_prompt = self._load_prompt("system.txt")
        state_prompt = self._load_prompt(f"{next_state.value.lower()}.txt")

        # Pass History here
        response_text = self.llm_service.generate_response(
            system_prompt=system_prompt,
            state_prompt=state_prompt,
            user_message=user_message,
            history=history 
        )
        
        return {
            "reply": response_text,
            "next_state": next_state.value,
            "extracted_attributes": extracted_attributes,
        }