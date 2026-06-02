"""
EpistemicSemanticGraph — Layer 1 + Layer 2 高階整合入口（實用化形式）

這個類別是目前「Layer 1 Epistemic Kernel + Layer 2 Semantic State Graph」最推薦的使用方式。

目標：
- 隱藏底層整合複雜度（Kernel 與 Graph 之間的同步、衝突連結、狀態傳遞等）
- 提供小而美的實用 API
- 作為後續 Layer 3（Context Compiler）、Layer 4（Cognitive Scheduler） 的穩固基礎

使用原則：
- 大多數情況只呼叫 `ingest_from_kernel`
- 需要低階控制時，再直接操作 `.graph` 或 `.kernel`
"""

from typing import List, Dict, Optional, Any
from epistemic_kernel import EpistemicKernel, KnowledgeClaim
from .models import SCU
from .graph import SCUGraph
from .integration import integrate_kernel_into_graph


class EpistemicSemanticGraph:
    """
    Layer 1 (Epistemic Kernel) + Layer 2 (Semantic State Graph) 的高階封裝。

    使用方式推薦：
        engine = EpistemicSemanticGraph()
        engine.ingest_claims(claims)           # 基本加入
        engine.ingest_from_kernel(kernel)      # 從已運行的 Kernel 同步（推薦）
        engine.get_high_risk_scus()
        engine.get_scus_with_active_contention()
    """

    def __init__(self):
        self.graph = SCUGraph()
        self._kernel: Optional[EpistemicKernel] = None

    @property
    def kernel(self) -> EpistemicKernel:
        """延遲建立 EpistemicKernel"""
        if self._kernel is None:
            self._kernel = EpistemicKernel()
        return self._kernel

    def ingest_claims(self, claims: List[KnowledgeClaim]):
        """簡單加入一批 KnowledgeClaim（不帶完整 epistemic 狀態）"""
        for claim in claims:
            scu = SCU(
                concept=claim.concept,
                confidence=claim.confidence,
                domain=["authentication", "security"],
            )
            self.graph.add_scu(scu)

    def ingest_from_kernel(self, kernel: EpistemicKernel, claims: List[KnowledgeClaim]) -> Dict:
        """
        推薦的主要入口：從 EpistemicKernel 完整同步狀態到 Semantic Graph。

        會自動處理：
        - SCU 建立
        - 信心、不確定性同步
        - 衝突資訊附加
        - 關係建立（盡力而為）
        """
        self._kernel = kernel
        report = integrate_kernel_into_graph(self.graph, kernel, claims)
        return report

    def ingest_scus(self, scus: List[SCU]) -> int:
        """
        直接從 Layer 2 Bootstrap（或其他來源）加入已建好的 SCU 清單。

        這是把「冷啟動產生的知識圖」餵進系統的主要方式。
        會保留 SCU 上已有的 relationships（depends_on / enables 等）。
        """
        count = 0
        for scu in scus:
            self.graph.add_scu(scu)
            count += 1
        return count

    def get_scus_with_active_contention(self) -> List[SCU]:
        return self.graph.get_scus_with_active_contention()

    def get_high_risk_scus(self, min_confidence: float = 0.7) -> List[SCU]:
        return self.graph.get_high_risk_scus(min_confidence)

    def detect_contentions(self) -> List[Dict]:
        return self.graph.detect_contentions()

    def get_summary(self) -> Dict:
        return self.graph.get_summary()

    def get_scu_by_concept(self, concept: str) -> Optional[SCU]:
        return self.graph.get_scu_by_concept(concept)

    def get_relationship_stats(self) -> Dict[str, Any]:
        """委派到底層 SCUGraph（Phase 1.4 關係增強後可用）。"""
        return self.graph.get_relationship_stats()

    def __repr__(self):
        return f"EpistemicSemanticGraph(scus={len(self.graph.scus)})"
