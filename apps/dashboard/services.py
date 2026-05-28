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

from apps.dashboard.registry import ModelAdminMeta, get_model_meta, get_registry

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


def serialize_instance(meta: ModelAdminMeta, obj, *, fields=None, for_edit=False):
    model = meta.model
    if for_edit or fields is None:
        field_names = [f.name for f in model._meta.fields]
    else:
        field_names = fields
    data = {'id': obj.pk}
    for name in field_names:
        if name == 'id':
            continue
        try:
            data[name] = _serialize_value(getattr(obj, name))
        except Exception:
            data[name] = ''
    if for_edit:
        for f in model._meta.many_to_many:
            data[f.name] = list(getattr(obj, f.name).values_list('pk', flat=True))
    data['__str__'] = str(obj)
    return data


def get_form_class(meta: ModelAdminMeta):
    from django import forms

    model = meta.model
    readonly = set(meta.readonly_fields)
    exclude = set(meta.exclude_fields)

    class DynamicAdminForm(ModelForm):
        class Meta:
            model = model
            fields = '__all__'
            exclude = list(exclude) if exclude else None

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for name, field in self.fields.items():
                if name in readonly:
                    field.disabled = True
                css = 'fn-input w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 text-sm'
                if isinstance(field.widget, forms.Textarea):
                    field.widget.attrs['class'] = css + ' min-h-[100px]'
                elif not isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs['class'] = css
            for f in model._meta.get_fields():
                if f.name in self.fields and 'ckeditor' in type(f).__module__:
                    self.fields[f.name].widget = forms.Textarea(attrs={
                        'class': 'fn-input w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 text-sm min-h-[200px]',
                        'rows': 10,
                    })

    if model == User:
        class UserAdminForm(DynamicAdminForm):
            password = forms.CharField(
                required=False,
                widget=PasswordInput(render_value=False),
                help_text='Required for new users. Leave blank to keep existing.',
            )

            class Meta(DynamicAdminForm.Meta):
                exclude = list(exclude) if exclude else None

        return UserAdminForm

    return DynamicAdminForm


def get_field_choices(meta: ModelAdminMeta):
    model = meta.model
    choices = {}
    for f in model._meta.get_fields():
        if not getattr(f, 'concrete', False):
            continue
        info = {
            'name': f.name,
            'type': f.get_internal_type(),
            'required': not f.blank and not f.null and not getattr(f, 'auto_created', False),
            'readonly': f.name in meta.readonly_fields,
        }
        if getattr(f, 'choices', None):
            info['choices'] = [{'value': c[0], 'label': c[1]} for c in f.choices]
        if isinstance(f, models.ForeignKey):
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
            info['type'] = 'TextField'
        choices[f.name] = info
    return choices


def queryset_for_meta(meta: ModelAdminMeta, request):
    qs = meta.model.objects.all()
    for f in meta.model._meta.get_fields():
        if isinstance(f, models.ForeignKey) or isinstance(f, models.OneToOneField):
            if f.name in meta.list_display or f.name in meta.list_filter:
                qs = qs.select_related(f.name)
    return qs


def apply_filters(meta: ModelAdminMeta, qs, params):
    q = (params.get('q') or '').strip()
    if q and meta.search_fields:
        q_obj = models.Q()
        for name in meta.search_fields:
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
    rows = [serialize_instance(meta, o, fields=meta.list_display) for o in page_obj]
    return {
        'rows': rows,
        'columns': meta.list_display,
        'page': page_obj.number,
        'pages': paginator.num_pages,
        'total': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    }


def _coerce_data(meta: ModelAdminMeta, data):
    cleaned = {}
    for key, val in data.items():
        if val is None:
            continue
        try:
            field = meta.model._meta.get_field(key)
        except Exception:
            cleaned[key] = val
            continue
        if isinstance(field, models.ManyToManyField):
            if isinstance(val, str):
                val = [v for v in val.split(',') if v.strip()]
            cleaned[key] = val
        elif isinstance(field, models.BooleanField):
            cleaned[key] = val in (True, 'true', '1', 'on', 'yes', 1)
        elif isinstance(field, models.ForeignKey):
            cleaned[key] = val or None
        else:
            cleaned[key] = val
    return cleaned


def save_instance(meta: ModelAdminMeta, data, instance=None, files=None):
    form_class = get_form_class(meta)
    payload = _coerce_data(meta, dict(data))
    password = payload.pop('password', None) if meta.model == User else None
    if meta.model == User and instance is None and not password:
        return None, {'password': ['Password is required for new users.']}
    form = form_class(payload, files=files, instance=instance)
    if not form.is_valid():
        return None, form.errors.as_json() if hasattr(form.errors, 'as_json') else form.errors
    obj = form.save(commit=False)
    if meta.model == User and password:
        obj.password = make_password(password)
    obj.save()
    form.save_m2m()
    return obj, None


def dashboard_stats():
    from apps.core.models import Contact, Post, VenueBooking
    from apps.blogs.models import Blog
    from apps.accounts.models import Profile

    now = timezone.now()
    week_ago = now - timedelta(days=7)

    users_total = User.objects.count()
    users_week = User.objects.filter(date_joined__gte=week_ago).count()
    posts_total = Post.objects.count()
    posts_open = Post.objects.filter(event_status=Post.STATUS_OPEN).count()
    posts_confirmed = Post.objects.filter(event_status=Post.STATUS_CONFIRMED).count()
    blogs_total = Blog.objects.count()
    bookings_pending = VenueBooking.objects.filter(status=VenueBooking.STATUS_PENDING).count()
    contacts_new = Contact.objects.filter(created_at__gte=week_ago).count()
    profiles_unverified = Profile.objects.filter(email_verified=False).count()

    users_by_day = list(
        User.objects.filter(date_joined__gte=now - timedelta(days=30))
        .annotate(day=TruncDate('date_joined'))
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
            {'label': 'Unverified emails', 'value': profiles_unverified, 'sub': 'Profiles', 'color': 'slate'},
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
            'meta': c.email,
            'time': c.created_at.isoformat() if c.created_at else '',
            'status': 'new',
            'url': '/iamadmin/core.contact/',
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
        'verified_profiles': Profile.objects.filter(email_verified=True).count(),
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
