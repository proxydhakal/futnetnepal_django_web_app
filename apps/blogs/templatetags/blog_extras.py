import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_BASE_TAG_RE = re.compile(r'<base\b[^>]*>', re.IGNORECASE)


@register.filter(is_safe=True)
def safe_blog_html(value):
    """Render blog HTML but strip <base> tags that break site-wide navigation."""
    if not value:
        return ''
    cleaned = _BASE_TAG_RE.sub('', str(value))
    return mark_safe(cleaned)
