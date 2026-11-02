"""Benchmark question definitions for capability evaluation.

Each benchmark has: id, dimension, question, and dimension-specific scoring data.
Dimensions: coding, reasoning, context, structured_output, speed.
"""

from __future__ import annotations

import ast
import json
import textwrap

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
        "question": textwrap.dedent("""\
            Read the following passage carefully and answer the question at the end.

            The history of computing is rich and fascinating. Charles Babbage designed the first mechanical
            computer, the Difference Engine, in 1822. Ada Lovelace, often called the first programmer,
            wrote algorithms for this machine. The first electronic digital computer, ENIAC, was completed
            in 1945 at the University of Pennsylvania and weighed about 27 tonnes. It could perform around
            5,000 additions per second. Grace Hopper invented the first compiler in 1952 and popularized
            the idea of machine-independent programming languages. The transistor, invented at Bell Labs
            in 1947, replaced vacuum tubes and made computers smaller and more reliable. In 1971, Intel
            released the first commercial microprocessor, the Intel 4004, which contained 2,300 transistors.
            The personal computer revolution began in the late 1970s with machines like the Apple II and
            the Altair 8800. Tim Berners-Lee invented the World Wide Web in 1989 while working at CERN in
            Switzerland. The key fact embedded in this passage is: the ENIAC weighed exactly 27 tonnes.
            The first search engine, Archie, was created in 1990 at McGill University in Montreal.
            Today, modern processors contain billions of transistors and can perform trillions of operations
            per second, a testament to the exponential growth described by Moore's Law.

            Question: How much did the ENIAC weigh? Answer with only the weight including units.\
        """),
        "expected_fact": "27 tonnes",
        "max_score": 20,
    },
    {
        "id": "x2",
        "dimension": "context",
        "question": textwrap.dedent("""\
            Read the following text and answer the question.

            Software engineering practices have evolved significantly since the 1960s. Waterfall
            methodology was formalized by Winston Royce in 1970, though he actually argued against
            its pure application. The Agile Manifesto was published in February 2001 by seventeen
            software developers meeting in Snowbird, Utah. It emphasized individuals and interactions,
            working software, customer collaboration, and responding to change. Extreme Programming (XP)
            was developed by Kent Beck in the late 1990s. Scrum, developed by Ken Schwaber and Jeff
            Sutherland, uses fixed-length iterations called sprints typically lasting two to four weeks.
            The specific embedded fact in this text: the Agile Manifesto was signed by exactly seventeen
            developers. DevOps emerged as a practice around 2008-2009, combining development and
            operations teams. Continuous Integration was pioneered by Grady Booch and later formalized
            as a practice by Kent Beck. Infrastructure as Code became popular with tools like Chef,
            released in 2009, and Puppet, which appeared in 2005. Kubernetes, an open-source container
            orchestration system, was released by Google in 2014.

            Question: How many developers signed the Agile Manifesto? Answer with only the number.\
        """),
        "expected_fact": "17",
        "max_score": 20,
    },
    {
        "id": "x3",
        "dimension": "context",
        "question": textwrap.dedent("""\
            Read the following passage and answer the question at the end.

            Machine learning has transformed many fields over the past decade. The term 'artificial
            intelligence' was coined by John McCarthy in 1956 at the Dartmouth Conference. Early AI
            systems used rule-based approaches and expert systems. The backpropagation algorithm,
            crucial for training neural networks, was popularized by Rumelhart, Hinton and Williams
            in 1986. Support Vector Machines were introduced by Vapnik and Cortes in 1995. Deep learning
            gained prominence when AlexNet won the ImageNet competition in 2012 with a top-5 error rate
            of 15.3 percent. The specific fact hidden in this document: AlexNet achieved a top-5 error
            rate of exactly 15.3 percent. The transformer architecture, introduced in the paper
            'Attention Is All You Need' in 2017 by Vaswani et al., revolutionized natural language
            processing. GPT-3, released by OpenAI in 2020, has 175 billion parameters. Large language
            models have since become central to modern AI applications in code generation, summarization,
            and dialogue systems.

            Question: What was AlexNet's top-5 error rate at ImageNet? Answer with only the percentage value (e.g. '15.3 percent').\
        """),
        "expected_fact": "15.3",
        "max_score": 20,
    },
    {
        "id": "x4",
        "dimension": "context",
        "question": textwrap.dedent("""\
            Read the following text and answer the question.

            The Internet has a fascinating history. ARPANET, the precursor to the Internet, was
            created in 1969 by the US Department of Defense. The first email was sent by Ray Tomlinson
            in 1971. He chose the @ symbol to separate the user name from the host name. The TCP/IP
            protocol suite was developed by Vint Cerf and Bob Kahn in 1974. Domain Name System (DNS)
            was designed by Paul Mockapetris in 1983. The key statistic embedded here: there were
            exactly 4 computers connected to ARPANET when it first launched in 1969. The HTTP protocol
            was defined by Tim Berners-Lee in 1989-1991. IPv4 addresses are 32 bits long, allowing
            approximately 4.3 billion unique addresses. IPv6 uses 128-bit addresses to provide a
            vastly larger address space. The first commercial Internet service provider, The World,
            started providing dial-up access in 1989 in the United States.

            Question: How many computers were connected to ARPANET when it first launched? Answer with only the number.\
        """),
        "expected_fact": "4",
        "max_score": 20,
    },
    {
        "id": "x5",
        "dimension": "context",
        "question": textwrap.dedent("""\
            Read the following passage and answer the question.

            Database management systems have a rich history. Edgar Codd introduced the relational model
            in his 1970 paper 'A Relational Model of Data for Large Shared Data Banks'. Oracle was
            founded in 1977 by Larry Ellison, Bob Miner and Ed Oates. IBM released DB2 in 1983.
            MySQL was created by Michael Widenius and David Axmark in 1995 and released as open source.
            PostgreSQL evolved from POSTGRES, developed at the University of California, Berkeley.
            The embedded key number in this text: Edgar Codd proposed exactly 12 rules for relational
            databases (also known as Codd's 12 rules, published in 1985). NoSQL databases gained
            popularity around 2009 with systems like MongoDB, CouchDB and Cassandra. Redis, an
            in-memory data structure store, was created by Salvatore Sanfilippo in 2009. The CAP
            theorem, formulated by Eric Brewer in 2000, states that a distributed system cannot
            simultaneously provide consistency, availability and partition tolerance.

            Question: How many rules did Edgar Codd propose for relational databases? Answer with only the number.\
        """),
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
    """Execute the function definition and run test cases."""
    # Extract code (strip markdown fences if present)
    code = _strip_code_fences(response)
    namespace: dict = {}
    try:
        exec(code, namespace)  # noqa: S102
    except Exception as exc:
        details["error"] = f"Code failed to execute: {exc}"
        return 0.0, details

    test_code = benchmark.get("test_code", "")
    try:
        exec(test_code, namespace)  # noqa: S102
        details["passed"] = True
        return float(max_score), details
    except AssertionError as exc:
        details["error"] = f"Test assertion failed: {exc}"
        return 0.0, details
    except Exception as exc:
        details["error"] = f"Test execution error: {exc}"
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
