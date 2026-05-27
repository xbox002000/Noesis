"""
Token Saving Experiment - Scenario Definition
Task: 審查 JWT 認證機制的安全性（Security Review of JWT Authentication）
"""

from epistemic_kernel.models import KnowledgeClaim


def create_jwt_security_scenario():
    """
    建立一個較真實的 JWT 安全審查情境，包含：
    - 多個不同信心的宣告
    - 來源差異（文件 vs 程式碼 vs 最佳實踐）
    - 明顯的衝突（Contention）
    - 不同類型的不確定性
    """
    claims = [
        # 高信心 - 文件與程式碼一致
        KnowledgeClaim(
            concept="JWT 使用 RS256 非對稱簽章演算法",
            confidence=0.92,
            source="auth.py + README.md"
        ),
        KnowledgeClaim(
            concept="Access Token 有效期設定為 15 分鐘",
            confidence=0.88,
            source="config.yaml + auth.py"
        ),
        KnowledgeClaim(
            concept="Refresh Token 有效期設定為 7 天",
            confidence=0.85,
            source="config.yaml"
        ),
        KnowledgeClaim(
            concept="Token 必須使用 HTTPS 傳輸",
            confidence=0.95,
            source="security_policy.md"
        ),

        # 中等信心 - 只有文件提到
        KnowledgeClaim(
            concept="Payload 中不應存放敏感個人資料",
            confidence=0.72,
            source="security_guidelines.md"
        ),
        KnowledgeClaim(
            concept="應實作 Token 撤銷機制（黑名單）",
            confidence=0.68,
            source="security_guidelines.md"
        ),

        # 低信心 - 猜測或舊文件
        KnowledgeClaim(
            concept="JWT 的 audience (aud) claim 應該嚴格驗證",
            confidence=0.55,
            source="舊版設計文件（2023）"
        ),

        # 明顯衝突來源（Contention）
        KnowledgeClaim(
            concept="Refresh Token 儲存在 LocalStorage（方便）",
            confidence=0.80,
            source="frontend/README.md"
        ),
        KnowledgeClaim(
            concept="Refresh Token 絕對不能存 LocalStorage，應使用 HttpOnly Cookie",
            confidence=0.90,
            source="security_policy.md + 資安顧問建議"
        ),

        # 另一個衝突：演算法相關
        KnowledgeClaim(
            concept="為了相容性，仍然支援 HS256 對稱簽章",
            confidence=0.65,
            source="legacy_support.md"
        ),
        KnowledgeClaim(
            concept="HS256 在分散式系統中存在嚴重金鑰洩漏風險，不應使用",
            confidence=0.87,
            source="auth.py 註解 + 資安審計報告"
        ),

        # 低信心但可能重要的項目
        KnowledgeClaim(
            concept="應該實作 jti (JWT ID) 來支援撤銷",
            confidence=0.45,
            source="TODO comment in auth.py"
        ),
    ]

    contentions = [
        {
            "claim_a": "Refresh Token 儲存在 LocalStorage",
            "claim_b": "Refresh Token 應使用 HttpOnly Cookie",
            "description": "前端實作與安全政策嚴重衝突，屬於高風險",
            "severity": "high"
        },
        {
            "claim_a": "支援 HS256 相容性",
            "claim_b": "HS256 在分散式系統中風險過高",
            "description": "向後相容 vs 安全性 的經典衝突",
            "severity": "high"
        }
    ]

    return claims, contentions
