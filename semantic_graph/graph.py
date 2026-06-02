"""
Layer 2 - SCUGraph 核心實作（純 Python 版本）
支援新增 SCU、關係管理、簡單查詢與 contention 偵測
"""

from typing import Dict, List, Optional, Any
from .models import SCU


class SCUGraph:
    """
    Semantic State Graph
    目前使用純 Python dict 實作，之後可升級為 networkx
    """

    def __init__(self):
        self.scus: Dict[str, SCU] = {}          # id -> SCU
        self.concept_index: Dict[str, str] = {} # concept -> scu_id（簡易去重）

    def add_scu(self, scu: SCU) -> str:
        """新增一個 SCU"""
        if scu.concept in self.concept_index:
            # 簡單處理：同概念則更新（之後可改成 merge 策略）
            existing_id = self.concept_index[scu.concept]
            self.scus[existing_id] = scu
            return existing_id

        self.scus[scu.id] = scu
        self.concept_index[scu.concept] = scu.id
        return scu.id

    def get_scu(self, scu_id: str) -> Optional[SCU]:
        return self.scus.get(scu_id)

    def get_scu_by_concept(self, concept: str) -> Optional[SCU]:
        scu_id = self.concept_index.get(concept)
        return self.scus.get(scu_id) if scu_id else None

    def add_relationship(self, source_id: str, relation_type: str, target_id: str,
                         strength: float = 1.0, confidence: float = 1.0, rel_source: str = "unknown"):
        """在兩個 SCU 之間建立關係（支援 strength / confidence / rel_source）。"""
        if source_id not in self.scus or target_id not in self.scus:
            raise ValueError("來源或目標 SCU 不存在")

        scu = self.scus[source_id]
        scu.add_relationship(relation_type, target_id, strength=strength, confidence=confidence, source=rel_source)

    def get_related(self, scu_id: str, relation_type: str = None) -> List[SCU]:
        """取得與某 SCU 有關係的其他 SCU（自動處理新舊關係格式）。"""
        scu = self.scus.get(scu_id)
        if not scu:
            return []

        results = []
        if relation_type:
            target_ids = scu.get_relationship_ids(relation_type)
            for tid in target_ids:
                if tid in self.scus:
                    results.append(self.scus[tid])
        else:
            # 回傳所有跨 SCU 關係（跳過 composed_of / files 等元資料）
            meta_keys = {"composed_of", "files"}
            for rt, _ in scu.relationships.items():
                if rt in meta_keys:
                    continue
                for tid in scu.get_relationship_ids(rt):
                    if tid in self.scus:
                        results.append(self.scus[tid])
        return results

    def detect_contentions(self) -> List[Dict]:
        """
        實用化改善後的 contention 偵測：
        - 檢查 explicit "conflicts_with" 關係
        - 也會把有 active_contentions 的 SCU 視為有衝突（即使還沒建立關係）
        """
        seen = set()
        contentions = []

        # 1. 從 explicit 關係偵測
        for scu in self.scus.values():
            conflict_ids = scu.get_relationship_ids("conflicts_with")
            for target_id in conflict_ids:
                if target_id not in self.scus:
                    continue
                target = self.scus[target_id]
                pair = frozenset([scu.id, target.id])
                if pair in seen:
                    continue
                seen.add(pair)

                severity = "high" if (scu.security_critical or target.security_critical) else "medium"
                contentions.append({
                    "scu_a": scu.concept,
                    "scu_b": target.concept,
                    "type": "explicit_conflict",
                    "severity": severity,
                    "scu_a_id": scu.id,
                    "scu_b_id": target.id,
                })

        # 2. 從 SCU 身上的 active_contentions 補充（更實用的來源）
        for scu in self.scus.values():
            if scu.active_contentions and scu.id not in seen:
                # 簡單處理：把有 active_contentions 的 SCU 標成有衝突
                contentions.append({
                    "scu_a": scu.concept,
                    "scu_b": "(來自 kernel 同步的衝突)",
                    "type": "epistemic_contention",
                    "severity": "high" if scu.security_critical else "medium",
                    "scu_a_id": scu.id,
                    "scu_b_id": None,
                    "descriptions": scu.active_contentions,
                })

        return contentions

    def get_summary(self) -> Dict:
        """回傳 Graph 摘要"""
        total_contentions = len(self.detect_contentions())
        return {
            "total_scus": len(self.scus),
            "total_contentions": total_contentions,
            "security_critical_count": sum(1 for s in self.scus.values() if s.security_critical),
            "high_abstraction_count": sum(1 for s in self.scus.values() if s.abstraction_level == "high"),
            "scus_with_active_contention": len(self.get_scus_with_active_contention()),
        }

    def get_scus_with_active_contention(self) -> List[SCU]:
        """實用方法：取得目前有活躍衝突的 SCU"""
        return [scu for scu in self.scus.values() if scu.active_contentions]

    def get_high_risk_scus(self, min_confidence: float = 0.7) -> List[SCU]:
        """實用方法：取得高風險（高信心 + 安全關鍵 + 有衝突）的 SCU"""
        return [
            scu for scu in self.scus.values()
            if scu.security_critical
            and scu.confidence >= min_confidence
            and scu.active_contentions
        ]

    def get_relationship_stats(self) -> Dict[str, Any]:
        """
        Phase 1.4 附加：關係統計工具（用於除錯與監控）。
        回報跨 SCU 關係的數量、類型分布、平均 strength 等。
        """
        total_rels = 0
        by_type: Dict[str, int] = {}
        strengths: List[float] = []
        meta_keys = {"composed_of", "files"}

        for scu in self.scus.values():
            for rt in scu.relationships:
                if rt in meta_keys:
                    continue
                cnt = len(scu.get_relationship_ids(rt))
                by_type[rt] = by_type.get(rt, 0) + cnt
                total_rels += cnt
                for d in scu.get_relationship_details(rt):
                    try:
                        strengths.append(float(d.get("strength", 1.0)))
                    except Exception:
                        pass

        avg = sum(strengths) / len(strengths) if strengths else 0.0
        return {
            "total_scus": len(self.scus),
            "total_inter_scu_relationships": total_rels,
            "by_type": dict(sorted(by_type.items())),
            "avg_strength": round(avg, 4),
            "min_strength": round(min(strengths), 4) if strengths else 0.0,
            "max_strength": round(max(strengths), 4) if strengths else 0.0,
            "strength_count": len(strengths),
        }

    def __repr__(self):
        return f"SCUGraph(scus={len(self.scus)}, contentions={len(self.detect_contentions())})"
