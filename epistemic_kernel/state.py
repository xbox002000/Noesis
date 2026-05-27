from typing import List, Dict
from .models import KnowledgeClaim, Uncertainty, Contention, UncertaintyType


class EpistemicState:
    """Epistemic State Tracker - 追蹤系統目前知道什麼、不知道什麼"""

    def __init__(self):
        self.known_knowns: List[KnowledgeClaim] = []
        self.known_unknowns: List[Uncertainty] = []
        self.suspected_unknowns: List[Uncertainty] = []
        self.active_contentions: List[Contention] = []

    def add_known(self, claim: KnowledgeClaim):
        self.known_knowns.append(claim)

    def add_known_unknown(self, uncertainty: Uncertainty):
        if uncertainty.type == UncertaintyType.EPISTEMIC:
            self.known_unknowns.append(uncertainty)
        else:
            self.suspected_unknowns.append(uncertainty)

    def add_contention(self, contention: Contention):
        self.active_contentions.append(contention)

    def get_summary(self) -> Dict:
        return {
            "known_knowns_count": len(self.known_knowns),
            "known_unknowns_count": len(self.known_unknowns),
            "suspected_unknowns_count": len(self.suspected_unknowns),
            "active_contentions_count": len(self.active_contentions),
            "has_blocking_contention": any(
                c.severity == "high" and not c.resolved
                for c in self.active_contentions
            ),
        }

    def print_summary(self):
        print("=== Epistemic State Summary ===")
        print(f"已知且有信心: {len(self.known_knowns)} 項")
        print(f"已知但不確定（可降低）: {len(self.known_unknowns)} 項")
        print(f"懷疑的不確定: {len(self.suspected_unknowns)} 項")
        print(f"活躍衝突: {len(self.active_contentions)} 項")

        if self.active_contentions:
            print("\n衝突詳情:")
            for c in self.active_contentions:
                status = "已解決" if c.resolved else "阻斷中"
                print(f"  - {c} [{status}]")
