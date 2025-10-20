# file: llm_client.py
import os
from .prompt_template import PROMPT_PREFIX
from google import genai
import json

class LLMClient:
    def __init__(self, token: str = None):
        self.token = token or os.getenv("GEMINI_API_KEY")
        if not self.token:
            raise RuntimeError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=self.token)

    async def ask(self, source_ra: dict, target_ra: dict, vocab: list, max_new_tokens: int = 512):
        prompt = PROMPT_PREFIX + "\n\nSOURCE_RA:\n" + json.dumps(source_ra) + \
                 "\n\nTARGET_RA:\n" + json.dumps(target_ra) + \
                 "\n\nVOCAB:\n" + json.dumps(vocab) + \
                 "\n\nReturn a minimal sequence of transformations in JSON format."

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",  # use working model
            contents=prompt
        )

        # Return raw response text
        txt = getattr(response, "text", "")
        if not txt:
            txt = "no_output"

        return txt
