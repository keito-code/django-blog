from django.http import JsonResponse
from typing import Optional, Dict, Any, Union


class ResponseFormatter:
    """
    統一されたレスポンス形式を提供するフォーマッタークラス
    
    レスポンス形式:
    成功時: {"success": true, "data": {...}, "error": null}
    失敗時: {"success": false, "data": null, "error": {"code": "...", "message": "..."}}
    """
    
    @staticmethod
    def success(data: Optional[Dict[str, Any]] = None, 
                message: Optional[str] = None,
                status: int = 200) -> JsonResponse:
        """
        成功レスポンスを生成
        
        Args:
            data: レスポンスデータ
            message: 成功メッセージ（オプション）
            status: HTTPステータスコード
            
        Returns:
            JsonResponse: 統一形式の成功レスポンス
        """
        response_data = {
            "success": True,
            "data": data,
            "error": None,
        }
        
        # メッセージがある場合はdataに含める
        if message and isinstance(response_data["data"], dict):
            response_data["data"]["message"] = message
        elif message and response_data["data"] is None:
            response_data["data"] = {"message": message}
            
        return JsonResponse(response_data, status=status)
    
    @staticmethod
    def error(message: str, 
              code: str = "error", 
              details: Optional[Dict[str, Any]] = None,
              status: int = 400) -> JsonResponse:
        """
        エラーレスポンスを生成
        
        Args:
            message: エラーメッセージ
            code: エラーコード
            details: 詳細なエラー情報（オプション）
            status: HTTPステータスコード
            
        Returns:
            JsonResponse: 統一形式のエラーレスポンス
        """
        error_data = {
            "code": code,
            "message": message,
        }
        
        # 詳細情報がある場合は追加
        if details:
            error_data["details"] = details
            
        response_data = {
            "success": False,
            "data": None,
            "error": error_data,
        }
        
        return JsonResponse(response_data, status=status)
    
    @staticmethod
    def validation_error(errors: Union[Dict[str, Any], str], 
                        status: int = 400) -> JsonResponse:
        """
        バリデーションエラー専用のレスポンスを生成
        
        Args:
            errors: バリデーションエラー（辞書または文字列）
            status: HTTPステータスコード
            
        Returns:
            JsonResponse: バリデーションエラーレスポンス
        """
        if isinstance(errors, str):
            return ResponseFormatter.error(
                message=errors,
                code="validation_error",
                status=status
            )
        
        return ResponseFormatter.error(
            message="Validation failed",
            code="validation_error",
            details=errors,
            status=status
        )
    
    @staticmethod
    def unauthorized(message: str = "Authentication required") -> JsonResponse:
        """
        認証エラー（401）レスポンスを生成
        
        Args:
            message: エラーメッセージ
            
        Returns:
            JsonResponse: 401エラーレスポンス
        """
        return ResponseFormatter.error(
            message=message,
            code="unauthorized",
            status=401
        )
    
    @staticmethod
    def forbidden(message: str = "Access denied") -> JsonResponse:
        """
        権限エラー（403）レスポンスを生成
        
        Args:
            message: エラーメッセージ
            
        Returns:
            JsonResponse: 403エラーレスポンス
        """
        return ResponseFormatter.error(
            message=message,
            code="forbidden",
            status=403
        )
    
    @staticmethod
    def not_found(message: str = "Resource not found") -> JsonResponse:
        """
        リソース不在（404）レスポンスを生成
        
        Args:
            message: エラーメッセージ
            
        Returns:
            JsonResponse: 404エラーレスポンス
        """
        return ResponseFormatter.error(
            message=message,
            code="not_found",
            status=404
        )
    
    @staticmethod
    def server_error(message: str = "Internal server error",
                    details: Optional[str] = None) -> JsonResponse:
        """
        サーバーエラー（500）レスポンスを生成
        
        Args:
            message: エラーメッセージ
            details: エラーの詳細（開発環境でのみ表示推奨）
            
        Returns:
            JsonResponse: 500エラーレスポンス
        """
        error_details = None
        if details:
            error_details = {"error_details": details}
            
        return ResponseFormatter.error(
            message=message,
            code="server_error",
            details=error_details,
            status=500
        )