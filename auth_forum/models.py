from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class General(models.Model):
    """Fake model used purely to hold app-level permissions."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", "Can access the forum"),
            ("manage_forum", "Can moderate the forum (lock/pin/delete)"),
            ("bypass_board_restrictions", "Can access boards regardless of group/state restrictions"),
        )


class Category(models.Model):
    """Top-level grouping for boards."""

    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_hidden = models.BooleanField(
        default=False, help_text=_("Hidden categories are only visible to moderators.")
    )

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name


class Board(models.Model):
    """A forum board (sub-forum) belonging to a category."""

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="boards"
    )
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_hidden = models.BooleanField(
        default=False,
        help_text=_("Hidden boards are not shown on the index unless you have access."),
    )

    # Access control — empty = open to all auth_forum.basic_access holders
    groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        related_name="forum_boards",
        help_text=_(
            "Restrict this board to members of these Alliance Auth groups. "
            "Leave empty to allow all users with basic_access."
        ),
    )
    states = models.ManyToManyField(
        "authentication.State",
        blank=True,
        related_name="forum_boards",
        help_text=_(
            "Restrict this board to users with these Alliance Auth states. "
            "Leave empty to allow all users with basic_access."
        ),
    )

    class Meta:
        ordering = ["category__order", "order", "name"]
        verbose_name = "Board"
        verbose_name_plural = "Boards"

    def __str__(self) -> str:
        return f"{self.category.name} / {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 1
            while Board.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def thread_count(self) -> int:
        return self.threads.count()

    @property
    def post_count(self) -> int:
        return Post.objects.filter(thread__board=self).count()

    @property
    def last_post(self):
        return (
            Post.objects.filter(thread__board=self).order_by("-created_at").first()
        )


class Thread(models.Model):
    """A discussion thread within a board."""

    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="threads")
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="forum_threads"
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_locked = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-is_pinned", "-updated_at"]
        verbose_name = "Thread"
        verbose_name_plural = "Threads"

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:260]
            slug = base
            n = 1
            while Thread.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def post_count(self) -> int:
        return self.posts.count()

    @property
    def last_post(self):
        return self.posts.order_by("-created_at").first()

    @property
    def first_post(self):
        return self.posts.order_by("created_at").first()


class Post(models.Model):
    """A single post (reply) within a thread."""

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="forum_posts"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_first_post = models.BooleanField(
        default=False,
        help_text=_("The opening post of the thread. Deleting it deletes the thread."),
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Post"
        verbose_name_plural = "Posts"

    def __str__(self) -> str:
        author_name = self.author.username if self.author else "deleted"
        return f"Post by {author_name} in '{self.thread.title}'"


class UserReadStatus(models.Model):
    """Tracks when a user last read a thread for unread indicators."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="forum_read_statuses"
    )
    thread = models.ForeignKey(
        Thread, on_delete=models.CASCADE, related_name="read_statuses"
    )
    last_read = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "thread")
        verbose_name = "User Read Status"
        verbose_name_plural = "User Read Statuses"

    def __str__(self) -> str:
        return f"{self.user.username} read '{self.thread.title}'"


class PostReaction(models.Model):
    """An emoji reaction to a post."""

    THUMBSUP = "thumbsup"
    O7 = "o7"
    LAUGH = "laugh"
    WOW = "wow"
    FIRE = "fire"

    REACTION_CHOICES = [
        (THUMBSUP, "👍"),
        (O7,       "o7"),
        (LAUGH,    "😂"),
        (WOW,      "😮"),
        (FIRE,     "🔥"),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_reactions")
    emoji = models.CharField(max_length=20, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["post", "user", "emoji"], name="unique_post_user_emoji"
            )
        ]
        verbose_name = "Post Reaction"
        verbose_name_plural = "Post Reactions"

    def __str__(self) -> str:
        return f"{self.user.username} reacted {self.emoji} to post #{self.post_id}"


class ThreadSubscription(models.Model):
    """Explicit subscription to a thread — user will receive AA bell notifications on new replies."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_subscriptions")
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="subscriptions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "thread")
        verbose_name = "Thread Subscription"
        verbose_name_plural = "Thread Subscriptions"

    def __str__(self) -> str:
        return f"{self.user.username} subscribed to '{self.thread.title}'"


class Poll(models.Model):
    """A poll attached to a thread (one per thread)."""

    thread = models.OneToOneField(Thread, on_delete=models.CASCADE, related_name="poll")
    question = models.CharField(max_length=255)
    allow_multiple = models.BooleanField(
        default=False,
        help_text=_("Allow users to select more than one option."),
    )
    closes_at = models.DateTimeField(
        null=True, blank=True, help_text=_("Leave blank for no expiry.")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Poll"
        verbose_name_plural = "Polls"

    def __str__(self) -> str:
        return f"Poll: {self.question}"

    def is_closed(self) -> bool:
        from django.utils import timezone
        return self.closes_at is not None and timezone.now() > self.closes_at

    @property
    def total_voters(self) -> int:
        """Distinct number of users who have voted in this poll."""
        return PollVote.objects.filter(option__poll=self).values("user").distinct().count()


class PollOption(models.Model):
    """One answer option in a poll."""

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "Poll Option"
        verbose_name_plural = "Poll Options"

    def __str__(self) -> str:
        return self.text


class PollVote(models.Model):
    """A single vote by a user on a poll option."""

    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_poll_votes")
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Poll Vote"
        verbose_name_plural = "Poll Votes"

    def __str__(self) -> str:
        return f"{self.user.username} voted '{self.option.text}'"
