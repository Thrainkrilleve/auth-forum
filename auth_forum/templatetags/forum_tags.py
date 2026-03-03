"""
auth_forum template tags and filters.
"""

import html
import re
import uuid

from django import template
from django.utils.safestring import mark_safe

try:
    import mistune
    _MISTUNE_AVAILABLE = True
except ImportError:
    _MISTUNE_AVAILABLE = False

register = template.Library()

# ---------------------------------------------------------------------------
# Allowed image URL scheme — only http/https, no data: URIs etc.
# ---------------------------------------------------------------------------
_IMG_URL_RE = re.compile(
    r"https?://[^\s<>\"'\]\[]{3,2000}",
    re.IGNORECASE,
)
# A line containing only an image URL (auto-renders without [img] tags)
_BARE_IMG_LINE_RE = re.compile(
    r"(?m)^[ \t]*(https?://[^\s<>"'\]\[]{3,2000}\.(?:jpe?g|png|gif|webp|svg)(?:\?[^\s<>"'\]\[]*)?)[ \t]*$",
    re.IGNORECASE,
)

def _safe_img(url: str) -> str:
    """Return a safe <img> tag if *url* looks like a real http(s) URL."""
    url = url.strip()
    if not _IMG_URL_RE.fullmatch(url):
        return html.escape(url)
    return (
        f'<img src="{html.escape(url)}" '
        f'class="forum-img-embed" alt="image" loading="lazy">'
    )


def _extract_blocks(text: str) -> tuple:
    """
    Pull [img] and [quote] blocks out of *text*, replace with UUID sentinels.
    Returns (stripped_text, mapping) where mapping maps sentinel → HTML.
    """
    mapping: dict = {}

    # [quote=Author]...[/quote]
    def _sub_quote_author(m):
        key = f"\x00BLOCK-{uuid.uuid4().hex}\x00"
        author = m.group(1).strip()
        body = m.group(2).strip()
        mapping[key] = (
            f'<div class="forum-quote-block">'
            f'<div class="forum-quote-author">'
            f'<i class="fas fa-quote-left fa-fw me-1"></i>{html.escape(author)}'
            f'</div>'
            f'<div class="forum-quote-body">{body}</div>'
            f'</div>'
        )
        return f"\n\n{key}\n\n"

    text = re.sub(
        r"\[quote=([^\]]{1,100})\](.*?)\[/quote\]",
        _sub_quote_author,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # [quote]...[/quote] (no author)
    def _sub_quote(m):
        key = f"\x00BLOCK-{uuid.uuid4().hex}\x00"
        body = m.group(1).strip()
        mapping[key] = (
            f'<div class="forum-quote-block">'
            f'<div class="forum-quote-body">{body}</div>'
            f'</div>'
        )
        return f"\n\n{key}\n\n"

    text = re.sub(
        r"\[quote\](.*?)\[/quote\]",
        _sub_quote,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # [img]url[/img]
    def _sub_img(m):
        key = f"\x00BLOCK-{uuid.uuid4().hex}\x00"
        mapping[key] = _safe_img(m.group(1))
        return f"\n\n{key}\n\n"

    text = re.sub(
        r"\[img\](.*?)\[/img\]",
        _sub_img,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Bare image URLs — a line containing only an image URL, no [img] tags needed
    def _sub_bare_img(m):
        key = f"\x00BLOCK-{uuid.uuid4().hex}\x00"
        mapping[key] = _safe_img(m.group(1).strip())
        return f"\n\n{key}\n\n"

    text = _BARE_IMG_LINE_RE.sub(_sub_bare_img, text)

    return text, mapping


def _restore_blocks(rendered: str, mapping: dict) -> str:
    """Replace sentinel markers back with the pre-rendered HTML."""
    for key, value in mapping.items():
        # mistune may wrap a lone paragraph token in <p>...</p>
        rendered = rendered.replace(f"<p>{key}</p>", value)
        rendered = rendered.replace(key, value)
    return rendered


if _MISTUNE_AVAILABLE:
    _md = mistune.create_markdown(
        escape=True,
        plugins=["strikethrough", "table"],
    )

    @register.filter(name="forum_render", is_safe=True)
    def forum_render(value: str) -> str:
        """Convert forum markup to safe HTML using mistune for Markdown."""
        if not value:
            return ""
        text, mapping = _extract_blocks(str(value))
        rendered = _md(text)
        rendered = _restore_blocks(rendered, mapping)
        return mark_safe(rendered)

else:
    # Fallback: minimal regex-based renderer when mistune isn't installed.
    @register.filter(name="forum_render", is_safe=True)
    def forum_render(value: str) -> str:
        """Minimal forum markup renderer (mistune not installed)."""
        if not value:
            return ""
        # Extract bare image URLs before html.escape to avoid double-escaping
        _bare_imgs: dict = {}
        _counter = [0]

        def _bare_sub(m):
            ph = f"@@FORUMIMG{_counter[0]}@@"
            _bare_imgs[ph] = _safe_img(m.group(1).strip())
            _counter[0] += 1
            return "\n" + ph + "\n"

        raw = _BARE_IMG_LINE_RE.sub(_bare_sub, str(value))
        text = html.escape(raw)
        # Restore bare images
        for _ph, _img_html in _bare_imgs.items():
            text = text.replace(_ph, _img_html)
        text = re.sub(
            r"\[img\](.*?)\[/img\]",
            lambda m: _safe_img(m.group(1)),
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        def _quote_author(m):
            author = html.escape(m.group(1).strip())
            return (
                f'<div class="forum-quote-block">'
                f'<div class="forum-quote-author">'
                f'<i class="fas fa-quote-left fa-fw me-1"></i>{author}'
                f'</div><div class="forum-quote-body">{m.group(2)}</div></div>'
            )

        text = re.sub(
            r"\[quote=([^\]]{1,100})\](.*?)\[/quote\]",
            _quote_author, text, flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(
            r"\[quote\](.*?)\[/quote\]",
            r'<div class="forum-quote-block"><div class="forum-quote-body">\1</div></div>',
            text, flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text, flags=re.DOTALL)
        text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", text, flags=re.DOTALL)
        text = re.sub(r"`(.+?)`", r"<code>\1</code>", text, flags=re.DOTALL)
        text = text.replace("\n", "<br>\n")
        return mark_safe(text)


# ---------------------------------------------------------------------------
# Utility filters
# ---------------------------------------------------------------------------


@register.filter
def dict_get(d, key):
    """Return d[key] or 0.  Usage: {{ reaction_counts|dict_get:emoji_key }}"""
    if d is None:
        return 0
    return d.get(key, 0)


@register.simple_tag
def giphy_api_key():
    """Output the configured Giphy API key for use in templates."""
    from auth_forum.app_settings import AUTH_FORUM_GIPHY_API_KEY
    return AUTH_FORUM_GIPHY_API_KEY
