import json
from datetime import timedelta

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth
from django.forms import ModelForm, PasswordInput
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.accounts.models import Profile, User as UserModel
from apps.core.contact_inquiry import maybe_send_contact_admin_reply
from apps.core.models import Contact
from apps.dashboard.registry import (
    CRUD_FORM_HIDDEN_FIELDS,
    ModelAdminMeta,
    get_model_meta,
    get_registry,
)
from apps.dashboard.slug_fields import (
    SLUG_FIELD,
    apply_auto_slug_to_payload,
    get_slug_source_field,
)
from futnetnepal.forms import SecureModelForm
from django.core.exceptions import ValidationError

from futnetnepal.input_validation import UnsafeInputError, sanitize_plain_text, sanitize_rich_text

User = get_user_model()
PAGE_SIZE = 20


def _serialize_value(value):
    if value is None:
        return ''
    if isinstance(value, models.Model):
        return str(value)
    if hasattr(value, 'isoformat'):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value)


def _format_list_value(field, value):
    if value is None or value == '':
        return ''
    choices = getattr(field, 'choices', None)
    if choices:
        return dict(choices).get(value, value)
    if isinstance(field, models.BooleanField):
        return 'Yes' if value else 'No'
    if isinstance(field, (models.ImageField, models.FileField)):
        name = getattr(value, 'name', None) or str(value)
        return name.split('/')[-1] if name else ''
    return _serialize_value(value)


def _crud_form_skip_fields(meta: ModelAdminMeta, *, for_edit=False):
    skip = (
        set(meta.exclude_fields)
        | set(meta.readonly_fields)
        | CRUD_FORM_HIDDEN_FIELDS
    )
    if meta.model == User and for_edit:
        skip.add('password')
    # Show linked user on profile edit (read-only), not hidden with other readonly fields
    if meta.key == 'accounts.profile' and for_edit:
        skip.discard('user')
    return skip


def _crud_form_field_names(meta: ModelAdminMeta, *, for_edit=False):
    skip = _crud_form_skip_fields(meta, for_edit=for_edit)
    names = []
    for f in meta.model._meta.fields:
        if not getattr(f, 'concrete', False):
            continue
        if f.name in skip:
            continue
        names.append(f.name)
    return names


def _serialize_field_value(field, value, *, for_edit=False):
    if for_edit and isinstance(field, (models.ForeignKey, models.OneToOneField)):
        if value is None:
            return ''
        return value.pk
    return _serialize_value(value)


def serialize_instance(meta: ModelAdminMeta, obj, *, fields=None, for_edit=False):
    model = meta.model
    field_map = {f.name: f for f in model._meta.fields}
    if for_edit:
        field_names = _crud_form_field_names(meta, for_edit=True)
    elif fields is None:
        field_names = [f.name for f in model._meta.fields]
    else:
        field_names = fields
    data = {'id': obj.pk}
    for name in field_names:
        if name in CRUD_FORM_HIDDEN_FIELDS:
            continue
        try:
            field = field_map.get(name)
            raw = getattr(obj, name)
            if field is not None:
                data[name] = _serialize_field_value(field, raw, for_edit=for_edit)
            else:
                data[name] = _serialize_value(raw)
        except Exception:
            data[name] = ''
    if for_edit:
        for f in model._meta.many_to_many:
            data[f.name] = list(getattr(obj, f.name).values_list('pk', flat=True))
    data['__str__'] = str(obj)
    return data


def normalize_form_errors(form):
    """Structured validation errors for the admin CRUD API and UI."""
    field_errors = {}
    for name, errs in form.errors.items():
        if name == '__all__':
            continue
        field_errors[name] = [str(e) for e in errs]
    non_field_errors = [str(e) for e in form.non_field_errors()]
    if non_field_errors:
        message = non_field_errors[0] if len(non_field_errors) == 1 else non_field_errors[0]
    elif field_errors:
        first_field = next(iter(field_errors))
        first_msgs = field_errors[first_field]
        label = first_field.replace('_', ' ').title()
        message = f'{label}: {first_msgs[0]}' if first_msgs else 'Please correct the highlighted fields.'
    else:
        message = 'Please correct the errors below.'
    return {
        'field_errors': field_errors,
        'non_field_errors': non_field_errors,
        'message': message,
    }


