"""
簡單但合理的 Token 估算器
用於實驗，不依賴外部 LLM tokenizer。
"""

def estimate_tokens(text: str) -> int:
    """
    粗略估算 token 數量。
    經驗法則：
    - 英文：約 4 個字元 = 1 token
    - 中文：約 1.5~2 個字元 = 1 token（這裡取保守值 2）
    - 混合內容取加權平均
    """
    if not text:
        return 0

    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars

    # 中文較密集，給較高 token 估計
    tokens = int((chinese_chars * 1.8 + other_chars * 0.28))

    return max(1, tokens)


def estimate_claim_tokens(claim) -> int:
    """估算單一 KnowledgeClaim 轉成文字後的 token 數"""
    content = f"{claim.concept} (來源: {claim.source}, 信心: {claim.confidence})"
    return estimate_tokens(content)


def estimate_total_tokens(claims) -> int:
    """估算一組 claims 總共需要的 token"""
    total = sum(estimate_claim_tokens(c) for c in claims)
    # 加上 prompt 框架的 overhead（系統指令、格式等）
    overhead = estimate_tokens(
        "你是一位資深資安工程師，請根據以下資訊進行 JWT 認證的安全審查與風險分析。"
    )
    return total + overhead
