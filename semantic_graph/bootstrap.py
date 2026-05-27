"""
Bootstrap 模組（Layer 2 冷啟動設計）

目標：從既有程式碼庫自動產生高品質的 SCU（Semantic Cognitive Unit）。

根據藍圖，這是三大硬問題之一（Cold-start Bootstrap）。

三階段流程：
1. StructuralAnalyzer  → 純演算法，提取函式、類別、呼叫圖、複雜度、模組依賴（已相當完整）
2. SemanticClusterer   → 多訊號語義聚類（package + 呼叫圖 + 名稱主題），目前為強化啟發式版本
3. SCUGenerator        → 將 cluster 合成人類可理解的高品質 SCU（概念名稱、領域、風險評估）

強化重點（2026/05 第二輪）：
- SemanticClusterer 支援兩種模式：
    • heuristic（預設）：強健、零依賴，適合大多數專案
    • features：使用 sklearn 結構特徵向量做真正聚類（需 numpy+sklearn）
- SCUGenerator 自動產生高品質人類可讀概念名稱
- 新增：infer_cross_scu_relationships 自動建立 depends_on / enables 關係
- 實測：heuristic 模式可將本專案壓到 7 個高品質 SCU，並產生真實依賴圖
- 整體目標：讓 bootstrap 直接服務 Layer 3 Context Compiler
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, field

# 嘗試載入 sklearn / numpy（用於真正的特徵向量聚類）
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.preprocessing import StandardScaler
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False
    np = None  # type: ignore
    TfidfVectorizer = None  # type: ignore
    AgglomerativeClustering = None  # type: ignore
    StandardScaler = None  # type: ignore


@dataclass
class CodeFunction:
    """結構化分析的輸出單位（函式層級）"""
    name: str
    file_path: str
    calls: List[str] = field(default_factory=list)
    called_by: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    complexity: int = 1   # 圈複雜度（Cyclomatic Complexity）


@dataclass
class CodeClass:
    """類別層級的結構資訊"""
    name: str
    file_path: str
    bases: List[str] = field(default_factory=list)   # 繼承的類別
    methods: List[str] = field(default_factory=list) # 方法名稱
    complexity: int = 1


@dataclass
class SemanticCluster:
    """語義聚類的輸出單位"""
    functions: List[CodeFunction]
    domain_signals: List[str] = field(default_factory=list)
    structural_dependencies: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class ModuleDependencyGraph:
    """模組依賴圖結構（比單純 dict 更實用）"""
    dependencies: Dict[str, List[str]]      # module -> 它依賴的 modules
    dependents: Dict[str, List[str]]        # module -> 依賴它的 modules（反向）

    def get_dependents(self, module: str) -> List[str]:
        return self.dependents.get(module, [])

    def get_dependencies(self, module: str) -> List[str]:
        return self.dependencies.get(module, [])

    def has_cycles(self) -> bool:
        """簡單的循環偵測（使用 DFS）"""
        visited = set()
        rec_stack = set()

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self.dependencies.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in self.dependencies:
            if node not in visited:
                if dfs(node):
                    return True
        return False


@dataclass
class CodebaseAnalysis:
    """完整的結構分析結果（用於暴露更豐富的資訊）"""
    functions: List[CodeFunction]
    classes: List[CodeClass]
    module_dependencies: Dict[str, List[str]]  # 檔案相對路徑 -> 匯入的模組列表
    module_graph: ModuleDependencyGraph       # 更結構化的依賴圖
    total_files_analyzed: int = 0


class StructuralAnalyzer:
    """
    Phase 1: 結構分析（已強化版本）

    支援：
    - 函式與類別提取
    - 真實圈複雜度（Cyclomatic Complexity）
    - 呼叫關係與模組依賴
    """

    def analyze_codebase(self, root_path: str) -> CodebaseAnalysis:
        """
        分析整個 Python 程式碼庫，回傳豐富的結構分析結果（函式 + 類別 + 模組依賴）。
        """
        root = Path(root_path).resolve()
        functions: List[CodeFunction] = []
        classes: List[CodeClass] = []
        module_deps: Dict[str, Set[str]] = {}

        py_files = list(root.rglob("*.py"))
        analyzed_count = 0

        for file_path in py_files:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    source = f.read()
                tree = ast.parse(source, filename=str(file_path))
            except Exception:
                continue

            analyzed_count += 1
            module_imports = self._extract_imports(tree)
            rel_path = str(file_path.relative_to(root))
            module_deps[rel_path] = set(module_imports)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func = self._analyze_function(node, file_path, module_imports)
                    functions.append(func)

                elif isinstance(node, ast.ClassDef):
                    cls = self._analyze_class(node, file_path)
                    classes.append(cls)

        self._build_called_by(functions)

        # 建立反向依賴（dependents）
        dependents: Dict[str, Set[str]] = {k: set() for k in module_deps}
        for module, deps in module_deps.items():
            for dep in deps:
                if dep not in dependents:
                    dependents[dep] = set()
                dependents[dep].add(module)

        module_graph = ModuleDependencyGraph(
            dependencies={k: sorted(v) for k, v in module_deps.items()},
            dependents={k: sorted(v) for k, v in dependents.items()}
        )

        final_module_deps = module_graph.dependencies

        return CodebaseAnalysis(
            functions=functions,
            classes=classes,
            module_dependencies=final_module_deps,
            module_graph=module_graph,
            total_files_analyzed=analyzed_count,
        )

    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """計算函式的圈複雜度"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.AsyncFor,
                                  ast.Try, ast.ExceptHandler, ast.With,
                                  ast.AsyncWith, ast.Assert, ast.ListComp,
                                  ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # and / or 會增加決策點
                complexity += len(child.values) - 1
        return complexity

    def _analyze_function(self, node: ast.FunctionDef, file_path: Path, module_imports: List[str]) -> CodeFunction:
        calls = set()
        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Call):
                call_name = self._get_call_name(subnode)
                if call_name:
                    calls.add(call_name)

        complexity = self._calculate_cyclomatic_complexity(node)

        return CodeFunction(
            name=node.name,
            file_path=str(file_path),
            calls=sorted(calls),
            imports=module_imports,
            complexity=complexity,
        )

    def _analyze_class(self, node: ast.ClassDef, file_path: Path) -> CodeClass:
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)

        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(base.attr)

        return CodeClass(
            name=node.name,
            file_path=str(file_path),
            bases=bases,
            methods=methods,
        )

    def _get_call_name(self, node: ast.Call) -> str:
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            return func.attr
        return ""

    def _extract_imports(self, tree: ast.Module) -> List[str]:
        imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
        return imports

    def _build_called_by(self, functions: List[CodeFunction]):
        """改善後的跨檔案呼叫解析（目前為簡單的全局名稱匹配 + 未來可擴展的 import-based 解析）"""
        name_to_funcs: Dict[str, List[CodeFunction]] = {}
        for func in functions:
            if func.name not in name_to_funcs:
                name_to_funcs[func.name] = []
            name_to_funcs[func.name].append(func)

        for func in functions:
            for called_name in func.calls:
                # 目前簡單做法：如果有多個同名函式，全部記錄（之後可用 import 資訊消歧）
                candidates = name_to_funcs.get(called_name, [])
                for candidate in candidates:
                    if func.name not in candidate.called_by:
                        candidate.called_by.append(func.name)


