from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from datetime import datetime
import uuid


class UncertaintyType(Enum):
    """四種不確定性類型（對應藍圖 Layer 1）"""
    ALEATORY = "aleatory"       # 不可約減的隨機性
    EPISTEMIC = "epistemic"     # 可透過更多資訊降低
    MODEL = "model"             # 模型本身能力的邊界
    CONTENTION = "contention"   # 資訊衝突


@dataclass
class KnowledgeClaim:
    """知識宣告（類似簡化版的 SCU）"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    concept: str = ""
    confidence: float = 0.0     # 0.0 ~ 1.0
    source: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __repr__(self):
        return f"Claim[{self.concept}] conf={self.confidence:.2f} src={self.source}"


@dataclass
class Uncertainty:
    """不確定性記錄"""
    type: UncertaintyType
    description: str
    impact: str = "medium"           # low / medium / high
    resolution_path: Optional[str] = None

    def __repr__(self):
        return f"Uncertainty[{self.type.value}] {self.description[:40]}..."


@dataclass
class Contention:
    """主動衝突"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    claim_a: str = ""
    claim_b: str = ""
    description: str = ""
    severity: str = "high"
    resolved: bool = False

    def __repr__(self):
        return f"Contention: {self.claim_a} vs {self.claim_b}"


@dataclass
class FailurePattern:
    """偵測到的失敗模式"""
    name: str
    symptoms: List[str]
    detected: bool = False
    recommendation: str = ""

    def __repr__(self):
        status = "DETECTED" if self.detected else "OK"
        return f"FailurePattern[{self.name}] {status}"
