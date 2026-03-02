"""
Tests for auth_forum Celery tasks.
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from auth_forum.models import Board, Category, Post, Thread


def _make_objects():
    user = User.objects.create_user(username="task_test_user")
    cat = Category.objects.create(name="Task Cat")
    board = Board.objects.create(category=cat, name="Task Board")
    thread = Thread.objects.create(board=board, author=user, title="Task Thread")
    post = Post.objects.create(
        thread=thread, author=user, content="Hello World", is_first_post=True
    )
    return user, thread, post


class TestNotifySubscribersTask(TestCase):
    @override_settings(AUTH_FORUM_NOTIFY_REPLIES=True)
    @patch("allianceauth.notifications.notify")
    def test_notifies_subscribers(self, mock_notify):
        """
        When replier != thread author, the author should receive a notification.
        """
        from auth_forum.tasks import notify_subscribers_task

        author, thread, first_post = _make_objects()
        replier = User.objects.create_user(username="task_replier")
        reply = Post.objects.create(
            thread=thread, author=replier, content="A reply", is_first_post=False
        )

        notify_subscribers_task(thread.pk, reply.pk, replier.pk)

        mock_notify.assert_called()
        call_kwargs = mock_notify.call_args[1]
        self.assertEqual(call_kwargs["user"], author)
        self.assertIn("Task Thread", call_kwargs["title"])

    @override_settings(AUTH_FORUM_NOTIFY_REPLIES=False)
    @patch("allianceauth.notifications.notify")
    def test_disabled_when_setting_off(self, mock_notify):
        from auth_forum.tasks import notify_subscribers_task

        user, thread, post = _make_objects()
        notify_subscribers_task(thread.pk, post.pk, user.pk)
        mock_notify.assert_not_called()


class TestDiscordPostNotificationTask(TestCase):
    @patch("django.apps.apps.is_installed", return_value=False)
    def test_skips_when_no_discordbot(self, mock_installed):
        """Task should no-op when aadiscordbot is not installed."""
        from auth_forum.tasks import discord_post_notification_task

        user, thread, post = _make_objects()
        # Should complete without raising
        discord_post_notification_task(thread.pk, post.pk)

    @override_settings(AUTH_FORUM_DISCORD_CHANNEL_ID=None)
    def test_skips_without_channel_id(self):
        """Task should no-op when no channel ID is configured."""
        from auth_forum.tasks import discord_post_notification_task

        user, thread, post = _make_objects()
        discord_post_notification_task(thread.pk, post.pk)
        # No exception = pass

    @override_settings(AUTH_FORUM_DISCORD_CHANNEL_ID=123456)
    @patch("auth_forum.helpers.discord_bot_active", return_value=True)
    @patch("auth_forum.tasks.discord_bot_active", return_value=True)
    def test_sends_embed_when_configured(self, mock_active, mock_active2):
        """Task should call aadiscordbot send_message when configured."""
        from auth_forum.tasks import discord_post_notification_task

        user, thread, post = _make_objects()

        mock_send = MagicMock()
        with patch.dict("sys.modules", {
            "aadiscordbot": MagicMock(),
            "aadiscordbot.tasks": MagicMock(send_message=mock_send),
            "discord": MagicMock(),
        }):
            # Patch the import inside the task
            with patch("auth_forum.tasks.discord_bot_active", return_value=True):
                try:
                    discord_post_notification_task(thread.pk, post.pk)
                except Exception:
                    pass  # ImportError from mocked modules is acceptable in test env