def get_form_class(meta: ModelAdminMeta):
    from django import forms

    # Nested Meta cannot reference outer locals with the same names (model, exclude).
    model_cls = meta.model
    readonly = set(meta.readonly_fields)
    exclude_list = list(meta.exclude_fields) if meta.exclude_fields else None

    class DynamicAdminForm(SecureModelForm):
        class Meta:
            model = model_cls
            fields = '__all__'
            exclude = exclude_list

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            auto_slug_source = get_slug_source_field(model_cls)
            for name, field in self.fields.items():
                if name in readonly:
                    field.disabled = True
                if auto_slug_source and name == SLUG_FIELD:
                    field.disabled = True
                    field.help_text = (
                        f'Generated automatically from {auto_slug_source.replace("_", " ")}.'
                    )
                css = 'fn-input w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 text-sm'
                if isinstance(field.widget, forms.Textarea):
                    field.widget.attrs['class'] = css + ' min-h-[100px]'
                elif not isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs['class'] = css
            for f in model_cls._meta.get_fields():
                if f.name in self.fields and 'ckeditor' in type(f).__module__:
                    self.fields[f.name].widget = forms.Textarea(attrs={
                        'class': 'fn-input w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 text-sm min-h-[200px]',
                        'rows': 10,
                    })

    if model_cls == User:
        class UserAdminForm(DynamicAdminForm):
            password = forms.CharField(
                required=False,
                widget=PasswordInput(render_value=False),
                help_text='Required for new users. Leave blank to keep existing.',
            )

            class Meta(DynamicAdminForm.Meta):
                fields = [
                    'username', 'email', 'full_name', 'role', 'status',
                    'profile_image', 'is_email_verified', 'is_active', 'is_staff',
                ]
                exclude = exclude_list

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if self.instance and self.instance.pk:
                    self.fields.pop('password', None)
                self.fields['role'].widget = forms.Select(
                    choices=UserModel.Role.choices,
                    attrs={'class': 'fn-input w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 text-sm'},
                )
                self.fields['status'].widget = forms.Select(
                    choices=UserModel.Status.choices,
                    attrs={'class': 'fn-input w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 text-sm'},
                )

        return UserAdminForm

    if model_cls == Contact:
        class ContactAdminForm(DynamicAdminForm):
            class Meta(DynamicAdminForm.Meta):
                fields = [
                    'fullname', 'email', 'phone', 'subject', 'message',
                    'status', 'admin_response', 'responded_at', 'responded_by',
                ]

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                inquiry_fields = (
                    'fullname', 'email', 'phone', 'subject', 'message',
                    'status', 'responded_at', 'responded_by',
                )
                for name in inquiry_fields:
                    if name in self.fields:
                        self.fields[name].disabled = True
                if 'admin_response' in self.fields:
                    self.fields['admin_response'].widget = forms.Textarea(attrs={
                        'class': 'fn-input w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 text-sm min-h-[140px]',
                        'rows': 6,
                        'placeholder': 'Write your reply to the customer…',
                    })
                    self.fields['admin_response'].help_text = (
                        'Saving sends this reply to the customer by email.'
                    )

        return ContactAdminForm

    if model_cls == Profile:
        class ProfileAdminForm(DynamicAdminForm):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if self.instance and self.instance.pk and 'user' in self.fields:
                    self.fields['user'].disabled = True
                    self.fields['user'].initial = self.instance.user_id

        return ProfileAdminForm

    return DynamicAdminForm


def enrich_edit_field_choices(meta: ModelAdminMeta, obj, choices: dict):
    """Per-record field metadata for edit modals (e.g. lock profile → user)."""
    if meta.key == 'accounts.profile' and obj.user_id:
        user_info = choices.get('user')
        if user_info:
            user_info['readonly'] = True
            user_info['required'] = True
            user_info['choices'] = [
                {'value': obj.user_id, 'label': str(obj.user)},
            ]
    return choices


