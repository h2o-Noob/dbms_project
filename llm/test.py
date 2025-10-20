# file: ra_llm_transform.py
import json
from gpt4all import GPT4All

# -------------------------
# Step 1: Hardcoded RA Trees
# -------------------------
planA = {
    "type": "Join",
    "condition": "A.id = B.id",
    "left": {"type": "Scan", "table": "A"},
    "right": {"type": "Scan", "table": "B"}
}

planB = {
    "type": "Join",
    "condition": "A.id = B.id",
    "left": {"type": "Scan", "table": "B"},
    "right": {"type": "Scan", "table": "A"}
}

rules = ["commute_join", "associate_join", "push_filter", "project_merge"]

# -------------------------
# Step 2: Create LLM Prompt
# -------------------------
prompt_template = f"""
You are given two relational algebra trees planA and planB, and a set of allowed rules.
Your task:
1. Identify potential equivalence patterns between planA and planB.
2. Suggest a minimal sequence of transformations to convert planA into planB.
3. Only use the allowed rules: {json.dumps(rules)}.
4. Output strictly in JSON format as a list of transformations.

planA: {json.dumps(planA)}
planB: {json.dumps(planB)}

Output example:
{{
  "transformations": [
    {{"rule": "commute_join", "target_node": "root_join"}}
  ]
}}
"""

# -------------------------
# Step 3: Load Local LLM
# -------------------------
model = GPT4All("gpt4all-lora-quantized.bin")  # replace with your model path

# -------------------------
# Step 4: Generate Transformations
# -------------------------
response = model.generate(prompt_template)

# -------------------------
# Step 5: Print Machine-Readable JSON
# -------------------------
try:
    # Sometimes LLM outputs text; try parsing JSON
    transformations = json.loads(response)
except json.JSONDecodeError:
    # fallback: print raw response
    transformations = response

print(json.dumps(transformations, indent=2))
