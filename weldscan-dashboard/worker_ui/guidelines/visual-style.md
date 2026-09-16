# Visual Style Guidelines

## Design Vocabulary

Professional, analytical, editorial.
Think institutional research — not product marketing, not AI startup.

---

## Color System

### Background

| Token | Value | Use |
|---|---|---|
| `bg-base` | `#F8F7F4` | Page background (warm off-white, not pure white) |
| `bg-surface` | `#FFFFFF` | Card, panel, table background |
| `bg-subtle` | `#F1F0ED` | Alternate row, secondary section |
| `bg-inverse` | `#1A1A1A` | Dark header, dark sidebar if used |

### Text

| Token | Value | Use |
|---|---|---|
| `text-primary` | `#111111` | Main body text, headings |
| `text-secondary` | `#555555` | Labels, captions, axis text |
| `text-muted` | `#999999` | Metadata, timestamps, footnotes |
| `text-inverse` | `#F8F7F4` | Text on dark backgrounds |

### Borders and Dividers

| Token | Value | Use |
|---|---|---|
| `border-strong` | `#D0CEC9` | Card border, table border |
| `border-subtle` | `#E8E6E1` | Section divider, row separator |

### Semantic / Data Colors

Use these for charts, status indicators, and data encoding only.
Do not use for decoration.

| Token | Value | Use |
|---|---|---|
| `data-blue` | `#2563EB` | Primary data series |
| `data-teal` | `#0D9488` | Secondary data series |
| `data-amber` | `#D97706` | Warning, cautionary trend |
| `data-red` | `#DC2626` | Negative, declining, alert |
| `data-slate` | `#64748B` | Neutral / reference series |
| `data-purple` | `#7C3AED` | Tertiary data series (use sparingly) |

### Accent

| Token | Value | Use |
|---|---|---|
| `accent` | `#1D4ED8` | Active state, selected filter, key link |

**Rule:** Never use accent color for decoration. Only for interactive state or the single most important data point on screen.

---

## Typography

### Font Stack

- **Primary:** `Inter` — body text, labels, UI
- **Data / Numbers:** `JetBrains Mono` or `IBM Plex Mono` — all numeric values in KPI cards, tables, chart annotations
- **Fallback:** `system-ui, -apple-system, sans-serif`

### Type Scale

| Role | Size | Weight | Line Height |
|---|---|---|---|
| Page title | 22px | 600 | 1.2 |
| Section heading | 16px | 600 | 1.3 |
| Subsection label | 13px | 500 | 1.4 |
| Body text | 14px | 400 | 1.6 |
| Caption / footnote | 12px | 400 | 1.5 |
| KPI value | 28–36px | 600 | 1.0 |
| KPI label | 11px | 500 uppercase | 1.2 |
| Table cell | 13px | 400 | 1.5 |
| Monospace number | 13–14px | 400 | 1.4 |

### Typography Rules

- Headings: never decorative, always descriptive of the content below
- Numbers: always monospaced, right-aligned in tables
- Labels: uppercase only for KPI labels (max 2–3 words), never for body text
- Do not use font size alone to create hierarchy — use weight and color together

---

## Border and Radius

- Cards and panels: `border-radius: 4px` (subtle, not pill-shaped)
- Inputs and filters: `border-radius: 4px`
- Badges and tags: `border-radius: 3px`
- Buttons: `border-radius: 4px`
- Never use `border-radius: 12px` or higher on data-facing components
- Tables have no border-radius

---

## Shadow

- Cards: `box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)`
- Dropdowns / popovers: `box-shadow: 0 4px 12px rgba(0,0,0,0.10)`
- No neumorphism, no glow effects, no colored shadows

---

## Overall Tone

- Warm off-white background (not cold pure white)
- Restrained use of color (mostly text-primary and text-secondary)
- Color appears in charts and data, not in chrome
- Border-defined structure, not shadow-heavy depth
- No gradient backgrounds, no glass effects, no blur backdrops
