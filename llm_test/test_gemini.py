# file: test_gemini.py
import os
from google import genai
from google.genai import types

API_KEY = "AIzaSyBjmoW88UamPSs2l5dyycu2yFkHATLr16g"
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

client = genai.Client(api_key=API_KEY)

prompt = "Say 'yes' if you received this message, otherwise say 'no'."

response = client.models.generate_content(
    model="gemini-2.5-flash",  # use the working model
    contents=prompt,
    # config=types.GenerateContentConfig(
    #     max_output_tokens=50,
    #     temperature=0.0,
    #     thinking_config=types.ThinkingConfig(
    #         thinking_budget=128,
    #         include_thoughts=False
    #     )
    # )
)


print("Gemini response:", response.text)
