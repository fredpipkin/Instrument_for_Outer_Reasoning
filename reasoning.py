# reasoning.py
# Procedural reasoning engine.
#
# Parses a scenario or decision context into structured components.
# Applies bounded analysis operations.
# Updates cognitive state via cost model.
# Produces structured output — not freeform prose.
#
# This module does not generate autonomous thought.
# It applies a fixed sequence of analysis procedures to user-supplied input.
# Output quality degrades when cognitive state variables fall below thresholds.

import re
import time
import math
from typing import Dict, List, Tuple

from config import STATE_FLOOR, STATE_CEILING

# ---------------------------------------------------------------------------
# Keyword lexicons — deterministic classification
# ---------------------------------------------------------------------------

_DECISION_MARKERS   = {"should", "choose", "decide", "option", "between",
                        "prefer", "select", "which", "whether", "pick"}
_RISK_MARKERS       = {"risk", "fail", "danger", "threat", "loss", "cost",
                        "wrong", "bad", "uncertain", "unsure", "maybe", "might"}
_CONSTRAINT_MARKERS = {"must", "cannot", "limit", "deadline", "budget",
                        "constraint", "rule", "require", "need", "only"}
_TEMPORAL_MARKERS   = {"urgent", "soon", "immediate", "deadline", "today",
                        "tomorrow", "week", "delay", "time", "when", "schedule"}
_STAKEHOLDER_WORDS  = {"we", "they", "team", "client", "user", "customer",
                        "manager", "board", "partner", "stakeholder", "people"}

# ---------------------------------------------------------------------------
# Complexity scoring
# ---------------------------------------------------------------------------

def _tokenise(text: str) -> List[str]:
    return re.findall(r"\b\w+\b", text.lower())


def _score_complexity(tokens: List[str]) -> Dict[str, float]:
    """
    Returns normalised scores [0.0, 1.0] for each complexity dimension.
    No heuristics — each score is a direct token count ratio.
    """
    total = max(len(tokens), 1)

    decision_score    = min(1.0, sum(1 for t in tokens if t in _DECISION_MARKERS)    / 3)
    risk_score        = min(1.0, sum(1 for t in tokens if t in _RISK_MARKERS)        / 4)
    constraint_score  = min(1.0, sum(1 for t in tokens if t in _CONSTRAINT_MARKERS)  / 3)
    temporal_score    = min(1.0, sum(1 for t in tokens if t in _TEMPORAL_MARKERS)    / 2)
    stakeholder_score = min(1.0, sum(1 for t in tokens if t in _STAKEHOLDER_WORDS)   / 4)
    length_score      = min(1.0, total / 80)

    return {
        "decision_complexity":    round(decision_score,    3),
        "risk_exposure":          round(risk_score,        3),
        "constraint_density":     round(constraint_score,  3),
        "temporal_pressure":      round(temporal_score,    3),
        "stakeholder_breadth":    round(stakeholder_score, 3),
        "input_volume":           round(length_score,      3),
    }


def _classify_scenario(scores: Dict[str, float]) -> str:
    """Classify the dominant scenario type from complexity scores."""
    candidates = [
        ("DECISION",    scores["decision_complexity"]),
        ("RISK",        scores["risk_exposure"]),
        ("CONSTRAINT",  scores["constraint_density"]),
        ("TEMPORAL",    scores["temporal_pressure"]),
        ("STAKEHOLDER", scores["stakeholder_breadth"]),
    ]
    dominant = max(candidates, key=lambda x: x[1])
    if dominant[1] < 0.1:
        return "OBSERVATION"
    return dominant[0]


# ---------------------------------------------------------------------------
# State cost model
# How much each analysis operation costs per cognitive variable
# ---------------------------------------------------------------------------

_ANALYSIS_COST = {
    "parse":     {"LAT": +0.02, "ATTN": -0.03, "MEM": -0.01, "DRIFT": +0.01, "EXT": 0.0},
    "classify":  {"LAT": -0.01, "ATTN": -0.02, "MEM": -0.01, "DRIFT": +0.01, "EXT": 0.0},
    "evaluate":  {"LAT": -0.03, "ATTN": -0.04, "MEM": -0.02, "DRIFT": +0.02, "EXT": +0.01},
    "recommend": {"LAT": -0.05, "ATTN": -0.03, "MEM": -0.02, "DRIFT": +0.02, "EXT": +0.02},
}


# ---------------------------------------------------------------------------
# Recommendation generation — bounded by state health
# ---------------------------------------------------------------------------

def _state_health(state: Dict[str, float]) -> float:
    """
    Composite health score [0.0, 1.0].
    Weighted: ATTN and MEM contribute most, DRIFT and EXT penalise.
    """
    return round(
        0.30 * state.get("ATTN", 0.9)
      + 0.25 * state.get("MEM",  0.9)
      + 0.20 * (1.0 - state.get("DRIFT", 0.05))
      + 0.15 * (1.0 - state.get("LAT",   0.10))
      + 0.10 * (1.0 - state.get("EXT",   0.00)),
        3
    )


def _confidence(health: float, complexity: float) -> float:
    """Confidence degrades with health loss and complexity increase."""
    return round(max(0.0, min(1.0, health * (1.0 - 0.4 * complexity))), 3)


