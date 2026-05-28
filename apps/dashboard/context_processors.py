from apps.dashboard.registry import get_registry, get_sidebar_sections

# First path segment under /iamadmin/ that is not a reserved page name
_SIDEBAR_RESERVED = frozenset({
    '', 'login', 'register', 'logout', 'analytics', 'users',
    'transactions', 'settings', 'api',
})


def _active_model_from_path(path: str) -> str:
    parts = [p for p in path.strip('/').split('/') if p]
    if len(parts) < 2 or parts[0] != 'iamadmin':
        return ''
    segment = parts[1]
    if segment in _SIDEBAR_RESERVED or not segment.startswith(('accounts.', 'auth.', 'blogs.', 'core.', 'contenttypes.', 'sessions.')):
        return ''
    return segment


def admin_nav(request):
    if not request.path.startswith('/iamadmin'):
        return {}
    active_model = _active_model_from_path(request.path)
    return {
        'registry': get_registry(),
        'sidebar_sections': get_sidebar_sections(active_model),
        'sidebar_active_model': active_model,
    }
