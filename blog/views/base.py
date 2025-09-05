import json
import logging
from typing import Any
from django.views import View
from django.http import HttpRequest, JsonResponse
from django.conf import settings
from accounts.responses import ResponseFormatter
from accounts.services import AuthService
from blog.exceptions import BlogPermissionError  

logger = logging.getLogger(__name__)


class ServiceBasedView(View):
    """サービス層を使うビューの基底クラス"""
    
    service_class = None  # サブクラスで定義
    require_auth = True   # デフォルトで認証必須
    
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """認証チェックと共通エラーハンドリング"""
        # 認証チェック
        if self.require_auth:
            auth_result = self._authenticate(request)
            if auth_result is not True:
                return auth_result  # エラーレスポンスを返す
        
        # エラーハンドリング
        try:
            return super().dispatch(request, *args, **kwargs)
        except BlogPermissionError as e:
            logger.info(f"Permission denied in {self.__class__.__name__}: {str(e)}")
            return ResponseFormatter.forbidden(str(e))
        except ValueError as e:
            logger.warning(f"Validation error in {self.__class__.__name__}: {str(e)}")
            return ResponseFormatter.validation_error(str(e))
        except Exception as e:
            logger.error(
                f"Unexpected error in {self.__class__.__name__}: {str(e)}", 
                exc_info=True
            )
            return ResponseFormatter.server_error(
                "An error occurred",
                details=str(e) if settings.DEBUG else None
            )
    
    def _authenticate(self, request: HttpRequest):
        """認証処理"""
        # Cookieからトークン取得
        access_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS_TOKEN)
        
        if not access_token:
            return ResponseFormatter.unauthorized("Authentication required")
        
        # トークン検証
        auth_service = AuthService()
        user = auth_service.verify_access_token(access_token)
        
        if not user:
            return ResponseFormatter.unauthorized("Invalid or expired token")
        
        # requestにユーザーを付加
        request.user = user
        return True  # 認証成功
    
    def get_json_data(self, request: HttpRequest) -> dict[str, Any]:
        """JSONボディをパース"""
        try:
            return json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format")
    
    def get_service(self):
        """サービスインスタンスを取得"""
        if not self.service_class:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define service_class"
            )
        return self.service_class()