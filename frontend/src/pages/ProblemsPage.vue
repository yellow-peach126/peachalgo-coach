<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { api, type Meta, type Problem } from "../api/client";

const loading = ref(true);
const error = ref("");
const message = ref("");
const problems = ref<Problem[]>([]);
const meta = ref<Meta | null>(null);
const selected = ref<Record<string, boolean>>({});

const q = ref("");
const stage = ref("");
const difficulty = ref("");
const tag = ref("");

async function loadMeta() {
  meta.value = await api.meta();
}

async function loadProblems() {
  loading.value = true;
  error.value = "";
  try {
    problems.value = await api.problems({
      q: q.value || undefined,
      stage: stage.value || undefined,
      difficulty: difficulty.value || undefined,
      tag: tag.value || undefined,
      limit: 100,
    });
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
  } finally {
    loading.value = false;
  }
}

const selectedCount = computed(
  () => Object.keys(selected.value).filter((id) => selected.value[id]).length,
);

const selectedIds = () => Object.keys(selected.value).filter((id) => selected.value[id]);

function isCompleted(id: string) {
  return !!problems.value.find((p) => p.id === id)?.completed;
}

function toggle(id: string) {
  if (isCompleted(id)) {
    message.value = "该题已完成，不可再选入今日。如需重做，请先在今日任务撤回反馈。";
    return;
  }
  selected.value = {
    ...selected.value,
    [id]: !selected.value[id],
  };
}

function isSelected(id: string) {
  return !!selected.value[id];
}

async function addSelected() {
  const ids = selectedIds().filter((id) => !isCompleted(id));
  if (!ids.length) {
    message.value = "请先勾选未完成的题目";
    return;
  }
  try {
    const res = await api.addToday(ids);
    message.value = res.message || `已加入今日任务 ${res.added} 题`;
    if (res.added > 0) {
      selected.value = {};
    }
  } catch (e) {
    message.value = e instanceof Error ? e.message : "添加失败";
  }
}

let timer: number | undefined;
watch([q, stage, difficulty, tag], () => {
  window.clearTimeout(timer);
  timer = window.setTimeout(loadProblems, 250);
});

onMounted(async () => {
  try {
    await loadMeta();
    await loadProblems();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
    loading.value = false;
  }
});
</script>

<template>
  <section>
    <header class="page-header">
      <div>
        <p class="page-kicker">Catalog</p>
        <h1 class="page-title">题库</h1>
        <p class="page-sub">
          按算法类型 / 难度 / 学习阶段筛选，把题加入今日任务。教练优先推荐今日列表；题库是补充。
        </p>
        <p class="catalog-note muted">
          {{ meta?.source_note || "题号来源于 LeetCode / 力扣，已排除 Plus 专享题。" }}
          <template v-if="meta">当前免费题 {{ meta.catalog.total }} 道。</template>
        </p>
      </div>
      <div class="page-meta">
        <button class="btn add-today-btn" :disabled="selectedCount === 0" @click="addSelected">
          加入今日（{{ selectedCount }}）
        </button>
      </div>
    </header>

    <div class="card filters">
      <input v-model="q" class="filter-input" placeholder="搜索题号 / 标题 / 标签" />
      <select v-model="difficulty" class="filter-input">
        <option value="">全部难度</option>
        <option v-for="d in meta?.difficulties || []" :key="d.id" :value="d.id">
          {{ d.label }}
        </option>
      </select>
      <select v-model="stage" class="filter-input">
        <option value="">全部阶段</option>
        <option v-for="s in meta?.stages || []" :key="s.id" :value="s.id">
          {{ s.title }}
        </option>
      </select>
      <select v-model="tag" class="filter-input">
        <option value="">全部算法类型</option>
        <option v-for="t in meta?.tags || []" :key="t.id" :value="t.id">
          {{ t.label }}
        </option>
      </select>
    </div>

    <p v-if="message" class="msg">{{ message }}</p>
    <p v-if="loading" class="muted loading-line">加载中...</p>
    <p v-else-if="error" class="error-text">{{ error }}</p>

    <div v-else class="stack list">
      <article
        v-for="p in problems"
        :key="p.id"
        class="card problem-card"
        :class="{ selected: isSelected(p.id), completed: !!p.completed }"
      >
        <button
          type="button"
          class="select-box"
          :class="{ on: isSelected(p.id), locked: !!p.completed }"
          :disabled="!!p.completed"
          :aria-pressed="isSelected(p.id)"
          :aria-label="
            p.completed
              ? `${p.title_zh || p.title} 已完成，不可选择`
              : isSelected(p.id)
                ? `取消选择 ${p.title_zh || p.title}`
                : `选择 ${p.title_zh || p.title}`
          "
          @click="toggle(p.id)"
        >
          <span class="select-check">{{ p.completed ? "✓" : isSelected(p.id) ? "✓" : "" }}</span>
          <span class="select-text">
            {{ p.completed ? "已完成" : isSelected(p.id) ? "已选" : "选择" }}
          </span>
        </button>

        <div class="problem-main">
          <strong class="problem-title">
            #{{ p.frontend_id || p.number }} {{ p.title_zh || p.title }}
            <span v-if="p.completed" class="done-badge">已完成</span>
          </strong>
          <div class="problem-en muted">
            {{ p.title }} · {{ p.stage_zh || p.stage }}
            <template v-if="p.completed && p.completed_result_zh">
              · 上次：{{ p.completed_result_zh }}
            </template>
          </div>
          <div class="row problem-tags">
            <span class="tag" :class="p.difficulty.toLowerCase()">
              {{ p.difficulty_zh || p.difficulty }}
            </span>
            <span class="tag">约 {{ p.est_minutes }} 分钟</span>
            <span v-if="p.is_template" class="tag peach">模板题</span>
            <span v-if="p.completed" class="tag signal">
              {{ p.completed_result_zh || "已做过" }}
            </span>
            <span v-for="t in p.tags_zh" :key="t" class="tag">{{ t }}</span>
          </div>
        </div>

        <div class="problem-actions">
          <button
            type="button"
            class="btn"
            :class="isSelected(p.id) ? 'secondary' : ''"
            :disabled="!!p.completed"
            @click="toggle(p.id)"
          >
            {{ p.completed ? "已完成" : isSelected(p.id) ? "取消选择" : "选入今日" }}
          </button>
          <a class="btn ghost" :href="p.url" target="_blank" rel="noreferrer">打开力扣</a>
        </div>
      </article>
      <p v-if="!problems.length" class="muted empty-line">没有匹配的题目，试试换个筛选条件。</p>
    </div>
  </section>
