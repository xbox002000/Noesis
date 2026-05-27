"""
LLM Quality A/B Test Framework
Layer 2 Bootstrap + Layer 3 Context Builder → Real LLM Evaluation

Purpose:
Move beyond token counting to measure actual answer *quality* when using
different context assembly strategies.

Variants compared (for each task):
  A. Naive All SCUs          — Dump every SCU the bootstrap produced
  B. High-Confidence Only    — Only SCUs with confidence >= 0.70
  C. Smart Context Builder   — Epistemic + Graph-enhanced (recommended)

This script generates ready-to-paste prompts for each variant so you can
feed them to any LLM (including Grok) and compare the outputs.

Usage:
    cd D:\Antigravity\grok-wt
    $env:PYTHONPATH="D:\Antigravity\grok-wt"; python -m experiments.llm_quality_ab_test

    # Optional: generate prompts only for specific task
    python -m experiments.llm_quality_ab_test --task 0   # Task A only

After generation, you can copy any prompt and ask me (Grok) to answer it.
We can then score the responses together using the rubric below.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from semantic_graph.bootstrap import bootstrap_from_codebase
from semantic_graph import EpistemicSemanticGraph
from experiments.token_efficient_context.builder import TokenEfficientContextBuilder


TASKS = [
    {
        "id": "A",
        "name": "理解 Epistemic Kernel 核心機制",
        "query": "解釋 Epistemic Kernel 如何進行信心傳遞（confidence propagation）與衝突處理。請特別說明系統如何偵測失敗模式，以及它對下游推理的影響。",
        "boost": ["confidence", "propagate", "contention", "failure", "kernel"],
    },
    {
        "id": "B",
        "name": "了解 Bootstrap 流程與強化",
        "query": "Semantic Graph 的 bootstrap 流程包含哪些階段？目前 heuristic 模式與 features 模式各有什麼優缺點？實際使用時推薦哪一種？",
        "boost": ["bootstrap", "cluster", "heuristic", "features", "scu"],
    },
    {
        "id": "C",
        "name": "Token 效率與 Context Compiler 設計哲學",
        "query": "目前 TokenEfficientContextBuilder 結合 Layer 1（Epistemic Kernel）與 Layer 2（Semantic Graph）後，在 token 節省與推理品質上帶來什麼具體優勢？為什麼這比傳統 RAG 或直接塞原始碼更好？",
        "boost": ["token", "context", "efficient", "layer", "builder"],
    },
    {
        "id": "D",
        "name": "衝突與關係推斷的實務價值",
        "query": "專案中如何實作了跨 SCU 的 depends_on / enables 關係推斷？這些關係在實際任務中如何被 Context Builder 利用？請舉例說明。",
        "boost": ["depends_on", "relationship", "contention", "graph", "enables"],
    },
]

QUALITY_RUBRIC = """
### LLM 回答品質評估量表（滿分 10 分）

請針對每個回答從以下 5 個維度打分（0-2 分）：

1. **事實正確性 (Factual Accuracy)**
   - 2 = 幾乎沒有錯誤，對專案細節掌握精準
   - 1 = 大方向正確，但有少數細節錯誤或混淆
   - 0 = 明顯錯誤或嚴重誤解

2. **Epistemic 誠實度 (Epistemic Honesty)**
   - 2 = 主動提到不確定性、衝突、知識邊界，或指出需要更多資訊
   - 1 = 偶爾承認不確定，但不夠明確
   - 0 = 從頭到尾都表現得「我什麼都知道」，從不提限制

3. **衝突與關係意識 (Conflict & Relationship Awareness)**
   - 2 = 清楚指出專案中存在的衝突、依賴關係，並說明其影響
   - 1 = 提到部分關係，但不深入
   - 0 = 把所有資訊當成獨立事實處理，完全忽略專案內的語義關係

4. **聚焦度與信噪比 (Focus & Signal-to-Noise)**
   - 2 = 回答高度針對問題，幾乎沒有廢話
   - 1 = 包含一些無關內容，但主軸清楚
   - 0 = 資訊過載，充滿低價值細節

5. **實用性與洞察深度 (Actionability & Insight)**
   - 2 = 提供有價值的洞見、架構建議，或明確指出下一步該看哪裡
   - 1 = 回答正確但較為表面
   - 0 = 只是複述資訊，缺乏洞察

