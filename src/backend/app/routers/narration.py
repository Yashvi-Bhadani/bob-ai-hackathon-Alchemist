"""
Bob Narration Router
Member 3 — feature/dashboard
"""

from __future__ import annotations

from fastapi import APIRouter

from app.services import bob_service
from app.models import NarrationRequest, NarrationResponse

router = APIRouter()


@router.post("/", response_model=NarrationResponse,
             summary="Ask Bob to explain a risk analysis result in natural language")
async def get_narration(request: NarrationRequest):
    """
    Sends structured analysis results to IBM Bob (watsonx.ai Granite) for
    natural-language explanation.

    If Bob is unavailable (no credentials, network failure, quota),
    a deterministic template narration is returned automatically.
    The `is_fallback` field in the response indicates which mode was used.

    Context types:
    - BOTTLENECK  — explain bottleneck scores
    - OUTAGE      — write an outage decision brief
    - SUPPLY_RISK — summarise supply chain risk
    - COMBINED    — executive combined risk brief with recommendation rationale
    """
    result = await bob_service.narrate(
        request.context_type.upper(),
        request.context_data,
    )
    return NarrationResponse(
        context_type=result["context_type"],
        narration_text=result["text"],
        is_fallback=result["is_fallback"],
        model_used=result["model_used"],
        prompt_hash=result["prompt_hash"],
    )