def get_field_choices(meta: ModelAdminMeta, *, for_edit=False):
    model = meta.model
    choices = {}
    skip = _crud_form_skip_fields(meta, for_edit=for_edit)
    for f in model._meta.get_fields():
        if not getattr(f, 'concrete', False):
            continue
        if f.name in skip:
            continue
        slug_source = get_slug_source_field(model) if f.name == SLUG_FIELD else None
        info = {
            'name': f.name,
            'type': f.get_internal_type(),
            'required': not f.blank and not f.null and not getattr(f, 'auto_created', False),
            'readonly': f.name in meta.readonly_fields or bool(slug_source),
        }
        if slug_source:
            info['auto_slug_from'] = slug_source
            info['required'] = False
        if getattr(f, 'choices', None):
            info['choices'] = [{'value': c[0], 'label': c[1]} for c in f.choices]
        if isinstance(f, (models.ForeignKey, models.OneToOneField)):
            related = f.related_model
            qs = related.objects.all()[:200]
            info['choices'] = [{'value': o.pk, 'label': str(o)} for o in qs]
            info['type'] = 'ForeignKey'
        if isinstance(f, models.ManyToManyField):
            related = f.related_model
            qs = related.objects.all()[:200]
            info['choices'] = [{'value': o.pk, 'label': str(o)} for o in qs]
            info['type'] = 'ManyToManyField'
        elif type(f).__name__ == 'RichTextUploadingField':
            info['type'] = 'RichTextField'
        choices[f.name] = info
    if meta.model == User and not for_edit:
        choices['password'] = {
            'name': 'password',
            'type': 'CharField',
            'required': True,
            'readonly': False,
        }
    return choices


def queryset_for_meta(meta: ModelAdminMeta, request):
    qs = meta.model.objects.all()
    if meta.key == 'accounts.profile':
        qs = qs.select_related('user')
    for f in meta.model._meta.get_fields():
        if isinstance(f, models.ForeignKey) or isinstance(f, models.OneToOneField):
            if f.name in meta.list_display or f.name in meta.list_filter:
                qs = qs.select_related(f.name)
    return qs


def apply_filters(meta: ModelAdminMeta, qs, params):
    q = (params.get('q') or '').strip()
    if q:
        try:
            q = sanitize_plain_text(q, max_length=200, field_label='Search')
        except Exception:
            return qs.none()
    if q and meta.search_fields:
        q_obj = models.Q()
        for name in meta.search_fields:
            if '__' in name:
                q_obj |= models.Q(**{f'{name}__icontains': q})
            else:
                q_obj |= models.Q(**{f'{name}__icontains': q})
        qs = qs.filter(q_obj)

    for name in meta.list_filter:
        val = params.get(f'filter_{name}')
        if val in (None, ''):
            continue
        field = meta.model._meta.get_field(name)
        if isinstance(field, models.BooleanField):
            qs = qs.filter(**{name: val.lower() in ('1', 'true', 'yes')})
        elif isinstance(field, models.ForeignKey):
            try:
                qs = qs.filter(**{name: int(val)})
            except (TypeError, ValueError):
                pass
        else:
            qs = qs.filter(**{name: val})
    return qs


def paginate_queryset(qs, page):
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(page)
    return page_obj, paginator


def list_rows(meta: ModelAdminMeta, request):
    qs = queryset_for_meta(meta, request)
    qs = apply_filters(meta, qs, request.GET)
    order = request.GET.get('order', '-pk')
    allowed = set(meta.list_display) | {meta.model._meta.pk.name}
    order_field = order.lstrip('-')
    if order_field in allowed or order_field == 'pk':
        qs = qs.order_by(order)
    else:
        qs = qs.order_by('-pk')

    page_num = request.GET.get('page', 1)
    page_obj, paginator = paginate_queryset(qs, page_num)
    field_map = {f.name: f for f in meta.model._meta.fields}
    rows = []
    for o in page_obj:
        row = serialize_instance(meta, o, fields=meta.list_display)
        for name in meta.list_display:
            if name in field_map:
                try:
                    row[name] = _format_list_value(field_map[name], getattr(o, name))
                except Exception:
                    pass
        rows.append(row)
    return {
        'rows': rows,
        'columns': meta.list_display,
        'page': page_obj.number,
        'pages': paginator.num_pages,
        'total': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    }


def _is_rich_text_field(field):
    return type(field).__name__ == 'RichTextUploadingField'


def _field_label(name):
    return name.replace('_', ' ').title()