**總分計算**：5 個維度加總（滿分 10 分）
建議分數帶：
- 9-10：優秀（可直接用於重要決策）
- 7-8 ：良好（需要少量人工校正）
- 5-6 ：普通（資訊不完整或有噪音）
- 0-4 ：不推薦使用
"""


def build_graph_and_builder(clustering_method: str = "heuristic"):
    print(f"[Setup] 執行 Bootstrap（{clustering_method} 模式）...")
    scus = bootstrap_from_codebase(".", clustering_method=clustering_method)

    print(f"[Setup] 載入 {len(scus)} 個 SCU 進入 EpistemicSemanticGraph...")
    graph = EpistemicSemanticGraph()
    graph.ingest_scus(scus)

    builder = TokenEfficientContextBuilder(graph=graph)
    print("[Setup] Context Builder 就緒\n")
    return builder, scus


def generate_prompt_variant(
    builder: TokenEfficientContextBuilder,
    task: dict,
    variant: str,
    honesty_level: str = "medium"
) -> str:
    """
    產生特定變體的完整 prompt。

    honesty_level 只對 B 類高信心變體有效：
        - "low"   : 傳統簡單高信心列表（最弱 epistemic 訊號）
        - "medium": 使用 builder 的 medium 模式（推薦，含豐富 Epistemic Note + Borderline）
        - "high"  : 使用 builder 的 high 模式（最強訊號）
    """
    system_instruction = (
        "You are a senior AI systems architect who is extremely careful about uncertainty, "
        "conflicts in information, and the cost of reasoning. "
        "You always surface what you know, what you don't know, and any contradictions you detect."
    )

    if variant == "A_naive_all":
        all_scus_text = "\n".join(
            f"- {s.concept}\n  Domain: {s.domain}\n  Relationships: {s.relationships}"
            for s in builder.graph.graph.scus.values()
        )
        context = f"以下是從程式碼庫 bootstrap 出的所有知識單元（未經任何過濾）：\n\n{all_scus_text}"
        prompt = builder.format_as_prompt(
            type("obj", (object,), {"context": context, "estimated_tokens": 0, "included_scus": [], "excluded_reason": {}})(),
            system_instruction=system_instruction
        )

    elif variant.startswith("B_high_conf"):
        # B 類現在支援不同誠實等級
        level = honesty_level.lower()
        if level == "low":
            # 傳統簡單高信心列表（最弱訊號）
            high_conf_scus = [s for s in builder.graph.graph.scus.values() if s.confidence >= 0.70]
            high_text = "\n".join(f"- {s.concept} (conf={s.confidence:.2f})" for s in high_conf_scus)
            context = f"以下是高信心（≥0.70）的知識單元：\n\n{high_text}"
            prompt = builder.format_as_prompt(
                type("obj", (object,), {"context": context, "estimated_tokens": 0, "included_scus": [], "excluded_reason": {}})(),
                system_instruction=system_instruction
            )
        else:
            # 使用 builder + 指定 honesty level（medium / high）
            prompt = builder.get_prompt_for_task(
                task_description=task["query"],
                max_tokens=800,
                min_confidence=0.60,
                min_relevance=0.10,
                use_graph_propagation=True,
                boost_terms=task["boost"],
                epistemic_honesty_level=level,
            )

    elif variant == "C_smart":
        result = builder.build_context_for_task(
            task_description=task["query"],
            max_tokens=800,
            min_confidence=0.60,
            min_relevance=0.10,
            use_graph_propagation=True,
            boost_terms=task["boost"],
        )
        prompt = builder.format_as_prompt(result, system_instruction=system_instruction)

    else:
        raise ValueError(f"Unknown variant: {variant}")

    return prompt


def main():
    parser = argparse.ArgumentParser(description="LLM Quality A/B Test Prompt Generator")
    parser.add_argument(
        "--task", type=int, default=None,
        help="只產生特定任務的 prompt（0=A, 1=B, 2=C, 3=D）"
    )
    parser.add_argument(
        "--method", choices=["heuristic", "features"], default="heuristic",
        help="使用的 bootstrap 聚類模式"
    )
    parser.add_argument(
        "--honesty-level", choices=["low", "medium", "high"], default="medium",
        dest="honesty_level",
        help="B 類高信心變體使用的 epistemic honesty 等級（預設 medium）"
    )
    args = parser.parse_args()

    output_dir = Path("experiments/ab_prompts")
    output_dir.mkdir(parents=True, exist_ok=True)

    builder, scus = build_graph_and_builder(args.method)

    tasks_to_run = TASKS if args.task is None else [TASKS[args.task]]

    print("=" * 70)
    print("LLM Quality A/B Test — Prompt Generation")
    print(f"聚類模式：{args.method}")
    print(f"Epistemic Honesty Level：{args.honesty_level}")
    print(f"SCU 總數：{len(scus)}")
    print("=" * 70)

    for task in tasks_to_run:
        print(f"\n【產生任務 {task['id']}】{task['name']}")
        print(f"問題：{task['query'][:80]}...")

        variants = {
            "A_naive_all": "Naive（所有 SCU）",
            "B_high_conf": f"High-Conf ({args.honesty_level})",
            "C_smart": "Smart Context Builder（推薦）",
        }

        for var_key, var_name in variants.items():
            prompt = generate_prompt_variant(builder, task, var_key, honesty_level=args.honesty_level)

            # 檔案命名包含 honesty level（特別對 B 類有意義）
            honesty_suffix = f"_{args.honesty_level}" if var_key.startswith("B") else ""
            filename = f"Task{task['id']}_{var_key}{honesty_suffix}_{args.method}.txt"
            filepath = output_dir / filename
            filepath.write_text(prompt, encoding="utf-8")

            token_estimate = len(prompt) // 3   # rough
            print(f"  [OK] {var_name:32} -> {filename}  (~{token_estimate} tokens)")

    print("\n" + "=" * 70)
    print("Prompts 已全部產生，位置：experiments/ab_prompts/")
    print("\n使用方式：")
    print("  1. 打開其中一個 .txt 檔案")
    print("  2. 複製全部內容貼給我（Grok）或其他 LLM")
    print("  3. 請 LLM 回答問題")
    print("  4. 使用下方量表評分並記錄")
    print("=" * 70)

    print(QUALITY_RUBRIC)

    print("\n建議下一步：")
    print("  - 選一個任務（例如 Task A）")
    print("  - 讓我用 C_smart 版本回答一次")
    print("  - 再讓我用不同 honesty level 的 B 版本回答同樣問題")
    print("  - 我們一起用上面的量表做系統化對比")


if __name__ == "__main__":
    main()