"""Central LOGGING dict for Django settings."""

import logging

from futnetnepal.env import env, env_bool, env_int


class RequestContextFilter(logging.Filter):
    """Attach request_id to every log record when inside HTTP middleware."""

    def filter(self, record):
        from futnetnepal.log_context import get_request_id

        record.request_id = get_request_id() or '-'
        return True


def build_logging_settings(*, debug: bool, log_level: str | None = None) -> dict:
    level = (log_level or env('LOG_LEVEL', default='DEBUG' if debug else 'INFO')).upper()
    log_sql = env_bool('LOG_SQL', default=False)

    return {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'request_context': {
                '()': 'futnetnepal.logging_config.RequestContextFilter',
            },
        },
        'formatters': {
            'stream': {
                'format': (
                    '{levelname} {asctime} rid={request_id} {name} | {message}'
                ),
                'style': '{',
            },
            'stream_verbose': {
                'format': (
                    '{levelname} {asctime} rid={request_id} {name} '
                    '{pathname}:{lineno} | {message}'
                ),
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'stream_verbose' if debug else 'stream',
                'filters': ['request_context'],
            },
        },
        'root': {
            'handlers': ['console'],
            'level': level,
        },
        'loggers': {
            # HTTP access + API/web request/response pairs
            'futnetnepal.request': {
                'handlers': ['console'],
                'level': level,
                'propagate': False,
            },
            # Django request errors (500) — middleware also logs details
            'django.request': {
                'handlers': ['console'],
                'level': 'ERROR',
                'propagate': False,
            },
            # ORM SQL (off unless LOG_SQL=true)
            'django.db.backends': {
                'handlers': ['console'],
                'level': 'DEBUG' if log_sql else 'WARNING',
                'propagate': False,
            },
            # Dev noise reducers
            'django.utils.autoreload': {
                'level': 'INFO' if debug else 'WARNING',
                'propagate': True,
            },
            'asyncio': {'level': 'WARNING', 'propagate': True},
            'channels': {'level': 'WARNING', 'propagate': True},
            'django.channels.server': {'level': 'WARNING', 'propagate': False},
            'daphne': {'level': 'WARNING', 'propagate': True},
            'django.server': {'level': 'WARNING', 'propagate': True},
            'django.template': {'level': 'WARNING', 'propagate': True},
            # Project apps
            'apps': {'level': level, 'propagate': True},
            'futnetnepal': {'level': level, 'propagate': True},
        },
    }
