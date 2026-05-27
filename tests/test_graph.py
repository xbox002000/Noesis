"""
Tests for semantic_graph.graph (SCUGraph)
"""

import pytest
from semantic_graph import SCU, SCUGraph


def test_add_scu_and_retrieve():
    graph = SCUGraph()
    scu = SCU(concept="JWT Lifecycle", confidence=0.85, security_critical=True)
    graph.add_scu(scu)

    assert graph.get_scu(scu.id) is not None
    assert graph.get_scu_by_concept("JWT Lifecycle") is not None


def test_add_relationship():
    graph = SCUGraph()
    scu1 = SCU(concept="Access Token Expiry")
    scu2 = SCU(concept="Refresh Token Expiry")
    graph.add_scu(scu1)
    graph.add_scu(scu2)

    graph.add_relationship(scu1.id, "depends_on", scu2.id)

    related = graph.get_related(scu1.id, "depends_on")
    assert len(related) == 1
    assert related[0].concept == "Refresh Token Expiry"


def test_detect_contentions_explicit():
    graph = SCUGraph()
    scu1 = SCU(concept="LocalStorage Storage", security_critical=True)
    scu2 = SCU(concept="HttpOnly Cookie Required", security_critical=True)
    graph.add_scu(scu1)
    graph.add_scu(scu2)

    graph.add_relationship(scu1.id, "conflicts_with", scu2.id)
    graph.add_relationship(scu2.id, "conflicts_with", scu1.id)

    contentions = graph.detect_contentions()
    assert len(contentions) == 1  # 去重後應該只有一筆
    assert contentions[0]["severity"] == "high"


def test_get_scus_with_active_contention():
    graph = SCUGraph()
    scu = SCU(concept="Risky Component", active_contentions=["Some conflict"])
    graph.add_scu(scu)

    conflicted = graph.get_scus_with_active_contention()
    assert len(conflicted) == 1
