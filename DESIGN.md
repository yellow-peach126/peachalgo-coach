---
name: PeachAlgo Coach
description: Local-first feedback-driven practice coach UI — calm dark study desk, signal actions, peach brand mark
colors:
  night-desk: "#0f1419"
  ink-panel: "#1a2332"
  ink-panel-2: "#243044"
  ink-border: "#2d3a4f"
  text-ink: "#e7eef8"
  text-muted: "#9fb0c7"
  signal-blue: "#3b82f6"
  success-green: "#22c55e"
  peach-amber: "#f59e0b"
  peach-orange: "#f97316"
  danger-red: "#ef4444"
  easy-green: "#4ade80"
  medium-gold: "#fbbf24"
  hard-coral: "#f87171"
  logo-ink: "#1a1205"
typography:
  title:
    fontFamily: "Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "1.6rem"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "0.9rem"
    fontWeight: 400
    lineHeight: 1.4
  tag:
    fontFamily: "Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 400
    lineHeight: 1.2
rounded:
  sm: "10px"
  md: "12px"
  lg: "14px"
  pill: "999px"
spacing:
  xs: "0.25rem"
  sm: "0.4rem"
  md: "0.75rem"
  lg: "1.25rem"
  xl: "1.5rem"
components:
  button-primary:
    backgroundColor: "{colors.signal-blue}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "0.55rem 1rem"
  button-secondary:
    backgroundColor: "{colors.ink-panel-2}"
    textColor: "{colors.text-ink}"
    rounded: "{rounded.sm}"
    padding: "0.55rem 1rem"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text-ink}"
    rounded: "{rounded.sm}"
    padding: "0.55rem 1rem"
  card:
    backgroundColor: "{colors.ink-panel}"
    textColor: "{colors.text-ink}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  tag:
    backgroundColor: "{colors.ink-panel-2}"
    textColor: "{colors.text-muted}"
    rounded: "{rounded.pill}"
    padding: "0.15rem 0.55rem"
  field-control:
    backgroundColor: "{colors.ink-panel-2}"
    textColor: "{colors.text-ink}"
    rounded: "{rounded.sm}"
    padding: "0.65rem 0.75rem"
  nav-link-active:
    backgroundColor: "{colors.ink-panel-2}"
    textColor: "{colors.text-ink}"
    rounded: "{rounded.pill}"
    padding: "0.45rem 0.8rem"
  brand-logo:
    backgroundColor: "{colors.peach-amber}"
    textColor: "{colors.logo-ink}"
    rounded: "{rounded.md}"
    size: "40px"
---

# Design System: PeachAlgo Coach

## 1. Overview

**Creative North Star: "The Study Desk Coach"**

This is the visual system of a quiet coach sitting beside a late-night study desk. The surface is dark and cool so attention stays on today’s tasks, not chrome. Hierarchy is spare: page title, short coach message, finishable task cards, one clear primary action. Personality is calm, restrained, coach-like—never gamified, never SaaS-dashboard theater, never a LeetCode skin.

Depth comes mostly from tonal steps (Night Desk → Ink Panel → Ink Panel 2), with a light ambient lift on cards. Brand warmth is concentrated in the peach logo mark and selective amber hover accents; body UI stays cool slate + Signal Blue so long sessions remain readable.

**Key Characteristics:**
- Dark cool study surface with restrained blue action
- Peach amber as brand spark, not full-screen theme
- Quiet, finishable components: primary / secondary / ghost
- Explainable task cards over hero metrics
- Chinese + Latin UI stack (Segoe UI / PingFang SC / Microsoft YaHei)

## 2. Colors

Cool night neutrals with one operational blue, semantic greens/reds/ambers, and a peach brand mark. Chroma is low on surfaces; accent rarity is intentional.

### Primary
- **Signal Blue** (`#3b82f6` / `--accent`): Primary buttons and the main “do this now” path (start problem, save feedback, generate plan). Use sparingly so it remains the coach’s pointer finger.

