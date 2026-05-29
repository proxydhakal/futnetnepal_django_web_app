import json

from django.conf import settings as django_settings
from django.utils import timezone
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.dashboard.permissions import StaffRequiredMixin
from apps.dashboard.registry import get_model_meta, get_registry
from apps.dashboard.services import (
    analytics_stats,
    dashboard_stats,
    enrich_edit_field_choices,
    get_field_choices,
    list_rows,
    recent_activity,
    save_instance,
    serialize_instance,
)
from apps.dashboard.slug_fields import generate_unique_slug
from futnetnepal.input_validation import sanitize_plain_text


class StaffLoginView(View):
    template_name = 'admin/auth/login.html'

    def get(self, request):
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            return redirect('dashboard:home')
        return render(request, self.template_name, {'form': AuthenticationForm()})

    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not (user.is_staff or user.is_superuser):
                form.add_error(None, 'Staff access only. Super Admin or staff role required.')
            elif getattr(user, 'status', 'ACTIVE') != 'ACTIVE':
                form.add_error(None, 'This account is not active.')
            else:
                login(request, user)
                return redirect(request.GET.get('next') or 'dashboard:home')
        return render(request, self.template_name, {'form': form})


class StaffRegisterView(View):
    """Info page — admin users are created via createsuperuser or User CRUD."""
    template_name = 'admin/auth/register.html'

    def get(self, request):
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            return redirect('dashboard:home')
        return render(request, self.template_name)


class StaffLogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('dashboard:login')

    def get(self, request):
        return self.post(request)


def _admin_page(request, template, page_id, **extra):
    ctx = {
        'registry': get_registry(),
        'active_page': page_id,
        'active_model': extra.pop('active_model', ''),
        **extra,
    }
    return render(request, template, ctx)


class DashboardHomeView(StaffRequiredMixin, View):
    template_name = 'admin/pages/dashboard.html'

    def get(self, request):
        stats = dashboard_stats()
        return _admin_page(
            request,
            self.template_name,
            'dashboard',
            dashboard_stats=stats,
            recent_activity_items=recent_activity(limit=12),
            now=timezone.now(),
        )


class AnalyticsView(StaffRequiredMixin, View):
    template_name = 'admin/pages/analytics.html'

    def get(self, request):
        return _admin_page(request, self.template_name, 'analytics')


class UsersManagementView(StaffRequiredMixin, View):
    template_name = 'admin/pages/users.html'

    def get(self, request):
        return _admin_page(request, self.template_name, 'users', active_model='accounts.user')


class TransactionsView(StaffRequiredMixin, View):
    template_name = 'admin/pages/transactions.html'

    def get(self, request):
        return _admin_page(request, self.template_name, 'transactions', active_model='core.venuebooking')


class SettingsView(StaffRequiredMixin, View):
    template_name = 'admin/pages/settings.html'

    def get(self, request):
        return _admin_page(request, self.template_name, 'settings', site_settings={
            'debug': django_settings.DEBUG,
            'site_url': getattr(django_settings, 'SITE_URL', ''),
            'allowed_hosts': django_settings.ALLOWED_HOSTS,
        })


class ModelListView(StaffRequiredMixin, View):
    template_name = 'admin/model_list.html'

    def get(self, request, model_key):
        meta = get_model_meta(model_key)
        return _admin_page(
            request, self.template_name, 'data',
            active_model=model_key,
            meta=meta,
            field_choices=get_field_choices(meta),
        )


class StatsAPIView(StaffRequiredMixin, View):
    def get(self, request):
        return JsonResponse(dashboard_stats())


class AnalyticsAPIView(StaffRequiredMixin, View):
    def get(self, request):
        return JsonResponse(analytics_stats())


class ActivityAPIView(StaffRequiredMixin, View):
    def get(self, request):
        return JsonResponse({'items': recent_activity()})


class ModelListAPIView(StaffRequiredMixin, View):
    def get(self, request, model_key):
        meta = get_model_meta(model_key)
        return JsonResponse(list_rows(meta, request))


class ModelDetailAPIView(StaffRequiredMixin, View):
    def get(self, request, model_key, pk):
        meta = get_model_meta(model_key)
        obj = get_object_or_404(meta.model, pk=pk)
        data = serialize_instance(meta, obj, for_edit=True)
        field_choices = get_field_choices(meta, for_edit=True)
        data['fields'] = enrich_edit_field_choices(meta, obj, field_choices)
        return JsonResponse(data)


def _parse_body(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body.decode() or '{}')
        except json.JSONDecodeError:
            return {}
    return request.POST.dict()


class SlugifyAPIView(StaffRequiredMixin, View):
    """Return a unique slug for admin CRUD (debounced from title/name/message)."""

    def post(self, request):
        data = _parse_body(request)
        text = data.get('text', '')
        try:
            text = sanitize_plain_text(str(text), max_length=500, field_label='Title')
        except Exception as exc:
            return JsonResponse({'slug': '', 'error': str(exc)}, status=400)

        model_key = (data.get('model_key') or '').strip()
        instance_pk = data.get('instance_pk') or None
        if instance_pk in ('', None):
            instance_pk = None

        if model_key:
            try:
                meta = get_model_meta(model_key)
            except LookupError:
                return JsonResponse({'error': 'Unknown model'}, status=400)
            slug = generate_unique_slug(text, meta.model, instance_pk=instance_pk)
        else:
            from django.utils.text import slugify

            slug = slugify(text)[:220] or 'item'

        return JsonResponse({'slug': slug})


class ModelCreateAPIView(StaffRequiredMixin, View):
    def post(self, request, model_key):
        meta = get_model_meta(model_key)
        data = _parse_body(request)
        obj, errors = save_instance(meta, data, files=request.FILES or None)
        if errors:
            return JsonResponse({'success': False, 'errors': errors}, status=400)
        return JsonResponse({'success': True, 'item': serialize_instance(meta, obj)})


class ModelUpdateAPIView(StaffRequiredMixin, View):
    def post(self, request, model_key, pk):
        meta = get_model_meta(model_key)
        obj = get_object_or_404(meta.model, pk=pk)
        data = _parse_body(request)
        obj, errors = save_instance(meta, data, instance=obj, files=request.FILES or None)
        if errors:
            return JsonResponse({'success': False, 'errors': errors}, status=400)
        return JsonResponse({'success': True, 'item': serialize_instance(meta, obj)})


class ModelDeleteAPIView(StaffRequiredMixin, View):
    def post(self, request, model_key, pk):
        meta = get_model_meta(model_key)
        obj = get_object_or_404(meta.model, pk=pk)
        obj.delete()
        return JsonResponse({'success': True})
