from django.contrib.auth import get_user_model

User = get_user_model()
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from django.conf import settings

from apps.accounts.email_utils import send_verification_email_code, send_verification_email_link
from apps.accounts.email_verification import EmailVerificationError, issue_email_code, verify_email_code
from apps.accounts.models import Profile
from apps.accounts.phone_verification import (
    PhoneVerificationError,
    issue_phone_otp,
    profile_for_email,
    verify_phone_otp,
)
from apps.api.permissions import IsEmailVerified
from apps.api.serializers import (
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PhoneSendOtpSerializer,
    PhoneVerifyOtpSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    UserMeSerializer,
    UserProfileUpdateSerializer,
    VerifyEmailSerializer,
)


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        profile = Profile.objects.get(user=user)
        return Response({
            'success': True,
            'message': 'Account created. Check your email for a verification code (step 1).',
            'user_id': user.pk,
            'email': user.email,
            'phone': profile.phone,
        }, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        return Response({
            'success': True,
            'tokens': _tokens_for_user(user),
            'user': UserMeSerializer(user, context={'request': request}).data,
        })


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def get(self, request):
        return Response(UserMeSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        serializer = UserProfileUpdateSerializer(
            request.user, data=request.data, partial=True, context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'success': True,
            'user': UserMeSerializer(user, context={'request': request}).data,
        })


class VerificationStatusAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        email = (request.query_params.get('email') or '').strip().lower()
        if not email:
            return Response(
                {'success': False, 'error': 'Email is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return Response(
                {'success': False, 'error': 'Account not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        profile = Profile.objects.get(user=user)
        return Response({
            'success': True,
            'email': user.email,
            'phone': profile.phone,
            'email_verified': user.is_email_verified,
            'phone_verified': profile.phone_verified,
        })


class VerifyEmailAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        token = (data.get('token') or '').strip()
        code = (data.get('code') or '').strip()
        email = (data.get('email') or '').strip().lower()

        if token:
            profile = Profile.objects.filter(email_verification_token=token).first()
            if profile is None:
                return Response(
                    {'success': False, 'error': 'Invalid or expired verification link.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            already = profile.user.is_email_verified
            if not already:
                profile.mark_email_verified()
            return Response({
                'success': True,
                'already_verified': already,
                'email_verified': True,
                'phone_verified': profile.phone_verified,
                'message': 'Email verified. Continue to phone verification.',
            })

        from apps.accounts.phone_verification import profile_for_email

        try:
            profile = profile_for_email(email)
            already = profile.user.is_email_verified
            if not already:
                verify_email_code(profile, code)
            profile.refresh_from_db()
            return Response({
                'success': True,
                'already_verified': already,
                'email_verified': profile.user.is_email_verified,
                'phone_verified': profile.phone_verified,
                'message': 'Email verified. Continue to phone verification.',
            })
        except EmailVerificationError as exc:
            return Response(
                {'success': False, 'error': str(exc), 'code': exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PhoneSendOtpAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PhoneSendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = (serializer.validated_data.get('email') or '').strip().lower()
        phone = serializer.validated_data.get('phone') or ''
        if request.user.is_authenticated:
            email = request.user.email
            if not phone:
                phone = request.user.profile.phone
        try:
            profile = profile_for_email(email) if email else None
            if profile is None and request.user.is_authenticated:
                profile = Profile.objects.get(user=request.user)
            if profile is None:
                return Response(
                    {'success': False, 'error': 'Email is required.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not profile.user.is_email_verified:
                return Response(
                    {'success': False, 'error': 'Verify your email before verifying your phone.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            dev_code = issue_phone_otp(profile, phone)
            payload = {'success': True, 'message': 'Verification code sent via SMS.'}
            if dev_code and settings.DEBUG:
                payload['dev_code'] = dev_code
            return Response(payload)
        except PhoneVerificationError as exc:
            return Response(
                {'success': False, 'error': str(exc), 'code': exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PhoneVerifyOtpAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PhoneVerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = (serializer.validated_data.get('email') or '').strip().lower()
        phone = serializer.validated_data.get('phone') or ''
        code = serializer.validated_data['code']
        if request.user.is_authenticated:
            email = request.user.email
            if not phone:
                phone = request.user.profile.phone
        try:
            profile = profile_for_email(email) if email else None
            if profile is None and request.user.is_authenticated:
                profile = Profile.objects.get(user=request.user)
            if profile is None:
                return Response(
                    {'success': False, 'error': 'Email is required.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            verify_phone_otp(profile, phone, code)
            return Response({'success': True, 'message': 'Phone number verified.'})
        except PhoneVerificationError as exc:
            return Response(
                {'success': False, 'error': str(exc), 'code': exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ResendVerificationAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = (serializer.validated_data.get('email') or '').strip().lower()
        if request.user.is_authenticated:
            email = request.user.email
        if not email:
            return Response(
                {'success': False, 'error': 'Email is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return Response({
                'success': True,
                'message': 'If an account exists, a verification email has been sent.',
            })
        profile = Profile.objects.get(user=user)
        if user.is_email_verified:
            return Response({
                'success': True,
                'message': 'This email is already verified.',
            })
        delivery = serializer.validated_data.get('delivery') or 'link'
        try:
            if delivery == 'code':
                code = issue_email_code(profile)
                send_verification_email_code(user, profile, code)
                payload = {'success': True, 'message': 'Verification code sent to your email.'}
                if code and settings.DEBUG:
                    payload['dev_code'] = code
                return Response(payload)
            send_verification_email_link(user, profile)
        except Exception:
            return Response(
                {'success': False, 'error': 'Could not send email. Try again later.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({
            'success': True,
            'message': 'Verification email sent.',
        })


class PasswordChangeAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.validated_data['form'].save()
        return Response({'success': True, 'message': 'Password changed successfully.'})


class PasswordResetRequestAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from apps.accounts.forms import StyledPasswordResetForm

        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        form = StyledPasswordResetForm(data={'email': serializer.validated_data['email']})
        if form.is_valid():
            from futnetnepal.email import base_email_context

            form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name='accounts/email/password_reset_email.txt',
                subject_template_name='accounts/email/password_reset_subject.txt',
                html_email_template_name='accounts/email/password_reset_email.html',
                extra_email_context=base_email_context(),
            )
        return Response({
            'success': True,
            'message': 'If an account exists for that email, a reset link has been sent.',
        })


class PasswordResetConfirmAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data['form'].save()
        return Response({
            'success': True,
            'message': 'Password reset successfully. You can log in now.',
        })


class TokenRefreshAPIView(TokenRefreshView):
    permission_classes = [AllowAny]
