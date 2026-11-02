"""Agent selection algorithm for task assignment.

Selects the best available agent for a task based on:
- Capability scores weighted by task type
- Context window penalty (task needs more tokens than agent has)
- Load penalty (agent is busy)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from task_weights import get_weights

# Penalty applied when the agent is busy (heartbeat_status == 'busy')
LOAD_PENALTY = 20.0

# Penalty multiplier when task context tokens exceed agent context_length.
# Score reduced proportionally to how much the agent is over its limit.
CONTEXT_PENALTY_BASE = 30.0

# Agents are considered offline if last_seen_at is older than this
ONLINE_THRESHOLD_SECONDS = 30


def _is_online(agent: dict) -> bool:
    last_seen = agent.get("last_seen_at")
    if not last_seen:
        return False
    try:
        # Parse ISO 8601 timestamp
        ts = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return (datetime.now(UTC) - ts).total_seconds() < ONLINE_THRESHOLD_SECONDS
    except (ValueError, TypeError):
        return False


def score_agent(
    agent: dict,
    scores_by_dim: dict[str, float],
    task_type: str,
    task_context_tokens: int = 0,
) -> tuple[float, dict]:
    """
    Compute a selection score for an agent.

    score = sum(weight_i * capability_i)
            - context_penalty  (task needs more tokens than agent context window)
            - load_penalty     (agent is busy)

    Returns (score, breakdown).
    """
    weights = get_weights(task_type)
    breakdown: dict = {}

    # Weighted capability score
    weighted = 0.0
    for dim, weight in weights.items():
        cap = scores_by_dim.get(dim, 0.0)
        contribution = weight * cap
        weighted += contribution
        breakdown[f"w_{dim}"] = round(contribution, 3)
    breakdown["weighted_capability"] = round(weighted, 3)

    # Context penalty: if task needs more tokens than the agent can handle
    agent_ctx = agent.get("context_length") or 0
    context_penalty = 0.0
    if task_context_tokens > 0 and agent_ctx > 0 and task_context_tokens > agent_ctx:
        # Penalty proportional to how much we exceed the context window
        overflow_ratio = (task_context_tokens - agent_ctx) / agent_ctx
        context_penalty = min(CONTEXT_PENALTY_BASE * overflow_ratio, CONTEXT_PENALTY_BASE)
    elif task_context_tokens > 0 and agent_ctx == 0:
        # Unknown context length: small penalty
        context_penalty = 5.0
    breakdown["context_penalty"] = round(context_penalty, 3)

    # Load penalty: agent is busy
    load_penalty = 0.0
    heartbeat_status = agent.get("heartbeat_status", "idle")
    if heartbeat_status == "busy":
        load_penalty = LOAD_PENALTY
    breakdown["load_penalty"] = round(load_penalty, 3)

    score = weighted - context_penalty - load_penalty
    breakdown["final_score"] = round(score, 3)
    return score, breakdown


def select_agent(
    task_type: str,
    task_context_tokens: int,
    available_agents: list[dict],
    all_scores: dict[str, dict[str, float]],
) -> tuple[str | None, dict]:
    """
    Select the best agent for a task.

    Parameters:
        task_type: string key matching task_weights.WEIGHTS
        task_context_tokens: estimated number of tokens for the task context
        available_agents: list of agent dicts from the database
        all_scores: {agent_id: {dimension: score_0_to_100}}

    Returns:
        (agent_id, reason_dict) or (None, reason_dict) if no agent is available.
    """
    # Filter to online agents only
    online = [a for a in available_agents if _is_online(a)]
    if not online:
        return None, {"reason": "No online agents", "candidates": []}

    candidates = []
    for agent in online:
        agent_id = agent["agent_id"]
        scores = all_scores.get(agent_id, {})
        final_score, breakdown = score_agent(agent, scores, task_type, task_context_tokens)
        breakdown["agent_id"] = agent_id
        breakdown["heartbeat_status"] = agent.get("heartbeat_status", "idle")
        candidates.append((final_score, agent_id, breakdown))

    if not candidates:
        return None, {"reason": "No scoreable candidates"}

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_agent_id, best_breakdown = candidates[0]

    reason = {
        "selected_agent": best_agent_id,
        "score": best_score,
        "breakdown": best_breakdown,
        "all_candidates": [
            {"agent_id": c[1], "score": c[0]} for c in candidates
        ],
    }
    return best_agent_id, reason