</template>

<style scoped>
.catalog-note {
  margin: 0.45rem 0 0;
  font-size: 0.86rem;
  max-width: 58ch;
  line-height: 1.5;
}

.filters {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 0.7rem;
  margin-bottom: 1rem;
  padding: 0.9rem;
}

.add-today-btn {
  min-width: 140px;
  white-space: nowrap;
}

.msg {
  margin: 0 0 0.85rem;
  padding: 0.65rem 0.85rem;
  border-radius: 12px;
  background: rgba(34, 197, 94, 0.08);
  border: 1px solid rgba(34, 197, 94, 0.2);
  color: #bbf7d0;
  font-size: 0.92rem;
}

.loading-line,
.empty-line {
  margin: 0.5rem 0;
}

.list {
  gap: 0.8rem;
}

.problem-card {
  display: grid;
  grid-template-columns: 84px 1fr auto;
  gap: 1rem;
  align-items: center;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    box-shadow 0.15s ease;
}

.problem-card.selected {
  border-color: var(--peach-border);
  background: color-mix(in srgb, var(--panel) 90%, #f59e0b 8%);
  box-shadow: 0 10px 28px rgba(245, 158, 11, 0.06);
}

.problem-card.completed {
  border-color: color-mix(in srgb, #22c55e 28%, var(--border));
  opacity: 0.93;
}

.problem-card.completed .problem-actions .btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.done-badge {
  display: inline-flex;
  margin-left: 0.4rem;
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  vertical-align: middle;
  color: #86efac;
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.28);
}

.select-box {
  width: 84px;
  min-height: 84px;
  border-radius: 13px;
  border: 1.5px solid var(--border);
  background: var(--panel-2);
  color: var(--muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  cursor: pointer;
  padding: 0.5rem;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    color 0.15s ease;
}

.select-box:hover:not(:disabled) {
  border-color: var(--peach-border);
  color: #fde68a;
}

.select-box.on {
  border-color: var(--peach);
  background: rgba(245, 158, 11, 0.15);
  color: #fcd34d;
}

.select-box.locked,
.select-box:disabled {
  cursor: not-allowed;
  border-color: rgba(34, 197, 94, 0.35);
  background: rgba(34, 197, 94, 0.1);
  color: #86efac;
}

.select-box:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.select-check {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  border: 2px solid currentColor;
  display: grid;
  place-items: center;
  font-size: 0.95rem;
  font-weight: 800;
  line-height: 1;
}

.select-box.on .select-check {
  background: #f59e0b;
  border-color: #f59e0b;
  color: #1a1205;
}

.select-box.locked .select-check,
.select-box:disabled .select-check {
  background: #22c55e;
  border-color: #22c55e;
  color: #052e16;
}

.select-text {
  font-size: 0.82rem;
  font-weight: 700;
}

.problem-main {
  min-width: 0;
}

.problem-title {
  display: block;
  margin-bottom: 0.2rem;
  font-size: 1.02rem;
  letter-spacing: -0.01em;
  color: var(--text-strong);
}

.problem-en {
  font-size: 0.88rem;
}

.problem-tags {
  margin-top: 0.5rem;
  gap: 0.4rem;
}

.problem-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 118px;
}

.problem-actions .btn,
.problem-actions a.btn {
  text-align: center;
  justify-content: center;
}

@media (max-width: 800px) {
  .filters {
    grid-template-columns: 1fr;
  }

  .problem-card {
    grid-template-columns: 72px 1fr;
  }

  .select-box {
    width: 72px;
    min-height: 72px;
  }

  .problem-actions {
    grid-column: 1 / -1;
    flex-direction: row;
  }

  .problem-actions .btn,
  .problem-actions a.btn {
    flex: 1;
  }
}
</style>
