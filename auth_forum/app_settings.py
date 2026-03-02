from django.conf import settings

# Number of posts displayed per page on the thread view
AUTH_FORUM_POSTS_PER_PAGE = getattr(settings, "AUTH_FORUM_POSTS_PER_PAGE", 20)

# Number of threads displayed per page on the board view
AUTH_FORUM_THREADS_PER_PAGE = getattr(settings, "AUTH_FORUM_THREADS_PER_PAGE", 25)

# Minimum characters required to trigger a search
AUTH_FORUM_SEARCH_MIN_LENGTH = getattr(settings, "AUTH_FORUM_SEARCH_MIN_LENGTH", 3)

# Send Alliance Auth bell notifications when someone replies to a thread you posted in
AUTH_FORUM_NOTIFY_REPLIES = getattr(settings, "AUTH_FORUM_NOTIFY_REPLIES", True)

# Optional: Discord channel ID to post new thread announcements to (requires aadiscordbot)
AUTH_FORUM_DISCORD_CHANNEL_ID = getattr(settings, "AUTH_FORUM_DISCORD_CHANNEL_ID", None)
