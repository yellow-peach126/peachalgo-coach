<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api, type Plan } from "../api/client";

const loading = ref(true);
const error = ref("");
const plan = ref<Plan | null>(null);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    plan.value = await api.plan();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
  } finally {
    loading.value = false;
  }
}

const progressPct = computed(() => {
  if (!plan.value || !plan.value.total_items) return 0;
  return Math.round((plan.value.done_items / plan.value.total_items) * 100);
});

function statusClass(status: string) {
  const s = (status || "").toLowerCase();
  if (s.includes("done") || s.includes("完成")) return "done";
  if (s.includes("skip") || s.includes("跳过")) return "skip";
  return "pending";
}

onMounted(load);
</script>

<template>
  <section>
    <header class="page-header">
      <div>
        <p class="page-kicker">Roadmap</p>
        <h1 class="page-title">学习路线</h1>
        <p class="page-sub">
          按阶段排好的计划队列。完成反馈后系统会动态微调，你也可以在题库自选加题。
        </p>
      </div>
    </header>

    <div v-if="loading" class="stack">
      <div class="card"><div class="skeleton" style="width: 50%"></div></div>
      <div class="card"><div class="skeleton" style="width: 70%"></div></div>
    </div>

    <p v-else-if="error" class="error-text">
      {{ error }}
      <RouterLink to="/onboarding" class="gen-link">去生成计划</RouterLink>
    </p>

    <div v-else-if="plan" class="stack">
      <div class="card summary">
        <div class="summary-head">
          <div>
            <div class="summary-title">
              计划状态
              <span class="status-pill">{{ plan.status === "active" ? "进行中" : plan.status }}</span>
            </div>
            <div class="summary-sub muted">
              开始于 {{ plan.start_date }} · 周期 {{ plan.horizon_days }} 天
            </div>
          </div>
          <div class="summary-metric">
            <div class="metric-num">{{ plan.done_items }}/{{ plan.total_items }}</div>
            <div class="metric-label muted">已完成</div>
          </div>
        </div>
        <div class="progress" aria-hidden="true">
          <div class="progress-fill" :style="{ width: `${progressPct}%` }"></div>
        </div>
        <div class="progress-caption muted">总进度 {{ progressPct }}%</div>
      </div>

      <article
        v-for="item in plan.items"
        :key="item.id"
        class="card plan-item"
        :class="statusClass(item.status)"
      >
        <div class="plan-main">
          <div class="plan-title-row">
            <strong class="plan-title">{{ item.title_zh || item.title }}</strong>
            <div class="row plan-status-tags">
              <span class="tag" :class="statusClass(item.status)">
                {{ item.status_zh || item.status }}
              </span>
              <span class="tag" :class="(item.difficulty || '').toLowerCase()">
                {{ item.difficulty_zh || item.difficulty }}
              </span>
              <span class="tag">{{ item.item_type_zh || item.item_type }}</span>
            </div>
          </div>
          <div class="plan-meta muted">
            {{ item.scheduled_date }} · {{ item.stage_zh || item.stage }}
          </div>
          <div class="reason" v-if="item.reason">{{ item.reason }}</div>
          <div class="row plan-tags" v-if="item.tags_zh?.length">
            <span v-for="t in item.tags_zh" :key="t" class="tag">{{ t }}</span>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.gen-link {
  margin-left: 0.5rem;
  color: #fcd34d;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.summary {
  padding: 1.2rem 1.25rem;
}

.summary-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  flex-wrap: wrap;
}

.summary-title {
  font-weight: 720;
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: wrap;
  color: var(--text-strong);
}

.status-pill {
  display: inline-flex;
  padding: 0.16rem 0.55rem;
  border-radius: 999px;
  background: var(--accent-soft);
  border: 1px solid rgba(59, 130, 246, 0.28);
  color: #93c5fd;
  font-size: 0.8rem;
  font-weight: 650;
}

.summary-sub {
  margin-top: 0.35rem;
  font-size: 0.9rem;
}

.summary-metric {
  text-align: right;
}

.metric-num {
  font-size: 1.55rem;
  font-weight: 750;
  letter-spacing: -0.03em;
  color: var(--text-strong);
  line-height: 1.1;
}

.metric-label {
  font-size: 0.8rem;
  margin-top: 0.15rem;
}

.progress {
  margin-top: 1rem;
}

.progress-caption {
  margin-top: 0.45rem;
  font-size: 0.82rem;
}

.plan-item {
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}

.plan-item:hover {
  border-color: color-mix(in srgb, var(--accent) 35%, var(--border));
}

.plan-item.done {
  border-color: color-mix(in srgb, #22c55e 28%, var(--border));
  background: color-mix(in srgb, var(--panel) 94%, #22c55e 6%);
}

.plan-item.pending {
  border-color: color-mix(in srgb, var(--peach) 16%, var(--border));
}

.plan-item.skip {
  opacity: 0.72;
}

.plan-title-row {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: flex-start;
  flex-wrap: wrap;
  margin-bottom: 0.35rem;
}

.plan-title {
  font-size: 1.02rem;
  letter-spacing: -0.01em;
  color: var(--text-strong);
}

.plan-meta {
  font-size: 0.88rem;
  margin-bottom: 0.4rem;
}

.reason {
  font-size: 0.9rem;
  color: #d4e4ff;
  padding: 0.55rem 0.75rem;
  border-radius: 10px;
  background: var(--accent-soft);
  border: 1px solid rgba(59, 130, 246, 0.16);
  line-height: 1.45;
}

.plan-tags {
  margin-top: 0.5rem;
  gap: 0.4rem;
}

.tag.done {
  color: #86efac;
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.25);
}

.tag.skip {
  color: var(--muted);
}

.tag.pending {
  color: #fcd34d;
  background: var(--peach-soft);
  border-color: var(--peach-border);
}
</style>