### Secondary
- **Success Green** (`#22c55e` / `--accent-2`): Positive completion / mastery signals. Not a second CTA color.
- **Peach Amber** (`#f59e0b` → `#f97316`): Brand mark gradient and selective hover accents (e.g. problem-card border on hover). Warmth lives here, not in the body background.

### Tertiary
- **Easy Green** (`#4ade80`), **Medium Gold** (`#fbbf24`), **Hard Coral** (`#f87171`): Difficulty tags only. Never repurpose as primary brand colors.
- **Danger Red** (`#ef4444` / `--danger`): Destructive or hard-fail states; error copy may use a lighter coral for contrast on dark panels.

### Neutral
- **Night Desk** (`#0f1419` / `--bg`): Page canvas; radial wash from `#1a2740` into Night Desk.
- **Ink Panel** (`#1a2332` / `--panel`): Card / modal surfaces (often slightly darkened via `color-mix`).
- **Ink Panel 2** (`#243044` / `--panel-2`): Nested controls, secondary buttons, tag fills, active nav chips.
- **Ink Border** (`#2d3a4f` / `--border`): 1px structural borders.
- **Text Ink** (`#e7eef8` / `--text`): Primary readable text.
- **Text Muted** (`#9fb0c7` / `--muted`): Supporting copy, labels, reasons—keep contrast usable on panels; do not fade further for “elegance.”

### Named Rules
**The One Signal Rule.** Signal Blue is the primary action color and stays rare. Screens should not become blue walls.

**The Peach Spark Rule.** Peach amber marks identity (logo, occasional hover). It is not the body theme and must not turn the app into warm cream or neon orange.

**The Cool Desk Rule.** Body background stays cool dark slate. Warmth is carried by the brand mark and selective accents—not by sand/cream/paper surfaces.

## 3. Typography

**Display Font:** Segoe UI with PingFang SC / Microsoft YaHei for CJK  
**Body Font:** Same stack (single family system)  
**Label/Mono Font:** Same stack at smaller sizes; no dedicated mono yet

**Character:** System-native, bilingual-first, low drama. Weight does hierarchy; display typefaces and tracking gimmicks are out of scope for the MVP coach UI.

### Hierarchy
- **Title** (700, `1.6rem`, tight page lead): `.page-title` — one job name per screen (“今日任务”).
- **Body** (400, `1rem`, line-height `1.5`): Default UI copy; keep lines readable, not marketing-long.
- **Label** (400, `0.9rem`, muted): Field labels and secondary meta.
- **Tag** (400, `0.8rem`): Chips for difficulty, streak, budget, algorithm tags.
- **Brand title** (700, default size): Header product name; subtitle at ~`0.85rem` muted.

### Named Rules
**The One Voice Type Rule.** One sans stack across the app. Do not pair a second similar geometric sans or introduce display serifs for “premium.”

**The Coach Caption Rule.** Recommendation reasons and helper text stay muted but legible—never light-gray-on-tinted illegibility.

## 4. Elevation

Hybrid: tonal layering first, light ambient lift second. Surfaces step Night Desk → Ink Panel → Ink Panel 2. Cards use a soft shadow and 1px border; they do not float as heavy material sheets. Sticky header uses translucent Night Desk + `backdrop-filter: blur(10px)`.

### Shadow Vocabulary
- **Card lift** (`box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2)`): Resting elevation for `.card` / modals.
- **Modal veil** (`background: rgba(0, 0, 0, 0.55)`): Fixed mask behind feedback dialogs.
- **Header glass**: `rgba(15, 20, 25, 0.75)` + blur — sticky orientation, not a second brand surface.

### Named Rules
**The Light Lift Rule.** Shadows stay soft and dark-session friendly. If it looks like a 2014 elevated card or a neon glow, the shadow is wrong.

**The Border Is Structure Rule.** 1px Ink Border defines containment. Colored left-side accent stripes are forbidden.

