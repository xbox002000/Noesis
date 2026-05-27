"""
Layer 1 (Epistemic Kernel) ↔ Layer 2 (Semantic State Graph) 整合模組

這個模組負責讓兩個層級產生實質的連接，而不是各自獨立。
目前重點：
- 把 EpistemicKernel 的輸出轉成 SCU
- 讓 SCU 能承載來自 Kernel 的 epistemic 狀態
- 提供同步機制（含改善後的概念匹配）
"""

from typing import List, Dict, Optional
from epistemic_kernel import EpistemicKernel, KnowledgeClaim, UncertaintyType
from .models import SCU
from .graph import SCUGraph


def _normalize(text: str) -> str:
    """簡單正規化，用來改善概念匹配"""
    return text.lower().replace("（", "(").replace("）", ")").replace(" ", "").strip()


def find_best_matching_scu(concept: str, graph: SCUGraph) -> Optional[SCU]:
    """
    實用化的概念匹配函式。
    支援：完全匹配 → 子字串匹配 → 關鍵詞匹配（針對常見衝突描述）。
    """
    norm_concept = _normalize(concept)

    # 1. 完全匹配
    for scu in graph.scus.values():
        if _normalize(scu.concept) == norm_concept:
            return scu

    # 2. 子字串匹配（雙向）
    for scu in graph.scus.values():
        norm_scu = _normalize(scu.concept)
        if norm_concept in norm_scu or norm_scu in norm_concept:
            return scu

    # 3. 關鍵詞匹配（實用化加強）
    keywords = [w for w in norm_concept.split() if len(w) > 2]
    for scu in graph.scus.values():
        norm_scu = _normalize(scu.concept)
        match_count = sum(1 for kw in keywords if kw in norm_scu)
        if match_count >= 2 or (len(keywords) <= 2 and match_count >= 1):
            return scu

    return None


def create_scu_from_knowledge_claim(
    claim: KnowledgeClaim,
    kernel: Optional[EpistemicKernel] = None
) -> SCU:
    """
    核心整合函式：將 Layer 1 的 KnowledgeClaim 轉成 Layer 2 的 SCU。
    """
    scu = SCU(
        concept=claim.concept,
        confidence=claim.confidence,
        domain=["authentication", "security"],
        uncertainty_type=None,
        change_frequency="volatile",
        security_critical=True,
    )

    if kernel:
        for contention in kernel.state.active_contentions:
            if claim.concept in contention.claim_a or claim.concept in contention.claim_b:
                scu.uncertainty_type = UncertaintyType.CONTENTION
                if contention.description not in scu.active_contentions:
                    scu.active_contentions.append(contention.description)
                break

    return scu


def build_scus_from_kernel(
    kernel: EpistemicKernel,
    claims: List[KnowledgeClaim]
) -> List[SCU]:
    """批次轉換"""
    return [create_scu_from_knowledge_claim(claim, kernel) for claim in claims]


def sync_kernel_to_graph(
    graph: SCUGraph,
    kernel: EpistemicKernel,
    claims: List[KnowledgeClaim]
) -> Dict:
    """把 Kernel 狀態同步到 Graph（含改善匹配）"""
    report = {"scus_added": 0, "scus_updated": 0, "contentions_synced": 0}

    for claim in claims:
        # 使用改善後的匹配找到對應 SCU
        existing = graph.get_scu_by_concept(claim.concept) or find_best_matching_scu(claim.concept, graph)

        if existing:
            existing.confidence = claim.confidence

            # 檢查這個 SCU 是否參與 kernel 中的任何衝突
            for cont in kernel.state.active_contentions:
                norm_scu = _normalize(existing.concept)
                norm_a = _normalize(cont.claim_a)
                norm_b = _normalize(cont.claim_b)

                participates = (norm_a in norm_scu or norm_scu in norm_a or
                                norm_b in norm_scu or norm_scu in norm_b)

                if participates:
                    existing.uncertainty_type = UncertaintyType.CONTENTION
                    if cont.description not in existing.active_contentions:
                        existing.active_contentions.append(cont.description)
                    report["contentions_synced"] += 1
                    break

            report["scus_updated"] += 1
        else:
            scu = create_scu_from_knowledge_claim(claim, kernel)
            graph.add_scu(scu)
            report["scus_added"] += 1

    return report


def enrich_graph_with_kernel_contentions(graph: SCUGraph, kernel: EpistemicKernel):
    """
    實用化版本：將 kernel 中的衝突同時做到兩件事：
    1. 盡量建立 SCU 之間的 conflicts_with 關係
    2. 把衝突描述附加到相關 SCU 的 active_contentions（這部分比較可靠）
    """
    for contention in kernel.state.active_contentions:
        scu_a = find_best_matching_scu(contention.claim_a, graph)
        scu_b = find_best_matching_scu(contention.claim_b, graph)

        # 盡量建立雙向關係（如果兩邊都找得到）
        if scu_a and scu_b:
            graph.add_relationship(scu_a.id, "conflicts_with", scu_b.id)
            graph.add_relationship(scu_b.id, "conflicts_with", scu_a.id)

        # 無論如何，盡量把衝突資訊附加到找得到的 SCU 上（這是更實用的部分）
        for scu in [scu_a, scu_b]:
            if scu:
                if contention.description not in scu.active_contentions:
                    scu.active_contentions.append(contention.description)
                scu.uncertainty_type = UncertaintyType.CONTENTION


def link_kernel_contentions_to_scus(graph: SCUGraph, kernel: EpistemicKernel):
    """
    實用化輔助函式：強制將 kernel 的所有衝突附加到相關 SCU 的 active_contentions。
    這是為了讓整合在真實資料不完美匹配時也能立即產生價值。
    """
    linked_count = 0
    for contention in kernel.state.active_contentions:
        for scu in graph.scus.values():
            norm_scu = _normalize(scu.concept)
            norm_a = _normalize(contention.claim_a)
            norm_b = _normalize(contention.claim_b)

            if (norm_a in norm_scu or norm_scu in norm_a or
                norm_b in norm_scu or norm_scu in norm_b):
                if contention.description not in scu.active_contentions:
                    scu.active_contentions.append(contention.description)
                scu.uncertainty_type = UncertaintyType.CONTENTION
                linked_count += 1
    return linked_count


def integrate_kernel_into_graph(
    graph: SCUGraph,
    kernel: EpistemicKernel,
    claims: List[KnowledgeClaim]
) -> Dict:
    """
    高階實用函式：一鍵完成 Kernel 與 Graph 的完整同步 + 衝突連結。
    這是目前推薦給外部使用的主要入口。
    """
    report = sync_kernel_to_graph(graph, kernel, claims)
    enrich_graph_with_kernel_contentions(graph, kernel)
    linked = link_kernel_contentions_to_scus(graph, kernel)
    report["contentions_linked_via_helper"] = linked
    return report
