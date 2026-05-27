"""
Layer 2 - Semantic Cognitive Unit (SCU) 核心模型
目前先實作核心必要欄位（對應使用者 1.b 選擇）
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
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

    # 關係（目前用 id 清單表示）
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    # 範例：
    # {
    #   "depends_on": ["scu_xxx", "scu_yyy"],
    #   "enables": ["scu_zzz"],
    #   "conflicts_with": ["scu_aaa"]
    # }

    # 動態與風險（核心實務欄位）
    change_frequency: str = "moderate"   # stable | moderate | volatile
    security_critical: bool = False

    last_validated: str = field(default_factory=lambda: datetime.now().isoformat())

    # 整合 Layer 1 後新增：這個 SCU 目前參與的衝突（便於追蹤）
    active_contentions: List[str] = field(default_factory=list)  # 存放衝突描述

    def add_relationship(self, relation_type: str, target_scu_id: str):
        """新增關係"""
        if relation_type not in self.relationships:
            self.relationships[relation_type] = []
        if target_scu_id not in self.relationships[relation_type]:
            self.relationships[relation_type].append(target_scu_id)

    def has_conflict_with(self, other_id: str) -> bool:
        """快速判斷是否與某 SCU 有衝突關係"""
        return other_id in self.relationships.get("conflicts_with", [])

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
