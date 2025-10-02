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
from .services import AuthService, UserService
from core.responses import ResponseFormatter
from rest_framework.generics import GenericAPIView
from core.serializers import (
    SuccessResponseSerializer,
    FailResponseSerializer,
    ErrorResponseSerializer  
)
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
    AdminUpdateUserSerializer
)

User = get_user_model()

@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFTokenView(APIView):
    """CSRFトークン取得エンドポイント"""
    authentication_classes = []
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
    authentication_classes = []
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=LoginSerializer,
        responses={
            200: LoginSuccessResponseSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer, 
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
            password=validated_data['password'],
            request=request
        )
        # サービスからの戻り値（辞書）で成功・失敗を判断
        if not login_result['ok']:
            # サービスが返した詳細なエラーメッセージを使う
            return ResponseFormatter.unauthorized(login_result['error'])

        user = login_result['user']
        tokens = login_result['tokens']

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
class LogoutView(GenericAPIView):
    """ログアウトエンドポイント"""
    permission_classes = [IsAuthenticated]
    serializer_class = SuccessResponseSerializer
    
    @extend_schema(
        request=None,
        responses={
            200: SuccessResponseSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer
        }
    )
    def post(self, request):
        """ログアウト処理"""
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH_TOKEN)
        
        # サービス層での処理結果をハンドリング
        if refresh_token:
            auth_service = AuthService()
            # 戻り値を受け取る
            logout_result = auth_service.logout(refresh_token)

            # 失敗ならサーバーエラー
            if not logout_result['ok']:
                return ResponseFormatter.server_error(
                    logout_result['error']
                )

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
class RefreshTokenView(GenericAPIView):
    """トークンリフレッシュエンドポイント"""
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = SuccessResponseSerializer
    
    @extend_schema(
        request=None,
        responses={
            200: SuccessResponseSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer
        }
    )
    def post(self, request):
        """アクセストークンを更新"""
        # Cookieからリフレッシュトークンを取得
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH_TOKEN)
        
        if not refresh_token:
            return ResponseFormatter.unauthorized("Refresh token is required")
        
        
        auth_service = AuthService()
        # サービスを呼び出し、結果を辞書で受け取る
        refresh_result = auth_service.refresh_tokens(refresh_token)

        if not refresh_result['ok']:
            return ResponseFormatter.unauthorized(refresh_result['error'])

        tokens = refresh_result['tokens']
    
        response = ResponseFormatter.success()

        # 生成したレスポンスオブジェクトに、新しいトークンをCookieとして設定
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
class RegisterView(APIView):
    """ユーザー登録エンドポイント"""
    authentication_classes = []
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: RegisterSuccessResponseSerializer,
            403: ErrorResponseSerializer,
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
        tokens = register_result['tokens'] 

        response = ResponseFormatter.created(
            data={'user': PublicUserSerializer(user).data}
        )
        
        # Cookie設定
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
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer
        }
    )
    def get(self, request):
        """現在のユーザー情報を取得"""
        user_serializer = self.get_user_serializer()
        serializer = user_serializer(request.user)
        return ResponseFormatter.success(data={'user': serializer.data})
    
    @extend_schema(
        request=UpdateUserSerializer,
        responses={
            200: UpdateUserResponseSerializer,
            422: FailResponseSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer
        }
    )

    def patch(self, request):
        """ユーザー情報を更新"""
        user_serializer = self.get_user_serializer()
        serializer = user_serializer(
            request.user, 
            data=request.data,
            partial=True
        )
        
        if not serializer.is_valid():
            return ResponseFormatter.validation_error(serializer.errors)

        # --- サービス層を呼び出して更新を依頼 ---
        user_service = UserService()
        updated_user = user_service.update_user(
            user=request.user, 
            validated_data=serializer.validated_data
        )

        # --- 出力処理 ---
        if request.user.is_staff:
            response_data = AdminUserSerializer(updated_user).data
        else:
            response_data = PrivateUserSerializer(updated_user).data

        return ResponseFormatter.success(data={'user': response_data})

class VerifyTokenView(APIView):
    """トークン検証エンドポイント"""
    authentication_classes = []
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
        
        if not verification_result['ok']:
            return ResponseFormatter.unauthorized(
                    verification_result['error'])
        
        return ResponseFormatter.success(data={'valid': True})