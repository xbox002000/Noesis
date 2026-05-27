"""
Layer 2 + Layer 1 整合實用示範（使用高階類別 EpistemicSemanticGraph）

推薦的使用方式已經大幅簡化。

執行方式：
    cd D:\Antigravity\grok-wt
    $env:PYTHONPATH="D:\Antigravity\grok-wt"; python -m semantic_graph.demo
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from experiments.token_saving.scenario import create_jwt_security_scenario
from epistemic_kernel import EpistemicKernel
from semantic_graph import EpistemicSemanticGraph


def run_layer1_layer2_integration_demo():
    """展示 Layer 1 與 Layer 2 的整合流程"""
    print("=== Layer 1 + Layer 2 整合示範（JWT 安全審查情境）===\n")

    # 1. 準備資料（重用之前的 JWT 情境）
    claims, contentions = create_jwt_security_scenario()

    # 2. 建立 Epistemic Kernel 並餵入資料 + 衝突
    kernel = EpistemicKernel()
    for claim in claims:
        kernel.add_claim(claim.concept, claim.confidence, claim.source)

    for cont in contentions:
        kernel.register_contention(
            claim_a=cont["claim_a"],
            claim_b=cont["claim_b"],
            description=cont["description"],
            severity=cont["severity"]
        )

    print("【步驟 1】Epistemic Kernel 狀態")
    kernel.get_state_summary()

    # 3. 使用高階類別 EpistemicSemanticGraph（推薦用法）
    print("\n【步驟 2】使用 EpistemicSemanticGraph 進行整合")
    engine = EpistemicSemanticGraph()
    report = engine.ingest_from_kernel(kernel, claims)
    print(f"  整合報告: {report}")

    print("\n=== 實用方法示範 ===")
    conflicted = engine.get_scus_with_active_contention()
    high_risk = engine.get_high_risk_scus()
    print(f"  有活躍衝突的 SCU 數量: {len(conflicted)}")
    print(f"  高風險 SCU 數量: {len(high_risk)}")

    print("\n=== Graph 摘要 ===")
    for k, v in engine.get_summary().items():
        print(f"  {k}: {v}")

    print("\n=== 單一 SCU 範例（已帶有 Layer 1 epistemic 資訊） ===")
    example = engine.get_scu_by_concept("Refresh Token 儲存在 LocalStorage（方便）")
    if example:
        print(f"  SCU: {example.concept}")
        print(f"  Confidence: {example.confidence}")
        print(f"  Uncertainty Type: {example.uncertainty_type}")
        print(f"  Active Contentions: {example.active_contentions}")

    print("\n=== 示範結束 ===")
    print("透過 EpistemicSemanticGraph，使用者可以很乾淨地使用 Layer 1 + Layer 2 的組合能力。")


def bootstrap_stub():
    """Bootstrap 方向說明（已大幅強化）"""
    print("\n=== Bootstrap 設計（semantic_graph/bootstrap.py） ===")
    print("已建立三階段介面（對應藍圖）：")
    print("  1. StructuralAnalyzer     （完整，含複雜度、呼叫圖、模組依賴）")
    print("  2. SemanticClusterer      （雙模式）")
    print("       - heuristic（預設）：package + 呼叫圖 + 名稱主題，強健快速")
    print("       - features（實驗）：sklearn 結構特徵向量 + AgglomerativeClustering")
    print("  3. SCUGenerator + 關係推斷")
    print("       - 自動產生高品質概念名稱")
    print("       - 自動建立跨 SCU 的 depends_on / enables 關係")
    print("高階入口：bootstrap_from_codebase(..., clustering_method='heuristic'|'features')")
    print("目前狀態：Layer 2 冷啟動已具實用價值，可直接餵給 Layer 3 Context Compiler。")


def main():
    run_layer1_layer2_integration_demo()
    bootstrap_stub()


if __name__ == "__main__":
    main()
