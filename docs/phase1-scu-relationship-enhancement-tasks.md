# Phase 1: SCU Relationship Enhancement - Development Tasks

**Goal**: Significantly improve the quantity, quality, and diversity of relationships between SCUs in the Semantic Graph, laying the foundation for more powerful Epistemic Notes in Layer 3 (especially `epistemic_honesty_level="medium"` and `"high"`).

**Overall Phase 1 Target**:
- Increase average number of relationships per SCU by at least 2x
- Introduce relationship strength (`strength`) and confidence
- Add module-level and class-level relationships
- Establish clean data structures and cleanup mechanisms

**Recommended Execution Order**:
1. 1.4 (Data structure) → 1.1 + 1.5 → 1.2 + 1.3

---

## Task 1.4: Introduce Relationship Strength and Structured Storage

**ID**: `phase1-1.4`  
**Priority**: High  
**Effort**: Easy → Medium (2–3 days)  
**Component**: Models + Bootstrap

### Description
Currently, `SCU.relationships` is stored as `Dict[str, List[str]]`. This is too limited for future needs (strength, confidence, source, etc.).

We need to evolve the storage format while maintaining backward compatibility where possible.

### Acceptance Criteria
- [ ] Define a clear structure for individual relationships (recommend using `Dict` or a small dataclass)
- [ ] Update `SCU.add_relationship()` to accept `strength`, `confidence`, `source`, and other metadata
- [ ] Update `SCUGraph.add_relationship()` and related methods
- [ ] Update `infer_cross_scu_relationships` to pass initial strength values
- [ ] Existing code that reads relationships continues to work (or has a clear migration path)
- [ ] Add basic validation (e.g., strength between 0.0 and 1.0)

### Suggested Data Structure

```python
# Recommended
relationships: Dict[str, List[Dict[str, Any]]]

# Example:
{
    "depends_on": [
        {
            "id": "scu_abc123",
            "strength": 0.85,
            "confidence": 0.9,
            "source": "function_call"
        }
    ]
}
```

### Dependencies
- None (foundational task)

### Files to Modify
- `semantic_graph/models.py`
- `semantic_graph/graph.py`
- `semantic_graph/bootstrap.py` (call sites)

### Unit Test Focus
- Test adding relationships with and without metadata
- Test updating strength on duplicate relationships
- Test backward compatibility when reading old-format data (if we keep support)
- Test validation of strength/confidence values

---

## Task 1.1: Strengthen Existing Call-Graph Relationship Inference

**ID**: `phase1-1.1`  
**Priority**: High  
**Effort**: Medium (4–6 days)  
**Component**: Bootstrap / Relationship Inference

### Description
The current `infer_cross_scu_relationships` only uses simple function name matching from `CodeFunction.calls`. This misses many real call relationships.

### Acceptance Criteria
- [ ] Function calls are resolved using import information (support `from x import y` style)
- [ ] Cross-file same-name functions are disambiguated where possible
- [ ] Basic support for indirect calls through variables/parameters (at least simple cases)
- [ ] Relationship strength is calculated (e.g., based on call frequency within a function)
- [ ] Performance remains acceptable on medium-sized codebases

### Suggested New/Refactored Functions

```python
def build_function_to_scu_index(
    scus: List[SCU], 
    all_functions: List[CodeFunction]
) -> Dict[str, str]:
    """Build a robust mapping from function name → SCU id, using import info for disambiguation."""

def resolve_call_target(
    call_name: str, 
    current_func: CodeFunction,
    all_functions: List[CodeFunction]
) -> Optional[str]:
    """Resolve a call to the most likely target function name."""
```

### Dependencies
- Task 1.4 (relationship data structure)

### Files to Modify
- `semantic_graph/bootstrap.py` (main work)
- Possibly add helper methods to `CodeFunction` or `CodebaseAnalysis`

### Unit Test Focus
- Cross-file function resolution using imports
- Same-name functions in different modules
- Simple variable-based indirect calls
- Strength calculation correctness

---

## Task 1.5: Relationship Normalization and Cleanup

