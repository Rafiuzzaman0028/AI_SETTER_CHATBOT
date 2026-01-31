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
        
        self.brain_model = "gpt-5.2"
        self.voice_model = "ft:gpt-4o-mini-2024-07-18:jamie-date:human-chat:CIbbXDDz:ckpt-step-34"
        self.brain_temperature = 0.2
        self.voice_temperature = 0.5
        self.max_output_tokens = 150
        self.use_voice_model = True

    def _clean_formatting(self, text: str) -> str:
        if not text: return ""
        text = re.sub(r'^(hey there|hi there|hey|hi|got it|sure thing|makes sense|totally|that makes sense)[\.,\s]+(\.\.\.)?\s*', '', text, flags=re.IGNORECASE)
        text = text.replace("—", ", ").replace(" - ", ", ")
        if text and len(text) > 0:
            text = text[0].lower() + text[1:]
        return text.strip()

    def _extract_text(self, response) -> str:
        return response.choices[0].message.content.strip()

    def _prepare_response(self, system_prompt: str, state_prompt: str, user_message: str, history: List[Dict]) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-10:])
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

    def generate_response(self, system_prompt: str, state_prompt: str, user_message: str, history: List[Dict]) -> str:
        draft = self._prepare_response(system_prompt, state_prompt, user_message, history)
        if not draft: return "Hmm, tell me more."
        if self.use_voice_model:
            draft = self._rewrite_human_tone(draft)
        final_text = self._clean_formatting(draft)
        return final_text

    def extract_attribute(self, text: str, attribute_type: str) -> str | None:
        prompts = {
            "location": "Extract location: 'US', 'CANADA', 'EU', 'OTHER'.",
            "relationship_goal": "Classify goal: 'SERIOUS', 'CASUAL'.",
            "fitness": "Classify fitness: 'FIT', 'AVERAGE', 'UNFIT'.",
            "finance": "Classify finance: 'LOW', 'HIGH' (savings/invest/comfortable).",
            "age": "Extract age number (e.g., 26). Return 'UNKNOWN' if missing."
        }
        if attribute_type not in prompts: return None
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", temperature=0.0,
                messages=[
                    {"role": "system", "content": f"Data Classifier. {prompts[attribute_type]}"},
                    {"role": "user", "content": text}
                ]
            )
            result = response.choices[0].message.content.strip().upper()
            result = re.sub(r'[^A-Z0-9]', '', result)
            if "UNKNOWN" in result: return None
            return result
        except Exception as e:
            logger.error(f"Extraction Error: {e}")
            return None

    def check_off_topic(self, user_message: str) -> str | None:
        identity_keywords = ["are you real", "are you really jamie", "is this a bot", "is this ai", "who is this"]
        if any(k in user_message.lower() for k in identity_keywords):
            return "oh no, sorry, i’m amanda, her assistant. i monitor her social accounts. it’s nice to meet you :)"
        if "why are you asking" in user_message.lower():
            return "just trying to get a better picture of where you're at so i can see if we can actually help."
        return None

    def classify_post_link_intent(self, text: str) -> str:
        system_prompt = (
            "Classify message intent:\n"
            "- BOUGHT (e.g. 'I bought it', 'Done')\n"
            "- QUESTION (e.g. 'Is it one time payment?')\n"
            "- HESITATION (e.g. 'I will do it later')\n"
            "- TECH_ISSUE (e.g. 'Link not working')\n"
            "- NEGOTIATION (e.g. 'Discount?')\n"
            "- OFF_TOPIC (e.g. 'Dating is hard')\n"
            "Return ONLY the category name."
        )
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", temperature=0.0,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
            )
            return response.choices[0].message.content.strip().upper()
        except: return "OFF_TOPIC"