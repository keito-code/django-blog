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
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema
from .services import AuthService
from .responses import ResponseFormatter
from .serializers import (
    LoginSerializer,
    LoginSuccessResponseSerializer,
    CSRFTokenResponseSerializer,
    RegisterSuccessResponseSerializer,
    PrivateUserResponseSerializer,
    UpdateUserResponseSerializer,
    VerifyTokenSuccessResponseSerializer,
    RegisterSerializer,
    PublicUserSerializer,
    PrivateUserSerializer,
    UpdateUserSerializer,
    AdminUserSerializer,
    AdminUpdateUserSerializer,
    SuccessResponseSerializer,
    FailResponseSerializer,
    ErrorResponseSerializer
)

User = get_user_model()

@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFTokenView(APIView):
    """CSRFトークン取得エンドポイント"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        responses={
            200: CSRFTokenResponseSerializer
        }
    )

    def get(self, request):
        """CSRFトークンを取得"""
        csrf_token = get_token(request)
        response = ResponseFormatter.success(
            data={'csrf_token': csrf_token}
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

@method_decorator(csrf_protect, name='dispatch')
class LoginView(APIView):
    """ログインエンドポイント（Cookie認証）"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=LoginSerializer,
        responses={
            200: LoginSuccessResponseSerializer,
            401: ErrorResponseSerializer, 
            422: FailResponseSerializer
        }
    )
    def post(self, request):
        """ユーザーログイン処理"""
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return ResponseFormatter.validation_error(serializer.errors)
        
        # サービス層で認証処理
        validated_data = serializer.validated_data
        auth_service = AuthService()
        login_result = auth_service.login(
            email=validated_data['email'],
            password=validated_data['password']
        )

        # 失敗時 (Noneが返ってきた場合)
        if login_result is None:
            return ResponseFormatter.unauthorized("Authentication failed")

        # 成功時（タプルが返ってきた場合）
        user, tokens = login_result

        # レスポンス作成
        response = ResponseFormatter.success(
                data={'user': PublicUserSerializer(user).data}
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
            200: SuccessResponseSerializer,
            401: ErrorResponseSerializer
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
        response = ResponseFormatter.success()
        
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
            200: SuccessResponseSerializer,
            401: ErrorResponseSerializer
        }
    )
    def post(self, request):
        """アクセストークンを更新"""
        # Cookieからリフレッシュトークンを取得
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH_TOKEN)
        
        if not refresh_token:
            return ResponseFormatter.unauthorized("Refresh token is required")
        
        # サービス層でトークンリフレッシュ
        auth_service = AuthService()
        new_tokens = auth_service.refresh_tokens(refresh_token)

        if new_tokens is None:
            return ResponseFormatter.unauthorized("Invalid refresh token")
        
        # セキュリティの観点からアクセストークンは返さない
        response = ResponseFormatter.success()

        # 生成したレスポンスオブジェクトに、新しいトークンをCookieとして設定
        response.set_cookie(
            key=settings.AUTH_COOKIE_ACCESS_TOKEN,
            value=new_tokens['access'],
            max_age=settings.AUTH_COOKIE_ACCESS_MAX_AGE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            path=settings.AUTH_COOKIE_PATH
        )
        
        response.set_cookie(
            key=settings.AUTH_COOKIE_REFRESH_TOKEN,
            value=new_tokens['refresh'],
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
            201: RegisterSuccessResponseSerializer,
            422: FailResponseSerializer
        }
    )
    def post(self, request):
        """新規ユーザー登録"""
        serializer = RegisterSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ResponseFormatter.validation_error(serializer.errors )

        validated_data = serializer.validated_data
        auth_service = AuthService()

        register_result = auth_service.register(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        # 辞書から受け取る
        user = register_result['user']
        new_tokens = register_result['tokens'] 

        response_data = PublicUserSerializer(user).data
        response = ResponseFormatter.created(data=response_data)
        
        # Cookie設定
        response.set_cookie(
            key=settings.AUTH_COOKIE_ACCESS_TOKEN,
            value=new_tokens['access'],
            max_age=settings.AUTH_COOKIE_ACCESS_MAX_AGE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            path=settings.AUTH_COOKIE_PATH
        )
        
        response.set_cookie(
            key=settings.AUTH_COOKIE_REFRESH_TOKEN,
            value=new_tokens['refresh'],
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

    def get_user_serializer(self):
        """
        リクエストのメソッド(GET/PATCH)とユーザーの権限に応じて
        使用するシリアライザーを動的に切り替える。
        """

        if self.request.method == 'PATCH':
            if self.request.user.is_staff:
                return AdminUpdateUserSerializer
            return UpdateUserSerializer
        
        if self.request.user.is_staff:
            return AdminUserSerializer
        return PrivateUserSerializer
    
    @extend_schema(
        responses={
            200: PrivateUserResponseSerializer,
            401: ErrorResponseSerializer
        }
    )
    def get(self, request):
        """現在のユーザー情報を取得"""
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(request.user)
        return ResponseFormatter.success(data=serializer.data)
    
    @extend_schema(
        request=UpdateUserSerializer,
        responses={
            200: UpdateUserResponseSerializer,
            422: FailResponseSerializer,
            401: ErrorResponseSerializer
        }
    )

    def patch(self, request):
        """ユーザー情報を更新"""
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            request.user, 
            data=request.data,
            partial=True
        )
        
        if not serializer.is_valid():
            return ResponseFormatter.validation_error(serializer.errors)

        # データベースを更新し、更新後のuserインスタンスを受け取る
        updated_user = serializer.save()

        # --- 出力処理 ---
        if request.user.is_staff:
            response_data = AdminUserSerializer(updated_user).data
        else:
            response_data = PrivateUserSerializer(updated_user).data

        return ResponseFormatter.success(data=response_data)

class VerifyTokenView(APIView):
    """トークン検証エンドポイント"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        responses={
            200: VerifyTokenSuccessResponseSerializer,
            401: ErrorResponseSerializer
        }
    )
    def get(self, request):
        access_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS_TOKEN)
        
        if not access_token:
            return ResponseFormatter.unauthorized("Token is required")
        
        # サービス層で検証
        auth_service = AuthService()
        verification_result = auth_service.verify_token(access_token)
        
        if not verification_result['success']:
            return ResponseFormatter.unauthorized(
                    verification_result.get('error', 'Invalid token')
                )
        
        # 単一責任に従い、検証結果だけを返す
        response_data = {'valid': True}
        return ResponseFormatter.success(data=response_data)
        
