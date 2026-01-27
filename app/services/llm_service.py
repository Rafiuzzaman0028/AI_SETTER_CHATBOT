# JamieBot/app/services/llm_service.py
# JamieBot/app/services/llm_service.py
import os
import logging
import re
from typing import List, Dict
from openai import OpenAI
from app.config import Config

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # ---- MODELS ----
        self.brain_model = "gpt-5.2" # or "gpt-5.2" if you have access
        self.voice_model = (
            "ft:gpt-4o-mini-2024-07-18:jamie-date:human-chat:CIbbXDDz:ckpt-step-34"
        )
        self.brain_temperature = 0.2
        self.voice_temperature = 0.5
        self.max_output_tokens = 150
        self.use_voice_model = True

    def _clean_formatting(self, text: str) -> str:
        """
        1. Strips repetitive openers.
        2. Removes dashes.
        3. Enforces lowercase start.
        """
        if not text: return ""
        
        # 1. Strip the overused openers
        text = re.sub(r'^(hey|got it|sure thing|makes sense|totally)[\.,\s]+(\.\.\.)?\s*', '', text, flags=re.IGNORECASE)

        # 2. Remove dashes
        text = text.replace("—", ", ").replace(" - ", ", ")
        
        # 3. Enforce lowercase start
        if text and len(text) > 0:
            text = text[0].lower() + text[1:]
            
        return text.strip()

    def _extract_text(self, response) -> str:
        return response.choices[0].message.content.strip()

    def _prepare_response(self, system_prompt: str, state_prompt: str, user_message: str, history: List[Dict]) -> str:
        """
        Injects History into the context window.
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add last 10 messages of history for context
        # (This solves the Amnesia bug)
        messages.extend(history[-10:])
        
        # Add current instructions + current message
        final_prompt = f"{state_prompt}\n\n[CURRENT USER MESSAGE]:\n{user_message}"
        messages.append({"role": "user", "content": final_prompt})

        response = self.client.chat.completions.create(
            model=self.brain_model,
            temperature=self.brain_temperature,
            max_completion_tokens=self.max_output_tokens,
            messages=messages
        )
        return self._extract_text(response)

    def _rewrite_human_tone(self, draft_text: str) -> str:
        style_prompt = (
            "Rewrite the following message as Jamie.\n"
            "Persona: Supportive older sister. Casual American vibe.\n"
            "STRICT FORMATTING RULES:\n"
            "1. NO DASHES (—) or hyphens (-). Use '...' or commas instead.\n"
            "2. Make it sound like a real text message.\n"
            "3. Do not answer questions not present in the draft.\n"
            "4. Do not add philosophical thoughts.\n"
            "5. End with the exact same question found in the draft (if any).\n\n"
            f"Draft to rewrite: \"{draft_text}\""
        )
        response = self.client.chat.completions.create(
            model=self.voice_model,
            temperature=self.voice_temperature,
            max_completion_tokens=self.max_output_tokens,
            messages=[{"role": "user", "content": style_prompt}]
        )
        return self._extract_text(response)

    # --- PUBLIC API ---
    def generate_response(self, system_prompt: str, state_prompt: str, user_message: str, history: List[Dict]) -> str:
        # 1. Generate Draft (With History)
        draft = self._prepare_response(system_prompt, state_prompt, user_message, history)
        
        if not draft: return "Hmm, tell me more."

        # 2. Voice Rewrite
        if self.use_voice_model:
            draft = self._rewrite_human_tone(draft)
        
        # 3. Final Cleaning
        final_text = self._clean_formatting(draft)
        return final_text

    def extract_attribute(self, text: str, attribute_type: str) -> str | None:
        prompts = {
            "location": "Extract location: 'US', 'CANADA', 'EU', 'OTHER'.",
            "relationship_goal": "Classify goal: 'SERIOUS', 'CASUAL'.",
            "fitness": "Classify fitness: 'FIT', 'AVERAGE', 'UNFIT'.",
            "finance": "Classify finance: 'LOW', 'HIGH'."
        }
        if attribute_type not in prompts: return None
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.0,
                messages=[
                    {"role": "system", "content": f"Extractor. {prompts[attribute_type]}"},
                    {"role": "user", "content": text}
                ]
            )
            result = response.choices[0].message.content.strip().upper()
            if "UNKNOWN" in result: return None
            return result
        except Exception as e:
            logger.error(f"Extraction Error: {e}")
            return None