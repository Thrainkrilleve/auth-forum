# Alliance Auth Forum

A full-featured forum plugin for [Alliance Auth](https://gitlab.com/allianceauth/allianceauth) (AA). Built for EVE Online alliances and corporations.

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![Django](https://img.shields.io/badge/django-4.2+-blue)
![Alliance Auth](https://img.shields.io/badge/allianceauth-4.0+-blue)

## Features

- **Categories & Boards**  Organise discussions into categories and boards
- **Per-Board Access Control**  Restrict boards to specific Alliance Auth groups or member states
- **Thread Locking & Pinning**  Moderators can lock or pin threads
- **Unread Tracking**  Threads show an unread badge until the user visits them
- **EVE Character Avatars**  Portrait, corporation, and alliance displayed on every post
- **Post Reactions**  5 emoji reactions (👍 o7 😂 😮 🔥) on every post; AA bell notification sent to post author
- **Thread Subscriptions**  Subscribe/unsubscribe per thread; auto-subscribed on first post or reply; AA bell on new replies
- **Polls**  Optional poll on any new thread with single or multi-choice voting and optional close date
- **Markdown Rendering**  Full Markdown support via `mistune` — headers, lists, tables, code fences, strikethrough; custom `[img]` and `[quote]` tags preserved
- **AA Bell Notifications**  Subscribers are notified via the Alliance Auth notification bell on new replies and reactions
- **Discord Integration**  Optional: posts new threads/replies to a Discord channel via `aadiscordbot` (never a hard dependency)
- **GDPR / AVOID_CDN Ready**  All CSS and JS are served as local static files  zero CDN references
- **Django Admin**  Full admin interface with bulk lock/pin/unpin actions
- **Bootstrap 5 Themes**  Inherits your Alliance Auth theme automatically (Darkly, Flatly, Materia, etc.)

## Installation

### Requirements

- Alliance Auth >= 4.0.0
- Python >= 3.10
- Django >= 4.2
- [mistune](https://github.com/lepture/mistune) >= 3.0.0 *(installed automatically as a dependency)*

### Step 1  Install the Package

**Docker:**
```bash
docker compose exec allianceauth_gunicorn bash
pip install git+https://github.com/Thrainkrilleve/auth-forum.git
```

**Systemd / bare metal:**
```bash
pip install git+https://github.com/Thrainkrilleve/auth-forum.git
```

### Step 2  Configure Alliance Auth

Add `auth_forum` to `INSTALLED_APPS` in your `local.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    "auth_forum",
]
```

### Step 3  Run Migrations

Migrations are pre-built and ship with the package. You do **not** need to run `makemigrations`.

```bash
# Alliance Auth shortcut
auth migrate

# or manually
python manage.py migrate auth_forum
```

### Step 4  Collect Static Files

```bash
auth collectstatic --noinput

# or manually
python manage.py collectstatic --noinput
```

### Step 5  Restart Services

Restart your Alliance Auth services.

### Step 6  Configure Permissions

Grant permissions via the Alliance Auth admin panel (`/admin`) → **Auth** → **Groups** → assign to the relevant group(s).

There are three permissions. Assign them based on the role breakdown below.

---

#### `auth_forum.basic_access`  Standard User / Member

Grant this to every member who should be able to use the forum.

| Capability | Details |
|---|---|
| View the forum index | Sees all visible categories and boards they have access to |
| Read threads | Can open any thread in a board they have access to |
| Create new threads | Can start a new thread in any board they have access to |
| Reply to threads | Can post replies to open (unlocked) threads |
| Edit own posts | Can edit their own posts at any time |
| Delete own posts | Can delete their own posts |
| Subscribe / unsubscribe | Receives AA bell notifications on new replies to threads they participate in |
| Search | Can use the forum search |
| Per-board access control | If a board is restricted to specific **groups** or **states**, the user must also be in one of those groups/states to see and enter that board |

> **Tip:** A user without `basic_access` cannot see the forum at all — the menu item and all forum URLs are blocked.

---

#### `auth_forum.manage_forum`  Moderator / Forum Admin

Grant this to officers, directors, or anyone who should be able to moderate and manage forum structure. This permission **includes everything** `basic_access` provides, plus:

| Capability | Details |
|---|---|
| All `basic_access` actions | Everything listed above |
| Lock / unlock threads | Prevents normal users from replying to a thread |
| Pin / unpin threads | Keeps a thread at the top of the board thread list |
| Edit any post | Can edit posts written by any user |
| Delete any post | Can delete posts written by any user |
| See hidden categories | Hidden categories (marked **is_hidden** in admin) are visible to moderators |
| See hidden boards | Hidden boards are visible to moderators regardless of group/state restrictions |
| Bypass board access control | Full bypass — same as `bypass_board_restrictions` below, plus also sees hidden boards |
| Create categories | Can add new top-level categories directly from the forum index page |
| Edit categories | Can rename/reorder/hide categories from the forum index page |
| Delete categories | Can delete a category and all its boards/threads/posts |
| Create boards | Can add new boards to any category from the forum index page |
| Edit boards | Can change a board's name, description, order, visibility, and access restrictions |
| Delete boards | Can delete a board and all its threads/posts |

> **Tip:** `manage_forum` does **not** imply Django superuser or Django admin access. It only affects what the user can do inside the forum plugin itself.

---

#### `auth_forum.bypass_board_restrictions`  Alliance-wide / Cross-board Access

Grant this to members who should be able to read all boards regardless of per-board group or state restrictions, **without** giving them full moderator powers.

| Capability | Details |
|---|---|
| All `basic_access` actions | Everything a standard member can do |
| Bypass board group/state restrictions | Can enter any board even if the board is restricted to specific groups or states they don't belong to |

> **Tip:** This permission does **not** reveal hidden boards (those require `manage_forum`), and does **not** grant any moderation capabilities (lock/pin/delete/manage). It is purely an access bypass.

## Updating

### Systemd / bare metal

```bash
pip install --upgrade git+https://github.com/Thrainkrilleve/auth-forum.git
auth migrate
auth collectstatic --noinput
supervisorctl restart myauth:
```

### Docker

```bash
docker compose exec allianceauth_gunicorn bash
pip install --upgrade git+https://github.com/Thrainkrilleve/auth-forum.git
auth migrate
auth collectstatic --noinput
exit
docker compose restart
```

### After Updating

1. Check [CHANGELOG.md](CHANGELOG.md) for any breaking changes
2. Run `auth migrate` in case new migrations were added
3. Run `auth collectstatic --noinput` to pick up updated static files

## Configuration

Add any of the following to your `local.py` to override defaults:

```python
# Number of posts shown per page on a thread (default: 20)
AUTH_FORUM_POSTS_PER_PAGE = 20

# Number of threads shown per page on a board (default: 25)
AUTH_FORUM_THREADS_PER_PAGE = 25

# Minimum search query length in characters (default: 3)
AUTH_FORUM_SEARCH_MIN_LENGTH = 3

# Send AA bell notifications to thread subscribers on new replies (default: True)
AUTH_FORUM_NOTIFY_REPLIES = True

# Send AA bell notifications to post authors when their post receives a reaction (default: True)
AUTH_FORUM_NOTIFY_REACTIONS = True

# Discord channel ID to post new thread / reply notifications to.
# Requires aadiscordbot to be installed. Leave None to disable.
AUTH_FORUM_DISCORD_CHANNEL_ID = None
```

### Discord Integration (Optional)

Install `aadiscordbot` and set the channel ID:

```bash
pip install git+https://github.com/pvyParts/allianceauth-discordbot.git
```

```python
# local.py
AUTH_FORUM_DISCORD_CHANNEL_ID = 123456789012345678  # your channel snowflake ID
```

The forum will never hard-require `aadiscordbot`  all Discord features degrade gracefully if it is not installed.

### GDPR / AVOID_CDN

The forum ships with all assets (CSS, JavaScript, fonts) as local static files. No external CDN calls are made. Setting `AVOID_CDN = True` in your `local.py` is fully supported out of the box.

## Development

### Set Up a Development Environment

```bash
# Clone the repo
git clone https://github.com/Thrainkrilleve/auth-forum.git
cd auth-forum

# Install in editable mode
pip install -e .

# Install dev dependencies
pip install -e .[dev]

# Enable pre-commit hooks
pre-commit install
```

### Running Tests

```bash
python runtests.py
```

Or with tox for all environments:

```bash
pip install tox
tox -l          # list available environments
tox -e py311-django42
```

### Code Style

This project uses:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **pylint** (via tox) for deeper static analysis

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes and add tests
4. Submit a pull request

## License

This project is licensed under the MIT License  see [LICENSE](LICENSE) for details.

## Credits

- Built for [Alliance Auth](https://gitlab.com/allianceauth/allianceauth)
- EVE Online and the EVE logo are the registered trademarks of CCP hf.

## Support

For issues, questions, or feature requests please use the [GitHub issue tracker](https://github.com/Thrainkrilleve/auth-forum/issues).
