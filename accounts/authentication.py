from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CookieJWTAuthentication(JWTAuthentication):
    """
    HTTPOnly Cookieを使用したJWT認証
    """
    
    def authenticate(self, request):
        raw_token = self.get_raw_token_from_cookie(request)
        if raw_token is None:
            return None

        if not isinstance(raw_token, str) or not raw_token.strip():
            logger.debug("Invalid token format in cookie")
            return None
        
        try:
            validated_token = self.get_validated_token(raw_token)

            if getattr(validated_token, "token_type", None) != "access":
                logger.warning("Non-access token detected in cookie")
                return None

            user = self.get_user(validated_token)
            if user is None:
                return None
            return user, validated_token

        except (TokenError, InvalidToken) as e:
            logger.debug(f"Token validation failed: {e}")
            return None
        except Exception as e:
            logger.debug(f"Unexpected auth error: {e}")
            return None
    
    def get_raw_token_from_cookie(self, request):
        return request.COOKIES.get(settings.AUTH_COOKIE_ACCESS_TOKEN)