"""
auth_forum template tags and filters.
"""

import html
import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# ---------------------------------------------------------------------------
# Allowed image URL scheme — only http/https, no data: URIs etc.
# ---------------------------------------------------------------------------
_IMG_URL_RE = re.compile(
    r"https?://[^\s<>\"'\]\[]{3,2000}",
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


@register.filter(name="forum_render", is_safe=True)
def forum_render(value: str) -> str:
    """
    Convert forum markup in *value* to safe HTML.

    Supported tags
    --------------
    [img]https://...[/img]          → <img>
    [quote=AuthorName]...[/quote]   → styled quote block with author
    [quote]...[/quote]              → styled quote block without author
    **text**                        → <strong>
    _text_                          → <em>
    `text`                          → <code>
    """
    if not value:
        return ""

    # 1. HTML-escape everything first to neutralise XSS
    text = html.escape(str(value))

    # 2. [img]url[/img]
    text = re.sub(
        r"\[img\](.*?)\[/img\]",
        lambda m: _safe_img(m.group(1)),
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # 3. [quote=Author]...[/quote]
    def _quote_with_author(m):
        author = html.escape(m.group(1).strip())
        body = m.group(2)
        return (
            f'<div class="forum-quote-block">'
            f'<div class="forum-quote-author">'
            f'<i class="fas fa-quote-left fa-fw me-1"></i>{author}'
            f"</div>{body}</div>"
        )

    text = re.sub(
        r"\[quote=([^\]]{1,100})\](.*?)\[/quote\]",
        _quote_with_author,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # 4. [quote]...[/quote] (no author)
    text = re.sub(
        r"\[quote\](.*?)\[/quote\]",
        r'<div class="forum-quote-block">\1</div>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # 5. **bold**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text, flags=re.DOTALL)

    # 6. _italic_  (word-boundary aware — won't clobber underscores in URLs)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", text, flags=re.DOTALL)

    # 7. `inline code`
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text, flags=re.DOTALL)

    # 8. Newlines → <br>
    text = text.replace("\n", "<br>\n")

    return mark_safe(text)
