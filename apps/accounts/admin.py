from django.contrib import admin

from apps.accounts.models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_verified', 'phone_verified', 'phone', 'dob')
    list_filter = ('email_verified', 'phone_verified')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('email_verification_token', 'email_verification_sent_at')
