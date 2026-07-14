import { createRouter, createWebHistory } from "vue-router";
import { api } from "./api/client";
import TodayPage from "./pages/TodayPage.vue";
import OnboardingPage from "./pages/OnboardingPage.vue";
import PlanPage from "./pages/PlanPage.vue";
import StatsPage from "./pages/StatsPage.vue";
import ProblemsPage from "./pages/ProblemsPage.vue";
import CheckinPage from "./pages/CheckinPage.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "today", component: TodayPage, meta: { requiresOnboarding: true } },
    { path: "/onboarding", name: "onboarding", component: OnboardingPage },
    { path: "/plan", name: "plan", component: PlanPage, meta: { requiresOnboarding: true } },
    { path: "/checkin", name: "checkin", component: CheckinPage, meta: { requiresOnboarding: true } },
    { path: "/stats", name: "stats", component: StatsPage, meta: { requiresOnboarding: true } },
    { path: "/problems", name: "problems", component: ProblemsPage, meta: { requiresOnboarding: true } },
  ],
});

let cachedOnboarded: boolean | null = null;

export function setOnboardedCache(value: boolean) {
  cachedOnboarded = value;
}

router.beforeEach(async (to) => {
  if (!to.meta.requiresOnboarding) return true;
  try {
    if (cachedOnboarded === null) {
      const profile = await api.profile();
      cachedOnboarded = profile.onboarded;
    }
    if (!cachedOnboarded) {
      return { name: "onboarding" };
    }
  } catch {
    return { name: "onboarding" };
  }
  return true;
});
