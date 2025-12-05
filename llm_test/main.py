import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Any, Dict
import json
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from .llm_client import LLMClient
from .transforms import ra_equal

load_dotenv()

app = FastAPI()
hf = LLMClient()  # Uses GEMINI_API_KEY from .env

# Serve frontend files
app.mount("/static", StaticFiles(directory="static"), name="static")

# --------------------------
# FULL VOCAB (all rules)
# --------------------------
VOCAB = [
    # Existing rules
    "FilterProjectTranspose",
    "JoinCommute",
    "ProjectPushdown",
    "FilterPushdown",
    "AddFilter",
    "RemoveFilter",
    "JoinReorder",
    "ProjectionMerge",
    "FilterMerge",
    "RenameColumns",
    "AggregatePushdown",

    # Additional Calcite rules
    # Filter transformations
    "FilterJoinRule",
    "FilterSortTransposeRule",
    "FilterSampleTransposeRule",
    "FilterSetOpTransposeRule",

    # Project transformations
    "ProjectJoinTransposeRule",
    "ProjectMergeRule",
    "ProjectRemoveRule",
    "ProjectTableScanRule",
    "ProjectSetOpTransposeRule",

    # Join transformations
    "JoinToMultiJoinRule",
    "JoinToSemiJoinRule",
    "JoinToCorrelateRule",
    "JoinToUnionRule",

    # Aggregate transformations
    "AggregateJoinTransposeRule",
    "AggregateFilterTransposeRule",
    "AggregateExpandDistinctAggregatesRule",
    "AggregateExpandWithinDistinctRule",
    "AggregateExtractProjectRule",

    # Sort transformations
    "SortProjectTransposeRule",
    "SortRemoveRule",
    "SortLimitTransposeRule",

    # Miscellaneous transformations
    "ProjectToWindowRule",
    "WindowToProjectRule",
    "FilterToCalcRule",
    "CalcToWindowRule",
    "UnionToDistinctRule"
]

class LLMRequest(BaseModel):
    source: Dict[str, Any]
    target: Dict[str, Any]

# ------------------------------------
# FRONTEND ENTRY POINT (index.html)
# ------------------------------------
@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read(), status_code=200)

# ------------------------------------
# API: Check RA Equivalence
# ------------------------------------
@app.post("/check_equivalence")
async def check_equivalence(req: LLMRequest):

    # 1. Quick check
    if ra_equal(req.source, req.target):
        return {
            "potential_equivalence": "yes",
            "trace": [],
            "llm": {
                "sequence": [],
                "score": 1.0,
                "notes": "SOURCE_RA and TARGET_RA are identical."
            }
        }

    # 2. Get LLM output
    try:
        llm_resp_text = await hf.ask(req.source, req.target, VOCAB)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not llm_resp_text or llm_resp_text == "no_output":
        return {
            "potential_equivalence": "no",
            "trace": [],
            "llm": "LLM returned no output"
        }

    # 3. Safely clean model output
    cleaned = (
        llm_resp_text.replace("```json", "")
                     .replace("```", "")
                     .strip()
    )

    # 4. Parse JSON
    try:
        parsed = json.loads(cleaned)
    except Exception:
        return {
            "potential_equivalence": "no",
            "trace": [],
            "llm": cleaned,
            "notes": "Invalid JSON from LLM"
        }

    return {
        "llm": parsed,
        "potential_equivalence": "yes" if parsed.get("sequence") else "no",
        "trace": [req.source]
    }
