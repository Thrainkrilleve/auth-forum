from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("auth_forum", "0002_bypass_board_restrictions_permission"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------ #
        #  PostReaction                                                        #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="PostReaction",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                (
                    "emoji",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("thumbsup", "👍"),
                            ("o7", "o7"),
                            ("laugh", "😂"),
                            ("wow", "😮"),
                            ("fire", "🔥"),
                        ],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reactions",
                        to="auth_forum.post",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="forum_reactions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Post Reaction",
                "verbose_name_plural": "Post Reactions",
            },
        ),
        migrations.AddConstraint(
            model_name="postreaction",
            constraint=models.UniqueConstraint(
                fields=["post", "user", "emoji"], name="unique_post_user_emoji"
            ),
        ),
        # ------------------------------------------------------------------ #
        #  ThreadSubscription                                                  #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="ThreadSubscription",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "thread",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscriptions",
                        to="auth_forum.thread",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="forum_subscriptions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Thread Subscription",
                "verbose_name_plural": "Thread Subscriptions",
                "unique_together": {("user", "thread")},
            },
        ),
        # ------------------------------------------------------------------ #
        #  Poll                                                                #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="Poll",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("question", models.CharField(max_length=255)),
                ("allow_multiple", models.BooleanField(default=False)),
                ("closes_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "thread",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="poll",
                        to="auth_forum.thread",
                    ),
                ),
            ],
            options={
                "verbose_name": "Poll",
                "verbose_name_plural": "Polls",
            },
        ),
        # ------------------------------------------------------------------ #
        #  PollOption                                                          #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="PollOption",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("text", models.CharField(max_length=200)),
                ("order", models.PositiveSmallIntegerField(default=0)),
                (
                    "poll",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="options",
                        to="auth_forum.poll",
                    ),
                ),
            ],
            options={
                "verbose_name": "Poll Option",
                "verbose_name_plural": "Poll Options",
                "ordering": ["order", "pk"],
            },
        ),
        # ------------------------------------------------------------------ #
        #  PollVote                                                            #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="PollVote",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("voted_at", models.DateTimeField(auto_now_add=True)),
                (
                    "option",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="votes",
                        to="auth_forum.polloption",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="forum_poll_votes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Poll Vote",
                "verbose_name_plural": "Poll Votes",
            },
        ),
    ]
