"""
認証認可に関するビュー

HTTPレイヤーの責務のみを担当し、ビジネスロジックはservices.pyに委譲する。
Cookie+JWT認証を実装し、CSRF保護を適用する。

設計判断：
- Django標準のViewを使用（APIViewではなく）
- 理由：Cookie+JWT認証は、JWTトークンをHTTP Cookieに保持するステートレスな設計。
- Cookieを利用するためCSRF保護が必須となる。
- APIViewは内部的にCSRF保護を無効化するため不適切
"""

import json
import logging
from django.conf import settings
from django.http import HttpResponseNotAllowed
from django.views import View
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.middleware.csrf import get_token
from .services import AuthService, UserService
from .responses import ResponseFormatter

logger = logging.getLogger(__name__)


class CSRFProtectedView(View):
    """CSRFプロテクションを適切に処理する基底ビュー"""
    
    http_method_names = ['post']  # 許可するHTTPメソッドを明示的に指定
    
    def dispatch(self, request, *args, **kwargs):
        """HTTPメソッドをチェックしてから、CSRFプロテクションを適用"""
        # 1. まずHTTPメソッドをチェック
        if request.method.lower() not in self.http_method_names:
            return HttpResponseNotAllowed(self.http_method_names)
        
        # 2. 許可されたメソッドの場合のみCSRFチェック
        return super().dispatch(request, *args, **kwargs)

class CSRFTokenView(View): 
    """CSRFトークン取得用ビュー"""

    http_method_names = ['get']  # GETのみ許可
    
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        """CSRFトークンを返す"""
        csrf_token = get_token(request)
        
        response = ResponseFormatter.success(
            data={'csrf_token': csrf_token},
            status=200
        )

        response.set_cookie(
            key=settings.CSRF_COOKIE_NAME,
            value=csrf_token,
            max_age=settings.CSRF_COOKIE_MAX_AGE,
            httponly=settings.CSRF_COOKIE_HTTPONLY,
            samesite=settings.CSRF_COOKIE_SAMESITE,
            secure=settings.CSRF_COOKIE_SECURE
        )
        return response


@method_decorator(csrf_protect, name='dispatch')
class LoginView(CSRFProtectedView):
    """ログイン用ビュー"""
    
    def post(self, request):
        """ユーザーログイン処理"""
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return ResponseFormatter.validation_error(
                "Invalid JSON format"
            )
            
        # 必須フィールドのチェック
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return ResponseFormatter.validation_error(
                "Email and password are required"
            )

        # サービス層で認証処理
        auth_service = AuthService()
        result = auth_service.login(email, password)
        
        if result is None:
            return ResponseFormatter.unauthorized(
                    "Invalid email or password"
                )

        user, access_token, refresh_token = result
        
        # レスポンス作成
        response = ResponseFormatter.success(
                data={
                    'message': 'Login successful',
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username if hasattr(user, 'username') else None
                    }
                },
                status=200
            )

        # Cookieにトークンを設定
        response.set_cookie(
            key=settings.AUTH_COOKIE_ACCESS_TOKEN,
            value=access_token,
            max_age=settings.AUTH_COOKIE_ACCESS_MAX_AGE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            secure=settings.AUTH_COOKIE_SECURE
        )
        response.set_cookie(
            key=settings.AUTH_COOKIE_REFRESH_TOKEN,
            value=refresh_token,
            max_age=settings.AUTH_COOKIE_REFRESH_MAX_AGE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            secure=settings.AUTH_COOKIE_SECURE
        )
        
        return response


