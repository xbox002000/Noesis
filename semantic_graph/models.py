"""
Layer 2 - Semantic Cognitive Unit (SCU) 核心模型
目前先實作核心必要欄位（對應使用者 1.b 選擇）
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid

# 嘗試與 Layer 1 整合（共用 UncertaintyType）
try:
    from epistemic_kernel.models import UncertaintyType
except ImportError:
    from enum import Enum
    class UncertaintyType(Enum):
        ALEATORY = "aleatory"
        EPISTEMIC = "epistemic"
        MODEL = "model"
        CONTENTION = "contention"


@dataclass
class SCU:
    """
    Semantic Cognitive Unit（語義認知單元）
    Layer 2 的核心抽象單位。
    """

    id: str = field(default_factory=lambda: f"scu_{uuid.uuid4().hex[:8]}")
    concept: str = ""                    # 核心概念名稱（例如 "JWT Token Lifecycle"）
    domain: List[str] = field(default_factory=list)   # 所屬領域，例如 ["authentication", "security"]
    abstraction_level: str = "mid"       # low | mid | high

    # Epistemic 相關（與 Layer 1 整合點）
    confidence: float = 0.0
    uncertainty_type: Optional[UncertaintyType] = None

    # 關係（Phase 1.4 升級後支援結構化中繼資料）
    # - 跨 SCU 關係 (depends_on / enables / conflicts_with 等): List[dict] with {"id", "strength", "confidence", "source"}
    # - 元資料 (composed_of / files): List[str] （保持簡潔）
    relationships: Dict[str, List[Any]] = field(default_factory=dict)
    # 新格式範例：
    # {
    #   "depends_on": [
    #       {"id": "scu_xxx", "strength": 0.85, "confidence": 0.9, "source": "call_graph"},
    #       ...
    #   ],
    #   "enables": [ ... ],
    #   "composed_of": ["func_a", "func_b"],   # 仍為 str list
    #   "files": ["/path/to/mod.py"]
    # }

    # 動態與風險（核心實務欄位）
    change_frequency: str = "moderate"   # stable | moderate | volatile
    security_critical: bool = False

    last_validated: str = field(default_factory=lambda: datetime.now().isoformat())

    # 整合 Layer 1 後新增：這個 SCU 目前參與的衝突（便於追蹤）
    active_contentions: List[str] = field(default_factory=list)  # 存放衝突描述

    def add_relationship(self, relation_type: str, target_scu_id: str, strength: float = 1.0, confidence: float = 1.0, source: str = "unknown"):
        """
        新增/更新跨 SCU 關係（支援 strength 等中繼資料）。
        對 composed_of / files 等元資料不建議使用此方法（直接指派 list[str] 即可）。
        """
        if relation_type not in self.relationships:
            self.relationships[relation_type] = []
        current = self.relationships[relation_type]

        # 計算有效 id 清單（支援新舊格式）
        existing_ids = []
        for e in current:
            if isinstance(e, str):
                existing_ids.append(e)
            elif isinstance(e, dict):
                existing_ids.append(e.get("id") or e.get("target_id") or "")

        if target_scu_id in existing_ids:
            return  # 已存在，避免重複

        # 驗證並正規化
        entry = {
            "id": target_scu_id,
            "strength": max(0.0, min(1.0, float(strength))),
            "confidence": max(0.0, min(1.0, float(confidence))),
            "source": str(source) if source else "unknown",
        }
        current.append(entry)

    def has_conflict_with(self, other_id: str) -> bool:
        """快速判斷是否與某 SCU 有衝突關係（支援新舊關係格式）"""
        return other_id in self.get_relationship_ids("conflicts_with")

    def get_relationship_ids(self, relation_type: str) -> List[str]:
        """
        傳回指定關係類型的目標 id 清單（永遠是 str）。
        自動相容舊格式 List[str] 與新格式 List[dict]。
        """
        items = self.relationships.get(relation_type, []) or []
        result: List[str] = []
        for it in items:
            if isinstance(it, str):
                result.append(it)
            elif isinstance(it, dict):
                rid = it.get("id") or it.get("target_id") or it.get("scu_id")
                if rid:
                    result.append(str(rid))
        return result

    def get_relationship_details(self, relation_type: str) -> List[Dict[str, Any]]:
        """
        傳回正規化後的完整關係細節（dict 列表）。
        舊格式的 str 會被包成 {"id": , "strength":1.0, ... "source":"legacy"}。
        """
        items = self.relationships.get(relation_type, []) or []
        details: List[Dict[str, Any]] = []
        for it in items:
            if isinstance(it, str):
                details.append({
                    "id": it,
                    "strength": 1.0,
                    "confidence": 1.0,
                    "source": "legacy",
                })
            elif isinstance(it, dict):
                details.append({
                    "id": it.get("id") or it.get("target_id") or "",
                    "strength": float(it.get("strength", 1.0)),
                    "confidence": float(it.get("confidence", 1.0)),
                    "source": it.get("source", "unknown"),
                })
        return details

    def __post_init__(self):
        """自動將舊格式的跨 SCU 關係升級為新結構（in-memory 相容）。"""
        inter_rel_types = {"depends_on", "enables", "conflicts_with"}
        for rt in list(self.relationships.keys()):
            if rt not in inter_rel_types:
                continue
            items = self.relationships.get(rt) or []
            if items and isinstance(items[0], str):
                self.relationships[rt] = [
                    {"id": tid, "strength": 1.0, "confidence": 1.0, "source": "legacy"}
                    for tid in items
                ]

    def normalize_relationships(self, min_strength: float = 0.0) -> None:
        """
        Phase 1.5: Clean up this SCU's relationships in place.

        - Removes duplicates (by target id)
        - Removes self-referential relationships (A depends_on A)
        - Optionally prunes relationships below min_strength
        - Only affects inter-SCU relation types (depends_on, enables, conflicts_with, ...)
        """
        inter_rel_types = {"depends_on", "enables", "conflicts_with", "inherits_from", "specializes", "composed_of"}  # composed_of is metadata but we keep it simple

        for rt in list(self.relationships.keys()):
            if rt not in inter_rel_types and rt != "files":
                continue

            items = self.relationships.get(rt, [])
            if not items:
                continue

            seen = set()
            cleaned = []

            for item in items:
                if rt in ("composed_of", "files"):
                    # metadata: simple dedup on value
                    val = item if isinstance(item, str) else str(item)
                    if val not in seen:
                        seen.add(val)
                        cleaned.append(item)
                    continue

                # rich relationship
                if isinstance(item, str):
                    tid = item
                    strength = 1.0
                else:
                    tid = item.get("id") or item.get("target_id") or ""
                    strength = float(item.get("strength", 1.0))

                if not tid or tid == self.id:  # self-loop
                    continue
                if strength < min_strength:
                    continue
                if tid in seen:
                    continue

                seen.add(tid)
                cleaned.append(item)

            self.relationships[rt] = cleaned

    def __repr__(self):
        return f"SCU[{self.concept}] conf={self.confidence:.2f} level={self.abstraction_level}"


def create_scu_from_claim(claim, uncertainty_type=None) -> SCU:
    """
    Layer 1 整合點：從 KnowledgeClaim 建立 SCU
    （目前簡單轉換，後續可擴充更多邏輯）
    """
    return SCU(
        concept=claim.concept,
        confidence=claim.confidence,
        domain=["authentication", "security"],   # 預設 JWT 相關
        uncertainty_type=uncertainty_type,
        change_frequency="volatile",             # JWT 相關通常變化較快
        security_critical=True,
    )


def normalize_relationships(scu: SCU, min_strength: float = 0.0) -> None:
    """
    Standalone Phase 1.5 helper (also available as SCU.normalize_relationships()).
    """
    scu.normalize_relationships(min_strength=min_strength)


def get_relationship_stats(scus: list[SCU]) -> dict:
    """
    Utility for debugging (Phase 1.5).
    Returns aggregate stats similar to SCUGraph.get_relationship_stats.
    """
    from collections import defaultdict
    total = 0
    by_type: dict[str, int] = defaultdict(int)
    strengths = []

    inter = {"depends_on", "enables", "conflicts_with"}

    for scu in scus:
        for rt, items in scu.relationships.items():
            if rt not in inter:
                continue
            ids = scu.get_relationship_ids(rt)
            by_type[rt] += len(ids)
            total += len(ids)
            for d in scu.get_relationship_details(rt):
                strengths.append(float(d.get("strength", 1.0)))

    avg = sum(strengths) / len(strengths) if strengths else 0.0
    return {
        "total_scus": len(scus),
        "total_inter_scu_relationships": total,
        "by_type": dict(sorted(by_type.items())),
        "avg_strength": round(avg, 4),
        "min_strength": round(min(strengths), 4) if strengths else 0.0,
        "max_strength": round(max(strengths), 4) if strengths else 0.0,
    }
