# Dashboard Component Guidelines

## KPI Cards

### Purpose

KPI cards summarize a single key metric with context.
They exist to anchor the reader's understanding before they read charts.

### Structure

```
┌─────────────────────────────┐
│ LABEL (uppercase, 11px)     │
│                             │
│ 24.6%     ▲ +1.2pp vs prev │
│ (monospace, 28-36px)        │
│                             │
│ Context note (12px, muted)  │
└─────────────────────────────┘
```

### Rules

- Always include: metric label, value, unit, comparison baseline or trend
- The value itself is not enough — always show what it is compared to
- Comparison baseline examples: "vs. prior period", "YoY", "vs. benchmark", "Q3 2024"
- Trend indicator: small directional arrow (▲ / ▼) + delta value, color-coded (`data-red` for decline, `data-teal` for improvement) only when direction has clear meaning
- Never use trend color when direction is ambiguous (e.g., higher interest rates — good or bad depends on context)
- KPI row maximum: 4 cards per row on desktop, 2 per row on tablet
- Card width is determined by the grid, not by the content

### What KPI Cards Are Not

- Not decorative stat displays
- Not a row of large glowing numbers
- Not a place for icons that duplicate the label
- Not an opportunity for color fills or gradient backgrounds

---

## Filters and Controls

### Placement

- Filters belong at the top of the section they affect, not in a persistent toolbar unless they affect the entire page
- Global page filters (date range, region, scenario) go in the sidebar or directly below the page header
- Never float filters in the middle of a content area

### Filter Components

| Filter type | Component |
|---|---|
| Date range | Dropdown with preset options (YTD, 1Y, 3Y, Custom) |
| Category | Segmented control (≤4 options) or dropdown (≥5 options) |
| Multi-select | Checkbox dropdown, not tag-filled inputs |
| Scenario / mode | Segmented control |

- Filters use `border-strong` border, `bg-surface` background, `text-primary` label
- Selected state: `accent` border, slight `bg-subtle` background
- No colorful filter pills, no emoji in filter labels

### Filter Behavior

- Applying a filter should immediately update all charts and tables in scope
- Active filters should be visible (label + selected value shown)
- A "Reset" or "Clear filters" action is always available when any non-default filter is applied

---

## Tables

### Use tables when

- Precision matters more than trend
- The user needs to compare specific values across rows
- The data has more than 2 dimensions that cannot be reduced to a chart

### Table Structure

- Header row: `bg-subtle`, `text-secondary`, 11–12px, uppercase, bold
- Body rows: alternating `bg-surface` / `bg-subtle` or solid `bg-surface` with `border-subtle` row separator
- Numbers: right-aligned, monospaced
- Text cells: left-aligned
- Row height: 36px
- Sticky header when table exceeds viewport height

### Table Rules

- Never center-align numbers
- Columns with values of different orders of magnitude need clear unit labels in the header
- Negative values: `text-color: data-red`, do not use parentheses alone
- Highlight row on hover: `bg-subtle` tint
- Pagination preferred over endless scroll for >50 rows

---

## Navigation

### Top-level navigation

- Maximum 6 items
- Text labels only — no icons without labels in primary navigation
- Active item: bottom border (2px `accent`) or background highlight
- Never use tabs that look like browser tabs

### In-page navigation

- Use anchor links or a sticky section indicator for long report pages
- In-page tabs for switching between related views (e.g., Chart / Table / Data)

---

## Empty States

- Always show an empty state when data is absent
- Empty state: short label explaining why data is missing + suggested action if applicable
- Never show a blank space where a chart should be
- Never show placeholder "loading..." text as a permanent state

---

## Loading States

- Use skeleton screens for charts and tables, not spinners
- Skeleton: `bg-subtle` rectangles matching the expected content shape
- Do not show partial data while loading