@method_decorator(csrf_protect, name='dispatch')
class RegisterView(CSRFProtectedView):
    """ユーザー登録用ビュー"""
    
    def post(self, request):
        """新規ユーザー登録処理"""
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return ResponseFormatter.validation_error(
                "Invalid JSON format"
            )

        # 必須フィールドのチェック
        email = data.get('email')
        password = data.get('password')
        username = data.get('username')
        
        if not email or not password or not username:
            missing_fields = []
            if not email:
                missing_fields.append('email')
            if not password:
                missing_fields.append('password')
            if not username:
                missing_fields.append('username')
            
            return ResponseFormatter.validation_error(
                f"Missing required fields: {', '.join(missing_fields)}"
            )

        # サービス層でユーザー作成
        user_service = UserService()
        try:
            user = user_service.create_user(
                email=email,
                password=password,
                username=username
            )
            
            return ResponseFormatter.success(
                data={
                    'message': 'Registration successful',
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username
                    }
                },
                status=201
            )
        except ValueError as e:
            # バリデーションエラー（重複メールなど）
            return ResponseFormatter.validation_error(str(e))
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return ResponseFormatter.server_error(
                "Registration failed",
                details=str(e) if settings.DEBUG else None
            )

@method_decorator(csrf_protect, name='dispatch')
class LogoutView(CSRFProtectedView):
    """ログアウト用ビュー"""
    
    def post(self, request):
        """ログアウト処理"""
        try:
            # リフレッシュトークンをCookieから取得
            refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH_TOKEN)
        
            # トークンがある場合はサービス層でログアウト処理
            if refresh_token:
                auth_service = AuthService()
                auth_service.logout(refresh_token)
            
            # レスポンス作成（トークンの有無に関わらず200を返す = 冪等性）
            response = ResponseFormatter.success(
                    data={'message': 'Logout successful'},
                    status=200
                )

            # Cookieをクリア
            response.delete_cookie(
                key=settings.AUTH_COOKIE_ACCESS_TOKEN,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )
            response.delete_cookie(
                key=settings.AUTH_COOKIE_REFRESH_TOKEN,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )
            
            return response

        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            # ログアウトはエラーでも成功扱い（セキュリティ的に）
            response = ResponseFormatter.success(
                data={'message': 'Logout completed'},
                status=200
            )
            
            # Cookieをクリア
            response.delete_cookie(
                key=settings.AUTH_COOKIE_ACCESS_TOKEN,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )
            response.delete_cookie(
                key=settings.AUTH_COOKIE_REFRESH_TOKEN,
                samesite=settings.AUTH_COOKIE_SAMESITE
            )
            
            return response

@method_decorator(csrf_protect, name='dispatch')
class RefreshView(CSRFProtectedView):
    """トークンリフレッシュ用ビュー"""
    
    def post(self, request):
        """アクセストークンのリフレッシュ処理"""
        try:
            # リフレッシュトークンをCookieから取得
            refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH_TOKEN)
        
            if not refresh_token:
                return ResponseFormatter.unauthorized(
                        "Refresh token not found"
                    )

            # サービス層でトークンリフレッシュ
            auth_service = AuthService()
            result = auth_service.refresh_tokens(refresh_token)
            
            if result is None:
                return ResponseFormatter.unauthorized(
                        "Invalid or expired refresh token"
                    )
            
            new_access_token, new_refresh_token = result
            
            # レスポンス作成
            response = ResponseFormatter.success(
                    data={'message': 'Token refreshed successfully'},
                    status=200
                )

            # 新しいトークンをCookieに設定
            response.set_cookie(
                key=settings.AUTH_COOKIE_ACCESS_TOKEN,
                value=new_access_token,
                max_age=settings.AUTH_COOKIE_ACCESS_MAX_AGE,
                httponly=settings.AUTH_COOKIE_HTTPONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE,
                secure=settings.AUTH_COOKIE_SECURE
            )
            response.set_cookie(
                key=settings.AUTH_COOKIE_REFRESH_TOKEN,
                value=new_refresh_token,
                max_age=settings.AUTH_COOKIE_REFRESH_MAX_AGE,
                httponly=settings.AUTH_COOKIE_HTTPONLY,
                samesite=settings.AUTH_COOKIE_SAMESITE,
                secure=settings.AUTH_COOKIE_SECURE
            )
            
            return response

        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return ResponseFormatter.server_error(
                "Token refresh failed",
                details=str(e) if settings.DEBUG else None
            )

    