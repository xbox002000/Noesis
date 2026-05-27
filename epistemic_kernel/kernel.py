from typing import List, Optional
from .models import (
    KnowledgeClaim, Uncertainty, Contention, UncertaintyType,
    FailurePattern
)
from .propagation import propagate_confidence, explain_propagation
from .state import EpistemicState
from .failure import FailureRecognizer
from .uncertainty import create_uncertainty, get_uncertainty_action


class EpistemicKernel:
    """
    Layer 1 - Epistemic Kernel 主入口

    負責：
    - 管理知識宣告
    - 執行信心傳遞
    - 追蹤不確定性與衝突
    - 偵測推理失敗模式
    """

    def __init__(self):
        self.claims: List[KnowledgeClaim] = []
        self.state = EpistemicState()
        self.failure_recognizer = FailureRecognizer()
        self.claim_index = {}  # id -> claim

    def add_claim(
        self,
        concept: str,
        confidence: float,
        source: str
    ) -> KnowledgeClaim:
        """加入一個新的知識宣告"""
        claim = KnowledgeClaim(
            concept=concept,
            confidence=confidence,
            source=source
        )
        self.claims.append(claim)
        self.claim_index[claim.id] = claim
        self.state.add_known(claim)
        return claim

    def propagate(
        self,
        claim_ids: List[str],
        corroboration_count: int = 0
    ) -> float:
        """
        對指定的宣告路徑執行信心傳遞
        """
        selected = [self.claim_index[cid] for cid in claim_ids if cid in self.claim_index]
        if not selected:
            return 0.0

        final_conf = propagate_confidence(selected, corroboration_count)

        # 檢查是否觸發失敗模式
        patterns = self.failure_recognizer.check_all(
            input_claims=selected,
            output_confidence=final_conf,
            has_active_contention=len(self.state.active_contentions) > 0
        )

        for p in patterns:
            if p.detected:
                print(f"\n[警告] 偵測到失敗模式: {p.name}")
                print(f"  建議: {p.recommendation}")

        return final_conf

    def register_uncertainty(
        self,
        type_: UncertaintyType,
        description: str,
        impact: str = "medium",
        resolution_path: Optional[str] = None
    ) -> Uncertainty:
        """登記一個不確定性"""
        uncertainty = create_uncertainty(
            type_, description, impact, resolution_path
        )
        self.state.add_known_unknown(uncertainty)
        return uncertainty

    def register_contention(
        self,
        claim_a: str,
        claim_b: str,
        description: str,
        severity: str = "high"
    ) -> Contention:
        """登記一場主動衝突"""
        contention = Contention(
            claim_a=claim_a,
            claim_b=claim_b,
            description=description,
            severity=severity
        )
        self.state.add_contention(contention)
        return contention

    def get_state_summary(self):
        self.state.print_summary()

    def explain_last_propagation(self, claim_ids: List[str], final_conf: float):
        selected = [self.claim_index[cid] for cid in claim_ids if cid in self.claim_index]
        print(explain_propagation(selected, final_conf))
