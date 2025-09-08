"""
認証認可に関するビュー (DRF APIView版)

HTTPレイヤーの責務のみを担当し、ビジネスロジックはservices.pyに委譲する。
Cookie+JWT認証を実装し、CSRF保護を適用する。
"""

from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .services import AuthService
from .responses import ResponseFormatter
from .serializers import (
    RegisterSerializer,
    PublicUserSerializer,
    PrivateUserSerializer,
    AdminUserSerializer,
)

User = get_user_model()

@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFTokenView(APIView):
    """CSRFトークン取得エンドポイント"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        responses={
            200: OpenApiResponse(
                description="CSRFトークン取得成功",
                response={
                    'type': 'object',
                    'properties': {
                        'csrfToken': {'type': 'string'}
                    }
                }
            )
        }
    )
    def get(self, request):
        """CSRFトークンを取得"""
        csrf_token = get_token(request)
        
        # ResponseFormatterを使用して統一形式で返す
        response = ResponseFormatter.success(
            data={'csrfToken': csrf_token}
        )
        
        # CSRFトークンをCookieに設定
        response.set_cookie(
            key=settings.CSRF_COOKIE_NAME,
            value=csrf_token,
            max_age=settings.CSRF_COOKIE_AGE,
            httponly=settings.CSRF_COOKIE_HTTPONLY,
            secure=settings.CSRF_COOKIE_SECURE,
            samesite=settings.CSRF_COOKIE_SAMESITE
        )
        
        return response


class LoginView(APIView):
    """ログインエンドポイント（Cookie認証）"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string'},
                    'password': {'type': 'string'}
                },
                'required': ['username', 'password']
            }
        },
        responses={
            200: OpenApiResponse(description="ログイン成功"),
            401: OpenApiResponse(description="認証失敗"),
            400: OpenApiResponse(description="バリデーションエラー")
        }
    )
    def post(self, request):
        """ユーザーログイン処理"""
        username = request.data.get('username')
        password = request.data.get('password')
        
        # 必須フィールドチェック
        if not username or not password:
            return ResponseFormatter.validation_error(
                "ユーザー名とパスワードは必須です"
            )
        
        # サービス層で認証処理
        auth_service = AuthService()
        result = auth_service.login(username, password)
        
        if not result['success']:
            return ResponseFormatter.unauthorized(
                result.get('error', '認証に失敗しました')
            )
        
        # レスポンス作成
        response = ResponseFormatter.success(
            data={
                'user': PublicUserSerializer(result['user']).data,
                'message': 'ログインに成功しました'
            }
        )
        
        # HttpOnly Cookieにトークンを設定
        response.set_cookie(
            key=settings.AUTH_COOKIE_ACCESS_TOKEN,
            value=result['access_token'],
            max_age=settings.AUTH_COOKIE_ACCESS_MAX_AGE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            path=settings.AUTH_COOKIE_PATH
        )
        
        response.set_cookie(
            key=settings.AUTH_COOKIE_REFRESH_TOKEN,
            value=result['refresh_token'],
            max_age=settings.AUTH_COOKIE_REFRESH_MAX_AGE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            path=settings.AUTH_COOKIE_PATH
        )
        
        return response


class LogoutView(APIView):
    """ログアウトエンドポイント"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: OpenApiResponse(description="ログアウト成功")
        }
    )
    def post(self, request):
        """ログアウト処理"""
        # Cookieからリフレッシュトークンを取得
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH_TOKEN)
        
        # トークンをブラックリストに追加（あれば）
        if refresh_token:
            auth_service = AuthService()
            auth_service.logout(refresh_token)
        
        # レスポンス作成
        response = ResponseFormatter.success(
            data={'message': 'ログアウトしました'}
        )
        
        # Cookie削除
        response.delete_cookie(
            key=settings.AUTH_COOKIE_ACCESS_TOKEN,
            path=settings.AUTH_COOKIE_PATH,
            domain=settings.AUTH_COOKIE_DOMAIN,
        )
        response.delete_cookie(
            key=settings.AUTH_COOKIE_REFRESH_TOKEN,
            path=settings.AUTH_COOKIE_PATH,
            domain=settings.AUTH_COOKIE_DOMAIN,
        )
        
        return response


class RefreshTokenView(APIView):
    """トークンリフレッシュエンドポイント"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        responses={
            200: OpenApiResponse(description="トークン更新成功"),
            401: OpenApiResponse(description="無効なリフレッシュトークン")
        }
    )
    def post(self, request):
        """アクセストークンを更新"""
        # Cookieからリフレッシュトークンを取得
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH_TOKEN)
        
        if not refresh_token:
            return ResponseFormatter.unauthorized(
                "リフレッシュトークンが必要です"
            )
        
        # サービス層でトークンリフレッシュ
        auth_service = AuthService()
        result = auth_service.refresh_token(refresh_token)
        
        if not result['success']:
            return ResponseFormatter.unauthorized(
                result.get('error', 'トークンの更新に失敗しました')
            )
        
        # レスポンス作成
        response = ResponseFormatter.success(
            data={'message': 'トークンを更新しました'}
        )
        
        # 新しいアクセストークンをCookieに設定
        response.set_cookie(
            key=settings.AUTH_COOKIE_ACCESS_TOKEN,
            value=result['access_token'],
            max_age=settings.AUTH_COOKIE_ACCESS_MAX_AGE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            path=settings.AUTH_COOKIE_PATH
        )
        
        # ローテーションされた場合は新しいリフレッシュトークンも設定
        if result.get('refresh_token'):
            response.set_cookie(
                key=settings.AUTH_COOKIE_REFRESH_TOKEN,
                value=result['refresh_token'],
                max_age=settings.AUTH_COOKIE_REFRESH_MAX_AGE,
                httponly=settings.AUTH_COOKIE_HTTPONLY,
                secure=settings.AUTH_COOKIE_SECURE,
                samesite=settings.AUTH_COOKIE_SAMESITE,
                domain=settings.AUTH_COOKIE_DOMAIN,
                path=settings.AUTH_COOKIE_PATH
            )
        
        return response


