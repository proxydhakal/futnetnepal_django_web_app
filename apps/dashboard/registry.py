from dataclasses import dataclass, field

from django.apps import apps
from django.db import models

# Apps whose models are never shown in /iamadmin/
SKIP_APP_LABELS = frozenset({
    'dashboard',
    'admin',
})

# Optional per-model blocklist (empty = register everything else)
SKIP_MODELS = frozenset()


def _project_app_labels():
    """App labels from this project (apps.* packages)."""
    return {
        app_config.label
        for app_config in apps.get_app_configs()
        if app_config.name.startswith('apps.')
    }


def _should_register(model) -> bool:
    if model._meta.abstract or model._meta.proxy:
        return False
    app_label = model._meta.app_label
    model_name = model._meta.model_name
    if app_label in SKIP_APP_LABELS:
        return False
    if (app_label, model_name) in SKIP_MODELS:
        return False
    # All project apps + auth, sessions, contenttypes (full CRUD coverage)
    if app_label in _project_app_labels():
        return True
    if app_label in ('auth', 'sessions', 'contenttypes'):
        return True
    return False


@dataclass
class ModelAdminMeta:
    key: str
    app_label: str
    model_name: str
    verbose_name: str
    verbose_name_plural: str
    list_display: list[str] = field(default_factory=list)
    search_fields: list[str] = field(default_factory=list)
    list_filter: list[str] = field(default_factory=list)
    readonly_fields: list[str] = field(default_factory=list)
    exclude_fields: list[str] = field(default_factory=list)

    @property
    def model(self):
        return apps.get_model(self.app_label, self.model_name)

    @property
    def url_prefix(self):
        return self.key.replace('.', '/')


def _field_sort_key(f):
    if f.primary_key:
        return (0, f.name)
    if isinstance(f, (models.CharField, models.TextField, models.EmailField, models.SlugField)):
        return (1, f.name)
    if isinstance(f, models.BooleanField):
        return (2, f.name)
    if isinstance(f, (models.DateTimeField, models.DateField, models.TimeField)):
        return (3, f.name)
    if isinstance(f, models.ForeignKey):
        return (4, f.name)
    return (5, f.name)


def _build_meta(model) -> ModelAdminMeta | None:
    if not _should_register(model):
        return None

    app_label = model._meta.app_label
    model_name = model._meta.model_name

    concrete = [
        f for f in model._meta.get_fields()
        if getattr(f, 'concrete', False) and not getattr(f, 'many_to_many', False)
    ]
    concrete.sort(key=_field_sort_key)

    list_display = [f.name for f in concrete[:8]]
    if not list_display and model._meta.pk:
        list_display = [model._meta.pk.name]

    search_fields = [
        f.name for f in concrete
        if isinstance(f, (models.CharField, models.TextField, models.EmailField, models.SlugField))
        and not isinstance(f, (models.FileField, models.ImageField))
    ][:6]

    list_filter = []
    for f in concrete:
        if isinstance(f, models.BooleanField):
            list_filter.append(f.name)
        elif isinstance(f, models.CharField) and getattr(f, 'choices', None):
            list_filter.append(f.name)
        elif isinstance(f, models.ForeignKey):
            list_filter.append(f.name)
    list_filter = list_filter[:5]

    readonly = []
    exclude = []
    for f in concrete:
        if getattr(f, 'auto_created', False) or isinstance(f, models.AutoField):
            readonly.append(f.name)
        if isinstance(f, models.DateTimeField) and getattr(f, 'auto_now', False):
            readonly.append(f.name)
        if isinstance(f, models.DateTimeField) and getattr(f, 'auto_now_add', False):
            readonly.append(f.name)

    if model_name == 'user':
        exclude = ['password', 'last_login']
        readonly.extend(['date_joined'])
    elif model_name == 'session':
        readonly.append('session_data')

    key = f'{app_label}.{model_name}'
    return ModelAdminMeta(
        key=key,
        app_label=app_label,
        model_name=model_name,
        verbose_name=model._meta.verbose_name,
        verbose_name_plural=model._meta.verbose_name_plural,
        list_display=list_display,
        search_fields=search_fields,
        list_filter=list_filter,
        readonly_fields=sorted(set(readonly)),
        exclude_fields=sorted(set(exclude)),
    )


def get_registry() -> dict[str, ModelAdminMeta]:
    registry = {}
    for model in apps.get_models():
        meta = _build_meta(model)
        if meta:
            registry[meta.key] = meta
    return dict(sorted(registry.items(), key=lambda x: (x[1].app_label, x[1].model_name)))


def get_model_meta(key: str) -> ModelAdminMeta:
    registry = get_registry()
    if key not in registry:
        raise LookupError(f'Unknown model: {key}')
    return registry[key]


def get_registry_groups():
    """Registry grouped by app_label (legacy). Prefer get_sidebar_sections()."""
    groups = {}
    for meta in get_registry().values():
        groups.setdefault(meta.app_label, []).append(meta)
    return [
        {'app_label': label, 'models': sorted(models, key=lambda m: m.verbose_name_plural)}
        for label, models in sorted(groups.items())
    ]


# Professional sidebar grouping (not raw Django app labels)
SIDEBAR_SECTIONS = [
    {
        'id': 'access',
        'label': 'Users & access',
        'icon': 'fa-users',
        'model_keys': ['auth.user', 'accounts.profile', 'auth.group', 'auth.permission'],
    },
    {
        'id': 'content',
        'label': 'Content & blog',
        'icon': 'fa-newspaper',
        'model_keys': ['core.post', 'blogs.blog', 'blogs.category', 'blogs.tag'],
    },
    {
        'id': 'venues',
        'label': 'Venues & bookings',
        'icon': 'fa-location-dot',
        'model_keys': ['core.venue', 'core.venuebooking', 'core.location', 'core.time'],
    },
    {
        'id': 'engagement',
        'label': 'Engagement',
        'icon': 'fa-heart',
        'model_keys': [
            'core.postcomment', 'core.postinterest', 'core.postreaction', 'core.notification',
        ],
    },
    {
        'id': 'messaging',
        'label': 'Messaging',
        'icon': 'fa-comments',
        'model_keys': ['core.directconversation', 'core.eventchatmessage'],
    },
    {
        'id': 'support',
        'label': 'Support',
        'icon': 'fa-envelope',
        'model_keys': ['core.contact'],
    },
    {
        'id': 'system',
        'label': 'System',
        'icon': 'fa-server',
        'model_keys': ['contenttypes.contenttype', 'sessions.session'],
    },
]


def get_sidebar_sections(active_model_key: str = ''):
    """Sidebar nav grouped by product area; marks section open when it contains active model."""
    registry = get_registry()
    assigned = set()
    sections = []

    for spec in SIDEBAR_SECTIONS:
        models = []
        for key in spec['model_keys']:
            meta = registry.get(key)
            if meta:
                models.append(meta)
                assigned.add(key)
        if not models:
            continue
        contains_active = active_model_key in {m.key for m in models}
        sections.append({
            'id': spec['id'],
            'label': spec['label'],
            'icon': spec['icon'],
            'models': models,
            'contains_active': contains_active,
        })

    orphans = [registry[k] for k in sorted(registry) if k not in assigned]
    if orphans:
        sections.append({
            'id': 'other',
            'label': 'Other',
            'icon': 'fa-folder',
            'models': orphans,
            'contains_active': any(m.key == active_model_key for m in orphans),
        })

    return sections
