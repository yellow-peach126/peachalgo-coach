<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import {
  api,
  type AttemptPayload,
  type FeedbackSummary,
  type TodayDoneItem,
  type TodayItem,
  type TodayResponse,
} from "../api/client";

const router = useRouter();
const loading = ref(true);
const error = ref("");
const data = ref<TodayResponse | null>(null);
const feedbackOpen = ref(false);
const current = ref<TodayItem | null>(null);
const feedbackMsg = ref("");
const feedbackSummary = ref<FeedbackSummary | null>(null);
const submitting = ref(false);
const undoingId = ref<number | null>(null);

const form = reactive<AttemptPayload>({
  problem_id: "",
  result: "solved_solo",
  felt_difficulty: "ok",
  minutes_spent: 20,
  note: "",
  plan_item_id: undefined,
});

const sections = computed(() => {
  const items = data.value?.items || [];
  const review = items.filter((i) => (i.item_type || "").toLowerCase() === "review");
  const weak = items.filter((i) => (i.item_type || "").toLowerCase() === "weak");
  const main = items.filter((i) => {
    const t = (i.item_type || "main").toLowerCase();
    return t !== "review" && t !== "weak";
  });
  return [
    {
      key: "review",
      label: "复习到期",
      hint: "间隔复习：巩固做过的题，避免只刷不复盘",
      items: review,
    },
    {
      key: "weak",
      label: "弱项补强",
      hint: "针对吃力标签或阶段的巩固题",
      items: weak,
    },
    {
      key: "main",
      label: "主线推进",
      hint: "按学习路线排的今日主线题",
      items: main,
    },
  ].filter((s) => s.items.length > 0);
});

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const today = await api.today();
    data.value = {
      ...today,
      done_items: today.done_items || [],
      remaining_est_minutes: today.remaining_est_minutes ?? today.total_est_minutes ?? 0,
      spent_minutes: today.spent_minutes ?? 0,
    };
    if (!today.onboarded) {
      await router.replace("/onboarding");
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
  } finally {
    loading.value = false;
  }
}

function openFeedback(item: TodayItem) {
  current.value = item;
  form.problem_id = item.problem.id;
  form.plan_item_id = item.plan_item_id;
  form.minutes_spent = item.problem.est_minutes;
  form.result = "solved_solo";
  form.felt_difficulty = "ok";
  form.note = "";
  feedbackMsg.value = "";
  feedbackOpen.value = true;
}

function quickFeedback(item: TodayItem, result: AttemptPayload["result"]) {
  openFeedback(item);
  form.result = result;
  if (result === "failed") form.felt_difficulty = "hard";
  if (result === "solved_solo") form.felt_difficulty = "ok";
  if (result === "solved_solution") form.felt_difficulty = "hard";
}

async function submitFeedback() {
  submitting.value = true;
  try {
    const res = await api.attempt(form);
    feedbackMsg.value = res.message;
    feedbackSummary.value = res.summary || null;
    feedbackOpen.value = false;
    await load();
  } catch (e) {
    feedbackMsg.value = e instanceof Error ? e.message : "提交失败";
    feedbackSummary.value = null;
  } finally {
    submitting.value = false;
  }
}

async function skipItem(item: TodayItem) {
  await api.skip(item.plan_item_id);
  await load();
}

async function undoDone(item: TodayDoneItem) {
  if (!item.can_undo) return;
  undoingId.value = item.attempt_id;
  try {
    const res = await api.undoAttempt(item.attempt_id);
    feedbackMsg.value = res.message;
    feedbackSummary.value = res.summary || null;
    await load();
  } catch (e) {
    feedbackMsg.value = e instanceof Error ? e.message : "撤回失败";
    feedbackSummary.value = null;
  } finally {
    undoingId.value = null;
  }
}

function difficultyClass(d: string) {
  return d.toLowerCase();
}

function typeLabel(item: TodayItem) {
  return item.item_type_zh || item.item_type || "主线";
}

function dismissSummary() {
  feedbackSummary.value = null;
  feedbackMsg.value = "";
}

onMounted(load);
</script>

