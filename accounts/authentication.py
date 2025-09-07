from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CookieJWTAuthentication(JWTAuthentication):
    """
    HTTPOnly Cookieを使用したJWT認証
    SimpleJWTを拡張してCookie対応
    
    責務：
    - Cookieからトークンを取得
    - トークンの検証
    - ユーザーオブジェクトの取得
    """
    
    def authenticate(self, request):
        """
        Cookieからトークンを取得して認証
        
        Returns:
            tuple: (user, validated_token) or None
        """
        raw_token = self.get_raw_token_from_cookie(request)
        if raw_token is None:
            return None
        
        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
            if user is None:
                return None
            return user, validated_token
        except TokenError as e:
            logger.debug(f"Token validation failed: {e}")
            return None
    
    def get_raw_token_from_cookie(self, request):
        """
        HTTPOnly Cookieからアクセストークンを取得
        
        Args:
            request: DjangoのHTTPRequestオブジェクト
            
        Returns:
            str: トークン文字列 or None
        """
        return request.COOKIES.get(settings.AUTH_COOKIE_ACCESS_TOKEN)