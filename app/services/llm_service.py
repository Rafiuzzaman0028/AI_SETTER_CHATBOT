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
        if not text: 
            return ""
        
        # 1. Strip the overused openers
        text = re.sub(r'^(hey there|hi there|hey|hi|got it|sure thing|makes sense|totally|that makes sense)[\.,\s]+(\.\.\.)?\s*', '', text, flags=re.IGNORECASE)
        
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
        """
        Uses LLM to classify user input into fixed categories.
        Returns None if the user was vague/unclear.
        """
        
        # Define the rules for each type
        prompts = {
            "location": (
                "Extract the location region.\n"
                "Rules:\n"
                "- If US, USA, United States, America -> Return 'US'\n"
                "- If Canada -> Return 'CANADA'\n"
                "- If UK, Europe, Germany, France, Italy, Spain, etc. -> Return 'EU'\n"
                "- If anywhere else (Asia, Africa, Australia, South America) -> Return 'OTHER'\n"
                "- If unknown/not mentioned -> Return 'UNKNOWN'\n"
                "Output one word only."
            ),
            "relationship_goal": (
                "Classify the relationship goal.\n"
                "Categories:\n"
                "- 'SERIOUS' (marriage, long-term, real relationship, partner, committed, wife)\n"
                "- 'CASUAL' (fun, short-term, seeing what's out there, hookup, vibe)\n"
                "Return 'SERIOUS', 'CASUAL', or 'UNKNOWN'."
            ),
            "fitness": (
                "Classify fitness level.\n"
                "Categories:\n"
                "- 'FIT' (gym, active, athletic, muscular, working out, built)\n"
                "- 'AVERAGE' (decent, okay, normal, fine)\n"
                "- 'UNFIT' (out of shape, overweight, no energy, lazy, not fit)\n"
                "Return 'FIT', 'AVERAGE', 'UNFIT', or 'UNKNOWN'."
            ),
            "finance": (
                "Classify financial status regarding coaching.\n"
                "Categories:\n"
                "- 'LOW' (broke, paycheck to paycheck, struggling, student, no money, tight)\n"
                "- 'HIGH' (good, doing well, comfortable, savings, invest, happy with it, stable, money is fine)\n"
                "Return 'LOW', 'HIGH', or 'UNKNOWN'."
            )
        }
        
        if attribute_type not in prompts:
            return None
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", 
                temperature=0.0,     # Deterministic
                messages=[
                    {"role": "system", "content": f"You are a data classifier. {prompts[attribute_type]}"},
                    {"role": "user", "content": text}
                ]
            )
            result = response.choices[0].message.content.strip().upper()
            
            # Clean up potential punctuation (e.g. "EU.")
            result = re.sub(r'[^A-Z]', '', result)

            if "UNKNOWN" in result:
                return None
            return result
            
        except Exception as e:
            logger.error(f"Extraction Error: {e}")
            return None
    
    # In app/services/llm_service.py

    def check_off_topic(self, user_message: str) -> str | None:
        """
        Detects if the user is asking a meta-question (Identity, Reality, Why).
        Returns a specific scripted response if detected, otherwise None.
        """
        
        # 1. Identity Check (Client specific rule from PDF)
        # "If someone asks if the bot is Jamie..."
        identity_keywords = ["are you real", "are you really jamie", "is this a bot", "is this ai", "who is this", "are you human"]
        if any(k in user_message.lower() for k in identity_keywords):
            return "oh no, sorry, i’m amanda, her assistant. i monitor her social accounts. it’s nice to meet you :)"

        # 2. "Why" Check (Defensiveness)
        if "why are you asking" in user_message.lower() or "why do you need to know" in user_message.lower():
            return "just trying to get a better picture of where you're at so i can see if we can actually help."

        # 3. Random/Nonsense Check (Optional - can be expanded)
        # If they ask about weather, politics, etc, we can add logic here.
        
        return None