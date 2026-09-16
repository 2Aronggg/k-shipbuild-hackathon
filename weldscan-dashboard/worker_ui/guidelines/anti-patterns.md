# Anti-Patterns — Prohibited Design Patterns

These patterns are prohibited by default.
Do not use them unless explicitly instructed with a specific reason.

---

## Layout Anti-Patterns

### Generic SaaS admin dashboard layout
Do not produce a layout that looks like a Notion, Salesforce, or standard analytics SaaS.
The target audience is analysts and researchers, not product managers reviewing KPIs.

### A grid of identical oversized cards
Do not fill the page with uniform card boxes of the same height and width.
Cards have different informational weight. Layout must reflect that.

### Every section inside a separate card
Not every content block needs a card border.
Use cards for components that are genuinely self-contained (a single KPI, a single chart).
Do not card-wrap running text, section headings, or explanatory paragraphs.

### Excessive whitespace
Do not use 64px+ padding inside cards.
Do not leave half the page blank to appear "clean."
Analytical dashboards are information-dense by nature.

### Arbitrary hero sections
Do not add a large banner or hero image at the top of an analytical page.
The page should begin with the most important data, not with branding.

### Full-width colored header bands
Do not use colored bands or gradient headers to separate sections.
Use typography and spacing to create hierarchy.

---

## Visual Style Anti-Patterns

### Decorative gradients
Do not use gradient backgrounds on cards, headers, or page backgrounds.
Gradients encode no information and add visual noise.

### Gradient text
Never apply gradient fills to text.

### Glassmorphism
Do not use `backdrop-filter: blur()` or frosted glass effects on any component.

### Colored card backgrounds
Cards use `bg-surface` (`#FFFFFF`) only.
Do not tint cards with blue, purple, green, or other hues.

### Arbitrary purple/blue AI-style gradients
Do not use purple-to-blue or teal-to-blue gradients anywhere.
These signal "AI product landing page" and undermine analytical credibility.

### Neumorphism
Do not use soft shadow-on-shadow styling.

### Colored shadows
Do not use `box-shadow` with color tints. Shadows must be black at low opacity only.

---

## Typography Anti-Patterns

### Emoji in any context
Emoji are prohibited. They do not belong in analytical or research interfaces.

### Decorative display fonts
Do not use serif display fonts or script fonts for any UI element.
The type system is Inter (UI) + monospace (numbers). Nothing else.

### All-caps body text
All-caps is permitted only for short KPI labels (2–3 words max).
Never use it for body text, section headings, or table content.

### Gradient text
Repeated for emphasis: never fill text with a gradient.

---

## Component Anti-Patterns

### Huge KPI numbers with little context
A large number alone is meaningless.
Every KPI value requires: unit, time reference, and comparison baseline.

### Icons placed for decoration
Do not add icons next to labels unless the icon adds information the label cannot convey.
Do not use a chart icon next to the word "Analytics."
Do not use a building icon next to a company name.

### Random icon usage
Do not fill the interface with icons to make it look populated.

### Decorative illustrations in analytical views
Do not place illustrations, SVG art, or decorative graphics in a dashboard or report page.
Illustrations belong in onboarding flows and empty states only, and even there use with restraint.

### Oversized buttons and CTAs
Analytical dashboards are not conversion pages.
Buttons and controls should be proportional to the content, not prominent.

### Fake metrics or placeholder statistics
Do not generate placeholder data to make a design look populated.
If data is not available, show a proper empty state.

---

## Chart Anti-Patterns

### Charts placed only for decoration
Every chart must exist because it answers a specific analytical question.
Do not add a sparkline because the card looks empty. Remove the card.

### Donut chart for more than 3 categories
Replace with a horizontal bar chart sorted by value.

### 3D charts
Never use 3D bar, 3D pie, or any three-dimensional chart rendering.

### Chart animations on load
Do not animate charts drawing themselves on page load.
Data should be visible immediately.

### Unlabeled axes
Every axis must have a label with a unit.

### Over-annotated charts
Do not annotate every data point.
Maximum 2 annotations per chart.

### Legend inside the chart area
Legends must be outside the plot area.

### Too many colors in one chart
Maximum 5 data series per chart, each with a distinct color from the data color palette.
If you need more, use small multiples.

---

## Navigation Anti-Patterns

### Unnecessary navigation items
Do not add navigation links to pages that do not exist or have no content.
Navigation must reflect actual pages.

### Icons-only navigation without tooltips
Navigation items without text labels must have accessible tooltips.

### Breadcrumbs on a single-level page
Do not add breadcrumbs where there is no hierarchy.
