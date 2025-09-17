"""
JSend仕様に準拠した統一レスポンス形式（DRF専用）
accounts/とblog/で共通使用
"""

from typing import Optional, Dict, Any
from rest_framework.response import Response
from rest_framework import status


class ResponseFormatter:
    """
    JSend仕様に準拠した統一レスポンス形式を提供するフォーマッタークラス
    
    レスポンス形式:
    - success: {"status": "success", "data": {...}}
    - fail: {"status": "fail", "data": {...}}  
    - error: {"status": "error", "message": "...", "code": "..."}
    
    注意: DRF（APIView/ViewSet）専用。Django Viewでは使用不可。
    """
    
    @staticmethod
    def success(data: Optional[Dict[str, Any]] = None, 
                status_code: int = status.HTTP_200_OK) -> Response:
        """
        成功レスポンス
        
        使用例:
            return ResponseFormatter.success({'user': user_data})
        """
        response_data = {
            "status": "success",
            "data": data
        }
        return Response(response_data, status=status_code)
    
    @staticmethod
    def fail(data: Dict[str, Any], 
             status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
        """
        失敗レスポンス（バリデーションエラーなど）
        
        使用例:
            return ResponseFormatter.fail({'email': ['無効なメールアドレス']})
        """
        response_data = {
            "status": "fail",
            "data": data
        }
        return Response(response_data, status=status_code)
    
    @staticmethod
    def error(message: str,
              code: Optional[str] = None,
              status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR) -> Response:
        """
        エラーレスポンス（システムエラーなど）
        
        使用例:
            return ResponseFormatter.error('サーバーエラー', code='SERVER_ERROR')
        """
        response_data = {
            "status": "error",
            "message": message
        }
        if code:
            response_data["code"] = code
        
        return Response(response_data, status=status_code)

    @staticmethod
    def created(data: Optional[Dict[str, Any]] = None) -> Response:
        """作成成功（201 Created）"""
        return ResponseFormatter.success(
            data=data, 
            status_code=status.HTTP_201_CREATED
        )
    
    @staticmethod
    def validation_error(errors: Dict[str, Any]) -> Response:
        """バリデーションエラー（422 Unprocessable Entity）"""
        return ResponseFormatter.fail(
            data=errors, 
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    
    @staticmethod
    def unauthorized(message: str = "Authentication required") -> Response:
        """認証エラー（401 Unauthorized）"""
        return ResponseFormatter.error(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def forbidden(message: str = "Access denied") -> Response:
        """権限エラー（403 Forbidden）"""
        return ResponseFormatter.error(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def not_found(message: str = "Resource not found") -> Response:
        """リソース未発見（404 Not Found）"""
        return ResponseFormatter.error(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )

    @staticmethod
    def method_not_allowed(message: str = "Method not allowed") -> Response:
        """メソッド不許可（405 Method Not Allowed）"""
        return ResponseFormatter.error(
            message=message,
            code="METHOD_NOT_ALLOWED",
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    @staticmethod
    def too_many_requests(message: str = "Too many requests") -> Response:
        """リクエスト過多（429 Too Many Requests）"""
        return ResponseFormatter.error(
            message=message,
            code="TOO_MANY_REQUESTS",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )

    @staticmethod
    def server_error(message: str = "Internal server error") -> Response:
        """サーバーエラー（500 Internal Server Error）"""
        return ResponseFormatter.error(
            message=message,
            code="SERVER_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )