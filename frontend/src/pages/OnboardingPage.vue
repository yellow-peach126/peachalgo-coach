<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { api, type Meta, type OnboardingPayload, type Profile } from "../api/client";
import { setOnboardedCache } from "../router";

const router = useRouter();
const loading = ref(false);
const error = ref("");
const dataMsg = ref("");
const meta = ref<Meta | null>(null);
const profile = ref<Profile | null>(null);
const exporting = ref(false);
const importing = ref(false);
const resetting = ref(false);

const form = reactive<OnboardingPayload>({
  language: "python",
  level: "easy",
  goal: "campus",
  daily_minutes: 60,
  horizon_days: 60,
  weak_tags: [],
});

const alreadyOnboarded = computed(() => !!profile.value?.onboarded);

function toggleTag(tag: string) {
  if (form.weak_tags.includes(tag)) {
    form.weak_tags = form.weak_tags.filter((t) => t !== tag);
  } else {
    form.weak_tags.push(tag);
  }
}

const selectedLevel = () => meta.value?.levels.find((l) => l.id === form.level);

function applyProfile(p: Profile) {
  form.language = p.language as OnboardingPayload["language"];
  form.level = p.level as OnboardingPayload["level"];
  form.goal = p.goal as OnboardingPayload["goal"];
  form.daily_minutes = p.daily_minutes;
  form.horizon_days = p.horizon_days;
  form.weak_tags = [...(p.weak_tags || [])];
}

async function submit() {
  loading.value = true;
  error.value = "";
  try {
    const p = await api.onboarding(form);
    profile.value = p;
    setOnboardedCache(true);
    await router.push("/");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "提交失败";
  } finally {
    loading.value = false;
  }
}

