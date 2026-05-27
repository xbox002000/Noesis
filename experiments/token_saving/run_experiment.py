"""
Token Saving Experiment Runner
比較 Naive 與 Epistemic Kernel 兩種策略在同一個任務下的資訊使用量
"""

from scenario import create_jwt_security_scenario
from strategies import naive_strategy, epistemic_strategy
from estimator import estimate_total_tokens, estimate_claim_tokens


def print_report(naive_claims, epistemic_claims, stats, naive_tokens, epistemic_tokens):
    print("\n" + "=" * 70)
    print("          Token 節省實驗報告 - JWT 安全審查任務")
    print("=" * 70)

    print("\n【任務】")
    print("對 JWT 認證機制進行安全性審查與風險分析")

    print("\n【輸入資料總覽】")
    print(f"  總宣告數量: {stats['total_claims']}")

    print("\n【Naive 策略（傳統做法）】")
    print(f"  納入宣告數: {len(naive_claims)}")
    print(f"  估計 Token 數: {naive_tokens}")
    print(f"  決策特點: 把所有 >= 0.5 信心的資訊全數餵給模型")

    print("\n【Epistemic Kernel 策略】")
    print(f"  納入宣告數: {len(epistemic_claims)}")
    print(f"  估計 Token 數: {epistemic_tokens}")
    print(f"  阻斷的宣告數: {stats['blocked_by_contention']}")
    print(f"  是否觸發高嚴重性衝突阻斷: {'是' if stats['has_blocking_contention'] else '否'}")

    print("\n【節省效果】")
    saved_count = len(naive_claims) - len(epistemic_claims)
    saved_tokens = naive_tokens - epistemic_tokens
    reduction_pct = (saved_tokens / naive_tokens * 100) if naive_tokens > 0 else 0

    print(f"  減少的宣告數: {saved_count}")
    print(f"  減少的估計 Token: {saved_tokens}")
    print(f"  Token 減少比例: {reduction_pct:.1f}%")

    print("\n【質性洞察】")
    if stats['has_blocking_contention']:
        print("  - Epistemic Kernel 成功偵測到高風險衝突（LocalStorage vs HttpOnly Cookie、HS256 風險）")
        print("  - Naive 策略會把互相矛盾的資訊同時餵給模型，增加幻覺與不一致風險")
        print("  - Epistemic 在衝突未解決前主動減少後續推理量，符合「不確定性優先」原則")
    else:
        print("  - 本次實驗未觸發強烈阻斷，差異主要來自信心門檻過濾")

    print("\n" + "=" * 70)
    print("實驗結束。")
    print("=" * 70 + "\n")


def main():
    claims, contentions = create_jwt_security_scenario()

    # Naive 策略
    naive_selected = naive_strategy(claims, min_confidence=0.50)
    naive_tokens = estimate_total_tokens(naive_selected)

    # Epistemic 策略
    epistemic_selected, stats = epistemic_strategy(claims, contentions)
    epistemic_tokens = estimate_total_tokens(epistemic_selected)

    # 輸出報告
    print_report(
        naive_claims=naive_selected,
        epistemic_claims=epistemic_selected,
        stats=stats,
        naive_tokens=naive_tokens,
        epistemic_tokens=epistemic_tokens
    )


if __name__ == "__main__":
    main()
