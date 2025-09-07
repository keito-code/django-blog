"""
認証サービス層（SimpleJWT版）
ビジネスロジックをシンプルに実装
"""
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)
User = get_user_model()


class AuthService:
    """認証関連のビジネスロジック"""
    
    def login(self, email: str, password: str) -> Optional[tuple[User, Dict[str, str]]]:
        """
        ユーザーログイン処理
        
        Returns:
            成功時: (user, {'access': token, 'refresh': token})
            失敗時: None
        """
        # メールアドレスで検索（大文字小文字無視）
        user = User.objects.filter(email__iexact=email).first()
        
        if not user or not user.check_password(password):
            logger.warning(f"ログイン失敗: {email}")
            return None
            
        if not user.is_active:
            logger.warning(f"非アクティブユーザーのログイン試行: {email}")
            return None
        
        # SimpleJWTでトークン生成
        refresh = RefreshToken.for_user(user)
        
        logger.info(f"ログイン成功: {email}")
        return user, {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }
    
    def refresh_tokens(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        トークンのリフレッシュ処理
        
        Returns:
            成功時: {'access': new_token, 'refresh': new_token}
            失敗時: None
        """
        try:
            refresh = RefreshToken(refresh_token)
            refresh.check_blacklist()
            
            # SimpleJWTの標準: rotate() を使う
            new_refresh = refresh.rotate()
            
            return {
                'access': str(new_refresh.access_token),
                'refresh': str(new_refresh)
            }
        except (TokenError, AttributeError) as e:
            logger.warning(f"トークンリフレッシュ失敗: {e}")
            return None
    
    def logout(self, refresh_token: str) -> bool:
        """
        ログアウト処理（トークンをブラックリスト登録）
        
        Returns:
            常にTrue（エラーでもユーザビリティ重視）
        """
        try:
            refresh = RefreshToken(refresh_token)
            refresh.blacklist()
            logger.info("ログアウト: トークンをブラックリスト登録")
        except (TokenError, AttributeError) as e:
            # エラーでも成功として扱う
            logger.debug(f"ログアウト時のエラー（無視）: {e}")
        return True


class UserService:
    """ユーザー管理のビジネスロジック"""
    
    def create_user(self, email: str, password: str, username: str) -> User:
        """
        新規ユーザー作成
        
        Raises:
            ValueError: メール/ユーザー名が既存の場合
        """
        if User.objects.filter(email__iexact=email).exists():
            logger.warning(f"メール重複: {email}")
            raise ValueError("Email already exists")
        
        if User.objects.filter(username__iexact=username).exists():
            logger.warning(f"ユーザー名重複: {username}")
            raise ValueError("Username already exists")
        
        user = User.objects.create_user(
            email=email,
            username=username,
            password=password
        )
        
        logger.info(f"ユーザー作成成功: {email}")
        return user
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """メールでユーザー取得"""
        return User.objects.filter(email__iexact=email).first()
    
    def update_user(self, user: User, **kwargs) -> User:
        """ユーザー情報更新"""
        for field, value in kwargs.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        user.save()
        logger.info(f"ユーザー更新: {user.email}")
        return user