# JamieBot/app/orchestrator.py
from typing import Dict, Optional

from app.state_machine.states import ConversationState
from app.state_machine.transitions import determine_next_state
from app.services.llm_service import LLMService
from app.validators.length_check import validate_length
from app.validators.question_check import validate_question_count
from app.validators.safety_check import validate_safety

from app.state_machine.exit_rules import normalize_text
from app.routing.problem_inference import infer_problem_tag, ProblemTag
from app.routing.product_catalog import get_product_for_problem


class Orchestrator:
    """
    Central controller that coordinates state logic,
    prompt selection, LLM generation, and validation.
    """

    def __init__(self):
        self.llm_service = LLMService()

    def _load_prompt(self, filename: str) -> str:
        """
        Loads a prompt file from the prompts directory.
        """
        with open(f"app/prompts/{filename}", "r", encoding="utf-8") as file:
            return file.read().strip()

    def process_message(
        self,
        user_message: str,
        current_state: ConversationState,
        extracted_attributes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Main orchestration function.
        """
        if extracted_attributes is None:
            extracted_attributes = {}

        # =================================================
        # 🧠 SEMANTIC EXTRACTION (The "Solid" Fix)
        # =================================================
        
        # 1. Location Extraction
        if current_state == ConversationState.QUAL_LOCATION:
            loc = self.llm_service.extract_attribute(user_message, "location")
            if loc: extracted_attributes["location_region"] = loc

        # 2. Relationship Extraction
        elif current_state == ConversationState.QUAL_RELATIONSHIP_GOAL:
            goal = self.llm_service.extract_attribute(user_message, "relationship_goal")
            if goal: extracted_attributes["relationship_goal"] = goal

        # 3. Fitness Extraction
        elif current_state == ConversationState.QUAL_FITNESS:
            fit = self.llm_service.extract_attribute(user_message, "fitness")
            if fit: extracted_attributes["fitness_level"] = fit

        # 4. Finance Extraction
        elif current_state == ConversationState.QUAL_FINANCE:
            fin = self.llm_service.extract_attribute(user_message, "finance")
            if fin: 
                extracted_attributes["financial_bucket"] = fin.lower() # transitions expects "low" or "high"

        # =================================================
        # END EXTRACTION
        # =================================================

        # 1️⃣ Determine next state (deterministic)
        next_state = determine_next_state(
            current_state=current_state,
            user_message=user_message,
            extracted_attributes=extracted_attributes,
        )

        # ================================
        # 🧠 STORE PRIMARY PROBLEM (ONCE)
        # ================================
        if "primary_problem" not in extracted_attributes:
            if current_state in {
                ConversationState.PROBLEM_DISCOVERY,
                ConversationState.COACHING_TRANSITION,
            }:
                normalized = normalize_text(user_message)
                inferred_problem = infer_problem_tag(normalized)

                if inferred_problem != ProblemTag.GENERAL:
                    extracted_attributes["primary_problem"] = inferred_problem

        # ================================
        #  STEP 4: ROUTE_HIGH_TICKET
        # ================================
        if next_state == ConversationState.ROUTE_HIGH_TICKET:
            normalized = normalize_text(user_message)

            # Retrieve raw value
            raw_tag = extracted_attributes.get("primary_problem")
            
            # FIX: Ensure we have a ProblemTag Enum, not a string
            if isinstance(raw_tag, str):
                try:
                    problem_tag = ProblemTag(raw_tag)
                except ValueError:
                    problem_tag = ProblemTag.GENERAL
            elif raw_tag:
                problem_tag = raw_tag
            else:
                problem_tag = infer_problem_tag(normalized)

            product = get_product_for_problem(problem_tag)

            response_text = (
                f"Based on what you shared earlier, this seems to be the main thing holding you back right now.\n\n"
                f"I’d recommend starting with **{product.name}** — it’s designed specifically for this.\n\n"
                f"You can check it out here:\n{product.link}"
            )

            return {
                "reply": response_text,
                "next_state": ConversationState.END.value,
                "extracted_attributes": extracted_attributes,
            }


        # ================================
        #  ROUTE_LOW_TICKET
        # ================================
        if next_state == ConversationState.ROUTE_LOW_TICKET:
            response_text = (
                "I’m not able to offer private coaching here, but I don’t want you leaving empty-handed.\n\n"
                "You can start here — it’s completely free and covers the fundamentals:\n\n"
                "https://www.jamiedatecoaching.com/free-dating-guide-gift"
            )

            return {
                "reply": response_text,
                "next_state": ConversationState.END.value,
                "extracted_attributes": extracted_attributes,
            }


        # 2️⃣ Load prompts
        # If conversation has ended, return cleanly
        if next_state == ConversationState.END:
            return {
                "reply": "Got it. I’ll leave things there for now.",
                "next_state": next_state.value,
            }

        # Otherwise, continue normally
        system_prompt = self._load_prompt("system.txt")
        state_prompt = self._load_prompt(f"{next_state.value.lower()}.txt")

        # 3️⃣ Generate response (retry up to 2 times)
        attempts = 0
        response_text = ""

        while attempts < 3:
            response_text = self.llm_service.generate_response(
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                user_message=user_message,
            )

            if (
                validate_length(response_text)
                and validate_question_count(response_text)
                and validate_safety(response_text)
            ):
                break

            attempts += 1

        # 4️⃣ Final safety fallback
        if not response_text:
            response_text = "Got it. Let me know when you’re ready to continue."

        return {
            "reply": response_text,
            "next_state": next_state.value,
            "extracted_attributes": extracted_attributes,
        }