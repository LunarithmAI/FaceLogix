---
name: FaceLogix Calibration Record
description: A cold calibration-paper system for direct, technically credible attendance verification.
colors:
  paper: "#f2f5f4"
  paper-deep: "#e5eae8"
  ink: "#111715"
  muted: "#4d5a56"
  line: "#aeb9b5"
  line-soft: "#d3dbd8"
  cobalt: "#1e5bff"
  cobalt-dark: "#123fb8"
  cobalt-pale: "#dce5ff"
  white: "#ffffff"
  signal: "#0b7446"
  error: "#a82e28"
typography:
  display:
    fontFamily: '"Archivo Variable", "Helvetica Neue", sans-serif'
    fontSize: "clamp(4.3rem, 7vw, 7.7rem)"
    fontWeight: 790
    lineHeight: 0.87
    letterSpacing: "-0.04em"
  headline:
    fontFamily: '"Archivo Variable", "Helvetica Neue", sans-serif'
    fontSize: "clamp(2.8rem, 5.5vw, 5.6rem)"
    fontWeight: 770
    lineHeight: 0.96
    letterSpacing: "-0.04em"
  title:
    fontFamily: '"Archivo Variable", "Helvetica Neue", sans-serif'
    fontSize: "clamp(1.45rem, 2.2vw, 2rem)"
    fontWeight: 700
    lineHeight: 1.05
  body:
    fontFamily: '"Archivo Variable", "Helvetica Neue", sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  action:
    fontFamily: '"Archivo Variable", "Helvetica Neue", sans-serif'
    fontSize: "1rem"
    fontWeight: 730
    lineHeight: 1.55
  data-label:
    fontFamily: '"IBM Plex Mono", "Cascadia Mono", "Roboto Mono", monospace'
    fontSize: "0.68rem"
    fontWeight: 700
    lineHeight: 1.55
    letterSpacing: "0.12em"
spacing:
  page-gutter: "clamp(1.1rem, 4vw, 4.5rem)"
  section-block: "clamp(6rem, 11vw, 11rem)"
  grid-unit: "2rem"
  action-gap: "1.5rem"
components:
  button-primary:
    backgroundColor: "{colors.cobalt}"
    textColor: "{colors.white}"
    typography: "{typography.action}"
    padding: "0.85rem 1.3rem"
  button-primary-hover:
    backgroundColor: "{colors.cobalt-dark}"
    textColor: "{colors.white}"
  button-dark:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
    typography: "{typography.action}"
    padding: "0.85rem 1.3rem"
  button-dark-hover:
    backgroundColor: "{colors.cobalt}"
    textColor: "{colors.white}"
  verification-control:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.data-label}"
    padding: "0.6rem 0.85rem"
  verification-control-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
---

# Design System: FaceLogix Calibration Record

## Overview

**Creative North Star: "Calibration Record"**

FaceLogix presents verification as an inspectable record rather than a biometric spectacle or a generic software dashboard. Cold paper surfaces, graphite key lines, cobalt registration fields, measurement labels, and exact typography make the interface feel controlled, operational, and technically credible.

The reusable system is the material and behavioral grammar: cold paper, one-pixel rules, square registration geometry, compressed display type, monospaced data labels, explicit state color, and short verification motion. The shipped landing route composes that grammar into a split hero, three-step workflow, deployment map, retention diagram, capability ledger, and repository close; those narrative arrangements are route-specific and are not templates for product screens.

**Key Characteristics:**
- Cold calibration paper with a faint two-rem registration grid
- Graphite typography and one-pixel structural key lines
- Cobalt reserved for registration, action, and active verification
- Sharp corners and square measurement marks throughout
- Large compressed headlines paired with exact monospaced labels
- State changes shown as a readable verification trace, never as spectacle

## Colors

The palette is nearly achromatic and paper-led; saturated color appears only where the record needs registration, action, success, or warning.

### Primary
- **Registration Cobalt** (`cobalt`): Primary actions, scan grids, scan traces, navigation rules, section fields, and active workflow markers.
- **Deep Cobalt** (`cobalt-dark`): Cobalt hover states, compact record identifiers, and the mobile repository link.
- **Pale Registration** (`cobalt-pale`): Stored-data fields and quiet cobalt-tinted supporting surfaces.

### Secondary
- **Verified Green** (`signal`): The completed verification index and trace. Use only for a confirmed successful state.

### Tertiary
- **Retention Red** (`error`): The explicit source-image discard notice. Use for destructive or non-retention warnings, not general emphasis.

### Neutral
- **Calibration Paper** (`paper`): Page canvas, sticky navigation veil, control cutouts, and anchor fills.
- **Deep Calibration Paper** (`paper-deep`): Inset scan field, closing field, and scrollbar track.
- **Graphite Ink** (`ink`): Primary copy, key lines, dark actions, and structural connectors.
- **Muted Graphite** (`muted`): Supporting copy and secondary measurement text.
- **Key Line** (`line`): Secondary dividers and disabled control borders.
- **Soft Key Line** (`line-soft`): Mobile menu row separators.
- **Instrument White** (`white`): Raised record surfaces and reversed text.

