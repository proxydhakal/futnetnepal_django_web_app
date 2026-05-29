"""Parse YouTube URLs into embed IDs / embed URLs."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

_YOUTUBE_HOSTS = frozenset({
    'youtube.com',
    'www.youtube.com',
    'm.youtube.com',
    'music.youtube.com',
    'youtu.be',
    'www.youtu.be',
})


def youtube_video_id(url: str | None) -> str | None:
    if not url:
        return None
    raw = url.strip()
    if not raw:
        return None

    if '://' not in raw:
        raw = f'https://{raw}'
    parsed = urlparse(raw)
    host = (parsed.netloc or '').lower().removeprefix('www.')

    if host in ('youtu.be',):
        video_id = parsed.path.lstrip('/').split('/')[0]
        return video_id or None

    if parsed.path.startswith('/embed/'):
        return parsed.path.split('/')[2] or None

    if parsed.path.startswith('/shorts/'):
        return parsed.path.split('/')[2] or None

    query = parse_qs(parsed.query)
    if 'v' in query and query['v']:
        return query['v'][0]

    match = re.search(
        r'(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})',
        raw,
    )
    if match:
        return match.group(1)
    return None


def youtube_embed_url(url: str | None, *, autoplay: bool = False) -> str:
    video_id = youtube_video_id(url)
    if not video_id:
        return ''
    params = ['rel=0', 'modestbranding=1']
    if autoplay:
        params.insert(0, 'autoplay=1')
    return f'https://www.youtube.com/embed/{video_id}?{"&".join(params)}'
