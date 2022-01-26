"""Nautobot configuration for nautobot-netbox-importer development/test environment."""
#########################
#                       #
#   Required settings   #
#                       #
#########################

import os
import sys

from nautobot.core.settings import *  # noqa F401,F403 pylint: disable=wildcard-import,unused-wildcard-import
from distutils.util import strtobool


def is_truthy(arg):
    """Convert "truthy" strings into Booleans.

    Examples:
        >>> is_truthy('yes')
        True
    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.
    """
    if isinstance(arg, bool):
        return arg
    return bool(strtobool(arg))


TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

# This is a list of valid fully-qualified domain names (FQDNs) for the Nautobot server. Nautobot will not permit write
# access to the server via any other hostnames. The first FQDN in the list will be treated as the preferred name.
#
# Example: ALLOWED_HOSTS = ['nautobot.example.com', 'nautobot.internal.local']
ALLOWED_HOSTS = os.getenv("NAUTOBOT_ALLOWED_HOSTS", "").split(" ")

# PostgreSQL database configuration. See the Django documentation for a complete list of available parameters:
#   https://docs.djangoproject.com/en/stable/ref/settings/#databases
DATABASES = {
    "default": {
        "NAME": os.getenv("NAUTOBOT_DB_NAME", "nautobot"),  # Database name
        "USER": os.getenv("NAUTOBOT_DB_USER", ""),  # Database username
        "PASSWORD": os.getenv("NAUTOBOT_DB_PASSWORD", ""),  # Datbase password
        "HOST": os.getenv("NAUTOBOT_DB_HOST", "localhost"),  # Database server
        "PORT": os.getenv("NAUTOBOT_DB_PORT", ""),  # Database port (leave blank for default)
        "CONN_MAX_AGE": os.getenv("NAUTOBOT_DB_TIMEOUT", 300),  # Database timeout
        "ENGINE": "django.db.backends.postgresql",  # Database driver (Postgres only supported!)
    }
}

# Redis variables
REDIS_HOST = os.getenv("NAUTOBOT_REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("NAUTOBOT_REDIS_PORT", 6379)
REDIS_PASSWORD = os.getenv("NAUTOBOT_REDIS_PASSWORD", "")

# Check for Redis SSL
REDIS_SCHEME = "redis"
REDIS_SSL = is_truthy(os.environ.get("REDIS_SSL", False))
if REDIS_SSL:
    REDIS_SCHEME = "rediss"

# The django-redis cache is used to establish concurrent locks using Redis. The
# django-rq settings will use the same instance/database by default.
#
# This "default" server is now used by RQ_QUEUES.
# >> See: nautobot.core.settings.RQ_QUEUES
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_SCHEME}://{REDIS_HOST}:{REDIS_PORT}/0",
        "TIMEOUT": 300,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": REDIS_PASSWORD,
        },
    }
}

# RQ_QUEUES is not set here because it just uses the default that gets imported
# up top via `from nautobot.core.settings import *`.

# REDIS CACHEOPS
CACHEOPS_REDIS = f"{REDIS_SCHEME}://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1"

# This key is used for secure generation of random numbers and strings. It must never be exposed outside of this file.
# For optimal security, SECRET_KEY should be at least 50 characters in length and contain a mix of letters, numbers, and
# symbols. Nautobot will not run without this defined. For more information, see
# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-SECRET_KEY
SECRET_KEY = os.getenv("NAUTOBOT_SECRET_KEY")


#########################
#                       #
#   Optional settings   #
#                       #
#########################

# Enable installed plugins. Add the name of each plugin to the list.
PLUGINS = ["nautobot_netbox_importer"]

# Plugins configuration settings. These settings are used by various plugins that the user may have installed.
# Each key in the dictionary is the name of an installed plugin and its value is a dictionary of settings.
# PLUGINS_CONFIG = {
#     'my_plugin': {
#         'foo': 'bar',
#         'buzz': 'bazz'
#     }
# }
