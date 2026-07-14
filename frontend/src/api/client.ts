export type Language =
  | "python"
  | "java"
  | "cpp"
  | "c"
  | "csharp"
  | "go"
  | "javascript"
  | "typescript"
  | "mysql"
  | "rust"
  | "kotlin"
  | "swift"
  | "php"
  | "ruby";
export type Level = "beginner" | "easy" | "medium" | "advanced";
export type Goal = "campus" | "social" | "foundation" | "contest" | "database";

export interface Problem {
  id: string;
  number: number;
  frontend_id: string;
  title: string;
  title_zh?: string | null;
  difficulty: string;
  difficulty_zh: string;
  tags: string[];
  tags_zh: string[];
  est_minutes: number;
  is_template: boolean;
  stage: string;
  stage_zh: string;
  url: string;
  url_en?: string | null;
  priority: number;
  paid_only?: boolean;
  source?: string;
  completed?: boolean;
  completed_result?: string | null;
  completed_result_zh?: string;
  completed_at?: string | null;
  in_today?: boolean;
  today_plan_item_id?: number | null;
  /** main | review | weak | custom */
  today_item_type?: string | null;
  /** Only bank-added custom items can be withdrawn from the catalog. */
  can_withdraw_today?: boolean;
}

export interface TodayItem {
  plan_item_id: number;
  problem: Problem;
  item_type: string;
  item_type_zh: string;
  status: string;
  status_zh: string;
  reason: string;
  scheduled_date: string;
}

export interface TodayDoneItem {
  attempt_id: number;
  plan_item_id?: number | null;
  problem: Problem;
  result: string;
  result_zh: string;
  felt_difficulty: string;
  felt_difficulty_zh: string;
  minutes_spent: number;
  created_at: string;
  can_undo: boolean;
}

export interface TodayResponse {
  date: string;
  onboarded: boolean;
  daily_minutes: number;
  items: TodayItem[];
  done_items: TodayDoneItem[];
  total_est_minutes: number;
  remaining_est_minutes: number;
  spent_minutes: number;
  streak_days: number;
  message: string;
  source_note: string;
}

export interface Profile {
  id: string;
  language: string;
  language_label: string;
  level: string;
  level_label: string;
  level_criteria: string;
  goal: string;
  goal_label: string;
  daily_minutes: number;
  horizon_days: number;
  weak_tags: string[];
  weak_tags_zh: string[];
  rating: number;
  onboarded: boolean;
}

export interface OnboardingPayload {
  language: Language;
  level: Level;
  goal: Goal;
  daily_minutes: number;
  horizon_days: number;
  weak_tags: string[];
}

export interface AttemptPayload {
  problem_id: string;
  result: "solved_solo" | "solved_hint" | "solved_solution" | "failed";
  felt_difficulty: "too_easy" | "ok" | "hard" | "very_hard";
  minutes_spent: number;
  note?: string;
  plan_item_id?: number;
}

export interface FeedbackChangeItem {
  kind: string;
  label: string;
  detail: string;
}

export interface FeedbackSummary {
  rating_before: number;
  rating_after: number;
  rating_delta: number;
  mastery_before: Record<string, number>;
  mastery_after: Record<string, number>;
  changes: FeedbackChangeItem[];
  checked_today: boolean;
  current_streak: number;
  review_scheduled: boolean;
}

export interface AttemptResult {
  id: number;
  problem_id: string;
  plan_item_id?: number | null;
  result: string;
  felt_difficulty: string;
  minutes_spent: number;
  performance: number;
  created_at: string;
  mastery_updates: Record<string, number>;
  summary?: FeedbackSummary | null;
  message: string;
}

export interface UndoAttemptResult {
  attempt_id: number;
  problem_id: string;
  restored_plan_item_id?: number | null;
  mastery_updates?: Record<string, number>;
  summary?: FeedbackSummary | null;
  message: string;
}

export interface Stats {
  rating: number;
  total_attempts: number;
  solo_ac_rate: number;
  completed_problems: number;
  skills: Array<{
    tag: string;
    tag_zh: string;
    mastery: number;
    attempts: number;
    solo_ac: number;
  }>;
  weak_top: string[];
  weak_top_zh: string[];
  message: string;
}