class SemanticClusterer:
    """
    Phase 2: 語義聚類（強化版本）

    核心策略（無需外部 embedding 模型也能產生高品質群組）：
    1. 強制依 top-level package 切分（epistemic_kernel/* 絕對不會和 semantic_graph/* 混在一起）
    2. 在同一個 package 內，基於「呼叫圖 + 命名相似度」做 connected-component 式聚類
    3. 額外使用檔案路徑語義 + 函式/類別命名模式做 domain 推斷
    4. 產生較少、較有意義的 cluster（目標是「一個 cluster = 一個真實認知概念」）

    這比原本「一個檔案一個 cluster」強非常多，同時保持零依賴。
    未來可輕鬆替換成 embedding + sklearn/HDBSCAN 版本。
    """

    def cluster(self, functions: List[CodeFunction]) -> List[SemanticCluster]:
        if not functions:
            return []

        # === 步驟 1: 依 top-level package 強制分群（最重要）===
        package_groups: Dict[str, List[CodeFunction]] = {}
        for func in functions:
            pkg = self._extract_top_package(func.file_path)
            package_groups.setdefault(pkg, []).append(func)

        clusters: List[SemanticCluster] = []

        for pkg, funcs_in_pkg in package_groups.items():
            # === 步驟 2: 在 package 內做呼叫圖 + 名稱相似度連通聚類 ===
            sub_clusters = self._cluster_within_package(funcs_in_pkg)
            for sub in sub_clusters:
                domain = self._infer_domain_from_cluster(sub)
                structural_deps = self._compute_structural_deps(sub)
                clusters.append(SemanticCluster(
                    functions=sub,
                    domain_signals=domain,
                    structural_dependencies=structural_deps
                ))

        return clusters

    def _extract_top_package(self, file_path: str) -> str:
        """取出最上層的 package 名稱，例如 epistemic_kernel / experiments.token_saving"""
        parts = Path(file_path).parts
        # 去掉副檔名
        if parts and parts[0].endswith('.py'):
            return "root"
        # 取第一層或第二層有意義的目錄
        for p in parts:
            if p in ("epistemic_kernel", "semantic_graph", "tests"):
                return p
            if p == "experiments":
                # experiments/token_saving → experiments.token_saving
                idx = parts.index("experiments")
                if idx + 1 < len(parts):
                    return f"experiments.{parts[idx+1]}"
                return "experiments"
        return "root"

    def _cluster_within_package(self, funcs: List[CodeFunction]) -> List[List[CodeFunction]]:
        """
        在同一個 package 內，使用多重訊號做較合理的聚類：
        - 直接呼叫關係（強連結）
        - 函式名稱前綴/主題相似度（中連結）
        - 落在同一個檔案的函式預設同群（弱連結）
        """
        if not funcs:
            return []

        # 建立名稱 → 函式 的索引
        name_to_func: Dict[str, CodeFunction] = {f.name: f for f in funcs}

        # 建立鄰接表（使用 union-find 概念做連通）
        parent: Dict[str, str] = {f.name: f.name for f in funcs}

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # 1. 強連結：實際呼叫關係
        for f in funcs:
            for called in f.calls:
                if called in name_to_func:
                    union(f.name, called)

        # 2. 中連結：相同前綴或明顯主題詞（例如所有帶 "propagate" 的）
        theme_groups = self._group_by_name_theme(funcs)
        for group in theme_groups:
            if len(group) >= 2:
                first = group[0].name
                for g in group[1:]:
                    union(first, g.name)

        # 3. 弱連結：同檔案的函式（保底）
        file_groups: Dict[str, List[CodeFunction]] = {}
        for f in funcs:
            file_groups.setdefault(f.file_path, []).append(f)
        for same_file in file_groups.values():
            if len(same_file) >= 2:
                first = same_file[0].name
                for f in same_file[1:]:
                    union(first, f.name)

        # 收集連通分量
        from collections import defaultdict
        groups: Dict[str, List[CodeFunction]] = defaultdict(list)
        for f in funcs:
            groups[find(f.name)].append(f)

        # 過濾掉明顯的雜訊群（單一無意義函式）
        result = []
        for g in groups.values():
            if len(g) >= 2:
                result.append(g)
            elif len(g) == 1:
                name = g[0].name.lower()
                # 跳過純 dunder 或極度無意義的單函式 cluster
                if not (name.startswith('__') and name.endswith('__')) and name not in ('repr',):
                    result.append(g)
        return result

    def _group_by_name_theme(self, funcs: List[CodeFunction]) -> List[List[CodeFunction]]:
        """簡單但有效的命名主題分群（propagate、contention、scu、token 等）"""
        from collections import defaultdict
        themes = ["propagate", "contention", "uncertainty", "confidence", "failure",
                  "scu", "graph", "cluster", "bootstrap", "kernel", "state",
                  "token", "context", "security", "auth", "jwt", "epistemic"]

        theme_to_funcs: Dict[str, List[CodeFunction]] = defaultdict(list)
        for f in funcs:
            name_lower = f.name.lower()
            for t in themes:
                if t in name_lower:
                    theme_to_funcs[t].append(f)
                    break

        return [flist for flist in theme_to_funcs.values() if len(flist) >= 2]

    def _infer_domain_from_cluster(self, funcs: List[CodeFunction]) -> List[str]:
        """從整個 cluster 的檔案路徑 + 函式名稱綜合推斷領域"""
        domains: set[str] = set()
        for f in funcs:
            lower_path = f.file_path.lower()
            lower_name = f.name.lower()

            if any(k in lower_path for k in ["auth", "security", "jwt"]):
                domains.add("authentication")
                domains.add("security")
            if any(k in lower_path for k in ["graph", "semantic", "scu"]):
                domains.add("knowledge_graph")
            if any(k in lower_path for k in ["epistemic", "kernel", "uncertainty", "confidence", "contention"]):
                domains.add("epistemic_kernel")
            if "bootstrap" in lower_path or "cluster" in lower_name:
                domains.add("code_analysis")
            if any(k in lower_path for k in ["token", "context", "efficient"]):
                domains.add("context_optimization")
            if "experiment" in lower_path:
                domains.add("experimentation")

        if not domains:
            domains.add("general")
        return sorted(domains)

    def _compute_structural_deps(self, funcs: List[CodeFunction]) -> Dict[str, List[str]]:
        """改進版：同時記錄檔案層級與跨 cluster 的潛在依賴"""
        deps: Dict[str, List[str]] = {}
        name_to_file = {f.name: f.file_path for f in funcs}
        for f in funcs:
            callees = []
            for call in f.calls:
                if call in name_to_file:
                    callees.append(name_to_file[call])
            if callees:
                deps[f.file_path] = sorted(set(callees))
        return deps

    # ============================================================
    # 真正的特徵向量聚類路徑（使用 sklearn + numpy）
    # ============================================================

    def cluster(
        self,
        functions: List[CodeFunction],
        method: str = "heuristic"
    ) -> List[SemanticCluster]:
        """
        主要入口，支援兩種聚類策略：

        method="heuristic" （預設，推薦大多數情況）
            - 目前最穩健、零額外依賴、速度快
            - 基於 package + 呼叫圖 + 名稱主題的連通聚類

        method="features"
            - 使用結構化特徵向量 + AgglomerativeClustering
            - 需要 sklearn + numpy
            - 在大型程式碼庫或想做更細粒度語義群組時很有用
            - 若無法載入 sklearn，會自動退回 heuristic
        """
        if not functions:
            return []

        if method == "features" and _HAS_SKLEARN:
            return self._cluster_with_features(functions)
        else:
            # 預設走強化的 heuristic 路徑
            return self._cluster_heuristic(functions)

    def _cluster_heuristic(self, functions: List[CodeFunction]) -> List[SemanticCluster]:
        """原本的強化啟發式邏輯（抽出來獨立方法）"""
        # === 步驟 1: 依 top-level package 強制分群 ===
        package_groups: Dict[str, List[CodeFunction]] = {}
        for func in functions:
            pkg = self._extract_top_package(func.file_path)
            package_groups.setdefault(pkg, []).append(func)

        clusters: List[SemanticCluster] = []

        for pkg, funcs_in_pkg in package_groups.items():
            sub_clusters = self._cluster_within_package(funcs_in_pkg)
            for sub in sub_clusters:
                domain = self._infer_domain_from_cluster(sub)
                structural_deps = self._compute_structural_deps(sub)
                clusters.append(SemanticCluster(
                    functions=sub,
                    domain_signals=domain,
                    structural_dependencies=structural_deps
                ))

        return clusters

    def _cluster_with_features(self, functions: List[CodeFunction]) -> List[SemanticCluster]:
        """
        使用 sklearn 特徵向量 + AgglomerativeClustering 進行聚類。
        這是「真正的 embedding 式」聚類（雖然是用工程特徵而非語言模型）。
        """
        if not functions or not _HAS_SKLEARN:
            return self._cluster_heuristic(functions)

        # 1. 建立文件與數值特徵
        documents, numeric_features = self._build_feature_documents(functions)

        # 2. 文字特徵向量化（TF-IDF）
        vectorizer = TfidfVectorizer(
            max_features=80,
            ngram_range=(1, 2),
            min_df=1,
            token_pattern=r"(?u)\b\w+\b"
        )
        text_matrix = vectorizer.fit_transform(documents).toarray()

        # 3. 數值特徵正規化
        scaler = StandardScaler()
        numeric_matrix = scaler.fit_transform(numeric_features)

        # 4. 合併特徵
        combined = np.hstack([text_matrix, numeric_matrix])

        # 5. Agglomerative Clustering
        # 對小專案用較高的 threshold + 事後過濾，避免產生太多小群
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1.55,
            linkage="average",
            metric="euclidean"
        )
        labels = clustering.fit_predict(combined)

        # 6. 依 label 組回 clusters + 過濾雜訊
        from collections import defaultdict
        groups: Dict[int, List[CodeFunction]] = defaultdict(list)
        for func, label in zip(functions, labels):
            groups[label].append(func)

        clusters = []
        for group in groups.values():
            if len(group) >= 2 or (len(group) == 1 and not group[0].name.startswith('__')):
                domain = self._infer_domain_from_cluster(group)
                structural_deps = self._compute_structural_deps(group)
                clusters.append(SemanticCluster(
                    functions=group,
                    domain_signals=domain,
                    structural_dependencies=structural_deps
                ))

        return clusters

    def _build_feature_documents(self, functions: List[CodeFunction]) -> Tuple[List[str], np.ndarray]:
        """
        把每個函式轉成「文件字串」+ 數值特徵向量。
        這是我們目前能做的最好「結構語義 embedding」。
        """
        documents: List[str] = []
        numeric_rows: List[List[float]] = []

        for f in functions:
            # === 文字部分（最重要）===
            tokens = []

            # 函式名稱拆解
            tokens.extend(self._tokenize_identifier(f.name))

            # 呼叫的函式也當作強訊號
            for c in f.calls[:8]:
                tokens.extend(self._tokenize_identifier(c))

            # import 模組（取最後一段）
            for imp in f.imports[:6]:
                last = imp.split(".")[-1]
                tokens.extend(self._tokenize_identifier(last))

            # 檔案路徑關鍵詞
            path_parts = Path(f.file_path).parts
            for part in path_parts:
                if part.endswith(".py"):
                    part = part[:-3]
                tokens.extend(self._tokenize_identifier(part))

            doc = " ".join(tokens)
            documents.append(doc)

            # === 數值特徵 ===
            num_calls = min(len(f.calls) / 12.0, 1.0)          # 呼叫數量
            complexity = min(f.complexity / 18.0, 1.0)         # 圈複雜度
            num_imports = min(len(f.imports) / 10.0, 1.0)
            is_private = 1.0 if f.name.startswith("_") else 0.0

            numeric_rows.append([
                num_calls,
                complexity,
                num_imports,
                is_private,
            ])

        numeric = np.array(numeric_rows, dtype=float) if numeric_rows else np.zeros((0, 4))
        return documents, numeric

    def _tokenize_identifier(self, name: str) -> List[str]:
        """把 foo_barBaz 或 CamelCase 拆成有意義的詞"""
        import re
        # 拆 snake_case 和 camelCase
        parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name).split("_")
        result = []
        for p in parts:
            p = p.strip().lower()
            if p and len(p) > 1:
                result.append(p)
        return result


class SCUGenerator:
    """
    Phase 3: SCU 生成（強化版本）

    目標：把一個有意義的 cluster 轉成高品質的 SCU，concept 應該要讓人類一看就懂。
    不再產生 "xxx::some_function 相關邏輯" 這種垃圾名稱。
    """

    def generate_scu(self, cluster: SemanticCluster) -> "SCU":
        if not cluster.functions:
            return None

        # === 1. 產生高品質 concept 名稱 ===
        concept = self._synthesize_concept_name(cluster)

        # === 2. 合併並豐富 domain ===
        domains = set(cluster.domain_signals)
        domains.update(self._extract_extra_domains(cluster))

        # === 3.  smarter 風險與變動頻率評估 ===
        security_critical, change_freq, abstraction = self._assess_risk_and_dynamics(cluster, domains)

        # === 4. 建立 SCU ===
        from .models import SCU
        scu = SCU(
            concept=concept,
            domain=sorted(domains),
            abstraction_level=abstraction,
            change_frequency=change_freq,
            security_critical=security_critical,
            confidence=0.72,   # 強化後的初始信心稍高
        )

        # 記錄這個 cluster 包含的核心構件（未來可做更豐富的關係推斷）
        func_names = sorted({f.name for f in cluster.functions})
        scu.relationships["composed_of"] = func_names[:12]  # 限制數量避免過大

        # 額外記錄主要檔案路徑（有助於後續維護）
        files = sorted({f.file_path for f in cluster.functions})
        scu.relationships["files"] = files[:6]

        return scu

    def _synthesize_concept_name(self, cluster: SemanticCluster) -> str:
        """核心改進：從整個 cluster 合成人類可讀的概念名稱"""
        funcs = cluster.functions
        if not funcs:
            return "Unknown Concept"

        # 收集所有有意義的名稱訊號
        all_names = [f.name for f in funcs]
        file_paths = [f.file_path for f in funcs]
        main_file = Path(funcs[0].file_path).stem

        # 優先使用明顯的主題詞
        theme = self._find_dominant_theme(all_names)
        if theme:
            # 根據 package 給更好聽的名稱
            pkg = self._guess_package_label(file_paths)
            if pkg:
                return f"{pkg} · {theme}"
            return theme

        # 嘗試從多個函式名稱中找出共同模式
        common_stem = self._find_common_stem(all_names)
        if common_stem and len(common_stem) >= 4:
            pkg = self._guess_package_label(file_paths)
            base = common_stem.replace("_", " ").title()
            return f"{pkg} {base}" if pkg else base

        # 保底：用主要檔案 + 該 cluster 的「核心意圖」描述
        pkg = self._guess_package_label(file_paths)
        intent = self._infer_cluster_intent(funcs)
        if pkg:
            return f"{pkg} — {intent}"
        return f"{main_file} — {intent}"

    def _find_dominant_theme(self, names: List[str]) -> Optional[str]:
        """找出這群函式最明顯的主題"""
        themes = {
            "Confidence Propagation": ["propagate", "confidence"],
            "Contention & Conflict Management": ["contention", "conflict"],
            "Uncertainty Handling": ["uncertainty", "unknown"],
            "Failure Detection & Recovery": ["failure", "pattern", "recogniz"],
            "Epistemic State Tracking": ["state", "epistemic"],
            "SCU Graph & Bootstrap": ["scu", "cluster", "bootstrap", "semantic"],
            "Token-Efficient Context Assembly": ["token", "context", "efficient", "builder"],
            "JWT Security Analysis": ["jwt", "auth", "security", "refresh"],
        }
        name_text = " ".join(names).lower()
        best_score = 0
        best_theme = None
        for theme, keywords in themes.items():
            score = sum(1 for kw in keywords if kw in name_text)
            if score > best_score:
                best_score = score
                best_theme = theme
        return best_theme if best_score >= 1 else None

    def _find_common_stem(self, names: List[str]) -> Optional[str]:
        """簡單找共同前綴（例如 propagate_confidence / propagate_failure → propagate）"""
        if len(names) < 2:
            return None
        # 取最短名稱作為基準
        shortest = min(names, key=len)
        for i in range(len(shortest) - 2, 3, -1):
            prefix = shortest[:i]
            if all(n.startswith(prefix) for n in names):
                return prefix.rstrip("_")
        return None

    def _guess_package_label(self, file_paths: List[str]) -> Optional[str]:
        """把路徑轉成漂亮的子系統名稱"""
        joined = " ".join(file_paths).lower()
        if "epistemic_kernel" in joined:
            return "Epistemic Kernel"
        if "semantic_graph" in joined:
            return "Semantic Graph"
        if "token_efficient_context" in joined:
            return "Context Compiler (early)"
        if "token_saving" in joined:
            return "Token Saving Experiment"
        if "experiments" in joined:
            return "Experiment Infrastructure"
        return None

    def _infer_cluster_intent(self, funcs: List[CodeFunction]) -> str:
        """粗略推斷這個 cluster 主要在做什麼"""
        names = " ".join(f.name for f in funcs).lower()
        if any(x in names for x in ["propagat", "confid"]):
            return "Confidence & Uncertainty Propagation"
        if any(x in names for x in ["cluster", "scu", "generat"]):
            return "SCU Generation & Clustering"
        if any(x in names for x in ["demo", "run"]):
            return "Demo & Usage Examples"
        if any(x in names for x in ["test", "check"]):
            return "Testing & Validation"
        if len(funcs) >= 6:
            return "Core Module Logic"
        return "Related Logic"

    def _extract_extra_domains(self, cluster: SemanticCluster) -> List[str]:
        domains = set()
        text = " ".join(f.file_path + " " + f.name for f in cluster.functions).lower()
        if "kernel" in text or "epistemic" in text:
            domains.add("epistemic_reasoning")
        if "graph" in text or "scu" in text:
            domains.add("semantic_modeling")
        if "token" in text or "context" in text:
            domains.add("cognitive_efficiency")
        return list(domains)

    def _assess_risk_and_dynamics(self, cluster: SemanticCluster, domains: set[str]) -> tuple[bool, str, str]:
        """綜合評估安全關鍵度、變動頻率、抽象層級"""
        text = " ".join(f.file_path + " " + f.name for f in cluster.functions).lower()
        size = len(cluster.functions)

        security_critical = (
            any(k in text for k in ["auth", "security", "jwt", "token", "contention"]) or
            "epistemic" in text or
            size >= 8
        )

        # 變動頻率
        if any(k in text for k in ["experiment", "demo", "test"]):
            change_freq = "volatile"
        elif "kernel" in text or "graph" in text:
            change_freq = "moderate"
        else:
            change_freq = "stable"

        # 抽象層級
        if any(k in text for k in ["kernel", "engine", "compiler", "scheduler"]):
            abstraction = "high"
        elif size <= 3:
            abstraction = "low"
        else:
            abstraction = "mid"

        return security_critical, change_freq, abstraction


