"""
Cookie認証専用のカスタム認証クラス
"""

import logging
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError

logger = logging.getLogger(__name__)


class CookieJWTAuthentication(JWTAuthentication):
    """
    CookieからJWTトークンを取得する認証クラス
    """
    
    def authenticate(self, request):
        """
        Cookie内のアクセストークンで認証
        
        Returns:
            tuple: (user, validated_token) or None
        """
        # settings.py から Cookie名を取得
        raw_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS_TOKEN)
        
        if not raw_token:
            return None
        
        try:
            # トークンを検証
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
            
            logger.debug(f"Cookie認証成功: ユーザー {user.username}")
            return user, validated_token
            
        except TokenError as e:
            # トークンエラーの詳細をログに記録
            logger.warning(
                f"無効なCookieトークン: {e.__class__.__name__}: {str(e)}", 
                extra={
                    'request_path': request.path,
                    'user_agent': request.META.get('HTTP_USER_AGENT', '不明'),
                }
            )
            return None
            
        except Exception as e:
            # 予期しないエラーをログに記録
            logger.error(
                f"Cookie認証で予期しないエラー: {e}", 
                exc_info=True,
                extra={'request_path': request.path}
            )
            return None