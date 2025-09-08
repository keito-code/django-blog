"""
認証認可に関するビュー (DRF APIView版)

HTTPレイヤーの責務のみを担当し、ビジネスロジックはservices.pyに委譲する。
Cookie+JWT認証を実装し、CSRF保護を適用する。
"""

from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
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
    UpdateUserSerializer,
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
                        'csrf_token': {'type': 'string'}
                    }
                }
            )
        }
    )
    def get(self, request):
        """CSRFトークンを取得"""
        csrf_token = get_token(request)
        response_data = ResponseFormatter.success(
            data={'csrf_token': csrf_token}
        )
        response = Response(response_data, status=status.HTTP_200_OK)
        
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

@method_decorator(csrf_protect, name='dispatch')
class LoginView(APIView):
    """ログインエンドポイント（Cookie認証）"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'email': {'type': 'string'},
                    'password': {'type': 'string'}
                },
                'required': ['email', 'password']
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
        email = request.data.get('email')
        password = request.data.get('password')
        
        # 必須フィールドチェック
        if not email or not password:
            return Response(
                ResponseFormatter.validation_error(
                    "Email and password are required"
                ), status=status.HTTP_400_BAD_REQUEST
            )
        
        # サービス層で認証処理
        auth_service = AuthService()
        result = auth_service.login(email, password)

        # 失敗時 (Noneが返ってきた場合)
        if result is None:
            return Response(
                ResponseFormatter.unauthorized(
                    "Authentication failed"
                ),
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 成功時（タプルが返ってきた場合）
        user, tokens = result

        # レスポンス作成
        response = Response(
            ResponseFormatter.success(
                data={
                    'user': PublicUserSerializer(user).data,
                    'message': 'Login successful'
                }
            ),
            status=status.HTTP_200_OK
        )
        
        # HttpOnly Cookieにトークンを設定
        response.set_cookie(
            key=settings.AUTH_COOKIE_ACCESS_TOKEN,
            value=tokens['access'],
            max_age=settings.AUTH_COOKIE_ACCESS_MAX_AGE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            path=settings.AUTH_COOKIE_PATH
        )
        
        response.set_cookie(
            key=settings.AUTH_COOKIE_REFRESH_TOKEN,
            value=tokens['refresh'],
            max_age=settings.AUTH_COOKIE_REFRESH_MAX_AGE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            path=settings.AUTH_COOKIE_PATH
        )
        
        return response

@method_decorator(csrf_protect, name='dispatch')
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
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH_TOKEN)
        
        # トークンがあればブラックリストに追加
        if refresh_token:
            auth_service = AuthService()
            auth_service.logout(refresh_token)
        
        # レスポンス作成
        response = Response(
            ResponseFormatter.success(
                data={'message': 'Logout successful'}
            ),
            status=status.HTTP_200_OK
        )
        
        # Cookie削除
        response.delete_cookie(
            key=settings.AUTH_COOKIE_ACCESS_TOKEN,
            path=settings.AUTH_COOKIE_PATH,
            domain=settings.AUTH_COOKIE_DOMAIN,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )
        response.delete_cookie(
            key=settings.AUTH_COOKIE_REFRESH_TOKEN,
            path=settings.AUTH_COOKIE_PATH,
            domain=settings.AUTH_COOKIE_DOMAIN,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )
        
        return response

@method_decorator(csrf_protect, name='dispatch')
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
            return Response(
                ResponseFormatter.unauthorized(
                    "Refresh token is required"
                ), status=status.HTTP_401_UNAUTHORIZED
            )
        
        # サービス層でトークンリフレッシュ
        auth_service = AuthService()
        result = auth_service.refresh_tokens(refresh_token)

        if result is None:
            return Response(
                ResponseFormatter.unauthorized("Invalid refresh token"),
                status=status.HTTP_401_UNAUTHORIZED
            )

        response = Response(
            ResponseFormatter.success(
                data={'message': 'Token refreshed successfully'}
            ),
            status=status.HTTP_200_OK
        )

        # 新しいアクセストークンをCookieに設定
        response.set_cookie(
            key=settings.AUTH_COOKIE_ACCESS_TOKEN,
            value=result['access'],
            max_age=settings.AUTH_COOKIE_ACCESS_MAX_AGE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            path=settings.AUTH_COOKIE_PATH
        )
        
        response.set_cookie(
            key=settings.AUTH_COOKIE_REFRESH_TOKEN,
            value=result['refresh'],
            max_age=settings.AUTH_COOKIE_REFRESH_MAX_AGE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            path=settings.AUTH_COOKIE_PATH
        )
        return response

@method_decorator(csrf_protect, name='dispatch')
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
            return Response(
                ResponseFormatter.validation_error(
                    serializer.errors
                ), status=status.HTTP_400_BAD_REQUEST
            )
        
        # ユーザー作成
        user = serializer.save()
        
        # トークン生成
        refresh = RefreshToken.for_user(user)
        
        # レスポンス作成
        response_data = ResponseFormatter.success(
            data={
                'user': PublicUserSerializer(user).data,
                'message': 'Registration successful'
            }
        )
        response = Response(response_data, status=status.HTTP_201_CREATED)
        
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

@method_decorator(csrf_protect, name='dispatch')
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
        
        return Response(
            ResponseFormatter.success(data=serializer.data),
            status=status.HTTP_200_OK
        )
    
    @extend_schema(
        request=UpdateUserSerializer,
        responses={
            200: OpenApiResponse(description="更新成功"),
            400: OpenApiResponse(description="バリデーションエラー"),
            401: OpenApiResponse(description="認証が必要です")
        }
    )

    def patch(self, request):
        """ユーザー情報を更新"""
        # スタッフかどうかでシリアライザーを切り替え
        if request.user.is_staff:
            serializer = AdminUserSerializer(
                request.user, 
                data=request.data, 
                partial=True
            )
        else:
            serializer = UpdateUserSerializer(
                request.user, 
                data=request.data, 
                partial=True
            )
        
        if not serializer.is_valid():
            return Response(
                ResponseFormatter.validation_error(
                    serializer.errors
                ), status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save()
        
        return Response(
            ResponseFormatter.success(
                data={
                    'user': serializer.data,
                    'message': 'Profile updated successfully'
                }
            ), status=status.HTTP_200_OK
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
    def get(self, request):
        # Cookieからアクセストークンを取得
        access_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS_TOKEN)
        
        if not access_token:
            return Response(
                ResponseFormatter.unauthorized(
                    "Token is required"
                ), status=status.HTTP_401_UNAUTHORIZED
            )
        
        # サービス層で検証
        auth_service = AuthService()
        result = auth_service.verify_token(access_token)
        
        if not result['success']:
            return Response(
                ResponseFormatter.unauthorized(
                    result.get('error', 'Invalid token')
                ), status=status.HTTP_401_UNAUTHORIZED
            )
        
        # ユーザー情報を含めて返す
        user = result.get('user')
        if user:
            return Response(
                ResponseFormatter.success(
                    data={
                        'valid': True,
                        'user': PublicUserSerializer(user).data
                    }
                ), status=status.HTTP_200_OK
            )
        
        return Response(
            ResponseFormatter.success(data={'valid': True}),
            status=status.HTTP_200_OK
        )