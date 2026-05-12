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
        self.voice_model = (
            "ft:gpt-4o-mini-2024-07-18:jamie-date:human-chat:CIbbXDDz:ckpt-step-34"
        )
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
        
        # ✅ FIX: Increased context window from 10 to 20
        # This solves the "Amnesia" where it forgets the user's goal
        messages.extend(history[-20:]) 
        
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
            "5. Ensure the question from the draft is integrated naturally into the message, but do NOT repeat it if you've already asked it in the body.\n\n"
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
        draft = self._prepare_response(system_prompt, state_prompt, user_message, history)
        if not draft: return "Hmm, tell me more."
        if self.use_voice_model:
            draft = self._rewrite_human_tone(draft)
        final_text = self._clean_formatting(draft)
        return final_text
    
    def extract_attribute(self, text: str, attribute_type: str) -> str | None:
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
            "relationship_goal": "Classify goal: 'SERIOUS', 'CASUAL'.",
            "fitness": "Classify fitness: 'FIT', 'AVERAGE', 'UNFIT'.",
            "finance": "Classify finance: 'LOW', 'HIGH' (savings/invest/comfortable).",
            "age": "Extract age number (e.g., 26). Return 'UNKNOWN' if missing.",
            "tried_solutions": "Summarize what the user has tried (e.g., YouTube, apps, other coaches). Return 'UNKNOWN' if missing.",
            "desired_outcome": "Summarize what the user wants (e.g., serious relationship, girlfriend, more matches). Return 'UNKNOWN' if missing."
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
        user_lower = user_message.lower()
        
        # 1. Identity Check (Expanded for typos and variations)
        identity_keywords =[
            "are you real", "are you really jamie", "is this a bot", 
            "is this ai", "are you a bot", "are u a bot",
            "who is this", "who are you", "who are u", "who r u",
            "is this jamie", "who am i speaking", "am i speaking to jamie"
        ]
        
        if any(k in user_lower for k in identity_keywords):
            # EXACT SCRIPT FROM PDF PAGE 1
            return (
                "I’m Jamie’s notetaker. My job is to understand what guys are struggling with in dating, "
                "so Jamie can better direct her coaching. All of the notes that I take from this chat I give "
                "to her to access what you might need to hear. Can I ask you a few more questions so I have a better understanding?"
            )
        
        # 2. Defensiveness Check
        if "why are you asking" in user_lower or "why do you need to know" in user_lower:
            return "just trying to get a better picture of where you're at so i can see if we can actually help."
        
        return None
    
    def classify_post_link_intent(self, text: str) -> str:
        """
        Determines the user's intent AFTER the link has been sent.
        """
        system_prompt = (
            "You are a classification tool. Classify the user's message into one of these categories:\n"
            "- BOUGHT (e.g. 'I bought it', 'Done', 'Just booked', 'Paid')\n"
            "- QUESTION (e.g. 'Is it one time payment?', 'How long is the call?', 'Do I get a recording?')\n"
            "- HESITATION (e.g. 'I will do it later', 'Not sure', 'I need to think')\n"
            "- TECH_ISSUE (e.g. 'Link not working', 'Error', 'Page wont load')\n"
            "- NEGOTIATION (e.g. 'Can I get a discount?', 'Too expensive')\n"
            "- OFF_TOPIC (e.g. 'Dating is hard', 'Thanks', 'Bye', random chat)\n"
            "Return ONLY the category name (e.g. BOUGHT)."
        )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", # Fast model is fine here
                temperature=0.0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ]
            )
            return response.choices[0].message.content.strip().upper()
        except Exception as e:
            logger.error(f"Intent Classification Error: {e}")
            return "OFF_TOPIC" # Default fallback