# Phase 1: SCU Relationship Enhancement - GitHub Issues 版本

以下內容設計成可以直接複製成 GitHub Issues 的格式。

**建議使用方式：**
1. 先建立一個 Epic Issue（追蹤總覽）
2. 再逐一建立子任務 Issue，並在 Epic Issue 中引用它們

---

## Epic Issue（建議先建立這個）

**標題：**
```
[Phase 1] SCU Relationship Enhancement - Epic
```

**Issue Body（複製以下內容）：**

```markdown
## 目標
大幅提升 Semantic Cognitive Unit (SCU) 之間關係的品質、數量與多樣性，讓 Layer 3（尤其是 Medium 與 Smart 模式）能產生更有洞察力的 Epistemic Note。

## 範圍
此 Epic 涵蓋 Phase 1 的所有基礎強化任務。

## 相關子任務
- [ ] #xxx - 1.4 為關係加入基礎強度（資料結構調整）
- [ ] #xxx - 1.1 強化現有呼叫圖關係推斷
- [ ] #xxx - 1.5 建立關係去重與清理機制
- [ ] #xxx - 1.2 加入模組層級依賴關係
- [ ] #xxx - 1.3 加入類別層級繼承與組合關係
- [ ] #xxx - 跨領域：更新 SCUGraph 與工具

## 預期成果
- SCU 平均關係數量提升至少 2 倍
- 引入 relationship strength 與 confidence
- 增加模組層級與類別層級關係
- 建立乾淨的資料結構與維護機制

**Labels**: `epic`, `phase-1`, `scu-relationship`, `layer-2`
**Milestone**: Phase 1 - SCU Relationship Enhancement
```

---

## 個別子任務 Issues（可直接複製建立）

### Issue 1: 1.4 為關係加入基礎強度（資料結構調整）

**標題建議：**
```
[Phase 1] 1.4 為關係加入基礎強度（資料結構調整）
```

**Issue Body：**

```markdown
## 目標
將 `SCU.relationships` 從 `Dict[str, List[str]]` 改為支援 `strength`、`confidence`、`source` 等中繼資料的結構。

## 描述
目前關係儲存方式過於簡單，無法支援後續的關係強度量化與可解釋性需求。此任務為 Phase 1 的基礎，建議優先執行。

## 驗收條件
- [ ] 修改 `SCU.add_relationship()` 支援傳入 strength、confidence、source 等欄位
- [ ] 更新 `SCUGraph` 相關方法
- [ ] 更新 `infer_cross_scu_relationships` 呼叫端
- [ ] 確保現有讀取關係的程式碼可正常運作（或提供相容層）
- [ ] 加入基礎驗證（strength 範圍 0.0~1.0）

## 建議資料結構
```python
relationships: Dict[str, List[Dict[str, Any]]]
```

## 預估難度 / 工時
Easy → Medium（2~3 天）

## 依賴
無（基礎任務）

## 涉及檔案
- `semantic_graph/models.py`
- `semantic_graph/graph.py`
- `semantic_graph/bootstrap.py`

**Labels**: `phase-1`, `scu-relationship`, `layer-2`, `enhancement`  
**Priority**: High
```

---

### Issue 2: 1.1 強化現有呼叫圖關係推斷

**標題建議：**
```
[Phase 1] 1.1 強化現有呼叫圖關係推斷
```

**Issue Body：**

```markdown
## 目標
大幅提升基於函式呼叫圖的 `depends_on` 關係數量與準確度。

## 描述
目前 `infer_cross_scu_relationships` 只做簡單的函式名稱比對，跨檔案解析能力弱，間接呼叫幾乎抓不到。

## 驗收條件
- [ ] 支援利用 import 資訊進行函式名稱消歧
- [ ] 改善跨檔案同名函式的解析
- [ ] 為關係加入 strength（例如依呼叫頻率）
- [ ] 建立可複用的 `build_function_to_scu_index` 函式

## 建議新增函式
- `build_function_to_scu_index(scus, all_functions)`
- `resolve_call_target(call_name, current_func, all_functions)`

## 預估難度 / 工時
Medium（4~6 天）

## 依賴
- 1.4（資料結構）

## 涉及檔案
- `semantic_graph/bootstrap.py`

**Labels**: `phase-1`, `scu-relationship`, `layer-2`, `enhancement`  
**Priority**: High
```

