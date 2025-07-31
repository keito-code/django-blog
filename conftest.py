import os
import sys
import django
from django.conf import settings

# プロジェクトのパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Django の設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myblog.settings.test')

# Django を初期化
django.setup()