async function exportLocal() {
  exporting.value = true;
  dataMsg.value = "";
  try {
    const data = await api.exportData();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const stamp = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `peachalgo-backup-${stamp}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    dataMsg.value = "备份已保存到本地下载目录。";
  } catch (e) {
    dataMsg.value = e instanceof Error ? e.message : "导出失败";
  } finally {
    exporting.value = false;
  }
}

function pickImportFile() {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "application/json,.json";
  input.onchange = async () => {
    const file = input.files?.[0];
    if (!file) return;
    importing.value = true;
    dataMsg.value = "";
    try {
      const text = await file.text();
      const json = JSON.parse(text) as Record<string, unknown>;
      const res = await api.importData(json);
      dataMsg.value = res.message;
      const p = await api.profile();
      profile.value = p;
      setOnboardedCache(!!p.onboarded);
      if (p.onboarded) applyProfile(p);
    } catch (e) {
      dataMsg.value = e instanceof Error ? e.message : "导入失败";
    } finally {
      importing.value = false;
    }
  };
  input.click();
}

async function clearLocal() {
  const ok = window.confirm(
    "确定清空本机全部学习数据？\n包括反馈、计划、掌握度与复习卡片。此操作不可撤销，请先导出备份。",
  );
  if (!ok) return;
  const ok2 = window.confirm("再次确认：真的要清空吗？");
  if (!ok2) return;
  resetting.value = true;
  dataMsg.value = "";
  try {
    const res = await api.resetData();
    dataMsg.value = res.message;
    setOnboardedCache(false);
    profile.value = await api.profile();
    form.language = "python";
    form.level = "easy";
    form.goal = "campus";
    form.daily_minutes = 60;
    form.horizon_days = 60;
    form.weak_tags = [];
  } catch (e) {
    dataMsg.value = e instanceof Error ? e.message : "清空失败";
  } finally {
    resetting.value = false;
  }
}

onMounted(async () => {
  try {
    const [m, p] = await Promise.all([api.meta(), api.profile()]);
    meta.value = m;
    profile.value = p;
    if (p.onboarded) {
      applyProfile(p);
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载配置失败";
  }
});
</script>

<template>
  <section class="onboarding">
    <header class="page-header">
      <div>
        <p class="page-kicker">{{ alreadyOnboarded ? "Settings" : "Setup" }}</p>
        <h1 class="page-title">
          {{ alreadyOnboarded ? "学习设置" : "欢迎使用 PeachAlgo Coach" }}
        </h1>
        <p class="page-sub">
          <template v-if="alreadyOnboarded">
            修改语言、水平或目标后可重新生成路线。重新生成会覆盖当前未完成计划。数据默认留在本机，可随时导出备份。
          </template>
          <template v-else>
            先告诉教练你的语言、水平、目标与每日时间——我们会生成可本地运行的学习路线。
          </template>
        </p>
      </div>
    </header>

    <div class="coach-note intro-note">
      {{ meta?.source_note || "题库题号来源于 LeetCode / 力扣（仅免费题元数据）。" }}
      这不是 OJ：做题在力扣，计划与反馈留在本机。
    </div>

    <div v-if="alreadyOnboarded && profile" class="card current-card">
      <div class="current-row">
        <div>
          <div class="current-label">当前配置</div>
          <div class="current-value muted">
            {{ profile.language_label }} · {{ profile.level_label }} · {{ profile.goal_label }} ·
            每天 {{ profile.daily_minutes }} 分钟 · {{ profile.horizon_days }} 天
          </div>
        </div>
        <RouterLink class="btn ghost" to="/">返回今日任务</RouterLink>
      </div>
    </div>

    <div class="card form-card">
      <div class="form-grid">
        <div class="field">
          <label for="language">主攻语言</label>
          <select id="language" v-model="form.language">
            <option v-for="lang in meta?.languages || []" :key="lang.id" :value="lang.id">
              {{ lang.label }}
            </option>
          </select>
          <div class="field-hint">
            算法题库共用；语言用于模板偏好与展示。选择 MySQL 时会更偏向数据库题。
          </div>
        </div>

        <div class="field">
          <label for="level">当前水平</label>
          <select id="level" v-model="form.level">
            <option v-for="lv in meta?.levels || []" :key="lv.id" :value="lv.id">
              {{ lv.label }}
            </option>
          </select>
          <div class="criteria" v-if="selectedLevel()">
            <strong>这一档意味着：</strong>{{ selectedLevel()?.criteria }}
          </div>
        </div>

        <div class="field">
          <label for="goal">目标</label>
          <select id="goal" v-model="form.goal">
            <option v-for="g in meta?.goals || []" :key="g.id" :value="g.id">
              {{ g.label }}
            </option>
          </select>
          <div class="field-hint">
            {{ meta?.goals.find((g) => g.id === form.goal)?.desc || "" }}
          </div>
        </div>

        <div class="field-row">
          <div class="field">
            <label for="minutes">每天可投入（分钟）</label>
            <select id="minutes" v-model.number="form.daily_minutes">
              <option :value="30">30</option>
              <option :value="60">60</option>
              <option :value="90">90</option>
              <option :value="120">120</option>
            </select>
          </div>

          <div class="field">
            <label for="horizon">计划周期（天）</label>
            <select id="horizon" v-model.number="form.horizon_days">
              <option :value="30">30</option>
              <option :value="60">60</option>
              <option :value="90">90</option>
            </select>
          </div>
        </div>
      </div>

      <div class="field">
        <label>薄弱项（可选）</label>
        <div class="chip-row">
          <button
            v-for="tag in (meta?.tags || []).slice(0, 18)"
            :key="tag.id"
            type="button"
            class="chip"
            :class="{ on: form.weak_tags.includes(tag.id) }"
            @click="toggleTag(tag.id)"
          >
            {{ tag.label }}
          </button>
        </div>
      </div>

      <div class="catalog muted" v-if="meta">
        当前免费题库：{{ meta.catalog.total }} 题（简单 {{ meta.catalog.easy }} /
        中等 {{ meta.catalog.medium }} / 困难 {{ meta.catalog.hard }}），已排除 Plus 会员专享题。
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>

      <div class="row actions">
        <button class="btn" :disabled="loading || !meta" @click="submit">
          {{
            loading
              ? "正在生成路线..."
              : alreadyOnboarded
                ? "重新生成学习路线"
                : "完成设置并生成学习路线"
          }}
        </button>
        <RouterLink v-if="alreadyOnboarded" class="btn ghost" to="/">取消</RouterLink>
      </div>
    </div>

    <div class="card data-card">
      <div class="current-label">本机数据</div>
      <p class="data-desc muted">
        计划、反馈、掌握度与打卡都存在你这台机器上。导出可备份；导入可恢复；清空会删除学习记录并要求重新设置。
      </p>
      <div class="row data-actions">
        <button class="btn secondary" type="button" :disabled="exporting" @click="exportLocal">
          {{ exporting ? "导出中..." : "导出备份 JSON" }}
        </button>
        <button class="btn secondary" type="button" :disabled="importing" @click="pickImportFile">
          {{ importing ? "导入中..." : "从备份恢复" }}
        </button>
        <button class="btn danger-ghost" type="button" :disabled="resetting" @click="clearLocal">
          {{ resetting ? "清空中..." : "清空本机数据" }}
        </button>
      </div>
      <p v-if="dataMsg" class="data-msg">{{ dataMsg }}</p>
    </div>
  </section>
</template>

<style scoped>
.intro-note {
  max-width: 760px;
  margin-bottom: 1rem;
}

.current-card {
  max-width: 760px;
  margin-bottom: 1rem;
}

.current-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.current-label {
  font-weight: 700;
  margin-bottom: 0.25rem;
  color: var(--text-strong);
}

.current-value {
  font-size: 0.92rem;
  line-height: 1.45;
}

.form-card {
  max-width: 760px;
}

.form-grid {
  display: grid;
  gap: 0.1rem;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.criteria {
  margin-top: 0.2rem;
  padding: 0.8rem 0.95rem;
  border-radius: 12px;
  background: var(--peach-soft);
  border: 1px solid var(--peach-border);
  color: #fde68a;
  font-size: 0.92rem;
  line-height: 1.5;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.chip {
  border: 1px solid var(--border);
  background: transparent;
  color: var(--muted);
  border-radius: 999px;
  padding: 0.42rem 0.8rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.88rem;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    color 0.15s ease;
}

.chip:hover {
  border-color: var(--border-strong);
  color: var(--text);
}

.chip.on {
  border-color: var(--peach-border);
  background: var(--peach-soft);
  color: #fcd34d;
}

.chip:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.catalog {
  margin: 0.2rem 0 1rem;
  font-size: 0.88rem;
  color: var(--muted-2);
}

.actions {
  margin-top: 0.15rem;
}

.data-card {
  max-width: 760px;
  margin-top: 1rem;
}

.data-desc {
  margin: 0.35rem 0 0.9rem;
  font-size: 0.9rem;
  line-height: 1.5;
  max-width: 54ch;
}

.data-actions {
  gap: 0.55rem;
}

.data-msg {
  margin: 0.85rem 0 0;
  padding: 0.7rem 0.85rem;
  border-radius: 12px;
  background: rgba(34, 197, 94, 0.08);
  border: 1px solid rgba(34, 197, 94, 0.2);
  color: #bbf7d0;
  font-size: 0.9rem;
}

@media (max-width: 640px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>
