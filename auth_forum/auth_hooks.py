from django.apps import apps
from django.utils.translation import gettext_lazy as _

from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls


# ---------------------------------------------------------------------------
# Menu item
# ---------------------------------------------------------------------------


class ForumMenuItem(MenuItemHook):
    """Sidebar menu entry for the forum."""

    def __init__(self):
        MenuItemHook.__init__(
            self,
            _("Forum"),
            "fas fa-comments fa-fw",
            "auth_forum:index",
            navactive=["auth_forum:"],
        )

    def render(self, request):
        if request.user.has_perm("auth_forum.basic_access"):
            return MenuItemHook.render(self, request)
        return ""


@hooks.register("menu_item_hook")
def register_menu():
    return ForumMenuItem()


# ---------------------------------------------------------------------------
# URL registration
# ---------------------------------------------------------------------------


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "auth_forum", r"^forum/")


# ---------------------------------------------------------------------------
# Dashboard hook — "Recent Threads" widget
# ---------------------------------------------------------------------------


def forum_dashboard_view(request):
    """Render a compact recent-threads widget for the AA dashboard."""
    if not request.user.has_perm("auth_forum.basic_access"):
        return ""

    from django.template.loader import render_to_string

    from .helpers import get_accessible_boards
    from .models import Thread

    try:
        accessible_boards = get_accessible_boards(request.user)
        board_ids = [b.id for b in accessible_boards]
        recent_threads = (
            Thread.objects.filter(board_id__in=board_ids)
            .select_related("board", "author")
            .order_by("-updated_at")[:5]
        )
        return render_to_string(
            "auth_forum/partials/dashboard_widget.html",
            {"recent_threads": recent_threads},
            request=request,
        )
    except Exception:
        return ""


class ForumDashboardHook:
    """Dashboard hook wrapper so the forum appears on the AA dashboard."""

    order = 500

    def render(self, request):
        return forum_dashboard_view(request)


@hooks.register("dashboard_hook")
def register_dashboard():
    return ForumDashboardHook()


# ---------------------------------------------------------------------------
# Discord Cogs hook (only registered when aadiscordbot is installed)
# ---------------------------------------------------------------------------


@hooks.register("discord_cogs_hook")
def register_discord_cogs():
    if apps.is_installed("aadiscordbot"):
        return ["auth_forum.cogs.forum_cog"]
    return []
