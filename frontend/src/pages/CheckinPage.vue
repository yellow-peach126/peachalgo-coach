<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { api, type CheckinCalendar, type CheckinDay } from "../api/client";

const loading = ref(true);
const error = ref("");
const shareMsg = ref("");
const sharing = ref(false);
const data = ref<CheckinCalendar | null>(null);

const now = new Date();
const viewYear = ref(now.getFullYear());
const viewMonth = ref(now.getMonth() + 1);

const weekLabels = ["一", "二", "三", "四", "五", "六", "日"];

async function load() {
  loading.value = true;
  error.value = "";
  try {
    data.value = await api.checkins({ year: viewYear.value, month: viewMonth.value });
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
  } finally {
    loading.value = false;
  }
}

function shiftMonth(delta: number) {
  let y = viewYear.value;
  let m = viewMonth.value + delta;
  if (m < 1) {
    m = 12;
    y -= 1;
  } else if (m > 12) {
    m = 1;
    y += 1;
  }
  viewYear.value = y;
  viewMonth.value = m;
}

const monthTitle = computed(() => `${viewYear.value} 年 ${viewMonth.value} 月`);

/** Calendar cells: leading blanks (Mon-first) + month days */
const calendarCells = computed(() => {
  const days = data.value?.days || [];
  if (!days.length) return [] as Array<CheckinDay | null>;

  // JS: 0=Sun ... 6=Sat → Mon-first index
  const first = new Date(viewYear.value, viewMonth.value - 1, 1);
  let lead = first.getDay() - 1;
  if (lead < 0) lead = 6;

  const cells: Array<CheckinDay | null> = [];
  for (let i = 0; i < lead; i++) cells.push(null);
  for (const d of days) cells.push(d);
  return cells;
});

function dayNumber(d: CheckinDay) {
  return Number(d.date.slice(8, 10));
}

function pad2(n: number) {
  return String(n).padStart(2, "0");
}

