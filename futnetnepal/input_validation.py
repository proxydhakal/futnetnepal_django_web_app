"""
Sanitize and validate user-supplied text (XSS / HTML injection defense in depth).

Django ORM already parameterizes SQL; we still reject null bytes and obvious
SQLi probe strings in free-text fields.
"""

import re

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

# Dangerous markup / script patterns
_TAG_RE = re.compile(r'<[^>]+>', re.IGNORECASE)
_SCRIPTISH_RE = re.compile(
    r'<\s*/?\s*(script|iframe|object|embed|link|style|meta|svg|form|img|base)\b',
    re.IGNORECASE,
)
_EVENT_HANDLER_RE = re.compile(r'\bon\w+\s*=', re.IGNORECASE)
_JS_SCHEME_RE = re.compile(r'javascript\s*:', re.IGNORECASE)
_DATA_HTML_RE = re.compile(r'data\s*:\s*text/html', re.IGNORECASE)

# SQL injection probes (defense in depth; ORM is primary protection)
_SQL_PROBE_RE = re.compile(
    r"(\bunion\b.+\bselect\b|\bdrop\b\s+\b(table|database)\b|"
    r"'\s*;\s*--|;\s*--\s*$|/\*|\*/|xp_)",
    re.IGNORECASE,
)

_USERNAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{1,149}$')
_NAME_RE = re.compile(r"^[\w\s.'-]{2,300}$", re.UNICODE)
_PHONE_DIGITS_RE = re.compile(r'^\d{10}$')
_TOKEN_RE = re.compile(r'^[a-zA-Z0-9_-]{1,128}$')
_OTP_RE = re.compile(r'^\d{4,8}$')

DEFAULT_MESSAGE = 'Invalid or unsafe characters in input.'


class UnsafeInputError(ValidationError):
    pass


def _reject_null_bytes(value: str, message=DEFAULT_MESSAGE):
    if '\x00' in value:
        raise UnsafeInputError(message)


def _reject_dangerous_markup(value: str, message=DEFAULT_MESSAGE):
    """Block scripts, event handlers, and javascript: URLs (allows normal HTML)."""
    if (
        _SCRIPTISH_RE.search(value)
        or _EVENT_HANDLER_RE.search(value)
        or _JS_SCHEME_RE.search(value)
        or _DATA_HTML_RE.search(value)
    ):
        raise UnsafeInputError(message)


def _reject_markup(value: str, message=DEFAULT_MESSAGE):
    """Plain-text fields: no HTML tags at all."""
    _reject_dangerous_markup(value, message)
    if _TAG_RE.search(value):
        raise UnsafeInputError('HTML tags are not allowed.')


def _reject_sql_probes(value: str, message=DEFAULT_MESSAGE):
    if _SQL_PROBE_RE.search(value):
        raise UnsafeInputError(message)


def reject_password_unsafe_chars(value: str):
    """Passwords: allow symbols; block null bytes and script injection only."""
    if value is None:
        return
    _reject_null_bytes(value)
    _reject_markup(value)


def sanitize_plain_text(
    value: str,
    *,
    max_length=None,
    multiline=False,
    min_length=None,
    check_sql=True,
    field_label='This field',
):
    if value is None:
        return value
    if not isinstance(value, str):
        raise UnsafeInputError(f'{field_label} must be text.')
    _reject_null_bytes(value)
    text = value.strip()
    if not multiline:
        text = re.sub(r'[\r\n]+', ' ', text).strip()
    _reject_markup(text)
    if check_sql:
        _reject_sql_probes(text)
    if min_length and len(text) < min_length:
        raise UnsafeInputError(f'{field_label} must be at least {min_length} characters.')
    if max_length and len(text) > max_length:
        raise UnsafeInputError(f'{field_label} must be at most {max_length} characters.')
    return text


def sanitize_email(value: str, *, field_label='Email'):
    text = sanitize_plain_text(value, max_length=254, field_label=field_label, check_sql=False)
    text = text.lower()
    validate_email(text)
    return text


def sanitize_username(value: str):
    text = sanitize_plain_text(value, max_length=150, field_label='Username', check_sql=False)
    if not _USERNAME_RE.match(text):
        raise UnsafeInputError(
            'Username may only contain letters, numbers, dots, hyphens, and underscores.',
        )
    return text


def sanitize_login(value: str):
    text = sanitize_plain_text(value, max_length=254, field_label='Login', check_sql=False)
    if '@' in text:
        return sanitize_email(text, field_label='Login')
    return sanitize_username(text)


def sanitize_person_name(value: str, *, max_length=300):
    text = sanitize_plain_text(
        value, max_length=max_length, min_length=2, field_label='Name', check_sql=False,
    )
    if not _NAME_RE.match(text):
        raise UnsafeInputError(
            'Name may only contain letters, numbers, spaces, and . \' -',
        )
    return text


