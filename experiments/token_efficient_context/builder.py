"""
Token-Efficient Context Builder

A lightweight utility that uses your existing EpistemicSemanticGraph
(Layer 1 + Layer 2) to assemble compact, high-signal context for LLM calls.

Recommended for real agent workflows:
- Build and maintain one EpistemicSemanticGraph for your codebase/knowledge.
- For each task, use this builder to extract only the most relevant + epistemically trustworthy SCUs.
- This gives you both token savings and better reasoning (avoids low-confidence and conflicted information).

Core usage pattern:

    from semantic_graph import EpistemicSemanticGraph
    from experiments.token_efficient_context.builder import (
        TokenEfficientContextBuilder,
        estimate_tokens
    )

    # 1. You maintain one graph (ingest your code / documents / previous reasoning)
    graph = EpistemicSemanticGraph()
    # ... your ingestion logic here ...

    # 2. For any task, build a focused context
    builder = TokenEfficientContextBuilder(graph=graph)

    result = builder.build_context_for_task(
        "Review the authentication logic for security issues",
        max_tokens=1500
    )

    prompt = builder.format_as_prompt(
        result,
        system_instruction="You are a senior security engineer."
    )

    # 3. Send `prompt` to the LLM. You get much smaller, higher-quality context.
"""



from typing import List, Optional, Dict
from dataclasses import dataclass

# Reuse our existing production-grade components
from epistemic_kernel import EpistemicKernel
from semantic_graph import EpistemicSemanticGraph, SCU

# Simple but reasonable token estimator (same spirit as previous experiment, improved)
def estimate_tokens(text: str) -> int:
    """
    Rough but practical token estimator.
    - English: ~4 chars per token
    - Chinese: ~1.7-2 chars per token (more information-dense)
    """
    if not text:
        return 0
    chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other = len(text) - chinese
    return int(chinese * 1.8 + other * 0.28) or 1


@dataclass
class ContextResult:
    context: str
    estimated_tokens: int
    included_scus: List[str]
    excluded_reason: Dict[str, int]   # e.g. {"low_confidence": 3, "active_contention": 2}


