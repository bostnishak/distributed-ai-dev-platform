"""Task classification weights for agent selection.

Each task type has a weight vector over capability dimensions.
Weights sum to 1.0 for each task type (speed weight is intentionally 0 for most tasks).
"""

DIMENSIONS = ["coding", "reasoning", "context", "structured_output", "speed"]

WEIGHTS: dict[str, dict[str, float]] = {
    "requirements_analysis": {
        "coding": 0.05,
        "reasoning": 0.35,
        "context": 0.50,
        "structured_output": 0.10,
        "speed": 0.00,
    },
    "database_schema": {
        "coding": 0.50,
        "reasoning": 0.30,
        "context": 0.10,
        "structured_output": 0.10,
        "speed": 0.00,
    },
    "backend": {
        "coding": 0.60,
        "reasoning": 0.20,
        "context": 0.10,
        "structured_output": 0.10,
        "speed": 0.00,
    },
    "frontend": {
        "coding": 0.60,
        "reasoning": 0.15,
        "context": 0.20,
        "structured_output": 0.05,
        "speed": 0.00,
    },
    "testing": {
        "coding": 0.55,
        "reasoning": 0.35,
        "context": 0.05,
        "structured_output": 0.05,
        "speed": 0.00,
    },
    "code_review": {
        "coding": 0.40,
        "reasoning": 0.40,
        "context": 0.15,
        "structured_output": 0.05,
        "speed": 0.00,
    },
    "integration": {
        "coding": 0.50,
        "reasoning": 0.30,
        "context": 0.15,
        "structured_output": 0.05,
        "speed": 0.00,
    },
    "documentation": {
        "coding": 0.10,
        "reasoning": 0.25,
        "context": 0.55,
        "structured_output": 0.10,
        "speed": 0.00,
    },
    "benchmark": {
        "coding": 0.00,
        "reasoning": 0.00,
        "context": 0.00,
        "structured_output": 0.00,
        "speed": 0.00,
    },
}

# Fallback weights for unknown task types (balanced across coding, reasoning, context)
DEFAULT_WEIGHTS: dict[str, float] = {
    "coding": 0.40,
    "reasoning": 0.30,
    "context": 0.20,
    "structured_output": 0.10,
    "speed": 0.00,
}


def get_weights(task_type: str) -> dict[str, float]:
    """Return weight vector for a task type, falling back to defaults."""
    return WEIGHTS.get(task_type, DEFAULT_WEIGHTS)