def _generate_recommendations(
    scenario_type: str,
    scores: Dict[str, float],
    state: Dict[str, float],
    health: float,
    confidence: float,
) -> List[Dict]:
    """
    Generate between 1 and 3 recommendations depending on state health.
    Low health → fewer, more conservative outputs.
    """
    recommendations = []
    complexity = sum(scores.values()) / len(scores)

    # Primary recommendation — always generated
    primary = _primary_recommendation(scenario_type, scores, complexity, health)
    primary["confidence"] = confidence
    primary["rank"] = 1
    recommendations.append(primary)

    # Secondary recommendation — only when health above threshold
    if health >= 0.55 and confidence >= 0.45:
        secondary = _secondary_recommendation(scenario_type, scores, complexity)
        secondary["confidence"] = round(confidence * 0.72, 3)
        secondary["rank"] = 2
        recommendations.append(secondary)

    # Tertiary — only at high health
    if health >= 0.75 and confidence >= 0.60:
        tertiary = {
            "action": "DEFER — Gather additional data before committing",
            "rationale": "Sufficient state capacity exists to support extended analysis",
            "confidence": round(confidence * 0.51, 3),
            "rank": 3,
        }
        recommendations.append(tertiary)

    return recommendations


def _primary_recommendation(
    scenario_type: str,
    scores: Dict[str, float],
    complexity: float,
    health: float,
) -> Dict:
    templates = {
        "DECISION": {
            "action": "COMMIT — Select lowest-complexity option with highest constraint satisfaction",
            "rationale": "Decision markers detected. Constraint density favours bounded selection.",
        },
        "RISK": {
            "action": "MITIGATE — Apply conservative path. Reduce exposure before proceeding",
            "rationale": "Risk markers elevated. Recommend staged validation over single commitment.",
        },
        "CONSTRAINT": {
            "action": "REFRAME — Identify which constraints are hard vs soft before analysis",
            "rationale": "Constraint density high. Binary yes/no recommendations premature.",
        },
        "TEMPORAL": {
            "action": "TRIAGE — Separate time-critical actions from deferred decisions",
            "rationale": "Temporal pressure detected. Sequencing required before content analysis.",
        },
        "STAKEHOLDER": {
            "action": "ALIGN — Establish shared definition of success before options evaluation",
            "rationale": "Multiple stakeholder vectors detected. Misalignment will compound error drift.",
        },
        "OBSERVATION": {
            "action": "LOG — Register observation. No decision node detected",
            "rationale": "Input classified as observation. No recommendation warranted.",
        },
    }

    base = templates.get(scenario_type, templates["OBSERVATION"])

    # Degrade recommendation specificity under low health
    if health < 0.40:
        base["action"] = "PAUSE — Cognitive state insufficient for reliable recommendation"
        base["rationale"] = f"State health at {health:.2f}. Output reliability below acceptable threshold."

    return base


def _secondary_recommendation(
    scenario_type: str,
    scores: Dict[str, float],
    complexity: float,
) -> Dict:
    if scores["risk_exposure"] > 0.4:
        return {
            "action": "HEDGE — Maintain reversibility in primary commitment",
            "rationale": "Risk exposure above threshold. Preserve optionality.",
        }
    if scores["temporal_pressure"] > 0.3:
        return {
            "action": "TIMEBOX — Set explicit decision deadline to prevent drift",
            "rationale": "Temporal pressure detected. Unconstrained analysis increases drift.",
        }
    return {
        "action": "DOCUMENT — Record reasoning chain before acting",
        "rationale": "Complexity score warrants explicit trace for future recall.",
    }


# ---------------------------------------------------------------------------
# Warnings — generated from state thresholds
# ---------------------------------------------------------------------------

def _generate_warnings(state: Dict[str, float], health: float) -> List[str]:
    warnings = []
    if state.get("DRIFT", 0) >= 0.60:
        warnings.append("DRIFT CRITICAL — Output reliability compromised. Review before acting.")
    if state.get("ATTN", 1) <= 0.35:
        warnings.append("ATTN DEGRADED — Attention instability may produce incomplete analysis.")
    if state.get("MEM", 1) <= 0.40:
        warnings.append("MEM DEGRADED — Memory integrity low. Recommendations may omit prior context.")
    if state.get("EXT", 0) >= 0.65:
        warnings.append("EXT HIGH — External reliance elevated. Verify recommendations independently.")
    if health < 0.40:
        warnings.append("STATE HEALTH CRITICAL — All recommendations should be treated as provisional.")
    return warnings


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def analyse(text: str, state: Dict[str, float]) -> Dict:
    """
    Main entry point.
    Receives raw input text and current cognitive state.
    Returns structured analysis result.
    Does not mutate state — returns cost deltas for the engine to apply.

    Steps:
        1. Tokenise and score
        2. Classify scenario type
        3. Compute state health and confidence
        4. Generate recommendations
        5. Compute state costs
        6. Return structured output

    State cost deltas are returned in result['state_deltas'] for the engine to apply.
    Confidence is derived from health and complexity, not from a probabilistic model.
    """
    tokens    = _tokenise(text)
    scores    = _score_complexity(tokens)
    stype     = _classify_scenario(scores)
    complexity = round(sum(scores.values()) / len(scores), 3)
    health    = _state_health(state)
    conf      = _confidence(health, complexity)

    # Accumulate state costs across all analysis steps
    deltas: Dict[str, float] = {k: 0.0 for k in ("LAT", "ATTN", "MEM", "DRIFT", "EXT")}
    steps_run = []

    for step in ("parse", "classify", "evaluate", "recommend"):
        for var, cost in _ANALYSIS_COST[step].items():
            deltas[var] += cost
        steps_run.append(step.upper())

    recommendations = _generate_recommendations(stype, scores, state, health, conf)
    warnings        = _generate_warnings(state, health)

    return {
        "scenario_type":   stype,
        "complexity":      complexity,
        "scores":          scores,
        "state_health":    health,
        "confidence":      conf,
        "steps":           steps_run,
        "recommendations": recommendations,
        "warnings":        warnings,
        "state_deltas":    {k: round(v, 4) for k, v in deltas.items()},
        "token_count":     len(tokens),
        "timestamp":       time.time(),
    }
