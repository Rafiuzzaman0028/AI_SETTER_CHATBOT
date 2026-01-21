# JamieBot/app/services/llm_service.py
import os, logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class LLMService:
    """
    Dual-model LLM service:
    - Stage 1 (Brain): correctness & structure
    - Stage 2 (Voice): human Jamie tone
    """
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=api_key)
        
        # ---- MODELS ----
        self.brain_model = "gpt-5.2"   # SAFE + AVAILABLE
        self.voice_model = (
            "ft:gpt-4o-mini-2024-07-18:jamie-date:human-chat:CIbbXDDz:ckpt-step-34"
        )
        # ---- GENERATION PARAMS ----
        self.brain_temperature = 0.2
        self.voice_temperature = 0.6
        self.max_output_tokens = 120
        # Feature flag (IMPORTANT)
        self.use_voice_model = True
    
    # RESPONSE EXTRACTION
    def _extract_text(self, response) -> str:
        """
        Safely extract text from OpenAI Responses API output.
        Works with dict-based and object-based SDK outputs.
        """
        texts = []
        for item in response.output:
            item_type = getattr(item, "type", None)
            if item_type == "output_text":
                if item.text:
                    texts.append(item.text)
            elif item_type == "message":
                for content in getattr(item, "content", []):
                    if getattr(content, "type", None) == "output_text":
                        texts.append(content.text)
        return " ".join(texts).strip()
    
    # STAGE 1 — BRAIN
    def _prepare_response(self, system_prompt, state_prompt, user_message) -> str:
        """
        Uses GPT to generate a correct, helpful draft response.
        This output is NOT shown to the user.
        """
        response = self.client.responses.create(
            model=self.brain_model,
            temperature=self.brain_temperature,
            max_output_tokens=self.max_output_tokens,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{
                        "type": "input_text",
                        "text": f"{state_prompt}\n\nUser message:\n{user_message}",
                    }],
                },
            ],
        )
        return self._extract_text(response)
    
    # STAGE 2 — VOICE
    def _rewrite_human_tone(self, draft_text: str) -> str:
        """
        Uses the fine-tuned model to rewrite text in a natural human tone.
        No system prompt — tone is learned from fine-tuning.
        """
        response = self.client.responses.create(
            model=self.voice_model,
            temperature=self.voice_temperature,
            max_output_tokens=self.max_output_tokens,
            input=[
                {
                    "role": "user",
                    "content": [{
                        "type": "input_text",
                        "text": (
                            "Rewrite the following message naturally, "
                            "as Jamie — calm, grounded, human and casual American accent"
                            "NO DASHES (—) or hyphens (-). Use '...' or commas instead.\n"
                            "Make it sound like a real text message (relaxed grammar is okay).\n"
                            "Do not add new ideas. "
                            "Do not add extra questions.keep it concise\n\n"
                            f"{draft_text}"
                        ),
                    }],
                },
            ],
        )
        return self._extract_text(response)
    
    # VALIDATION
    def _validate_final_response(self, text: str) -> bool:
        if not text:
            return False
        
        if text.count("?") > 1:
            return False
        
        if len(text.split()) > 40:
            return False
        
        forbidden = [
            "price", "cost", "buy", "sign up",
            "guarantee", "limited", "program"
        ]
        
        lower = text.lower()
        
        return not any(p in lower for p in forbidden)
    
    # PUBLIC API
    def generate_response(self, system_prompt, state_prompt, user_message) -> str:
        # Stage 1
        """
        Full two-stage generation:
        1. GPT-4.1-mini prepares the response
        2. Fine-tuned model rewrites it in human tone
        """
        
        draft = self._prepare_response(
            system_prompt=system_prompt,
            state_prompt=state_prompt,
            user_message=user_message,
        )
        
        # HARD GUARD
        if not draft:
            return "Hmm, can you say a bit more about that?"
        
        # Single-model fallback
        if not self.use_voice_model:
            return draft
        
        # Stage 2
        rewritten = self._rewrite_human_tone(draft)
        if not self._validate_final_response(rewritten):
            return draft
        
        return rewritten
    
    def extract_attribute(self, text: str, attribute_type: str) -> str | None:
        """
        Uses LLM to classify user input into fixed categories.
        Returns None if the user was vague/unclear.
        """
        
        # Define the rules for each type
        prompts = {
            "location": (
                "Extract the location. "
                "Return 'US', 'CANADA', 'EU', or 'OTHER'. "
                "If unclear or not mentioned, return 'UNKNOWN'."
            ),
            "relationship_goal": (
                "Classify the relationship goal. "
                "Categories: 'SERIOUS' (marriage, long-term, real, partner, committed), "
                "'CASUAL' (fun, short-term, seeing what's out there, hookup). "
                "Return 'SERIOUS', 'CASUAL', or 'UNKNOWN'."
            ),
            "fitness": (
                "Classify fitness level. "
                "Categories: 'FIT' (gym, active, athletic, muscular, working out), "
                "'AVERAGE' (decent, okay, normal, fine), "
                "'UNFIT' (out of shape, overweight, no energy, lazy). "
                "Return 'FIT', 'AVERAGE', 'UNFIT', or 'UNKNOWN'."
            ),
            "finance": (
                "Classify financial status regarding coaching. "
                "Categories: 'LOW' (broke, paycheck to paycheck, struggling, student, no money), "
                "'HIGH' (good, doing well, comfortable, savings, invest). "
                "Return 'LOW', 'HIGH', or 'UNKNOWN'."
            )
        }
        
        if attribute_type not in prompts:
            return None
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-5.2", # Fast and smart enough
                temperature=0.0,     # Deterministic
                messages=[
                    {"role": "system", "content": f"You are a data extractor. {prompts[attribute_type]}"},
                    {"role": "user", "content": text}
                ]
            )
            result = response.choices[0].message.content.strip().upper()
            
            # Filter out UNKNOWN or garbage
            if "UNKNOWN" in result:
                return None
            return result
            
        except Exception as e:
            logger.error(f"Extraction Error: {e}")
            return None
