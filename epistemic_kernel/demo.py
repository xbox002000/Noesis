"""
Layer 1 - Epistemic Kernel 示範腳本

執行方式：
    cd D:\Antigravity\grok-wt
    python -m epistemic_kernel.demo

或直接：
    python epistemic_kernel\demo.py
"""

from epistemic_kernel import (
    EpistemicKernel,
    UncertaintyType,
)


def print_separator(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def run_demo():
    kernel = EpistemicKernel()

    print_separator("情境 1：正常信心傳遞 + 佐證加成")
    print("假設我們讀到三個關於 JWT 有效期的宣告：")

    c1 = kernel.add_claim("JWT 有效期為 24 小時", 0.75, "README.md")
    c2 = kernel.add_claim("JWT 有效期為 24 小時", 0.80, "config.yaml")
    c3 = kernel.add_claim("JWT 有效期實作是 8 小時", 0.90, "auth.py")

    print(f"  - {c1}")
    print(f"  - {c2}")
    print(f"  - {c3}")

    # 正常路徑（只有前兩個一致的來源）
    conf1 = kernel.propagate([c1.id, c2.id], corroboration_count=2)
    print(f"\n只看前兩個來源的傳遞信心: {conf1}")
    kernel.explain_last_propagation([c1.id, c2.id], conf1)

    print_separator("情境 2：偵測到衝突（Contention）")
    print("第三個來源與前兩個明顯矛盾 → 建立活躍衝突")

    contention = kernel.register_contention(
        claim_a="JWT 有效期 24 小時（文件）",
        claim_b="JWT 有效期 8 小時（程式碼）",
        description="README 與實際實作不一致，影響 token 安全政策",
        severity="high"
    )
    print(f"  已登記衝突: {contention}")

    kernel.get_state_summary()

    print_separator("情境 3：Epistemic Uncertainty（可降低的不確定性）")
    print("我們還不知道這個服務的 rate limit，這屬於可透過查文件降低的不確定性。")

    uncertainty = kernel.register_uncertainty(
        UncertaintyType.EPISTEMIC,
        description="目前不知道此 API 的 rate limit 是多少",
        impact="high",
        resolution_path="查看官方 API 文件或進行實際測試"
    )
    print(f"  不確定性: {uncertainty}")
    print(f"  建議行動: {getattr(uncertainty, 'type', None) and '識別並收集更多資訊'}")

    print_separator("情境 4：觸發 Reasoning Collapse（信心崩潰）")
    print("模擬：輸入信心都很低，但系統卻輸出非常高的信心")

    low_claims = [
        kernel.add_claim("某功能可能存在", 0.35, "猜測"),
        kernel.add_claim("另一份文件提到類似功能", 0.40, "舊文件"),
    ]

    # 故意傳入很高的輸出信心（模擬錯誤行為）
    print("故意測試：輸入最低信心 0.35，卻假設輸出 0.85")
    patterns = kernel.failure_recognizer.check_all(
        input_claims=low_claims,
        output_confidence=0.85
    )
    for p in patterns:
        if p.detected:
            print(f"  [OK] 成功偵測到: {p.name}")
            print(f"    建議: {p.recommendation}")

    print_separator("情境 5：Epistemic State 總覽")
    kernel.get_state_summary()

    print("\n" + "=" * 60)
    print("  Layer 1 Epistemic Kernel 原型示範結束")
    print("=" * 60)
    print("\n你現在可以修改 demo.py 加入更多情境，或直接在 Python shell 中使用 EpistemicKernel。")


if __name__ == "__main__":
    run_demo()
