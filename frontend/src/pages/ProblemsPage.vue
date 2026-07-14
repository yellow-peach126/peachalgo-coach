<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { api, type Meta, type Problem } from "../api/client";

const loading = ref(true);
const error = ref("");
const message = ref("");
const problems = ref<Problem[]>([]);
/** Always from /api/today — independent of bank filters/limit. */
const todayPicked = ref<
  Array<{ problem: Problem; plan_item_id: number; item_type: string }>
>([]);
const meta = ref<Meta | null>(null);
/** Local multi-select for problems not yet in today / completed. */
const selected = ref<Record<string, boolean>>({});
const busyId = ref<string | null>(null);

const q = ref("");
const stage = ref("");
const difficulty = ref("");
const tag = ref("");

async function loadMeta() {
  meta.value = await api.meta();
}

async function loadTodayPicked() {
  try {
    const today = await api.today();
    todayPicked.value = (today.items || []).map((item) => {
      const canWithdraw = item.item_type === "custom";
      return {
        problem: {
          ...item.problem,
          in_today: true,
          today_plan_item_id: item.plan_item_id,
          today_item_type: item.item_type,
          can_withdraw_today: canWithdraw,
          completed: false,
        },
        plan_item_id: item.plan_item_id,
        item_type: item.item_type,
      };
    });
  } catch {
    // Bank still usable without today panel if offline/not onboarded edge.
    todayPicked.value = [];
  }
}

async function loadProblems() {
  loading.value = true;
  error.value = "";
  try {
    const [list] = await Promise.all([
      api.problems({
        q: q.value || undefined,
        stage: stage.value || undefined,
        difficulty: difficulty.value || undefined,
        tag: tag.value || undefined,
        limit: 100,
      }),
      loadTodayPicked(),
    ]);
    const todayIds = new Set(todayPicked.value.map((t) => t.problem.id));
    // Merge authoritative today flags (problems list may miss some under filters).
    problems.value = [...list]
      .map((p) => {
        const hit = todayPicked.value.find((t) => t.problem.id === p.id);
        if (hit && !p.completed) {
          const itemType = p.today_item_type || hit.item_type;
          return {
            ...p,
            in_today: true,
            today_plan_item_id: p.today_plan_item_id ?? hit.plan_item_id,
            today_item_type: itemType,
            can_withdraw_today:
              p.can_withdraw_today ?? itemType === "custom",
          };
        }
        if (!todayIds.has(p.id)) {
          return {
            ...p,
            in_today: false,
            today_plan_item_id: null,
            today_item_type: null,
            can_withdraw_today: false,
          };
        }
        return p;
      })
      .sort((a, b) => {
        const as = a.completed ? 2 : a.in_today ? 0 : 1;
        const bs = b.completed ? 2 : b.in_today ? 0 : 1;
        if (as !== bs) return as - bs;
        return (a.number || 0) - (b.number || 0);
      });
    const next = { ...selected.value };
    for (const p of problems.value) {
      if (p.completed || p.in_today) delete next[p.id];
    }
    selected.value = next;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
  } finally {
    loading.value = false;
  }
}

const selectedCount = computed(
  () => Object.keys(selected.value).filter((id) => selected.value[id]).length,
);

const inTodayProblems = computed(() => todayPicked.value.map((t) => t.problem));

/** Only bank-added custom picks can be withdrawn from the catalog. */
const withdrawableTodayProblems = computed(() =>
  todayPicked.value.filter((t) => t.item_type === "custom").map((t) => t.problem),
);

const selectedIds = () => Object.keys(selected.value).filter((id) => selected.value[id]);

function isCompleted(id: string) {
  return !!problems.value.find((p) => p.id === id)?.completed;
}

function isInToday(id: string) {
  return !!problems.value.find((p) => p.id === id)?.in_today;
}

function canWithdraw(p: Problem) {
  if (!p.in_today || p.completed) return false;
  if (typeof p.can_withdraw_today === "boolean") return p.can_withdraw_today;
  return p.today_item_type === "custom";
}

