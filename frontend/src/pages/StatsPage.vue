<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, type Stats } from "../api/client";

const loading = ref(true);
const error = ref("");
const stats = ref<Stats | null>(null);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    // Always live from remaining attempts / skill rows (submit & undo both rewrite these).
    stats.value = await api.stats();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section>
    <header class="page-header">
      <div>
        <p class="page-kicker">Mastery</p>
        <h1 class="page-title">掌握度与统计</h1>
        <p class="page-sub">
          分数来自你提交的做题反馈，不是力扣 AC 率。没有反馈的标签显示为未评估，不会假装「已经会一半」。
        </p>
      </div>
    </header>

    <div v-if="loading" class="stack">
      <div class="stats-grid">
        <div class="card stat-card"><div class="skeleton" style="width: 40%"></div></div>
        <div class="card stat-card"><div class="skeleton" style="width: 40%"></div></div>
        <div class="card stat-card"><div class="skeleton" style="width: 40%"></div></div>
        <div class="card stat-card"><div class="skeleton" style="width: 40%"></div></div>
      </div>
    </div>

    <p v-else-if="error" class="error-text">{{ error }}</p>

    <div v-else-if="stats" class="stack">
      <div class="stats-grid">
        <div class="card stat-card">
          <div class="stat-label">能力分</div>
          <div class="metric">{{ stats.rating }}</div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">做题次数</div>
          <div class="metric">{{ stats.total_attempts }}</div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">独立通过率</div>
          <div class="metric">
            {{ stats.total_attempts ? Math.round(stats.solo_ac_rate * 100) + "%" : "—" }}
          </div>
        </div>
        <div class="card stat-card">
          <div class="stat-label">完成题数</div>
          <div class="metric">{{ stats.completed_problems }}</div>
        </div>
      </div>

      <div class="card coach-card">
        <div class="coach-note" style="margin: 0">{{ stats.message }}</div>
        <div v-if="stats.weak_top_zh.length" class="row weak-row">
          <span class="muted weak-label">薄弱 Top</span>
          <span v-for="tag in stats.weak_top_zh" :key="tag" class="tag peach">{{ tag }}</span>
        </div>
      </div>

      <div class="card skills-card">
        <h3 class="section-title">标签掌握度</h3>
        <div v-if="!stats.skills.length" class="empty-skills">
          <div class="muted">
            暂无已评估标签。完成几道题并提交反馈后，这里才会出现分数——未做过的标签不会显示成 50%。
          </div>
          <RouterLink class="btn secondary empty-cta" to="/">去今日任务</RouterLink>
        </div>
        <div v-for="s in stats.skills" :key="s.tag" class="skill-row">
          <div class="skill-head">
            <strong class="skill-name">{{ s.tag_zh || s.tag }}</strong>
            <span class="muted skill-meta">
              <template v-if="s.attempts > 0">
                {{ s.mastery }} · {{ s.solo_ac }}/{{ s.attempts }} 独立通过
              </template>
              <template v-else>未评估</template>
            </span>
          </div>
          <div class="bar" aria-hidden="true">
            <div
              class="bar-fill"
              :class="{ empty: s.attempts <= 0 }"
              :style="{ width: s.attempts > 0 ? `${s.mastery}%` : '0%' }"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.85rem;
}

.stat-card {
  padding: 1.05rem 1.1rem;
  min-height: 96px;
}

.stat-label {
  color: var(--muted);
  font-size: 0.85rem;
  font-weight: 600;
}

.metric {
  margin-top: 0.4rem;
  font-size: 1.75rem;
  font-weight: 750;
  letter-spacing: -0.03em;
  line-height: 1.1;
  color: var(--text-strong);
}

.coach-card {
  padding: 1rem 1.15rem;
}

.weak-row {
  margin-top: 0.9rem;
  gap: 0.4rem;
}

.weak-label {
  font-size: 0.88rem;
  font-weight: 600;
}

.skills-card {
  padding: 1.15rem 1.2rem;
}

.section-title {
  margin: 0 0 1rem;
  font-size: 1.02rem;
  font-weight: 720;
  letter-spacing: -0.01em;
  color: var(--text-strong);
}

.empty-skills {
  padding: 0.2rem 0 0.4rem;
  display: grid;
  gap: 0.85rem;
  max-width: 48ch;
}

.empty-cta {
  width: fit-content;
}

.skill-row {
  margin-bottom: 1.05rem;
}

.skill-row:last-child {
  margin-bottom: 0;
}

.skill-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.skill-name {
  font-size: 0.96rem;
  color: var(--text-strong);
}

.skill-meta {
  font-size: 0.85rem;
}

.bar {
  margin-top: 0.45rem;
  height: 8px;
  border-radius: 999px;
  background: var(--panel-2);
  border: 1px solid var(--border);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #f59e0b, #22c55e);
  transition: width 0.28s cubic-bezier(0.22, 1, 0.36, 1);
}

.bar-fill.empty {
  background: transparent;
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
