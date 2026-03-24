# Nano Atoms Extension Capabilities PRD

## 1. Objective

Nano Atoms should not stop at “generate one version of an app”. The upgraded product should:

1. improve first-pass quality,
2. support controlled iteration on top of an existing version,
3. make generation outcomes more explainable and repairable.

This document defines the extension capabilities beyond the current baseline product.

## 2. Product Positioning

Compared with a generic AI app generator, Nano Atoms should emphasize:

- better result accountability,
- faster follow-up iteration,
- clearer visibility into what the system fixed or still recommends.

## 3. Extension Capabilities

### 3.1 Quality Guardian

Status: implemented in this iteration.

Quality Guardian runs after the main generation flow and before the version is marked complete.

Core responsibilities:

- inspect renderability and export completeness,
- check whether the page has enough high-value layout blocks,
- record preview repairs and image handling results,
- apply soft polish when the result is structurally too weak,
- output a quality report with score, checks, repairs, and next-step suggestions.

User-facing value:

- users can see whether the version is stable,
- the system becomes self-healing instead of only error-reporting,
- the workspace can guide the next iteration with concrete prompts.

### 3.2 Scoped Iteration

Status: implemented in this iteration.

Scoped iteration lets users refine only part of the current app instead of regenerating everything.

Supported scopes:

- full
- hero
- landing
- auth
- data
- style

Behavior:

- the frontend exposes scope chips in the workspace chat panel,
- the backend builds a scope-aware prompt using the latest schema summary,
- the model is instructed to keep unaffected areas stable.

User-facing value:

- lower iteration cost,
- less accidental regression,
- more usable “conversation-based editing”.

### 3.3 Brief Clarifier

Status: planned.

Brief Clarifier should enrich underspecified prompts before the Product and Design Director stages. It will infer target users, page intent, and likely flows when the prompt is too short.

### 3.4 Brand / Asset Driven Generation

Status: partially implemented in this iteration.

This capability allows users to upload project assets and references so the generator can use them as grounded context.

Currently implemented:

- project-level asset upload and management,
- support for images, PDF, CSV, TXT, JSON, and office files,
- automatic inclusion of uploaded assets in generation prompt context,
- automatic reuse of uploaded image assets in visual slots when possible.

Planned next:

- explicit logo / palette extraction,
- reference-site parsing,
- form field generation from uploaded structured files.

## 4. Functional Flow

### Generation Flow

1. User submits prompt.
2. Product and Design Director define structure and quality direction.
3. Architect, UI Builder, Code, Media, and QA generate the app.
4. Quality Guardian evaluates the output, applies soft polish, and produces a report.
5. Workspace shows preview, files, and quality feedback.

### Iteration Flow

1. User selects a scope in workspace chat.
2. Backend summarizes the current schema.
3. System builds a scoped iteration prompt.
4. New version is generated while preserving unaffected areas as much as possible.

## 5. Acceptance Criteria

- Every completed version includes a quality report.
- Workspace displays quality score, repairs, and next-step suggestions.
- Users can trigger scoped iteration from the chat panel.
- Scoped iteration requests include current-version context on the backend.
- Existing build and preview flows remain available.

## 6. Delivery Plan

### P0

- Quality Guardian
- Scoped Iteration

### P1

- Brief Clarifier
- richer quality checks for forms, tables, and navigation

### P2

- richer Brand / Asset Driven Generation
- upload-based business context extraction
