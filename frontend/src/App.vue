<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from "vue-router";
import { computed, onMounted, ref } from "vue";
import { api } from "./api/client";

const route = useRoute();
const appName = ref("PeachAlgo Coach");
const sourceNote = ref("题库题号来源于 LeetCode / 力扣");
const links = [
  { to: "/", label: "今日任务" },
  { to: "/plan", label: "学习路线" },
  { to: "/checkin", label: "打卡" },
  { to: "/stats", label: "掌握度" },
  { to: "/problems", label: "题库" },
  { to: "/onboarding", label: "设置" },
];

const activePath = computed(() => route.path);

onMounted(async () => {
  try {
    const meta = await api.meta();
    appName.value = meta.app_name;
    sourceNote.value = meta.source_note;
  } catch {
    // keep defaults
  }
});
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <div class="container topbar-inner">
        <RouterLink to="/" class="brand" aria-label="回到今日任务">
          <div class="logo" aria-hidden="true">桃</div>
          <div class="brand-copy">
            <div class="brand-title">{{ appName }}</div>
            <div class="brand-sub">本地刷题教练</div>
          </div>
        </RouterLink>

        <nav class="nav" aria-label="主导航">
          <RouterLink
            v-for="link in links"
            :key="link.to"
            :to="link.to"
            class="nav-link"
            :class="{ active: activePath === link.to }"
          >
            {{ link.label }}
          </RouterLink>
        </nav>
      </div>
    </header>

    <main class="container main">
      <RouterView />
    </main>

    <footer class="footer">
      <div class="container footer-inner">
        <span class="footer-note">{{ sourceNote }}</span>
        <span class="footer-note">数据默认留在本机 · 可在设置中导出</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  border-bottom: 1px solid color-mix(in srgb, var(--border) 85%, transparent);
  background: rgba(11, 16, 22, 0.82);
  backdrop-filter: blur(16px) saturate(1.2);
}

.topbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: var(--header-h);
  padding: 0.7rem 0;
  flex-wrap: wrap;
}

.brand {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  min-width: 0;
}

.logo {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  font-weight: 850;
  font-size: 1.02rem;
  color: var(--logo-ink);
  background: linear-gradient(145deg, #f59e0b 0%, #f97316 100%);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.1) inset,
    0 8px 20px rgba(245, 158, 11, 0.16);
}

.brand-copy {
  min-width: 0;
}

.brand-title {
  font-weight: 750;
  letter-spacing: -0.02em;
  line-height: 1.15;
  color: var(--text-strong);
}

.brand-sub {
  margin-top: 0.12rem;
  color: var(--muted-2);
  font-size: 0.78rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav {
  display: flex;
  gap: 0.2rem;
  flex-wrap: wrap;
  padding: 0.2rem;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid color-mix(in srgb, var(--border) 70%, transparent);
}

.nav-link {
  padding: 0.48rem 0.85rem;
  border-radius: 9px;
  color: var(--muted);
  font-size: 0.9rem;
  font-weight: 600;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}

.nav-link:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.04);
}

.nav-link.active {
  background: var(--panel-2);
  color: var(--text-strong);
  box-shadow: 0 0 0 1px var(--border);
}

.nav-link:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.main {
  flex: 1;
  padding: 1.75rem 0 2.25rem;
}

.footer {
  padding-bottom: 1.35rem;
}

.footer-inner {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding-top: 0.9rem;
  border-top: 1px solid color-mix(in srgb, var(--border) 70%, transparent);
}

.footer-note {
  color: var(--muted-2);
  font-size: 0.8rem;
}

@media (max-width: 760px) {
  .brand-sub {
    display: none;
  }

  .nav {
    width: 100%;
    overflow-x: auto;
    flex-wrap: nowrap;
  }

  .nav-link {
    flex: 0 0 auto;
  }

  .main {
    padding-top: 1.35rem;
  }
}
</style>
