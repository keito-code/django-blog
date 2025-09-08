import os
import sys
from pathlib import Path

# .env.testのパスを定義
REPO_DIR = Path(__file__).resolve().parent.parent.parent
env_path = REPO_DIR / '.env.test'

# .env.testが存在しない場合はエラー
if not env_path.exists():
    print(f"Error: {env_path} not found. Test settings require .env.test file.")
    sys.exit(1)

# .base.py に渡すために環境変数として設定
os.environ["ENV_PATH"] = str(env_path)

# base.pyを読み込む
from .base import *

# テスト用のデータベース設定
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # メモリ上にDBを作成（高速）
    }
}

# セキュリティ設定を無効化（テスト環境）
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
AUTH_COOKIE_SECURE = False

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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {"console": {"class": "logging.StreamHandler"}},
    'root': {"handlers": ["console"], "level": "WARNING"},
}