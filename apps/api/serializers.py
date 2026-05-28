from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers

from apps.accounts.email_utils import send_verification_email_code, send_verification_email_link
from apps.accounts.email_verification import EmailVerificationError, issue_email_code, verify_email_code
from apps.accounts.forms import RegisterForm, UserProfileUpdateForm, UserUpdateForm
from apps.accounts.models import Profile
from apps.accounts.phone_verification import PhoneVerificationError, issue_phone_otp
from apps.accounts.stats import user_profile_stats
from apps.blogs.models import Blog, Category, Tag
from apps.core.forms import ContactForm, UserPostForm, VenueBookingForm
from apps.core.models import (
    Contact,
    DirectConversation,
    EventChatMessage,
    Location,
    Notification,
    Post,
    Time,
    Venue,
    VenueBooking,
)


def _validate_django_form(form):
    """Raise DRF ValidationError from a Django Form (no raise_exception on Form)."""
    if not form.is_valid():
        raise serializers.ValidationError(form.errors)


def absolute_media_url(request, field):
    if not field:
        return None
    url = field.url
    if request:
        return request.build_absolute_uri(url)
    return url


class UserBriefSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'full_name', 'avatar_url')

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_avatar_url(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile and profile.profile_image:
            return absolute_media_url(self.context.get('request'), profile.profile_image)
        return None


class ProfileSerializer(serializers.ModelSerializer):
    profile_image_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            'phone', 'address', 'dob', 'email_verified', 'phone_verified',
            'profile_image_url', 'cover_image_url',
        )
        read_only_fields = ('email_verified', 'phone_verified')

    def get_profile_image_url(self, obj):
        return absolute_media_url(self.context.get('request'), obj.profile_image)

    def get_cover_image_url(self, obj):
        return absolute_media_url(self.context.get('request'), obj.cover_image)


class UserMeSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    stats = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'profile', 'stats',
        )
        read_only_fields = ('id', 'username', 'email')

    def get_stats(self, obj):
        return user_profile_stats(obj)


class UserProfileUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    full_name = serializers.CharField(max_length=300, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=10, required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    dob = serializers.DateField(required=False, allow_null=True)
    profile_image = serializers.ImageField(required=False)
    cover_image = serializers.ImageField(required=False)

    def update(self, instance, validated_data):
        user = instance
        profile = user.profile
        user_data = {}
        for key in ('username', 'email', 'full_name', 'first_name'):
            if key in validated_data:
                user_data[key] = validated_data[key]
        if user_data:
            user_form = UserUpdateForm(user_data, instance=user)
            _validate_django_form(user_form)
            user = user_form.save()

        profile_data = {}
        for key in ('phone', 'address', 'dob'):
            if key in validated_data:
                profile_data[key] = validated_data[key]
        files = {}
        if 'profile_image' in validated_data:
            files['profile_image'] = validated_data['profile_image']
        if 'cover_image' in validated_data:
            files['cover_image'] = validated_data['cover_image']
        if profile_data or files:
            profile_form = UserProfileUpdateForm(profile_data, files=files or None, instance=profile)
            _validate_django_form(profile_form)
            profile_form.save()
        return user


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=10)
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        form = RegisterForm(data=attrs)
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)
        attrs['form'] = form
        return attrs

    def create(self, validated_data):
        user = validated_data['form'].save()
        profile = Profile.objects.get(user=user)
        try:
            code = issue_email_code(profile)
            send_verification_email_code(user, profile, code)
        except Exception:
            pass
        return user


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context.get('request')
        user = authenticate(
            request,
            login=attrs['login'].strip(),
            password=attrs['password'],
        )
        if user is None:
            raise serializers.ValidationError('Invalid username/email or password.')
        profile = getattr(user, 'profile', None)
        if profile is not None and not profile.email_verified:
            raise serializers.ValidationError(
                'Please verify your email before logging in.',
                code='email_unverified',
            )
        if profile is not None and profile.phone and not profile.phone_verified:
            raise serializers.ValidationError(
                'Please verify your phone number before logging in.',
                code='phone_unverified',
            )
        attrs['user'] = user
        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField(required=False, allow_blank=True)
    code = serializers.CharField(required=False, allow_blank=True, max_length=6)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, attrs):
        token = (attrs.get('token') or '').strip()
        code = (attrs.get('code') or '').strip()
        email = (attrs.get('email') or '').strip().lower()
        if token:
            return attrs
        if code and email:
            return attrs
        raise serializers.ValidationError('Provide either token (web link) or code and email (mobile).')


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    delivery = serializers.ChoiceField(
        choices=('link', 'code'),
        default='link',
        required=False,
    )


class PhoneSendOtpSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)


class PhoneVerifyOtpSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    code = serializers.CharField(max_length=6)


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ('id', 'name')


class TimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Time
        fields = ('id', 'name', 'slug')


class VenueSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), source='location', write_only=True, required=False,
    )
    picture_url = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = Venue
        fields = (
            'id', 'name', 'slug', 'address', 'phone', 'email',
            'location', 'location_id', 'picture_url',
        )

    def get_phone(self, obj):
        if obj.phone is None:
            return ''
        return str(obj.phone)

    def get_picture_url(self, obj):
        return absolute_media_url(self.context.get('request'), obj.picture)


def _post_form_payload(attrs):
    """Build UserPostForm data dict from serializer attrs (model instances or PKs)."""
    loc = attrs.get('location')
    ven = attrs.get('venue')
    tim = attrs.get('time')
    return {
        'location': loc.pk if hasattr(loc, 'pk') else loc,
        'venue': ven.pk if hasattr(ven, 'pk') else ven,
        'time': tim.pk if hasattr(tim, 'pk') else tim,
        'date': attrs.get('date'),
        'message': attrs.get('message'),
    }


class PostSerializer(serializers.ModelSerializer):
    author = UserBriefSerializer(read_only=True)
    venue = serializers.StringRelatedField(read_only=True)
    location = serializers.StringRelatedField(read_only=True)
    time = serializers.StringRelatedField(read_only=True)
    venue_id = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.all(), source='venue', write_only=True,
    )
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), source='location', write_only=True,
    )
    time_id = serializers.PrimaryKeyRelatedField(
        queryset=Time.objects.all(), source='time', write_only=True,
    )
    location_pk = serializers.IntegerField(source='location_id', read_only=True)
    venue_pk = serializers.IntegerField(source='venue_id', read_only=True)
    time_pk = serializers.IntegerField(source='time_id', read_only=True)
    whenpublished = serializers.CharField(read_only=True)
    interest_count = serializers.IntegerField(read_only=True, required=False)
    like_count = serializers.IntegerField(read_only=True, required=False)
    comment_count = serializers.IntegerField(read_only=True, required=False)
    user_interested = serializers.BooleanField(read_only=True, required=False)
    user_liked = serializers.BooleanField(read_only=True, required=False)
    user_can_chat = serializers.BooleanField(read_only=True, required=False)
    is_host = serializers.SerializerMethodField()
    event_locked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            'id', 'slug', 'message', 'date', 'event_status',
            'author', 'venue', 'location', 'time',
            'venue_id', 'location_id', 'time_id',
            'location_pk', 'venue_pk', 'time_pk',
            'created_at', 'updated_at', 'whenpublished',
            'interest_count', 'like_count', 'comment_count',
            'user_interested', 'user_liked', 'user_can_chat',
            'is_host', 'event_locked',
        )
        read_only_fields = (
            'id', 'slug', 'author', 'event_status', 'created_at', 'updated_at',
        )

    def get_is_host(self, obj):
        user = self.context['request'].user
        return obj.author_id == user.pk

    def get_event_locked(self, obj):
        return obj.event_status == Post.STATUS_CONFIRMED

    def create(self, validated_data):
        form = UserPostForm(data=_post_form_payload(validated_data))
        _validate_django_form(form)
        post = form.save(commit=False)
        post.author = self.context['request'].user
        post.save()
        return post

    def validate(self, attrs):
        if self.instance is None:
            form = UserPostForm(data=_post_form_payload(attrs))
            if not form.is_valid():
                raise serializers.ValidationError(form.errors)
        return attrs


class PostCommentCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000)
    parent_id = serializers.IntegerField(required=False, allow_null=True)


