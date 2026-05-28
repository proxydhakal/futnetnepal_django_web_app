from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.email_utils import send_verification_email_link
from apps.accounts.phone_verification import (
    PhoneVerificationError,
    issue_phone_otp,
    profile_for_email,
    verify_phone_otp,
)
from apps.accounts.forms import (
    LoginForm,
    RegisterForm,
    UserProfileUpdateForm,
    UserUpdateForm,
)
from apps.accounts.models import Profile
from apps.accounts.stats import user_profile_stats
from apps.core.engagement import posts_with_engagement
from apps.core.models import Location, Time, Venue
from django.db.models import Count


def _profile_context(request, user_profile):
    return {
        'stats': user_profile_stats(request.user),
        'posts': posts_with_engagement(request.user).filter(author=request.user),
        'userprofiledata': user_profile,
        'times': Time.objects.values('id', 'name').annotate(total=Count('post')),
        'venues': Venue.objects.select_related('location').all(),
        'timess': Time.objects.all(),
        'locations': Location.objects.all(),
        'user_form': UserUpdateForm(instance=request.user),
        'profile_form': UserProfileUpdateForm(instance=user_profile),
    }


class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            if request.user.profile.email_verified and (
                not request.user.profile.phone or request.user.profile.phone_verified
            ):
                return redirect(settings.LOGIN_REDIRECT_URL)
            return redirect('accounts:verify_account')
        return render(request, self.template_name, {'form': LoginForm(request)})

    def post(self, request):
        if request.user.is_authenticated:
            if request.user.profile.email_verified:
                return redirect(settings.LOGIN_REDIRECT_URL)
            return redirect('accounts:verify_email_pending')
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, 'Welcome back!')
            next_url = request.GET.get('next') or settings.LOGIN_REDIRECT_URL
            return redirect(next_url)
        user = getattr(form, 'user_cache', None)
        if user is not None and hasattr(user, 'profile') and not user.profile.email_verified:
            request.session['pending_verify_email'] = user.email
            request.session['pending_verify_phone'] = user.profile.phone or ''
            messages.warning(
                request,
                'Please verify your email before logging in. '
                'We can send you a new link from the next page.',
            )
            return redirect('accounts:verify_account')
        if user is not None and hasattr(user, 'profile') and user.profile.phone and not user.profile.phone_verified:
            request.session['pending_verify_email'] = user.email
            request.session['pending_verify_phone'] = user.profile.phone
            messages.warning(request, 'Please verify your phone number before logging in.')
            return redirect('accounts:verify_account')
        return render(request, self.template_name, {'form': form})


class RegisterView(View):
    template_name = 'accounts/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            if request.user.profile.email_verified:
                return redirect(settings.LOGIN_REDIRECT_URL)
            return redirect('accounts:verify_email_pending')
        return render(request, self.template_name, {'form': RegisterForm()})

    def post(self, request):
        if request.user.is_authenticated:
            if request.user.profile.email_verified:
                return redirect(settings.LOGIN_REDIRECT_URL)
            return redirect('accounts:verify_email_pending')
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            profile = Profile.objects.get(user=user)
            try:
                send_verification_email_link(user, profile)
            except Exception:
                messages.error(
                    request,
                    'Account created but we could not send the verification email. '
                    'Use “Resend verification email” on the next page.',
                )
            request.session['pending_verify_email'] = user.email
            request.session['pending_verify_phone'] = profile.phone
            messages.success(
                request,
                'Account created! Verify your email first, then your phone.',
            )
            return redirect('accounts:verify_account')
        return render(request, self.template_name, {'form': form})


class SignupEmailSentView(TemplateView):
    template_name = 'accounts/signup_email_sent.html'


class VerifyAccountView(View):
    """Email + phone verification after signup (before login)."""

    template_name = 'accounts/verify_account.html'

    def get(self, request):
        email = request.session.get('pending_verify_email', '')
        phone = request.session.get('pending_verify_phone', '')
        if request.user.is_authenticated:
            email = request.user.email
            phone = request.user.profile.phone or phone
        profile = None
        if email:
            user = User.objects.filter(email__iexact=email).first()
            if user:
                profile = Profile.objects.get(user=user)
        return render(request, self.template_name, {
            'email': email,
            'phone': phone,
            'email_verified': profile.email_verified if profile else False,
            'phone_verified': profile.phone_verified if profile else False,
        })


class PhoneSendOtpView(View):
    def post(self, request):
        email = (request.POST.get('email') or '').strip().lower()
        phone = request.POST.get('phone') or ''
        if request.user.is_authenticated:
            email = request.user.email
            if not phone:
                phone = request.user.profile.phone
        try:
            profile = profile_for_email(email) if email else None
            if profile is None and request.user.is_authenticated:
                profile = Profile.objects.get(user=request.user)
            if profile is None:
                return JsonResponse({'success': False, 'error': 'Email is required.'}, status=400)
            if not profile.email_verified:
                return JsonResponse(
                    {'success': False, 'error': 'Verify your email before verifying your phone.'},
                    status=400,
                )
            dev_code = issue_phone_otp(profile, phone)
            payload = {'success': True, 'message': 'Verification code sent via SMS.'}
            if dev_code and settings.DEBUG:
                payload['dev_code'] = dev_code
            return JsonResponse(payload)
        except PhoneVerificationError as exc:
            return JsonResponse({'success': False, 'error': str(exc), 'code': exc.code}, status=400)

    def dispatch(self, request, *args, **kwargs):
        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=405)
        return super().dispatch(request, *args, **kwargs)


