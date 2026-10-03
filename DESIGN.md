# DESIGN.md — AI Review & Operations System (ODIPKS Construction OS)

## 1. Visual Language & Core Principles
- **Calm, Precise, Trustworthy**: Designed like a precision instrument in a quiet architect's studio or private bank.
- **Space is the luxury**: Generous whitespace, layered progressive disclosure, no visual clutter.
- **Quiet color, one accent**: Neutral warm surfaces (`#FAFAF9` in light mode, `#0E0E10` in dark mode) paired with a signature desaturated indigo accent (`#3D4FD8` light / `#7B8BFF` dark).
- **Subtle depth**: 1px low-opacity borders (`rgba(20,20,25,0.08)` / `rgba(255,255,255,0.08)`), very soft shadows, and frosted-glass blurs on floating elements.
- **Typography**: Self-hosted Geist Sans and Geist Mono with tabular figures (`font-variant-numeric: tabular-nums`) for numeric data alignment.

---

## 2. Design Tokens

```css
:root {
  /* Surfaces: Light mode - warm off-white */
  --bg:            #FAFAF9;   /* page background */
  --surface:       #FFFFFF;   /* cards, panels */
  --surface-sunk:  #F3F3F1;   /* inputs, table headers, wells */
  --border:        rgba(20, 20, 25, 0.08);
  --border-strong: rgba(20, 20, 25, 0.16);

  /* Typography */
  --text:          #17171A;
  --text-muted:    #6B6B73;
  --text-faint:    #9A9AA2;

  /* Signature Accent */
  --accent:        #3D4FD8;
  --accent-soft:   rgba(61, 79, 216, 0.10);
  --accent-hover:  #3242BE;
  --accent-contrast: #FFFFFF;

  /* Status Colors */
  --success:       #2F7D5B;
  --success-soft:  rgba(47, 125, 91, 0.12);
  --warning:       #B7791F;
  --warning-soft:  rgba(183, 121, 31, 0.12);
  --danger:        #B4443C;
  --danger-soft:   rgba(180, 68, 60, 0.12);

  /* Geometry & Rhythm */
  --radius-sm:     8px;
  --radius-md:     12px;
  --radius-lg:     20px;
  --radius-pill:   999px;
  --space:         8px;

  /* Depth */
  --shadow-soft:   0 1px 2px rgba(0, 0, 0, 0.04), 0 8px 24px rgba(0, 0, 0, 0.06);
  --shadow-float:  0 4px 20px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);
  --glass:         rgba(255, 255, 255, 0.75);

  /* Transitions */
  --ease:          cubic-bezier(0.2, 0.8, 0.2, 1);
  --fast:          150ms;
  --base:          240ms;
}

[data-theme="dark"] {
  /* Surfaces: Dark mode - deep slate-black */
  --bg:            #0E0E10;
  --surface:       #161618;
  --surface-sunk:  #1D1D20;
  --border:        rgba(255, 255, 255, 0.08);
  --border-strong: rgba(255, 255, 255, 0.16);

  --text:          #F2F2F3;
  --text-muted:    #9C9CA5;
  --text-faint:    #6E6E77;

  --accent:        #7B8BFF;
  --accent-soft:   rgba(123, 139, 255, 0.14);
  --accent-hover:  #8E9DFF;
  --accent-contrast: #0E0E10;

  --success:       #4EAA7F;
  --success-soft:  rgba(78, 170, 127, 0.14);
  --warning:       #D69538;
  --warning-soft:  rgba(214, 149, 56, 0.14);
  --danger:        #D46159;
  --danger-soft:   rgba(212, 97, 89, 0.14);

  --shadow-soft:   0 1px 2px rgba(0, 0, 0, 0.3), 0 8px 24px rgba(0, 0, 0, 0.45);
  --shadow-float:  0 4px 24px rgba(0, 0, 0, 0.6), 0 1px 4px rgba(0, 0, 0, 0.4);
  --glass:         rgba(22, 22, 24, 0.78);
}
```

---

## 3. Component Architecture & Guidelines

### `Button` (`src/components/ui/Button.tsx`)
- Geometry: Full pill (`rounded-pill`).
- Variants: `primary`, `secondary`, `destructive`, `ghost`, `accent-soft`.
- States: Calm hover, focus ring glow, subtle press down (`active:scale-[0.99]`), disabled opacity.

### `Input` (`src/components/ui/Input.tsx`)
- Sunken fill (`bg-surface-sunk`), hairline border, accent focus ring with subtle glow.
- Inline calm validation error messages and deliberate password/PIN reveal toggle.

### `Card` (`src/components/ui/Card.tsx`)
- Clean rounded surface (`--radius-lg` / `--radius-md`), hairline border, soft shadow, generous internal padding (16-32px).
- Internal hierarchy structured through subtle dividers and whitespace, avoiding nested boxes.

### `Badge` (`src/components/ui/Badge.tsx`)
- Pill-shaped chip with soft tinted background and matching text.
- Special variants: `ai` (subtle sparkle marker) and `verified` (human sign-off marker).

### `Table` (`src/components/ui/Table.tsx`)
- Airy rows, hairline horizontal dividers (`--border`), sticky quiet header, barely visible row hover tint.
- Numeric columns automatically use `tabular-nums` alignment with monospace font.

### `Modal` & `Drawer` (`src/components/ui/Modal.tsx`)
- Frosted-glass backdrop (`--glass`), smooth fade-and-rise entrance, Escape key listener.

### `Skeleton` (`src/components/ui/Skeleton.tsx`)
- Restrained shimmer animation for non-frantic loading states.

### `Toast` (`src/components/ui/Toast.tsx`)
- Non-intrusive floating status banner with calm language and auto-dismiss.

---

## 4. Confidentiality & Security Protocol Suite

1. **`MaskedField` (`src/components/ui/MaskedField.tsx`):**
   - Automatically masks financial figures, phone numbers, and sensitive identifiers.
   - Smooth click-to-reveal interaction with automatic 15-second re-mask timer.
2. **`PrivacyShield` (`src/components/ui/PrivacyShield.tsx`):**
   - Content blurs smoothly (`privacy-blur`) when the browser tab loses focus or when user is idle for 5 minutes.
   - Shows an elegant lock screen with PIN unlock instead of an abrupt logout.
3. **`SecurityTrustIndicator` (`src/components/ui/SecurityTrustIndicator.tsx`):**
   - Quiet top bar indicator showing encrypted TLS status, current authenticated role, and one-click immutable audit trail modal.
4. **`CommandPalette` (`src/components/ui/CommandPalette.tsx`):**
   - Fast `⌘K` / `Ctrl+K` keyboard modal for instant navigation, theme toggling, and quick role switching.

---

## 5. The Two-Pane AI Review Workspace (`src/components/review/TwoPaneReviewWorkspace.tsx`)
- **Left Pane (Source Material):** Piling boring logs, concrete displacement, equipment runtime, and delays with interactive highlight markers.
- **Right Pane (AI Analysis):** Model assessment, visual confidence gauge (e.g. 94.2%), interactive findings with flag toggles, and collapsible chain-of-thought reasoning.
- **Bidirectional Linking:** Clicking an AI finding smoothly scrolls to and highlights the source passage; clicking a source passage highlights the corresponding finding.
- **Sticky Action Bar:** `[R] Reject`, `[F] Flag for Revision`, `[A] Approve & Sign` with keyboard shortcuts.
- **Calm Progress:** Refined pulse line during analysis, never a frantic spinner.
