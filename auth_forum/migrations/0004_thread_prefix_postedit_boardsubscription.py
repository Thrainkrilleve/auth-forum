import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth_forum", "0003_reactions_polls_subscriptions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------ #
        #  Thread.prefix                                                       #
        # ------------------------------------------------------------------ #
        migrations.AddField(
            model_name="thread",
            name="prefix",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", ""),
                    ("question", "Question"),
                    ("guide", "Guide"),
                    ("answered", "Answered"),
                    ("announcement", "Announcement"),
                    ("discussion", "Discussion"),
                ],
                default="",
                help_text="Optional flair prefix shown before the thread title.",
                max_length=20,
            ),
        ),
        # ------------------------------------------------------------------ #
        #  PostEdit                                                            #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="PostEdit",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("old_content", models.TextField()),
                ("edited_at", models.DateTimeField(auto_now_add=True)),
                (
                    "editor",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="forum_edits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="edits",
                        to="auth_forum.post",
                    ),
                ),
            ],
            options={
                "verbose_name": "Post Edit",
                "verbose_name_plural": "Post Edits",
                "ordering": ["-edited_at"],
            },
        ),
        # ------------------------------------------------------------------ #
        #  BoardSubscription                                                   #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="BoardSubscription",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "board",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscriptions",
                        to="auth_forum.board",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="forum_board_subscriptions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Board Subscription",
                "verbose_name_plural": "Board Subscriptions",
                "unique_together": {("user", "board")},
            },
        ),
    ]
