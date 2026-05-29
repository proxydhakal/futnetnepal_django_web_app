from django.contrib.auth import views as auth_views
from django.urls import path

from apps.accounts.forms import (
    StyledPasswordChangeForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)
from apps.accounts.views import (
    BrandedPasswordResetView,
    EditProfile,
    LoginView,
    LogoutView,
    PasswordChangeDoneView,
    PhoneSendOtpView,
    PhoneVerifyOtpView,
    ProfileUpdateAjaxView,
    PasswordCheckView,
    RegisterView,
    ResendVerificationView,
    SignupEmailSentView,
    UserProfileView,
    VerifyAccountView,
    VerifyEmailPendingView,
    VerifyEmailView,
)

app_name = 'accounts'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('signup/', RegisterView.as_view(), name='signup'),
    path('signup/password-check/', PasswordCheckView.as_view(), name='password_check'),
    path('signup/sent/', SignupEmailSentView.as_view(), name='signup_email_sent'),
    path('verify-account/', VerifyAccountView.as_view(), name='verify_account'),
    path('verify-phone/send/', PhoneSendOtpView.as_view(), name='phone_send_otp'),
    path('verify-phone/confirm/', PhoneVerifyOtpView.as_view(), name='phone_verify_otp'),
    path('verify-email/', VerifyEmailPendingView.as_view(), name='verify_email_pending'),
    path('verify-email/resend/', ResendVerificationView.as_view(), name='resend_verification'),
    path('verify/<str:token>/', VerifyEmailView.as_view(), name='verify_email'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileUpdateAjaxView.as_view(), name='profile_update'),
    path('edit/<str:username>/', EditProfile.as_view(), name='updateprofile'),
    path(
        'password/change/',
        auth_views.PasswordChangeView.as_view(
            template_name='accounts/password_change.html',
            form_class=StyledPasswordChangeForm,
            success_url='/accounts/password/change/done/',
        ),
        name='password_change',
    ),
    path(
        'password/change/done/',
        PasswordChangeDoneView.as_view(),
        name='password_change_done',
    ),
    path(
        'password/reset/',
        BrandedPasswordResetView.as_view(
            template_name='accounts/password_reset.html',
            form_class=StyledPasswordResetForm,
            email_template_name='accounts/email/password_reset_email.txt',
            subject_template_name='accounts/email/password_reset_subject.txt',
            success_url='/accounts/password/reset/done/',
            html_email_template_name='accounts/email/password_reset_email.html',
        ),
        name='password_reset',
    ),
    path(
        'password/reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'password/reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            form_class=StyledSetPasswordForm,
            success_url='/accounts/password/reset/complete/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'password/reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
]
