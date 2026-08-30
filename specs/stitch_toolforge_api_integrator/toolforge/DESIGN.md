---
name: ToolForge
colors:
  surface: '#10131a'
  surface-dim: '#10131a'
  surface-bright: '#363940'
  surface-container-lowest: '#0b0e14'
  surface-container-low: '#191c22'
  surface-container: '#1d2026'
  surface-container-high: '#272a31'
  surface-container-highest: '#32353c'
  on-surface: '#e1e2eb'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#e1e2eb'
  inverse-on-surface: '#2e3037'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#ffb95f'
  on-tertiary: '#472a00'
  tertiary-container: '#ca8100'
  on-tertiary-container: '#3e2400'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#10131a'
  on-background: '#e1e2eb'
  surface-variant: '#32353c'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  unit-1: 0.25rem
  unit-2: 0.5rem
  unit-3: 0.75rem
  unit-4: 1rem
  unit-6: 1.5rem
  unit-8: 2rem
  unit-12: 3rem
  container-max: 1440px
  gutter: 24px
---

## Brand & Style
The design system is engineered for an "infrastructure-grade" developer experience. It prioritizes technical precision and high-density information without sacrificing aesthetic clarity. The style is a synthesis of **Minimalism** and **Modern Corporate**, utilizing a dark-first approach that reduces eye strain for long-term engineering tasks.

The brand personality is serious, trustworthy, and systematic. Every element should feel intentional and high-fidelity, using subtle depth and micro-interactions to signal reliability and speed. The interface should evoke the feeling of a sophisticated command center—clean, responsive, and powerful.

## Colors
The palette is rooted in deep charcoal tones to establish a professional developer environment. 

- **Primary (#3B82F6):** Used for primary actions, focus states, and active toolpaths.
- **Success (#10B981):** Applied to healthy API statuses, deployment completions, and verified agent connections.
- **Warning (#F59E0B):** Reserved for rate-limiting alerts, deprecation notices, and non-breaking configuration errors.
- **Background (#0B0E14):** The foundational layer for the entire application.
- **Surface (#161B22):** Used for cards, sidebars, and nested containers to create visual hierarchy.
- **Border (#30363D):** A low-contrast gray for subtle structural definition.

## Typography
This design system employs a dual-font strategy:
1. **Inter** handles all UI text, navigation, and documentation prose. It is selected for its high legibility and neutral, professional tone.
2. **JetBrains Mono** is utilized for all technical data, including API endpoints, JSON payloads, environment variables, and code snippets.

On mobile devices, `headline-xl` should scale down to 24px and `headline-lg` to 20px to ensure the interface remains usable in compact viewports.

## Layout & Spacing
The layout follows a **Fluid Grid** model with a maximum container width of 1440px for desktop. It uses an 8px spacing rhythm for components and a 4px scale for micro-spacing (e.g., icons inside buttons).

- **Desktop (1024px+):** 12-column grid with 24px gutters and 48px side margins.
- **Tablet (768px - 1023px):** 8-column grid with 20px gutters and 24px side margins.
- **Mobile (0 - 767px):** 4-column grid with 16px gutters and 16px side margins.

Content should be grouped into cards and logical sections to prevent "information sprawl." Use generous vertical whitespace (`unit-12`) between major sections to maintain a premium feel.

## Elevation & Depth
Depth is achieved through **Tonal Layers** rather than heavy shadows. In this design system, surfaces move "closer" to the user by becoming lighter in color.

1. **Level 0 (Background):** #0B0E14 - The base layer.
2. **Level 1 (Card/Surface):** #161B22 - The primary container for content.
3. **Level 2 (Popovers/Modals):** #1C2128 - Used for elements that float above the main UI.

Shadows should be extremely subtle: `0 4px 12px rgba(0, 0, 0, 0.5)`. Borders are the primary method of separation—use 1px solid lines in #30363D for all card and input boundaries.

## Shapes
The shape language is "Soft-Technical." Elements use a consistent `0.5rem` (8px) radius for standard components like buttons and inputs. Larger containers like cards use `0.75rem` (12px) to provide a softer, more modern framing for dense technical data.

- **Buttons/Inputs:** 8px (rounded)
- **Cards/Containers:** 12px (rounded-lg)
- **Status Pills:** 9999px (pill-shaped)

## Components

### Navigation
The header is a compact, top-aligned bar (64px height) with a subtle bottom border. Use `label-sm` for navigation links to maintain a technical, "utility" feel.

### Cards
Technical cards feature a distinct header section separated by a 1px border. Use `headline-md` for card titles and place primary actions (like "Edit" or "Test") in the top right of the card header.

### Buttons & Inputs
- **Primary Button:** Solid #3B82F6 with white text.
- **Secondary Button:** Outline style with #30363D border and white text.
- **Inputs:** Use `surface_color_hex` for the background. Placeholders must use JetBrains Mono to signal where developers should input code-related strings.

### Code Blocks
Render code blocks with a background of #010409. Use a syntax highlighting theme that emphasizes the Primary and Success colors. Include a "Copy" button in the top right that appears on hover.

### Status Indicators
For active processes, use a "Pulse" animation on a 8px circle. 
- **Active/Live:** Green pulse.
- **Syncing:** Blue pulse.
- **Error:** Solid Amber (no pulse).

### Progressive Checklist
For agent configuration steps, use a vertical list where completed items use the Success color and a checkmark, while current items are highlighted with a Primary left-border.