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
- **AA Bell Notifications**  Subscribers are notified via the Alliance Auth notification bell on new replies
- **Discord Integration**  Optional: posts new threads/replies to a Discord channel via `aadiscordbot` (never a hard dependency)
- **GDPR / AVOID_CDN Ready**  All CSS and JS are served as local static files  zero CDN references
- **Django Admin**  Full admin interface with bulk lock/pin/unpin actions
- **Bootstrap 5 Themes**  Inherits your Alliance Auth theme automatically (Darkly, Flatly, Materia, etc.)

## Installation

### Requirements

- Alliance Auth >= 4.0.0
- Python >= 3.10
- Django >= 4.2

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

Grant permissions in Alliance Auth admin (`/admin`):

| Permission | Description |
|---|---|
| `auth_forum.basic_access` | Access the forum  read threads and post replies |
| `auth_forum.manage_forum` | Moderate the forum  lock/pin threads, delete any post |

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