class RegisterView(APIView):
    """ユーザー登録エンドポイント"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(description="登録成功"),
            400: OpenApiResponse(description="バリデーションエラー")
        }
    )
    def post(self, request):
        """新規ユーザー登録"""
        serializer = RegisterSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ResponseFormatter.validation_error(
                serializer.errors
            )
        
        # ユーザー作成
        user = serializer.save()
        
        # トークン生成
        refresh = RefreshToken.for_user(user)
        
        # レスポンス作成
        response = ResponseFormatter.success(
            data={
                'user': PublicUserSerializer(user).data,
                'message': '登録が完了しました'
            },
            status=201
        )
        
        # Cookie設定
        response.set_cookie(
            key=settings.AUTH_COOKIE_ACCESS_TOKEN,
            value=str(refresh.access_token),
            max_age=settings.AUTH_COOKIE_ACCESS_MAX_AGE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            path=settings.AUTH_COOKIE_PATH
        )
        
        response.set_cookie(
            key=settings.AUTH_COOKIE_REFRESH_TOKEN,
            value=str(refresh),
            max_age=settings.AUTH_COOKIE_REFRESH_MAX_AGE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            path=settings.AUTH_COOKIE_PATH
        )
        
        return response


class CurrentUserView(APIView):
    """現在のユーザー情報エンドポイント"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: OpenApiResponse(description="ユーザー情報取得成功"),
            401: OpenApiResponse(description="認証が必要です")
        }
    )
    def get(self, request):
        """現在のユーザー情報を取得"""
        # スタッフかどうかでシリアライザーを切り替え
        if request.user.is_staff:
            serializer = AdminUserSerializer(request.user)
        else:
            serializer = PrivateUserSerializer(request.user)
        
        return ResponseFormatter.success(data=serializer.data)
    
    @extend_schema(
        request=PrivateUserSerializer,
        responses={
            200: OpenApiResponse(description="更新成功"),
            400: OpenApiResponse(description="バリデーションエラー"),
            401: OpenApiResponse(description="認証が必要です")
        }
    )
    def put(self, request):
        """ユーザー情報を更新"""
        # スタッフかどうかでシリアライザーを切り替え
        if request.user.is_staff:
            serializer = AdminUserSerializer(
                request.user, 
                data=request.data, 
                partial=True
            )
        else:
            serializer = PrivateUserSerializer(
                request.user, 
                data=request.data, 
                partial=True
            )
        
        if not serializer.is_valid():
            return ResponseFormatter.validation_error(
                serializer.errors
            )
        
        serializer.save()
        
        return ResponseFormatter.success(
            data={
                'user': serializer.data,
                'message': 'プロフィールを更新しました'
            }
        )


class VerifyTokenView(APIView):
    """トークン検証エンドポイント"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        responses={
            200: OpenApiResponse(description="トークン有効"),
            401: OpenApiResponse(description="トークン無効")
        }
    )
    def post(self, request):
        """トークンの有効性を検証"""
        # Cookieからアクセストークンを取得
        access_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS_TOKEN)
        
        if not access_token:
            return ResponseFormatter.unauthorized(
                "トークンが必要です"
            )
        
        # サービス層で検証
        auth_service = AuthService()
        result = auth_service.verify_token(access_token)
        
        if not result['success']:
            return ResponseFormatter.unauthorized(
                result.get('error', 'トークンが無効です')
            )
        
        # ユーザー情報を含めて返す
        user = result.get('user')
        if user:
            return ResponseFormatter.success(
                data={
                    'valid': True,
                    'user': PublicUserSerializer(user).data
                }
            )
        
        return ResponseFormatter.success(data={'valid': True})