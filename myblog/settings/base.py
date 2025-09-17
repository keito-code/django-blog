from pathlib import Path
import os
import dj_database_url
from csp.constants import NONCE, SELF
from datetime import timedelta
from decouple import Config, RepositoryEnv, Csv

# 環境ごとの .env ファイルを切り替え可能にする
ENV_PATH = os.environ.get("ENV_PATH")  # test.py から渡される
if ENV_PATH:
    config = Config(RepositoryEnv(ENV_PATH))
else:
    from decouple import config as default_config
    config = default_config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY') # defaultを削除

JWT_SECRET_KEY = config('JWT_SECRET_KEY')  # defaultなし

SIMPLE_JWT = {
    'SIGNING_KEY': JWT_SECRET_KEY,
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

DEBUG = config('DEBUG', cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# 管理画面のURLを環境変数から取得 (セキュリティ向上)
ADMIN_URL = config('ADMIN_URL') # 必須にする

# APIのバージョン管理
API_VERSION = 'v1'

# Cookie名の定義（フロントエンドと共有する契約値）
AUTH_COOKIE_ACCESS_TOKEN = 'access_token'
AUTH_COOKIE_REFRESH_TOKEN = 'refresh_token'
CSRF_COOKIE_NAME = 'csrf_token'

# JWT Cookie認証設定
AUTH_COOKIE_HTTPONLY = True  # XSS対策: JSからアクセス不可
AUTH_COOKIE_SAMESITE = 'Lax'  # CSRF対策: 適度なセキュリティ
AUTH_COOKIE_ACCESS_MAX_AGE = 60 * 30  # 30分
AUTH_COOKIE_REFRESH_MAX_AGE = 60 * 60 * 24 * 14  # 14日
AUTH_COOKIE_PATH = '/'

# CSRF Cookie設定（JWT認証と連携）
CSRF_COOKIE_HTTPONLY = False  # JSからアクセス必要
CSRF_COOKIE_SAMESITE = 'Lax'  # AUTH_COOKIEと同じ設定
CSRF_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1年

# 環境別設定
if DEBUG:
    AUTH_COOKIE_SECURE = False  # 開発: HTTPでも動作
    AUTH_COOKIE_DOMAIN = None   # 開発: localhost用
    CSRF_COOKIE_SECURE = False 
    CSRF_COOKIE_DOMAIN = None
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:8000',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:8000',
    ]

else:
    AUTH_COOKIE_SECURE = True   # 本番: HTTPS必須
    AUTH_COOKIE_DOMAIN = config('COOKIE_DOMAIN') 
    CSRF_COOKIE_SECURE = True 
    CSRF_COOKIE_DOMAIN = config('COOKIE_DOMAIN')
    CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv())


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'csp',
    'axes',
    'blog',
    'accounts',
    'core',
    'rest_framework',
    'corsheaders',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'drf_spectacular',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'myblog.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'csp.context_processors.nonce',
            ],
        },
    },
]

WSGI_APPLICATION = 'myblog.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600
    )
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}  # 8文字以上
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'ja'

TIME_ZONE = 'Asia/Tokyo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = '/blog/'
LOGOUT_REDIRECT_URL = '/blog/'

