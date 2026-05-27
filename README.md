# Noesis

**An AI-Native Cognitive Runtime**

Noesis is an experimental runtime designed from the ground up for AI systems that reason under uncertainty, manage finite cognitive resources, and maintain epistemic honesty.

> "Uncertainty is not a bug — it is the fundamental input to every inference step."

## Core Philosophy

Traditional agent frameworks treat AI as a smarter function:
```
input → AI → output
```

Noesis is built on a fundamentally different model:
```
partial_context + uncertainty + goals
  → reasoning under constraints
  → confidence-weighted action
  → feedback that changes the reasoner itself
```

## Key Concepts

- **Epistemic Kernel (Layer 1)**: First-class uncertainty tracking, confidence propagation, contention detection, and failure pattern recognition.
- **Semantic Graph (Layer 2)**: Knowledge is represented as Semantic Cognitive Units (SCUs) rather than raw files or chunks, with explicit relationships (`depends_on`, `enables`, etc.).
- **Context Compiler (Layer 3)**: Intelligent, epistemically-aware context assembly with multiple honesty levels (`low` / `medium` / `high`).

## Current Features

- `TokenEfficientContextBuilder` with pluggable honesty levels
- Automatic generation of rich **Epistemic Notes** (including exclusion reasons, Borderline SCUs, and Potential Impact)
- Heuristic + feature-based SCU bootstrapping from Python codebases
- Cross-SCU relationship inference
- Experimental A/B testing framework for comparing context strategies

## Project Structure

```
Noesis/
├── epistemic_kernel/          # Layer 1 - Confidence, Contention, Failure Detection
├── semantic_graph/            # Layer 2 - SCU Graph + Bootstrap
├── experiments/
│   ├── token_efficient_context/
│   └── llm_quality_ab_test.py
├── docs/                      # Development plans and reports
└── tests/
```

## Quick Start

```bash
# Clone the repo
git clone https://github.com/xbox002000/Noesis.git
cd Noesis

# Install dependencies (if any)
pip install -r requirements.txt   # (if exists)

# Example: Generate prompts with different honesty levels
python -m experiments.llm_quality_ab_test --task 0 --honesty-level medium
```

## Documentation

- [AI Native Runtime Blueprint](AI_NATIVE_RUNTIME_BLUEPRINT.md)
- [Phase 1 Development Tasks](docs/phase1-scu-relationship-enhancement-tasks.md)
- [Medium Epistemic Honesty Improvement Report](experiments/reports/Medium_Epistemic_Honesty_Improvement_Report.md)

## Current Status

This project is in active research and prototyping phase.

- The `epistemic_honesty_level="medium"` mode in the Context Builder is already quite usable and significantly improves model honesty compared to naive approaches.
- The full stack (especially Layer 2 relationship quality) is still under heavy development.

## Philosophy & Goals

We believe future agent systems should not treat uncertainty as an afterthought. Noesis aims to explore what a runtime built around the following principles could look like:

- Uncertainty is first-class
- Cognition has cost
- Trust must be earned
- Failure is semantic, not syntactic
- Human governance, not micromanagement

## License

MIT License

---

*This project is an exploration into building systems that can honestly reason about what they know, what they don't know, and what they might be wrong about.*