def _coerce_data(meta: ModelAdminMeta, data):
    cleaned = {}
    field_errors = {}
    for key, val in data.items():
        if val is None:
            continue
        try:
            field = meta.model._meta.get_field(key)
        except Exception:
            cleaned[key] = val
            continue
        try:
            if isinstance(field, models.ManyToManyField):
                if isinstance(val, str):
                    val = [v for v in val.split(',') if v.strip()]
                cleaned[key] = val
            elif isinstance(field, models.BooleanField):
                cleaned[key] = val in (True, 'true', '1', 'on', 'yes', 1)
            elif isinstance(field, models.ForeignKey):
                cleaned[key] = val or None
            elif isinstance(val, str) and isinstance(field, models.SlugField):
                from django.utils.text import slugify

                max_len = field.max_length or 50
                cleaned[key] = slugify(val)[:max_len]
            elif isinstance(val, str) and isinstance(field, (models.CharField, models.TextField)):
                label = _field_label(key)
                if _is_rich_text_field(field):
                    cleaned[key] = sanitize_rich_text(
                        val,
                        max_length=getattr(field, 'max_length', None),
                        field_label=label,
                    )
                else:
                    cleaned[key] = sanitize_plain_text(
                        val,
                        max_length=field.max_length,
                        multiline=isinstance(field, models.TextField),
                        field_label=label,
                    )
            else:
                cleaned[key] = val
        except (ValidationError, UnsafeInputError) as exc:
            msgs = list(getattr(exc, 'messages', None) or [str(exc)])
            field_errors[key] = msgs
    if field_errors:
        first_key = next(iter(field_errors))
        first_msg = field_errors[first_key][0]
        return cleaned, {
            'field_errors': field_errors,
            'non_field_errors': [],
            'message': f'{_field_label(first_key)}: {first_msg}',
        }
    return cleaned, None


def save_instance(meta: ModelAdminMeta, data, instance=None, files=None):
    previous_response = ''
    if meta.key == 'core.contact' and instance is not None:
        previous_response = (instance.admin_response or '').strip()

    form_class = get_form_class(meta)
    payload, coercion_errors = _coerce_data(meta, dict(data))
    if coercion_errors:
        return None, coercion_errors
    payload = apply_auto_slug_to_payload(meta, payload, instance=instance)
    for hidden in CRUD_FORM_HIDDEN_FIELDS:
        payload.pop(hidden, None)
    if meta.key == 'accounts.profile' and instance is not None:
        payload.setdefault('user', instance.user_id)
    password = payload.pop('password', None) if meta.model == User else None
    if meta.model == User and instance is None and not password:
        return None, {'password': ['Password is required for new users.']}
    form = form_class(payload, files=files, instance=instance)
    if not form.is_valid():
        return None, normalize_form_errors(form)
    obj = form.save(commit=False)
    if meta.model == User:
        if password:
            obj.password = make_password(password)
        _apply_user_role_flags(obj)
    obj.save()
    form.save_m2m()
    if meta.model == User:
        Profile.objects.get_or_create(user=obj)

    if meta.key == 'core.contact' and instance is not None:
        try:
            maybe_send_contact_admin_reply(obj, previous_response=previous_response)
        except Exception as exc:
            return None, {'admin_response': [f'Could not send reply email: {exc}']}

    return obj, None


def _apply_user_role_flags(user):
    """Keep role, is_superuser, and is_staff aligned."""
    if user.role == UserModel.Role.SUPER_ADMIN:
        user.is_superuser = True
        user.is_staff = True
    elif user.role == UserModel.Role.VENDOR:
        user.is_superuser = False
    elif user.role == UserModel.Role.USER:
        user.is_superuser = False


