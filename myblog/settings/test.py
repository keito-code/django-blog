import os
os.environ['DEBUG'] = 'False'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['ALLOWED_HOSTS'] = '*'
os.environ['ADMIN_URL'] = 'admin/'

from .base import *

# HTTPS リダイレクトを無効化（テスト環境）
SECURE_SSL_REDIRECT = False

# 他のセキュリティ設定も無効化
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False


# テスト用のデータベース設定
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # メモリ上にDBを作成（高速）
    }
}

# メディアファイルの保存先を一時ディレクトリに
import tempfile
MEDIA_ROOT = tempfile.mkdtemp()

# 静的ファイルの設定
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# キャッシュを無効化
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# メール送信をコンソールに出力（実際には送信しない）
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# パスワードハッシュを簡略化（テスト高速化）
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]



# ログを抑制（テスト実行時の出力をきれいに）
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}