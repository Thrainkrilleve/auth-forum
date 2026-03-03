"""
Views for auth_forum.

All views require:
  - @login_required
  - auth_forum.basic_access permission
  - Per-board user_can_access_board() check where needed
"""

import os
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _

from .app_settings import (
    AUTH_FORUM_POSTS_PER_PAGE,
    AUTH_FORUM_SEARCH_MIN_LENGTH,
    AUTH_FORUM_THREADS_PER_PAGE,
    AUTH_FORUM_UPLOAD_ENABLED,
    AUTH_FORUM_UPLOAD_MAX_SIZE,
)
from .helpers import (
    get_accessible_boards,
    get_unread_thread_ids,
    mark_thread_read,
    user_can_access_board,
)
from .forms import BoardForm, CategoryForm
from .models import (
    Board, BoardSubscription, Category, Post, PostEdit, Thread,
    PostReaction, ThreadSubscription, Poll, PollOption, PollVote,
)


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
    # Moderators see hidden categories too so they can manage them
    is_mod = request.user.has_perm("auth_forum.manage_forum")
    categories = Category.objects.all().order_by("order", "name") if is_mod \
        else Category.objects.filter(is_hidden=False).order_by("order", "name")
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
        "user_board_subscribed": BoardSubscription.objects.filter(
            user=request.user, board=the_board
        ).exists(),
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
            from .tasks import notify_subscribers_task, discord_post_notification_task, notify_mention_task

            notify_subscribers_task.delay(the_thread.pk, new_post.pk, request.user.pk)
            discord_post_notification_task.delay(the_thread.pk, new_post.pk)
            notify_mention_task.delay(new_post.pk, request.user.pk)

            mark_thread_read(request.user, the_thread)
            messages.success(request, _("Reply posted."))
            return redirect("auth_forum:thread", thread_pk=the_thread.pk)

    # GET — list posts, mark as read
    posts_qs = (
        the_thread.posts.select_related("author__profile__main_character")
        .prefetch_related("reactions")
        .order_by("created_at")
    )
    paginator = Paginator(posts_qs, AUTH_FORUM_POSTS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Augment each post with character metadata and reaction data
    for p in page_obj:
        p.char_ctx = _char_context(p.author) if p.author else {}
        p.post_total = _get_user_post_count(p.author) if p.author else 0
        # Reactions: count per emoji and which ones the current user gave
        p.reaction_counts = {}
        p.user_reactions = set()
        for r in p.reactions.all():
            p.reaction_counts[r.emoji] = p.reaction_counts.get(r.emoji, 0) + 1
            if r.user_id == request.user.pk:
                p.user_reactions.add(r.emoji)

    mark_thread_read(request.user, the_thread)

    # Subscription status
    is_subscribed = ThreadSubscription.objects.filter(
        user=request.user, thread=the_thread
    ).exists()

    # Poll (only show on first page)
    poll = None
    poll_options = []
    poll_total = 0
    user_voted_ids = set()
    if page_number in (1, "1", None):
        try:
            poll = the_thread.poll
            poll_options = list(
                poll.options.annotate(vote_count_ann=Count("votes")).order_by("order", "pk")
            )
            poll_total = poll.total_voters
            user_voted_ids = set(
                PollVote.objects.filter(
                    option__poll=poll, user=request.user
                ).values_list("option_id", flat=True)
            )
        except Poll.DoesNotExist:
            pass

    context = {
        "thread": the_thread,
        "board": the_thread.board,
        "page_obj": page_obj,
        "can_moderate": request.user.has_perm("auth_forum.manage_forum"),
        "can_reply": not the_thread.is_locked
        or request.user.has_perm("auth_forum.manage_forum"),
        "user_subscribed": is_subscribed,
        "is_subscribed": is_subscribed,
        "poll": poll,
        "poll_options": poll_options,
        "poll_total": poll_total,
        "user_voted_ids": user_voted_ids,
        "reaction_choices": PostReaction.REACTION_CHOICES,
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
                prefix=request.POST.get("prefix", "").strip(),
            )
            first_post = Post.objects.create(
                thread=new_t,
                author=request.user,
                content=content,
                is_first_post=True,
            )

        # Auto-subscribe the thread author
        ThreadSubscription.objects.get_or_create(user=request.user, thread=new_t)

        # Optional poll creation
        poll_question = request.POST.get("poll_question", "").strip()
        poll_options_raw = request.POST.getlist("poll_options")
        poll_options_clean = [o.strip() for o in poll_options_raw if o.strip()]
        if poll_question and len(poll_options_clean) >= 2:
            from django.utils.dateparse import parse_datetime
            closes_at_str = request.POST.get("poll_closes_at", "").strip()
            closes_at = parse_datetime(closes_at_str) if closes_at_str else None
            allow_multiple = request.POST.get("poll_allow_multiple") == "on"
            poll_obj = Poll.objects.create(
                thread=new_t,
                question=poll_question,
                allow_multiple=allow_multiple,
                closes_at=closes_at,
            )
            for i, opt_text in enumerate(poll_options_clean[:10]):
                PollOption.objects.create(poll=poll_obj, text=opt_text, order=i)

        from .tasks import discord_post_notification_task, notify_mention_task, notify_board_subscribers_task

        discord_post_notification_task.delay(new_t.pk, first_post.pk)
        notify_mention_task.delay(first_post.pk, request.user.pk)
        notify_board_subscribers_task.delay(new_t.pk)
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

        # Save edit history before overwriting
        PostEdit.objects.create(post=post, editor=request.user, old_content=post.content)
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
    board_filter = request.GET.get("board", "").strip()
    author_filter = request.GET.get("author", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    results = []
    too_short = False

    accessible_boards = get_accessible_boards(request.user)
    accessible_board_ids = [b.id for b in accessible_boards]

    if query:
        if len(query) < AUTH_FORUM_SEARCH_MIN_LENGTH:
            too_short = True
        else:
            qs = (
                Post.objects.filter(
                    thread__board_id__in=accessible_board_ids,
                    content__icontains=query,
                )
                .select_related("thread__board__category", "author")
                .order_by("-created_at")
            )
            if board_filter:
                qs = qs.filter(thread__board_id=board_filter)
            if author_filter:
                qs = qs.filter(author__username__icontains=author_filter)
            if date_from:
                qs = qs.filter(created_at__date__gte=date_from)
            if date_to:
                qs = qs.filter(created_at__date__lte=date_to)
            results = qs[:50]

    context = {
        "query": query,
        "results": results,
        "too_short": too_short,
        "min_length": AUTH_FORUM_SEARCH_MIN_LENGTH,
        "all_boards": accessible_boards,
        "board_filter": board_filter,
        "author_filter": author_filter,
        "date_from": date_from,
        "date_to": date_to,
    }
    return render(request, "auth_forum/search.html", context)


# ---------------------------------------------------------------------------
# Category management (manage_forum only)
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.manage_forum")
def create_category(request):
    """Create a new category."""
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Category created."))
        return redirect("auth_forum:index")
    return render(request, "auth_forum/manage_category.html", {"form": form, "title": _("New Category")})


@login_required
@permission_required("auth_forum.manage_forum")
def edit_category(request, category_pk):
    """Edit an existing category."""
    category = get_object_or_404(Category, pk=category_pk)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Category updated."))
        return redirect("auth_forum:index")
    return render(request, "auth_forum/manage_category.html", {"form": form, "title": _("Edit Category"), "category": category})


@login_required
@permission_required("auth_forum.manage_forum")
def delete_category(request, category_pk):
    """Delete a category and all its boards/threads/posts."""
    category = get_object_or_404(Category, pk=category_pk)
    if request.method == "POST":
        category.delete()
        messages.success(request, _("Category deleted."))
        return redirect("auth_forum:index")
    return render(request, "auth_forum/delete_category_confirm.html", {"category": category})


# ---------------------------------------------------------------------------
# Board management (manage_forum only)
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.manage_forum")
def create_board(request, category_pk=None):
    """Create a new board, optionally pre-filling the category."""
    initial = {}
    if category_pk:
        category = get_object_or_404(Category, pk=category_pk)
        initial["category"] = category
    form = BoardForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Board created."))
        return redirect("auth_forum:index")
    return render(request, "auth_forum/manage_board.html", {"form": form, "title": _("New Board")})


@login_required
@permission_required("auth_forum.manage_forum")
def edit_board(request, board_slug):
    """Edit an existing board."""
    the_board = get_object_or_404(Board, slug=board_slug)
    form = BoardForm(request.POST or None, instance=the_board)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Board updated."))
        return redirect("auth_forum:board", board_slug=the_board.slug)
    return render(request, "auth_forum/manage_board.html", {"form": form, "title": _("Edit Board"), "board": the_board})


@login_required
@permission_required("auth_forum.manage_forum")
def delete_board(request, board_slug):
    """Delete a board and all its threads/posts."""
    the_board = get_object_or_404(Board, slug=board_slug)
    if request.method == "POST":
        the_board.delete()
        messages.success(request, _("Board deleted."))
        return redirect("auth_forum:index")
    return render(request, "auth_forum/delete_board_confirm.html", {"board": the_board})


# ---------------------------------------------------------------------------
# Toggle reaction on a post
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
@require_POST
def toggle_reaction(request, post_pk):
    """Add or remove an emoji reaction on a post."""
    post = get_object_or_404(Post.objects.select_related("thread__board", "author"), pk=post_pk)

    if not user_can_access_board(request.user, post.thread.board):
        return redirect("auth_forum:index")

    emoji = request.POST.get("emoji", "")
    valid_emojis = [k for k, _ in PostReaction.REACTION_CHOICES]
    if emoji not in valid_emojis:
        return redirect("auth_forum:thread", thread_pk=post.thread.pk)

    reaction, created = PostReaction.objects.get_or_create(
        post=post, user=request.user, emoji=emoji
    )
    if not created:
        reaction.delete()
    elif post.author and post.author != request.user:
        from .tasks import notify_reaction_task
        notify_reaction_task.delay(post.pk, request.user.pk, emoji)

    # Redirect back to the correct page, anchored to the post
    page = request.POST.get("page", "")
    url = reverse("auth_forum:thread", kwargs={"thread_pk": post.thread.pk})
    if page:
        url += f"?page={page}"
    url += f"#post-{post.pk}"
    return redirect(url)


# ---------------------------------------------------------------------------
# Toggle thread subscription
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
@require_POST
def toggle_subscription(request, thread_pk):
    """Subscribe to or unsubscribe from a thread."""
    the_thread = get_object_or_404(Thread.objects.select_related("board"), pk=thread_pk)

    if not user_can_access_board(request.user, the_thread.board):
        return redirect("auth_forum:index")

    sub, created = ThreadSubscription.objects.get_or_create(
        user=request.user, thread=the_thread
    )
    if not created:
        sub.delete()
        messages.info(request, _("Unsubscribed from thread."))
    else:
        messages.success(request, _("Subscribed — you'll be notified of new replies."))

    return redirect("auth_forum:thread", thread_pk=the_thread.pk)


# ---------------------------------------------------------------------------
# Vote on a poll
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
@require_POST
def vote_poll(request, poll_pk):
    """Record or update a user's vote on a poll."""
    poll = get_object_or_404(Poll.objects.select_related("thread__board"), pk=poll_pk)

    if not user_can_access_board(request.user, poll.thread.board):
        return redirect("auth_forum:index")

    if poll.is_closed():
        messages.error(request, _("This poll is closed."))
        return redirect("auth_forum:thread", thread_pk=poll.thread.pk)

    option_ids = request.POST.getlist("option")
    if not option_ids:
        messages.error(request, _("Please select at least one option."))
        return redirect("auth_forum:thread", thread_pk=poll.thread.pk)

    if not poll.allow_multiple:
        option_ids = option_ids[:1]

    with transaction.atomic():
        # Remove any existing votes for this user on this poll
        PollVote.objects.filter(option__poll=poll, user=request.user).delete()
        # Record new votes
        options = PollOption.objects.filter(poll=poll, pk__in=option_ids)
        for opt in options:
            PollVote.objects.create(option=opt, user=request.user)

    messages.success(request, _("Vote recorded."))
    return redirect("auth_forum:thread", thread_pk=poll.thread.pk)


# ---------------------------------------------------------------------------
# Mark all threads as read
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
@require_POST
def mark_all_read(request):
    """Mark all accessible threads as read."""
    accessible_boards = get_accessible_boards(request.user)
    board_ids = [b.id for b in accessible_boards]
    thread_ids = list(Thread.objects.filter(board_id__in=board_ids).values_list("id", flat=True))
    with transaction.atomic():
        for tid in thread_ids:
            from .helpers import mark_thread_read as _mark_read
            from .models import UserReadStatus
            UserReadStatus.objects.update_or_create(
                user=request.user, thread_id=tid, defaults={}
            )
    messages.success(request, _("All threads marked as read."))
    return redirect("auth_forum:index")


@login_required
@permission_required("auth_forum.basic_access")
@require_POST
def mark_board_read(request, board_slug):
    """Mark all threads in a board as read."""
    from .models import UserReadStatus
    the_board = get_object_or_404(Board, slug=board_slug)
    if not user_can_access_board(request.user, the_board):
        return redirect("auth_forum:index")
    thread_ids = list(the_board.threads.values_list("id", flat=True))
    with transaction.atomic():
        for tid in thread_ids:
            UserReadStatus.objects.update_or_create(
                user=request.user, thread_id=tid, defaults={}
            )
    messages.success(request, _("Board marked as read."))
    return redirect("auth_forum:board", board_slug=board_slug)


# ---------------------------------------------------------------------------
# Jump to first unread post in thread
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
def thread_first_unread(request, thread_pk):
    """Redirect to the page and anchor of the first unread post."""
    from .models import UserReadStatus
    the_thread = get_object_or_404(Thread.objects.select_related("board"), pk=thread_pk)
    if not user_can_access_board(request.user, the_thread.board):
        return redirect("auth_forum:index")

    read_status = UserReadStatus.objects.filter(user=request.user, thread=the_thread).first()
    if read_status:
        first_unread = (
            the_thread.posts.filter(created_at__gt=read_status.last_read)
            .order_by("created_at")
            .first()
        )
    else:
        first_unread = the_thread.posts.order_by("created_at").first()

    if not first_unread:
        return redirect("auth_forum:thread", thread_pk=thread_pk)

    posts_before = the_thread.posts.filter(created_at__lt=first_unread.created_at).count()
    page = (posts_before // AUTH_FORUM_POSTS_PER_PAGE) + 1
    url = reverse("auth_forum:thread", kwargs={"thread_pk": thread_pk})
    if page > 1:
        url += f"?page={page}"
    url += f"#post-{first_unread.pk}"
    return redirect(url)


# ---------------------------------------------------------------------------
# Board subscription
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
@require_POST
def toggle_board_subscription(request, board_slug):
    """Subscribe to or unsubscribe from a board."""
    the_board = get_object_or_404(Board, slug=board_slug)
    if not user_can_access_board(request.user, the_board):
        return redirect("auth_forum:index")
    sub, created = BoardSubscription.objects.get_or_create(user=request.user, board=the_board)
    if not created:
        sub.delete()
        messages.info(request, _("Unsubscribed from board."))
    else:
        messages.success(request, _("Subscribed — you'll be notified of new threads."))
    return redirect("auth_forum:board", board_slug=board_slug)


# ---------------------------------------------------------------------------
# Move thread (manage_forum only)
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.manage_forum")
def move_thread(request, thread_pk):
    """Move a thread to a different board."""
    the_thread = get_object_or_404(Thread.objects.select_related("board"), pk=thread_pk)
    if request.method == "POST":
        new_board_id = request.POST.get("target_board")
        new_board = get_object_or_404(Board, pk=new_board_id)
        the_thread.board = new_board
        the_thread.save(update_fields=["board"])
        messages.success(request, _(f"Thread moved to {new_board.name}."))
        return redirect("auth_forum:thread", thread_pk=the_thread.pk)
    all_boards = Board.objects.select_related("category").order_by("category__order", "order", "name")
    # Group boards by category name for display
    boards_by_category: dict = {}
    for b in all_boards:
        cat_name = b.category.name if b.category else "—"
        boards_by_category.setdefault(cat_name, []).append(b)
    return render(request, "auth_forum/move_thread.html", {
        "thread": the_thread,
        "boards_by_category": boards_by_category,
    })


# ---------------------------------------------------------------------------
# Post edit history
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
def post_history(request, post_pk):
    """View the edit history for a post."""
    post = get_object_or_404(Post.objects.select_related("thread__board", "author"), pk=post_pk)
    if not user_can_access_board(request.user, post.thread.board):
        return redirect("auth_forum:index")
    edits = post.edits.select_related("editor").order_by("-edited_at")
    return render(request, "auth_forum/post_history.html", {"post": post, "edits": edits})


# ---------------------------------------------------------------------------
# Live preview (API)
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
def preview_content(request):
    """Return rendered HTML for a content string (used by the editor preview toggle)."""
    if request.method != "POST":
        return HttpResponse("", status=405)
    from .templatetags.forum_tags import forum_render
    content = request.POST.get("content", "")
    return JsonResponse({"html": forum_render(content)})


# ---------------------------------------------------------------------------
# @mention autocomplete (API)
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
def mention_autocomplete(request):
    """JSON: usernames matching ?q=... (min 2 chars)."""
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"users": []})
    users = list(
        User.objects.filter(username__istartswith=q)
        .order_by("username")[:8]
        .values_list("username", flat=True)
    )
    return JsonResponse({"users": users})


# ---------------------------------------------------------------------------
# Image upload (paste / drag-and-drop)
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
def upload_image(request):
    """Accept a pasted or dragged image file, save it, and return the public URL."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    if not AUTH_FORUM_UPLOAD_ENABLED:
        return JsonResponse({"error": "Image upload is not enabled on this server."}, status=403)

    img = request.FILES.get("image")
    if not img:
        return JsonResponse({"error": "No file received."}, status=400)
    if img.size > AUTH_FORUM_UPLOAD_MAX_SIZE:
        return JsonResponse({"error": "File too large."}, status=400)
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if img.content_type not in allowed_types:
        return JsonResponse({"error": "Unsupported file type."}, status=400)

    from django.conf import settings
    ext = img.name.rsplit(".", 1)[-1].lower() if "." in img.name else "png"
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = os.path.join(settings.MEDIA_ROOT, "auth_forum", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    with open(os.path.join(upload_dir, filename), "wb") as fh:
        for chunk in img.chunks():
            fh.write(chunk)
    url = settings.MEDIA_URL.rstrip("/") + f"/auth_forum/uploads/{filename}"
    return JsonResponse({"url": url})


# ---------------------------------------------------------------------------
# Forum statistics
# ---------------------------------------------------------------------------


@login_required
@permission_required("auth_forum.basic_access")
def stats(request):
    """Forum-wide statistics page."""
    top_posters = (
        Post.objects.filter(author__isnull=False)
        .values("author__username")
        .annotate(post_count=Count("id"))
        .order_by("-post_count")[:10]
    )
    top_threads = Thread.objects.select_related("board").order_by("-view_count")[:10]
    most_active = (
        Thread.objects.select_related("board")
        .annotate(reply_count=Count("posts"))
        .order_by("-reply_count")[:10]
    )
    total_posts = Post.objects.count()
    total_threads = Thread.objects.count()
    total_users = (
        User.objects.filter(forum_posts__isnull=False).distinct().count()
    )
    context = {
        "top_posters": top_posters,
        "top_threads": top_threads,
        "most_active": most_active,
        "total_posts": total_posts,
        "total_threads": total_threads,
        "total_users": total_users,
    }
    return render(request, "auth_forum/stats.html", context)