function toggle(id: string) {
  const p = problems.value.find((x) => x.id === id);
  if (!p) return;
  if (p.completed) {
    message.value = "该题已完成，不可再选入今日。如需重做，请先在今日任务撤回反馈。";
    return;
  }
  // Clicking the left box on a withdrawable in-today problem = withdraw.
  if (p.in_today) {
    if (canWithdraw(p)) {
      void withdrawFromToday(p);
    } else {
      message.value =
        "这道题来自学习路线，不能在题库里撤回。它会留在今日任务与学习路线中。";
    }
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
  const ids = selectedIds().filter((id) => !isCompleted(id) && !isInToday(id));
  if (!ids.length) {
    message.value = "请先勾选未完成、且未在今日队列的题目";
    return;
  }
  try {
    const res = await api.addToday(ids);
    message.value = res.message || `已加入今日任务 ${res.added} 题。可在上方「今日已选」撤回。`;
    selected.value = {};
    await loadProblems();
  } catch (e) {
    message.value = e instanceof Error ? e.message : "添加失败";
  }
}

async function withdrawFromToday(p: Problem) {
  if (p.completed) return;
  const fromPanel = todayPicked.value.find((t) => t.problem.id === p.id);
  const planItemId = p.today_plan_item_id || fromPanel?.plan_item_id;
  if (!p.in_today && !fromPanel) return;
  if (!canWithdraw(p) && fromPanel?.item_type !== "custom") {
    message.value =
      "这道题来自学习路线，不能在题库里撤回。它会留在今日任务与学习路线中。";
    return;
  }
  busyId.value = p.id;
  try {
    const res = await api.removeToday({
      problem_ids: [p.id],
      plan_item_ids: planItemId ? [planItemId] : undefined,
    });
    message.value = res.message || "已从今日撤回自选题";
    await loadProblems();
  } catch (e) {
    message.value = e instanceof Error ? e.message : "撤回失败";
  } finally {
    busyId.value = null;
  }
}

async function addOne(p: Problem) {
  if (p.completed || p.in_today) return;
  busyId.value = p.id;
  try {
    const res = await api.addToday([p.id]);
    message.value = res.message || "已加入今日。可点「撤回选择」移出。";
    if (selected.value[p.id]) {
      const next = { ...selected.value };
      delete next[p.id];
      selected.value = next;
    }
    await loadProblems();
  } catch (e) {
    message.value = e instanceof Error ? e.message : "添加失败";
  } finally {
    busyId.value = null;
  }
}

function primaryAction(p: Problem) {
  if (p.completed) return;
  if (p.in_today) {
    if (canWithdraw(p)) {
      void withdrawFromToday(p);
    } else {
      message.value =
        "这道题来自学习路线，不能在题库里撤回。它会留在今日任务与学习路线中。";
    }
    return;
  }
  if (isSelected(p.id)) {
    toggle(p.id);
    return;
  }
  void addOne(p);
}

function primaryLabel(p: Problem) {
  if (p.completed) return "已完成";
  if (busyId.value === p.id) {
    return p.in_today && canWithdraw(p) ? "撤回中..." : "处理中...";
  }
  if (p.in_today) return canWithdraw(p) ? "撤回选择" : "路线题";
  if (isSelected(p.id)) return "取消勾选";
  return "选入今日";
}

function statusLabel(p: Problem) {
  if (p.completed) return "已完成";
  if (p.in_today) return canWithdraw(p) ? "已选择" : "路线题";
  if (isSelected(p.id)) return "已勾选";
  return "选择";
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
  <section class="problems-page" :class="{ 'has-dock': true }">
    <header class="page-header">
      <div>
        <p class="page-kicker">Catalog</p>
        <h1 class="page-title">题库</h1>
        <p class="page-sub">
          勾选题目后，用底部「加入今日」确认。你从题库加的题可「撤回选择」；学习路线题会保留在路线里，不能在这里撤掉。
        </p>
        <p class="catalog-note muted">
          {{ meta?.source_note || "题号来源于 LeetCode / 力扣，已排除 Plus 专享题。" }}
          <template v-if="meta">当前免费题 {{ meta.catalog.total }} 道。</template>
        </p>
      </div>
      <div class="page-meta">
        <span v-if="inTodayProblems.length" class="tag signal">
          今日已选 {{ inTodayProblems.length }}
        </span>
        <span v-if="selectedCount" class="tag peach">待确认 {{ selectedCount }}</span>
      </div>
    </header>

    <div v-if="inTodayProblems.length" class="card today-panel">
      <div class="today-panel-head">
        <div>
          <div class="today-panel-title">今日队列</div>
          <p class="today-panel-sub muted">
            仅「自选题」可在此撤回。学习路线题会留在今日任务与学习路线中。
          </p>
        </div>
        <RouterLink class="btn secondary" to="/">查看今日任务</RouterLink>
      </div>
      <div class="today-chip-row">
        <div v-for="p in inTodayProblems" :key="`today-${p.id}`" class="today-chip">
          <span class="today-chip-title">
            <span
              class="today-chip-mark"
              :class="{ roadmap: !canWithdraw(p) }"
              aria-hidden="true"
            >
              {{ canWithdraw(p) ? "自选题" : "路线题" }}
            </span>
            #{{ p.frontend_id || p.number }} {{ p.title_zh || p.title }}
          </span>
          <button
            v-if="canWithdraw(p)"
            type="button"
            class="btn danger-ghost chip-withdraw"
            :disabled="busyId === p.id"
            @click="withdrawFromToday(p)"
          >
            {{ busyId === p.id ? "撤回中..." : "撤回选择" }}
          </button>
          <span v-else class="roadmap-lock muted">路线保留</span>
        </div>
      </div>
    </div>

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
        :class="{
          selected: isSelected(p.id),
          completed: !!p.completed,
          'in-today': !!p.in_today && !p.completed,
        }"
      >
        <button
          type="button"
          class="select-box"
          :class="{
            on: isSelected(p.id) || !!p.in_today,
            locked: !!p.completed || (!!p.in_today && !canWithdraw(p)),
            today: !!p.in_today && !p.completed && canWithdraw(p),
            roadmap: !!p.in_today && !p.completed && !canWithdraw(p),
          }"
          :disabled="!!p.completed || busyId === p.id || (!!p.in_today && !canWithdraw(p))"
          :aria-pressed="isSelected(p.id) || !!p.in_today"
          :aria-label="
            p.completed
              ? `${p.title_zh || p.title} 已完成`
              : p.in_today
                ? canWithdraw(p)
                  ? `撤回选择 ${p.title_zh || p.title}`
                  : `${p.title_zh || p.title} 为学习路线题，不可撤回`
                : isSelected(p.id)
                  ? `取消勾选 ${p.title_zh || p.title}`
                  : `勾选 ${p.title_zh || p.title}`
          "
          @click="toggle(p.id)"
        >
          <span class="select-check">
            {{ p.completed || p.in_today || isSelected(p.id) ? "✓" : "" }}
          </span>
          <span class="select-text">{{ statusLabel(p) }}</span>
        </button>

        <div class="problem-main">
          <strong class="problem-title">
            #{{ p.frontend_id || p.number }} {{ p.title_zh || p.title }}
            <span v-if="p.completed" class="done-badge">已完成</span>
            <span v-else-if="p.in_today && canWithdraw(p)" class="today-badge">已选择</span>
            <span v-else-if="p.in_today" class="roadmap-badge">路线题</span>
            <span v-else-if="isSelected(p.id)" class="picked-badge">已勾选</span>
          </strong>
          <div class="problem-en muted">
            {{ p.title }} · {{ p.stage_zh || p.stage }}
            <template v-if="p.completed && p.completed_result_zh">
              · 上次：{{ p.completed_result_zh }}
            </template>
            <template v-else-if="p.in_today && canWithdraw(p)"> · 自选加入今日，可撤回</template>
            <template v-else-if="p.in_today"> · 学习路线安排，不可在此撤回</template>
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
            <span v-else-if="p.in_today && canWithdraw(p)" class="tag signal">自选今日</span>
            <span v-else-if="p.in_today" class="tag">路线今日</span>
            <span v-for="t in p.tags_zh" :key="t" class="tag">{{ t }}</span>
          </div>
        </div>

        <div class="problem-actions">
          <button
            v-if="!p.in_today || canWithdraw(p) || p.completed"
            type="button"
            class="btn"
            :class="p.in_today && !p.completed ? 'danger-ghost withdraw-btn' : isSelected(p.id) ? 'secondary' : ''"
            :disabled="!!p.completed || busyId === p.id"
            @click="primaryAction(p)"
          >
            {{ primaryLabel(p) }}
          </button>
          <span v-else class="btn secondary roadmap-keep" title="学习路线题，保留在计划中">路线保留</span>
          <a class="btn ghost" :href="p.url" target="_blank" rel="noreferrer">打开力扣</a>
        </div>
      </article>
      <p v-if="!problems.length" class="muted empty-line">没有匹配的题目，试试换个筛选条件。</p>
    </div>

    <!-- Fixed bottom dock: always visible while scrolling -->
    <div class="today-dock" role="region" aria-label="加入今日任务">
      <div class="today-dock-inner">
        <div class="today-dock-copy">
          <div class="today-dock-title">
            <template v-if="selectedCount > 0">已勾选 {{ selectedCount }} 题，确认加入今日</template>
            <template v-else-if="withdrawableTodayProblems.length > 0">
              自选题 {{ withdrawableTodayProblems.length }} · 可撤回；路线题不会被撤掉
            </template>
            <template v-else-if="inTodayProblems.length > 0">
              今日 {{ inTodayProblems.length }} 题均为学习路线安排
            </template>
            <template v-else>勾选题目后点此加入今日</template>
          </div>
          <p class="today-dock-sub muted">
            底部固定栏；只有你从题库添加的题可以撤回，不会改动学习路线。
          </p>
        </div>
        <div class="today-dock-actions">
          <button
            v-if="selectedCount > 0"
            type="button"
            class="btn secondary dock-clear"
            @click="selected = {}"
          >
            清空勾选
          </button>
          <button
            type="button"
            class="btn add-today-btn dock-primary"
            :disabled="selectedCount === 0"
            @click="addSelected"
          >
            加入今日（{{ selectedCount }}）
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.problems-page.has-dock {
  /* leave room so last cards aren't hidden behind the fixed dock */
  padding-bottom: 6.5rem;
}

