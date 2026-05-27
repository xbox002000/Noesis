from .models import UncertaintyType, Uncertainty


def create_uncertainty(
    type_: UncertaintyType,
    description: str,
    impact: str = "medium",
    resolution_path: str = None
) -> Uncertainty:
    """建立不確定性記錄的輔助函式"""
    return Uncertainty(
        type=type_,
        description=description,
        impact=impact,
        resolution_path=resolution_path
    )


def get_uncertainty_action(uncertainty: Uncertainty) -> str:
    """
    根據不確定性類型給出建議行動（對應藍圖）
    """
    actions = {
        UncertaintyType.ALEATORY: "接受並設定邊界（acknowledge_and_bound）",
        UncertaintyType.EPISTEMIC: "識別並收集更多資訊（identify_and_reduce）",
        UncertaintyType.MODEL: "標記並升級給更強模型或人類（flag_and_escalate）",
        UncertaintyType.CONTENTION: "表面化衝突並進行仲裁（surface_and_arbitrate）",
    }
    return actions.get(uncertainty.type, "未知類型")