<template>
  <section class="today">
    <header class="page-header">
      <div>
        <p class="page-kicker">Today</p>
        <h1 class="page-title">今日任务</h1>
        <p class="page-sub">
          {{ data?.message || "加载今日安排..." }}
        </p>
      </div>
      <div class="page-meta" v-if="data && !loading">
        <RouterLink class="tag peach" to="/checkin">连续 {{ data.streak_days }} 天</RouterLink>
        <span class="tag signal">预算 {{ data.daily_minutes }} 分钟</span>
        <span class="tag">待做 {{ data.items.length }}</span>
        <span class="tag success" v-if="data.done_items?.length">
          已完成 {{ data.done_items.length }}
        </span>
        <RouterLink class="btn secondary" to="/problems">从题库添加</RouterLink>
      </div>
    </header>

    <div v-if="feedbackSummary" class="card summary-card">
      <div class="summary-head">
        <div>
          <div class="summary-title">教练变更摘要</div>
          <p class="summary-msg muted">{{ feedbackMsg || "反馈已处理，计划与掌握度已更新。" }}</p>
        </div>
        <button class="btn ghost" type="button" @click="dismissSummary">知道了</button>
      </div>
      <ul class="summary-list">
        <li v-for="(c, idx) in feedbackSummary.changes" :key="idx" class="summary-item">
          <span class="summary-kind" :class="c.kind">{{ c.label }}</span>
          <span class="summary-detail">{{ c.detail }}</span>
        </li>
      </ul>
      <div class="row summary-links">
        <RouterLink class="btn secondary" to="/stats">查看掌握度</RouterLink>
        <RouterLink class="btn ghost" to="/checkin">查看打卡</RouterLink>
        <RouterLink class="btn ghost" to="/plan">查看学习路线</RouterLink>
      </div>
    </div>

    <div v-if="loading" class="stack">
      <div class="card skeleton-card">
        <div class="skeleton" style="width: 40%; height: 1.1rem"></div>
        <div class="skeleton" style="width: 70%; margin-top: 0.9rem"></div>
        <div class="skeleton" style="width: 55%; margin-top: 0.55rem"></div>
      </div>
      <div class="card skeleton-card">
        <div class="skeleton" style="width: 48%; height: 1.1rem"></div>
        <div class="skeleton" style="width: 62%; margin-top: 0.9rem"></div>
      </div>
    </div>

    <p v-else-if="error" class="error-text">{{ error }}</p>

    <template v-else-if="data">
      <div
        v-if="data.items.length === 0 && (!data.done_items || data.done_items.length === 0)"
        class="card empty-state"
      >
        <h2>今天没有待做题</h2>
        <p>
          可能已全部完成，或计划还空着。可以从题库自选加题，也可以去看总路线与掌握度。
        </p>
        <div class="row">
          <RouterLink class="btn" to="/problems">去题库自选</RouterLink>
          <RouterLink class="btn secondary" to="/plan">查看总路线</RouterLink>
          <RouterLink class="btn ghost" to="/stats">查看掌握度</RouterLink>
          <RouterLink class="btn ghost" to="/checkin">查看打卡</RouterLink>
        </div>
      </div>

      <div
        v-if="data.items.length === 0 && data.done_items?.length"
        class="card empty-state done-empty"
      >
        <h2>今日待做已清空</h2>
        <p>不错。可以去打卡页分享今日记录，或提前看明日主线。</p>
        <div class="row">
          <RouterLink class="btn" to="/checkin">打开打卡日历</RouterLink>
          <RouterLink class="btn secondary" to="/plan">查看学习路线</RouterLink>
        </div>
      </div>

      <div v-for="sec in sections" :key="sec.key" class="stack task-list">
        <div class="section-label">
          <span>{{ sec.label }} · {{ sec.items.length }}</span>
        </div>
        <p class="section-hint muted">{{ sec.hint }}</p>
        <article
          v-for="(item, index) in sec.items"
          :key="item.plan_item_id"
          class="card task-card"
          :class="sec.key"
        >
          <div class="task-index" aria-hidden="true">
            {{ String(index + 1).padStart(2, "0") }}
          </div>

          <div class="task-body">
            <div class="task-top">
              <h2 class="task-title">
                <span class="task-id">#{{ item.problem.frontend_id || item.problem.number }}</span>
                {{ item.problem.title_zh || item.problem.title }}
              </h2>
              <div class="row task-tags">
                <span class="tag" :class="difficultyClass(item.problem.difficulty)">
                  {{ item.problem.difficulty_zh || item.problem.difficulty }}
                </span>
                <span class="tag">{{ typeLabel(item) }}</span>
                <span class="tag">约 {{ item.problem.est_minutes }} 分钟</span>
              </div>
            </div>

            <div class="coach-note reason">
              {{ item.reason || "今日推荐：推进主线进度。" }}
            </div>

            <div class="row algo-tags" v-if="item.problem.tags_zh?.length">
              <span v-for="tag in item.problem.tags_zh" :key="tag" class="tag">{{ tag }}</span>
            </div>

            <div class="task-actions row">
              <a class="btn" :href="item.problem.url" target="_blank" rel="noreferrer">
                去力扣做题
              </a>
              <button class="btn secondary" type="button" @click="openFeedback(item)">
                提交反馈
              </button>
              <button class="btn ghost" type="button" @click="skipItem(item)">改到明天</button>
            </div>
            <div class="row quick-row">
              <span class="muted quick-label">快速反馈</span>
              <button class="chip-btn" type="button" @click="quickFeedback(item, 'solved_solo')">
                独立通过
              </button>
              <button class="chip-btn" type="button" @click="quickFeedback(item, 'solved_solution')">
                看题解过
              </button>
              <button class="chip-btn" type="button" @click="quickFeedback(item, 'failed')">
                未完成
              </button>
            </div>
          </div>
        </article>
      </div>

      <div v-if="data.done_items?.length" class="stack done-list">
        <div class="section-label">今日已完成 · 点错可撤回</div>
        <article
          v-for="item in data.done_items"
          :key="item.attempt_id"
          class="card done-card"
        >
          <div class="done-mark" aria-hidden="true">✓</div>
          <div class="done-body">
            <div class="done-head">
              <div>
                <strong class="done-title">
                  #{{ item.problem.frontend_id || item.problem.number }}
                  {{ item.problem.title_zh || item.problem.title }}
                </strong>
                <div class="row done-tags">
                  <span class="tag signal">{{ item.result_zh || item.result }}</span>
                  <span class="tag">{{ item.felt_difficulty_zh || item.felt_difficulty }}</span>
                  <span class="tag">用时 {{ item.minutes_spent }} 分钟</span>
                </div>
              </div>
              <button
                v-if="item.can_undo"
                class="btn danger-ghost undo-btn"
                type="button"
                :disabled="undoingId === item.attempt_id"
                @click="undoDone(item)"
              >
                {{ undoingId === item.attempt_id ? "撤回中..." : "撤回反馈" }}
              </button>
            </div>
          </div>
        </article>
      </div>
    </template>

    <p v-if="feedbackMsg && !feedbackSummary" class="toast">{{ feedbackMsg }}</p>
    <p v-if="data?.source_note" class="source muted">{{ data.source_note }}</p>

    <div
      v-if="feedbackOpen"
      class="modal-mask"
      role="dialog"
      aria-modal="true"
      aria-labelledby="feedback-title"
      @click.self="feedbackOpen = false"
    >
      <div class="card modal">
        <h3 id="feedback-title">
          反馈：#{{ current?.problem.frontend_id }}
          {{ current?.problem.title_zh || current?.problem.title }}
        </h3>
        <p class="modal-sub">
          提交后会更新掌握度、学习路线、题库完成状态与打卡。点错可在「今日已完成」撤回。
        </p>

        <div class="field">
          <label for="result">结果</label>
          <select id="result" v-model="form.result">
            <option value="solved_solo">独立通过</option>
            <option value="solved_hint">看提示后通过</option>
            <option value="solved_solution">看题解后通过</option>
            <option value="failed">未完成</option>
          </select>
        </div>

        <div class="field">
          <label for="felt">主观难度</label>
          <select id="felt" v-model="form.felt_difficulty">
            <option value="too_easy">太简单</option>
            <option value="ok">刚好</option>
            <option value="hard">偏难</option>
            <option value="very_hard">很难</option>
          </select>
        </div>

        <div class="field">
          <label for="minutes">耗时（分钟）</label>
          <input
            id="minutes"
            v-model.number="form.minutes_spent"
            type="number"
            min="1"
            max="600"
          />
        </div>

        <div class="field">
          <label for="note">笔记（可选）</label>
          <textarea
            id="note"
            v-model="form.note"
            rows="3"
            placeholder="卡点、模板、复盘..."
          />
        </div>

        <div class="row">
          <button class="btn" type="button" :disabled="submitting" @click="submitFeedback">
            {{ submitting ? "保存中..." : "保存并调整计划" }}
          </button>
          <button class="btn ghost" type="button" @click="feedbackOpen = false">取消</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.summary-card {
  margin-bottom: 1.15rem;
  border-color: color-mix(in srgb, var(--accent) 35%, var(--border));
  background: color-mix(in srgb, var(--panel) 90%, #3b82f6 8%);
}

.summary-head {
  display: flex;
  justify-content: space-between;
  gap: 0.85rem;
  align-items: flex-start;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}

.summary-title {
  font-weight: 740;
  font-size: 1.02rem;
  color: var(--text-strong);
  margin-bottom: 0.25rem;
}

.summary-msg {
  margin: 0;
  font-size: 0.9rem;
  max-width: 56ch;
  line-height: 1.45;
}

.summary-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.45rem;
}

