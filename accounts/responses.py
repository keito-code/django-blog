from typing import Optional, Dict, Any
from django.http import JsonResponse


class ResponseFormatter:
    """
    JSend仕様に準拠した統一レスポンス形式を提供するフォーマッタークラス
    
    レスポンス形式:
    - success: {"status": "success", "data": {...}}
    - fail: {"status": "fail", "data": {...}}  
    - error: {"status": "error", "message": "...",}
    """
    
    @staticmethod
    def success(data: Optional[Dict[str, Any]] = None, 
                status_code: int = 200) -> JsonResponse:
    
        response_data = {
            "status": "success",
            "data": data
        }
        
        return JsonResponse(response_data, status=status_code)
    
    @staticmethod
    def fail(data: Dict[str, Any], status_code: int = 400) -> JsonResponse:

        # views.pyでエラーメッセージを辞書として渡す必要がある
        response_data = {
            "status": "fail",
            "data": data
        }
        
        return JsonResponse(response_data, status=status_code)
    
    @staticmethod
    def error(message: str, 
              status_code: int = 500) -> JsonResponse:

        response_data = {
            "status": "error",
            "message": message
        }
        
        return JsonResponse(response_data, status=status_code)
    
    @staticmethod
    def validation_error(errors: Dict[str, Any]) -> JsonResponse:
        return ResponseFormatter.fail(
            data=errors, 
            status_code=422
        )
    
    @staticmethod
    def unauthorized(message: str = "Authentication required") -> JsonResponse:
        return ResponseFormatter.error(
            message=message,
            status_code=401
        )
    
    @staticmethod
    def forbidden(message: str = "Access denied") -> JsonResponse:
        return ResponseFormatter.error(
            message=message,
            status_code=403
        )
    
    @staticmethod
    def not_found(message: str = "Resource not found") -> JsonResponse:
        return ResponseFormatter.error(
            message=message,
            status_code=404
        )
    
    @staticmethod
    def server_error(message: str = "Internal server error") -> JsonResponse:
        return ResponseFormatter.error(
            message=message,
            status_code=500
        )
    
    @staticmethod
    def created(data: Optional[Dict[str, Any]] = None) -> JsonResponse:
        return ResponseFormatter.success(data=data, status_code=201)
