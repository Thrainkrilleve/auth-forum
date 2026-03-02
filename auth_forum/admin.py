from django.contrib import admin
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from .models import Board, Category, Post, Thread, UserReadStatus


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------


class BoardInline(admin.TabularInline):
    model = Board
    extra = 1
    fields = ("name", "description", "order", "is_hidden")
    show_change_link = True


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "board_count", "is_hidden")
    list_editable = ("order", "is_hidden")
    search_fields = ("name",)
    inlines = [BoardInline]

    @admin.display(description=_("Boards"))
    def board_count(self, obj):
        return obj.boards.count()


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "order",
        "thread_count_display",
        "post_count_display",
        "is_hidden",
    )
    list_select_related = ("category",)
    list_editable = ("order", "is_hidden")
    list_filter = ("category", "is_hidden")
    search_fields = ("name", "description")
    filter_horizontal = ("groups", "states")
    readonly_fields = ("slug",)
    fieldsets = (
        (None, {"fields": ("category", "name", "description", "slug", "order", "is_hidden")}),
        (
            _("Access Control"),
            {
                "description": _(
                    "Leave both empty to allow all users with basic_access. "
                    "When both are set, either matching group OR state grants access."
                ),
                "fields": ("groups", "states"),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _thread_count=Count("threads", distinct=True),
            )
        )

    @admin.display(description=_("Threads"), ordering="_thread_count")
    def thread_count_display(self, obj):
        return obj._thread_count

    @admin.display(description=_("Posts"))
    def post_count_display(self, obj):
        return Post.objects.filter(thread__board=obj).count()


# ---------------------------------------------------------------------------
# Thread
# ---------------------------------------------------------------------------


def action_lock_threads(modeladmin, request, queryset):
    queryset.update(is_locked=True)


action_lock_threads.short_description = _("Lock selected threads")


def action_unlock_threads(modeladmin, request, queryset):
    queryset.update(is_locked=False)


action_unlock_threads.short_description = _("Unlock selected threads")


def action_pin_threads(modeladmin, request, queryset):
    queryset.update(is_pinned=True)


action_pin_threads.short_description = _("Pin selected threads")


def action_unpin_threads(modeladmin, request, queryset):
    queryset.update(is_pinned=False)


action_unpin_threads.short_description = _("Unpin selected threads")


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "board",
        "author",
        "post_count_display",
        "view_count",
        "is_locked",
        "is_pinned",
        "created_at",
        "updated_at",
    )
    list_select_related = ("board__category", "author")
    list_filter = ("board__category", "board", "is_locked", "is_pinned")
    search_fields = ("title", "author__username")
    readonly_fields = ("slug", "created_at", "updated_at", "view_count")
    actions = [
        action_lock_threads,
        action_unlock_threads,
        action_pin_threads,
        action_unpin_threads,
    ]

    @admin.display(description=_("Posts"))
    def post_count_display(self, obj):
        return obj.posts.count()


# ---------------------------------------------------------------------------
# Post
# ---------------------------------------------------------------------------


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("__str__", "thread", "author", "is_first_post", "created_at", "updated_at")
    list_select_related = ("thread__board", "author")
    list_filter = ("thread__board",)
    search_fields = ("content", "author__username", "thread__title")
    readonly_fields = ("created_at", "updated_at", "is_first_post")


# ---------------------------------------------------------------------------
# UserReadStatus
# ---------------------------------------------------------------------------


@admin.register(UserReadStatus)
class UserReadStatusAdmin(admin.ModelAdmin):
    list_display = ("user", "thread", "last_read")
    list_select_related = ("user", "thread")
    search_fields = ("user__username", "thread__title")
    readonly_fields = ("last_read",)
