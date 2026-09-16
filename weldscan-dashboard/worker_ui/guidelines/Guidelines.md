# Figma Make — Master Guidelines

## Purpose

This file is the authoritative design instruction document for Figma Make.
All other guidelines files extend these rules. When there is a conflict, this file takes precedence.

---

## Core Principle

**The interface must communicate information first. Visual decoration is secondary.**

This project builds analytical dashboards, research reports, and data-driven web pages.
The audience reads to understand data, not to admire the design.
Every visual decision must serve comprehension.

---

## What This Is Not

Do not create:
- A generic SaaS admin dashboard
- A marketing landing page
- A dark-mode fintech app with glowing cards
- An AI product homepage with gradients and illustrations

---

## What This Is

Create interfaces that resemble:
- Bloomberg Terminal layouts (dense, efficient, structured)
- Stripe Dashboard (clean typography, honest data display)
- Linear (disciplined spacing, strong hierarchy, no noise)
- Institutional research reports (OECD, IMF, academic journals)
- Editorial data journalism (NYT Graphics, FT Visual Storytelling)

---

## Page Creation Order

When creating any new page or section, follow this sequence strictly:

1. Understand the information hierarchy — what is the most important finding?
2. Decide which information deserves the most visual prominence.
3. Build the page structure and grid.
4. Place charts and analytical content.
5. Add controls (filters, toggles) only when they serve the data.
6. Apply visual styling last.

Do not add UI elements to make the page look more complete or polished.
If a section has no analytical purpose, remove it.

---

## Visual Hierarchy Rules

- The most important insight must be visually dominant.
- Section titles must clearly describe what the section contains.
- Every chart must be readable without a tooltip.
- KPI values must always appear with context (unit, time period, comparison baseline).
- Never use visual scale to imply importance that does not exist in the data.

---

## Decision Rules for Figma Make

When in doubt:
- Choose density over whitespace
- Choose data over decoration
- Choose monospace over display fonts for numbers
- Choose muted color over vivid color
- Choose annotation over legend when possible
- Choose table over chart when precision matters more than trend

---

## File Structure Reference

| File | Role |
|---|---|
| `guidelines/Guidelines.md` | Master rules (this file) |
| `guidelines/visual-style.md` | Color, typography, shadow, border |
| `guidelines/layout.md` | Grid, spacing, responsive rules |
| `guidelines/dashboard.md` | KPI cards, filters, sidebar, navigation |
| `guidelines/data-visualization.md` | Charts, axes, legends, annotation |
| `guidelines/anti-patterns.md` | Prohibited patterns |
| `guidelines/report-content.md` | Project-specific content template |

---

## Priority Order

1. Information clarity
2. Visual hierarchy
3. Typographic legibility
4. Data density
5. Aesthetic consistency
6. Visual polish (last)
