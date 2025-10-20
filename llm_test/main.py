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


app = FastAPI()
hf = LLMClient()  # will now use GEMINI_API_KEY from .env

VOCAB = ["FilterProjectTranspose","JoinCommute","ProjectPushdown"]

class RATree(BaseModel):
    tree: Dict[str, Any]

class LLMRequest(BaseModel):
    source: Dict[str, Any]
    target: Dict[str, Any]

@app.post("/suggest")
async def suggest(req: LLMRequest):
    try:
        resp = await hf.ask(req.source, req.target, VOCAB)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if resp == "no_output":
        resp = "LLM returned no output"

    return {"llm": resp}

@app.post("/verify")
async def verify(req: LLMRequest, llm_proposal: Dict[str, Any] = None):
    if llm_proposal is None:
        return {"error":"llm_proposal_missing"}
    seq = llm_proposal.get("sequence",[])
    r = apply_sequence(req.source, seq, VOCAB)
    if not r.get("ok"):
        return {"verified": False, "reason": r.get("error"), "trace": r.get("trace")}
    final = r.get("final")
    eq = ra_equal(final, req.target)
    return {"verified": bool(eq), "final": final, "target": req.target, "trace": r.get("trace")}

@app.post("/check")
async def check(req: LLMRequest):
    try:
        llm_resp = await hf.ask(req.source, req.target, VOCAB)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if llm_resp == "no_output":
        llm_resp = "LLM returned no output"

    # Skip sequence application since we are just returning raw LLM output
    return {"llm": llm_resp, "verified": None, "final": None, "trace": None}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