---

### Issue 3: 1.5 建立關係去重與清理機制

**標題建議：**
```
[Phase 1] 1.5 建立關係去重與清理機制
```

**Issue Body：**

```markdown
## 目標
確保 SCU 關係乾淨、一致，並提供維護工具。

## 驗收條件
- [ ] 建立 `normalize_relationships(scu)` 函式
- [ ] 移除重複關係與自我依賴
- [ ] 支援依 strength 過濾弱關係
- [ ] 在 bootstrap 結束後自動執行清理
- [ ] 提供 `get_relationship_stats(scus)` 工具函式

## 預估難度 / 工時
Easy → Medium（2~3 天）

## 依賴
- 1.4（資料結構）

## 涉及檔案
- `semantic_graph/bootstrap.py`

**Labels**: `phase-1`, `scu-relationship`, `layer-2`, `enhancement`  
**Priority**: High
```

---

### Issue 4: 1.2 加入模組層級依賴關係

**標題建議：**
```
[Phase 1] 1.2 加入模組層級依賴關係
```

**Issue Body：**

```markdown
## 目標
利用現有的 `CodebaseAnalysis.module_graph` 建立模組層級的 `depends_on` 關係。

## 驗收條件
- [ ] 根據模組 import 關係建立 SCU 層級的 module-level depends_on
- [ ] 使用 `source` 欄位區分「函式層級」與「模組層級」關係
- [ ] 避免與函式層級關係過度重複

## 預估難度 / 工時
Medium（3~4 天）

## 依賴
- 1.4（資料結構）

## 涉及檔案
- `semantic_graph/bootstrap.py`

**Labels**: `phase-1`, `scu-relationship`, `layer-2`, `enhancement`  
**Priority**: Medium
```

---

### Issue 5: 1.3 加入類別層級繼承與組合關係

**標題建議：**
```
[Phase 1] 1.3 加入類別層級繼承與組合關係
```

**Issue Body：**

```markdown
## 目標
利用 `CodeClass.bases` 建立 `inherits_from` 與基礎的組合關係。

## 驗收條件
- [ ] 正確建立類別繼承對應的 SCU 關係
- [ ] 初步支援組合關係偵測
- [ ] 關係正確歸屬到所屬 SCU

## 預估難度 / 工時
Medium ~ Hard（4~6 天）

## 依賴
- 1.4（資料結構）

## 涉及檔案
- `semantic_graph/bootstrap.py`

**Labels**: `phase-1`, `scu-relationship`, `layer-2`, `enhancement`  
**Priority**: Medium
```

---

### Issue 6: 跨領域 - SCUGraph 與工具更新

**標題建議：**
```
[Phase 1] 更新 SCUGraph 與關係相關工具以支援新格式
```

**Issue Body：**

```markdown
## 目標
確保 `SCUGraph` 與相關工具能正確處理新的關係資料結構。

## 驗收條件
- [ ] `add_relationship`、`get_related` 等方法支援新格式
- [ ] 提供 `get_relationship_stats(scus)` 工具
- [ ] 更新文件與範例

## 預估難度 / 工時
Medium

## 依賴
- 1.4

**Labels**: `phase-1`, `scu-relationship`, `layer-2`, `enhancement`  
**Priority**: High
```

---

## 使用說明

1. 先在 GitHub 建立 Epic Issue（複製第一個區塊）。
2. 建立完 Epic 後，逐一建立上面的子任務 Issue。
3. 在 Epic Issue 的描述中，把子任務 Issue 編號填上去，形成連結。
4. 可為所有 Issue 加上相同 Milestone（例如 `Phase 1 - SCU Relationship`）。

需要我幫你再產生一個「更精簡版」的 Issue 列表（適合快速建立），還是產生一個包含 Assignee / Project 的版本？