# visual-style.md

## Visual direction

Use a dark, restrained industrial interface with cool gray, muted teal, and blue accents.

The interface should feel:
- technical
- precise
- modern
- controlled
- high-contrast without looking cyberpunk
- suitable for an industrial RT inspection workspace

The RT image must remain the strongest visual element.
UI colors should support the image, not compete with it.

---

## Core color palette

Use only the following palette for the general interface.

### Dark surfaces

- `#161617` — Primary dark background
- `#333336` — Elevated dark surface / secondary panel
- `#2B3A37` — Muted green-gray surface
- `#271A11` — Warm dark brown accent surface

### Neutral grays

- `#6E6E73` — Secondary text / subdued controls
- `#86868B` — Muted text / inactive states
- `#D2D2D7` — Light border / secondary light surface
- `#F4F8FB` — Primary light text / light surface

### Cool industrial accents

- `#41626A` — Muted teal
- `#3397D4` — Primary blue accent
- `#9FC6F4` — Soft blue highlight

### Special accent

- `#EA33C0` — Magenta emphasis

Magenta must be used very sparingly.
It is not a primary brand color and must never dominate the page.

---

## Color roles

### Application background

Primary application background:

`#161617`

Use this for:
- overall canvas
- main workspace background
- areas surrounding the RT viewer

Do not use pure black (`#000000`).

---

### Primary surfaces

Primary panels:

`#333336`

Use for:
- inspection result panels
- toolbars
- secondary information areas
- modal surfaces

Alternative muted surface:

`#2B3A37`

Use selectively for:
- secondary inspection information
- reference information
- inactive supporting areas

Avoid making every section a differently colored panel.

---

### Primary text

Primary text on dark surfaces:

`#F4F8FB`

Use for:
- titles
- primary labels
- important inspection values
- selected states

Secondary text:

`#D2D2D7`

Use for:
- descriptions
- secondary values
- metadata

Muted text:

`#86868B`

Use for:
- inactive labels
- tertiary information
- disabled controls

Very low-priority text:

`#6E6E73`

Do not use this color for small text when contrast becomes insufficient.

---

## Primary interaction color

Primary interactive accent:

`#3397D4`

Use for:
- selected controls
- active tabs
- primary links
- focus states
- active image tools
- important interactive indicators

Do not fill large areas with this color.

---

## Secondary interaction color

Soft blue:

`#9FC6F4`

Use for:
- subtle selected backgrounds
- hover states
- secondary highlights
- lightweight information indicators

Pair with `#161617` or `#333336` text when used on light surfaces.

---

## Industrial reference color

Muted teal:

`#41626A`

Use for:
- IQI / reference information
- image quality reference markers
- calibration-related UI
- neutral technical indicators

This color should visually distinguish reference information from actual detected defects.

---

## Special accent

Magenta:

`#EA33C0`

Use only for exceptional UI emphasis such as:
- one special active state
- temporary notification
- rare visual emphasis

Never use magenta for:
- large backgrounds
- gradients
- primary navigation
- normal inspection status
- decorative effects

Target usage should remain below approximately 3–5% of the visible interface.

---

## Warm accent

Dark brown:

`#271A11`

Use very selectively.

Possible uses:
- muted warning background
- archived / historical information
- contextual comparison states

Do not use as a major page background.

---

## Borders and dividers

Primary border on dark surfaces:

`#333336`

Visible divider:

`#6E6E73`

Light-mode / light-surface border:

`#D2D2D7`

Prefer subtle 1px separators.

Avoid:
- bright outlines around every card
- nested bordered containers
- glowing borders

---

## RT image treatment

The RT image must remain grayscale.

Never:
- recolor the RT image
- apply blue or teal tint
- add gradients over the image
- reduce image readability for visual styling

Controls and annotations should sit above the image without visually overpowering it.

---

## Defect markers

Defect marker colors are semantic and independent from the general UI palette.

Keep the currently defined defect colors:

- P1 = Red
- P2 = Orange
- P3 = Green

Do not replace P1/P2/P3 colors with the general interface palette.

The general palette should be used for the surrounding application UI only.

IQI and other reference objects should use:

`#41626A`

or a neutral gray from the palette.

---

## Recommended color hierarchy

The interface should visually follow approximately:

- 55–65% `#161617`
- 15–25% `#333336`
- 5–10% neutral grays
- 5–8% `#3397D4`
- small amounts of `#41626A` and `#9FC6F4`
- less than 3–5% `#EA33C0`

Do not attempt to use every palette color on every screen.

---

## Avoid

Do not introduce additional arbitrary colors.

Avoid:
- purple gradients
- blue gradients
- neon cyan
- glowing UI
- rainbow status colors
- excessive use of magenta
- excessive saturated blue
- pure black backgrounds
- generic cyber-security dashboard styling

The palette should feel controlled rather than colorful.