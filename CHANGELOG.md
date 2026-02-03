# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0](https://github.com/AlteredCraft/chat-rag-explorer/compare/chat-rag-explorer-v0.1.0...chat-rag-explorer-v0.2.0) (2026-02-03)


### Features

* add Release Please for automated versioning and changelog ([1bbca36](https://github.com/AlteredCraft/chat-rag-explorer/commit/1bbca367e59da1e73b0cd2b38fa5eb78389705fd))

## [Unreleased]

### Features

- About page (`/about`) with project overview, tech stack, features, and architecture
- About link in sidebar header next to Settings
- Highlighted "Inspect Request Details" feature in README and About page with screenshots
- Workshop calendar link (lu.ma) showing past deliveries
- Educational info box on Settings page showing `.models_list` file status
- Info box displays whether file exists and count of configured models
- Link to openrouter.ai/models for browsing available models
- Conditional "Show free models only" filter - only displays when free models exist
- Unit tests for `get_models_list_status()` function
- IBM Plex Sans and Plex Mono fonts for improved typography
- CSS design tokens for consistent spacing, shadows, and transitions
- Skip link for keyboard navigation (accessibility)
- ARIA landmarks, roles, and live regions throughout HTML
- Focus-visible states on all interactive elements
- Mobile responsive layout with bottom drawer sidebar
- Hamburger menu toggle for mobile navigation
- Message slide-in animations and modal transitions

### Changed

- **Renamed project from "Chat RAG Explorer" to "RAG Lab"**
- Bolder header title with orange accent on "RAG"
- Model Selection UI now educates users about model list curation
- Primary accent color changed from blue to warm orange (#ea580c)
- Help icons converted to buttons with 44px touch targets (WCAG compliance)
- Sidebar now scrollable to access all sections including RAG
- Settings tabs horizontally scrollable on mobile
- Info box styling aligned with orange accent theme

## [0.1.0] - 2026-02-02

### Changed

- Decouple logging setup from Flask for early initialization (08376aa)

## [0.0.1] - 2026-02-01

### Changed

- Copy sample ChromaDB to working directory on startup (1fddf02)
- Re-chunked morn at 256 (1eb76d1)
