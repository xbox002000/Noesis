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


# ============================================================
# Phase 1.4 新關係結構測試
# ============================================================

def test_add_relationship_with_strength():
    """測試新增帶 strength/confidence/source 的關係"""
    graph = SCUGraph()
    scu1 = SCU(concept="Caller")
    scu2 = SCU(concept="Callee")
    graph.add_scu(scu1)
    graph.add_scu(scu2)

    graph.add_relationship(scu1.id, "depends_on", scu2.id, strength=0.75, confidence=0.9, rel_source="call_graph")

    # 檢查 SCU 內部儲存
    rels = scu1.relationships.get("depends_on", [])
    assert len(rels) == 1
    assert isinstance(rels[0], dict)
    assert rels[0]["id"] == scu2.id
    assert abs(rels[0]["strength"] - 0.75) < 0.001
    assert rels[0]["source"] == "call_graph"

    # 檢查 helper
    ids = scu1.get_relationship_ids("depends_on")
    assert ids == [scu2.id]

    details = scu1.get_relationship_details("depends_on")
    assert details[0]["strength"] == 0.75

    # graph 層級查詢仍正常
    related = graph.get_related(scu1.id, "depends_on")
    assert len(related) == 1
    assert related[0].id == scu2.id


def test_relationship_validation_clamping():
    """strength/confidence 應被 clamp 到 [0,1]"""
    scu = SCU(concept="Test")
    scu.add_relationship("depends_on", "scu_other", strength=1.5, confidence=-0.3, source="test")
    details = scu.get_relationship_details("depends_on")
    assert details[0]["strength"] == 1.0
    assert details[0]["confidence"] == 0.0


def test_legacy_relationship_compat():
    """直接設定舊格式 list[str] 時，getter 與 has_conflict 應相容，並在 post_init 升級"""
    scu = SCU(concept="Legacy")
    # 模擬舊資料（繞過新 add）
    scu.relationships["depends_on"] = ["scu_old1", "scu_old2"]
    scu.relationships["conflicts_with"] = ["scu_bad"]

    # getter 應正常工作
    assert scu.get_relationship_ids("depends_on") == ["scu_old1", "scu_old2"]
    assert scu.has_conflict_with("scu_bad") is True

    # __post_init__ 會在 dataclass 建立時跑；這裡手動觸發類似行為或直接檢查 getter
    # 重新建立以觸發 post_init
    scu2 = SCU(concept="Legacy2")
    scu2.relationships["depends_on"] = ["scu_x"]
    scu2.__post_init__()  # 手動觸發升級
    assert isinstance(scu2.relationships["depends_on"][0], dict)
    assert scu2.get_relationship_ids("depends_on") == ["scu_x"]


def test_get_related_skips_metadata():
    """get_related 全掃描時應跳過 composed_of / files"""
    graph = SCUGraph()
    scu = SCU(concept="Main")
    graph.add_scu(scu)
    # 設定元資料 + 真關係
    scu.relationships["composed_of"] = ["func1", "func2"]
    scu.relationships["files"] = ["/a.py"]
    other = SCU(concept="Dep")
    graph.add_scu(other)
    graph.add_relationship(scu.id, "depends_on", other.id)

    all_related = graph.get_related(scu.id)
    assert len(all_related) == 1
    assert all_related[0].concept == "Dep"
