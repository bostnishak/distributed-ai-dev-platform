"""Benchmark question definitions for capability evaluation.

Each benchmark has: id, dimension, question, and dimension-specific scoring data.
Dimensions: coding, reasoning, context, structured_output, speed.
"""

from __future__ import annotations

import json
import secrets

from prompt_loader import load_prompt
from sandbox import runner

# ---------------------------------------------------------------------------
# Benchmark definitions
# ---------------------------------------------------------------------------

BENCHMARKS: list[dict] = [
    # --- coding (5 questions) -----------------------------------------------
    {
        "id": "c1",
        "dimension": "coding",
        "question": (
            "Write a Python function named add_numbers(a, b) that returns the sum of two numbers. "
            "Output only the function definition."
        ),
        "test_code": "assert add_numbers(2, 3) == 5\nassert add_numbers(-1, 1) == 0\nassert add_numbers(0, 0) == 0",
        "max_score": 20,
    },
    {
        "id": "c2",
        "dimension": "coding",
        "question": (
            "Write a Python function named is_palindrome(s) that returns True if the string s is a "
            "palindrome (ignoring case and spaces), False otherwise. Output only the function definition."
        ),
        "test_code": (
            "assert is_palindrome('racecar') == True\n"
            "assert is_palindrome('hello') == False\n"
            "assert is_palindrome('A man a plan a canal Panama'.replace(' ', '')) == True"
        ),
        "max_score": 20,
    },
    {
        "id": "c3",
        "dimension": "coding",
        "question": (
            "Write a Python function named flatten(lst) that takes a nested list and returns a flat list. "
            "Example: flatten([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]. "
            "Output only the function definition."
        ),
        "test_code": (
            "assert flatten([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]\n"
            "assert flatten([]) == []\n"
            "assert flatten([[1, 2], [3]]) == [1, 2, 3]"
        ),
        "max_score": 20,
    },
    {
        "id": "c4",
        "dimension": "coding",
        "question": (
            "Write a Python function named count_words(text) that returns a dictionary with word "
            "frequencies (case-insensitive). Output only the function definition."
        ),
        "test_code": (
            "result = count_words('Hello world hello')\n"
            "assert result.get('hello') == 2\n"
            "assert result.get('world') == 1"
        ),
        "max_score": 20,
    },
    {
        "id": "c5",
        "dimension": "coding",
        "question": (
            "Write a Python function named binary_search(arr, target) that performs binary search and "
            "returns the index of target in sorted list arr, or -1 if not found. "
            "Output only the function definition."
        ),
        "test_code": (
            "assert binary_search([1, 3, 5, 7, 9], 5) == 2\n"
            "assert binary_search([1, 3, 5, 7, 9], 4) == -1\n"
            "assert binary_search([], 1) == -1"
        ),
        "max_score": 20,
    },
    # --- reasoning (5 questions) --------------------------------------------
    {
        "id": "r1",
        "dimension": "reasoning",
        "question": "A farmer has 17 sheep. All but 9 die. How many sheep does the farmer have left? Answer with only the number.",
        "expected_substring": "9",
        "max_score": 20,
    },
    {
        "id": "r2",
        "dimension": "reasoning",
        "question": (
            "If you have a 3-litre jug and a 5-litre jug, how many litres can you measure exactly "
            "using these two jugs? List all possible exact amounts separated by commas. "
            "Answer with only the numbers."
        ),
        "expected_substring": "1",
        "max_score": 20,
    },
    {
        "id": "r3",
        "dimension": "reasoning",
        "question": (
            "A train travels at 60 km/h for 2 hours, then at 90 km/h for 1 hour. "
            "What is the total distance in km? Answer with only the number."
        ),
        "expected_substring": "210",
        "max_score": 20,
    },
    {
        "id": "r4",
        "dimension": "reasoning",
        "question": (
            "There are 5 red balls and 3 blue balls in a bag. "
            "What is the probability of drawing a red ball? "
            "Express as a fraction in the form a/b. Answer with only the fraction."
        ),
        "expected_substring": "5/8",
        "max_score": 20,
    },
    {
        "id": "r5",
        "dimension": "reasoning",
        "question": (
            "If today is Wednesday and you have a meeting in 10 days, what day of the week is the meeting? "
            "Answer with only the day name."
        ),
        "expected_substring": "saturday",
        "max_score": 20,
    },
    # --- context (5 questions) ----------------------------------------------
    {
        "id": "x1",
        "dimension": "context",
        "question": load_prompt("b2_bench_x1.txt"),
        "expected_fact": "27 tonnes",
        "max_score": 20,
    },
    {
        "id": "x2",
        "dimension": "context",
        "question": load_prompt("b2_bench_x2.txt"),
        "expected_fact": "17",
        "max_score": 20,
    },
    {
        "id": "x3",
        "dimension": "context",
        "question": load_prompt("b2_bench_x3.txt"),
        "expected_fact": "15.3",
        "max_score": 20,
    },
    {
        "id": "x4",
        "dimension": "context",
        "question": load_prompt("b2_bench_x4.txt"),
        "expected_fact": "4",
        "max_score": 20,
    },
    {
        "id": "x5",
        "dimension": "context",
        "question": load_prompt("b2_bench_x5.txt"),
        "expected_fact": "12",
        "max_score": 20,
    },
    # --- structured_output (5 questions) ------------------------------------
    {
        "id": "s1",
        "dimension": "structured_output",
        "question": (
            "Return a JSON object with exactly these fields: "
            '{"name": "Alice", "age": 30, "active": true}. '
            "Output only valid JSON, nothing else."
        ),
        "required_fields": ["name", "age", "active"],
        "max_score": 20,
    },
    {
        "id": "s2",
        "dimension": "structured_output",
        "question": (
            "Return a JSON array of 3 objects, each with fields 'id' (integer) and 'value' (string). "
            "Output only valid JSON, nothing else."
        ),
        "required_fields": ["id", "value"],
        "expect_array": True,
        "max_score": 20,
    },
    {
        "id": "s3",
        "dimension": "structured_output",
        "question": (
            'Return a JSON object with field "items" containing an array of strings: '
            '["apple", "banana", "cherry"]. Output only valid JSON, nothing else.'
        ),
        "required_fields": ["items"],
        "max_score": 20,
    },
    {
        "id": "s4",
        "dimension": "structured_output",
        "question": (
            "Return a JSON object representing a person with fields: "
            '"first_name" (string), "last_name" (string), "birth_year" (integer), '
            '"email" (string). Use any realistic values. Output only valid JSON, nothing else.'
        ),
        "required_fields": ["first_name", "last_name", "birth_year", "email"],
        "max_score": 20,
    },
    {
        "id": "s5",
        "dimension": "structured_output",
        "question": (
            "Return a JSON object with a 'status' field set to 'ok' and a 'count' field set to 42. "
            "Output only valid JSON, nothing else."
        ),
        "required_fields": ["status", "count"],
        "max_score": 20,
    },
    # --- speed (5 questions: these are answered quickly and scored by tokens/s) ---
    {
        "id": "sp1",
        "dimension": "speed",
        "question": "What is 2 + 2? Answer with only the number.",
        "max_score": 20,
    },
    {
        "id": "sp2",
        "dimension": "speed",
        "question": "What color is the sky on a clear day? Answer in one word.",
        "max_score": 20,
    },
    {
        "id": "sp3",
        "dimension": "speed",
        "question": "What is the capital of France? Answer in one word.",
        "max_score": 20,
    },
    {
        "id": "sp4",
        "dimension": "speed",
        "question": "How many days are in a week? Answer with only the number.",
        "max_score": 20,
    },
    {
        "id": "sp5",
        "dimension": "speed",
        "question": "What is the boiling point of water in Celsius? Answer with only the number.",
        "max_score": 20,
    },
]