class PhoneVerifyOtpView(View):
    def post(self, request):
        email = (request.POST.get('email') or '').strip().lower()
        phone = request.POST.get('phone') or ''
        code = request.POST.get('code') or ''
        if request.user.is_authenticated:
            email = request.user.email
            if not phone:
                phone = request.user.profile.phone
        try:
            profile = profile_for_email(email) if email else None
            if profile is None and request.user.is_authenticated:
                profile = Profile.objects.get(user=request.user)
            if profile is None:
                return JsonResponse({'success': False, 'error': 'Email is required.'}, status=400)
            verify_phone_otp(profile, phone, code)
            return JsonResponse({'success': True, 'message': 'Phone number verified.'})
        except PhoneVerificationError as exc:
            return JsonResponse({'success': False, 'error': str(exc), 'code': exc.code}, status=400)

    def dispatch(self, request, *args, **kwargs):
        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=405)
        return super().dispatch(request, *args, **kwargs)


class VerifyEmailPendingView(View):
    template_name = 'accounts/verify_email_pending.html'

    def get(self, request):
        email = request.session.get('pending_verify_email', '')
        if request.user.is_authenticated:
            email = request.user.email
        return render(request, self.template_name, {'email': email})


class ResendVerificationView(View):
    def post(self, request):
        email = (request.POST.get('email') or '').strip().lower()
        if request.user.is_authenticated:
            email = request.user.email
        if not email:
            messages.error(request, 'Please enter your email address.')
            return redirect('accounts:verify_account')
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            messages.info(
                request,
                'If an account exists for that email, a verification link has been sent.',
            )
            return redirect('accounts:verify_account')
        profile = Profile.objects.get(user=user)
        if profile.email_verified:
            messages.info(request, 'This email is already verified. You can log in.')
            return redirect('accounts:login')
        try:
            send_verification_email_link(user, profile)
            request.session['pending_verify_email'] = user.email
            messages.success(request, 'Verification email sent. Check your inbox for the link.')
        except Exception:
            messages.error(
                request,
                'Could not send email. Please try again later or contact support.',
            )
        return redirect('accounts:verify_account')


class VerifyEmailView(View):
    template_success = 'accounts/verify_email_success.html'
    template_invalid = 'accounts/verify_email_invalid.html'

    def get(self, request, token):
        profile = Profile.objects.filter(email_verification_token=token).first()
        if profile is None:
            return render(request, self.template_invalid)
        if profile.email_verified:
            return render(request, self.template_success, {'already_verified': True})
        profile.mark_email_verified()
        request.session.pop('pending_verify_email', None)
        return render(request, self.template_success, {'already_verified': False})


class LogoutView(View):
    def post(self, request):
        logout(request)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'redirect': '/'})
        messages.info(request, 'You have been logged out.')
        return redirect('index')

    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'POST required'}, status=405)
        return redirect('home')


class UserProfileView(LoginRequiredMixin, View):
    template_name = 'accounts/profile.html'

    def get(self, request):
        user_profile = Profile.objects.get(user=request.user)
        context = _profile_context(request, user_profile)
        context['start_editing'] = request.GET.get('edit') == '1'
        return render(request, self.template_name, context)


class ProfileUpdateAjaxView(LoginRequiredMixin, View):
    def post(self, request):
        user_profile = Profile.objects.get(user=request.user)
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileUpdateForm(
            request.POST, request.FILES, instance=user_profile,
        )
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            user_profile = profile_form.save()
            return JsonResponse({
                'success': True,
                'message': 'Profile updated successfully.',
                'user': {
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.get_full_name() or user.username,
                },
                'profile': {
                    'phone': user_profile.phone or '',
                    'phone_verified': user_profile.phone_verified,
                    'address': user_profile.address or '',
                    'dob': user_profile.dob.isoformat() if user_profile.dob else '',
                    'profile_image_url': user_profile.profile_image.url,
                    'cover_image_url': user_profile.cover_image.url,
                },
            })
        errors = {}
        for field, errs in user_form.errors.items():
            errors[f'user_{field}'] = errs
        for field, errs in profile_form.errors.items():
            errors[f'profile_{field}'] = errs
        return JsonResponse({'success': False, 'errors': errors}, status=400)


class EditProfile(LoginRequiredMixin, View):
    """Legacy URL — redirect to unified profile page."""

    def get(self, request, username):
        if request.user.username != username:
            messages.error(request, 'You can only edit your own profile.')
            return redirect('accounts:profile')
        return redirect(reverse('accounts:profile') + '?edit=1')


class PasswordChangeDoneView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/password_change_done.html'