## 5. Components

Quiet and finishable. Primary path obvious; secondary and ghost available without visual noise.

### Buttons
- **Shape:** Gently rounded controls (`10px`)
- **Primary:** Signal Blue fill, white text, semibold — “去力扣做题”, “保存并调整计划”
- **Secondary:** Ink Panel 2 fill + Ink Border — supporting actions (“提交反馈”, “从题库添加”)
- **Ghost:** Transparent + border — skip / cancel / tertiary navigation
- **Disabled:** `opacity: 0.5`, not-allowed cursor
- **Hover / Focus:** Prefer border or background step changes; problem cards may take Peach Amber border on hover. Always provide a visible focus treatment for keyboard users.

### Chips / Tags
- **Style:** Pill (`999px`), Ink Panel 2 fill, Ink Border, muted text
- **Semantic:** `.easy` / `.medium` / `.hard` recolor text only (Easy Green / Medium Gold / Hard Coral)
- **Use:** Streak, budget, est. minutes, item type, algorithm tags—metadata, not CTAs

### Cards / Containers
- **Corner Style:** `14px` (`--radius`)
- **Background:** Darkened Ink Panel
- **Border:** 1px Ink Border
- **Shadow Strategy:** Card lift (see Elevation)
- **Internal Padding:** ~`1.25rem`
- **Pattern:** Task cards stack with `0.75rem` gap; empty states are a single card with clear next links—not illustration spam

### Inputs / Fields
- **Style:** Grid label + control; control uses Ink Panel 2, Ink Border, `10px` radius, `0.65rem 0.75rem` padding
- **Label:** `0.9rem` muted
- **Focus:** Keep high-contrast border/ring; avoid novelty glows
- **Error / Disabled:** Error text may use light coral on dark; disabled follows button opacity language

### Navigation
- **Top bar:** Sticky glass header, brand mark + product title left, pill links right
- **Logo:** 40×40, `12px` radius, peach amber → orange gradient, dark logo ink “桃”
- **Links:** Muted by default; active/hover = Ink Panel 2 chip + Text Ink
- **Layout width:** Content `min(1100px, 100% - 2rem)` centered

### Signature: Problem task card
Primary object of the product. Shows number + title, difficulty chip, type chip, estimate, **visible recommendation reason**, tag row, then actions: primary outbound to LeetCode, secondary feedback, ghost reschedule. Coach over catalog: reason is not optional decoration.

### Signature: Feedback modal
Centered card on dark veil (`z-index` ~50). Collects result, felt difficulty, minutes, optional note. Primary submit copy should reinforce plan adjustment (“保存并调整计划”).

## 6. Do's and Don'ts

### Do:
- **Do** lead screens with today’s coach job (title + short message + finishable tasks).
- **Do** keep Signal Blue for the primary action path only.
- **Do** show recommendation reasons on task cards in muted-but-readable type.
- **Do** preserve peach amber as a brand spark (logo / selective hover), not a page wash.
- **Do** honor WCAG AA contrast and `prefers-reduced-motion` for any motion you add.
- **Do** keep daily UI calm enough for 30–120 minute study blocks.

### Don't:
- **Don't** ship generic SaaS dashboard templates: hero metrics, identical icon+heading card grids, KPI theater.
- **Don't** use gamification medal spam: badges, leaderboards, confetti that distract from practice.
- **Don't** clone LeetCode / 力扣 visual language—this is a coach shell, not another problem browser.
- **Don't** use neon cyber-hacker aesthetics (fluorescent terminal stacks that look sharp and read poorly).
- **Don't** use side-stripe borders (`border-left` / `border-right` > 1px) as accent decoration.
- **Don't** use gradient text (`background-clip: text`) or decorative glassmorphism as default chrome.
- **Don't** warm the body into cream/sand/paper; the Cool Desk Rule holds.
- **Don't** bury feedback—submitting result / difficulty / time is the product, not a hidden form.