# セキュリティ設定
if not DEBUG:
    # セッションクッキーのセキュリティ
    SESSION_COOKIE_SECURE = True  # HTTPS接続でのみ送信

    # クリックジャッキング対策
    X_FRAME_OPTIONS = 'DENY'  # iframe内での表示を完全禁止
    
    # コンテンツタイプの推測を防ぐ
    SECURE_CONTENT_TYPE_NOSNIFF = True  # IEのコンテンツ自動判定を無効化
        # HTTPSリダイレクト設定
    if os.environ.get('DISABLE_SSL_REDIRECT'):
        # ローカルで本番モードテスト用
        SECURE_SSL_REDIRECT = False
    else:
        # 本番環境のみTrue
        SECURE_SSL_REDIRECT = True

    # リファラーポリシー
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    
    # HSTS (HTTP Strict Transport Security)
    # ブラウザに「このサイトは今後HTTPSでのみアクセスする」と記憶させる
    # 段階的に期間を延長することで、設定ミスのリスクを最小化
    
    # SECURE_HSTS_SECONDS = 3600  # 初期設定: 1時間（2025/07/29）
    
    # 段階的延長計画：
    # フェーズ1: 2025/07/30 - 1日に延長（完了）
    # SECURE_HSTS_SECONDS = 86400  # 24時間
    
    # フェーズ2: 2025/08/08 - 1週間に延長予定
    SECURE_HSTS_SECONDS = 604800  # 7日間
    
    # フェーズ3: 2025/08/15 - 1ヶ月に延長予定
    # SECURE_HSTS_SECONDS = 2592000  # 30日間
    
    # フェーズ4: 2025/09/15 - 1年に延長予定（最終目標）
    # SECURE_HSTS_SECONDS = 31536000  # 365日間
    
    # 将来的な追加設定（現在は無効）
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True  # サブドメインも対象に
    # SECURE_HSTS_PRELOAD = True  # ブラウザのプリロードリストに登録

SESSION_COOKIE_HTTPONLY = True

# django-axes 設定（ブルートフォース対策）
AXES_FAILURE_LIMIT = 5  # 5回失敗でロック
AXES_COOLOFF_TIME = 1  # 1時間ロック
AXES_RESET_ON_SUCCESS = True  # 成功したらカウントリセット

# 認証バックエンドの設定
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
    'axes.backends.AxesBackend',
]

# ログ設定（セキュリティ監視用）
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'axes': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ログディレクトリの作成
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)


# Content Security Policy (CSP) 設定 (django-csp 4.0+ 形式)
CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'base-uri': (SELF,),
        'connect-src': (SELF,),
        'default-src': (SELF,),
        'font-src': (
            SELF, 
            'https://stackpath.bootstrapcdn.com', 
            'https://cdn.jsdelivr.net'
        ),
        'form-action': (SELF,),
        'frame-src': ("'none'",),  
        'img-src': (SELF, 'data:', 'https:'),
        'object-src': ("'none'",),  
        'report-uri': '/csp-report/',
        'script-src': (
            SELF, 
            NONCE,  # NONCEは維持（スクリプトのセキュリティ）
            'https://stackpath.bootstrapcdn.com', 
            'https://cdn.jsdelivr.net'
        ),
        'style-src': (
            SELF, 
            "'unsafe-inline'",  # DRFの画面表示に必要なため許容
            'https://stackpath.bootstrapcdn.com', 
            'https://cdn.jsdelivr.net'
        )
    },
    'EXCLUDE_URL_PREFIXES': ('/admin/',),
}

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'accounts.authentication.CookieJWTAuthentication',
    ],
    'DEFAULT_RENDERER_CLASSES': (
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
        'djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'djangorestframework_camel_case.parser.CamelCaseFormParser',
        'djangorestframework_camel_case.parser.CamelCaseMultiPartParser',
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
    ),
    "EXCEPTION_HANDLER": 'core.exceptions.custom_exception_handler',
    # バージョニング設定
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
    # レートリミット設定
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '1000/hour',
        'user': '10000/hour'
    },
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# drf-spectacular設定
SPECTACULAR_SETTINGS = {
    'TITLE': 'Django Blog API',
    'DESCRIPTION': 'ブログシステムのREST API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,

     'SECURITY': [
        {'bearerAuth': []}
    ],

    'SECURITY_SCHEMES': {
        'bearerAuth': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
    },

    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields'
    ],
}

# CORS設定
if DEBUG:
    # 開発環境では localhost を許可
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
else:
    # 本番環境では環境変数から取得（必須）
    CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=Csv())

# JWT認証のために必要
CORS_ALLOW_CREDENTIALS = True

# 許可するヘッダー
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]