# Index by id for quick lookup
BENCHMARK_BY_ID: dict[str, dict] = {b["id"]: b for b in BENCHMARKS}

# Group by dimension
BENCHMARKS_BY_DIMENSION: dict[str, list[dict]] = {}
for _b in BENCHMARKS:
    BENCHMARKS_BY_DIMENSION.setdefault(_b["dimension"], []).append(_b)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_response(benchmark: dict, response: str, tokens_per_second: float | None = None) -> tuple[float, dict]:
    """Score a model response against a benchmark. Returns (score, details)."""
    dimension = benchmark["dimension"]
    max_score = benchmark["max_score"]
    details: dict = {"dimension": dimension, "benchmark_id": benchmark["id"]}

    if dimension == "coding":
        score, details = _score_coding(benchmark, response, max_score, details)
    elif dimension == "reasoning":
        score, details = _score_reasoning(benchmark, response, max_score, details)
    elif dimension == "context":
        score, details = _score_context(benchmark, response, max_score, details)
    elif dimension == "structured_output":
        score, details = _score_structured(benchmark, response, max_score, details)
    elif dimension == "speed":
        score, details = _score_speed(tokens_per_second, max_score, details)
    else:
        score = 0.0
        details["error"] = f"Unknown dimension: {dimension}"

    return score, details


