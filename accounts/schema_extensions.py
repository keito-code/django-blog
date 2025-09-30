"""
カスタム認証クラスをOpenAPIスキーマに定義するための拡張。
DRFのデフォルトではカスタム認証を自動でスキーマ化できないため必要。
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension

class CookieJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """JWT + Cookie認証のOpenAPI定義"""
    target_class = 'accounts.authentication.CookieJWTAuthentication'
    name = 'jwtCookieAuth'

    def get_security_definition(self, auto_schema):
        """
        OpenAPIの認証定義を返す
        Swagger UIやReDocで表示される認証方法の詳細
        """
        return {
            'type': 'apiKey',
            'in': 'cookie',
            'name': 'access_token',
            'description': 'JWT in HttpOnly cookie'
        }