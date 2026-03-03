from django.conf import settings

# Number of posts displayed per page on the thread view
AUTH_FORUM_POSTS_PER_PAGE = getattr(settings, "AUTH_FORUM_POSTS_PER_PAGE", 20)

# Number of threads displayed per page on the board view
AUTH_FORUM_THREADS_PER_PAGE = getattr(settings, "AUTH_FORUM_THREADS_PER_PAGE", 25)

# Minimum characters required to trigger a search
AUTH_FORUM_SEARCH_MIN_LENGTH = getattr(settings, "AUTH_FORUM_SEARCH_MIN_LENGTH", 3)

# Send Alliance Auth bell notifications when someone replies to a thread you posted in
AUTH_FORUM_NOTIFY_REPLIES = getattr(settings, "AUTH_FORUM_NOTIFY_REPLIES", True)

# Send Alliance Auth bell notifications when someone reacts to your post
AUTH_FORUM_NOTIFY_REACTIONS = getattr(settings, "AUTH_FORUM_NOTIFY_REACTIONS", True)

# Optional: Discord channel ID to post new thread announcements to (requires aadiscordbot)
AUTH_FORUM_DISCORD_CHANNEL_ID = getattr(settings, "AUTH_FORUM_DISCORD_CHANNEL_ID", None)

# Giphy API key for the GIF picker in the post editor
AUTH_FORUM_GIPHY_API_KEY = getattr(settings, "AUTH_FORUM_GIPHY_API_KEY", "lyLrhIGwjOxCC9KdPgizXFQY1x3KsfJy")

# Image paste/drag upload — disabled by default; set MEDIA_ROOT + MEDIA_URL in Django settings
AUTH_FORUM_UPLOAD_ENABLED = getattr(settings, "AUTH_FORUM_UPLOAD_ENABLED", False)
# Maximum upload size in bytes (default 5 MB)
AUTH_FORUM_UPLOAD_MAX_SIZE = getattr(settings, "AUTH_FORUM_UPLOAD_MAX_SIZE", 5 * 1024 * 1024)

# Notify users when they are @mentioned in a post
AUTH_FORUM_NOTIFY_MENTIONS = getattr(settings, "AUTH_FORUM_NOTIFY_MENTIONS", True)

# Notify board subscribers when a new thread is created
AUTH_FORUM_NOTIFY_BOARD_SUBSCRIBERS = getattr(settings, "AUTH_FORUM_NOTIFY_BOARD_SUBSCRIBERS", True)
