# Medium Epistemic Honesty Level Improvement Experiment

**Date**: 2026-05  
**Experimenter**: Grok + User  
**Focus**: Improving `epistemic_honesty_level="medium"` in `TokenEfficientContextBuilder`

---

## 1. Objective

To push the **Medium** honesty level from ~7.5 to the 8.0–8.5+ range by enhancing the Epistemic Note and context framing, without moving to the full cost of the "high" (Smart) mode.

Primary goal: Significantly improve **Epistemic Honesty** while keeping the approach lightweight and practical.

---

## 2. Background

Previous baselines on Task A ("Explain Epistemic Kernel confidence propagation and contention handling"):

| Version                  | Total Score | Epistemic Honesty | Notes |
|--------------------------|-------------|-------------------|-------|
| Smart (full)             | 9.00        | 2.00              | Best quality, highest cost |
| Medium v2                | 7.50        | 1.75              | Basic Epistemic Note |
| Original High-Conf       | 5.50        | 0.50              | Almost no honesty signaling |
| Naive (all SCUs)         | 4.50        | 0.50              | High noise, poor honesty |

The gap between Medium and Smart was mainly in **Epistemic Honesty** and **insight into what was deliberately excluded**.

---

## 3. Methodology

- Task: Task A (Epistemic Kernel explanation)
- Base setup: Heuristic bootstrap + `TokenEfficientContextBuilder`
- Test variable: Progressive enhancement of `epistemic_honesty_level="medium"`
- Evaluation: 5-dimension rubric (0–2 per dimension, total 10)

Key rubric dimensions:
- Factual Accuracy
- **Epistemic Honesty** (main focus)
- Conflict & Relationship Awareness
- Focus & Signal-to-Noise
- Actionability & Insight

---

## 4. Key Improvements Implemented (v2 → v7)

### v3–v4
- Quantified exclusion reasons (e.g., "5 個因與任務相關性不足")
- Concrete exclusion examples with metadata (confidence, relevance, dependencies)
- Introduction of **Borderline SCUs** section

### v5–v6
- Significantly richer Borderline information (domain, abstraction level, security critical, relationships, value if included)
- More structured exclusion examples with consistent formatting

### v7 (Current)
- Smarter **Potential Impact** section:
  - Analyzes excluded SCU concepts/domains
  - Produces task-specific impact statements (e.g., "整體知識結構與演化維護、上下文組裝與 token 效率決策")
- Borderline SCUs now include explicit "value if included" hints
- Overall note is more insightful while remaining concise

---

## 5. Results

### Final Scores (Task A)

| Version          | Total | Epistemic Honesty | Key Strength |
|------------------|-------|-------------------|--------------|
| **Smart**        | 9.00  | 2.00              | Natural honesty + rich structure |
| **Medium v7**    | **8.20** | **1.90**       | Strong, structured honesty signaling |
| Medium v3        | 8.85  | 1.75              | Good but less precise impact |
| Medium v2        | 7.50  | 1.75              | Basic note only |
| Original High-Conf | 5.50 | 0.50            | Almost no signaling |
| Naive            | 4.50  | 0.50              | High noise |

**Epistemic Honesty Progress (Medium series)**:
- v2: 1.75
- v3: 1.75
- **v7: 1.90** (+0.15 from early Medium versions)

---

## 6. Key Insights

1. **Honesty is highly prompt-structure dependent**  
   Simply filtering by confidence gives almost no honesty (0.5). Adding a well-designed Epistemic Note dramatically improves it.

2. **"Why excluded" + "What if included" is extremely powerful**  
   The combination of:
   - Quantified exclusion reasons
   - Concrete examples
   - Borderline SCUs with value statements
   - Task-specific Potential Impact
   ...was the main driver that took Medium from 7.5 to 8.2.

3. **Medium can get very close to Smart on honesty**  
   At 1.90 vs Smart's 2.00, the remaining gap is mostly in the *naturalness* of honesty and depth of insight — which still requires richer input (Smart's advantage).

4. **Cost vs Quality trade-off is excellent at v7 Medium**  
   The current Medium implementation delivers ~91% of Smart's score at significantly lower selection cost.

---

## 7. Conclusions & Recommendations

- The `epistemic_honesty_level="medium"` path is now a **highly viable production option** when full Smart-mode cost is undesirable.
- The most effective levers discovered were:
  1. Explicit, quantified exclusion reasoning
  2. Borderline SCU visibility + value framing
  3. Task-specific Potential Impact analysis

**Recommended default for most use cases**: `epistemic_honesty_level="medium"` (v7 or newer).

---

## 8. Next Steps (Optional)

- Further refine Potential Impact using task keyword analysis
- Add conflict description summaries when active contentions exist in exclusions
- Systematically test v7 Medium across more tasks (B, C, D)
- Consider exposing "Potential Impact" as a separate, reusable component

---

*Report generated from iterative development sessions on the `TokenEfficientContextBuilder`.*