.summary-item {
  display: flex;
  gap: 0.65rem;
  align-items: baseline;
  flex-wrap: wrap;
  padding: 0.45rem 0.6rem;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.12);
  border: 1px solid color-mix(in srgb, var(--border) 80%, transparent);
}

.summary-kind {
  flex-shrink: 0;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  background: var(--panel-2);
  border: 1px solid var(--border);
  color: var(--muted);
}

.summary-kind.rating,
.summary-kind.mastery {
  color: #93c5fd;
  background: var(--accent-soft);
  border-color: rgba(59, 130, 246, 0.28);
}

.summary-kind.plan,
.summary-kind.review {
  color: #fcd34d;
  background: var(--peach-soft);
  border-color: var(--peach-border);
}

.summary-kind.checkin,
.summary-kind.restore {
  color: #86efac;
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.28);
}

.summary-detail {
  font-size: 0.92rem;
  color: var(--text);
}

.summary-links {
  margin-top: 0.85rem;
  gap: 0.5rem;
}

.section-hint {
  margin: -0.15rem 0 0.15rem;
  font-size: 0.84rem;
}

.task-list,
.done-list {
  gap: 0.85rem;
  margin-bottom: 1.4rem;
}

.task-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 1.05rem;
  align-items: start;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    background 0.15s ease;
}