class TokenEfficientContextBuilder:
    """
    Token-Efficient Context Builder

    A practical utility that uses Epistemic Kernel (Layer 1) + Semantic Graph (Layer 2)
    to assemble high-signal, low-token context for LLM calls.

    Designed to be easy to integrate into real agent workflows.

    Typical usage:
        from semantic_graph import EpistemicSemanticGraph
        from experiments.token_efficient_context.builder import TokenEfficientContextBuilder

        # You already have a populated graph from your agent
        my_graph = EpistemicSemanticGraph()
        # ... ingest your SCUs / kernel data into my_graph ...

        builder = TokenEfficientContextBuilder(graph=my_graph)
        context = builder.build_context_for_task(
            user_query="Review the authentication logic for security issues",
            max_tokens=1200
        )
        prompt = builder.format_as_prompt(context, system_instruction="You are a senior security engineer.")
    """

    def __init__(
        self,
        graph: Optional[EpistemicSemanticGraph] = None,
        default_min_confidence: float = 0.65,
        default_min_relevance: float = 0.15,
        default_use_graph_propagation: bool = True,
    ):
        """
        Args:
            graph: Your long-lived EpistemicSemanticGraph (recommended).
            default_min_confidence: Default epistemic quality filter.
            default_min_relevance: Default semantic relevance filter.
            default_use_graph_propagation: Whether to use graph neighbors by default.
        """
        self.graph = graph or EpistemicSemanticGraph()
        self._has_data = len(self.graph.graph.scus) > 0 if graph else False

        # Store sensible defaults so agents don't have to repeat parameters every call
        self.default_min_confidence = default_min_confidence
        self.default_min_relevance = default_min_relevance
        self.default_use_graph_propagation = default_use_graph_propagation

    def ingest_graph(self, graph: EpistemicSemanticGraph):
        """Replace the internal graph with a pre-populated one (recommended for real usage)."""
        self.graph = graph
        self._has_data = len(self.graph.graph.scus) > 0

    def ingest_scus(self, scus: List[SCU]) -> int:
        """
        直接從 bootstrap 或其他 Layer 2 來源加入 SCU。
        這是目前把冷啟動知識圖接入 Context Builder 最乾淨的方式。
        """
        count = self.graph.ingest_scus(scus)
        self._has_data = True
        return count

    def seed_with_jwt_scenario(self):
        """
        Convenience method for demos and experiments.
        Seeds the builder with the classic JWT security review scenario.
        Not intended for production agent use.
        """
        from experiments.token_saving.scenario import create_jwt_security_scenario
        claims, contentions = create_jwt_security_scenario()

        kernel = EpistemicKernel()
        for c in claims:
            kernel.add_claim(c.concept, c.confidence, c.source)
        for cont in contentions:
            kernel.register_contention(
                claim_a=cont["claim_a"],
                claim_b=cont["claim_b"],
                description=cont["description"],
                severity=cont["severity"]
            )

        self.graph.ingest_from_kernel(kernel, claims)
        self._has_data = True
        print("[TokenEfficientContextBuilder] (Demo) Seeded with JWT scenario.")

    def _compute_relevance(
        self,
        scu: SCU,
        task_description: str,
        boost_terms: Optional[list[str]] = None,
    ) -> float:
        """
        Relevance scoring between a task and an SCU.

        Combines:
        - Word/phrase overlap (concept + domain)
        - Epistemic quality (confidence, no active contentions)
        - Optional boost for important terms
        - Light graph awareness (via propagation in the caller)

        Returns a score roughly in [0, ~2.0].
        """
        task_lower = task_description.lower()
        task_words = set(task_lower.split())

        if not task_words:
            return 0.0

        concept_lower = scu.concept.lower()
        concept_words = set(concept_lower.split())
        domain_text = " ".join(scu.domain).lower()
        domain_words = set(domain_text.split())

        # Improved overlap: reward consecutive phrase matches
        phrase_boost = 0.0
        task_phrases = self._extract_simple_phrases(task_lower)
        for phrase in task_phrases:
            if phrase in concept_lower or phrase in domain_text:
                phrase_boost += 0.15

        # Base Jaccard-style overlap
        intersection = len(task_words & (concept_words | domain_words))
        union = len(task_words | (concept_words | domain_words))
        base_overlap = intersection / union if union > 0 else 0.0

        # Epistemic quality
        epistemic = scu.confidence
        if scu.active_contentions:
            epistemic *= 0.55

        # Boost terms (user or auto-provided important keywords)
        boost = 0.0
        terms_to_boost = boost_terms or []
        for term in terms_to_boost:
            if term.lower() in concept_lower or term.lower() in domain_text:
                boost += 0.12

        score = (base_overlap * 0.6 + phrase_boost) * epistemic + boost

        return min(score, 2.5)  # cap it

    def _extract_simple_phrases(self, text: str) -> list[str]:
        """Very lightweight phrase extraction for better matching."""
        words = text.split()
        phrases = []
        # bigrams
        for i in range(len(words) - 1):
            phrases.append(f"{words[i]} {words[i+1]}")
        return phrases + words  # include unigrams too

    def build_context_for_task(
        self,
        task_description: str,
        max_tokens: Optional[int] = None,
        min_confidence: float = 0.65,
        min_relevance: float = 0.15,
        include_epistemic_info: bool = True,
        use_graph_propagation: bool = True,
        propagation_decay: float = 0.35,
        boost_terms: Optional[list[str]] = None,
        epistemic_honesty_level: str = "medium",   # "low" | "medium" | "high"
    ) -> ContextResult:
        """
        The main method for real agent use.

        Selects a small set of high-value SCUs for the given task using both
        epistemic quality (Layer 1) and semantic/graph relevance (Layer 2).

        Args:
            task_description: What the agent needs to do.
            max_tokens: Hard budget for the returned context (rough estimate).
            min_confidence: Minimum confidence from the epistemic kernel.
            min_relevance: Minimum relevance score to the task.
            include_epistemic_info: Whether to append epistemic metadata to each item.
            use_graph_propagation: Whether to give bonus score to direct neighbors in the graph.
            propagation_decay: How much relevance decays when propagating to neighbors.

        Returns:
            ContextResult with the filtered context and metadata.

        epistemic_honesty_level:
            "low"   : Minimal signaling (current High-Conf style)
            "medium": Add clear epistemic note + cautious header (recommended for most cases)
            "high"  : Strongest signaling + full graph-enhanced framing (closest to Smart)
        """
        if not self._has_data:
            raise RuntimeError(
                "No data loaded. Use ingest_graph() with your EpistemicSemanticGraph, "
                "or seed_with_jwt_scenario() for demos."
            )

        # Structured exclusion tracking for better Epistemic Notes (especially in Medium level)
        exclusions: dict[str, list] = {
            "low_confidence": [],      # list[SCU]
            "active_contention": [],   # list[SCU]
            "low_relevance": [],       # list[tuple[SCU, float]]  (SCU + relevance score)
        }

        task_lower = task_description.lower()

        # Step 1: Score all SCUs
        scored: list[tuple[SCU, float]] = []
        for scu in self.graph.graph.scus.values():
            if scu.confidence < min_confidence:
                exclusions["low_confidence"].append(scu)
                continue
            if scu.active_contentions:
                exclusions["active_contention"].append(scu)
                continue

            relevance = self._compute_relevance(scu, task_description)
            if relevance < min_relevance:
                exclusions["low_relevance"].append((scu, relevance))
                continue

            scored.append((scu, relevance))

        # Step 2: Optional graph propagation
        if use_graph_propagation:
            scored = self._apply_graph_propagation(scored, propagation_decay, min_confidence)

        # Step 3: Sort and truncate by token budget
        scored.sort(key=lambda x: x[1] * x[0].confidence, reverse=True)

        lines = []
        included = []
        current_tokens = 0

        header = f"Task: {task_description}\n\nRelevant knowledge (epistemically filtered + graph-enhanced):\n"
        current_tokens += estimate_tokens(header)
        lines.append(header)

        for scu, relevance in scored:
            entry = f"- {scu.concept}"
            if include_epistemic_info:
                entry += f" (conf={scu.confidence:.2f}, rel={relevance:.2f})"
                if scu.uncertainty_type:
                    entry += f" [uncertainty: {scu.uncertainty_type.value}]"
                if scu.active_contentions:
                    entry += " [has active contentions]"

            entry_tokens = estimate_tokens(entry)
            if max_tokens and current_tokens + entry_tokens > max_tokens:
                break

            lines.append(entry)
            included.append(scu.concept)
            current_tokens += entry_tokens

        context = "\n".join(lines)

        # === Identify Borderline SCUs for Medium honesty level (richer data) ===
        borderline_scus = []
        if epistemic_honesty_level.lower() in ("medium", "high"):
            borderline_candidates = []
            for scu in self.graph.graph.scus.values():
                if scu in [s for s, _ in scored]:
                    continue
                rel = self._compute_relevance(scu, task_description)
                # Borderline criteria: decent confidence + relevance close to threshold, or has minor issues
                if (scu.confidence >= min_confidence * 0.9 and rel >= min_relevance * 0.55) or \
                   (scu.confidence >= min_confidence and len(scu.active_contentions) > 0 and rel >= min_relevance * 0.4):
                    reason = []
                    if rel < min_relevance:
                        reason.append(f"相關性 {rel:.2f}（接近門檻）")
                    if scu.active_contentions:
                        reason.append(f"有 {len(scu.active_contentions)} 個活躍衝突")
                    if not reason:
                        reason.append("高信心但相關性邊緣")
                    borderline_candidates.append((scu, rel, "；".join(reason)))
            borderline_candidates.sort(key=lambda x: x[1], reverse=True)
            borderline_scus = borderline_candidates[:2]  # top 2 richest borderline cases

        # === Epistemic Honesty Layer ===
        top_scus_for_note = [scu for scu, _ in scored[:3]] if scored else []
        epistemic_header, epistemic_note = self._build_epistemic_framing(
            epistemic_honesty_level=epistemic_honesty_level,
            total_scus=len(self.graph.graph.scus),
            included_count=len(included),
            min_confidence=min_confidence,
            task_description=task_description,
            top_scus=top_scus_for_note,
            exclusions=exclusions,
            borderline_scus=borderline_scus,
        )

        # Build final header
        if epistemic_header:
            final_header = epistemic_header.format(task=task_description)
        else:
            final_header = f"Task: {task_description}\n\nRelevant knowledge (epistemically filtered + graph-enhanced):\n"

        # Rebuild lines with the new header
        lines = [final_header] + lines[1:] if lines else [final_header]
        context = "\n".join(lines)

        if epistemic_note:
            context = context + "\n\n" + epistemic_note

        # Convert new structured exclusions back to count format for ContextResult compatibility
        excluded_counts = {k: len(v) for k, v in exclusions.items()}

        return ContextResult(
            context=context,
            estimated_tokens=estimate_tokens(context),
            included_scus=included,
            excluded_reason=excluded_counts,
        )

    def _apply_graph_propagation(
        self,
        scored: list[tuple[SCU, float]],
        decay: float,
        min_confidence: float
    ) -> list[tuple[SCU, float]]:
        """Give small bonus to direct neighbors of highly relevant SCUs."""
        final_scores: dict[str, float] = {scu.id: rel for scu, rel in scored}

        for scu, relevance in scored:
            for rel_type, targets in scu.relationships.items():
                if rel_type == "conflicts_with":
                    continue
                for target_id in targets:
                    neighbor = self.graph.graph.get_scu(target_id)
                    if (
                        neighbor
                        and neighbor.id not in final_scores
                        and neighbor.confidence >= min_confidence
                        and not neighbor.active_contentions
                    ):
                        final_scores[neighbor.id] = relevance * decay

        # Rebuild list
        result = []
        for scu_id, score in final_scores.items():
            scu = self.graph.graph.get_scu(scu_id)
            if scu:
                result.append((scu, score))
        return result

    def _build_epistemic_framing(
        self,
        epistemic_honesty_level: str,
        total_scus: int,
        included_count: int,
        min_confidence: float,
        task_description: str = "",
        top_scus: list = None,
        exclusions: dict = None,
        borderline_scus: list = None,
    ) -> tuple[str, str]:
        """
        Returns (header, note) based on desired epistemic honesty level.
        Enhanced version with Chinese support and light relationship info for medium level.
        """
        level = epistemic_honesty_level.lower()
        is_chinese = any('\u4e00' <= c <= '\u9fff' for c in task_description)

        top_scus = top_scus or []

        if level == "low":
            if is_chinese:
                header = f"Task: {{task}}\n\n高信心知識（≥{min_confidence}）：\n"
            else:
                header = f"Task: {{task}}\n\nHigh-confidence knowledge (≥{min_confidence}):\n"
            note = ""
            return header, note

        elif level == "medium":
            if is_chinese:
                header = (
                    f"Task: {{task}}\n\n"
                    f"高信心知識（已過濾視圖 – 非完整知識）：\n"
                )
                note_lines = [
                    "**Epistemic Note（認知說明）**：",
                    f"- 本次上下文僅包含 {included_count} 個高信心 SCU（信心 ≥ {min_confidence}）。",
                    f"- 目前知識圖總共有 {total_scus} 個 SCU。",
                ]

                # === 新增：量化排除理由 ===
                exclusions = exclusions or {}
                reason_parts = []
                if exclusions.get("active_contention"):
                    reason_parts.append(f"{len(exclusions['active_contention'])} 個因存在活躍衝突")
                if exclusions.get("low_confidence"):
                    reason_parts.append(f"{len(exclusions['low_confidence'])} 個因信心低於門檻")
                if exclusions.get("low_relevance"):
                    reason_parts.append(f"{len(exclusions['low_relevance'])} 個因與任務相關性不足")

                if reason_parts:
                    note_lines.append(f"- 被排除的 SCU 原因：{ '、'.join(reason_parts) }。")
                else:
                    note_lines.append("- 這是刻意過濾後的子集。")

                # === 新增：更結構化且豐富的排除例子（每類最多 2 個，附詳細元數據）===
                example_lines = []
                for reason_key, items in exclusions.items():
                    if not items:
                        continue
                    reason_label = {
                        "low_relevance": "相關性不足",
                        "active_contention": "存在活躍衝突",
                        "low_confidence": "信心低於門檻",
                    }.get(reason_key, reason_key)

                    for item in items[:2]:
                        if reason_key == "low_relevance":
                            scu, rel = item
                            dep_info = scu.relationships.get("depends_on", [])[:2]
                            en_info = scu.relationships.get("enables", [])[:1]
                            dep_str = f"，依賴 {dep_info}" if dep_info else ""
                            en_str = f"，啟用 {en_info}" if en_info else ""
                            cont_str = f"，{len(scu.active_contentions)} 個衝突" if scu.active_contentions else ""
                            domain_str = f"，{scu.domain}" if scu.domain else ""
                            example_lines.append(
                                f"  • [{reason_label}] {scu.concept}（相關性 {rel:.2f}，信心 {scu.confidence:.2f}{domain_str}{dep_str}{en_str}{cont_str}）"
                            )
                        else:
                            scu = item
                            dep_info = scu.relationships.get("depends_on", [])[:2]
                            en_info = scu.relationships.get("enables", [])[:1]
                            dep_str = f"，依賴 {dep_info}" if dep_info else ""
                            en_str = f"，啟用 {en_info}" if en_info else ""
                            cont_str = f"，{len(scu.active_contentions)} 個衝突" if scu.active_contentions else ""
                            domain_str = f"，{scu.domain}" if scu.domain else ""
                            example_lines.append(
                                f"  • [{reason_label}] {scu.concept}（信心 {scu.confidence:.2f}{domain_str}{dep_str}{en_str}{cont_str}）"
                            )
                if example_lines:
                    note_lines.append("- 排除例子：")
                    note_lines.extend(example_lines)

                # === 新增：Borderline SCUs（大幅豐富資訊 + 納入價值） ===
                borderline_scus = borderline_scus or []
                if borderline_scus:
                    note_lines.append("\n- **Borderline SCUs（接近門檻但被刻意排除）**：")
                    for scu, rel, reason in borderline_scus:
                        deps = scu.relationships.get("depends_on", [])[:2]
                        enables = scu.relationships.get("enables", [])[:2]
                        dep_str = f"，依賴 {deps}" if deps else ""
                        en_str = f"，啟用 {enables}" if enables else ""
                        contentions = f"，有 {len(scu.active_contentions)} 個衝突" if scu.active_contentions else ""
                        domain_str = f"，領域 {scu.domain}" if scu.domain else ""
                        abs_str = f"，抽象層級 {scu.abstraction_level}"
                        sec_str = "，安全關鍵" if scu.security_critical else ""

                        # 簡單推斷納入價值
                        value_hint = ""
                        concept_lower = scu.concept.lower()
                        if any(k in concept_lower for k in ["graph", "scu", "bootstrap"]):
                            value_hint = "，若納入可強化整體知識結構理解"
                        elif any(k in concept_lower for k in ["context", "compiler", "token"]):
                            value_hint = "，若納入可改善上下文組裝品質"
                        elif "epistemic" in concept_lower or "state" in concept_lower:
                            value_hint = "，若納入可提升不確定性管理能力"

                        note_lines.append(
                            f"  • {scu.concept}（{reason}{dep_str}{en_str}{contentions}{domain_str}{abs_str}{sec_str}，信心 {scu.confidence:.2f}{value_hint}）"
                        )

                note_lines.append("- 請在回答時主動指出你的假設、知識缺口，以及需要哪些額外資訊才能給出更有信心的回答。")

                # === 新增：對本次任務的潛在影響（Potential Impact）- 更精準版 ===
                excluded_concepts = []
                excluded_domains = set()
                for items in (exclusions or {}).values():
                    for item in items:
                        scu = item[0] if isinstance(item, (list, tuple)) else item
                        excluded_concepts.append(scu.concept)
                        if hasattr(scu, 'domain') and scu.domain:
                            excluded_domains.update(scu.domain)

                impact_lines = []
                if excluded_concepts:
                    # 簡單關鍵字分析，產生更針對性的影響描述
                    focus_areas = []
                    concepts_text = " ".join(excluded_concepts).lower()
                    if any(k in concepts_text for k in ["graph", "scu", "bootstrap", "cluster"]):
                        focus_areas.append("整體知識結構與演化維護")
                    if any(k in concepts_text for k in ["context", "compiler", "token"]):
                        focus_areas.append("上下文組裝與 token 效率決策")
                    if any(k in concepts_text for k in ["epistemic", "state", "failure"]):
                        focus_areas.append("不確定性管理與失敗模式偵測")

                    if focus_areas:
                        impact_lines.append(f"因為缺少與 {', '.join(sorted(excluded_domains))} 相關的知識，")
                        impact_lines.append(f"你對「{ '、'.join(focus_areas)}」等面向的理解可能會比較片面或缺乏結構性視角。")
                    else:
                        impact_lines.append(f"因為缺少 {', '.join(sorted(excluded_domains))} 相關的知識，")
                        impact_lines.append("你對與這些領域高度相關的推理面向理解可能會比較片面或保守。")

                if borderline_scus:
                    bl_names = [scu.concept for scu, _, _ in borderline_scus[:2]]
                    impact_lines.append(f"若將 Borderline SCU（如 {', '.join(bl_names)}）納入，可能會補強你對知識圖整體結構與邊界案例的掌握。")

                if impact_lines:
                    note_lines.append("\n- **對本次任務的潛在影響**：")
                    note_lines.extend([f"  {line}" for line in impact_lines])

                # 為 medium 等級加入少量關係資訊
                if top_scus:
                    note_lines.append("\n- 部分核心 SCU 的主要依賴關係：")
                    for scu in top_scus[:3]:
                        deps = scu.relationships.get("depends_on", [])[:2]
                        if deps:
                            note_lines.append(f"  • {scu.concept} 依賴於: {deps}")

                note = "\n".join(note_lines)
            else:
                header = (
                    f"Task: {{task}}\n\n"
                    f"High-confidence knowledge (filtered view – not complete):\n"
                )
                note = (
                    f"**Epistemic Note**:\n"
                    f"- This context contains only {included_count} high-confidence SCUs (confidence ≥ {min_confidence}).\n"
                    f"- Total SCUs in the current knowledge graph: {total_scus}.\n"
                    f"- This is a deliberately filtered subset. Information outside these SCUs is either lower confidence, conflicted, or not yet considered relevant.\n"
                    f"- Please explicitly surface any assumptions, gaps, or areas where you would need additional knowledge to give a confident answer."
                )
                if top_scus:
                    note += "\n- Key dependencies among top SCUs:\n"
                    for scu in top_scus[:3]:
                        deps = scu.relationships.get("depends_on", [])[:2]
                        en = scu.relationships.get("enables", [])[:2]
                        dep_str = f"depends on {deps}" if deps else ""
                        en_str = f", enables {en}" if en else ""
                        note += f"  • {scu.concept}: {dep_str}{en_str}\n"
            return header, note

        elif level == "high":
            if is_chinese:
                header = f"Task: {{task}}\n\n相關知識（經認知過濾 + 圖關係增強）：\n"
                note = (
                    "**Epistemic Note（認知說明）**：\n"
                    "- 這是經過強力策展、具圖結構感知的上下文。\n"
                    "- 僅選取最相關且在認知上值得信賴的 SCU。\n"
                    "- 請以保守態度推理，並清楚說明基於此上下文你的知識邊界。"
                )
            else:
                header = f"Task: {{task}}\n\nRelevant knowledge (epistemically filtered + graph-enhanced):\n"
                note = (
                    f"**Epistemic Note**:\n"
                    f"- This is a strongly curated, graph-aware context.\n"
                    f"- Only the most relevant and epistemically trustworthy SCUs have been selected.\n"
                    f"- You are expected to reason conservatively and clearly state the limits of your knowledge based on this context."
                )
            return header, note

        else:
            return self._build_epistemic_framing("medium", total_scus, included_count, min_confidence, task_description, top_scus)

    def format_as_prompt(
        self,
        result: ContextResult,
        system_instruction: Optional[str] = None,
        include_exclusion_note: bool = False,
    ) -> str:
        """Turn a ContextResult into a ready-to-send prompt."""
        parts = []
        if system_instruction:
            parts.append(system_instruction.strip())
            parts.append("")

        parts.append(result.context)

        if include_exclusion_note and result.excluded_reason:
            note = "\n[Note: Some lower-value or conflicting information was filtered for token efficiency.]"
            parts.append(note)

        return "\n".join(parts)

    def estimate_tokens(self, text: str) -> int:
        """Expose the internal token estimator (useful for budgeting)."""
        return estimate_tokens(text)

    def get_prompt_for_task(
        self,
        task_description: str,
        system_instruction: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Convenience method that builds context and formats it as a ready-to-send prompt.

        This is the method most agents will call in a loop.

        You can pass `epistemic_honesty_level="medium"` (or "low"/"high") here.
        """
        result = self.build_context_for_task(task_description, **kwargs)
        return self.format_as_prompt(result, system_instruction=system_instruction)

    def __repr__(self):
        n = len(self.graph.graph.scus) if self.graph else 0
        return f"TokenEfficientContextBuilder(scus={n}, has_data={self._has_data})"
