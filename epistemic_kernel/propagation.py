from typing import List
from .models import KnowledgeClaim


def propagate_confidence(
    claims: List[KnowledgeClaim],
    corroboration_count: int = 0
) -> float:
    """
    信心傳遞引擎（Confidence Propagation）

    核心規則（來自藍圖）：
    - 輸出信心不能高於路徑上任何一個輸入信心的最小值
    - 多個獨立來源佐證可以小幅提升信心
    """
    if not claims:
        return 0.0

    # 取路徑上最弱的一環
    base_confidence = min(claim.confidence for claim in claims)

    # 獨立佐證加成（最多 +0.15）
    boost = min(0.15, corroboration_count * 0.05)

    final_confidence = min(1.0, base_confidence + boost)
    return round(final_confidence, 3)


def explain_propagation(claims: List[KnowledgeClaim], final_conf: float) -> str:
    """產生人類可讀的解釋"""
    if not claims:
        return "沒有任何輸入宣告。"

    min_claim = min(claims, key=lambda c: c.confidence)
    return (
        f"路徑上最低信心來自「{min_claim.concept}」({min_claim.confidence:.2f})，"
        f"最終輸出信心被限制為 {final_conf:.3f}"
    )
