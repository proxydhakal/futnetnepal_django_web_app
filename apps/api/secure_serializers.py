"""DRF helpers for secure string input."""

from rest_framework import serializers

from futnetnepal.input_validation import (
    reject_password_unsafe_chars,
    sanitize_choice,
    sanitize_login,
    sanitize_otp_code,
    sanitize_person_name,
    sanitize_plain_text,
    sanitize_token,
    sanitize_username,
)


class SecureInputSerializerMixin:
    """Apply sanitizers to declared SECURE_STRING_FIELDS on validate()."""

    SECURE_STRING_FIELDS = {}

    def validate(self, attrs):
        attrs = super().validate(attrs)
        for name, kind in self.SECURE_STRING_FIELDS.items():
            if name not in attrs or attrs[name] is None:
                continue
            value = attrs[name]
            if not isinstance(value, str):
                continue
            attrs[name] = _sanitize_by_kind(kind, value, name)
        return attrs


def _sanitize_by_kind(kind, value, field_name):
    if kind == 'login':
        return sanitize_login(value)
    if kind == 'username':
        return sanitize_username(value)
    if kind == 'name':
        return sanitize_person_name(value)
    if kind == 'multiline':
        max_len = 2000 if field_name == 'body' else 5000
        return sanitize_plain_text(value, max_length=max_len, multiline=True)
    if kind == 'plain':
        return sanitize_plain_text(value, max_length=100)
    if kind == 'token':
        return sanitize_token(value)
    if kind == 'otp':
        return sanitize_otp_code(value)
    if kind == 'password':
        reject_password_unsafe_chars(value)
        return value
    if kind.startswith('choice:'):
        allowed = set(kind.split(':', 1)[1].split(','))
        return sanitize_choice(value, allowed)
    return sanitize_plain_text(value)


class SecureCharField(serializers.CharField):
    def __init__(self, *args, secure_kind='plain', **kwargs):
        self.secure_kind = secure_kind
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        return _sanitize_by_kind(self.secure_kind, value, self.field_name or 'field')