.task-card:hover {
  border-color: color-mix(in srgb, var(--peach) 42%, var(--border));
  box-shadow: var(--shadow-card);
  background: color-mix(in srgb, var(--panel) 92%, var(--panel-2));
}

.task-card.review {
  border-color: color-mix(in srgb, var(--accent) 28%, var(--border));
}

.task-card.weak {
  border-color: color-mix(in srgb, var(--peach) 28%, var(--border));
}

.task-index {
  width: 2.55rem;
  height: 2.55rem;
  margin-top: 0.05rem;
  border-radius: 11px;
  display: grid;
  place-items: center;
  font-size: 0.8rem;
  font-weight: 750;
  letter-spacing: 0.04em;
  color: #fcd34d;
  background: var(--peach-soft);
  border: 1px solid var(--peach-border);
}

.task-card.review .task-index {
  color: #93c5fd;
  background: var(--accent-soft);
  border-color: rgba(59, 130, 246, 0.28);
}

.task-body {
  min-width: 0;
}

.task-top {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  margin-bottom: 0.8rem;
}

.task-title {
  margin: 0;
  font-size: 1.12rem;
  font-weight: 720;
  letter-spacing: -0.018em;
  line-height: 1.35;
  color: var(--text-strong);
}

.task-id {
  color: var(--muted-2);
  font-weight: 650;
  margin-right: 0.28rem;
}

.task-tags {
  gap: 0.4rem;
}

.reason {
  margin-bottom: 0.8rem;
}

.algo-tags {
  margin-bottom: 1rem;
  gap: 0.4rem;
}

.task-actions {
  gap: 0.55rem;
}

.quick-row {
  margin-top: 0.7rem;
  gap: 0.4rem;
}

.quick-label {
  font-size: 0.8rem;
  font-weight: 600;
}

.chip-btn {
  border: 1px solid var(--border);
  background: transparent;
  color: var(--muted);
  border-radius: 999px;
  padding: 0.28rem 0.7rem;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 600;
}

.chip-btn:hover {
  border-color: var(--border-strong);
  color: var(--text);
  background: rgba(255, 255, 255, 0.03);
}

.done-empty {
  margin-bottom: 1rem;
}

.done-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.9rem;
  align-items: start;
  border-color: color-mix(in srgb, var(--accent-2) 26%, var(--border));
  background: color-mix(in srgb, var(--panel) 94%, #22c55e 6%);
}

.done-mark {
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  display: grid;
  place-items: center;
  font-size: 0.85rem;
  font-weight: 800;
  color: #052e16;
  background: #22c55e;
  margin-top: 0.15rem;
}

.done-body {
  min-width: 0;
}

.done-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.85rem;
  flex-wrap: wrap;
}

.done-title {
  display: block;
  margin-bottom: 0.45rem;
  font-size: 1rem;
  color: var(--text-strong);
}

.done-tags {
  gap: 0.4rem;
}

.undo-btn {
  flex-shrink: 0;
}

.toast {
  margin-top: 0.75rem;
  padding: 0.75rem 0.95rem;
  border-radius: 12px;
  background: rgba(34, 197, 94, 0.08);
  border: 1px solid rgba(34, 197, 94, 0.22);
  color: #bbf7d0;
  font-size: 0.92rem;
}

.source {
  margin-top: 1rem;
  font-size: 0.82rem;
  color: var(--muted-2);
}

.skeleton-card {
  min-height: 118px;
}

@media (max-width: 640px) {
  .task-card {
    grid-template-columns: 1fr;
  }

  .task-index {
    width: fit-content;
    height: auto;
    padding: 0.28rem 0.55rem;
  }

  .task-actions .btn {
    flex: 1 1 auto;
  }

  .done-card {
    grid-template-columns: 1fr;
  }

  .done-mark {
    width: fit-content;
    height: auto;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
  }
}
</style>
