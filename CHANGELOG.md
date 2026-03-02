# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
