"""
Views for auth_forum.

All views require:
  - @login_required
  - auth_forum.basic_access permission
  - Per-board user_can_access_board() check where needed
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _

from .app_settings import (
    AUTH_FORUM_POSTS_PER_PAGE,
    AUTH_FORUM_SEARCH_MIN_LENGTH,
    AUTH_FORUM_THREADS_PER_PAGE,
)
from .helpers import (
    get_accessible_boards,
    get_unread_thread_ids,
    mark_thread_read,
    user_can_access_board,
)
from .models import Board, Category, Post, Thread


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_post_count(user) -> int:
    """Total posts by a user across the entire forum."""
    return Post.objects.filter(author=user).count()


def _char_context(user) -> dict:
    """Return EVE character info for a user's sidebar on post cards."""
    try:
        main = user.profile.main_character
        return {
            "character_name": main.character_name if main else user.username,
            "portrait_url": main.portrait_url_64 if main else None,
            "corporation_name": main.corporation_name if main else None,
            "alliance_name": main.alliance_name if main else None,
        }
    except Exception:
        return {
            "character_name": user.username,
            "portrait_url": None,
            "corporation_name": None,
            "alliance_name": None,
        }


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
def index(request):
    """Forum home: all accessible categories and their boards."""
    accessible_boards = get_accessible_boards(request.user)
    accessible_board_ids = [b.id for b in accessible_boards]

    # Gather all thread IDs across accessible boards for unread computation
    thread_ids = list(
        Thread.objects.filter(board_id__in=accessible_board_ids).values_list(
            "id", flat=True
        )
    )
    unread_ids = get_unread_thread_ids(request.user, thread_ids)

    # Build board metadata map
    board_meta = {}
    for board in accessible_boards:
        board_thread_ids = [
            t
            for t in Thread.objects.filter(board=board).values_list("id", flat=True)
        ]
        unread_count = len(
            [tid for tid in board_thread_ids if tid in unread_ids]
        )
        last_post = board.last_post
        board_meta[board.id] = {
            "board": board,
            "thread_count": board.thread_count,
            "post_count": board.post_count,
            "last_post": last_post,
            "unread_count": unread_count,
        }

    # Build ordered category → boards structure
    categories = Category.objects.filter(is_hidden=False).order_by("order", "name")
    cat_data = []
    for cat in categories:
        cat_boards = [
            board_meta[b.id] for b in accessible_boards if b.category_id == cat.id
        ]
        if cat_boards:
            cat_data.append({"category": cat, "boards": cat_boards})

    context = {
        "cat_data": cat_data,
        "total_unread": len(unread_ids),
    }
    return render(request, "auth_forum/index.html", context)


# ---------------------------------------------------------------------------
# Board (thread list)
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
def board(request, board_slug):
    """List threads in a board, pinned first then by last activity."""
    the_board = get_object_or_404(
        Board.objects.prefetch_related("groups", "states"), slug=board_slug
    )
    if not user_can_access_board(request.user, the_board):
        messages.error(request, _("You do not have access to that board."))
        return redirect("auth_forum:index")

    threads_qs = (
        Thread.objects.filter(board=the_board)
        .select_related("author")
        .order_by("-is_pinned", "-updated_at")
    )

    thread_ids = list(threads_qs.values_list("id", flat=True))
    unread_ids = get_unread_thread_ids(request.user, thread_ids)

    paginator = Paginator(threads_qs, AUTH_FORUM_THREADS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "board": the_board,
        "page_obj": page_obj,
        "unread_ids": unread_ids,
        "can_moderate": request.user.has_perm("auth_forum.manage_forum"),
    }
    return render(request, "auth_forum/board.html", context)