def _score_coding(benchmark: dict, response: str, max_score: float, details: dict) -> tuple[float, dict]:
    """Run the answered code and the benchmark's checks inside the isolated container, never in this process.

    The answer comes from whichever machine the task was given to: it is untrusted code.
    """
    marker = f"__gecti_{secrets.token_hex(8)}__"
    script = "\n".join([_strip_code_fences(response), "", benchmark.get("test_code", ""), "", f"print({marker!r})"])
    done = runner.run_python_code(script)
    if not done.get("docker_available", True):
        details["error"] = "Not graded: the isolated container is not available, and answered code is never run outside it."
        return 0.0, details
    if done.get("ok") and marker in str(done.get("stdout", "")):
        details["passed"] = True
        return float(max_score), details
    last = (str(done.get("stderr", "")).strip().splitlines() or ["no output"])[-1][:300]
    details["error"] = f"Test assertion failed: {last}" if "AssertionError" in last else f"Code failed to execute: {last}"
    return 0.0, details


def _score_reasoning(benchmark: dict, response: str, max_score: float, details: dict) -> tuple[float, dict]:
    expected = benchmark.get("expected_substring", "").lower()
    answer = response.strip().lower()
    if expected and expected in answer:
        details["passed"] = True
        return float(max_score), details
    details["expected"] = expected
    details["got"] = answer[:200]
    return 0.0, details


def _score_context(benchmark: dict, response: str, max_score: float, details: dict) -> tuple[float, dict]:
    fact = benchmark.get("expected_fact", "").lower()
    answer = response.strip().lower()
    if fact and fact in answer:
        details["passed"] = True
        return float(max_score), details
    details["expected_fact"] = fact
    details["got"] = answer[:200]
    return 0.0, details


def _score_structured(benchmark: dict, response: str, max_score: float, details: dict) -> tuple[float, dict]:
    raw = _strip_code_fences(response).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        details["error"] = f"Invalid JSON: {exc}"
        return 0.0, details

    required = benchmark.get("required_fields", [])
    expect_array = benchmark.get("expect_array", False)

    if expect_array:
        if not isinstance(parsed, list) or len(parsed) == 0:
            details["error"] = "Expected a non-empty JSON array"
            return 0.0, details
        # Check each element has required fields
        for item in parsed:
            if not isinstance(item, dict):
                details["error"] = "Array elements must be objects"
                return 0.0, details
            missing = [f for f in required if f not in item]
            if missing:
                details["error"] = f"Missing fields: {missing}"
                return 0.0, details
    else:
        if not isinstance(parsed, dict):
            details["error"] = "Expected a JSON object"
            return 0.0, details
        missing = [f for f in required if f not in parsed]
        if missing:
            details["error"] = f"Missing fields: {missing}"
            return 0.0, details

    details["passed"] = True
    return float(max_score), details


def _score_speed(tokens_per_second: float | None, max_score: float, details: dict) -> tuple[float, dict]:
    """Score speed dimension based on tokens per second. 50 t/s = full score."""
    if tokens_per_second is None or tokens_per_second <= 0:
        details["error"] = "No tokens_per_second measurement"
        return 0.0, details
    # Linear scale: 0 t/s → 0, 50+ t/s → max_score
    score = min(float(max_score), (tokens_per_second / 50.0) * max_score)
    details["tokens_per_second"] = tokens_per_second
    details["passed"] = True
    return score, details


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```python ... ``` or ``` ... ```)."""
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)


def aggregate_dimension_scores(raw_scores: list[tuple[str, float, float]]) -> dict[str, float]:
    """
    Aggregate multiple raw scores per dimension into a 0-100 score per dimension.
    raw_scores: list of (dimension, score, max_score)
    """
    totals: dict[str, list] = {}
    for dim, score, max_score in raw_scores:
        totals.setdefault(dim, [0.0, 0.0])
        totals[dim][0] += score
        totals[dim][1] += max_score
    return {
        dim: round((earned / total * 100) if total > 0 else 0.0, 1)
        for dim, (earned, total) in totals.items()
    }
