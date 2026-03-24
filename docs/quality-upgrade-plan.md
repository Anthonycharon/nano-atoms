# Nano Atoms Quality Upgrade Plan

## Background

The current generation flow is stable enough to produce runnable apps, but the first-pass results still look like low-fidelity prototypes. The main issues are:

- The schema mostly relies on low-level atoms such as `card`, `text`, and `table`, so generated pages often feel assembled rather than designed.
- Visual guidance is too weak. The UI step mainly returns colors and font settings, but not a real art direction.
- The exported HTML/CSS runtime uses one generic visual system, which flattens different app types into the same look.

This iteration focuses on one target: improve the quality of generated applications.

## Goals

1. Raise the default visual quality of generated apps, especially landing pages, auth pages, and showcase-style experiences.
2. Improve structure quality so generated pages feel intentional, not placeholder-heavy.
3. Add at least one extension capability required by the assessment.

## Non-goals

- No race mode or multi-version competition workflow.
- No attempt to fully recreate atoms.dev.
- No major database schema migration.

## Extension Capability

This iteration adds a new derived capability: `Design Director`.

The `Design Director` agent turns the user request and PRD into a structured design brief:

- audience and experience goal
- visual direction
- layout density
- section recommendations
- quality checklist

This brief is then used by the architect and UI builder so the pipeline can generate better first-pass results.

## Planned Implementation

### 1. Quality-aware generation pipeline

- Insert `Design Director` between `Product` and `Architect`.
- Persist the generated design brief in the version payload for inspection and future iteration.

### 2. Richer schema building blocks

Add high-value composite components:

- `hero`
- `feature-grid`
- `stats-band`
- `split-section`
- `cta-band`
- `auth-card`

These components let the system generate polished layouts without overfitting every result to the same basic card stack.

### 3. Stronger visual system

- Extend `ui_theme` with canvas, surface, density, accent, and shadow tokens.
- Use those tokens in the preview renderer and static export renderer.

### 4. Renderer and export upgrade

- Render the new composite blocks in the React preview.
- Render the same blocks in exported HTML/CSS/JS output.
- Add image fallbacks for composite components that use hero visuals.

## Acceptance Criteria

- The agent flow includes the new `Design Director` step.
- New rich sections are supported in both preview and exported code.
- Landing and auth experiences render with stronger hierarchy and better first-pass polish.
- Existing generation flow still completes and build checks pass.
