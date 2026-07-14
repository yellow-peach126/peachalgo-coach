# 如何贡献题目元数据

感谢你帮助扩展 PeachAlgo Coach 题库。

## 原则

1. **只提交元数据**，不要粘贴 LeetCode 题面全文、测试用例或官方题解正文。
2. 每题必须有可访问的 LeetCode 链接。
3. 标签、阶段、预估时间尽量准确，方便路线规划。
4. 优先补充「某阶段缺失的模板题 / 高频题」。

## 文件位置

```text
backend/data/problems.json
```

## 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| id | ✅ | 建议 `lc-{题号}`，全局唯一 |
| number | ✅ | LeetCode 题号（整数） |
| title | ✅ | 英文标题 |
| title_zh | 推荐 | 中文标题 |
| difficulty | ✅ | `Easy` / `Medium` / `Hard` |
| tags | ✅ | 字符串数组，见下方枚举 |
| prerequisites | 可选 | 前置知识点 id |
| est_minutes | ✅ | 预估分钟数 |
| is_template | ✅ | 是否模板题 |
| stage | ✅ | 所属阶段 id |
| url | ✅ | 题目链接 |
| priority | ✅ | 数字越小越优先，建议 1–100 |

## 阶段枚举（stage）

```text
lang-basics
array-hash
two-pointers
stack-queue
linked-list
binary-tree
heap
binary-search
backtracking
greedy
graph
dp
interview-mix
```

## 常用标签（tags）

```text
array
string
hash-table
two-pointers
sliding-window
stack
queue
linked-list
tree
binary-tree
bst
bfs
dfs
heap
binary-search
backtracking
greedy
graph
union-find
dynamic-programming
math
bit-manipulation
sorting
prefix-sum
monotonic-stack
```

## 示例

```json
{
  "id": "lc-1",
  "number": 1,
  "title": "Two Sum",
  "title_zh": "两数之和",
  "difficulty": "Easy",
  "tags": ["array", "hash-table"],
  "prerequisites": [],
  "est_minutes": 20,
  "is_template": true,
  "stage": "array-hash",
  "url": "https://leetcode.com/problems/two-sum/",
  "priority": 10
}
```

## PR 检查清单

- [ ] `id` 不与现有题目冲突
- [ ] `number` / `url` 正确
- [ ] `stage` 与 `tags` 合理
- [ ] 未包含题面全文
- [ ] JSON 可被解析（逗号、引号正确）
- [ ] 若是模板题，`is_template` 为 `true`

## 本地验证

```bash
cd backend
python -c "import json; json.load(open('data/problems.json', encoding='utf-8')); print('OK')"
```
