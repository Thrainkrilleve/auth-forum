"""
Business-logic helpers for auth_forum.

Kept separate from views so they can be called from tasks and tests without
importing the full Django request cycle.
"""

from django.apps import apps
from django.contrib.auth.models import User
from django.db.models import QuerySet, Prefetch

from .models import Board, Thread, Post, UserReadStatus


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


def user_can_access_board(user, board: Board) -> bool:
    """
    Return True if *user* is allowed to view/post in *board*.

    Rules (all must be satisfied):
    1. User must have the ``auth_forum.basic_access`` permission.
    2. If the board has group restrictions, the user must be in at least one.
    3. If the board has state restrictions, the user's current AA state must
       be in the list.
    4. Rules 2 and 3 are combined with OR when both are present (group OR state).
    """
    if not user.has_perm("auth_forum.basic_access"):
        return False

    board_groups = board.groups.all()
    board_states = board.states.all()

    has_group_restriction = board_groups.exists()
    has_state_restriction = board_states.exists()

    # No restrictions → open to all basic_access holders
    if not has_group_restriction and not has_state_restriction:
        return True

    # Check group membership
    if has_group_restriction:
        user_group_ids = user.groups.values_list("id", flat=True)
        if board_groups.filter(id__in=user_group_ids).exists():
            return True

    # Check AA state
    if has_state_restriction:
        try:
            user_state = user.profile.state
            if board_states.filter(pk=user_state.pk).exists():
                return True
        except Exception:
            pass

    return False


def get_accessible_boards(user) -> QuerySet:
    """
    Return a queryset of all Board objects the user can access.

    Prefetches groups and states to avoid N+1 inside user_can_access_board.
    The heavy lifting (Python-level filtering) is done after the DB query so
    we always honour both group and state rules correctly.
    """
    boards = Board.objects.select_related("category").prefetch_related(
        "groups", "states"
    )
    return [b for b in boards if not b.is_hidden and user_can_access_board(user, b)]


# ---------------------------------------------------------------------------
# Unread tracking
# ---------------------------------------------------------------------------


def get_unread_thread_ids(user, thread_ids) -> set:
    """
    Return a set of thread IDs from *thread_ids* that have posts newer than
    the user's last-read timestamp (or the user has never read at all).
    """
    read_statuses = UserReadStatus.objects.filter(
        user=user, thread_id__in=thread_ids
    ).values("thread_id", "last_read")

    read_map = {row["thread_id"]: row["last_read"] for row in read_statuses}

    unread = set()
    threads = Thread.objects.filter(id__in=thread_ids).prefetch_related(
        Prefetch("posts", queryset=Post.objects.order_by("-created_at"))
    )
    for thread in threads:
        last_post = thread.posts.order_by("-created_at").first()
        if not last_post:
            continue
        if thread.id not in read_map:
            unread.add(thread.id)
        elif last_post.created_at > read_map[thread.id]:
            unread.add(thread.id)

    return unread


def mark_thread_read(user, thread: Thread) -> None:
    """Upsert a UserReadStatus for (user, thread)."""
    UserReadStatus.objects.update_or_create(user=user, thread=thread)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def get_thread_subscribers(thread: Thread, exclude_user=None) -> QuerySet:
    """
    Return queryset of Users who have posted in *thread* — these are the
    users to notify on a new reply.
    """
    qs = (
        User.objects.filter(forum_posts__thread=thread)
        .distinct()
        .exclude(pk=thread.author_id if thread.author_id else 0)
    )
    if exclude_user:
        qs = qs.exclude(pk=exclude_user.pk)
    # Also include the thread author
    author_qs = User.objects.filter(pk=thread.author_id) if thread.author_id else User.objects.none()
    if exclude_user and thread.author_id == exclude_user.pk:
        author_qs = User.objects.none()
    return (qs | author_qs).distinct()


# ---------------------------------------------------------------------------
# Discord integration (optional — only active when aadiscordbot is installed)
# ---------------------------------------------------------------------------


def discord_bot_active() -> bool:
    """Return True if allianceauth-discordbot is installed in this project."""
    return apps.is_installed("aadiscordbot")
