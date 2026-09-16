# Layout Guidelines

## Core Layout Model

Use a fixed-width, content-centered layout with optional sidebar.
Do not use full-bleed layouts with components floating at arbitrary widths.

---

## Page Structure

### Option A — Full-width report (default for research dashboards)

```
┌─────────────────────────────────────────────────────────┐
│  Page Header (title, period, source)                    │
├─────────────────────────────────────────────────────────┤
│  Summary / Key Findings strip                           │
├─────────────────────────────────────────────────────────┤
│  Main content area (charts, tables, text)               │
│                                                         │
│  [Chart]              [Chart]                           │
│  [Table]                                                │
│  [Text analysis]      [Supporting chart]                │
├─────────────────────────────────────────────────────────┤
│  Footnotes / Data sources                               │
└─────────────────────────────────────────────────────────┘
```

### Option B — Sidebar dashboard

```
┌──────────┬──────────────────────────────────────────────┐
│ Sidebar  │ Content area                                 │
│ (240px)  │                                              │
│          │ [KPI row]                                    │
│ Nav      │ [Main chart]                                 │
│ Filters  │ [Secondary charts / table]                   │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

---

## Grid System

- Base grid: 12 columns
- Gutter: 24px
- Outer margin: 40px (desktop), 24px (tablet), 16px (mobile)
- Max content width: 1280px centered

### Common column splits

| Use | Columns |
|---|---|
| Full-width chart or table | 12 |
| Two equal charts | 6 / 6 |
| Main chart + supporting | 8 / 4 |
| Three summary stats | 4 / 4 / 4 |
| KPI row (four items) | 3 / 3 / 3 / 3 |
| Wide table + narrow notes | 9 / 3 |

---

## Spacing Scale

Use this scale consistently. Do not use arbitrary pixel values.

| Token | Value | Use |
|---|---|---|
| `space-1` | 4px | Inline gap (icon–label, badge padding) |
| `space-2` | 8px | Tight row spacing, small label gap |
| `space-3` | 12px | List item spacing, compact card padding |
| `space-4` | 16px | Standard card padding, form row gap |
| `space-5` | 24px | Between components within a section |
| `space-6` | 32px | Between sections |
| `space-7` | 48px | Between major page sections |
| `space-8` | 64px | Page-level vertical separation |

---

## Section Structure

Every section follows this order:

1. Section heading (16px, 600 weight)
2. Optional: 1–2 line description or context note
3. Content (chart, table, or text)
4. Optional: footnote or data source label

Sections are separated by `space-7` (48px) vertically.
Do not separate sections with full-width decorative dividers or colored banners.
Use a 1px `border-subtle` line only when the sections would otherwise be ambiguous.

---

## Header

Page header contains:
- Report / dashboard title (left-aligned)
- Optional: subtitle or period label directly beneath
- Optional: top-right metadata (date range, last updated, data source name)

Header height: 64px on dashboard, 80–100px on report pages.
No navigation tabs inside the header unless the page has fewer than 6 top-level views.

---

## Sidebar (when used)

- Width: 240px fixed
- Background: `bg-base` or `bg-inverse`
- No heavy borders on individual nav items
- Active item: left border accent (3px `accent` color) + `text-primary`
- Inactive item: `text-secondary`
- Sidebar contains navigation and global filters only
- Never put data or charts in the sidebar

---

## Responsive Behavior

- Desktop (≥1024px): full grid, sidebar visible
- Tablet (768–1023px): sidebar collapses to icon rail or top navigation, grid narrows
- Mobile (<768px): single column, charts stack, sidebar becomes drawer

On mobile, tables become horizontally scrollable — never truncate data columns.

---

## Density

Prefer comfortable density over excessive whitespace.
A dashboard is not a marketing page.
- Card padding: 16px (not 32px or 40px)
- Row height in tables: 36px
- Chart area: 80% of card height
- Label and axis text do not need large breathing room
