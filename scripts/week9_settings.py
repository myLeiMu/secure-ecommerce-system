"""Dedicated loopback benchmark configuration; never use for a published site."""
from service.settings import *  # noqa: F403

SECURE_SSL_REDIRECT = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
CACHES = {'default': {'BACKEND':'django.core.cache.backends.locmem.LocMemCache', 'LOCATION':'week9',
                      'OPTIONS': {'MAX_ENTRIES': 2000}}}
REDIS_CONFIG = {'HOST':'127.0.0.1', 'PORT':1}