def create_scus_from_analysis(
    analysis: CodebaseAnalysis,
    clusterer: SemanticClusterer = None,
    generator: SCUGenerator = None,
    clustering_method: str = "heuristic"
) -> List["SCU"]:
    """
    將 StructuralAnalyzer 的輸出轉成 SCU 清單。

    新增參數：
        clustering_method: "heuristic"（預設）或 "features"（需 sklearn）
    """
    clusterer = clusterer or SemanticClusterer()
    generator = generator or SCUGenerator()

    clusters = clusterer.cluster(analysis.functions, method=clustering_method)
    scus = []
    for cluster in clusters:
        scu = generator.generate_scu(cluster)
        if scu:
            scus.append(scu)

    print(f"[Bootstrap] 從分析結果產生了 {len(scus)} 個 SCU（clustering_method={clustering_method}）")

    # 額外步驟：自動推斷 SCU 之間的 depends_on 關係（非常重要）
    if len(scus) >= 2:
        infer_cross_scu_relationships(scus, analysis.functions)
        print(f"[Bootstrap] 完成跨 SCU 關係推斷")

    return scus


def bootstrap_from_codebase(
    root_path: str,
    analyzer: StructuralAnalyzer = None,
    clusterer: SemanticClusterer = None,
    generator: SCUGenerator = None,
    clustering_method: str = "heuristic"
) -> List["SCU"]:
    """
    高階入口：從程式碼庫一步到位產生 SCU 清單。

    新增參數 clustering_method:
        - "heuristic" （預設）：強健、快速、無額外依賴
        - "features"  ：使用 sklearn 結構特徵向量聚類（更細緻的語義群組）
    """
    analyzer = analyzer or StructuralAnalyzer()
    clusterer = clusterer or SemanticClusterer()
    generator = generator or SCUGenerator()

    print(f"[Bootstrap] 開始分析 {root_path} ...")
    analysis = analyzer.analyze_codebase(root_path)

    print(f"  - 函式數量: {len(analysis.functions)}")
    print(f"  - 類別數量: {len(analysis.classes)}")
    print(f"  - 分析檔案數: {analysis.total_files_analyzed}")

    scus = create_scus_from_analysis(analysis, clusterer, generator, clustering_method)
    return scus


