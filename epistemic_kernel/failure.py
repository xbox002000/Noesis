from typing import List
from .models import KnowledgeClaim, FailurePattern


class FailureRecognizer:
    """Failure Pattern Recognizer - 偵測藍圖中定義的四種失敗模式"""

    def __init__(self):
        self.patterns = {
            "reasoning_collapse": FailurePattern(
                name="reasoning_collapse",
                symptoms=[
                    "信心在沒有新資訊的情況下大幅跳升",
                    "結論信心遠高於輸入信心"
                ],
                recommendation="暫停推理，要求更多資訊再繼續。"
            ),
            "context_poisoning": FailurePattern(
                name="context_poisoning",
                symptoms=[
                    "低信任度的訊號開始主導推理鏈"
                ],
                recommendation="隔離該訊號，重新評估信任鏈。"
            ),
            "circular_reasoning": FailurePattern(
                name="circular_reasoning",
                symptoms=[
                    "推理圖中出現循環依賴"
                ],
                recommendation="打破循環，引入外部參考點。"
            ),
            "premature_convergence": FailurePattern(
                name="premature_convergence",
                symptoms=[
                    "在資訊不足的情況下就收斂到答案"
                ],
                recommendation="強制進行反方論證（devil's advocate）再做決定。"
            ),
        }

    def detect_reasoning_collapse(
        self, input_claims: List[KnowledgeClaim], output_confidence: float
    ) -> FailurePattern:
        """偵測信心崩潰（輸出信心遠高於輸入）"""
        if not input_claims:
            return self.patterns["reasoning_collapse"]

        min_input = min(c.confidence for c in input_claims)
        pattern = self.patterns["reasoning_collapse"]

        if output_confidence > min_input + 0.25:   # 超過 25% 的不合理提升
            pattern.detected = True
        return pattern

    def detect_premature_convergence(
        self, input_claims: List[KnowledgeClaim], has_active_contention: bool
    ) -> FailurePattern:
        """偵測過早收斂"""
        pattern = self.patterns["premature_convergence"]

        # 簡單啟發式：輸入很少 + 沒有活躍衝突卻快速收斂
        avg_conf = sum(c.confidence for c in input_claims) / len(input_claims) if input_claims else 0
        if len(input_claims) <= 2 and avg_conf > 0.8 and not has_active_contention:
            pattern.detected = True
        return pattern

    def check_all(self, **kwargs) -> List[FailurePattern]:
        """統一檢查所有可能觸發的模式"""
        detected = []

        if "input_claims" in kwargs and "output_confidence" in kwargs:
            p = self.detect_reasoning_collapse(
                kwargs["input_claims"], kwargs["output_confidence"]
            )
            if p.detected:
                detected.append(p)

        if "input_claims" in kwargs and "has_active_contention" in kwargs:
            p = self.detect_premature_convergence(
                kwargs["input_claims"], kwargs["has_active_contention"]
            )
            if p.detected:
                detected.append(p)

        return detected
