# The team's six models — spot checks

Measured on 4 October 2026 on the master computer:

- Ollama 0.35.0 on the NVIDIA RTX 4060 Laptop GPU (8 GB)
- `think: false`, temperature 0
- one run per check

These are quick checks, not a benchmark. The capability evaluation in Sprint 2 (PB-21 benchmark sets, PB-22 evaluation runner) measures the models properly, with several items per dimension.

## Facts and measurements

| Agent | Model | Parameters | Context window | Capabilities (Ollama) | Load time | Speed |
|---|---|---|---|---|---|---|
| uye1 | qwen3.5:4b | 4.7B | 262,144 | vision, tools, thinking | 7.1 s | 41 tokens/s |
| uye2 | phi4-mini | 3.8B | 131,072 | tools | 5.0 s | 53 tokens/s |
| uye3 | llama3.2:3b | 3.2B | 131,072 | tools | 9.7 s | 63 tokens/s |
| uye4 | gemma4:e4b | 8.0B (4B effective) | 131,072 | vision, audio, tools, thinking | 17.5 s | 38 tokens/s |
| uye5 | qwen2.5-coder:7b | 7.6B | 32,768 | tools, insert (no thinking) | 6.4 s | 33 tokens/s |
| uye6 | qwen3:1.7b | 2.0B | 40,960 | tools, thinking | 3.9 s | 88 tokens/s |

All models are Q4_K_M quantised. Speed is generation speed for a short Python function. CPU-only computers will be several times slower.

## Spot checks

| Model | Writes `is_prime(n)` | JSON with a schema | Reasoning question | Two Turkish sentences |
|---|---|---|---|---|
| qwen3.5:4b | yes | valid | correct (4) | correct, fluent |
| phi4-mini | yes | valid | **wrong** (2) | fluent |
| llama3.2:3b | yes | valid | correct (4) | weaker: mixed in an English word, grammar mistake |
| gemma4:e4b | yes | valid | correct (4) | correct, fluent |
| qwen2.5-coder:7b | yes | valid | correct (4) | did not keep to the format (numbered list) |
| qwen3:1.7b | yes | valid | **wrong** (explained instead of answering, and gave a rabbit 2 legs) | inaccurate content |

The test prompts:

- **Reasoning:** "10 heads and 28 legs on a farm of chickens and rabbits; how many rabbits? Only the number." The answer is 4.
- **JSON:** Ollama's `format` with a two-field schema.

## Observations for Sprint 2

- **Structured output:** every model produced valid JSON with Ollama's `format`, so it is a reliable channel for agent results (PB-30).
- **Long documents:** context windows differ by a factor of eight, from 32,768 for the coder to 262,144 for Qwen3.5. Context is worth its own score in the capability profile.
- **Vision:** only Qwen3.5 4B and Gemma 4 E4B accept images (PB-36).
- **Speed:** the 1.7B model is the fastest but failed both language checks. Speed alone should not win an assignment.
- **Wrong answers:** in the Assistant, small models also made factual and arithmetic mistakes inside otherwise good answers ([test report](../scrum/sprint-1/test-report.md), AT-16 and AT-20).
- **Next step:** these single runs do not rank the models. PB-21 should use at least five items per dimension, as its acceptance criteria say.