def sanitize_phone_digits(value: str):
    _reject_null_bytes(value)
    digits = re.sub(r'\D', '', value.strip())
    if not _PHONE_DIGITS_RE.match(digits):
        raise UnsafeInputError('Enter a valid 10-digit mobile number.')
    return digits


def sanitize_token(value: str, *, max_length=128):
    text = (value or '').strip()
    _reject_null_bytes(text)
    if not text:
        return text
    if len(text) > max_length or not _TOKEN_RE.match(text):
        raise UnsafeInputError('Invalid token.')
    return text


def sanitize_otp_code(value: str):
    text = (value or '').strip()
    _reject_null_bytes(text)
    if not _OTP_RE.match(text):
        raise UnsafeInputError('Invalid verification code.')
    return text


def sanitize_rich_text(value: str, *, max_length=None, field_label='Content'):
    """Allow safe HTML from CKEditor; block scripts, handlers, and SQL probes."""
    if value is None:
        return value
    if not isinstance(value, str):
        raise UnsafeInputError(f'{field_label} must be text.')
    _reject_null_bytes(value)
    text = value.strip()
    if not text:
        return text
    _reject_dangerous_markup(text)
    if _SQL_PROBE_RE.search(text):
        raise UnsafeInputError(DEFAULT_MESSAGE)
    if max_length and len(text) > max_length:
        raise UnsafeInputError(f'{field_label} is too long.')
    return text


def sanitize_choice(value: str, allowed: set[str], *, field_label='Value'):
    text = sanitize_plain_text(value, max_length=64, field_label=field_label, check_sql=False)
    if text not in allowed:
        raise UnsafeInputError(f'Invalid {field_label.lower()}.')
    return text


# Field name → sanitizer kind for Django forms
def _model_field(form, name):
    model = getattr(getattr(form, '_meta', None), 'model', None)
    if model is None:
        return None
    try:
        return model._meta.get_field(name)
    except Exception:
        return None


def _is_rich_text_model_field(form, name) -> bool:
    mf = _model_field(form, name)
    return mf is not None and type(mf).__name__ == 'RichTextUploadingField'


def _is_slug_model_field(form, name) -> bool:
    from django.db import models

    mf = _model_field(form, name)
    return mf is not None and isinstance(mf, models.SlugField)


FIELD_KIND_BY_NAME = {
    'username': 'username',
    'email': 'email',
    'phone': 'phone',
    'full_name': 'name',
    'fullname': 'name',
    'login': 'login',
    'message': 'multiline',
    'body': 'multiline',
    'notes': 'multiline',
    'address': 'plain',
    'q': 'plain',
    'token': 'token',
    'code': 'otp',
    'uid': 'token',
}


def secure_clean_form_data(form, cleaned_data):
    if not cleaned_data:
        return cleaned_data
    password_names = {
        'password', 'password1', 'password2',
        'old_password', 'new_password1', 'new_password2',
    }
    for name, value in list(cleaned_data.items()):
        if value is None or not isinstance(value, str):
            continue
        field = form.fields.get(name)
        if field is None:
            continue
        is_password = name in password_names or isinstance(field.widget, forms.PasswordInput)
        if is_password:
            reject_password_unsafe_chars(value)
            continue

        if _is_rich_text_model_field(form, name):
            mf = _model_field(form, name)
            cleaned_data[name] = sanitize_rich_text(
                value,
                max_length=getattr(mf, 'max_length', None),
                field_label=name.replace('_', ' ').title(),
            )
            continue

        if _is_slug_model_field(form, name):
            from django.utils.text import slugify

            mf = _model_field(form, name)
            max_len = getattr(mf, 'max_length', None) or 50
            cleaned_data[name] = slugify(value)[:max_len]
            continue

        kind = FIELD_KIND_BY_NAME.get(name)
        if kind is None and isinstance(field, forms.EmailField):
            kind = 'email'
        if kind is None and isinstance(field.widget, forms.Textarea) and not _is_rich_text_model_field(form, name):
            kind = 'multiline'
        if kind is None:
            kind = 'plain'

        max_length = getattr(field, 'max_length', None)

        if kind == 'email':
            cleaned_data[name] = sanitize_email(value)
        elif kind == 'username':
            cleaned_data[name] = sanitize_username(value)
        elif kind == 'login':
            cleaned_data[name] = sanitize_login(value)
        elif kind == 'phone':
            cleaned_data[name] = sanitize_phone_digits(value)
        elif kind == 'name':
            cleaned_data[name] = sanitize_person_name(value, max_length=max_length or 300)
        elif kind == 'multiline':
            cleaned_data[name] = sanitize_plain_text(
                value, max_length=max_length, multiline=True,
            )
        elif kind == 'token':
            cleaned_data[name] = sanitize_token(value, max_length=max_length or 128)
        elif kind == 'otp':
            cleaned_data[name] = sanitize_otp_code(value)
        else:
            cleaned_data[name] = sanitize_plain_text(value, max_length=max_length)
    return cleaned_data