**ID**: `phase1-1.5`  
**Priority**: Medium-High  
**Effort**: Easy → Medium (2–3 days)  
**Component**: Bootstrap / Utilities

### Description
After relationship inference, we need a reliable cleanup pass to remove duplicates, self-loops, and weak relationships.

### Acceptance Criteria
- [ ] A dedicated `normalize_relationships(scu: SCU)` function exists
- [ ] Duplicate relationships are removed
- [ ] Self-referential relationships (`A depends_on A`) are filtered
- [ ] Weak relationships can be optionally pruned based on strength threshold
- [ ] Cleanup is automatically called at the end of bootstrap process
- [ ] A utility function `get_relationship_stats(scus)` is available for debugging

### Dependencies
- Task 1.4 (needs the new relationship structure)

### Files to Modify
- `semantic_graph/bootstrap.py` (add cleanup logic + call site)

### Unit Test Focus
- Duplicate removal
- Self-dependency filtering
- Weak relationship pruning with different thresholds
- Statistics function correctness

---

## Task 1.2: Add Module-Level Dependency Relationships

**ID**: `phase1-1.2`  
**Priority**: Medium  
**Effort**: Medium (3–4 days)  
**Component**: Bootstrap

### Description
Leverage the existing `CodebaseAnalysis.module_graph` to create module-level `depends_on` relationships between SCUs.

### Acceptance Criteria
- [ ] SCUs belonging to modules that import each other get module-level `depends_on` relationships
- [ ] Module-level relationships are distinguished from function-level ones (via `source` field)
- [ ] No excessive duplication with function-level relationships
- [ ] Module-level relationships have reasonable strength values

### Dependencies
- Task 1.4 (relationship structure)
- Access to `CodebaseAnalysis.module_graph`

### Files to Modify
- `semantic_graph/bootstrap.py`

### Unit Test Focus
- Module import relationships are correctly reflected in SCUs
- Distinction between function-level and module-level relationships

---

## Task 1.3: Add Class-Level Inheritance and Composition Relationships

**ID**: `phase1-1.3`  
**Priority**: Medium  
**Effort**: Medium → Hard (4–6 days)  
**Component**: Bootstrap

### Description
Use `CodeClass.bases` and class structure to create `inherits_from` and basic composition relationships.

### Acceptance Criteria
- [ ] Class inheritance is correctly mapped to SCU-level `inherits_from` relationships
- [ ] Basic composition relationships (classes containing instances of other classes) are detected where feasible
- [ ] Relationships are properly attached to the owning SCU(s)

### Dependencies
- Task 1.4
- `CodeClass` data from `StructuralAnalyzer`

### Files to Modify
- `semantic_graph/bootstrap.py`

### Unit Test Focus
- Single and multiple inheritance cases
- Correct mapping when classes and functions live in the same SCU
- Handling of external base classes (e.g., `object`, third-party classes)

---

## Cross-Cutting Tasks

| ID | Task | Description | Effort | Notes |
|----|------|-------------|--------|-------|
| **1.X** | Update `SCUGraph` methods | Ensure `add_relationship`, `get_related`, etc. work with the new relationship format | Medium | Critical for downstream usage |
| **1.Y** | Add relationship statistics utility | `get_relationship_stats(scus) -> dict` for debugging and monitoring | Easy | Very useful during development |
| **1.Z** | Documentation & Examples | Update docstrings and add a small example showing the new relationship structure | Easy | Important for maintainability |

---

## Summary & Recommendations

**Must-do in Phase 1**:
- 1.4 (Data structure)
- 1.1 (Call graph improvement)
- 1.5 (Cleanup)

**Strongly recommended**:
- 1.2 and 1.3 (to increase relationship diversity quickly)

**Risk Mitigation**:
- Do **1.4 first** to avoid refactoring pain later.
- Add good test coverage early — relationship logic is easy to break silently.
- Keep backward compatibility where possible (or provide a clear migration path).

Would you like me to also create:
- A GitHub Issue template version of these tasks?
- A dependency graph (text or Mermaid)?
- Detailed implementation sketches for any specific task (e.g., 1.1 or 1.4)?

Just let me know how you want to proceed.