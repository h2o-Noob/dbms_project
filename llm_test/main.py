# file: main.py
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List
import os
from dotenv import load_dotenv
load_dotenv()
from .llm_client import LLMClient
from .transforms import apply_sequence, ra_equal
import json


app = FastAPI()
hf = LLMClient()  # will now use GEMINI_API_KEY from .env

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


class RATree(BaseModel):
    tree: Dict[str, Any]

class LLMRequest(BaseModel):
    source: Dict[str, Any]
    target: Dict[str, Any]


@app.post("/check_equivalence")
async def check_equivalence(req: LLMRequest):
    # 1. Quick equivalence check
    if ra_equal(req.source, req.target):
        return {
            "potential_equivalence": "yes",
            "trace": [],
            "llm": {"sequence": [], "score": 1.0, "notes": "SOURCE_RA and TARGET_RA are identical."}
        }

    # 2. Ask LLM for a suggested transformation
    try:
        llm_resp_text = await hf.ask(req.source, req.target, VOCAB)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if llm_resp_text == "no_output":
        llm_resp_text = "LLM returned no output"

    # 3. Parse LLM JSON safely
    try:
        parsed = json.loads(llm_resp_text.strip("```json").strip("```"))
    except Exception:
        return {"llm": llm_resp_text, "potential_equivalence": "no", "trace": "invalid LLM JSON"}

    # 4. Return LLM suggestion with potential equivalence flag
    return {
        "llm": parsed,
        "potential_equivalence": "yes" if parsed.get("sequence") else "no",
        "trace": [req.source]  # Keep original source RA as trace for context
    }



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