.catalog-note {
  margin: 0.45rem 0 0;
  font-size: 0.86rem;
  max-width: 58ch;
  line-height: 1.5;
}

.today-panel {
  margin-bottom: 1rem;
  border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
  background: color-mix(in srgb, var(--panel) 88%, #3b82f6 10%);
  padding: 1rem 1.1rem;
}

.today-panel-head {
  display: flex;
  justify-content: space-between;
  gap: 0.85rem;
  align-items: flex-start;
  flex-wrap: wrap;
  margin-bottom: 0.85rem;
}

.today-panel-title {
  font-weight: 740;
  color: var(--text-strong);
  margin-bottom: 0.25rem;
}

.today-panel-sub {
  margin: 0;
  font-size: 0.88rem;
  max-width: 52ch;
  line-height: 1.45;
}

.today-chip-row {
  display: grid;
  gap: 0.55rem;
}

.today-chip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding: 0.65rem 0.8rem;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.16);
  border: 1px solid color-mix(in srgb, var(--border) 80%, transparent);
}

.today-chip-title {
  font-weight: 650;
  color: var(--text-strong);
  font-size: 0.95rem;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.today-chip-mark {
  display: inline-flex;
  align-items: center;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 750;
  color: #93c5fd;
  background: rgba(59, 130, 246, 0.16);
  border: 1px solid rgba(59, 130, 246, 0.35);
}

.today-chip-mark.roadmap {
  color: var(--muted);
  background: rgba(154, 173, 196, 0.1);
  border-color: color-mix(in srgb, var(--border) 80%, transparent);
}

.roadmap-lock {
  font-size: 0.82rem;
  font-weight: 650;
  padding: 0.35rem 0.55rem;
}

.chip-withdraw {
  flex-shrink: 0;
  min-height: 2.2rem;
  padding: 0.4rem 0.85rem;
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

/* Fixed bottom action dock */
.today-dock {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 40;
  pointer-events: none;
  padding: 0 1rem calc(0.75rem + env(safe-area-inset-bottom, 0px));
}

.today-dock-inner {
  pointer-events: auto;
  max-width: var(--content, 1040px);
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 0.85rem 1rem;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--accent) 35%, var(--border));
  background: rgba(15, 22, 34, 0.92);
  backdrop-filter: blur(14px) saturate(1.15);
  box-shadow:
    0 12px 40px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.03) inset;
}