class VenueBookingSerializer(serializers.ModelSerializer):
    venue = VenueSerializer(read_only=True)
    venue_id = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.all(), source='venue', write_only=True,
    )
    time_slot = TimeSerializer(read_only=True)
    time_slot_id = serializers.PrimaryKeyRelatedField(
        queryset=Time.objects.all(), source='time_slot', write_only=True,
        required=False, allow_null=True,
    )
    display_time = serializers.SerializerMethodField()

    class Meta:
        model = VenueBooking
        fields = (
            'id', 'venue', 'venue_id', 'booking_date', 'preferred_time',
            'time_slot', 'time_slot_id', 'notes', 'status', 'display_time', 'created_at',
        )
        read_only_fields = ('id', 'status', 'created_at')

    def get_display_time(self, obj):
        return obj.display_time()

    def create(self, validated_data):
        venue = validated_data.pop('venue')
        form = VenueBookingForm(data={
            'booking_date': validated_data['booking_date'],
            'preferred_time': validated_data.get('preferred_time'),
            'notes': validated_data.get('notes', ''),
        })
        _validate_django_form(form)
        booking = form.save(commit=False)
        booking.user = self.context['request'].user
        booking.venue = venue
        booking.time_slot = validated_data.get('time_slot')
        booking.save()
        return booking

    def validate(self, attrs):
        if not attrs.get('preferred_time') and not attrs.get('time_slot'):
            raise serializers.ValidationError(
                'Provide preferred_time or time_slot_id.',
            )
        form = VenueBookingForm(data={
            'booking_date': attrs.get('booking_date'),
            'preferred_time': attrs.get('preferred_time'),
            'notes': attrs.get('notes', ''),
        })
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)
        return attrs


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserBriefSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = (
            'id', 'notification_type', 'message', 'url', 'is_read',
            'created_at', 'actor', 'post_id',
        )


class ConversationSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    post_id = serializers.IntegerField()
    post_slug = serializers.CharField()
    other_user = UserBriefSerializer()
    title = serializers.CharField()
    subtitle = serializers.CharField()
    event_status = serializers.CharField()
    event_locked = serializers.BooleanField()
    is_host = serializers.BooleanField()
    last_message = serializers.CharField(allow_blank=True)
    last_message_at = serializers.CharField(allow_blank=True)


class ChatMessageSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    body = serializers.CharField()
    message_type = serializers.CharField()
    created_at = serializers.CharField()
    user_id = serializers.IntegerField(allow_null=True)
    user_name = serializers.CharField(allow_blank=True)
    is_mine = serializers.BooleanField()


class ChatSendSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=1000)


class OpenConversationSerializer(serializers.Serializer):
    post_id = serializers.IntegerField()
    username = serializers.CharField(required=False, allow_blank=True)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'title')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 't_name')


class BlogListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    author = UserBriefSerializer(read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Blog
        fields = (
            'id', 'title', 'slug', 'count', 'category', 'author',
            'cover_image_url', 'created_at', 'updated_at',
        )

    def get_cover_image_url(self, obj):
        return absolute_media_url(self.context.get('request'), obj.cover_image)


class BlogDetailSerializer(BlogListSerializer):
    tags = TagSerializer(many=True, read_only=True)
    content = serializers.CharField(read_only=True)

    class Meta(BlogListSerializer.Meta):
        fields = BlogListSerializer.Meta.fields + ('content', 'tags')


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('fullname', 'phone', 'email', 'message')

    def validate(self, attrs):
        form = ContactForm(data=attrs)
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)
        return attrs

    def create(self, validated_data):
        return Contact.objects.create(**validated_data)


class SearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=100)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password1 = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from apps.accounts.forms import StyledPasswordChangeForm
        form = StyledPasswordChangeForm(
            user=self.context['request'].user, data=attrs,
        )
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)
        attrs['form'] = form
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password1 = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode
        from apps.accounts.forms import StyledSetPasswordForm

        try:
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({'uid': 'Invalid reset link.'})
        if not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError({'token': 'Invalid or expired reset link.'})
        form = StyledSetPasswordForm(user=user, data={
            'new_password1': attrs['new_password1'],
            'new_password2': attrs['new_password2'],
        })
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)
        attrs['user'] = user
        attrs['form'] = form
        return attrs
