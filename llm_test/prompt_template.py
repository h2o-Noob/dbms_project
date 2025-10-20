# file: prompt_template.py
PROMPT_PREFIX = """You are a constrained RA transformer finder. Inputs:
1) SOURCE_RA: JSON canonical RA tree
2) TARGET_RA: JSON canonical RA tree
3) VOCAB: JSON list of allowed transformation names

Output a JSON object with exactly this schema:
{
  "sequence": [
    {
      "step_id": integer,
      "rule": string,
      "node_id": string,
      "params": object,
      "explanation": string
    }
  ],
  "score": float,
  "notes": string
}

Constraints:
- Use only rules present in VOCAB.
- Prefer sequences of length <= 6.
- Output only valid JSON and nothing else.
"""
