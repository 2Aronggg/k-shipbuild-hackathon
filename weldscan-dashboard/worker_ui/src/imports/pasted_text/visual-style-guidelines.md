# Visual Style Guidelines

## Design Vocabulary

Industrial, technical, precise, restrained.

The interface should feel like a modern inspection workspace used in a professional engineering environment.

It must NOT feel like:
- an institutional research report
- a generic SaaS dashboard
- an AI startup product
- a cybersecurity command center
- a gaming interface

The RT inspection image is the visual focus.
UI styling should remain controlled and secondary to inspection content.

---

# Color System

## Core Palette

Use the following palette as the primary visual system.

| Token | Value | Use |
|---|---|---|
| `bg-base` | `#161617` | Main application background |
| `bg-surface` | `#333336` | Primary panels and controls |
| `bg-secondary` | `#2B3A37` | Secondary technical surfaces |
| `bg-warm` | `#271A11` | Rare contextual warm surface |
| `text-primary` | `#F4F8FB` | Main text and headings |
| `text-secondary` | `#D2D2D7` | Secondary information |
| `text-muted` | `#86868B` | Metadata and inactive information |
| `text-disabled` | `#6E6E73` | Disabled / very low-priority information |
| `accent-primary` | `#3397D4` | Main interactive state |
| `accent-soft` | `#9FC6F4` | Hover and secondary highlight |
| `accent-technical` | `#41626A` | Technical / reference information |
| `accent-special` | `#EA33C0` | Rare exceptional emphasis |

---

## Backgrounds

### Main workspace

Use:

`#161617`

for:
- application canvas
- RT inspection workspace
- image-viewer surrounding area
- persistent application chrome

Do not use pure black.

---

### Panels

Primary panels:

`#333336`

Use for:
- inspection results
- tool controls
- secondary content panels
- modal surfaces

Secondary technical panels:

`#2B3A37`

Use for:
- reference data
- IQI information
- secondary inspection information
- inactive supporting areas

Do not give every section its own different background color.

---

# Text

### Primary

`#F4F8FB`

Use for:
- page title
- selected inspection result
- important labels
- primary values
- active controls

### Secondary

`#D2D2D7`

Use for:
- normal body text
- secondary values
- descriptions

### Muted

`#86868B`

Use for:
- timestamps
- metadata
- inactive navigation
- secondary labels

### Disabled

`#6E6E73`

Use only for:
- disabled states
- very low-priority information

Do not use low-contrast gray for essential inspection information.

---

# Interactive Accent

## Primary accent

`#3397D4`

Use only for:
- selected tabs
- active tools
- primary interaction state
- focus indicator
- important links

Avoid large blue filled surfaces.

Blue should communicate interaction, not decoration.

---

## Soft accent

`#9FC6F4`

Use for:
- hover states
- lightweight selection backgrounds
- secondary active indicators
- subtle information emphasis

---

# Technical / Reference Color

Use:

`#41626A`

for information that is technical but is NOT a defect.

Examples:
- IQI reference area
- calibration indicators
- measurement reference
- image-quality information
- technical annotations

This distinction is important:

**technical reference ≠ detected defect**

---

# Special Accent

`#EA33C0`

Use extremely sparingly.

Acceptable:
- rare temporary highlight
- exceptional interaction state
- one distinctive visual detail

Never use for:
- main navigation
- large backgrounds
- normal buttons
- inspection status
- gradients
- decoration across multiple components

Target visible usage:
less than 3% of the screen.

---

# Semantic Inspection Colors

Inspection states are semantic and may exist outside the general palette.

Do not replace meaningful inspection colors simply to match the UI palette.

Porosity markers:

- `P1` — Red
- `P2` — Orange
- `P3` — Green

These colors should only appear on:
- defect marker
- selected defect indicator
- corresponding small status label

Never fill large panels using defect colors.

IQI/reference annotations must use neutral or technical colors, preferably:

`#41626A`

---

# Typography

## Primary Typeface

Use a clean modern sans-serif for the primary interface.

Preferred:

`Inter`

Fallback:

`system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`

Use the same primary typeface consistently across:
- headings
- buttons
- navigation
- labels
- descriptions

---

## Technical Typeface

Use:

`IBM Plex Mono`

or

`JetBrains Mono`

only for:
- inspection IDs
- measurement values
- millimeter coordinates
- timestamps
- confidence values
- technical codes

Do NOT use monospace for the entire application.

---

# Type Scale

| Role | Size | Weight |
|---|---:|---:|
| Main title | 22px | 600 |
| Section title | 16px | 600 |
| Panel title | 14px | 600 |
| Body | 14px | 400 |
| UI label | 13px | 500 |
| Metadata | 12px | 400 |
| Technical value | 13–14px | 500 |
| Button | 14px | 500–600 |

---

# Typography Rules

Avoid excessive uppercase.

Do NOT render:
- navigation
- section headings
- buttons
- body labels

entirely in uppercase.

Use sentence case by default.

Uppercase may only be used for:
- very short technical abbreviations
- established engineering notation
- compact status codes

Typography must prioritize fast recognition in a field environment.

---

# Border and Radius

Use restrained geometry.

### Radius

- Panels: `6px`
- Buttons: `5px`
- Inputs: `5px`
- Tags: `4px`
- Tool controls: `5px`

Avoid:
- pill-shaped UI
- excessive rounded cards
- radius above `10px` for normal interface panels

---

# Borders

Use subtle borders to separate functional regions.

Recommended:

Primary border:
`rgba(244, 248, 251, 0.10)`

Strong border:
`rgba(244, 248, 251, 0.18)`

Selected border:
`#3397D4`

Do not outline every individual block.

Use spacing before borders whenever possible.

---

# Shadow

Dark UI should primarily use contrast between surfaces rather than heavy shadows.

Default panel shadow:

`0 1px 2px rgba(0,0,0,0.28)`

Floating elements:

`0 6px 18px rgba(0,0,0,0.32)`

Do not use:
- glow
- colored shadow
- neon halo
- glassmorphism

---

# RT Image Treatment

The RT image must remain visually dominant.

Rules:

- Preserve the original grayscale image.
- Never recolor or tint it.
- Do not place a dark overlay across the entire image.
- Do not add decorative gradients.
- Do not reduce contrast for aesthetic purposes.

Annotations must remain lightweight and precise.

Prefer:
- small marker
- thin outline
- compact label

Avoid:
- oversized bounding boxes
- large translucent colored areas
- annotations covering the defect itself

---

# Surface Hierarchy

Use color hierarchy approximately as follows:

1. `#161617` — page/background
2. `#333336` — primary workspace surface
3. `#2B3A37` — secondary technical surface
4. neutral text colors
5. `#3397D4` — interaction
6. semantic defect colors
7. `#EA33C0` — rare exceptional accent

Do NOT attempt to display every palette color simultaneously.

---

# Overall Tone

The interface should feel:

- dark but readable
- technical but not intimidating
- industrial without appearing outdated
- high information density without clutter
- visually quiet around the RT image
- deliberately designed rather than template-generated

Color should communicate function.

Decorative color usage should be minimal.

---

# Prohibited Visual Patterns

Never use:

- warm beige / editorial report styling
- pure white page backgrounds
- purple-blue gradients
- neon cyan
- glowing borders
- glassmorphism
- excessive card nesting
- every section inside a rounded rectangle
- full-screen black with bright neon text
- cyberpunk styling
- command-center styling
- decorative charts
- arbitrary colors outside the defined palette
- large blocks of magenta
- monospace typography across the full interface