from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Q
import os

class Command(BaseCommand):
    help = 'Render本番用のスーパーユーザーを作成（冪等）'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # 環境変数から取得
        username_raw = os.getenv("SUPERUSER_USERNAME")
        email_raw = os.getenv("SUPERUSER_EMAIL")
        password = os.getenv("SUPERUSER_PASSWORD")

        # 環境変数チェック
        if not all([username_raw, email_raw, password]):
            self.stdout.write(
                self.style.ERROR("❌ SUPERUSER_* 環境変数が未設定です")
            )
            return

        # 入力値の正規化
        username = username_raw.strip()
        email = email_raw.strip().lower()

        # usernameまたはemailで既存チェック
        if User.objects.filter(Q(username=username) | Q(email=email)).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️ ユーザー '{username}' またはメール '{email}' は既に存在します。スキップします。"
                )
            )
            return

        # スーパーユーザー作成
        try:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ スーパーユーザー '{username}' を作成しました。"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ エラー: {str(e)}")
            )
            raise