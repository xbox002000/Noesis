"""
Noesis - Practical AI-Native Cognitive Runtime

Main public API for large organizations and production agent use.

Core practical components:
- Token-efficient, epistemically honest context building (Layer 3)
- SCU Graph + Bootstrap from code (Layer 2)
- Epistemic Kernel primitives (Layer 1)

Example usage for production agents:

    from noesis import (
        bootstrap_from_codebase,
        EpistemicSemanticGraph,
        TokenEfficientContextBuilder,
    )

    # 1. Bootstrap once (or incrementally)
    scus = bootstrap_from_codebase("/path/to/your/large/monorepo")

    # 2. Maintain a graph
    engine = EpistemicSemanticGraph()
    engine.ingest_scus(scus)

    # 3. For every LLM call in your agent:
    builder = TokenEfficientContextBuilder(graph=engine)
    result = builder.build_context_for_task(
        "Review the authentication changes for security issues",
        max_tokens=2000,
        epistemic_honesty_level="medium",  # recommended
    )

    prompt = builder.format_as_prompt(result, system_instruction="You are a senior security engineer.")

    # Send prompt to your LLM. Get better answers at ~1% of the token cost.
"""

from semantic_graph import (
    EpistemicSemanticGraph,
    SCU,
    SCUGraph,
    bootstrap_from_codebase,
    StructuralAnalyzer,
    SemanticClusterer,
    SCUGenerator,
    normalize_relationships,
    get_relationship_stats,
)

from experiments.token_efficient_context.builder import (
    TokenEfficientContextBuilder,
    ContextResult,
    estimate_tokens,
)

# Re-export the most practical high-level functions
__all__ = [
    # Graph + Bootstrap (Layer 2 entrypoints)
    "EpistemicSemanticGraph",
    "SCU",
    "SCUGraph",
    "bootstrap_from_codebase",
    "StructuralAnalyzer",
    "SemanticClusterer",
    "SCUGenerator",
    # Context Builder (the star for production use - Layer 3)
    "TokenEfficientContextBuilder",
    "ContextResult",
    "estimate_tokens",
]

__version__ = "0.1.0a0"