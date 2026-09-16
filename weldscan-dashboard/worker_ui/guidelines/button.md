# Button Guidelines

## Purpose

Buttons must feel functional, compact, and deliberate.

They should support an industrial inspection workflow and must not resemble oversized SaaS marketing CTAs.

---

## General Rules

- Use one consistent button system across the interface.
- Use sentence case.
- Do not use emoji inside buttons.
- Use vector icons only when the icon improves recognition.
- Keep buttons compact and task-oriented.
- Avoid decorative buttons.
- Avoid gradients, glow, glass effects, and colored shadows.
- Do not make every action visually equal.

---

## Primary Button

Use for the single most important action in the current context.

Examples:
- Confirm inspection
- Save result
- Escalate to senior inspector

Style:
- Solid `accent-primary`
- High-contrast text
- Medium font weight
- Height: 36–40px
- Horizontal padding: 14–18px
- Border radius: 5px
- No gradient
- No glow
- No heavy shadow

Only one primary button should visually dominate a section.

---

## Secondary Button

Use for supporting actions.

Examples:
- Recheck
- Compare case
- View inspection basis

Style:
- Transparent or neutral surface
- Subtle border
- Primary or secondary text color
- Same height as primary buttons
- Same radius as primary buttons

Secondary buttons must not compete visually with the primary action.

---

## Tertiary / Tool Button

Use for lightweight image-viewer controls.

Examples:
- Zoom
- Pan
- Toggle overlay
- Annotation
- Reset view

Style:
- Minimal container
- Icon-first
- Compact square or rectangular control
- Neutral default state
- Accent color only when active or selected

Avoid surrounding every tool icon with a heavy card.

---

## Icon Buttons

- Use one consistent outline icon family.
- Maintain consistent icon stroke width.
- Recommended icon size: 16–18px.
- Minimum touch target on tablet: approximately 40–44px.
- Provide tooltip or visible label if the meaning is not immediately obvious.
- Never mix emoji and vector icons.

---

## Destructive / Critical Actions

Destructive colors should only indicate genuinely destructive actions.

Examples:
- Reject result
- Delete annotation

Do not use red simply to make a button visually prominent.

Escalation is not destructive and should not automatically use red.

---

## Selected States

For toggle-style buttons:

- Active state: `accent-primary`
- Inactive state: neutral surface
- Selected state must be obvious without relying solely on color.
- Use icon, border, background, or text weight together when appropriate.

---

## Button Hierarchy

Preferred hierarchy:

1. Primary action
2. Secondary action
3. Tertiary tools
4. Destructive actions only when required

Avoid showing multiple primary buttons next to each other.

---

## Prohibited Patterns

Never use:

- pill-shaped CTA buttons
- oversized marketing buttons
- gradients
- glow effects
- emoji
- random icon colors
- excessive rounded corners
- multiple competing primary buttons
- bright semantic colors for ordinary actions
- buttons that contain unnecessary explanatory paragraphs