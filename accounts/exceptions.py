from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.views import exception_handler
from django.core.exceptions import PermissionDenied
from django.http import Http404
from accounts.responses import ResponseFormatter 

def custom_exception_handler(exc, context):
    """
    DRF例外を JSend形式 に統一するカスタムハンドラ
    """

    # バリデーションエラー -> 422
    if isinstance(exc, ValidationError):
        return ResponseFormatter.validation_error(exc.detail)

    # JSONパースエラー -> 400
    if isinstance(exc, ParseError):
        return ResponseFormatter.error(
            message=str(exc.detail),
            status_code=400
        )

    # 上記以外の場合、DRFのデフォルトハンドラを呼び出す
    response = exception_handler(exc, context)

    # DRFが処理できない例外をここで処理
    if response is None:
        if isinstance(exc, PermissionDenied):
            return ResponseFormatter.forbidden(str(exc) or "Permission denied.")
        
        if isinstance(exc, Http404):
            return ResponseFormatter.not_found(str(exc) or "Resource not found.")
        
        # 予期せぬエラーは500として返す
        return ResponseFormatter.server_error() 

    # その他のDRFエラーをカスタム形式に変換
    detail = response.data.get('detail', None)

    if response.status_code == 401:
        return ResponseFormatter.unauthorized(detail or "Authentication required.")
        
    elif response.status_code == 403:
        return ResponseFormatter.forbidden(detail or "Access denied.")
        
    elif response.status_code == 404:
        return ResponseFormatter.not_found(detail or "Resource not found.")
    
    else:
        # 405 Method Not Allowed や 429 Throttled など、その他のエラー
        return ResponseFormatter.error(
            message=detail or "An error occurred.",
            status_code=response.status_code
        )

