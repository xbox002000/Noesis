"""
Naive vs Epistemic 兩種策略的選擇邏輯
"""

from typing import List, Tuple
from epistemic_kernel import EpistemicKernel, UncertaintyType


def naive_strategy(claims, min_confidence: float = 0.50) -> List:
    """
    Naive 策略：
    - 把幾乎所有高於門檻的資訊都塞進去
    - 不處理衝突
    - 不區分不確定性類型
    """
    selected = [c for c in claims if c.confidence >= min_confidence]
    return selected


def epistemic_strategy(claims, contentions) -> Tuple[List, dict]:
    """
    Epistemic Kernel 策略：
    - 只納入高信心且無高嚴重性衝突的資訊
    - 遇到高嚴重性衝突時主動「阻斷」相關路徑
    - 過濾低價值的不確定性
    """
    kernel = EpistemicKernel()

    # 把所有宣告餵給 Kernel（用來偵測衝突與狀態）
    for c in claims:
        kernel.add_claim(c.concept, c.confidence, c.source)

    # 註冊已知的衝突
    for cont in contentions:
        kernel.register_contention(
            claim_a=cont["claim_a"],
            claim_b=cont["claim_b"],
            description=cont["description"],
            severity=cont["severity"]
        )

    # Epistemic 選擇規則
    selected = []
    blocked = []
    high_severity_contention = any(
        c.severity == "high" and not c.resolved
        for c in kernel.state.active_contentions
    )

    for c in claims:
        # 規則 1: 信心必須夠高
        if c.confidence < 0.70:
            continue

        # 規則 2: 如果存在高嚴重性衝突，且此宣告與衝突相關 → 阻斷
        is_related_to_contention = any(
            c.concept in cont["claim_a"] or c.concept in cont["claim_b"]
            for cont in contentions
        )

        if high_severity_contention and is_related_to_contention:
            blocked.append(c)
            continue

        selected.append(c)

    stats = {
        "total_claims": len(claims),
        "naive_selected": len([c for c in claims if c.confidence >= 0.5]),
        "epistemic_selected": len(selected),
        "blocked_by_contention": len(blocked),
        "has_blocking_contention": high_severity_contention,
    }

    return selected, stats