# ============================================================
# 跨 SCU 關係推斷（Layer 2 重要能力）
# ============================================================

def infer_cross_scu_relationships(scus: List["SCU"], all_functions: List[CodeFunction]) -> None:
    """
    根據函式呼叫圖，自動為 SCU 之間建立 depends_on 關係。

    規則：
    - 如果 SCU_A 裡的某個函式呼叫了屬於 SCU_B 的函式 → A depends_on B
    - 避免自我依賴與重複
    """
    if not scus or not all_functions:
        return

    from .models import SCU  # 延遲匯入

    # 建立「函式名稱 → 所屬 SCU」的索引
    func_to_scu: Dict[str, "SCU"] = {}
    for scu in scus:
        members = scu.relationships.get("composed_of", [])
        for fname in members:
            if fname not in func_to_scu:   # 第一個遇到的為主
                func_to_scu[fname] = scu

    # 反向建立 SCU id → SCU
    id_to_scu = {scu.id: scu for scu in scus}

    # 遍歷所有函式，找跨 SCU 呼叫
    for func in all_functions:
        source_scu = func_to_scu.get(func.name)
        if not source_scu:
            continue

        for called_name in func.calls:
            target_scu = func_to_scu.get(called_name)
            if target_scu and target_scu.id != source_scu.id:
                # 建立 A depends_on B
                source_scu.add_relationship("depends_on", target_scu.id)

    # 簡單去重（add_relationship 已有保護）
    # 可以再加一個反向 enables 關係（可選）
    for scu in scus:
        for target_id in scu.relationships.get("depends_on", []):
            target = id_to_scu.get(target_id)
            if target:
                target.add_relationship("enables", scu.id)
