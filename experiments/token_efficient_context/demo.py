"""
Practical Token Reduction Demo

This script shows how to use TokenEfficientContextBuilder in a realistic way.

It demonstrates:
- Building a compact, high-quality context from an EpistemicSemanticGraph
- Measurable token savings vs naive approaches
- Correctly avoiding conflicted / low-value information

Recommended real-world pattern:
    1. Maintain one long-lived EpistemicSemanticGraph in your agent.
    2. For every LLM call, use TokenEfficientContextBuilder to extract focused context.

Run:
    cd D:\Antigravity\grok-wt
    $env:PYTHONPATH="D:\Antigravity\grok-wt"; python -m experiments.token_efficient_context.demo
"""

from experiments.token_efficient_context.builder import (
    TokenEfficientContextBuilder,
    estimate_tokens,
)
from semantic_graph import EpistemicSemanticGraph
from epistemic_kernel import EpistemicKernel
from experiments.token_saving.scenario import create_jwt_security_scenario


def build_demo_graph() -> EpistemicSemanticGraph:
    """Helper that creates a populated graph (simulates what your agent would have)."""
    claims, contentions = create_jwt_security_scenario()

    kernel = EpistemicKernel()
    for c in claims:
        kernel.add_claim(c.concept, c.confidence, c.source)
    for cont in contentions:
        kernel.register_contention(
            claim_a=cont["claim_a"],
            claim_b=cont["claim_b"],
            description=cont["description"],
            severity=cont["severity"]
        )

    graph = EpistemicSemanticGraph()
    graph.ingest_from_kernel(kernel, claims)
    return graph


def run_comparison():
    print("=" * 70)
    print("Token-Efficient Context Builder — Clean Usage Demo")
    print("=" * 70)

    # === Recommended pattern: inject your existing graph ===
    my_graph = build_demo_graph()
    builder = TokenEfficientContextBuilder(graph=my_graph)

    task = "Review the JWT authentication mechanism for security risks and best practices"

    print(f"\nTask: {task}\n")

    # --- Naive baselines (for comparison) ---
    print("--- Naive Approaches ---")
    all_scus = "\n".join(f"- {s.concept}" for s in my_graph.graph.scus.values())
    naive_full = estimate_tokens(f"Task: {task}\n\n{all_scus}")
    print(f"1. Dump all knowledge: ~{naive_full} tokens")

    high_conf = "\n".join(
        f"- {s.concept}" for s in my_graph.graph.scus.values() if s.confidence >= 0.8
    )
    naive_high = estimate_tokens(f"Task: {task}\n\n{high_conf}")
    print(f"2. High-confidence only (≥0.8): ~{naive_high} tokens")

    # --- Our approach (the clean way) ---
    print("\n--- Using TokenEfficientContextBuilder (recommended) ---")
    # For the JWT security task, we give the builder some important terms to boost
    key_jwt_terms = ["jwt", "refresh", "access", "token", "hs256", "rs256", "cookie"]
    result = builder.build_context_for_task(
        task,
        max_tokens=600,
        min_relevance=0.10,
        use_graph_propagation=True,
        boost_terms=key_jwt_terms,   # this helps the relevance scorer
    )

    print(f"Resulting context size: ~{result.estimated_tokens} tokens")
    print(f"SCUs included: {len(result.included_scus)}")
    print(f"Filtered out: {result.excluded_reason}")

    print("\n--- Comparison ---")
    best_naive = min(naive_full, naive_high)
    savings = best_naive - result.estimated_tokens
    pct = (savings / best_naive * 100) if best_naive > 0 else 0

    print(f"Best naive baseline : ~{best_naive} tokens")
    print(f"Token-efficient     : ~{result.estimated_tokens} tokens")
    print(f"Absolute savings    : ~{savings} tokens")
    print(f"Relative reduction  : {pct:.1f}%")

    print("\n" + "=" * 70)
    print("Key benefits demonstrated:")
    print("- Significant token reduction")
    print("- Explicit avoidance of active high-severity contentions")
    print("- Graph propagation adds related high-value context automatically")
    print("=" * 70)


if __name__ == "__main__":
    run_comparison()
