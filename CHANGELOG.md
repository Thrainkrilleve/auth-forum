# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