.today-dock-copy {
  min-width: 0;
  flex: 1 1 220px;
}

.today-dock-title {
  font-weight: 740;
  color: var(--text-strong);
  font-size: 0.98rem;
  letter-spacing: -0.01em;
}

.today-dock-sub {
  margin: 0.2rem 0 0;
  font-size: 0.82rem;
  line-height: 1.4;
}

.today-dock-actions {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-shrink: 0;
}

.dock-primary {
  min-width: 148px;
  min-height: 2.65rem;
  font-weight: 750;
  box-shadow: 0 8px 22px rgba(59, 130, 246, 0.22);
}

.dock-primary:disabled {
  box-shadow: none;
  opacity: 0.55;
}

.dock-clear {
  min-height: 2.65rem;
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

.problem-card.in-today {
  border-color: color-mix(in srgb, var(--accent) 45%, var(--border));
  background: color-mix(in srgb, var(--panel) 88%, #3b82f6 10%);
}

.problem-card.completed {
  border-color: color-mix(in srgb, #22c55e 28%, var(--border));
  opacity: 0.93;
}

.done-badge,
.today-badge,
.roadmap-badge,
.picked-badge {
  display: inline-flex;
  margin-left: 0.4rem;
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  vertical-align: middle;
}

.done-badge {
  color: #86efac;
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.28);
}

.today-badge {
  color: #93c5fd;
  background: rgba(59, 130, 246, 0.14);
  border: 1px solid rgba(59, 130, 246, 0.35);
}

.roadmap-badge {
  color: #cbd5e1;
  background: rgba(148, 163, 184, 0.12);
  border: 1px solid rgba(148, 163, 184, 0.28);
}

.picked-badge {
  color: #fcd34d;
  background: rgba(245, 158, 11, 0.14);
  border: 1px solid rgba(245, 158, 11, 0.35);
}

.roadmap-keep {
  cursor: default;
  opacity: 0.9;
  text-align: center;
  justify-content: center;
}

.select-box.roadmap {
  cursor: default;
  border-color: color-mix(in srgb, var(--border) 90%, #94a3b8);
  background: rgba(148, 163, 184, 0.08);
  color: #cbd5e1;
}

.select-box.roadmap .select-check {
  background: #64748b;
  border-color: #64748b;
  color: #fff;
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

.select-box.today {
  border-color: rgba(59, 130, 246, 0.6);
  background: rgba(59, 130, 246, 0.16);
  color: #93c5fd;
  cursor: pointer;
}

.select-box.today:hover:not(:disabled) {
  border-color: rgba(239, 68, 68, 0.55);
  background: rgba(239, 68, 68, 0.12);
  color: #fca5a5;
}

.select-box.today .select-check {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #fff;
}

.select-box.today:hover:not(:disabled) .select-check {
  background: #ef4444;
  border-color: #ef4444;
  color: #fff;
}

.select-box.locked {
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

.select-box.on:not(.today) .select-check {
  background: #f59e0b;
  border-color: #f59e0b;
  color: #1a1205;
}

.select-box.locked .select-check {
  background: #22c55e;
  border-color: #22c55e;
  color: #052e16;
}

.select-text {
  font-size: 0.78rem;
  font-weight: 700;
  text-align: center;
  line-height: 1.2;
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
  min-width: 128px;
}

.problem-actions .btn,
.problem-actions a.btn {
  text-align: center;
  justify-content: center;
}

.withdraw-btn {
  font-weight: 700;
}

@media (max-width: 800px) {
  .problems-page.has-dock {
    padding-bottom: 8.5rem;
  }

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

  .today-dock-inner {
    flex-direction: column;
    align-items: stretch;
    gap: 0.7rem;
  }

  .today-dock-actions {
    width: 100%;
  }

  .dock-primary,
  .dock-clear {
    flex: 1;
  }
}
</style>
