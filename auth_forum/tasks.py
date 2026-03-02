"""
Celery tasks for auth_forum.

- notify_subscribers_task: fires Alliance Auth bell notifications to thread subscribers.
- discord_post_notification_task: optionally sends a Discord embed (requires aadiscordbot).
"""

from celery import shared_task
from allianceauth.services.hooks import get_extension_logger

from .app_settings import AUTH_FORUM_NOTIFY_REPLIES, AUTH_FORUM_DISCORD_CHANNEL_ID
from .helpers import discord_bot_active

logger = get_extension_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_subscribers_task(self, thread_pk: int, post_pk: int, actor_pk: int):
    """
    Send an Alliance Auth bell notification to every subscriber of the thread
    when a new post is made.

    Subscribers = thread author + anyone who has previously posted in the thread,
    excluding the user who just posted (*actor_pk*).
    """
    if not AUTH_FORUM_NOTIFY_REPLIES:
        return

    try:
        from django.contrib.auth.models import User
        from allianceauth.notifications import notify

        from .models import Thread, Post
        from .helpers import get_thread_subscribers

        post = Post.objects.select_related("thread", "author").get(pk=post_pk)
        thread = post.thread
        actor = User.objects.get(pk=actor_pk)

        subscribers = get_thread_subscribers(thread, exclude_user=actor)

        for user in subscribers:
            notify(
                user=user,
                title=f"New reply in: {thread.title}",
                message=(
                    f"{actor.username} replied to \"{thread.title}\" "
                    f"in {thread.board.name}."
                ),
                level="info",
            )

        logger.debug(
            "Notified %d subscriber(s) for thread pk=%d", subscribers.count(), thread_pk
        )

    except Exception as exc:
        logger.exception("notify_subscribers_task failed for post_pk=%d", post_pk)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def discord_post_notification_task(self, thread_pk: int, post_pk: int):
    """
    Send a Discord embed to AUTH_FORUM_DISCORD_CHANNEL_ID when a new thread or
    reply is posted. Only fires when aadiscordbot is installed **and**
    AUTH_FORUM_DISCORD_CHANNEL_ID is configured.
    """
    if not discord_bot_active():
        return
    if not AUTH_FORUM_DISCORD_CHANNEL_ID:
        return

    try:
        from .models import Post
        from aadiscordbot.tasks import send_message  # type: ignore
        from discord import Embed, Color  # type: ignore

        post = Post.objects.select_related("thread__board", "author").get(pk=post_pk)
        thread = post.thread

        author_name = post.author.username if post.author else "Unknown"
        try:
            main_char = post.author.profile.main_character
            author_name = main_char.character_name if main_char else author_name
        except Exception:
            pass

        verb = "started a new thread" if post.is_first_post else "replied"

        embed = Embed(
            title=thread.title,
            description=post.content[:500] + ("…" if len(post.content) > 500 else ""),
            color=Color.blue(),
        )
        embed.set_author(name=author_name)
        embed.add_field(name="Board", value=thread.board.name, inline=True)
        embed.add_field(name="Action", value=verb, inline=True)
        embed.set_footer(text="Alliance Auth Forum")

        send_message(channel_id=AUTH_FORUM_DISCORD_CHANNEL_ID, embed=embed)
        logger.debug(
            "Sent Discord notification for post_pk=%d to channel %d",
            post_pk,
            AUTH_FORUM_DISCORD_CHANNEL_ID,
        )

    except Exception as exc:
        logger.exception("discord_post_notification_task failed for post_pk=%d", post_pk)
        raise self.retry(exc=exc)