# ---------------------------------------------------------------------------
# Thread (post list)
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
def thread(request, thread_pk):
    """Display all posts in a thread; handle inline reply submission."""
    the_thread = get_object_or_404(
        Thread.objects.select_related("board__category", "author").prefetch_related(
            "board__groups", "board__states"
        ),
        pk=thread_pk,
    )
    if not user_can_access_board(request.user, the_thread.board):
        messages.error(request, _("You do not have access to that board."))
        return redirect("auth_forum:index")

    # Increment view count
    Thread.objects.filter(pk=the_thread.pk).update(view_count=the_thread.view_count + 1)

    if request.method == "POST":
        if the_thread.is_locked and not request.user.has_perm("auth_forum.manage_forum"):
            messages.error(request, _("This thread is locked."))
            return redirect("auth_forum:thread", thread_pk=the_thread.pk)

        content = request.POST.get("content", "").strip()
        if not content:
            messages.error(request, _("Post content cannot be empty."))
        else:
            with transaction.atomic():
                new_post = Post.objects.create(
                    thread=the_thread,
                    author=request.user,
                    content=content,
                    is_first_post=False,
                )
                # Touch thread updated_at so it bubbles up in board listing
                the_thread.save(update_fields=["updated_at"])

            # Fire async tasks
            from .tasks import notify_subscribers_task, discord_post_notification_task

            notify_subscribers_task.delay(the_thread.pk, new_post.pk, request.user.pk)
            discord_post_notification_task.delay(the_thread.pk, new_post.pk)

            mark_thread_read(request.user, the_thread)
            messages.success(request, _("Reply posted."))
            return redirect("auth_forum:thread", thread_pk=the_thread.pk)

    # GET — list posts, mark as read
    posts_qs = (
        the_thread.posts.select_related("author__profile__main_character")
        .order_by("created_at")
    )
    paginator = Paginator(posts_qs, AUTH_FORUM_POSTS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Augment each post with character metadata for the sidebar
    for p in page_obj:
        p.char_ctx = _char_context(p.author) if p.author else {}
        p.post_total = _get_user_post_count(p.author) if p.author else 0

    mark_thread_read(request.user, the_thread)

    context = {
        "thread": the_thread,
        "board": the_thread.board,
        "page_obj": page_obj,
        "can_moderate": request.user.has_perm("auth_forum.manage_forum"),
        "can_reply": not the_thread.is_locked
        or request.user.has_perm("auth_forum.manage_forum"),
    }
    return render(request, "auth_forum/thread.html", context)


# ---------------------------------------------------------------------------
# New thread
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
def new_thread(request, board_slug):
    """Create a new thread with an opening post."""
    the_board = get_object_or_404(
        Board.objects.prefetch_related("groups", "states"), slug=board_slug
    )
    if not user_can_access_board(request.user, the_board):
        messages.error(request, _("You do not have access to that board."))
        return redirect("auth_forum:index")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()

        errors = []
        if not title:
            errors.append(_("Thread title is required."))
        if len(title) > 255:
            errors.append(_("Thread title must be 255 characters or fewer."))
        if not content:
            errors.append(_("Post content is required."))

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(
                request,
                "auth_forum/new_thread.html",
                {"board": the_board, "title": title, "content": content},
            )

        with transaction.atomic():
            new_t = Thread.objects.create(
                board=the_board,
                author=request.user,
                title=title,
            )
            first_post = Post.objects.create(
                thread=new_t,
                author=request.user,
                content=content,
                is_first_post=True,
            )

        from .tasks import discord_post_notification_task

        discord_post_notification_task.delay(new_t.pk, first_post.pk)
        mark_thread_read(request.user, new_t)
        messages.success(request, _("Thread created."))
        return redirect("auth_forum:thread", thread_pk=new_t.pk)

    return render(request, "auth_forum/new_thread.html", {"board": the_board})


# ---------------------------------------------------------------------------
# Edit post
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
def edit_post(request, post_pk):
    """Edit a post. Only the author or a moderator may edit."""
    post = get_object_or_404(Post.objects.select_related("thread__board", "author"), pk=post_pk)

    if not (
        request.user == post.author
        or request.user.has_perm("auth_forum.manage_forum")
    ):
        messages.error(request, _("You do not have permission to edit that post."))
        return redirect("auth_forum:thread", thread_pk=post.thread.pk)

    if not user_can_access_board(request.user, post.thread.board):
        messages.error(request, _("You do not have access to that board."))
        return redirect("auth_forum:index")

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if not content:
            messages.error(request, _("Post content cannot be empty."))
            return render(request, "auth_forum/edit_post.html", {"post": post})

        post.content = content
        post.save(update_fields=["content", "updated_at"])
        messages.success(request, _("Post updated."))
        return redirect("auth_forum:thread", thread_pk=post.thread.pk)

    return render(request, "auth_forum/edit_post.html", {"post": post})


# ---------------------------------------------------------------------------
# Delete post
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
def delete_post(request, post_pk):
    """
    Delete a post.  If it is the first post in the thread, the entire thread
    is deleted after a GET-based confirmation step.
    """
    post = get_object_or_404(Post.objects.select_related("thread__board", "author"), pk=post_pk)

    if not (
        request.user == post.author
        or request.user.has_perm("auth_forum.manage_forum")
    ):
        messages.error(request, _("You do not have permission to delete that post."))
        return redirect("auth_forum:thread", thread_pk=post.thread.pk)

    if not user_can_access_board(request.user, post.thread.board):
        messages.error(request, _("You do not have access to that board."))
        return redirect("auth_forum:index")

    thread_pk = post.thread.pk
    board_slug = post.thread.board.slug

    if request.method == "POST":
        if post.is_first_post:
            the_thread = post.thread
            the_thread.delete()
            messages.success(request, _("Thread deleted."))
            return redirect("auth_forum:board", board_slug=board_slug)
        else:
            post.delete()
            messages.success(request, _("Post deleted."))
            return redirect("auth_forum:thread", thread_pk=thread_pk)

    return render(
        request,
        "auth_forum/delete_post_confirm.html",
        {"post": post, "deletes_thread": post.is_first_post},
    )


# ---------------------------------------------------------------------------
# Lock thread (manage_forum only)
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.manage_forum")
@require_POST
def lock_thread(request, thread_pk):
    """Toggle the locked state of a thread."""
    the_thread = get_object_or_404(Thread, pk=thread_pk)
    the_thread.is_locked = not the_thread.is_locked
    the_thread.save(update_fields=["is_locked"])
    state = _("locked") if the_thread.is_locked else _("unlocked")
    messages.success(request, _(f"Thread {state}."))
    return redirect("auth_forum:thread", thread_pk=the_thread.pk)


# ---------------------------------------------------------------------------
# Pin thread (manage_forum only)
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.manage_forum")
@require_POST
def pin_thread(request, thread_pk):
    """Toggle the pinned state of a thread."""
    the_thread = get_object_or_404(Thread, pk=thread_pk)
    the_thread.is_pinned = not the_thread.is_pinned
    the_thread.save(update_fields=["is_pinned"])
    state = _("pinned") if the_thread.is_pinned else _("unpinned")
    messages.success(request, _(f"Thread {state}."))
    return redirect("auth_forum:thread", thread_pk=the_thread.pk)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
def search(request):
    """Full-text search across posts in boards the user can access."""
    query = request.GET.get("q", "").strip()
    results = []
    too_short = False

    if query:
        if len(query) < AUTH_FORUM_SEARCH_MIN_LENGTH:
            too_short = True
        else:
            accessible_boards = get_accessible_boards(request.user)
            accessible_board_ids = [b.id for b in accessible_boards]

            results = (
                Post.objects.filter(
                    thread__board_id__in=accessible_board_ids,
                    content__icontains=query,
                )
                .select_related("thread__board__category", "author")
                .order_by("-created_at")[:50]
            )

    context = {
        "query": query,
        "results": results,
        "too_short": too_short,
        "min_length": AUTH_FORUM_SEARCH_MIN_LENGTH,
    }
    return render(request, "auth_forum/search.html", context)
