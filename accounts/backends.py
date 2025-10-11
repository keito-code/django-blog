from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailBackend(ModelBackend):
    """メールアドレスでの認証を可能にする"""
    def authenticate(self, request, email=None, password=None, **kwargs):
        if not email or not password:
            return None

        # 前後の空白削除 + 小文字化
        cleaned_email = email.strip().lower()

        try:
            user = User.objects.get(email__iexact=cleaned_email)
            if user.check_password(password):
                return user
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            # ユーザーが存在しない、または複数存在する場合、
            return None

        # パスワードが違う場合
        return None