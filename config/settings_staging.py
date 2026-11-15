
import os
from urllib.parse import urlparse

import dj_database_url
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

from .settings import *


# Membaca variabel khusus database staging.
load_dotenv(BASE_DIR / ".env.staging", override=True)

STAGING_DATABASE_URL = os.getenv(
    "STAGING_DATABASE_URL",
    ""
).strip()

if not STAGING_DATABASE_URL:
    raise ImproperlyConfigured(
        "STAGING_DATABASE_URL belum diisi pada .env.staging."
    )

parsed_url = urlparse(STAGING_DATABASE_URL)

if parsed_url.scheme not in ("postgres", "postgresql"):
    raise ImproperlyConfigured(
        "STAGING_DATABASE_URL harus menggunakan PostgreSQL."
    )

if not parsed_url.hostname or "neon.tech" not in parsed_url.hostname:
    raise ImproperlyConfigured(
        "Koneksi staging harus berasal dari Neon."
    )

if "-pooler" in parsed_url.hostname:
    raise ImproperlyConfigured(
        "Gunakan koneksi Direct Neon (pooling OFF) "
        "untuk migrasi dan pengelolaan data demo."
    )

DATABASES = {
    "default": dj_database_url.parse(
        STAGING_DATABASE_URL,
        conn_max_age=60,
        conn_health_checks=True,
        ssl_require=True,
    )
}

# Penanda keamanan untuk perintah pengelolaan data demo.
DEMO_DATA_ENV = "staging"
