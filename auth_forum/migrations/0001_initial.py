import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("authentication", "0001_initial"),
    ]

    operations = [
        # ------------------------------------------------------------------ #
        #  General (fake permissions model)                                   #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="General",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
            ],
            options={
                "managed": False,
                "default_permissions": (),
                "permissions": (
                    ("basic_access", "Can access the forum"),
                    ("manage_forum", "Can moderate the forum (lock/pin/delete)"),
                ),
            },
        ),
        # ------------------------------------------------------------------ #
        #  Category                                                            #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=128, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("order", models.PositiveIntegerField(db_index=True, default=0)),
                ("is_hidden", models.BooleanField(default=False, help_text=_("Hidden categories are only visible to moderators."))),
            ],
            options={
                "verbose_name": "Category",
                "verbose_name_plural": "Categories",
                "ordering": ["order", "name"],
            },
        ),
        # ------------------------------------------------------------------ #
        #  Board                                                               #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="Board",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="boards",
                        to="auth_forum.category",
                    ),
                ),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True, default="")),
                ("slug", models.SlugField(blank=True, max_length=160, unique=True)),
                ("order", models.PositiveIntegerField(db_index=True, default=0)),
                ("is_hidden", models.BooleanField(default=False, help_text=_("Hidden boards are not shown on the index unless you have access."))),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text=_("Restrict this board to members of these Alliance Auth groups. Leave empty to allow all users with basic_access."),
                        related_name="forum_boards",
                        to="auth.group",
                    ),
                ),
                (
                    "states",
                    models.ManyToManyField(
                        blank=True,
                        help_text=_("Restrict this board to users with these Alliance Auth states. Leave empty to allow all users with basic_access."),
                        related_name="forum_boards",
                        to="authentication.state",
                    ),
                ),
            ],
            options={
                "verbose_name": "Board",
                "verbose_name_plural": "Boards",
                "ordering": ["category__order", "order", "name"],
            },
        ),
        # ------------------------------------------------------------------ #
        #  Thread                                                              #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="Thread",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "board",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="threads",
                        to="auth_forum.board",
                    ),
                ),
                (
                    "author",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="forum_threads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("slug", models.SlugField(blank=True, max_length=280, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_locked", models.BooleanField(default=False)),
                ("is_pinned", models.BooleanField(default=False)),
                ("view_count", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Thread",
                "verbose_name_plural": "Threads",
                "ordering": ["-is_pinned", "-updated_at"],
            },
        ),
        # ------------------------------------------------------------------ #
        #  Post                                                                #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="Post",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "thread",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="posts",
                        to="auth_forum.thread",
                    ),
                ),
                (
                    "author",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="forum_posts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_first_post", models.BooleanField(default=False, help_text=_("The opening post of the thread. Deleting it deletes the thread."))),
            ],
            options={
                "verbose_name": "Post",
                "verbose_name_plural": "Posts",
                "ordering": ["created_at"],
            },
        ),
        # ------------------------------------------------------------------ #
        #  UserReadStatus                                                      #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="UserReadStatus",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="forum_read_statuses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "thread",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="read_statuses",
                        to="auth_forum.thread",
                    ),
                ),
                ("last_read", models.DateTimeField(auto_now=True)),
            ],
            options={
                "unique_together": {("user", "thread")},
                "verbose_name": "User Read Status",
                "verbose_name_plural": "User Read Statuses",
            },
        ),
    ]