async function shareCard() {
  if (!data.value || sharing.value) return;
  sharing.value = true;
  shareMsg.value = "";
  try {
    const canvas = document.createElement("canvas");
    const w = 720;
    const h = 960;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("无法创建画布");

    // Background
    const bg = ctx.createLinearGradient(0, 0, 0, h);
    bg.addColorStop(0, "#101722");
    bg.addColorStop(0.45, "#0b1016");
    bg.addColorStop(1, "#0b1016");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);

    // Soft glow
    const glow = ctx.createRadialGradient(120, 80, 20, 120, 80, 280);
    glow.addColorStop(0, "rgba(59,130,246,0.18)");
    glow.addColorStop(1, "rgba(59,130,246,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, w, 360);

    const peachGlow = ctx.createRadialGradient(620, 40, 10, 620, 40, 220);
    peachGlow.addColorStop(0, "rgba(245,158,11,0.14)");
    peachGlow.addColorStop(1, "rgba(245,158,11,0)");
    ctx.fillStyle = peachGlow;
    ctx.fillRect(400, 0, 320, 280);

    // Logo mark
    roundRect(ctx, 48, 48, 56, 56, 14);
    const logoGrad = ctx.createLinearGradient(48, 48, 104, 104);
    logoGrad.addColorStop(0, "#f59e0b");
    logoGrad.addColorStop(1, "#f97316");
    ctx.fillStyle = logoGrad;
    ctx.fill();
    ctx.fillStyle = "#1a1205";
    ctx.font = "700 26px Segoe UI, PingFang SC, Microsoft YaHei, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("桃", 76, 77);

    ctx.textAlign = "left";
    ctx.fillStyle = "#e8eef8";
    ctx.font = "700 28px Segoe UI, PingFang SC, Microsoft YaHei, sans-serif";
    ctx.fillText("PeachAlgo Coach", 124, 68);
    ctx.fillStyle = "#9aadc4";
    ctx.font = "500 16px Segoe UI, PingFang SC, Microsoft YaHei, sans-serif";
    ctx.fillText("本地刷题教练 · 打卡海报", 124, 98);

    // Card panel
    roundRect(ctx, 40, 140, w - 80, 720, 20);
    ctx.fillStyle = "#151d2a";
    ctx.fill();
    ctx.strokeStyle = "#273246";
    ctx.lineWidth = 1;
    ctx.stroke();

    // Streak hero
    ctx.fillStyle = "#9aadc4";
    ctx.font = "600 16px Segoe UI, PingFang SC, Microsoft YaHei, sans-serif";
    ctx.fillText("连续打卡", 72, 190);

    ctx.fillStyle = "#f4f7fc";
    ctx.font = "800 72px Segoe UI, PingFang SC, Microsoft YaHei, sans-serif";
    ctx.fillText(String(data.value.current_streak), 72, 270);
    ctx.fillStyle = "#fcd34d";
    ctx.font = "700 28px Segoe UI, PingFang SC, Microsoft YaHei, sans-serif";
    ctx.fillText("天", 72 + ctx.measureText(String(data.value.current_streak)).width + 12, 270);

    // Stats row
    const stats = [
      { label: "历史最长", value: `${data.value.longest_streak} 天` },
      { label: "累计打卡", value: `${data.value.total_checkin_days} 天` },
      {
        label: "本月",
        value: `${data.value.month_checkin_days} 天`,
      },
    ];
    stats.forEach((s, i) => {
      const x = 72 + i * 200;
      ctx.fillStyle = "#6f849d";
      ctx.font = "600 14px Segoe UI, PingFang SC, Microsoft YaHei, sans-serif";
      ctx.fillText(s.label, x, 330);
      ctx.fillStyle = "#e8eef8";
      ctx.font = "700 24px Segoe UI, PingFang SC, Microsoft YaHei, sans-serif";
      ctx.fillText(s.value, x, 364);
    });

    // Mini calendar title
    ctx.fillStyle = "#e8eef8";
    ctx.font = "700 20px Segoe UI, PingFang SC, Microsoft YaHei, sans-serif";
    ctx.fillText(monthTitle.value, 72, 420);

    // Week headers
    const cell = 72;
    const gridX = 84;
    const gridY = 450;
    weekLabels.forEach((lab, i) => {
      ctx.fillStyle = "#6f849d";
      ctx.font = "600 14px Segoe UI, PingFang SC, Microsoft YaHei, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(lab, gridX + i * cell + cell / 2, gridY);
    });

    // Days
    calendarCells.value.forEach((day, idx) => {
      const row = Math.floor(idx / 7);
      const col = idx % 7;
      const cx = gridX + col * cell + cell / 2;
      const cy = gridY + 36 + row * cell + cell / 2;
      if (!day) return;

      if (day.checked) {
        ctx.beginPath();
        ctx.arc(cx, cy, 22, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(34, 197, 94, 0.18)";
        ctx.fill();
        ctx.strokeStyle = "rgba(34, 197, 94, 0.55)";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // check mark
        ctx.strokeStyle = "#22c55e";
        ctx.lineWidth = 3;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.beginPath();
        ctx.moveTo(cx - 8, cy + 1);
        ctx.lineTo(cx - 2, cy + 8);
        ctx.lineTo(cx + 10, cy - 7);
        ctx.stroke();
      } else {
        ctx.fillStyle = day.is_today ? "#93c5fd" : "#6f849d";
        ctx.font = "600 16px Segoe UI, PingFang SC, Microsoft YaHei, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(dayNumber(day)), cx, cy);
      }
    });

    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";

    // Footer
    ctx.fillStyle = "#6f849d";
    ctx.font = "500 14px Segoe UI, PingFang SC, Microsoft YaHei, sans-serif";
    ctx.fillText("提交做题反馈即记为当天打卡 · 数据留在本机", 72, 820);
    ctx.fillStyle = "#9aadc4";
    ctx.font = "600 15px Segoe UI, PingFang SC, Microsoft YaHei, sans-serif";
    const stamp = `${viewYear.value}-${pad2(viewMonth.value)}-${pad2(now.getDate())}`;
    ctx.fillText(stamp, 72, 848);

    // Download
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob((b) => resolve(b), "image/png"),
    );
    if (!blob) throw new Error("生成图片失败");

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `peachalgo-checkin-${viewYear.value}${pad2(viewMonth.value)}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    shareMsg.value = "打卡海报已保存到本地下载目录。";
  } catch (e) {
    shareMsg.value = e instanceof Error ? e.message : "分享失败";
  } finally {
    sharing.value = false;
  }
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

watch([viewYear, viewMonth], load);
onMounted(load);
</script>

<template>
  <section class="checkin">
    <header class="page-header">
      <div>
        <p class="page-kicker">Check-in</p>
        <h1 class="page-title">打卡日历</h1>
        <p class="page-sub">
          {{ data?.message || "加载打卡记录..." }}
        </p>
      </div>
      <div class="page-meta" v-if="data && !loading">
        <span class="tag peach">连续 {{ data.current_streak }} 天</span>
        <span class="tag signal">最长 {{ data.longest_streak }} 天</span>
        <span class="tag">累计 {{ data.total_checkin_days }} 天</span>
        <span class="tag success" v-if="data.checked_today">今日已打卡</span>
        <span class="tag" v-else>今日未打卡</span>
        <button class="btn" type="button" :disabled="sharing" @click="shareCard">
          {{ sharing ? "生成中..." : "分享保存图片" }}
        </button>
      </div>
    </header>

    <div v-if="loading" class="stack">
      <div class="card"><div class="skeleton" style="width: 40%"></div></div>
      <div class="card"><div class="skeleton" style="width: 80%; height: 12rem"></div></div>
    </div>

    <p v-else-if="error" class="error-text">{{ error }}</p>

    <template v-else-if="data">
      <div class="stats-row">
        <div class="card stat">
          <div class="stat-label">连续打卡</div>
          <div class="stat-value accent">{{ data.current_streak }}</div>
          <div class="stat-unit muted">天</div>
        </div>
        <div class="card stat">
          <div class="stat-label">历史最长</div>
          <div class="stat-value">{{ data.longest_streak }}</div>
          <div class="stat-unit muted">天</div>
        </div>
        <div class="card stat">
          <div class="stat-label">累计打卡</div>
          <div class="stat-value">{{ data.total_checkin_days }}</div>
          <div class="stat-unit muted">天</div>
        </div>
        <div class="card stat">
          <div class="stat-label">本月打卡</div>
          <div class="stat-value">{{ data.month_checkin_days }}</div>
          <div class="stat-unit muted">天</div>
        </div>
      </div>

      <div class="card calendar-card">
        <div class="cal-toolbar">
          <button class="btn ghost nav-btn" type="button" @click="shiftMonth(-1)" aria-label="上个月">
            ‹
          </button>
          <h2 class="cal-title">{{ monthTitle }}</h2>
          <button class="btn ghost nav-btn" type="button" @click="shiftMonth(1)" aria-label="下个月">
            ›
          </button>
        </div>

        <div class="week-row" aria-hidden="true">
          <span v-for="w in weekLabels" :key="w" class="week-cell">{{ w }}</span>
        </div>

        <div class="day-grid" role="grid" :aria-label="monthTitle">
          <div
            v-for="(cell, idx) in calendarCells"
            :key="idx"
            class="day-cell"
            :class="{
              empty: !cell,
              checked: cell?.checked,
              today: cell?.is_today,
              future: cell && cell.date > new Date().toISOString().slice(0, 10),
            }"
            role="gridcell"
          >
            <template v-if="cell">
              <span class="day-num">{{ dayNumber(cell) }}</span>
              <span v-if="cell.checked" class="check-mark" aria-label="已打卡">✓</span>
              <span v-else-if="cell.is_today" class="today-dot" aria-label="今天"></span>
            </template>
          </div>
        </div>

        <div class="legend muted">
          <span class="legend-item"><span class="swatch checked"></span>已打卡</span>
          <span class="legend-item"><span class="swatch today"></span>今天</span>
          <span class="legend-item">规则：当天至少提交 1 次做题反馈，即记为打卡</span>
        </div>
      </div>

      <div class="card tip-card">
        <div class="coach-note" style="margin: 0">
          打卡与连续天数来自真实反馈记录，不是单独点一下「签到」。去今日任务做题并提交反馈，日历会自动变绿。
        </div>
        <div class="row tip-actions">
          <RouterLink class="btn" to="/">去今日任务</RouterLink>
          <button class="btn secondary" type="button" :disabled="sharing" @click="shareCard">
            {{ sharing ? "生成中..." : "分享保存图片到本地" }}
          </button>
        </div>
      </div>
    </template>

    <p v-if="shareMsg" class="toast">{{ shareMsg }}</p>
  </section>
</template>

<style scoped>
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.85rem;
  margin-bottom: 1rem;
}

.stat {
  padding: 1rem 1.1rem;
  min-height: 104px;
  position: relative;
}

.stat-label {
  color: var(--muted);
  font-size: 0.85rem;
  font-weight: 600;
}

.stat-value {
  margin-top: 0.35rem;
  font-size: 1.85rem;
  font-weight: 780;
  letter-spacing: -0.03em;
  line-height: 1.1;
  color: var(--text-strong);
}

.stat-value.accent {
  color: #fcd34d;
}

.stat-unit {
  margin-top: 0.15rem;
  font-size: 0.8rem;
}

.calendar-card {
  padding: 1.15rem 1.2rem 1.25rem;
  margin-bottom: 1rem;
}

.cal-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.cal-title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 740;
  letter-spacing: -0.02em;
  color: var(--text-strong);
}

.nav-btn {
  min-width: 2.5rem;
  min-height: 2.5rem;
  padding: 0;
  font-size: 1.35rem;
  line-height: 1;
}

.week-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0.35rem;
  margin-bottom: 0.35rem;
}

.week-cell {
  text-align: center;
  color: var(--muted-2);
  font-size: 0.8rem;
  font-weight: 650;
  padding: 0.25rem 0;
}

.day-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0.4rem;
}

.day-cell {
  aspect-ratio: 1;
  min-height: 52px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.15rem;
  position: relative;
}

.day-cell.empty {
  visibility: hidden;
}

.day-cell:not(.empty) {
  background: var(--panel-2);
  border-color: var(--border);
}

.day-cell.today:not(.checked) {
  border-color: rgba(59, 130, 246, 0.45);
  box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.15);
}

.day-cell.checked {
  background: rgba(34, 197, 94, 0.12);
  border-color: rgba(34, 197, 94, 0.4);
}

.day-cell.future {
  opacity: 0.55;
}

.day-num {
  font-size: 0.92rem;
  font-weight: 650;
  color: var(--muted);
  line-height: 1;
}

.day-cell.checked .day-num {
  color: #86efac;
  font-size: 0.78rem;
}

.day-cell.today .day-num {
  color: #93c5fd;
}

.day-cell.checked.today .day-num {
  color: #bbf7d0;
}

.check-mark {
  width: 1.45rem;
  height: 1.45rem;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: #22c55e;
  color: #052e16;
  font-size: 0.82rem;
  font-weight: 850;
  line-height: 1;
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.25);
}

.today-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: var(--accent);
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem 1.1rem;
  align-items: center;
  margin-top: 1rem;
  padding-top: 0.9rem;
  border-top: 1px solid color-mix(in srgb, var(--border) 80%, transparent);
  font-size: 0.82rem;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.swatch {
  width: 0.85rem;
  height: 0.85rem;
  border-radius: 5px;
  border: 1px solid var(--border);
  display: inline-block;
}

.swatch.checked {
  background: rgba(34, 197, 94, 0.25);
  border-color: rgba(34, 197, 94, 0.5);
}

.swatch.today {
  background: var(--accent-soft);
  border-color: rgba(59, 130, 246, 0.45);
}

.tip-card {
  padding: 1.05rem 1.15rem;
}

.tip-actions {
  margin-top: 0.95rem;
  gap: 0.55rem;
}

.toast {
  margin-top: 0.9rem;
  padding: 0.75rem 0.95rem;
  border-radius: 12px;
  background: rgba(34, 197, 94, 0.08);
  border: 1px solid rgba(34, 197, 94, 0.22);
  color: #bbf7d0;
  font-size: 0.92rem;
}

@media (max-width: 900px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 560px) {
  .stats-row {
    grid-template-columns: 1fr 1fr;
  }

  .day-cell {
    min-height: 44px;
    border-radius: 10px;
  }

  .check-mark {
    width: 1.2rem;
    height: 1.2rem;
    font-size: 0.72rem;
  }
}
</style>
