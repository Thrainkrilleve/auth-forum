# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.0] - 2026-03-03

### Added
- **Auto image loading** — bare image URLs (http/https ending in `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`) pasted directly into a post are automatically rendered as inline images without needing `[img]` tags
- **Giphy GIF picker** — new GIF button in all three editor toolbars (reply, new thread, edit post) opens a searchable Giphy modal; trending GIFs shown on open; click any GIF to insert it directly into the post
- `AUTH_FORUM_GIPHY_API_KEY` setting in `app_settings.py`

## [0.3.0] - 2026-03-01

### Added
- **Post Reactions** — 5 emoji reactions (👍 o7 😂 😮 🔥) on every post via inline mini-forms; reaction counts shown on buttons; active reaction highlighted; AA bell notification sent to post author on first reaction
- **Thread Subscriptions** — subscribe/unsubscribe button on thread pages; new replies send AA bell notifications to all subscribers; new thread author and repliers auto-subscribed on post
- **Polls** — optional poll when creating a new thread (question + up to 10 options, multi-choice toggle, optional close date); live vote tallies shown as percentage progress bars after voting; results locked after poll closes
- **Markdown rendering** via `mistune>=3.0.0` — full Markdown now rendered in posts (headers, lists, ordered lists, blockquotes, code fences, tables, strikethrough); falls back gracefully to regex renderer if mistune is not installed
- New `dict_get` template filter for accessing reaction count dicts from templates
- `AUTH_FORUM_NOTIFY_REACTIONS` setting (default `True`) to toggle reaction notifications
- New models: `PostReaction`, `ThreadSubscription`, `Poll`, `PollOption`, `PollVote`
- Migration `0003_reactions_polls_subscriptions` creates all new models

### Changed
- `forum_render` template filter now delegates to mistune for Markdown; `[img]` and `[quote]` custom blocks extracted before Markdown processing and restored after
- `get_thread_subscribers` helper now uses `ThreadSubscription` model as canonical source with backward-compatible fallback
- `mistune>=3.0.0` added as a runtime dependency

## [0.2.5] - 2026-03-01

### Added
- Image embedding support via `[img]https://...[/img]` tag — renders a responsive `<img>` element in posts
- New `templatetags/forum_tags.py` with `forum_render` filter that converts forum markup to safe HTML (XSS-safe via html.escape + allowlist)
- All formatting tags now rendered on display: `[img]`, `[quote]`, `[quote=Author]`, `**bold**`, `_italic_`, `` `code` ``
- Image toolbar button (\U0001f5bc) added to all three editor toolbars (reply, new thread, edit post)

### Fixed
- Post content no longer uses `white-space: pre-wrap` — line breaks now rendered as `<br>` tags via the filter

## [0.2.4] - 2026-03-01

### Added
- New permission `auth_forum.bypass_board_restrictions` — lets a user access boards regardless of per-board group/state restrictions without granting full moderator powers
- Migration `0002_bypass_board_restrictions_permission.py` creates the new permission in the DB
- README updated to document the new permission as a distinct third permission

## [0.2.3] - 2026-03-01

### Fixed
- Replaced all theme-dependent CSS variable backgrounds (`--forum-surface`, `--forum-surface-alt`) with a theme-agnostic `rgba(255,255,255,0.06)` tint — fixes white/light headers on thread list, post sidebar, reply box, quote blocks across all Bootstrap 5 themes including Darkly

## [0.2.2] - 2026-03-01

### Fixed
- Accordion category headers now correctly inherit the dark theme background (overrode Bootstrap's `--bs-accordion-btn-bg` variable which was defaulting to white)
- Management buttons (+, edit, delete) now sit inline inside the accordion header row instead of wrapping below it
- Post card sidebar and reply form header no longer show a light grey strip on dark themes (fixed `--forum-surface-alt` fallback colour)

## [0.2.1] - 2026-03-01

### Changed
- Expanded README permissions section with a full capability breakdown for `basic_access` and `manage_forum`

## [0.2.0] - 2026-03-01

### Added
- In-app category management — create, edit, and delete categories directly from the forum (requires `manage_forum` permission)
- In-app board management — create, edit, and delete boards with full access-control config (requires `manage_forum` permission)
- "New Category" and "New Board" buttons in the forum index header for moderators
- Per-category inline buttons: add board, edit, delete
- Per-board inline edit button on the index page
- Empty-state now shows "Create First Category" / "Create First Board" buttons for moderators
- Moderators bypass all board group/state restrictions and see hidden boards and categories
- `forms.py` with `CategoryForm` and `BoardForm`
- 8 new URL patterns for category/board management
- 4 new templates: `manage_category.html`, `manage_board.html`, `delete_category_confirm.html`, `delete_board_confirm.html`

## [0.1.0] - 2026-03-01

### Added
- Initial release of Alliance Auth Forum
- Categories, Boards, Threads, and Posts data models
- Per-board access control tied to Alliance Auth groups and member states
- Thread locking and pinning (requires `manage_forum` permission)
- Unread thread tracking per user
- EVE character portrait, corporation, and alliance display on posts
- Alliance Auth bell notifications for thread subscribers on new replies
- Optional Discord channel posting via `aadiscordbot` (soft dependency)
- Full Bootstrap 5 support with automatic theme inheritance
- GDPR / `AVOID_CDN` compliant  all static assets served locally
- Django admin with bulk lock/pin/unpin thread actions
- Celery tasks for async notifications
- Optional Discord slash commands cog (`/forum recent`, `/forum search`)
- Pre-built migrations  no `makemigrations` required after install