def dashboard_stats():
    from apps.core.models import Contact, Post, VenueBooking
    from apps.blogs.models import Blog
    from apps.accounts.models import Profile

    now = timezone.now()
    week_ago = now - timedelta(days=7)

    users_total = User.objects.count()
    users_week = User.objects.filter(created_at__gte=week_ago).count()
    posts_total = Post.objects.count()
    posts_open = Post.objects.filter(event_status=Post.STATUS_OPEN).count()
    posts_confirmed = Post.objects.filter(event_status=Post.STATUS_CONFIRMED).count()
    blogs_total = Blog.objects.count()
    bookings_pending = VenueBooking.objects.filter(status=VenueBooking.STATUS_PENDING).count()
    contacts_new = Contact.objects.filter(created_at__gte=week_ago).count()
    profiles_unverified = User.objects.filter(is_email_verified=False).count()

    users_by_day = list(
        User.objects.filter(created_at__gte=now - timedelta(days=30))
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    posts_by_status = list(
        Post.objects.values('event_status').annotate(count=Count('id')).order_by('event_status')
    )
    posts_by_month = list(
        Post.objects.annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')[:12]
    )
    bookings_by_status = list(
        VenueBooking.objects.values('status').annotate(count=Count('id')).order_by('status')
    )

    def _fmt_day(rows, key='day'):
        return {
            'labels': [r[key].strftime('%b %d') if r[key] else '' for r in rows],
            'values': [r['count'] for r in rows],
        }

    return {
        'cards': [
            {'label': 'Users', 'value': users_total, 'sub': f'+{users_week} this week', 'color': 'sky'},
            {'label': 'Posts', 'value': posts_total, 'sub': f'{posts_open} open · {posts_confirmed} confirmed', 'color': 'emerald'},
            {'label': 'Blogs', 'value': blogs_total, 'sub': 'Published articles', 'color': 'violet'},
            {'label': 'Pending bookings', 'value': bookings_pending, 'sub': 'Venue requests', 'color': 'amber'},
            {'label': 'New contacts', 'value': contacts_new, 'sub': 'Last 7 days', 'color': 'rose'},
            {'label': 'Unverified emails', 'value': profiles_unverified, 'sub': 'User accounts', 'color': 'slate'},
        ],
        'charts': {
            'users_daily': _fmt_day(users_by_day),
            'posts_status': {
                'labels': [r['event_status'] for r in posts_by_status],
                'values': [r['count'] for r in posts_by_status],
            },
            'posts_monthly': _fmt_day(posts_by_month, key='month'),
            'bookings_status': {
                'labels': [r['status'] for r in bookings_by_status],
                'values': [r['count'] for r in bookings_by_status],
            },
        },
        'registry_count': len(get_registry()),
    }


def recent_activity(limit=12):
    """Recent rows for dashboard activity feed."""
    from apps.core.models import Contact, Post, VenueBooking
    from apps.blogs.models import Blog

    items = []
    for p in Post.objects.select_related('author').order_by('-created_at')[:limit]:
        items.append({
            'type': 'post',
            'title': f'New post · {p.slug}',
            'meta': p.author.username if p.author_id else '—',
            'time': p.created_at.isoformat() if p.created_at else '',
            'status': p.event_status,
            'url': '/iamadmin/core.post/',
        })
    for b in VenueBooking.objects.select_related('user', 'venue').order_by('-created_at')[:8]:
        items.append({
            'type': 'booking',
            'title': f'Booking · {b.venue.name}',
            'meta': b.user.username,
            'time': b.created_at.isoformat() if b.created_at else '',
            'status': b.status,
            'url': '/iamadmin/core.venuebooking/',
        })
    for c in Contact.objects.order_by('-created_at')[:5]:
        items.append({
            'type': 'contact',
            'title': f'Contact · {c.fullname}',
            'meta': f'{c.get_subject_display()} · {c.email}',
            'time': c.created_at.isoformat() if c.created_at else '',
            'status': c.status,
            'url': f'/iamadmin/core.contact/?edit={c.pk}',
        })
    for bl in Blog.objects.select_related('author').order_by('-created_at')[:5]:
        items.append({
            'type': 'blog',
            'title': f'Blog · {bl.title[:40]}',
            'meta': bl.author.username if bl.author_id else '—',
            'time': bl.created_at.isoformat() if bl.created_at else '',
            'status': 'published',
            'url': '/iamadmin/blogs.blog/',
        })
    items.sort(key=lambda x: x['time'], reverse=True)
    return items[:limit]


def analytics_stats():
    """Extended analytics for dedicated analytics page."""
    from apps.core.models import Post, VenueBooking, Notification
    from apps.accounts.models import Profile

    base = dashboard_stats()
    now = timezone.now()
    month_ago = now - timedelta(days=30)

    from apps.core.models import PostComment, PostInterest

    engagement = {
        'interests': PostInterest.objects.count(),
        'comments': PostComment.objects.count(),
        'notifications': Notification.objects.filter(created_at__gte=month_ago).count(),
        'verified_users': User.objects.filter(is_email_verified=True).count(),
        'vendors': User.objects.filter(role=UserModel.Role.VENDOR).count(),
        'super_admins': User.objects.filter(role=UserModel.Role.SUPER_ADMIN).count(),
    }
    bookings_trend = list(
        VenueBooking.objects.filter(created_at__gte=month_ago)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    labels = [r['day'].strftime('%b %d') if r['day'] else '' for r in bookings_trend]
    values = [r['count'] for r in bookings_trend]
    base['charts']['bookings_daily'] = {'labels': labels, 'values': values}
    base['engagement'] = engagement
    return base
