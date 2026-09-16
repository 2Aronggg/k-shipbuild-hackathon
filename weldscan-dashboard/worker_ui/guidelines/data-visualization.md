# Data Visualization Guidelines

## Core Rule

Every chart must be readable without interaction.
The chart title, axis labels, and annotation must together tell the reader what the chart shows and what it means.

---

## Chart Selection

Choose chart type based on the analytical question, not visual appeal.

| Question | Chart type |
|---|---|
| How does X change over time? | Line chart |
| How do multiple series trend over time? | Multi-line or area chart (stacked only if composition matters) |
| How large is X compared to Y? | Bar chart (horizontal if labels are long) |
| What is the composition of X? | Stacked bar or small multiples |
| What is the distribution of X? | Histogram or box plot |
| How are X and Y related? | Scatter plot |
| What is the magnitude of effect by variable? | Horizontal bar chart (SHAP, feature importance) |
| How do values respond over time after a shock? | Line chart with confidence band (IRF) |
| What are the exact values? | Table |

**Never choose a chart type for visual novelty.**
Donut charts: only for 2–3 part composition. Never for trends.
Radar charts: rarely justified — use small multiple bar charts instead.
Treemap: only for hierarchical data where relative area is meaningful.

---

## Chart Anatomy

Every chart must have:

1. **Title** — declarative or descriptive (e.g., "Inflation declines sharply after rate hike" or "Monthly CPI, 2020–2024")
2. **Axis labels** — always present, with units (%, pp, USD bn, index)
3. **Data source** — footnote below chart, small and muted
4. At least one of: **annotation**, **legend**, or **direct label**

Optional but preferred:
- Reference line (e.g., "0", "target", "pre-shock baseline")
- Shaded region for notable periods (recession, policy change, event)
- Callout annotation for the most important data point

---

## Axes

- X-axis: time or categories, never leave unlabeled
- Y-axis: include unit in label (not just in title)
- Dual Y-axis: use only when two series have fundamentally different scales AND their relationship is the analytical point. Label both axes clearly. Do not use for aesthetic variety.
- Y-axis range: start at 0 for bar charts. For line charts, set range to data context — do not artificially compress or expand.
- Gridlines: horizontal only, `border-subtle` color, not distracting
- Tick marks: minimal — only enough to orient the reader

---

## Color in Charts

Use the data color tokens from `visual-style.md`.

Rules:
- Single series: `data-blue`
- Two series: `data-blue` + `data-teal`
- Three series: `data-blue` + `data-teal` + `data-amber`
- Four+ series: reconsider whether a single chart is appropriate
- Highlight one series: use `data-blue` for focus, `data-slate` for all others
- Negative / declining: `data-red`
- Neutral / reference: `data-slate`
- Do not use color for decoration
- Do not use more than 5 colors in a single chart

### Confidence Bands / Uncertainty

- Fill: very light tint of the series color (10–15% opacity)
- Border: same color at 30% opacity
- Label the band clearly: "90% CI", "±1 SD"

---

## Legends

- Prefer direct labeling over legends when possible (label the line at its end point)
- If legend is necessary: place above or below the chart, left-aligned
- Never place legend inside the chart area where it overlaps data
- Legend items: color swatch (12x12px circle or line segment) + label, no border

---

## Annotations

Use annotations to highlight the most important moment or value in the chart.

- Single callout box: `bg-surface`, `border-strong` border, 12px text
- Vertical reference line: 1px dashed `text-muted` color + short label
- Shaded period: very light `bg-subtle` fill with optional label at top

Do not annotate every data point. One or two annotations per chart is the maximum.

---

## Time Series Charts

- X-axis: date labels at even intervals, not crowded
- Format: "Jan 2023", "Q1 2024", "2020" depending on granularity
- Recession shading or event markers: allowed and encouraged when contextually relevant
- Forecast period: distinguish with dashed line + shaded uncertainty band

---

## SHAP / Feature Importance Charts

- Horizontal bar chart, sorted by absolute value (largest at top)
- Left side: negative contribution (`data-red`)
- Right side: positive contribution (`data-blue` or `data-teal`)
- Center reference line at 0
- Bar labels: feature name left-aligned, value right-aligned at bar end
- Include total observation count in subtitle

---

## Impulse Response Function (IRF) Charts

- Line chart showing response over time (horizon on X, effect magnitude on Y)
- Reference line at 0 (horizontal)
- Shaded confidence band (90% or 95%) — light fill, no heavy border
- X-axis: "Periods after shock" or "Quarters"
- Y-axis: unit of the response variable
- If showing multiple IRFs (different variables or models): use small multiples, not overlapping lines on one chart
- Title format: "Response of [Y] to [X] shock"

---

## Small Multiples

Use small multiples when:
- The same chart type is repeated for multiple categories
- Comparing the same metric across subgroups

- Consistent axis scales across all panels (unless explicitly showing relative comparison)
- Shared legend once, not repeated per panel
- Panel label: small, top-left, `text-secondary`
- Grid layout: prefer 2×N or 3×N, not 1×N (vertical stacking loses comparison value)

---

## Chart Sizing

- Full-width chart (12 col): height 320–400px
- Half-width chart (6 col): height 280–320px
- Quarter-width / sparkline: height 120–160px
- Do not make charts taller to fill space — resize the container or add another chart

---

## Chart Interaction

- Tooltip on hover: show exact values, formatted consistently with the axis
- Tooltip format: label + value + unit + date (if applicable)
- Crosshair: vertical line on time series charts
- Click to highlight: optional, use only when cross-filtering is meaningful
- No animated entrance effects for data points (transitions on filter change are acceptable)
