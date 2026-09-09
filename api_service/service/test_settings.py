"""Isolated local test environment: no production database or external services."""
from .settings import *  # noqa

DEBUG = False
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
REDIS_CONFIG = {'HOST': '127.0.0.1', 'PORT': 1}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