**The Registration Rule.** Cobalt identifies action, active measurement, or a deliberately bounded field; it does not wash ordinary paper sections.

**The State Color Rule.** Green means verified and red means a concrete retention warning. Neither color is decorative.

## Typography

**Display Font:** Archivo Variable (with Helvetica Neue and sans-serif fallbacks)  
**Body Font:** Archivo Variable (with Helvetica Neue and sans-serif fallbacks)  
**Label/Mono Font:** IBM Plex Mono (with Cascadia Mono, Roboto Mono, and monospace fallbacks)

**Character:** Archivo carries both blunt operational copy and tightly compressed display statements, using its variable weight range for precise hierarchy. The monospaced stack marks identifiers, measurements, node types, and process labels; it reads as instrumentation rather than developer decoration.

### Hierarchy
- **Display** (weight 790, `clamp(4.3rem, 7vw, 7.7rem)`, line-height 0.87, tracking -0.04em): Hero promise only, balanced and constrained to an 8ch measure.
- **Headline** (weight 770, `clamp(2.8rem, 5.5vw, 5.6rem)`, line-height 0.96, tracking -0.04em): Major section statements.
- **Title** (weight 700, `clamp(1.45rem, 2.2vw, 2rem)`, line-height 1.05): Workflow titles; smaller cards use observed fixed sizes from 1.15rem to 1.25rem.
- **Body** (weight 400, 1rem, line-height 1.55): Default explanatory copy. Lead copy grows fluidly to 1.2rem or 1.3rem and stays between 35rem and 47rem wide where the route establishes a measure.
- **Action** (weight 730, 1rem, line-height 1.55): Primary and dark calls to action. Compact header actions use weight 700 at 0.8rem.
- **Data Label** (weight 700, 0.58rem–0.7rem, tracking 0.05em–0.12em, uppercase): Record headers, workflow markers, node types, connectors, measurement labels, and ledger categories.

**The Instrument Label Rule.** Use the mono face only for identifiers, states, categories, and measured system facts; prose remains Archivo.

**The Compression Rule.** Large headlines use negative tracking and short measures. Do not reproduce display compression in body copy.

## Layout

The reusable frame is a centered maximum width of 94rem with a fluid horizontal gutter and generous section blocks. A fixed two-rem grid sits faintly under the paper, while visible content aligns through explicit CSS grids, zero-gap ledgers, and one-pixel connecting rules. Reusable controls use a 1.5rem action gap; section spacing expands fluidly from 6rem to 11rem.

The landing route starts with a two-column hero whose right record has a 32rem minimum width, then changes its ratios at 68rem. At 52rem, the header swaps desktop navigation and action for a native `details` menu; the hero, architecture, privacy, closing, ledger, and footer become single-column; the workflow becomes a vertical measured track. At 30rem, hero actions stack, the verification control takes a full row, and measurement labels wrap. Architecture connectors and the retention path rotate from horizontal to vertical before the primary content stack.

**The Record Grid Rule.** Use layout lines to explain adjacency, order, or containment. Decorative boxes without a record function do not belong to this system.

**The Route Boundary Rule.** The split hero, workflow track, architecture map, retention diagram, capability ledger, and closing composition tell this landing route's story. Reuse their tokens and geometry, not their exact page sequence.

## Elevation & Depth

The system is flat and line-defined by default. Paper tone, reversed cobalt fields, and one-pixel borders carry most depth. The verification record is the single lifted surface, using a hard-offset ambient shadow; its moving scan line alone receives a cobalt glow. The sticky header uses a translucent paper field with a 12px backdrop blur, while focus depth is a two-stage paper-and-cobalt ring rather than a soft shadow.

### Shadow Vocabulary
- **Verification Record Lift** (`1.1rem 1.1rem 2.75rem rgb(49 67 61 / 0.13)`): Only the hero verification record floats above the paper.
- **Scan Trace Glow** (`0 0.5rem 1.2rem rgb(30 91 255 / 0.24)`): Only the animated one-pixel scan trace.
- **Focus Ring** (`0 0 0 3px var(--paper), 0 0 0 6px var(--cobalt)`): Keyboard focus on links, buttons, and menu summaries.

**The Flat Record Rule.** Surfaces stay flat unless a lifted verification instrument or an interaction state requires separation.

## Shapes

All visible controls, cards, menu fields, nodes, markers, and registration marks are square; the shipped CSS declares no border radii. Structural geometry uses one-pixel graphite or contextual white borders. The wordmark is a 1.55rem square with four inset corner marks, verification anchors are eight-pixel squares, and the hero record carries a 4.7rem by 1.2rem cobalt registration tab offset above its frame.

Grids are functional: the page uses a faint graphite two-rem grid, and the scan field uses a faint cobalt two-rem grid. Arrowheads, path lines, and border breaks communicate flow without introducing rounded pills or ornamental silhouettes.

**The Sharp Instrument Rule.** Preserve square corners and one-pixel key lines across every component in this visual world.

