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
                message: Optional[str] = None) -> Dict[str, Any]:
        """
        成功レスポンスを生成
        
        Args:
            data: レスポンスデータ
            message: 成功メッセージ（オプション）
            
        Returns:
            Dict: 統一形式の成功レスポンス
        """
        response_data = {
            "success": True,
            "data": data if data else {},
            "error": None,
        }
        
        # メッセージがある場合はdataに含める
        if message:
            if isinstance(response_data["data"], dict):
                response_data["data"]["message"] = message
            else:
                response_data["data"] = {"message": message}
            
        return response_data
    
    @staticmethod
    def error(message: str, 
              code: str = "error", 
              details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        エラーレスポンスを生成
        
        Args:
            message: エラーメッセージ
            code: エラーコード
            details: 詳細なエラー情報（オプション）
            
        Returns:
            Dict: 統一形式のエラーレスポンス
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
        
        return response_data
    
    @staticmethod
    def validation_error(errors: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """
        バリデーションエラー専用のレスポンスを生成
        
        Args:
            errors: バリデーションエラー（辞書または文字列）
            
        Returns:
            Dict: バリデーションエラーレスポンス
        """
        if isinstance(errors, str):
            return ResponseFormatter.error(
                message=errors,
                code="validation_error"
            )
        
        return ResponseFormatter.error(
            message="Validation failed",
            code="validation_error",
            details=errors
        )
    
    @staticmethod
    def unauthorized(message: str = "Authentication required") -> Dict[str, Any]:
        """
        認証エラー（401）レスポンスを生成
        
        Args:
            message: エラーメッセージ
            
        Returns:
            Dict: 401エラーレスポンス
        """
        return ResponseFormatter.error(
            message=message,
            code="unauthorized"
        )
    
    @staticmethod
    def forbidden(message: str = "Access denied") -> Dict[str, Any]:
        """
        権限エラー（403）レスポンスを生成
        
        Args:
            message: エラーメッセージ
            
        Returns:
            Dict: 403エラーレスポンス
        """
        return ResponseFormatter.error(
            message=message,
            code="forbidden"
        )
    
    @staticmethod
    def not_found(message: str = "Resource not found") -> Dict[str, Any]:
        """
        リソース不在（404）レスポンスを生成
        
        Args:
            message: エラーメッセージ
            
        Returns:
            Dict: 404エラーレスポンス
        """
        return ResponseFormatter.error(
            message=message,
            code="not_found"
        )
    
    @staticmethod
    def server_error(message: str = "Internal server error",
                    details: Optional[str] = None) -> Dict[str, Any]:
        """
        サーバーエラー（500）レスポンスを生成
        
        Args:
            message: エラーメッセージ
            details: エラーの詳細（開発環境でのみ表示推奨）
            
        Returns:
            Dict: 500エラーレスポンス
        """
        error_details = None
        if details:
            error_details = {"error_details": details}
            
        return ResponseFormatter.error(
            message=message,
            code="server_error",
            details=error_details
        )