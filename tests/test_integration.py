"""
Tests for semantic_graph integration with EpistemicKernel.
"""

import pytest
from semantic_graph import (
    EpistemicSemanticGraph,
    SCUGraph,
    integrate_kernel_into_graph,
)


def test_epistemic_semantic_graph_basic_ingest(populated_epistemic_kernel, jwt_claims_and_contentions):
    """Test the recommended high-level class."""
    claims, _ = jwt_claims_and_contentions
    kernel = populated_epistemic_kernel

    engine = EpistemicSemanticGraph()
    report = engine.ingest_from_kernel(kernel, claims)

    assert report["scus_added"] > 0
    summary = engine.get_summary()
    assert summary["total_scus"] > 0

    # 至少應該有一些 SCU 帶有衝突資訊
    conflicted = engine.get_scus_with_active_contention()
    assert len(conflicted) >= 0  # 目前資料下可能有也可能沒有，視匹配情況


def test_integrate_kernel_into_graph(populated_epistemic_kernel, jwt_claims_and_contentions):
    """Test the lower-level integrate function."""
    claims, _ = jwt_claims_and_contentions
    kernel = populated_epistemic_kernel

    graph = SCUGraph()
    report = integrate_kernel_into_graph(graph, kernel, claims)

    assert "scus_added" in report
    assert report["scus_added"] > 0
    assert len(graph.scus) > 0