export interface CheckinDay {
  date: string;
  checked: boolean;
  attempts: number;
  minutes_spent: number;
  is_today: boolean;
}

export interface CheckinCalendar {
  year: number;
  month: number;
  days: CheckinDay[];
  checked_dates: string[];
  current_streak: number;
  longest_streak: number;
  total_checkin_days: number;
  month_checkin_days: number;
  checked_today: boolean;
  message: string;
}

export interface PlanItem {
  id: number;
  problem_id: string;
  title: string;
  title_zh?: string | null;
  difficulty: string;
  difficulty_zh: string;
  scheduled_date: string;
  item_type: string;
  item_type_zh: string;
  status: string;
  status_zh: string;
  reason: string;
  stage: string;
  stage_zh: string;
  url: string;
  tags_zh: string[];
}

export interface Plan {
  id: number;
  status: string;
  start_date: string;
  horizon_days: number;
  total_items: number;
  done_items: number;
  items: PlanItem[];
}

export interface Meta {
  app_name: string;
  source_note: string;
  languages: Array<{ id: string; label: string }>;
  levels: Array<{ id: string; label: string; criteria: string }>;
  goals: Array<{ id: string; label: string; desc?: string }>;
  stages: Array<{ id: string; title: string }>;
  tags: Array<{ id: string; label: string }>;
  difficulties: Array<{ id: string; label: string }>;
  catalog: {
    total: number;
    easy: number;
    medium: number;
    hard: number;
    note: string;
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; app: string; problems_loaded: number }>("/api/health"),
  meta: () => request<Meta>("/api/meta"),
  profile: () => request<Profile>("/api/profile"),
  onboarding: (payload: OnboardingPayload) =>
    request<Profile>("/api/onboarding", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  today: () => request<TodayResponse>("/api/today"),
  attempt: (payload: AttemptPayload) =>
    request<AttemptResult>("/api/attempts", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  undoAttempt: (attempt_id: number) =>
    request<UndoAttemptResult>(`/api/attempts/${attempt_id}/undo`, {
      method: "POST",
    }),
  skip: (plan_item_id: number) =>
    request<PlanItem>("/api/today/skip", {
      method: "POST",
      body: JSON.stringify({ plan_item_id }),
    }),
  addToday: (problem_ids: string[]) =>
    request<{
      items: PlanItem[];
      added: number;
      skipped_existing: number;
      skipped_invalid: number;
      message: string;
    }>("/api/today/add", {
      method: "POST",
      body: JSON.stringify({ problem_ids }),
    }),
  removeToday: (payload: { problem_ids?: string[]; plan_item_ids?: number[] }) =>
    request<{ removed: number; skipped: number; message: string }>("/api/today/remove", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  plan: () => request<Plan>("/api/plan"),
  stats: () => request<Stats>("/api/stats"),
  exportData: () => request<Record<string, unknown>>("/api/export"),
  importData: (payload: Record<string, unknown>) =>
    request<{ ok: boolean; restored_attempts: number; restored_plan_items: number; message: string }>(
      "/api/import",
      { method: "POST", body: JSON.stringify(payload) },
    ),
  resetData: () =>
    request<{ ok: boolean; cleared: Record<string, number>; message: string }>("/api/reset", {
      method: "POST",
    }),
  checkins: (params?: { year?: number; month?: number }) => {
    const qs = new URLSearchParams();
    if (params?.year) qs.set("year", String(params.year));
    if (params?.month) qs.set("month", String(params.month));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<CheckinCalendar>(`/api/checkins${suffix}`);
  },
  problems: (params?: {
    tag?: string;
    difficulty?: string;
    stage?: string;
    q?: string;
    limit?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.tag) qs.set("tag", params.tag);
    if (params?.difficulty) qs.set("difficulty", params.difficulty);
    if (params?.stage) qs.set("stage", params.stage);
    if (params?.q) qs.set("q", params.q);
    if (params?.limit) qs.set("limit", String(params.limit));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<Problem[]>(`/api/problems${suffix}`);
  },
};
