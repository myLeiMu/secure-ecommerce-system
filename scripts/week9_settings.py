"""Dedicated loopback benchmark configuration; never use for a published site."""
from service.settings import *  # noqa: F403

SECURE_SSL_REDIRECT = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
CACHES = {'default': {'BACKEND':'django.core.cache.backends.locmem.LocMemCache', 'LOCATION':'week9',
                      'OPTIONS': {'MAX_ENTRIES': 2000}}}
REDIS_CONFIG = {'HOST':'127.0.0.1', 'PORT':1}

if os.environ.get('WEEK9_CAPACITY') == '1':
    import re
    if not re.fullmatch(r'test_week9_[0-9a-f]{16}', os.environ.get('DB_NAME', '')):
        raise RuntimeError('Capacity mode requires an owned isolated test database')
    MIDDLEWARE = [name for name in MIDDLEWARE if name != 'api.middleware.RateLimitMiddleware']

if os.environ.get('WEEK9_CACHE') == 'redis':
    prefix = os.environ['WEEK9_CACHE_PREFIX']
    if not prefix.startswith('test_week9_'):
        raise RuntimeError('Redis experiment requires an isolated key prefix')
    CACHES = {'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://{}:{}/{}'.format(os.environ['REDIS_HOST'], os.environ['REDIS_PORT'], os.environ['REDIS_DB']),
        'KEY_PREFIX': prefix,
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    'PASSWORD': os.environ.get('REDIS_PASSWORD') or None,
                    'SOCKET_CONNECT_TIMEOUT': 5, 'SOCKET_TIMEOUT': 5},
    }}
