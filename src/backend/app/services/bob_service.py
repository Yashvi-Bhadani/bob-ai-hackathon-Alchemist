"""
Bob Narration Service
=====================
Sends structured JSON context to IBM Bob (watsonx.ai) and returns
a natural-language explanation/decision brief.

If Bob is unavailable (no API key, network error, or quota exceeded),
the service falls back to deterministic template narration so the
application remains fully functional.

Bob usage:
  - Bottleneck explanation
  - Outage decision brief
  - Supply chain risk summary
  - Combined risk summary
  - Recommendation rationale

The prompt is carefully structured so Bob explains the numbers —
Bob does NOT perform the calculations.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BOB_API_URL = os.getenv("BOB_API_URL", "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation")
BOB_API_KEY = os.getenv("BOB_API_KEY", "")
BOB_PROJECT_ID = os.getenv("BOB_PROJECT_ID", "")
BOB_MODEL_ID = os.getenv("BOB_MODEL_ID", "ibm/granite-13b-instruct-v2")
BOB_MAX_TOKENS = int(os.getenv("BOB_MAX_TOKENS", "600"))

_SYSTEM_CONTEXT = (
    "You are the Fab Bottleneck & Supply Chain Risk Advisor, an industrial "
    "intelligence assistant for semiconductor manufacturing operations. "
    "Your role is to explain pre-calculated risk analysis results in clear, "
    "concise professional language. You do NOT perform calculations — the "
    "numbers are provided to you. Focus on: what the numbers mean, why they "
    "matter to operations, and what the recommended actions are. "
    "Be direct, use manufacturing terminology, and keep the response under 250 words."
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _get_iam_token() -> str | None:
    """Exchange IBM Cloud API key for a Bearer token."""
    if not BOB_API_KEY:
        return None
    try:
        resp = httpx.post(
            "https://iam.cloud.ibm.com/identity/token",
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": BOB_API_KEY,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as exc:
        logger.warning("IBM IAM token exchange failed: %s", exc)
        return None


async def call_bob(prompt: str, context_type: str) -> dict[str, Any]:
    """
    Call IBM Bob (watsonx.ai) with the given prompt.
    Returns: {"text": str, "is_fallback": bool, "model_used": str}
    """
    if not BOB_API_KEY or not BOB_PROJECT_ID:
        logger.info("Bob API credentials not configured — using fallback narration.")
        return {"text": _fallback_narration(prompt, context_type), "is_fallback": True, "model_used": "fallback"}

    token = _get_iam_token()
    if not token:
        return {"text": _fallback_narration(prompt, context_type), "is_fallback": True, "model_used": "fallback"}

    full_prompt = f"{_SYSTEM_CONTEXT}\n\n{prompt}"
    payload = {
        "model_id": BOB_MODEL_ID,
        "input": full_prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": BOB_MAX_TOKENS,
            "stop_sequences": [],
            "temperature": 0.3,
        },
        "project_id": BOB_PROJECT_ID,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                BOB_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            generated = data["results"][0]["generated_text"].strip()
            return {"text": generated, "is_fallback": False, "model_used": BOB_MODEL_ID}
    except Exception as exc:
        logger.warning("Bob API call failed: %s — using fallback narration.", exc)
        return {"text": _fallback_narration(prompt, context_type), "is_fallback": True, "model_used": "fallback"}


def build_bottleneck_prompt(data: dict) -> str:
    critical = [t for t in data.get("tools", []) if t.get("is_critical")]
    lines = [
        "=== BOTTLENECK ANALYSIS RESULTS ===",
        f"Total tools analysed: {len(data.get('tools', []))}",
        f"Critical bottlenecks detected: {len(critical)}",
    ]
    for t in data.get("tools", [])[:5]:
        lines.append(
            f"- {t['tool_id']} ({t['process_step']}): "
            f"Utilisation {t['utilization_pct']:.1f}%, "
            f"WIP {t['wip_lots']} lots, "
            f"Score {t['bottleneck_score']:.3f}, "
            f"Critical: {t['is_critical']}"
        )
    lines.append(
        "\nTask: Explain what these bottleneck scores mean for fab operations. "
        "Identify the most critical tool and explain WHY it is a bottleneck "
        "(cite the specific metrics). State the operational risk in plain terms."
    )
    return "\n".join(lines)


def build_outage_prompt(data: dict) -> str:
    return (
        f"=== OUTAGE SIMULATION RESULTS ===\n"
        f"Tool: {data['tool_id']} ({data['process_step']})\n"
        f"Simulated outage duration: {data['outage_hours']} hours\n"
        f"Backlog during outage: {data['outage_backlog_lots']} lots ({data['backlog_wafers']} wafers)\n"
        f"Total backlog to clear: {data['total_backlog_lots']} lots\n"
        f"Recovery time: {data.get('recovery_hours', 'N/A')} hours\n"
        f"Is recoverable within 24h: {data.get('is_recoverable', 'Unknown')}\n"
        f"Downstream steps affected: {len(data.get('downstream_impact', []))}\n"
        f"Downstream detail: {json.dumps(data.get('downstream_impact', [])[:3])}\n"
        f"\nTask: Write a concise decision brief for the fab operations manager. "
        f"Explain the impact of this outage, the recovery challenge, and the "
        f"downstream production risk. Be specific about the numbers."
    )


def build_supply_risk_prompt(data: dict) -> str:
    return (
        f"=== SUPPLY CHAIN RISK ASSESSMENT ===\n"
        f"Material: {data.get('material_id')} — {data.get('material_name', '')}\n"
        f"HHI (supplier concentration): {data.get('hhi_value', 'N/A')} "
        f"(level: {data.get('concentration_level', 'N/A')})\n"
        f"Inventory coverage: {data.get('inventory_coverage_days', 'N/A')} days "
        f"(risk: {data.get('inventory_risk_tier', 'N/A')})\n"
        f"Single Point of Failure: {data.get('has_spof', False)}\n"
        f"Geopolitical risk score: {data.get('geopolitical_risk_score', 0):.2f}\n"
        f"Combined supply risk score: {data.get('combined_supply_risk', 0):.3f} "
        f"({data.get('risk_tier', 'N/A')})\n"
        f"\nTask: Write a supply chain risk summary for procurement and operations. "
        f"Explain the main risk drivers, what SPOF means in this context, and "
        f"what the coverage numbers imply for production continuity."
    )


def build_combined_risk_prompt(data: dict) -> str:
    recs = data.get("recommendations", [])
    rec_text = "\n".join(
        f"  {r['priority']}. [{r['category']}] {r['recommendation'][:100]}..."
        for r in recs[:3]
    )
    return (
        f"=== COMBINED RISK ASSESSMENT ===\n"
        f"Tool: {data['tool_id']} ({data.get('process_step', '')})\n"
        f"Manufacturing Risk Score: {data['manufacturing_risk_score']:.3f}\n"
        f"Supply Chain Risk Score: {data['supply_chain_risk_score']:.3f}\n"
        f"Combined Risk Score: {data['combined_risk_score']:.3f} "
        f"({data.get('risk_tier_label', data.get('risk_tier', ''))})\n"
        f"Confidence: {data.get('confidence_pct', 80)}%\n"
        f"\nTop Recommendations:\n{rec_text}\n"
        f"\nTask: Write an executive decision brief (max 200 words) explaining: "
        f"(1) why this risk is at its current level, "
        f"(2) the main risk drivers, "
        f"(3) which recommendation is most urgent and why."
    )


def _fallback_narration(prompt: str, context_type: str) -> str:
    """
    Template-based fallback narration when Bob is unavailable.
    The application must remain functional without Bob.
    """
    templates = {
        "BOTTLENECK": (
            "⚠️ Bottleneck Analysis (Deterministic Report)\n\n"
            "The analysis has identified one or more critical bottleneck tools on the fab floor. "
            "A tool is classified as critical when its composite Bottleneck Score exceeds 0.75, "
            "which occurs when utilisation is high (>85%), WIP queue depth is significant relative "
            "to shift capacity, and capacity pressure is elevated. High utilisation at a single "
            "tool step creates a queue that propagates downstream, increasing cycle time across "
            "the entire production flow. Immediate actions such as rerouting lots to alternate "
            "qualified tools and adjusting lot prioritisation are recommended."
        ),
        "OUTAGE": (
            "⚠️ Outage Impact Brief (Deterministic Report)\n\n"
            "The outage simulation has calculated the backlog accumulation and recovery window "
            "for the specified tool and downtime duration. During the outage period, incoming "
            "lots continue to arrive at the tool queue while processing is halted, creating an "
            "immediate backlog. After the tool returns to service, recovery time is determined "
            "by the net clearance rate — the difference between the tool's maximum processing "
            "rate and the ongoing arrival rate. Downstream process steps that depend on output "
            "from this tool will experience proportional delays, compounding the production impact."
        ),
        "SUPPLY_RISK": (
            "⚠️ Supply Chain Risk Summary (Deterministic Report)\n\n"
            "The supply chain risk assessment has evaluated supplier concentration (HHI), "
            "inventory coverage, single-point-of-failure exposure, and geopolitical risk for "
            "the critical material associated with this tool. A high HHI value indicates that "
            "supply is concentrated in few suppliers, increasing disruption risk. Low inventory "
            "coverage days indicate limited buffer against supply delays. A confirmed SPOF means "
            "that a single supplier disruption could halt production of this material entirely. "
            "Actions: emergency replenishment orders and accelerated second-source qualification "
            "are recommended."
        ),
        "COMBINED": (
            "⚠️ Combined Risk Decision Brief (Deterministic Report)\n\n"
            "The combined risk score integrates manufacturing bottleneck severity with supply "
            "chain vulnerability. A high combined score indicates that the tool faces simultaneous "
            "pressure from both production constraints and material supply risk, creating compounded "
            "exposure. The prioritised mitigation recommendations address: (1) alternative tool "
            "routing to relieve queue pressure, (2) lot scheduling adjustments for HOT-priority "
            "product, (3) emergency inventory replenishment, and (4) long-term supplier "
            "diversification. The most time-sensitive action is the inventory replenishment, "
            "followed by immediate lot rerouting where alternate tools have spare capacity."
        ),
    }
    return templates.get(context_type, templates["COMBINED"])


async def narrate(context_type: str, context_data: dict) -> dict[str, Any]:
    """
    Main entry point for narration requests.
    Builds the appropriate prompt, calls Bob, returns result with fallback flag.
    """
    prompt_builders = {
        "BOTTLENECK": build_bottleneck_prompt,
        "OUTAGE":     build_outage_prompt,
        "SUPPLY_RISK":build_supply_risk_prompt,
        "COMBINED":   build_combined_risk_prompt,
    }
    builder = prompt_builders.get(context_type, build_combined_risk_prompt)
    prompt = builder(context_data)
    result = await call_bob(prompt, context_type)
    result["context_type"] = context_type
    result["prompt_hash"] = _sha256(prompt)
    return result