## Components

Components share square corners, one-pixel borders, strong weight contrast, and visible keyboard focus. Repository actions use short ease-out state changes, navigation links reveal a measured rule, and active controls move down one pixel.

### Buttons
- **Shape:** Square, with a minimum height of 3.2rem, 0.85rem by 1.3rem padding, and a transparent one-pixel border that preserves geometry.
- **Primary:** Registration cobalt with instrument white text; hover moves to deep cobalt over 160ms ease-out.
- **Dark:** Graphite ink with instrument white text and a 13rem minimum width on the closing action; hover moves to cobalt over 160ms ease-out.
- **Compact Header Action:** Graphite ink with instrument white text, a graphite border, and 0.7rem by 1rem padding; hover moves to cobalt over 150ms ease-out.
- **Focus / Active:** Apply the shared focus ring on `:focus-visible`; active state translates down one pixel.

### Cards / Containers
- **Corner Style:** Square, with one-pixel key lines.
- **Background:** Instrument white for verification and retention records, calibration paper for workflow markers, pale registration for stored representation, and low-alpha cobalt-dark over cobalt for architecture nodes.
- **Shadow Strategy:** Flat by default; only the verification record uses Verification Record Lift.
- **Internal Padding:** Record rows use 0.8rem–1rem, map nodes use 1.15rem, and retention items use 1.25rem.

### Navigation
- **Desktop:** A sticky 4.5rem rail with wordmark left, centered uppercase section links, and a right control group containing the language switch and dark repository action. Link rules reveal from left to right over 180ms ease-out.
- **Mobile:** At 52rem and below, the rail becomes 4rem high and exposes a bordered `details` summary. The open menu spans the rail width, uses one-rem link rows, includes the language switch after the repository link, and closes after a link or language is selected.
- **Focus:** Wordmark, links, action, menu summary, and both language buttons receive the shared visible focus ring.

### Language Switch
- **Structure:** Two square 2.25rem cells inside one graphite key line. Labels use the data face at 0.68rem and a 2.35rem minimum height.
- **State:** The selected language uses registration cobalt with white text and `aria-pressed="true"`; the unselected language stays transparent and moves to deep calibration paper on hover.
- **Behavior:** Desktop and mobile controls remain synchronized. A selection updates page copy, document language, metadata, verification state, the shareable URL, and local preference without reloading.

### Verification Control
- **Style:** A transparent, square button with a one-pixel graphite border, a 2.6rem minimum height, 0.6rem by 0.85rem padding, and a 6.4rem minimum width.
- **Hover / Disabled:** Hover reverses to graphite with white text. Disabled state uses key-line and muted colors with a wait cursor.
- **State:** The adjacent polite live region moves from ready, through checking liveness, to attendance recorded; the letter index changes from A to B to C.

### Verification Record
- **Structure:** A lifted white frame with mono header, deep-paper scan field, one-pixel scan trace, live state row, and measurement row.
- **Motion:** Scan moves from 8% to 92% over 1.8s using `cubic-bezier(0.22, 1, 0.36, 1)`. The normal completion delay is 1850ms.
- **Reduced Motion:** The scan animation and transitions collapse to 0.01ms and one iteration; the verification completion delay becomes 120ms.
- **State Color:** Cobalt marks ready and scanning; verified green replaces it only after confirmation.

### Workflow Markers and Data Nodes
- **Markers:** 6.8rem by 3.1rem square labels sit directly on the workflow rule; only the active verification step is cobalt-filled.
- **Architecture Nodes:** Minimum 9rem high with 1.15rem padding, a translucent dark-cobalt field, and an 80%-white key line.
- **Retention Items:** Minimum 11rem high with 1.25rem padding. The stored representation uses pale registration; the discard note uses a retention-red border and text.

### Accessibility Conventions
- Use semantic landmarks, ordered workflow structure, real links and buttons, labelled diagrams, and heading relationships through `aria-labelledby`.
- Keep illustrative canvas and decorative grids hidden from assistive technology; expose verification text through `aria-live="polite"`.
- Preserve the skip link, keyboard-operable native mobile menu, shared focus ring, forced-color borders, and reduced-motion branch.

## Do's and Don'ts

### Do:
- **Do** build from cold paper, graphite one-pixel rules, square fields, and measured alignment.
- **Do** reserve cobalt for action, registration, active verification, and bounded technical fields.
- **Do** pair compressed Archivo headlines with monospaced identifiers and measurement labels.
- **Do** turn horizontal diagrams into readable vertical flows at the established responsive thresholds.
- **Do** preserve keyboard focus, reduced motion, forced-color borders, semantic structure, and live verification text.

### Don't:
- **Don't** round buttons, cards, nodes, markers, or menu fields.
- **Don't** add ambient shadows to ordinary surfaces; the lifted verification record and scan trace are the observed exceptions.
- **Don't** use green or red as decoration or generic emphasis.
- **Don't** replace registration grids and key lines with soft decorative color gradients.
- **Don't** treat the landing route's split hero, diagrams, ledger, or section sequence as universal application layouts.
