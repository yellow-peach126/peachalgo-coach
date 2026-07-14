"""Shared product constants — Chinese-first UI copy."""

from __future__ import annotations

# English product name (Chinese meaning: 黄桃算法教练)
APP_NAME = "PeachAlgo Coach"
APP_NAME_ZH = "黄桃算法教练"  # Chinese gloss only, not used as project title
SOURCE_NOTE = "题库题号与题目信息来源于 LeetCode / 力扣，仅保存元数据与外链，不含题面。"

LANGUAGES: list[dict[str, str]] = [
    {"id": "python", "label": "Python"},
    {"id": "java", "label": "Java"},
    {"id": "cpp", "label": "C++"},
    {"id": "c", "label": "C"},
    {"id": "csharp", "label": "C#"},
    {"id": "go", "label": "Go"},
    {"id": "javascript", "label": "JavaScript"},
    {"id": "typescript", "label": "TypeScript"},
    {"id": "mysql", "label": "MySQL"},
    {"id": "rust", "label": "Rust"},
    {"id": "kotlin", "label": "Kotlin"},
    {"id": "swift", "label": "Swift"},
    {"id": "php", "label": "PHP"},
    {"id": "ruby", "label": "Ruby"},
]

LEVELS: list[dict[str, str]] = [
    {
        "id": "beginner",
        "label": "零基础入门",
        "criteria": "几乎没刷过算法题，或只会写简单循环/条件；目标是先建立题感与基础模板。",
    },
    {
        "id": "easy",
        "label": "能做简单题",
        "criteria": "能独立做出多数 Easy；对哈希、双指针、基础链表/树有印象，Medium 常需看提示。",
    },
    {
        "id": "medium",
        "label": "能做部分中等题",
        "criteria": "常见 Medium（滑动窗口、树遍历、二分、基础 DP）能独立或短时做完；Hard 仍吃力。",
    },
    {
        "id": "advanced",
        "label": "冲刺高阶",
        "criteria": "Medium 正确率较高，开始系统练 Hard / 综合题 / 较难 DP 与图论；准备高强度面试或竞赛入门。",
    },
]

GOALS: list[dict[str, str]] = [
    {"id": "campus", "label": "校招面试", "desc": "覆盖高频算法与模板，偏数组/树/DP 入门。"},
    {"id": "social", "label": "社招面试", "desc": "中高频 Medium 为主，强调解题速度与稳定性。"},
    {"id": "foundation", "label": "巩固基础", "desc": "从 Easy 模板稳步推进，节奏更保守。"},
    {"id": "contest", "label": "竞赛入门", "desc": "更早接触构造、组合、图论与较难 DP。"},
    {"id": "database", "label": "数据库 / SQL", "desc": "偏 Database 题；适合主攻 MySQL 的用户。"},
]

DIFFICULTY_ZH = {
    "Easy": "简单",
    "Medium": "中等",
    "Hard": "困难",
}

# Fallback Chinese tags if catalog tag_zh missing
TAG_ZH_FALLBACK = {
    "array": "数组",
    "string": "字符串",
    "hash-table": "哈希表",
    "two-pointers": "双指针",
    "sliding-window": "滑动窗口",
    "stack": "栈",
    "queue": "队列",
    "linked-list": "链表",
    "tree": "树",
    "binary-tree": "二叉树",
    "bst": "二叉搜索树",
    "binary-search-tree": "二叉搜索树",
    "bfs": "广度优先搜索",
    "dfs": "深度优先搜索",
    "heap": "堆",
    "heap-priority-queue": "堆（优先队列）",
    "binary-search": "二分查找",
    "backtracking": "回溯",
    "greedy": "贪心",
    "graph": "图",
    "union-find": "并查集",
    "dynamic-programming": "动态规划",
    "math": "数学",
    "bit-manipulation": "位运算",
    "sorting": "排序",
    "prefix-sum": "前缀和",
    "monotonic-stack": "单调栈",
    "database": "数据库",
    "design": "设计",
    "simulation": "模拟",
    "recursion": "递归",
    "divide-and-conquer": "分治",
    "memoization": "记忆化搜索",
    "shortest-path": "最短路",
    "topological-sort": "拓扑排序",
    "counting": "计数",
    "matrix": "矩阵",
    "enumeration": "枚举",
    "number-theory": "数论",
    "geometry": "几何",
    "game-theory": "博弈",
    "combinatorics": "组合数学",
    "string-matching": "字符串匹配",
    "rolling-hash": "滚动哈希",
    "interactive": "交互",
    "brainteaser": "脑筋急转弯",
    "iterator": "迭代器",
    "doubly-linked-list": "双向链表",
    "randomized": "随机化",
    "data-stream": "数据流",
    "ordered-set": "有序集合",
    "trie": "字典树",
    "segment-tree": "线段树",
    "binary-indexed-tree": "树状数组",
    "line-sweep": "扫描线",
    "probability-and-statistics": "概率与统计",
    "minimum-spanning-tree": "最小生成树",
    "strongly-connected-component": "强连通分量",
    "eulerian-circuit": "欧拉回路",
    "biconnected-component": "双连通分量",
    "counting-sort": "计数排序",
    "radix-sort": "基数排序",
    "bucket-sort": "桶排序",
    "merge-sort": "归并排序",
    "quickselect": "快速选择",
    "shell": "Shell",
    "concurrency": "多线程",
    "hash-function": "哈希函数",
}

STAGE_ZH = {
    "lang-basics": "语法与复杂度基础",
    "array-hash": "数组 / 字符串 / 哈希",
    "two-pointers": "双指针 / 滑动窗口",
    "stack-queue": "栈 / 队列",
    "linked-list": "链表",
    "binary-tree": "二叉树 / DFS / BFS",
    "heap": "堆 / 优先队列",
    "binary-search": "二分查找",
    "backtracking": "回溯",
    "greedy": "贪心",
    "graph": "图论基础",
    "dp": "动态规划",
    "database": "数据库 / SQL",
    "interview-mix": "面试综合高频",
}

ITEM_TYPE_ZH = {
    "main": "主线推荐",
    "review": "复习",
    "weak": "弱项补强",
    "custom": "自行添加",
}
