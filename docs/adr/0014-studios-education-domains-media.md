# ADR-0014: Visual Slide QA, Multimodal VQA, Data Leakage Guard, SM-2 Education, Cited KBs & Media Generators (Wave 3D)

- **Status:** Accepted
- **Date:** 2026-11-24

## Decision
1. **EPK-08 (`master/studios/render_qa.py`):** WCAG 2.2 contrast calculation, bullet/word overflow checks, and automatic citation slide generation.
2. **EPK-09 (`master/multimodal/vqa.py`):** Honest local image VQA inspector, video keyframe scene-change detector, and Turkish ASR WER benchmark.
3. **EPK-18 (`master/studios/leakage_guard.py`):** Train/test duplicate & target-correlation leakage guard plus ephemeral `:memory:` read-only SQL analytics.
4. **EPK-19 (`master/education/service.py`):** Persistent SQLite SM-2 spaced repetition flashcards and rubric-weighted exam autograder.
5. **EPK-20 (`master/domains/kb_service.py`):** Curated Turkish legal/health/finance KB with mandatory statute citation, disclaimer, and 112 emergency redirection guard.
6. **EPK-21 (`master/domains/engineering_bench.py`):** 15 literature-verified engineering formula benchmarks and 30-case G-code safety validator.
7. **EPK-22 (`master/media/generators.py`):** Deterministic SRT subtitle builder, Three.js 3D scene generator, and honest backend availability probe.
